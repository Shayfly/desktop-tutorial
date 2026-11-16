"""Warehouse 112 (owner 2026-11-16): no test file falls outside CI. Runs in ci-fast (test_ci_*). The real repository is
checked as it is (test_the_repository_is_covered), and a copy of it shows the check catches a new PostgreSQL file that no
job runs -- the exact way tests/test_company_loss_failed_build_pg.py went unrun (#404)."""
from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_VAR = 'M4D2_' + 'DATABASE_URL'   # split: this file itself must not read as needing PostgreSQL
spec = importlib.util.spec_from_file_location('ci_test_coverage', ROOT / 'scripts' / 'ci_test_coverage.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def copy():
    tmp = Path(tempfile.mkdtemp())
    (tmp / '.github' / 'workflows').mkdir(parents=True)
    for name in ('intake-budget-pg.yml', 'v24-ci.yml'):
        shutil.copy(ROOT / '.github' / 'workflows' / name, tmp / '.github' / 'workflows' / name)
    shutil.copytree(ROOT / 'tests', tmp / 'tests', ignore=shutil.ignore_patterns('__pycache__'))
    return tmp


class TheRepositoryIsCovered(unittest.TestCase):
    def test_the_repository_is_covered(self):
        self.assertEqual(C.problems(), [])


class TheCheckCatches(unittest.TestCase):
    def setUp(self):
        self.root = copy()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_new_postgres_file_no_job_runs_fails(self):
        (self.root / 'tests' / 'test_new_ledger_pg.py').write_text('import unittest\n')
        self.assertEqual(len(C.problems(self.root)), 1)
        self.assertIn('tests/test_new_ledger_pg.py needs PostgreSQL', C.problems(self.root)[0])

    def test_a_file_that_reads_the_database_variable_counts_too(self):
        (self.root / 'tests' / 'test_new_thing.py').write_text("import os\nURL = os.getenv('" + DB_VAR + "')\n")
        self.assertIn('tests/test_new_thing.py needs PostgreSQL', ' '.join(C.problems(self.root)))

    def test_a_named_gap_with_a_reason_is_accepted_and_without_one_raises(self):
        (self.root / 'tests' / 'test_new_ledger_pg.py').write_text('import unittest\n')
        nyr = self.root / 'tests' / 'pg_not_yet_run.txt'
        kept = nyr.read_text()                       # the repository's own waivers stay; the new line is added
        nyr.write_text(kept + 'tests/test_new_ledger_pg.py  # needs a fixture table not in the migrations yet\n')
        self.assertEqual(C.problems(self.root), [])
        nyr.write_text(kept + 'tests/test_new_ledger_pg.py\n')
        with self.assertRaises(ValueError):
            C.problems(self.root)

    def test_the_general_job_must_collect_everything(self):
        wf = self.root / '.github' / 'workflows' / 'v24-ci.yml'
        wf.write_text(wf.read_text().replace(C.GENERAL_RUN, 'python -m pytest -q tests/test_auth.py'))
        self.assertIn('general coverage is unknown', ' '.join(C.problems(self.root)))


if __name__ == '__main__':
    unittest.main()
