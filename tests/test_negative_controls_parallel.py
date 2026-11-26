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

    def test_the_tests_of_a_control_do_not_see_the_runners_settings(self):
        (self.repo / 'test_env.py').write_text(textwrap.dedent('''
            import os, unittest
            from lib import gate
            class E(unittest.TestCase):
                def test_refuses(self): self.assertFalse(gate(-1))
                def test_plain_environment(self): self.assertNotIn('NC_JOBS', os.environ)
        '''))
        with mock.patch.dict(os.environ, {'NC_JOBS': '3', 'NC_ENV': ''}):
            nc = load()
            nc.ROOT = self.repo
            with redirect_stdout(io.StringIO()):
                ok, detail = nc.run_control({'mutations': [{'file': 'lib.py', 'old': 'return x > 0', 'new': 'return True'}],
                                             'targets': ['test_env.py'], 'expect_failed': ['test_refuses']})
        self.assertTrue(ok, detail)

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



class Shards(unittest.TestCase):
    """NC_SHARD (2026-11-26): v24-ci shares the controls among parallel jobs (run 45713038574 passed its 18-minute limit
    in one job). Every spec runs in exactly one shard, whole, and nothing is skipped."""

    def load_with(self, shard):
        with mock.patch.dict(os.environ, {'NC_SHARD': shard, 'NC_JOBS': '1', 'NC_ENV': ''}):
            return load()

    def test_every_spec_of_the_repository_is_in_exactly_one_shard(self):
        nc = self.load_with('')
        loaded = [(p, json.loads(p.read_text(encoding='utf-8')))
                  for p in sorted((ROOT / 'tests' / 'negative_controls').glob('*.json'))]
        work = [sum(1 for c in s['controls'] if not c.get('envs') or '' in c['envs']) for _p, s in loaded]
        self.assertEqual(work, [nc.work(s) for _p, s in loaded])        # v24-ci's controls: not the pg job's own
        for n in (1, 2, 3, 4):
            with self.subTest(shards=n):
                parts = nc.shards(loaded, n)
                self.assertEqual(sorted(i for part in parts for i in part), list(range(len(loaded))))
                sizes = [sum(work[i] for i in part) for part in parts]
                self.assertLessEqual(max(sizes) - min(sizes), max(work))
        self.assertEqual(nc.shards(loaded, 3), nc.shards(list(loaded), 3))          # the same specs, the same shards

    def test_a_shard_runs_only_its_specs_and_together_they_run_all(self):
        repo = pathlib.Path(tempfile.mkdtemp())
        (repo / 'lib.py').write_text('def gate(x):\n    return x > 0\n')
        (repo / 'test_lib.py').write_text('import unittest\nfrom lib import gate\n'
                                          'class T(unittest.TestCase):\n'
                                          '    def test_refuses(self): self.assertFalse(gate(-1))\n')
        specs = repo / 'tests' / 'negative_controls'
        specs.mkdir(parents=True)
        for name in ('a', 'b', 'c', 'd', 'e'):
            (specs / f'{name}.json').write_text(json.dumps({'pr': name, 'controls': [
                {'id': 'NC1', 'what': name, 'mutations': [{'file': 'lib.py', 'old': 'return x > 0', 'new': 'return True'}],
                 'targets': ['test_lib.py'], 'expect_failed': ['test_refuses']}]}))
        ran = []
        for i in (1, 2, 3):
            nc = self.load_with(f'{i}/3')
            nc.ROOT, nc.SPECS = repo, specs
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(nc.main([]), 0)
            out = buf.getvalue()
            self.assertIn(f'title=negative-controls shard {i}/3::', out)
            ran += [l.split('title=SPEC ')[1].split('::')[0] for l in out.splitlines() if 'title=SPEC' in l]
        self.assertEqual(sorted(ran), ['a', 'b', 'c', 'd', 'e'])               # each spec once, none skipped

    def test_an_empty_shard_fails_loudly(self):
        repo = pathlib.Path(tempfile.mkdtemp())
        specs = repo / 'tests' / 'negative_controls'
        specs.mkdir(parents=True)
        (specs / 'only.json').write_text(json.dumps({'pr': 'only', 'controls': []}))
        nc = self.load_with('2/2')
        nc.ROOT, nc.SPECS = repo, specs
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(nc.main([]), 1)
        self.assertIn('holds no spec', buf.getvalue())

    def test_a_shard_must_be_i_of_n(self):
        for bad in ('0/3', '4/3', '3', 'one/3', '1/0'):
            with self.subTest(shard=bad):
                with self.assertRaises(ValueError):
                    self.load_with(bad)
        self.assertIsNone(self.load_with('').SHARD)
        self.assertEqual(self.load_with('2/3').SHARD, (2, 3))
        self.assertIn('NC_SHARD', self.load_with('').RUNNER_SETTINGS)     # never reaches the tests a control runs

    def test_ci_runs_every_shard(self):
        import yaml
        job = yaml.safe_load((ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8'))['jobs'][
            'negative-controls']
        shards = job['strategy']['matrix']['shard']
        self.assertFalse(job['strategy']['fail-fast'])                  # one red shard does not cancel the others
        # the review of 2026-11-26: an `exclude` of a shard, or a condition on the step, drops a shard silently
        self.assertEqual(set(job['strategy']), {'fail-fast', 'matrix'})
        self.assertEqual(set(job['strategy']['matrix']), {'shard'})      # no exclude, no include
        [step] = [s for s in job['steps'] if 'run_negative_controls.py' in s.get('run', '')]
        self.assertEqual(step['run'], 'python scripts/run_negative_controls.py')
        self.assertEqual(step['env']['NC_SHARD'], '${{ matrix.shard }}/' + str(len(shards)))
        self.assertEqual(shards, list(range(1, len(shards) + 1)))       # 1..n: no shard is missing
        for where in (step, job):
            self.assertNotIn('if', where)                               # no shard's controls are skipped
            self.assertNotIn('continue-on-error', where)


if __name__ == '__main__':
    unittest.main()
