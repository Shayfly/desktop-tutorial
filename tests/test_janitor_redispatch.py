"""Janitor re-dispatches QUEUED work whose queue entry was lost (post-deploy
check 2026-10-09: a build pushed during a deploy drain was taken by the
stopped worker's open blocking read and stayed QUEUED)."""
import os
import unittest
import uuid
from unittest.mock import patch

from omni_prod import maintenance


class RedispatchUnitTests(unittest.TestCase):
    def test_only_lost_items_are_sent_again(self):
        sent = []
        with patch.object(maintenance, 'queued_too_long', return_value=[
                (maintenance.BUILD_JOB, 'bld_lost'), (maintenance.BUILD_JOB, 'bld_waiting'),
                (maintenance.MODIFICATION_JOB, 'mod_lost')]):
            out = maintenance.redispatch_lost(None, queued_ids=lambda: ['bld_waiting'],
                                              enqueue=lambda f, i: sent.append((f, i)), attempts={})
        self.assertEqual(out, ['bld_lost', 'mod_lost'])
        self.assertEqual(sent, [(maintenance.BUILD_JOB, 'bld_lost'), (maintenance.MODIFICATION_JOB, 'mod_lost')])

    def test_an_item_is_sent_at_most_three_times(self):
        sent, attempts = [], {}
        with patch.object(maintenance, 'queued_too_long', return_value=[(maintenance.BUILD_JOB, 'bld_x')]):
            for _ in range(5):
                maintenance.redispatch_lost(None, queued_ids=lambda: [], enqueue=lambda f, i: sent.append(i),
                                            attempts=attempts)
        self.assertEqual(sent, ['bld_x'] * 3)

    def test_a_redis_error_is_reported_not_raised(self):
        class P:
            def connection(self):
                raise RuntimeError('db down')
        out = maintenance.run_once(pool=P(), preview_repo=type('R', (), {'mark_expired': lambda self: 0})(),
                                   jobs=None, subscriptions=None, stop_preview=None, runtime_host='h',
                                   queued_ids=lambda: [], enqueue=lambda f, i: None)
        self.assertTrue(any(e.startswith('redispatch') for e in out['errors']))


DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')


def _skip():
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as c:
            if c.execute("SELECT to_regclass('public.build_events')").fetchone()[0] is None:
                return 'schema through 031 not applied'
    except Exception as exc:
        return f'no live Postgres: {exc}'
    return None


@unittest.skipIf(_skip(), _skip())
class QueuedTooLongLivePostgresTests(unittest.TestCase):
    def test_old_queued_builds_without_a_stop_request_are_found(self):
        from omni_prod.db import DatabasePool
        pool = DatabasePool(DATABASE_URL)
        old, new, stopping = (f'bld_{uuid.uuid4().hex[:10]}' for _ in range(3))
        with pool.connection() as c:
            with c.transaction():
                c.execute("INSERT INTO build_jobs(id, project_id, status, created_at) VALUES (%s,'t','queued', now() - interval '5 hours 59 minutes')", (old,))
                c.execute("INSERT INTO build_jobs(id, project_id, status) VALUES (%s,'t','queued')", (new,))
                c.execute("INSERT INTO build_jobs(id, project_id, status, created_at, cancel_requested_at) VALUES (%s,'t','queued', now() - interval '10 minutes', now())", (stopping,))
        with pool.connection() as c:
            with c.transaction():  # earlier test runs leave queued rows behind; age them out of the window
                c.execute("UPDATE build_jobs SET created_at = now() - interval '2 days' WHERE status = 'queued' "
                          "AND id NOT IN (%s, %s, %s)", (old, new, stopping))
        ids = [i for _, i in maintenance.queued_too_long(pool, 3)]
        self.assertIn(old, ids)
        self.assertNotIn(new, ids)
        self.assertNotIn(stopping, ids)
        with pool.connection() as c:
            with c.transaction():
                c.execute("INSERT INTO build_jobs(id, project_id, status, created_at) VALUES (%s,'t','queued', now() - interval '1 day')",
                          (f'bld_{uuid.uuid4().hex[:10]}',))
        self.assertEqual(len(maintenance.queued_too_long(pool, 3)), len(ids))  # too old: left alone


if __name__ == '__main__':
    unittest.main()
