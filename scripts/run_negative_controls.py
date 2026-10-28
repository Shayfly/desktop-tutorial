"""Negative controls in CI, readable without log access (2026-10-27).

Every tests/negative_controls/*.json spec names a deliberate breakage (exact text replaced once in a file) and the
EXACT set of tests that must fail because of it. For each control this copies the repository to a temp dir, applies
the mutation, runs pytest on the targets, and prints one ::notice with PASS|FAIL and the NAMES of the tests that
failed. A control that did not run -- mutation not applied, nothing collected, pytest crashed, an expected test
skipped -- is FAIL, never a silent pass. The sha256 of each spec's evidence files is printed as a ::notice too.
Exit 1 when any control FAILs.

  python scripts/run_negative_controls.py            # every spec
  python scripts/run_negative_controls.py pr154      # specs whose file name starts with pr154
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPECS = ROOT / 'tests' / 'negative_controls'
IGNORE = shutil.ignore_patterns('.git', 'node_modules', '__pycache__', '*.pyc', '.pytest_cache')


def notice(title: str, message: str) -> None:
    clean = ' '.join(str(message).replace('%', '%25').split())
    print(f'::notice title={title}::{clean}'[:4000], flush=True)


def _git(repo, *args, check=False):
    return subprocess.run(['git', '-c', 'user.name=nc', '-c', 'user.email=nc@localhost', *args], cwd=repo,
                          capture_output=True, text=True, check=check)


ENV = (os.getenv('NC_ENV') or '').strip()      # '' (v24-ci, no Postgres) | 'pg' (intake-budget-pg, real Postgres)


def expected_for(spec: dict, env: str) -> list[str]:
    """The tests this environment must see fail. A control may name its own set per environment
    (`expect_failed_pg`): in pg the real-store tests run, so a mutation breaks them too."""
    return sorted(spec.get(f'expect_failed_{env}') or spec['expect_failed']) if env else sorted(spec['expect_failed'])


def verdict(failed, expected, env: str) -> tuple[bool, str]:
    """An expected test that did not fail is ALWAYS a FAIL (the control proves nothing). A test that failed beyond
    the expected set is a FAIL too -- except in pg, where it is reported as INFO: there the real-store tests also
    run and a mutation may break more than the set the spec names. Never the other way round."""
    missing = sorted(set(expected) - set(failed))
    extra = sorted(set(failed) - set(expected))
    ok = not missing and (not extra or env == 'pg')
    return ok, ((f' missing={missing}' if missing else '') + (f' extra={extra}' if extra and not ok else '')
                + (f' INFO extra failures in {env}: {extra}' if extra and ok else ''))


def run_control(spec: dict, cid: str = 'NC', nc_env: str | None = None) -> tuple[bool, str]:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='nc-'))
    try:
        repo = tmp / 'repo'
        shutil.copytree(ROOT, repo, ignore=IGNORE)
        files = sorted({m['file'] for m in spec['mutations']})
        # The mutated files are tracked in a throw-away git repo of the copy, so the evidence is git's own diff and
        # a clean status after the restore -- not a claim by this script.
        _git(repo, 'init', '-q', check=True)
        _git(repo, 'add', '--', *files, check=True)
        _git(repo, 'commit', '-q', '-m', 'baseline', check=True)
        applied = []
        for m in spec['mutations']:
            path = repo / m['file']
            text = path.read_text(encoding='utf-8')
            found = text.count(m['old'])
            if found != 1:
                return False, f"DID NOT RUN: mutation not applied ({m['file']}: target text found {found} times, need 1)"
            line_no = text[:text.index(m['old'])].count('\n') + 1
            before = text.splitlines()[line_no - 1].strip()
            path.write_text(text.replace(m['old'], m['new']), encoding='utf-8')
            # Read the mutated file back: the evidence is the line as it now IS, not the line we meant to write.
            after = path.read_text(encoding='utf-8').splitlines()[line_no - 1].strip()
            applied.append(f"{m['file']}:{line_no} {m['old'].strip()!r} -> {after!r}")
            print(f"NC-EVIDENCE MUTATION {cid} applied: {m['file']}:{line_no}", flush=True)
            print(f"NC-EVIDENCE MUTATION {cid}   before: {before}", flush=True)
            print(f"NC-EVIDENCE MUTATION {cid}   after:  {after}", flush=True)
        # A mutation that changed nothing must fail LOUDLY, never become a green control that tests nothing
        # (the code control of #162 went stale exactly like that in a759a13).
        if _git(repo, 'diff', '--quiet', '--', *files).returncode == 0:
            print(f"NC-EVIDENCE MUTATION {cid} FAILED: git diff is empty, the mutation changed nothing", flush=True)
            return False, 'DID NOT RUN: the mutation changed nothing (git diff --quiet succeeded)'
        for line in _git(repo, 'diff', '-U0', '--', *files).stdout.splitlines():
            print(f"NC-EVIDENCE MUTATION {cid} diff: {line}", flush=True)
        report = tmp / 'report.xml'
        proc_env = {**os.environ, 'PYTHONPATH': str(repo), 'OMNI_EVIDENCE_NOTICES': ''}
        try:
            proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                                   f'--junitxml={report}', *spec['targets']],
                                  cwd=repo, env=proc_env, capture_output=True, text=True, timeout=1200)
        except subprocess.TimeoutExpired:
            return False, 'DID NOT RUN: pytest timed out'
        finally:
            # Restore and prove nothing leaks: tracked files back to baseline, status clean.
            _git(repo, 'checkout', '-q', '--', *files)
            status = _git(repo, 'status', '--porcelain', '--untracked-files=no').stdout.strip()
            print(f"NC-EVIDENCE restore {cid}: {'clean' if not status else 'DIRTY ' + status}", flush=True)
        if status:
            return False, f'restore not clean: {status}'
        if not report.exists():
            return False, f'DID NOT RUN: no pytest report (exit {proc.returncode}) {proc.stdout[-300:]}'
        cases = list(ET.parse(report).getroot().iter('testcase'))
        if not cases:
            return False, 'DID NOT RUN: no test was collected'
        failed = sorted({c.get('name') for c in cases
                         if c.find('failure') is not None or c.find('error') is not None})
        skipped = {c.get('name') for c in cases if c.find('skipped') is not None}
        env = ENV if nc_env is None else nc_env       # a name, never the process environment (2026-10-28 bug)
        if not isinstance(env, str):
            return False, 'DID NOT RUN: the environment name is not a string'
        expected = expected_for(spec, env)
        not_run = sorted(set(expected) & skipped)
        if not_run:
            return False, f'DID NOT RUN: expected tests were skipped {not_run} (ran={len(cases)})'
        ok, note = verdict(failed, expected, env)
        return ok, (f"mutation {'; '.join(applied)} | failed={failed} expected[{env or 'default'}]={expected} "
                    f"ran={len(cases)}" + note)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str]) -> int:
    prefix = argv[0] if argv else ''
    specs = sorted(p for p in SPECS.glob('*.json') if p.name.startswith(prefix))
    if not specs:
        notice('negative-controls', f'FAIL no spec matched {prefix!r} in {SPECS.relative_to(ROOT)}')
        return 1
    # GitHub shows at most 10 notices per step and keeps the FIRST ones (2026-10-28: the controls of pr162/pr170 were
    # cut). So each control's result is a plain log line, and every spec gets ONE ::notice summary after all its
    # controls ran -- one notice per spec, all of them visible. A FAIL is also an ::error with its full detail.
    all_ok = True
    for path in specs:
        spec = json.loads(path.read_text(encoding='utf-8'))
        digests = []
        for f in spec.get('sha256', []):
            digest = hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
            digests.append(f'{f} {digest[:16]}')
            print(f"NC-EVIDENCE {spec['pr']} sha256 {f} {digest}", flush=True)
        passed, failed = [], []
        for control in spec['controls']:
            ok, detail = run_control(control, control['id'])
            all_ok &= ok
            (passed if ok else failed).append(control['id'])
            print(f"NC-EVIDENCE RESULT {spec['pr']} {control['id']} {'PASS' if ok else 'FAIL'} "
                  f"{control['what']} -> {detail}", flush=True)
            if not ok:
                clean = ' '.join(f"{control['what']} -> {detail}".replace('%', '%25').split())
                print(f"::error title={spec['pr']} {control['id']} FAIL::{clean}"[:4000], flush=True)
        n = len(spec['controls'])
        verdict = 'PASS' if not failed else 'FAIL'
        notice(f"SPEC {spec['pr']}", f"{len(passed)}/{n} {verdict} (" + ' '.join(c['id'] for c in spec['controls'])
               + ')' + (f' failed={failed}' if failed else '') + (f" | sha256 {'; '.join(digests)}" if digests else ''))
    return 0 if all_ok else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
