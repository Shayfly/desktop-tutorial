"""NC_SCOPE (2026-11-22): the pg job's negative-controls step ran every spec again after v24-ci had run them all, and
ran out of its 14-minute limit on #499 with every control PASS (the job may not exceed 20 minutes). With
NC_SCOPE=declared it runs only the controls a real database changes; v24-ci keeps NC_SCOPE unset (all). Tested on a
tiny fake repository, as tests/test_negative_controls_parallel.py does."""
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

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(**env):
    with mock.patch.dict(os.environ, env, clear=False):
        spec = importlib.util.spec_from_file_location('nc_scope', ROOT / 'scripts' / 'run_negative_controls.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class TheScope(unittest.TestCase):
    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp())
        (self.repo / 'lib.py').write_text('def gate(x):\n    return x > 0\n')
        test = textwrap.dedent('''
            import unittest
            from lib import gate
            class T(unittest.TestCase):
                def test_refuses(self): self.assertFalse(gate(-1))
        ''')
        (self.repo / 'test_plain.py').write_text(test)
        db_var = 'M4D2_' + 'DATABASE_URL'     # split, as in test_ci_test_coverage.py: this file connects to no database
        (self.repo / 'test_reaches_db.py').write_text(f"import os\nURL = os.getenv('{db_var}')\n" + test)
        specs = self.repo / 'tests' / 'negative_controls'
        specs.mkdir(parents=True)
        mut = [{'file': 'lib.py', 'old': 'return x > 0', 'new': 'return True'}]
        controls = [
            {'id': 'NC1', 'what': 'plain', 'mutations': mut, 'targets': ['test_plain.py'], 'expect_failed': ['test_refuses']},
            {'id': 'NC2', 'what': 'envs pg', 'envs': ['pg'], 'mutations': mut, 'targets': ['test_plain.py'],
             'expect_failed': ['test_refuses']},
            {'id': 'NC3', 'what': 'its own pg expectation', 'mutations': mut, 'targets': ['test_plain.py'],
             'expect_failed': ['test_refuses'], 'expect_failed_pg': ['test_refuses']},
            {'id': 'NC4', 'what': 'a target that reaches a database', 'mutations': mut, 'targets': ['test_reaches_db.py'],
             'expect_failed': ['test_refuses']},
            {'id': 'NC5', 'what': 'a pg-named target', 'mutations': mut, 'targets': ['test_x_pg.py'],
             'expect_failed': ['test_refuses']},
        ]
        (self.repo / 'test_x_pg.py').write_text(test)
        (specs / 'a.json').write_text(json.dumps({'pr': 'a', 'controls': controls}))

    def spec_line(self, **env):
        nc = load(NC_JOBS='1', **env)
        nc.ROOT, nc.SPECS = self.repo, self.repo / 'tests' / 'negative_controls'
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = nc.main([])
        return code, next(l for l in buf.getvalue().splitlines() if 'title=SPEC a' in l)

    def test_declared_in_the_pg_job_runs_only_what_a_database_changes(self):
        code, line = self.spec_line(NC_ENV='pg', NC_SCOPE='declared')
        self.assertEqual(code, 0, line)
        self.assertIn('4/4 PASS (NC2 NC3 NC4 NC5)', line)
        self.assertIn('not run here: NC1 (runs in v24-ci)', line)

    def test_the_default_runs_everything_as_before(self):
        for env in ({'NC_ENV': 'pg'}, {'NC_ENV': ''}):
            with self.subTest(env):
                code, line = self.spec_line(**env)
                n = '5/5' if env['NC_ENV'] == 'pg' else '4/4'      # NC2 is pg only
                self.assertIn(f'{n} PASS', line)

    def test_an_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            load(NC_SCOPE='some')

    def test_the_pg_job_declares_the_scope_and_v24_ci_does_not(self):
        def nc_step(name):
            d = yaml.safe_load((ROOT / '.github' / 'workflows' / name).read_text(encoding='utf-8'))
            return next(s for j in d['jobs'].values() for s in j.get('steps', [])
                        if s.get('run') == 'python scripts/run_negative_controls.py')
        self.assertEqual(nc_step('intake-budget-pg.yml')['env']['NC_SCOPE'], 'declared')
        self.assertNotIn('NC_SCOPE', nc_step('v24-ci.yml').get('env') or {})


if __name__ == '__main__':
    unittest.main()
