"""S13 (the owner, 2026-11-27, answer 6): migration 050 and the media infrastructure on REAL PostgreSQL (intake-budget-pg;
a throw-away database per class, every repository migration applied through the real runner). Needs M4D2_DATABASE_URL.

  asset_rights      the rights record and its gate (omni_prod/asset_rights.py), and the trigger that makes it evidence
  media_render_jobs the render queue (omni_prod/media_queue.py): idempotency, SKIP LOCKED between two real connections,
                    lease expiry after a "killed" worker, attempts, the total budget, tenant-scoped reads
  end to end        put -> record rights -> deliver to the owner; the same reference is the unknown answer for another
                    account; with no row, or a restricted one, nothing is delivered
  the rollback      infra/postgres/rollback/050_media_infra.down.sql removes exactly what 050 made
No provider is called; the handlers are plain functions."""
from __future__ import annotations

import datetime as dt
import os
import threading
import unittest
import uuid
from pathlib import Path

from omni_prod.asset_rights import (AssetRight, AssetRightsStore, RightsConflict, RightsMissing, RightsRestricted,
                                    RightsStale)
from omni_prod.media_queue import IdempotencyConflict, MediaJobQueue, drain, run_one
from omni_prod.media_store import MediaNotFound, TenantMediaStore
from omni_prod.migrations import discover_migrations
from omni_prod.schema_manifest import EXPECTED_VERSIONS, REQUIRED_MIGRATION
from tests.test_media_store import MP4, png, real_store

ROOT = Path(__file__).resolve().parent.parent
UP = ROOT / 'infra' / 'postgres' / '050_media_infra.sql'
DOWN = ROOT / 'infra' / 'postgres' / 'rollback' / '050_media_infra.down.sql'
DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
T0 = dt.datetime(2026, 11, 27, 12, 0, tzinfo=dt.timezone.utc)
TODAY = dt.date(2026, 11, 27)
TERMS = 'https://provider.example/terms'


class TheFiles(unittest.TestCase):
    def test_050_is_discovered_listed_in_the_manifest_and_bootstrapped(self):
        self.assertIn(50, {m.version for m in discover_migrations(UP.parent)})
        self.assertIn(50, EXPECTED_VERSIONS)
        self.assertGreaterEqual(REQUIRED_MIGRATION, 50)
        self.assertIn('-- BEGIN SOURCE 050_media_infra.sql', (ROOT / 'infra' / 'staging' / 'bootstrap_neon_empty.sql').read_text(encoding='utf-8'))

    def test_the_rollback_drops_exactly_what_050_creates(self):
        up, down = UP.read_text(encoding='utf-8'), DOWN.read_text(encoding='utf-8')
        for table in ('asset_rights', 'media_render_jobs'):
            self.assertIn(f'CREATE TABLE IF NOT EXISTS {table}', up)
            self.assertIn(f'DROP TABLE IF EXISTS {table}', down)
        for obj in ('DROP TRIGGER IF EXISTS asset_rights_append_only', 'DROP FUNCTION IF EXISTS asset_rights_are_evidence()',
                    'DELETE FROM schema_migrations WHERE version = 50'):
            self.assertIn(obj, down)

    def test_the_queue_is_named_and_its_wakeup_does_not_share_the_build_queue(self):
        from omni_prod import queueing
        self.assertEqual(queueing.MEDIA_QUEUE, 'omni-media')
        self.assertNotIn(queueing.MEDIA_QUEUE, (queueing.BUILD_QUEUE, queueing.PREVIEW_QUEUE))


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += dt.timedelta(seconds=seconds)


@unittest.skipUnless(DATABASE_URL, 'NOT_RUN: needs M4D2_DATABASE_URL (runs in intake-budget-pg)')
class _Database(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        cls.dbname = f'media_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url, min_size=1, max_size=6)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def sql(self, query, args=()):
        with self.pool.connection() as conn:
            with conn.transaction():
                cur = conn.execute(query, args)
                return cur.fetchall() if cur.description else cur.rowcount


def right_for(ref, *, account='usr_alice', project='prj_1', commercial=True, read_on=TODAY, provider='acme-video', **kw):
    return AssetRight(account_id=account, project_id=project, sha256=ref.sha256, media_key=ref.key, kind='video', mime=ref.mime,
                      provider=provider, model='clip-1', terms_url=TERMS, terms_read_on=read_on, commercial_use=commercial,
                      provider_task_id='task-1', prompt_sha256='b' * 64, restrictions=kw.pop('restrictions', ''), **kw)


class Rights(_Database):
    def setUp(self):
        self.s3, self.bucket = real_store()
        self.rights = AssetRightsStore(self.pool, today=lambda: TODAY)
        self.alice = TenantMediaStore(self.s3, 'usr_alice', rights=self.rights)
        self.bob = TenantMediaStore(self.s3, 'usr_bob', rights=self.rights)
        self.ref = self.alice.put('prj_1', MP4 + uuid.uuid4().bytes, 'video/mp4')     # a new file per test

    def test_a_file_with_no_rights_record_is_not_delivered(self):
        with self.assertRaises(RightsMissing):
            self.alice.deliver(self.ref)
        with self.assertRaises(RightsMissing):
            self.alice.link(self.ref)

    def test_a_recorded_file_reaches_its_owner_and_is_the_unknown_answer_for_another_account(self):
        self.assertTrue(self.rights.record(right_for(self.ref)))
        self.assertEqual(self.alice.deliver(self.ref), self.alice.read(self.ref))
        self.assertIn('X-Amz-Expires=300', self.alice.link(self.ref))
        with self.assertRaises(MediaNotFound):
            self.bob.deliver(self.ref)

    def test_the_row_says_who_made_it_and_that_the_customer_owns_it(self):
        self.rights.record(right_for(self.ref))
        row = self.sql('SELECT provider, model, terms_url, commercial_use, owner, provider_task_id FROM asset_rights WHERE sha256 = %s',
                       (self.ref.sha256,))
        self.assertEqual(row, [('acme-video', 'clip-1', TERMS, True, 'customer', 'task-1')])

    def test_a_restriction_blocks_delivery_and_says_why(self):
        self.rights.record(right_for(self.ref, commercial=False, restrictions='personal use only (clause 7.1)'))
        with self.assertRaises(RightsRestricted) as caught:
            self.alice.deliver(self.ref)
        self.assertIn('clause 7.1', str(caught.exception))

    def test_terms_read_ninety_one_days_ago_block_and_ninety_do_not(self):
        self.rights.record(right_for(self.ref, read_on=TODAY - dt.timedelta(days=90)))
        self.assertTrue(self.alice.deliver(self.ref))
        other = self.alice.put('prj_1', MP4 + uuid.uuid4().bytes, 'video/mp4')
        self.rights.record(right_for(other, read_on=TODAY - dt.timedelta(days=91), provider='old-provider'))
        with self.assertRaises(RightsStale):
            self.alice.deliver(other)
        self.assertIn(('old-provider', 'clip-1', 91), self.rights.stale_terms())

    def test_recording_twice_is_quiet_and_recording_other_facts_is_refused(self):
        self.assertTrue(self.rights.record(right_for(self.ref)))
        self.assertFalse(self.rights.record(right_for(self.ref)))
        with self.assertRaises(RightsConflict):
            self.rights.record(right_for(self.ref, commercial=False))
        self.assertTrue(self.rights.require(account_id='usr_alice', project_id='prj_1', sha256=self.ref.sha256).commercial_use)

    def test_a_record_is_evidence_it_is_never_updated_or_deleted(self):
        import psycopg
        self.rights.record(right_for(self.ref))
        for statement in ('UPDATE asset_rights SET commercial_use = false', 'DELETE FROM asset_rights'):
            with self.assertRaises(psycopg.errors.RaiseException):
                self.sql(statement)

    def test_the_database_refuses_what_the_module_would_refuse(self):
        import psycopg
        base = dict(account_id='usr_alice', project_id='prj_1', build_id=None, sha256='d' * 64,
                    media_key='tenants/usr_alice/projects/prj_1/media/' + 'd' * 64 + '.mp4', kind='video', mime='video/mp4',
                    provider='p', model='m', provider_task_id=None, terms_url=TERMS, terms_read_on=TODAY,
                    commercial_use=True, restrictions='', prompt_sha256=None)
        insert = 'INSERT INTO asset_rights ({}) VALUES ({})'
        bad = [dict(base, owner='provider'), dict(base, sha256='short'), dict(base, terms_url='http://x'),
               dict(base, provider='  '), dict(base, kind='song'),
               dict(base, media_key='tenants/usr_bob/projects/prj_1/media/' + 'd' * 64 + '.mp4')]
        for row in bad:
            with self.assertRaises(psycopg.errors.CheckViolation, msg=str(row)):
                self.sql(insert.format(', '.join(row), ', '.join(['%s'] * len(row))), tuple(row.values()))
        self.sql(insert.format(', '.join(base), ', '.join(['%s'] * len(base))), tuple(base.values()))    # and the good one passes

    def test_the_module_refuses_a_record_that_is_not_the_customers(self):
        for bad in (right_for(self.ref, owner='provider'), right_for(self.ref, provider=' '),
                    right_for(self.ref, account='usr_bob')):
            with self.assertRaises(ValueError):
                self.rights.record(bad)


class Queue(_Database):
    def setUp(self):
        self.clock = Clock()
        self.q = MediaJobQueue(self.pool, now=self.clock)
        self.sql('DELETE FROM media_render_jobs')
        self.n = 0

    def job(self, *, account='usr_alice', key=None, budget=600, attempts=3, kind='clip', payload=None):
        self.n += 1
        return self.q.enqueue(account_id=account, project_id='prj_1', build_id='bld_1', kind=kind,
                              idempotency_key=key or f'req-{self.n}-{uuid.uuid4().hex[:8]}', payload=payload or {'shots': 3},
                              budget_seconds=budget, max_attempts=attempts)[0]

    def test_the_same_request_is_one_job_and_a_different_one_under_its_key_is_refused(self):
        a, created = self.q.enqueue(account_id='usr_alice', project_id='prj_1', build_id='bld_1', kind='clip',
                                    idempotency_key='clip-request-1', payload={'a': 1}, budget_seconds=60)
        b, again = self.q.enqueue(account_id='usr_alice', project_id='prj_1', build_id='bld_1', kind='clip',
                                  idempotency_key='clip-request-1', payload={'a': 1}, budget_seconds=60)
        self.assertEqual((created, again, a.job_id), (True, False, b.job_id))
        with self.assertRaises(IdempotencyConflict):
            self.q.enqueue(account_id='usr_alice', project_id='prj_1', build_id='bld_1', kind='clip',
                           idempotency_key='clip-request-1', payload={'a': 2}, budget_seconds=60)
        self.assertEqual(self.sql("SELECT count(*) FROM media_render_jobs WHERE idempotency_key = 'clip-request-1'"), [(1,)])
        # the same key under another account is another job
        c = self.job(account='usr_bob', key='clip-request-1')
        self.assertNotEqual(c.job_id, a.job_id)

    def test_oldest_first_and_an_empty_queue_answers_none(self):
        first, second = self.job(), self.job()
        self.clock.advance(1)
        self.assertEqual(self.q.claim('w1', lease_seconds=30).job_id, first.job_id)
        self.assertEqual(self.q.claim('w1', lease_seconds=30).job_id, second.job_id)
        self.assertIsNone(self.q.claim('w1', lease_seconds=30))

    def test_two_workers_on_two_connections_never_get_the_same_job(self):
        for _ in range(8):
            self.job()
        got, errors, gate = [], [], threading.Barrier(4, timeout=10)

        def work(name):
            try:
                gate.wait()
                while True:
                    job = self.q.claim(name, lease_seconds=60)
                    if job is None:
                        return
                    got.append(job.job_id)
            except Exception as exc:       # noqa: BLE001
                errors.append(exc)
        threads = [threading.Thread(target=work, args=(f'w{i}',)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        self.assertEqual(errors, [])
        self.assertEqual(len(got), 8)
        self.assertEqual(len(set(got)), 8, 'a job was handed to two workers')

    def test_a_killed_worker_loses_its_job_to_the_next_claim_and_the_attempt_is_counted(self):
        job = self.job()
        first = self.q.claim('dies', lease_seconds=30)
        self.assertEqual((first.attempts, first.lease_owner), (1, 'dies'))
        self.clock.advance(29)
        self.assertIsNone(self.q.claim('w2', lease_seconds=30), 'a live lease is not taken')
        self.clock.advance(2)                                                    # the lease ran out; nobody finished
        second = self.q.claim('w2', lease_seconds=30)
        self.assertEqual((second.job_id, second.attempts, second.lease_owner), (job.job_id, 2, 'w2'))
        self.assertFalse(self.q.complete(job.job_id, 'dies', {'x': 1}), 'the dead worker finished late: refused')
        self.assertTrue(self.q.complete(job.job_id, 'w2', {'x': 1}))
        done = self.q.get(account_id='usr_alice', job_id=job.job_id)
        self.assertEqual((done.status, done.result, done.lease_owner), ('succeeded', {'x': 1}, None))

    def test_a_job_that_loses_its_worker_on_every_attempt_ends_dead_not_running_forever(self):
        job = self.job(attempts=2)
        for worker in ('a', 'b'):
            self.assertEqual(self.q.claim(worker, lease_seconds=10).job_id, job.job_id)
            self.clock.advance(11)
        self.assertIsNone(self.q.claim('c', lease_seconds=10))
        ended = self.q.get(account_id='usr_alice', job_id=job.job_id)
        self.assertEqual((ended.status, ended.attempts, ended.error_code), ('dead', 2, 'lease_lost_attempts_used'))

    def test_the_total_budget_counts_from_the_first_start_and_a_heartbeat_cannot_stretch_it(self):
        job = self.job(budget=100)
        self.q.claim('w', lease_seconds=60)
        self.clock.advance(50)
        self.assertTrue(self.q.heartbeat(job.job_id, 'w', lease_seconds=600))
        lease = self.sql('SELECT lease_expires_at FROM media_render_jobs WHERE job_id = %s', (job.job_id,))[0][0]
        self.assertEqual(lease, T0 + dt.timedelta(seconds=100), 'the lease stops at the budget, not at +600')
        self.clock.advance(51)
        self.assertFalse(self.q.heartbeat(job.job_id, 'w', lease_seconds=60))
        self.assertIsNone(self.q.claim('w2', lease_seconds=60))
        ended = self.q.get(account_id='usr_alice', job_id=job.job_id)
        self.assertEqual((ended.status, ended.error_code), ('failed', 'budget_exceeded'))

    def test_a_failure_with_retry_goes_back_until_the_attempts_are_used(self):
        job = self.job(attempts=2)
        self.q.claim('w', lease_seconds=60)
        self.assertTrue(self.q.fail(job.job_id, 'w', code='provider_busy', message='try later', retry=True))
        self.assertEqual(self.q.get(account_id='usr_alice', job_id=job.job_id).status, 'queued')
        self.q.claim('w', lease_seconds=60)
        self.assertTrue(self.q.fail(job.job_id, 'w', code='provider_busy', message='again', retry=True))
        ended = self.q.get(account_id='usr_alice', job_id=job.job_id)
        self.assertEqual((ended.status, ended.error_code, ended.attempts), ('dead', 'provider_busy', 2))

    def test_only_the_lease_holder_may_finish_or_fail_a_job(self):
        job = self.job()
        self.q.claim('owner', lease_seconds=60)
        self.assertFalse(self.q.complete(job.job_id, 'thief', {}))
        self.assertFalse(self.q.fail(job.job_id, 'thief', code='x', message='', retry=False))
        self.assertFalse(self.q.heartbeat(job.job_id, 'thief', lease_seconds=60))
        self.assertEqual(self.q.get(account_id='usr_alice', job_id=job.job_id).status, 'running')

    def test_another_account_reads_a_job_as_an_unknown_id(self):
        job = self.job()
        self.assertIsNone(self.q.get(account_id='usr_bob', job_id=job.job_id))
        self.assertIsNone(self.q.get(account_id='usr_bob', job_id='mrj_' + '0' * 32))

    def test_every_input_is_bounded_and_a_bad_one_raises(self):
        base = dict(account_id='usr_alice', project_id='prj_1', build_id='b', kind='clip', idempotency_key='request-0001',
                    payload={}, budget_seconds=60)
        for change in ({'budget_seconds': 0}, {'budget_seconds': 7201}, {'max_attempts': 6}, {'max_attempts': 0},
                       {'kind': 'Clip!'}, {'idempotency_key': 'x'}, {'payload': 'text'}):
            with self.assertRaises(ValueError, msg=str(change)):
                self.q.enqueue(**{**base, **change})
        with self.assertRaises(ValueError):
            self.q.claim('w', lease_seconds=0)
        with self.assertRaises(ValueError):
            self.q.claim('w', lease_seconds=1801)
        with self.assertRaises(ValueError):
            self.q.claim(' ', lease_seconds=10)

    def test_run_one_completes_a_job_and_an_unknown_kind_fails_out_loud(self):
        ok, odd = self.job(kind='clip'), self.job(kind='hologram')
        calls = []
        handlers = {'clip': lambda j: calls.append((j.job_id, j.attempts)) or {'frames': 3}}
        self.assertEqual(drain(self.q, 'w', handlers, max_jobs=5), [ok.job_id, odd.job_id])
        self.assertEqual(calls, [(ok.job_id, 1)])
        self.assertEqual(self.q.get(account_id='usr_alice', job_id=ok.job_id).result, {'frames': 3})
        failed = self.q.get(account_id='usr_alice', job_id=odd.job_id)
        self.assertEqual((failed.status, failed.error_code), ('failed', 'no_handler'))

    def test_a_handler_that_raises_is_retried_with_its_attempt_number_and_then_dead(self):
        job = self.job(attempts=2)
        seen = []

        def boom(j):
            seen.append(j.attempts)
            raise RuntimeError('provider timed out')
        self.assertEqual(run_one(self.q, 'w', {'clip': boom}), job.job_id)
        self.assertEqual(run_one(self.q, 'w', {'clip': boom}), job.job_id)
        self.assertIsNone(run_one(self.q, 'w', {'clip': boom}))
        self.assertEqual(seen, [1, 2])
        ended = self.q.get(account_id='usr_alice', job_id=job.job_id)
        self.assertEqual((ended.status, ended.error_code), ('dead', 'handler_error'))
        self.assertIn('provider timed out', ended.error_message)

    def test_a_handler_that_returns_a_non_dict_fails_the_job_and_drain_is_bounded(self):
        self.job()
        self.job()
        self.job()
        self.assertEqual(len(drain(self.q, 'w', {'clip': lambda j: 'done'}, max_jobs=2)), 2)
        self.assertEqual(self.sql("SELECT count(*) FROM media_render_jobs WHERE status = 'queued'"), [(1,)])
        self.assertEqual(self.sql("SELECT count(*) FROM media_render_jobs WHERE error_code = 'handler_result'"), [(2,)])
        with self.assertRaises(ValueError):
            drain(self.q, 'w', {}, max_jobs=0)

    def test_the_database_refuses_a_running_job_with_no_lease(self):
        import psycopg
        job = self.job()
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.sql("UPDATE media_render_jobs SET status = 'running' WHERE job_id = %s", (job.job_id,))


class Rollback(unittest.TestCase):
    @unittest.skipUnless(DATABASE_URL, 'NOT_RUN: needs M4D2_DATABASE_URL (runs in intake-budget-pg)')
    def test_the_rollback_removes_both_tables_the_trigger_and_the_migration_row(self):
        import psycopg
        from omni_prod.migration_runner import apply_migrations
        admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        name = f'media_down_{uuid.uuid4().hex[:8]}'
        admin.execute(f'CREATE DATABASE {name}')
        try:
            with psycopg.connect(DATABASE_URL.rsplit('/', 1)[0] + '/' + name) as conn:
                apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
                present = "SELECT to_regclass('asset_rights') IS NOT NULL, to_regclass('media_render_jobs') IS NOT NULL"
                self.assertEqual(conn.execute(present).fetchone(), (True, True))
                conn.commit()
                conn.execute(DOWN.read_text(encoding='utf-8'))
                self.assertEqual(conn.execute(present).fetchone(), (False, False))
                self.assertEqual(conn.execute("SELECT count(*) FROM pg_proc WHERE proname = 'asset_rights_are_evidence'").fetchone(), (0,))
                self.assertEqual(conn.execute('SELECT count(*) FROM schema_migrations WHERE version = 50').fetchone(), (0,))
                conn.commit()
                # the migration applies again after a rollback
                apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
                self.assertEqual(conn.execute(present).fetchone(), (True, True))
        finally:
            admin.execute(f'DROP DATABASE IF EXISTS {name} WITH (FORCE)')
            admin.close()


if __name__ == '__main__':
    unittest.main()
