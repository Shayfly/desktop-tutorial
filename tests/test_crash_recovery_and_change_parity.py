"""Crash recovery and change parity (autonomous completion directive §5)."""
import os
import unittest
import uuid
from unittest.mock import MagicMock

from omni_prod import maintenance
from omni_prod.build_control import BuildCancelled, BuildControl, ModificationJobs

DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')


def _skip():
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as c:
            row = c.execute("SELECT 1 FROM information_schema.columns WHERE table_name='build_jobs' "
                            "AND column_name='heartbeat_at'").fetchone()
            if row is None:
                return 'schema through 033 not applied'
    except Exception as exc:
        return f'no live Postgres: {exc}'
    return None


@unittest.skipIf(_skip(), _skip())
class RecoveryLivePostgresTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.db import DatabasePool
        self.pool = DatabasePool(DATABASE_URL)
        self.subs = MagicMock()
        self.sent = []

    def _build(self, *, stale=True, stop=False, attempts=0):
        bid = f'bld_{uuid.uuid4().hex[:12]}'
        with self.pool.connection() as c:
            with c.transaction():
                c.execute("INSERT INTO build_jobs(id, project_id, status, started_at, heartbeat_at, recovery_attempts, "
                          "cancel_requested_at) VALUES (%s, 't', 'running', now(), now() - %s::interval, %s, %s)",
                          (bid, '20 minutes' if stale else '1 minute', attempts, 'now()' if stop else None))
        return bid

    def _status(self, bid):
        with self.pool.connection() as c:
            return c.execute("SELECT status, error_code, recovery_attempts FROM build_jobs WHERE id=%s", (bid,)).fetchone()

    def run_once(self, busy=()):
        return maintenance.recover_lost_running(self.pool, subscriptions=self.subs,
                                                enqueue=lambda f, i: self.sent.append((f, i)),
                                                busy_ids=lambda: list(busy), minutes=15)

    def test_lost_build_is_requeued_once_then_failed(self):
        bid = self._build()
        out = self.run_once()
        self.assertIn(bid, out['recovered'])
        self.assertEqual(self._status(bid)[0], 'queued')
        self.assertIn((maintenance.BUILD_JOB, bid), self.sent)
        # the second loss ends it and releases the reservation
        with self.pool.connection() as c:
            with c.transaction():
                c.execute("UPDATE build_jobs SET status='running', heartbeat_at = now() - interval '20 minutes' WHERE id=%s", (bid,))
        out = self.run_once()
        self.assertIn(bid, out['failed'])
        self.assertEqual(self._status(bid)[:2], ('failed', 'worker_lost'))
        self.subs.release.assert_called_with(build_id=bid)

    def test_a_stop_request_on_a_lost_build_ends_it_cancelled(self):
        bid = self._build(stop=True)
        self.assertIn(bid, self.run_once()['cancelled'])
        self.assertEqual(self._status(bid)[:2], ('cancelled', 'cancelled_by_user'))

    def test_fresh_heartbeat_or_live_worker_is_left_alone(self):
        fresh = self._build(stale=False)
        busy = self._build()
        out = self.run_once(busy=[busy])
        self.assertNotIn(fresh, sum(out.values(), []))
        self.assertNotIn(busy, sum(out.values(), []))
        self.assertEqual(self._status(busy)[0], 'running')


@unittest.skipIf(_skip(), _skip())
class ChangeParityLivePostgresTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.db import DatabasePool
        self.pool = DatabasePool(DATABASE_URL)
        self.jobs = ModificationJobs(self.pool)
        with self.pool.connection() as c:
            row = c.execute("SELECT id, project_id FROM project_versions LIMIT 1").fetchone()
        if row is None:
            with self.pool.connection() as c:
                with c.transaction():
                    vid = f'v_{uuid.uuid4().hex[:12]}'
                    c.execute("INSERT INTO project_versions(id, project_id, repository_sha256, message) VALUES (%s,'t','x','m')", (vid,))
                    row = (vid, 't')
        self.vid, self.project = row

    def _mod(self, status):
        mid = f'mod_{uuid.uuid4().hex[:12]}'
        with self.pool.connection() as c:
            with c.transaction():
                c.execute("INSERT INTO modification_requests(id, project_id, user_id, source_version_id, "
                          "source_spec_version_id, followup, status) VALUES (%s,%s,'u',%s,%s,'f',%s)",
                          (mid, self.project, self.vid, self.vid, status))
        return mid

    def test_queued_change_is_cancelled_and_running_change_stops_at_the_next_step(self):
        q = self._mod('QUEUED')
        self.assertEqual(self.jobs.request_cancel(q, self.project, requested_by='u'), 'cancelled')
        r = self._mod('RUNNING')
        self.assertFalse(self.jobs.checkpoint(r))
        self.assertEqual(self.jobs.request_cancel(r, self.project, requested_by='u'), 'cancel_requested')
        control = BuildControl(self.jobs, r)
        with self.assertRaises(BuildCancelled):
            control.before_model_call('modification')
        log = self.jobs.events(r, self.project)
        self.assertEqual([e['kind'] for e in log], ['cancel', 'cancel'])
        with self.assertRaises(KeyError):
            self.jobs.events(r, 'another-tenant')

    def test_lost_running_change_is_requeued(self):
        m = self._mod('RUNNING')
        with self.pool.connection() as c:
            with c.transaction():
                c.execute("UPDATE modification_requests SET heartbeat_at = now() - interval '20 minutes' WHERE id=%s", (m,))
        sent = []
        out = maintenance.recover_lost_running(self.pool, subscriptions=MagicMock(),
                                               enqueue=lambda f, i: sent.append((f, i)), minutes=15)
        self.assertIn(m, out['recovered'])
        self.assertIn((maintenance.MODIFICATION_JOB, m), sent)


if __name__ == '__main__':
    unittest.main()
