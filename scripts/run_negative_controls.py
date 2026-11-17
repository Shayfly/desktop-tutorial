"""Negative controls in CI, readable without log access (2026-10-27).

Every tests/negative_controls/*.json spec names a deliberate breakage (exact text replaced once in a file) and the
EXACT set of tests that must fail because of it. For each control this copies the repository to a temp dir, applies
the mutation, runs pytest on the targets, and prints one ::notice with PASS|FAIL and the NAMES of the tests that
failed. A control that did not run -- mutation not applied, nothing collected, pytest crashed, an expected test
skipped -- is FAIL, never a silent pass. The sha256 of each spec's evidence files is printed as a ::notice too.
Exit 1 when any control FAILs.

  python scripts/run_negative_controls.py            # every spec
  python scripts/run_negative_controls.py pr154      # specs whose file name starts with pr154

Parallel (2026-11-17): NC_JOBS=N runs N controls at once; each control's lines are buffered and printed in the same
order and format as a serial run. The pg job's step had been raised 5 -> 10 -> 14 minutes in two days and still ran
over (main: 8:56 to 11:37; a branch with one more spec: over 14). The owner's rule is to investigate, not to raise a
limit again: the time is 574 pytest starts in a row on a 4-core runner. On a real database (NC_ENV=pg) every worker
gets its own copy of the migrated database (CREATE DATABASE ... TEMPLATE, from NC_DB_URL) and its own Redis database
index (from NC_REDIS_URL): a test that empties build_jobs in one control never touches another control's data.
NC_JOBS=1 (the default) is the serial run, unchanged.
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
JOBS = int(os.getenv('NC_JOBS') or '1')        # not a number -> ValueError at start, never a silent default
RUNNER_SETTINGS = ('NC_JOBS', 'NC_DB_URL', 'NC_REDIS_URL')
if JOBS < 1:
    raise ValueError(f'NC_JOBS must be at least 1, not {JOBS}')


def _with_path(url: str, path: str) -> str:
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, '/' + path, parts.query, parts.fragment))


def slot_env(slot: int, environ=None) -> dict:
    """The environment of one parallel worker: every variable that holds the job's database URL points at the
    worker's own database (nc_<slot>), every one that holds the job's Redis URL at its own index (slot + 1; 0 stays
    the job's). Only exact values are replaced; nothing else changes."""
    environ = os.environ if environ is None else environ
    extra = {}
    db, redis = (environ.get('NC_DB_URL') or '').strip(), (environ.get('NC_REDIS_URL') or '').strip()
    for source, target in ((db, _with_path(db, f'nc_{slot}') if db else ''),
                           (redis, _with_path(redis, str(slot + 1)) if redis else '')):
        if source:
            extra.update({k: target for k, v in environ.items() if v == source and k not in ('NC_DB_URL', 'NC_REDIS_URL')})
    return extra


def prepare_databases(jobs: int) -> None:
    """One copy of the migrated job database per worker. Loud on any failure: a shared database is never assumed."""
    db = (os.getenv('NC_DB_URL') or '').strip()
    if not db:
        raise SystemExit('NC_JOBS > 1 on a real database (NC_ENV=pg) needs NC_DB_URL: one database per worker')
    import psycopg
    from urllib.parse import urlsplit
    source = urlsplit(db).path.lstrip('/')
    import time
    with psycopg.connect(_with_path(db, 'template1'), autocommit=True) as conn:
        for slot in range(jobs):
            conn.execute(f'DROP DATABASE IF EXISTS nc_{slot}')
            for attempt in range(1, 6):          # a template cannot be copied while a session is on it: bounded
                try:
                    conn.execute(f'CREATE DATABASE nc_{slot} TEMPLATE "{source}"')
                    break
                except psycopg.errors.ObjectInUse:
                    if attempt == 5:
                        raise
                    print(f'NC-EVIDENCE databases: {source} is in use, copy {slot} retried ({attempt}/5)', flush=True)
                    time.sleep(2)
    print(f'NC-EVIDENCE databases: {jobs} copies of {source} (nc_0..nc_{jobs - 1})', flush=True)


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


def run_control(spec: dict, cid: str = 'NC', nc_env: str | None = None, out=None, env_extra=None) -> tuple[bool, str]:
    out = out or (lambda line: print(line, flush=True))
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
            out(f"NC-EVIDENCE MUTATION {cid} applied: {m['file']}:{line_no}")
            out(f"NC-EVIDENCE MUTATION {cid}   before: {before}")
            out(f"NC-EVIDENCE MUTATION {cid}   after:  {after}")
        # A mutation that changed nothing must fail LOUDLY, never become a green control that tests nothing
        # (the code control of #162 went stale exactly like that in a759a13).
        if _git(repo, 'diff', '--quiet', '--', *files).returncode == 0:
            out(f"NC-EVIDENCE MUTATION {cid} FAILED: git diff is empty, the mutation changed nothing")
            return False, 'DID NOT RUN: the mutation changed nothing (git diff --quiet succeeded)'
        for line in _git(repo, 'diff', '-U0', '--', *files).stdout.splitlines():
            out(f"NC-EVIDENCE MUTATION {cid} diff: {line}")
        report = tmp / 'report.xml'
        proc_env = {**os.environ, **(env_extra or {}), 'PYTHONPATH': str(repo), 'OMNI_EVIDENCE_NOTICES': ''}
        for key in RUNNER_SETTINGS:           # the runner's own settings never reach the tests it runs: a test of the
            proc_env.pop(key, None)           # runner itself must see a plain environment
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
            out(f"NC-EVIDENCE restore {cid}: {'clean' if not status else 'DIRTY ' + status}")
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
        if not ok:   # 2026-11-15 (#393): an unexpected failure is shown with its own assertion, not only its name
            for c in cases:
                f = c.find('failure') if c.find('failure') is not None else c.find('error')
                if f is not None and c.get('name') not in expected:
                    detail = ' '.join(((f.get('message') or '') + ' ' + (f.text or '')[-600:]).split())[:900]
                    out(f"NC-EVIDENCE UNEXPECTED {cid} {c.get('name')}: {detail}")
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
    loaded = [(path, json.loads(path.read_text(encoding='utf-8'))) for path in specs]
    results = {}                                      # (spec index, control index) -> future of (ok, detail, lines)
    pool = None
    if JOBS > 1:
        import queue
        from concurrent.futures import ThreadPoolExecutor
        if ENV == 'pg':
            prepare_databases(JOBS)
        slots = queue.Queue()
        for slot in range(JOBS):
            slots.put(slot)

        def job(control):
            slot, lines = slots.get(), []
            try:
                ok, detail = run_control(control, control['id'], out=lines.append,
                                         env_extra=slot_env(slot) if ENV == 'pg' else None)
            finally:
                slots.put(slot)
            return ok, detail, lines
        pool = ThreadPoolExecutor(max_workers=JOBS)
        for si, (_, spec) in enumerate(loaded):
            for ci, c in enumerate(spec['controls']):
                if not c.get('envs') or ENV in c['envs']:
                    results[(si, ci)] = pool.submit(job, c)
    for si, (path, spec) in enumerate(loaded):
        digests = []
        for f in spec.get('sha256', []):
            digest = hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
            digests.append(f'{f} {digest[:16]}')
            print(f"NC-EVIDENCE {spec['pr']} sha256 {f} {digest}", flush=True)
        passed, failed, infos, elsewhere = [], [], [], []
        here = [c for c in spec['controls'] if not c.get('envs') or ENV in c['envs']]
        for c in spec['controls']:
            if c not in here:                 # e.g. a real-Postgres race: said in the SPEC line, never silently dropped
                elsewhere.append(f"{c['id']} ({'/'.join(c['envs'])} only)")
        for control in here:
            if pool is None:
                ok, detail = run_control(control, control['id'])
            else:                             # the lines of this control, in order, after it finished
                ok, detail, lines = results[(si, spec['controls'].index(control))].result()
                for line in lines:
                    print(line, flush=True)
            all_ok &= ok
            (passed if ok else failed).append(control['id'])
            if ok and ' INFO ' in detail:                     # an extra failure in pg: in the SPEC line, not buried
                infos.append(control['id'] + ' ' + detail.split(' INFO ', 1)[1])
            print(f"NC-EVIDENCE RESULT {spec['pr']} {control['id']} {'PASS' if ok else 'FAIL'} "
                  f"{control['what']} -> {detail}", flush=True)
            if not ok:
                clean = ' '.join(f"{control['what']} -> {detail}".replace('%', '%25').split())
                print(f"::error title={spec['pr']} {control['id']} FAIL::{clean}"[:4000], flush=True)
        n = len(here)
        verdict = 'PASS' if not failed and here else 'FAIL'
        if not here and elsewhere:            # every control runs in another job: said, never shown as a failure
            verdict = 'NOT RUN HERE'
        notice(f"SPEC {spec['pr']}", f"{len(passed)}/{n} {verdict} (" + ' '.join(c['id'] for c in here)
               + ')' + (f' failed={failed}' if failed else '') + (f" | INFO {'; '.join(infos)}" if infos else '')
               + (f" | not run here: {', '.join(elsewhere)}" if elsewhere else '')
               + (f" | sha256 {'; '.join(digests)}" if digests else ''))
    if pool is not None:
        pool.shutdown()
    return 0 if all_ok else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
