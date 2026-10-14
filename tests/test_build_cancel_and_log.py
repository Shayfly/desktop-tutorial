"""Stop a build and its live log (directive 2026-10-09 §10, §12).

Unit tests use the existing BuildHarness; the repository tests run against a
real Postgres with migration 031 applied (skipped, not faked, otherwise).
"""
from __future__ import annotations

import os
import unittest
import uuid
from decimal import Decimal

from omni_prod.build_control import BuildCancelled, BuildControl, ControlledExecutor, install
from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.models import BuildStatus
from tests.test_m3_preview_logic import BuildHarness, FakeJobs


class _Jobs(FakeJobs):
    def __init__(self, stop_after_checks: int | None = None):
        super().__init__()
        self.events: list[tuple[str, str]] = []
        self.stop_after = stop_after_checks
        self.asked = 0

    def add_event(self, build_id, kind, message):
        self.events.append((kind, message))

    def cancel_requested(self, build_id):
        self.asked += 1
        return self.stop_after is not None and self.asked > self.stop_after


class _Exec:
    def __init__(self, reports):
        self.reports = list(reports)
        self.runs = 0
        self.last_probe = {'status': 'passed'}

    def execute(self, *, repository, spec):
        self.runs += 1
        return self.reports.pop(0)


class BuildControlTests(unittest.TestCase):
    def test_checkpoint_raises_only_after_a_stop_request(self):
        jobs = _Jobs(stop_after_checks=1)
        control = BuildControl(jobs, 'bld_1')
        control.checkpoint()
        with self.assertRaises(BuildCancelled):
            control.checkpoint()
        self.assertEqual(jobs.events[-1][0], 'cancel')

    def test_model_call_is_logged_in_customer_language_and_checked_first(self):
        jobs = _Jobs()
        control = BuildControl(jobs, 'bld_1')
        control.before_model_call('codegen')
        control.before_model_call('repair')
        self.assertEqual([k for k, _ in jobs.events], ['model', 'model'])
        self.assertEqual(jobs.events[0][1], 'כותב את הקוד')
        self.assertEqual(jobs.asked, 2)

    def test_stop_before_a_model_call_never_reaches_the_provider(self):
        jobs = _Jobs(stop_after_checks=0)
        control = BuildControl(jobs, 'bld_1')
        with self.assertRaises(BuildCancelled):
            control.before_model_call('codegen')
        self.assertEqual(control.model_calls, 0)

    def test_executor_logs_each_test_round_and_keeps_delegation(self):
        jobs = _Jobs()
        control = BuildControl(jobs, 'bld_1')
        inner = _Exec([ExecutionReport(False, (AcceptanceFailure('AC-1', 'the list is empty after adding', 'E'),), 'log'),
                       ExecutionReport(True, (), 'log')])
        ex = ControlledExecutor(inner, control)
        ex.execute(repository={}, spec=None)
        ex.execute(repository={}, spec=None)
        self.assertIn('סבב בדיקות 1: 1 נכשלו — the list is empty after adding', jobs.events[0][1])
        self.assertEqual(jobs.events[1][1], 'סבב בדיקות 2: כל הבדיקות עברו')
        self.assertEqual(ex.last_probe, {'status': 'passed'})  # evidence still reachable

    def test_stop_before_a_sandbox_run_skips_the_run(self):
        jobs = _Jobs(stop_after_checks=0)
        inner = _Exec([ExecutionReport(True, (), 'log')])
        with self.assertRaises(BuildCancelled):
            ControlledExecutor(inner, BuildControl(jobs, 'bld_1')).execute(repository={}, spec=None)
        self.assertEqual(inner.runs, 0)

    def test_install_hooks_gateway_and_engine(self):
        class G:
            before_call = None
        class E:
            executor = _Exec([])
        g, e = G(), E()
        control = BuildControl(_Jobs(), 'b')
        install(e, g, control)
        self.assertEqual(g.before_call, control.before_model_call)
        self.assertIsInstance(e.executor, ControlledExecutor)


class CancelledBuildJobTests(unittest.TestCase):
    def test_stop_during_generation_writes_cancelled_and_settles_only_real_spend(self):
        h = BuildHarness(calls=2, engine_exc=BuildCancelled('build bld_1 stopped by its owner'))
        h.jobs = _Jobs()
        self.assertEqual(h.run(), 'cancelled')
        self.assertEqual(h.final['target'], BuildStatus.CANCELLED)
        self.assertEqual(h.final['error_code'], 'cancelled_by_user')
        self.assertIsNone(h.final.get('result_version_id'))
        h.workspace.commit.assert_not_called()  # no version from a stopped build
        h.subs.settle.assert_called_once_with(build_id='bld_1', actual_provider_cost_usd=Decimal('0.50'))

    def test_stop_before_any_paid_call_releases_the_reservation(self):
        h = BuildHarness(calls=0)
        h.jobs = _Jobs(stop_after_checks=0)
        self.assertEqual(h.run(), 'cancelled')
        h.engine.build.assert_not_called()
        h.subs.release.assert_called_once_with(build_id='bld_1')
        h.subs.settle.assert_not_called()


DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')


def _skip_reason():
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            if conn.execute("SELECT to_regclass('public.build_events')").fetchone()[0] is None:
                return 'schema (through migration 031) not applied'
    except Exception as exc:
        return f'no live Postgres: {exc}'
    return None


_SKIP = _skip_reason()


@unittest.skipIf(_SKIP, _SKIP)
class CancelRepositoryLivePostgresTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.db import DatabasePool
        from omni_prod.job_repository import PostgresBuildRepository
        self.pool = DatabasePool(DATABASE_URL)
        self.jobs = PostgresBuildRepository(self.pool)
        self.project = f'tenant_{uuid.uuid4().hex[:8]}'

    def _build(self, status):
        build_id = f'bld_{uuid.uuid4().hex[:10]}'
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute("INSERT INTO build_jobs(id, project_id, status) VALUES (%s, %s, %s)",
                             (build_id, self.project, status))
        return build_id

    def _row(self, build_id):
        with self.pool.connection() as conn:
            return conn.execute("SELECT status, error_code, cancel_requested_at IS NOT NULL, finished_at IS NOT NULL "
                                "FROM build_jobs WHERE id = %s", (build_id,)).fetchone()

    def test_queued_build_is_cancelled_at_once_and_never_claimed(self):
        b = self._build('queued')
        self.assertEqual(self.jobs.request_cancel(b, self.project, requested_by='u1'), 'cancelled')
        self.assertEqual(self._row(b), ('cancelled', 'cancelled_by_user', True, True))
        # The worker's claim fails: it never starts.
        self.assertFalse(self.jobs.transition(build_id=b, expected=BuildStatus.QUEUED, target=BuildStatus.RUNNING))
        self.assertEqual(self.jobs.request_cancel(b, self.project, requested_by='u1'), 'cancelled')  # idempotent

    def test_running_build_gets_a_flag_the_worker_reads(self):
        b = self._build('running')
        self.assertFalse(self.jobs.cancel_requested(b))
        self.assertEqual(self.jobs.request_cancel(b, self.project, requested_by='u1'), 'cancel_requested')
        self.assertTrue(self.jobs.cancel_requested(b))
        self.assertEqual(self._row(b)[0], 'running')
        self.assertTrue(self.jobs.transition(build_id=b, expected=BuildStatus.RUNNING, target=BuildStatus.CANCELLED,
                                             error_code='cancelled_by_user'))

    def test_finished_build_is_not_changed(self):
        b = self._build('ready')
        self.assertEqual(self.jobs.request_cancel(b, self.project, requested_by='u1'), 'ready')
        self.assertEqual(self._row(b)[:3], ('ready', None, False))

    def test_another_tenant_cannot_cancel_or_read_the_log(self):
        b = self._build('queued')
        with self.assertRaises(KeyError):
            self.jobs.request_cancel(b, 'tenant_other', requested_by='intruder')
        with self.assertRaises(KeyError):
            self.jobs.events(b, 'tenant_other')
        self.assertEqual(self._row(b)[0], 'queued')

    def test_phase_changes_and_events_form_an_ordered_log(self):
        b = self._build('running')
        self.jobs.update_phase(b, 'GENERATING', 'x')
        self.jobs.add_event(b, 'model', 'כותב את הקוד')
        self.jobs.add_event(b, 'check', 'סבב בדיקות 1: כל הבדיקות עברו')
        log = self.jobs.events(b, self.project)
        self.assertEqual([e['kind'] for e in log], ['phase', 'model', 'check'])
        later = self.jobs.events(b, self.project, after=log[0]['seq'])
        self.assertEqual(len(later), 2)
        self.assertEqual(self.jobs.latest_for_project(self.project)['build_id'], b)


if __name__ == '__main__':
    unittest.main()
