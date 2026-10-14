"""Build state machine (Production Assurance v2 §5): legal transitions, phases
forward-only while RUNNING, and no way to skip a gate by retry, duplicate
delivery, a stale worker or a crash."""
import os
import unittest
import uuid

from omni_prod.build_state import PHASES, assert_transition, can_transition, phase_may_follow, terminal
from omni_prod.models import BuildStatus

DATABASE_URL = os.environ.get('M4D2_DATABASE_URL')


class TransitionTableTests(unittest.TestCase):
    def test_terminal_states_are_final(self):
        for s in (BuildStatus.READY, BuildStatus.FAILED, BuildStatus.CANCELLED):
            self.assertTrue(terminal(s))
            for t in BuildStatus:
                self.assertFalse(can_transition(s, t), (s, t))

    def test_ready_only_from_running(self):
        self.assertTrue(can_transition(BuildStatus.RUNNING, BuildStatus.READY))
        with self.assertRaises(ValueError):
            assert_transition(BuildStatus.QUEUED, BuildStatus.READY)     # no READY without running the pipeline

    def test_phases_only_move_forward(self):
        self.assertTrue(phase_may_follow('PLANNING', 'GENERATING'))
        self.assertTrue(phase_may_follow('GENERATING', 'GENERATING'))
        self.assertFalse(phase_may_follow('VERIFYING', 'GENERATING'))
        self.assertTrue(phase_may_follow('RUNNING', 'PLANNING'))          # just claimed
        self.assertFalse(phase_may_follow('PLANNING', 'NOT_A_PHASE'))
        self.assertEqual(PHASES[-1], 'VERIFYING')


@unittest.skipUnless(DATABASE_URL, 'live PostgreSQL not configured')
class LivePostgresStateTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.db import DatabasePool
        from omni_prod.job_repository import PostgresBuildRepository
        self.pool = DatabasePool(DATABASE_URL)
        self.jobs = PostgresBuildRepository(self.pool)

    def _build(self, status='queued'):
        build_id = f'bld_{uuid.uuid4().hex[:10]}'
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute("INSERT INTO build_jobs(id, project_id, status) VALUES (%s, %s, %s)",
                             (build_id, f'tenant_{uuid.uuid4().hex[:6]}', status))
        return build_id

    def _row(self, build_id):
        with self.pool.connection() as conn:
            return conn.execute('SELECT status, phase FROM build_jobs WHERE id = %s', (build_id,)).fetchone()

    def test_duplicate_delivery_claims_once(self):
        b = self._build()
        self.assertTrue(self.jobs.transition(build_id=b, expected=BuildStatus.QUEUED, target=BuildStatus.RUNNING))
        self.assertFalse(self.jobs.transition(build_id=b, expected=BuildStatus.QUEUED, target=BuildStatus.RUNNING))

    def test_a_failed_build_cannot_be_retried_into_ready(self):
        b = self._build()
        self.jobs.transition(build_id=b, expected=BuildStatus.QUEUED, target=BuildStatus.RUNNING)
        self.assertTrue(self.jobs.transition(build_id=b, expected=BuildStatus.RUNNING, target=BuildStatus.FAILED,
                                             error_code='release_policy_failed'))
        # a retry/duplicate worker that still thinks it is RUNNING cannot write READY
        self.assertFalse(self.jobs.transition(build_id=b, expected=BuildStatus.RUNNING, target=BuildStatus.READY))
        self.assertEqual(self._row(b)[0], 'failed')

    def test_phase_writes_forward_only_and_never_after_terminal(self):
        b = self._build()
        self.jobs.transition(build_id=b, expected=BuildStatus.QUEUED, target=BuildStatus.RUNNING)
        self.assertTrue(self.jobs.update_phase(b, 'PLANNING'))
        self.assertTrue(self.jobs.update_phase(b, 'VERIFYING'))
        self.assertFalse(self.jobs.update_phase(b, 'GENERATING'))           # backwards
        self.assertEqual(self._row(b)[1], 'VERIFYING')
        self.jobs.transition(build_id=b, expected=BuildStatus.RUNNING, target=BuildStatus.READY)
        self.assertFalse(self.jobs.update_phase(b, 'VERIFYING'))            # stale worker after READY
        self.assertEqual(self._row(b), ('ready', 'READY'))


if __name__ == '__main__':
    unittest.main()
