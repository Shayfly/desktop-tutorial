"""G8's rules, bounds and wiring without starting a server (the real-server cases are in tests/test_g8_runtime_load.py).
Every rule of `judge` is exercised on its own here, so each negative control runs in a second."""
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import runtime_load as R
from omni_prod.autonomous_core import ExecutionReport
from omni_prod.skill_units import gate as G
from tests.test_g8_runtime_load import GOOD, LocalSandbox


class TheRulesAndTheBounds(unittest.TestCase):
    def test_each_limit_is_judged_on_its_own(self):
        ok = {'started': True, 'requests': R.REQUESTS, 'errors': 0, 'alive': True, 'p95_ms': 40, 'rss_kb': 30_000}
        self.assertEqual(R.judge(ok), [])
        self.assertEqual([f['code'] for f in R.judge({**ok, 'p95_ms': R.P95_LIMIT_MS + 1})], ['LOAD_SLOW'])
        self.assertEqual([f['code'] for f in R.judge({**ok, 'rss_kb': R.RSS_LIMIT_KB + 1})], ['MEMORY_HIGH'])
        self.assertEqual([f['code'] for f in R.judge({**ok, 'requests': R.REQUESTS - 1})], ['LOAD_ERRORS'])
        self.assertEqual([f['code'] for f in R.judge({**ok, 'alive': False})], ['RUNTIME_CRASHED'])
        self.assertEqual(R.judge({**ok, 'p95_ms': R.P95_LIMIT_MS, 'rss_kb': R.RSS_LIMIT_KB}), [])   # the limit itself passes
        self.assertEqual({f['code'] for f in R.judge({**ok, 'alive': False, 'errors': 3})}, {'LOAD_ERRORS', 'RUNTIME_CRASHED'})
        for code in R.CODES:
            self.assertIn(code, R._FIX)

    def test_a_server_that_never_started_is_its_own_finding(self):
        self.assertEqual([f['code'] for f in R.judge({'started': False, 'requests': 0})], ['LOAD_NOT_STARTED'])

    def test_warn_records_and_goes_on_and_block_fails_on_the_same_measurement(self):
        import json

        class Measured(LocalSandbox):
            def _run(self, repository, argv, build_id, profile='default'):
                return {'returncode': 0, 'stdout': 'RUNTIME-LOAD ' + json.dumps(
                    {'started': True, 'requests': R.REQUESTS, 'errors': 7, 'alive': True, 'p95_ms': 30, 'rss_kb': 20000})}
        warn = R.RuntimeLoadExecutor(Measured(), 'warn')
        self.assertTrue(warn.execute(repository=GOOD, spec=None).passed)
        self.assertEqual((warn.last_load['status'], [f['code'] for f in warn.last_load['findings']]), ('fail', ['LOAD_ERRORS']))
        block = R.RuntimeLoadExecutor(Measured(), 'block')
        report = block.execute(repository=GOOD, spec=None)
        self.assertFalse(report.passed)
        self.assertIn('LOAD_ERRORS', report.failures[0].message)

    def test_the_run_is_bounded(self):
        self.assertGreaterEqual(R.CONCURRENCY, 4)                       # visitors arrive together: one at a time proves nothing
        self.assertIn('REQUESTS, CONCURRENCY, START, WALL = %d, %d,' % (R.REQUESTS, R.CONCURRENCY), R._LOAD)
        self.assertLessEqual(R.REQUESTS, 200)
        self.assertLess(R.START_SECONDS + 5, R.WALL_SECONDS)
        self.assertLess(R.WALL_SECONDS, 120)

    def test_what_cannot_run_is_not_run_never_a_pass(self):
        class NoSandbox:
            def execute(self, *, repository, spec):
                return ExecutionReport(True, (), 'ok')
        warn = R.RuntimeLoadExecutor(NoSandbox(), 'warn')
        self.assertTrue(warn.execute(repository=GOOD, spec=None).passed)
        self.assertEqual(warn.last_load['status'], 'NOT_RUN')
        block = R.RuntimeLoadExecutor(NoSandbox(), 'block')
        self.assertFalse(block.execute(repository=GOOD, spec=None).passed)        # blocking: NOT_RUN is not PASS
        self.assertFalse(R.RuntimeLoadExecutor(NoSandbox(), 'block').execute(repository={'app.py': 'x'}, spec=None).passed)

    def test_a_product_that_failed_earlier_is_not_load_tested(self):
        class Failing(LocalSandbox):
            def execute(self, *, repository, spec):
                return ExecutionReport(False, (), 'no')
        gate = R.RuntimeLoadExecutor(Failing(), 'block')
        self.assertFalse(gate.execute(repository=GOOD, spec=None).passed)
        self.assertEqual((gate._inner.runs, gate.last_load), ([], None))

    def test_a_deadline_ends_the_build_instead_of_being_a_result(self):
        from omni_prod.build_control import BuildDeadline

        class Late(LocalSandbox):
            def _run(self, *a, **k):
                raise BuildDeadline('out of time')
        with self.assertRaises(BuildDeadline):
            R.RuntimeLoadExecutor(Late(), 'warn').execute(repository=GOOD, spec=None)


class TheGate(unittest.TestCase):
    def test_it_enters_at_warn_and_its_mode_is_written_on_every_build(self):
        from types import SimpleNamespace
        self.assertIn('G8', G.CALIBRATING)
        engine = SimpleNamespace(executor=LocalSandbox())
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_G8', None)
            self.assertEqual(R.install(engine), 'warn')
        self.assertEqual(engine.gate_modes['G8'], 'warn')
        self.assertIsInstance(engine.executor, R.RuntimeLoadExecutor)
        self.assertEqual(R.report(engine), {'gate': 'G8', 'mode': 'warn', 'last': None})

    def test_off_is_said_and_installs_nothing(self):
        from types import SimpleNamespace
        engine = SimpleNamespace(executor=LocalSandbox())
        with mock.patch.dict(os.environ, {'OMNI_GATE_G8': 'off'}), self.assertLogs(R.__name__, 'WARNING') as logs:
            R.install(engine)
        self.assertIn('GATE_OFF gate=G8', logs.output[0])
        self.assertIsInstance(engine.executor, LocalSandbox)
        self.assertEqual(R.report(engine)['mode'], 'off')

    def test_the_worker_and_the_rehearsal_install_it_and_the_evidence_carries_it(self):
        root = Path(__file__).resolve().parent.parent
        worker = (root / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        self.assertIn('install_runtime_load(engine)', worker)
        self.assertIn("evidence['runtime_load'] = runtime_load_report(engine)", worker)
        rehearsal = (root / 'omni_prod' / 'rehearsal.py').read_text(encoding='utf-8')
        self.assertIn('install_runtime_load(engine)', rehearsal)
        self.assertIn("report['runtime_load'] = runtime_load_report(engine)", rehearsal)


if __name__ == '__main__':
    unittest.main()
