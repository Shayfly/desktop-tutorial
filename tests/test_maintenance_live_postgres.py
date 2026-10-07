"""Maintenance loop against a REAL Postgres (skipped without M4D2_DATABASE_URL schema).

Stuck RUNNING builds are failed as worker_lost and their reservation released;
expired previews on this host are marked and handed to the stop task.
"""
import os
import unittest
import uuid
from decimal import Decimal

DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')


def _skip():
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as c:
            if c.execute("SELECT to_regclass('public.project_previews')").fetchone()[0] is None:
                return 'schema not applied'
    except Exception as exc:
        return f'no live Postgres: {exc}'
    return None


_SKIP = _skip()


@unittest.skipIf(_SKIP, _SKIP)
class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.creator_accounts import PostgresAccountService
        from omni_prod.db import DatabasePool
        from omni_prod.job_repository import PostgresBuildRepository
        from omni_prod.preview_repository import PostgresPreviewRepository
        from omni_prod.subscription_store import PostgresSubscriptionService
        self.pool = DatabasePool(DATABASE_URL)
        self.subs = PostgresSubscriptionService(pool=self.pool)
        self.jobs = PostgresBuildRepository(self.pool)
        self.previews = PostgresPreviewRepository(self.pool)
        acc, _ = PostgresAccountService(token_secret='t' * 48, pool=self.pool).register(
            email=f'm-{uuid.uuid4().hex[:8]}@example.com', password='a-long-password-123')
        self.account = acc
        self.project = f'tenant_{uuid.uuid4().hex[:10]}'

    def tearDown(self):
        getattr(self.pool, 'close', lambda: None)()

    def test_stale_running_build_is_failed_and_released(self):
        from omni_prod import maintenance
        bid = f'bld_{uuid.uuid4().hex}'
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    self.subs.reserve(cur, build_id=bid, user_id=self.account.id, project_id=self.project,
                                      cost_class='standard', credits=0, estimated_provider_cost_usd=Decimal('0.5'),
                                      internal_qa=True)
                    cur.execute("INSERT INTO build_jobs(id, project_id, version_id, status, started_at) "
                                "VALUES (%s, %s, 'pending', 'running', now() - interval '2 hours')", (bid, self.project))
        fresh = f'bld_{uuid.uuid4().hex}'
        with self.pool.connection() as conn:
            conn.execute("INSERT INTO build_jobs(id, project_id, version_id, status, started_at) "
                         "VALUES (%s, %s, 'pending', 'running', now())", (fresh, self.project))
            conn.commit()
        stale = maintenance.stale_builds(self.pool, 45)
        self.assertIn(bid, stale)
        self.assertNotIn(fresh, stale)
        self.assertTrue(maintenance.reap_build(self.jobs, self.subs, bid, 45))
        with self.pool.connection() as conn:
            status, code = conn.execute("SELECT status, error_code FROM build_jobs WHERE id = %s", (bid,)).fetchone()
            res = conn.execute("SELECT status FROM credit_reservations WHERE build_id = %s", (bid,)).fetchone()[0]
        self.assertEqual((status, code), ('failed', 'worker_lost'))
        self.assertEqual(res, 'RELEASED')
        self.assertFalse(maintenance.reap_build(self.jobs, self.subs, bid, 45))  # idempotent

    def test_expired_preview_on_this_host_is_cleaned(self):
        from omni_prod import maintenance
        pid = f'prv_{uuid.uuid4().hex}'
        with self.pool.connection() as conn:
            conn.execute("INSERT INTO project_previews(id, project_id, version_id, status, expires_at, runtime_host, host_port) "
                         "VALUES (%s, %s, 'v1', 'RUNNING', now() - interval '1 minute', 'host-a', 40000)", (pid, self.project))
            conn.commit()
        stopped = []
        result = maintenance.run_once(pool=self.pool, preview_repo=self.previews, jobs=self.jobs, subscriptions=self.subs,
                                      stop_preview=stopped.append, runtime_host='host-a')
        self.assertGreaterEqual(result['expired'], 1)
        self.assertIn(pid, stopped)
        self.assertEqual(result['errors'], [])


if __name__ == '__main__':
    unittest.main()
