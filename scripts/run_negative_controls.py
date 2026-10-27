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


def run_control(spec: dict) -> tuple[bool, str]:
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='nc-'))
    try:
        repo = tmp / 'repo'
        shutil.copytree(ROOT, repo, ignore=IGNORE)
        for m in spec['mutations']:
            path = repo / m['file']
            text = path.read_text(encoding='utf-8')
            found = text.count(m['old'])
            if found != 1:
                return False, f"DID NOT RUN: mutation not applied ({m['file']}: target text found {found} times, need 1)"
            path.write_text(text.replace(m['old'], m['new']), encoding='utf-8')
        report = tmp / 'report.xml'
        env = {**os.environ, 'PYTHONPATH': str(repo), 'OMNI_EVIDENCE_NOTICES': ''}
        try:
            proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                                   f'--junitxml={report}', *spec['targets']],
                                  cwd=repo, env=env, capture_output=True, text=True, timeout=1200)
        except subprocess.TimeoutExpired:
            return False, 'DID NOT RUN: pytest timed out'
        if not report.exists():
            return False, f'DID NOT RUN: no pytest report (exit {proc.returncode}) {proc.stdout[-300:]}'
        cases = list(ET.parse(report).getroot().iter('testcase'))
        if not cases:
            return False, 'DID NOT RUN: no test was collected'
        failed = sorted({c.get('name') for c in cases
                         if c.find('failure') is not None or c.find('error') is not None})
        skipped = {c.get('name') for c in cases if c.find('skipped') is not None}
        expected = sorted(spec['expect_failed'])
        not_run = sorted(set(expected) & skipped)
        if not_run:
            return False, f'DID NOT RUN: expected tests were skipped {not_run} (ran={len(cases)})'
        ok = failed == expected
        return ok, f'failed={failed} expected={expected} ran={len(cases)}'
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str]) -> int:
    prefix = argv[0] if argv else ''
    specs = sorted(p for p in SPECS.glob('*.json') if p.name.startswith(prefix))
    if not specs:
        notice('negative-controls', f'FAIL no spec matched {prefix!r} in {SPECS.relative_to(ROOT)}')
        return 1
    all_ok = True
    for path in specs:
        spec = json.loads(path.read_text(encoding='utf-8'))
        for f in spec.get('sha256', []):
            digest = hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
            notice(f"{spec['pr']} sha256", f'{f} {digest}')
        for control in spec['controls']:
            ok, detail = run_control(control)
            all_ok &= ok
            notice(f"{spec['pr']} {control['id']}", f"{'PASS' if ok else 'FAIL'} {control['what']} -> {detail}")
    return 0 if all_ok else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
