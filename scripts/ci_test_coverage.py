"""Warehouse 112 (owner 2026-11-16): CI blindness. Every test file must be run by a CI job; a test file that needs
PostgreSQL must be run by the one job that has it (intake-budget-pg), or be named in tests/pg_not_yet_run.txt with the
reason. Found: tests/test_company_loss_failed_build_pg.py was never run anywhere (#404), and 16 more such files.

A file needs PostgreSQL when its name ends in _pg.py or it reads M4D2_DATABASE_URL. The general job (v24-ci `test`)
runs `python -m pytest -q` with no paths, so it collects every tests/**/test_*.py; this script checks that too.

  python scripts/ci_test_coverage.py        # exit 1 and one ::error per uncovered file
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PG_JOB = ROOT / '.github' / 'workflows' / 'intake-budget-pg.yml'
GENERAL_JOB = ROOT / '.github' / 'workflows' / 'v24-ci.yml'
NOT_YET = ROOT / 'tests' / 'pg_not_yet_run.txt'
GENERAL_RUN = 'python -m pytest -q --junitxml=pytest-report.xml'


def needs_pg(path: Path) -> bool:
    return path.name.endswith('_pg.py') or 'M4D2_DATABASE_URL' in path.read_text(encoding='utf-8', errors='replace')


def pg_listed(job_text: str) -> set[str]:
    return {m.split('::')[0] for m in re.findall(r'tests/[\w/]+\.py(?:::[\w:\[\]-]+)?', job_text)}


def not_yet(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        path, _, reason = line.partition('#')
        if not reason.strip():
            raise ValueError(f'{NOT_YET.name}: {path.strip()} has no reason')
        out[path.strip()] = reason.strip()
    return out


def problems(root: Path = ROOT) -> list[str]:
    out = []
    general = (root / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8')
    if GENERAL_RUN not in general:
        out.append(f'v24-ci no longer runs "{GENERAL_RUN}" (all tests, no paths): the general coverage is unknown')
    listed = pg_listed((root / '.github' / 'workflows' / 'intake-budget-pg.yml').read_text(encoding='utf-8'))
    nyr_file = root / 'tests' / 'pg_not_yet_run.txt'
    waived = not_yet(nyr_file.read_text(encoding='utf-8')) if nyr_file.exists() else {}
    files = sorted(str(p.relative_to(root)) for p in (root / 'tests').rglob('test_*.py'))
    for f in files:
        if needs_pg(root / f) and f not in listed and f not in waived:
            out.append(f'{f} needs PostgreSQL but no job runs it: add it to intake-budget-pg.yml, '
                       f'or to tests/pg_not_yet_run.txt with the reason')
    for f in listed:
        if not (root / f).exists():
            out.append(f'intake-budget-pg.yml lists {f}, which does not exist')
    for f in waived:
        if f in listed:
            out.append(f'{f} is both run by intake-budget-pg and listed as not yet run: remove it from the list')
        if not (root / f).exists():
            out.append(f'tests/pg_not_yet_run.txt names {f}, which does not exist')
    return out


def main() -> int:
    found = problems()
    for p in found:
        print(f'::error title=CI test coverage::{p}')
    print(f'::notice title=CI test coverage::{"FAIL" if found else "PASS"} ({len(found)} problem(s))')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
