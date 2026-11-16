"""A build ends itself before the queue kills the worker (the owner, 2026-11-16: "the worker dies mid-build").

Production, 2026-11-16: bld_426addd3 and bld_0e142230 were killed 15 minutes after they started (the queue's
900-second job timeout), in repair round 5-6, with no terminal state; one of them had caught the queue's
JobTimeoutException inside the visual check and reported it as a failed check. The real BuildControl, engine loop,
failure_code and control_exceptions run here; only the clock and the stores are in memory."""
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod import queueing as Q
from omni_prod import verification_verdict as V
from omni_prod.autonomous_core import AutonomousProductEngine
from omni_prod.build_control import BuildCancelled, BuildControl, BuildDeadline, install

ROOT = Path(__file__).resolve().parent.parent


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Jobs:
    def __init__(self):
        self.events, self.beats = [], 0

    def add_event(self, build_id, kind, message):
        self.events.append((kind, message))

    def checkpoint(self, build_id):
        self.beats += 1
        return False


class TheBudgetIsOrdered(unittest.TestCase):
    def test_repair_stops_before_the_build_stops_before_the_queue_kills(self):
        self.assertLess(Q.BUILD_REPAIR_UNTIL_SECONDS, Q.BUILD_STOP_AT_SECONDS)
        self.assertLessEqual(Q.BUILD_STOP_AT_SECONDS + 120, Q.BUILD_JOB_TIMEOUT_SECONDS)   # room to settle and write
        self.assertLess(Q.BUILD_JOB_TIMEOUT_SECONDS, 45 * 60)                               # and before the janitor

    def test_the_queue_and_every_build_job_use_the_one_limit(self):
        src = (ROOT / 'omni_prod' / 'queueing.py').read_text(encoding='utf-8')
        self.assertIn('default_timeout=BUILD_JOB_TIMEOUT_SECONDS', src)
        self.assertIn('timeout: int = BUILD_JOB_TIMEOUT_SECONDS', src)
        self.assertNotIn('900', src.split('def queue(')[1])                  # no second number below the constants

    def test_a_wrong_budget_is_refused(self):
        for kw in ({'repair_until_seconds': 0}, {'stop_at_seconds': -1}, {'repair_until_seconds': True},
                   {'repair_until_seconds': 50, 'stop_at_seconds': 50}, {'stop_at_seconds': '900'}):
            with self.assertRaises(ValueError, msg=str(kw)):
                BuildControl(Jobs(), 'b', **kw)


class TheBuildStopsItself(unittest.TestCase):
    def setUp(self):
        self.clock, self.jobs = Clock(), Jobs()
        self.control = BuildControl(self.jobs, 'bld_x', clock=self.clock)

    def test_inside_the_budget_a_step_runs_and_the_heartbeat_is_written(self):
        self.clock.now += Q.BUILD_STOP_AT_SECONDS - 1
        self.control.checkpoint()
        self.assertEqual(self.jobs.beats, 1)

    def test_past_the_limit_the_next_step_raises_and_says_so_to_the_customer(self):
        self.clock.now += Q.BUILD_STOP_AT_SECONDS
        with self.assertRaises(BuildDeadline) as ctx:
            self.control.before_model_call('repair')
        self.assertEqual(self.jobs.beats, 0)                                  # no step started
        self.assertIn(str(Q.BUILD_STOP_AT_SECONDS), str(ctx.exception))
        kind, message = self.jobs.events[-1]
        self.assertEqual(kind, 'info')
        self.assertIn(f'{Q.BUILD_STOP_AT_SECONDS // 60} דקות', message)
        self.assertIn('נעצרה', message)

    def test_a_deadline_is_a_failure_with_its_own_code_not_a_cancel(self):
        from omni_prod.worker_tasks import failure_code
        self.assertFalse(issubclass(BuildDeadline, BuildCancelled))
        self.assertEqual(failure_code(BuildDeadline('x')), 'build_timeout')
        self.assertEqual(failure_code(RuntimeError('x')), 'worker_exception')

    def test_the_queues_own_timeout_gets_the_same_code(self):
        from omni_prod.worker_tasks import failure_code
        timeouts = V.queue_timeouts()
        if not timeouts:
            self.skipTest('NOT_RUN: rq is not installed in this environment')
        self.assertEqual(failure_code(timeouts[0]('Task exceeded maximum timeout value (900 seconds)')), 'build_timeout')


class ATimeLimitIsNeverACheckFailure(unittest.TestCase):
    def test_a_check_re_raises_the_deadline_instead_of_reporting_it(self):
        self.assertIn(BuildDeadline, V.control_exceptions())
        with self.assertRaises(BuildDeadline):
            V.reraise_control(BuildDeadline('x'))
        V.reraise_control(RuntimeError('an ordinary check error is still reported, not raised'))

    def test_the_queues_timeout_is_re_raised_too(self):
        timeouts = V.queue_timeouts()
        if not timeouts:
            self.skipTest('NOT_RUN: rq is not installed in this environment')
        self.assertIn(timeouts[0], V.control_exceptions())
        with self.assertRaises(timeouts[0]):                                 # bld_0e142230: it was swallowed here
            V.reraise_control(timeouts[0]('Task exceeded maximum timeout value (900 seconds)'))

    def test_the_visual_check_asks_before_it_reports(self):
        src = (ROOT / 'omni_prod' / 'visual_qa.py').read_text(encoding='utf-8')
        self.assertIn('reraise_control', src)


class TheRepairLoopStopsWhenOutOfTime(unittest.TestCase):
    def test_install_gives_the_engine_the_controls_clock(self):
        clock = Clock()
        control = BuildControl(Jobs(), 'b', clock=clock)
        engine = SimpleNamespace(executor=SimpleNamespace(execute=lambda **k: None), core=SimpleNamespace())
        install(engine, SimpleNamespace(), control)
        self.assertFalse(engine.core.out_of_time())
        clock.now += Q.BUILD_REPAIR_UNTIL_SECONDS
        self.assertTrue(engine.core.out_of_time())

    def engine(self, clock, control, seconds_per_check):
        """The real engine and repair loop (the harness of test_j3_three_repair_round_policy); each check takes time."""
        from tests.test_j3_three_repair_round_policy import Architect, Generator, Repairer, Verifier

        class SlowVerifier(Verifier):
            def execute(inner, *, repository, spec):
                clock.now += seconds_per_check
                return super().execute(repository=repository, spec=spec)
        repair, verify = Repairer(), SlowVerifier()
        engine = AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=repair,
                                         executor=verify, max_repair_rounds=3)
        engine._summary = lambda repo, failures=(): {'files': [{'path': k, 'content': v} for k, v in repo.items()]}
        engine.out_of_time = control.out_of_repair_time
        return engine, repair, verify

    def test_a_build_out_of_time_starts_no_new_round_and_is_judged_on_its_best(self):
        clock = Clock()
        control = BuildControl(Jobs(), 'b', clock=clock)
        engine, repair, verify = self.engine(clock, control, seconds_per_check=Q.BUILD_REPAIR_UNTIL_SECONDS // 2 + 1)
        result = engine.build('site')
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.stop_reason, 'time_budget')
        self.assertEqual(repair.calls, 1)                    # round 0 + one repair fit; the third check never started
        self.assertEqual(len(verify.runs), 2)
        self.assertLess(clock.now - 1000.0, Q.BUILD_STOP_AT_SECONDS)   # it stopped itself before the hard limit

    def test_a_build_inside_its_time_still_gets_all_its_rounds(self):
        clock = Clock()
        control = BuildControl(Jobs(), 'b', clock=clock)
        engine, repair, verify = self.engine(clock, control, seconds_per_check=1)
        result = engine.build('site')
        self.assertEqual(repair.calls, 3)
        self.assertEqual(result.stop_reason, 'max_repair_rounds')

    def test_the_loop_asks_before_every_round_and_names_the_reason(self):
        src = (ROOT / 'omni_prod' / 'autonomous_core.py').read_text(encoding='utf-8')
        loop = src[src.index('while not report.passed and rounds < self.max_repair_rounds:'):]
        first = loop[:loop.index('if missing_input is not None:')]
        self.assertIn('if callable(out_of_time) and out_of_time():', first)
        self.assertIn("stop_reason = 'time_budget'", first)
        self.assertIn('break', first)

    def test_the_failure_message_says_the_build_was_out_of_time(self):
        src = (ROOT / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        self.assertIn("getattr(result, 'stop_reason', '') == 'time_budget'", src)
        self.assertIn('stopped repairing: the build was out of time', src)


class TheCustomerIsTold(unittest.TestCase):
    def test_every_way_a_build_can_stop_on_time_has_words_in_both_languages(self):
        js = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
        for code in ('build_timeout', 'provider_liability_unknown', 'worker_lost'):
            self.assertEqual(js.count(f"      {code}:'"), 2, code)           # Hebrew and English
            self.assertIn(f'{code}: 3', js, code)                            # the step the build stopped at


if __name__ == '__main__':
    unittest.main()
