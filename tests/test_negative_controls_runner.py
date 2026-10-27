"""scripts/run_negative_controls.py on a tiny fake repository: PASS only on the exact expected failures; every way
of not running (mutation not applied, nothing collected, expected test skipped) is FAIL, never a silent pass."""
import importlib.util
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


if __name__ == '__main__':
    unittest.main()
