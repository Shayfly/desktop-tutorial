"""scripts/run_negative_controls.py on a tiny fake repository: PASS only on the exact expected failures; every way
of not running (mutation not applied, nothing collected, expected test skipped) is FAIL, never a silent pass."""
import importlib.util
import io
from contextlib import redirect_stdout
import pathlib
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('nc', ROOT / 'scripts' / 'run_negative_controls.py')
nc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nc)


class Runner(unittest.TestCase):
    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp())
        (self.repo / 'lib.py').write_text('def gate(x):\n    return x > 0\n')
        (self.repo / 'test_lib.py').write_text(textwrap.dedent('''
            import unittest
            from lib import gate
            class T(unittest.TestCase):
                def test_refuses(self): self.assertFalse(gate(-1))
                def test_accepts(self): self.assertTrue(gate(1))
                @unittest.skip('not here')
                def test_skipped(self): pass
        '''))
        self.old_root, nc.ROOT = nc.ROOT, self.repo

    def tearDown(self):
        nc.ROOT = self.old_root

    def control(self, old='return x > 0', new='return True', expect=('test_refuses',), targets=('test_lib.py',)):
        return nc.run_control({'mutations': [{'file': 'lib.py', 'old': old, 'new': new}],
                               'targets': list(targets), 'expect_failed': list(expect)})

    def test_exact_expected_failures_pass(self):
        ok, detail = self.control()
        self.assertTrue(ok, detail)
        self.assertIn("failed=['test_refuses']", detail)

    def test_the_applied_line_is_read_back_and_reported(self):
        ok, detail = self.control()
        self.assertIn("mutation lib.py:2 'return x > 0' -> 'return True'", detail)   # file:line, old -> line as it now is

    def test_a_mutation_that_changes_nothing_fails_loudly(self):
        """The stale-control failure of a759a13: the target exists but the replacement is identical -> no diff."""
        out = io.StringIO()
        with redirect_stdout(out):
            ok, detail = self.control(new='return x > 0')
        self.assertFalse(ok)
        self.assertIn('the mutation changed nothing', detail)
        self.assertIn('NC-EVIDENCE MUTATION NC FAILED: git diff is empty', out.getvalue())

    def test_log_shows_mutation_diff_and_clean_restore(self):
        out = io.StringIO()
        with redirect_stdout(out):
            ok, _ = self.control()
        log = out.getvalue()
        self.assertTrue(ok)
        self.assertIn('NC-EVIDENCE MUTATION NC applied: lib.py:2', log)
        self.assertIn('NC-EVIDENCE MUTATION NC   before: return x > 0', log)
        self.assertIn('NC-EVIDENCE MUTATION NC   after:  return True', log)
        self.assertIn('NC-EVIDENCE MUTATION NC diff: -    return x > 0', log)
        self.assertIn('NC-EVIDENCE MUTATION NC diff: +    return True', log)
        self.assertIn('NC-EVIDENCE restore NC: clean', log)

    def test_different_failures_fail(self):
        self.assertFalse(self.control(expect=('test_refuses', 'test_accepts'))[0])

    def test_mutation_not_applied_is_fail_did_not_run(self):
        ok, detail = self.control(old='no such text')
        self.assertFalse(ok)
        self.assertIn('DID NOT RUN: mutation not applied', detail)

    def test_nothing_collected_is_fail(self):
        ok, detail = self.control(targets=('test_lib.py::T::nope',))
        self.assertFalse(ok)
        self.assertIn('DID NOT RUN', detail)

    def test_expected_test_skipped_is_fail(self):
        ok, detail = self.control(expect=('test_refuses', 'test_skipped'))
        self.assertFalse(ok)
        self.assertIn('expected tests were skipped', detail)

    def test_the_real_repository_is_never_mutated(self):
        self.control()
        self.assertIn('return x > 0', (self.repo / 'lib.py').read_text())


class OneSummaryNoticePerSpec(unittest.TestCase):
    """GitHub shows at most 10 notices per step and keeps the first ones: with one notice per control the controls of
    the later specs were cut (2026-10-28). Each spec now prints ONE summary notice after all its controls ran."""

    def test_one_notice_per_spec_after_its_controls_and_an_error_for_a_fail(self):
        import json
        from unittest import mock
        d = pathlib.Path(tempfile.mkdtemp())
        for name, ids in (('a_first.json', ('NC1', 'NC2')), ('b_second.json', ('NC1', 'NC2', 'NC3', 'NC4'))):
            (d / name).write_text(json.dumps({'pr': name.split('.')[0], 'controls': [
                {'id': i, 'what': f'w{i}', 'mutations': [], 'targets': [], 'expect_failed': []} for i in ids]}))
        results = iter([(True, 'x'), (True, 'x'), (True, 'x'), (False, 'boom'), (True, 'x'), (True, 'x')])
        out = io.StringIO()
        with mock.patch.object(nc, 'SPECS', d), mock.patch.object(nc, 'run_control', lambda c, cid: next(results)), \
                redirect_stdout(out):
            code = nc.main([])
        lines = out.getvalue().splitlines()
        notices = [l for l in lines if l.startswith('::notice')]
        self.assertEqual(notices, ['::notice title=SPEC a_first::2/2 PASS (NC1 NC2)',
                                   "::notice title=SPEC b_second::3/4 FAIL (NC1 NC2 NC3 NC4) failed=['NC2']"])
        self.assertEqual(code, 1)
        self.assertTrue(any(l.startswith('::error title=b_second NC2 FAIL::') and 'boom' in l for l in lines))
        self.assertIn('NC-EVIDENCE RESULT b_second NC4 PASS wNC4 -> x', lines)
        # the summary comes after every control of its spec
        self.assertGreater(lines.index(notices[1]), lines.index('NC-EVIDENCE RESULT b_second NC4 PASS wNC4 -> x'))


class PerEnvironmentExpectations(unittest.TestCase):
    """2026-10-28: in pg the real-store tests also run, so a mutation breaks more than v24-ci sees."""

    def test_each_environment_compares_with_its_own_set(self):
        spec = {'expect_failed': ['a'], 'expect_failed_pg': ['a', 'real_store']}
        self.assertEqual(nc.expected_for(spec, ''), ['a'])
        self.assertEqual(nc.expected_for(spec, 'pg'), ['a', 'real_store'])
        self.assertEqual(nc.expected_for({'expect_failed': ['a']}, 'pg'), ['a'])     # no pg set: the default

    def test_an_expected_test_that_did_not_fail_is_a_fail_everywhere(self):
        for env in ('', 'pg'):
            ok, note = nc.verdict(['a'], ['a', 'b'], env)
            self.assertFalse(ok, env)
            self.assertIn("missing=['b']", note)

    def test_an_extra_failure_is_info_only_in_pg(self):
        ok, note = nc.verdict(['a', 'x'], ['a'], 'pg')
        self.assertTrue(ok)
        self.assertIn("INFO extra failures in pg: ['x']", note)
        ok, note = nc.verdict(['a', 'x'], ['a'], '')
        self.assertFalse(ok)
        self.assertIn("extra=['x']", note)


class TheDetailNeverCarriesTheProcessEnvironment(unittest.TestCase):
    """2026-10-28: `env` was both the environment NAME and the subprocess environment dict, so the dict reached the
    annotation text (a public repo). The detail must name the environment only."""

    def test_the_runner_keeps_the_two_apart(self):
        import inspect
        src = inspect.getsource(nc.run_control)
        self.assertIn('proc_env = {**os.environ', src)
        self.assertNotIn('env = {**os.environ', src.replace('proc_env = {**os.environ', ''))


class TheInfoIsInTheSpecLine(unittest.TestCase):
    def test_an_extra_failure_in_pg_appears_in_the_summary_notice(self):
        import json
        from unittest import mock
        d = pathlib.Path(tempfile.mkdtemp())
        (d / 'x.json').write_text(json.dumps({'pr': 'x', 'controls': [
            {'id': 'NC1', 'what': 'w', 'mutations': [], 'targets': [], 'expect_failed': ['a']}]}))
        out = io.StringIO()
        with mock.patch.object(nc, 'SPECS', d), mock.patch.object(
                nc, 'run_control', lambda c, cid: (True, "mutation m | failed=['a', 'r'] INFO extra failures in pg: ['r']")), \
                redirect_stdout(out):
            self.assertEqual(nc.main([]), 0)
        notices = [l for l in out.getvalue().splitlines() if l.startswith('::notice')]
        self.assertEqual(notices, ["::notice title=SPEC x::1/1 PASS (NC1) | INFO NC1 extra failures in pg: ['r']"])


if __name__ == '__main__':
    unittest.main()
