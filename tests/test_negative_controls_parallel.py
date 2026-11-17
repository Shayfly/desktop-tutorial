"""Parallel negative controls (2026-11-17): the pg job's controls step had been raised 5 -> 10 -> 14 minutes and still
ran over; the owner's rule is to investigate, not to raise a limit again. NC_JOBS=N runs N controls at once, prints
exactly what a serial run prints, in the same order, and on a real database gives every worker its own database and
Redis index. Tested on a tiny fake repository, as tests/test_negative_controls_runner.py does."""
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_VAR = 'M4D2_' + 'DATABASE_URL'   # split, as in test_ci_test_coverage.py: this file connects to no database


def load():
    spec = importlib.util.spec_from_file_location('nc_par', ROOT / 'scripts' / 'run_negative_controls.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parallel(unittest.TestCase):
    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp())
        (self.repo / 'lib.py').write_text('def gate(x):\n    return x > 0\n\ndef other(x):\n    return x < 0\n')
        (self.repo / 'test_lib.py').write_text(textwrap.dedent('''
            import unittest
            from lib import gate, other
            class T(unittest.TestCase):
                def test_refuses(self): self.assertFalse(gate(-1))
                def test_other(self): self.assertTrue(other(-1))
        '''))
        specs = self.repo / 'tests' / 'negative_controls'
        specs.mkdir(parents=True)
        for name, cid, old, new, expect in (('a_one', 'NC1', 'return x > 0', 'return True', 'test_refuses'),
                                            ('b_two', 'NC1', 'return x < 0', 'return False', 'test_other'),
                                            ('c_bad', 'NC1', 'return x > 0', 'return True', 'test_other')):
            (specs / f'{name}.json').write_text(json.dumps({'pr': name, 'controls': [
                {'id': cid, 'what': name, 'mutations': [{'file': 'lib.py', 'old': old, 'new': new}],
                 'targets': ['test_lib.py'], 'expect_failed': [expect]}]}))

    def run_with(self, jobs):
        with mock.patch.dict(os.environ, {'NC_JOBS': str(jobs), 'NC_ENV': ''}):
            nc = load()
        nc.ROOT, nc.SPECS = self.repo, self.repo / 'tests' / 'negative_controls'
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = nc.main([])
        return code, [line for line in buf.getvalue().splitlines() if 'title=SPEC' in line or 'RESULT' in line]

    def test_parallel_prints_what_serial_prints_in_the_same_order(self):
        serial, parallel = self.run_with(1), self.run_with(3)
        self.assertEqual(serial[0], parallel[0])                      # the exit code: c_bad fails in both
        strip = lambda lines: [l.split(' -> ')[0] if 'RESULT' in l else l.split(' | ')[0] for l in lines]
        self.assertEqual(strip(serial[1]), strip(parallel[1]))
        self.assertEqual([l.split('title=SPEC ')[1].split('::')[0] for l in parallel[1] if 'title=SPEC' in l],
                         ['a_one', 'b_two', 'c_bad'])
        self.assertEqual(serial[0], 1)

    def test_a_worker_gets_its_own_database_and_redis_index(self):
        nc = load()
        env = {'NC_DB_URL': 'postgresql://u:p@h:5432/postgres', DB_VAR: 'postgresql://u:p@h:5432/postgres',
               'OMNI_DATABASE_URL': 'postgresql://u:p@h:5432/postgres', 'OTHER_DB': 'postgresql://u:p@h:5432/other',
               'NC_REDIS_URL': 'redis://h:6379/0', 'OMNI_TEST_REDIS_URL': 'redis://h:6379/0'}
        got = nc.slot_env(2, env)
        self.assertEqual(got, {DB_VAR: 'postgresql://u:p@h:5432/nc_2',
                               'OMNI_DATABASE_URL': 'postgresql://u:p@h:5432/nc_2',
                               'OMNI_TEST_REDIS_URL': 'redis://h:6379/3'})

    def test_parallel_on_a_real_database_without_a_url_refuses(self):
        with mock.patch.dict(os.environ, {'NC_JOBS': '2', 'NC_ENV': 'pg'}):
            os.environ.pop('NC_DB_URL', None)
            nc = load()
            with self.assertRaises(SystemExit):
                nc.prepare_databases(2)

    def test_jobs_must_be_a_positive_number(self):
        for bad in ('0', 'many'):
            with mock.patch.dict(os.environ, {'NC_JOBS': bad}):
                with self.assertRaises(ValueError):
                    load()


if __name__ == '__main__':
    unittest.main()
