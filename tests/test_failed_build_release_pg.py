"""Founder 2026-11-02 20:32, on real PostgreSQL: a failed build releases its credits (RELEASED, never SETTLED) and a
successful one settles. Runs in intake-budget-pg (skipped elsewhere without M4D2_DATABASE_URL)."""
from __future__ import annotations

import os
import pathlib
import unittest
import uuid
from decimal import Decimal

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()


class FailedBuildReleasesCredits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        root = pathlib.Path(__file__).resolve().parents[1]
        cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        cls.dbname = f'rel_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(root / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def setUp(self):
        from omni_prod.subscription_store import PostgresSubscriptionService
        self.subs = PostgresSubscriptionService(pool=self.pool)
        self.user = f'usr_{uuid.uuid4().hex[:10]}'
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO creator_accounts (id, email, password_hash, salt_b64) VALUES (%s,%s,%s,%s)',
                         (self.user, f'{self.user}@example.com', 'x', 'x'))
            conn.execute("INSERT INTO creator_subscriptions(user_id, plan_code, cycle, credits_used, provider_spend_usd) "
                         "VALUES (%s, 'pro', %s, 0, 0)", (self.user, self.subs._cycle_now()))
            conn.commit()

    def q(self, sql, *args):
        with self.pool.connection() as conn:
            return conn.execute(sql, args).fetchone()

    def counters(self):
        row = self.q('SELECT credits_used, provider_spend_usd FROM creator_subscriptions WHERE user_id = %s', self.user)
        return int(row[0]), Decimal(str(row[1]))

    def reserve(self, credits=45, estimate='0.50'):
        build_id = f'bld_{uuid.uuid4().hex}'
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    d = self.subs.reserve(cur, build_id=build_id, user_id=self.user, project_id='k', cost_class='standard',
                                          credits=credits, estimated_provider_cost_usd=Decimal(estimate))
                    self.assertTrue(d.allowed, d.reason)
        return build_id

    def test_a_failed_build_returns_the_whole_balance(self):
        before = self.counters()
        bid = self.reserve()
        self.assertEqual(self.counters()[0], before[0] + 45)
        out = self.subs.release_failed(build_id=bid, actual_provider_cost_usd=Decimal('0.0267'))
        self.assertEqual(out['credits_refunded'], 45)
        self.assertEqual(self.q('SELECT status FROM credit_reservations WHERE build_id=%s', bid)[0], 'RELEASED')
        self.assertEqual(self.counters(), (before[0], before[1] + Decimal('0.0267')))   # credits back, real cost on record
        ledger = self.q('SELECT account_id, delta, reason FROM credit_ledger WHERE idempotency_key=%s',
                        f'failed-build-release:{bid}')
        self.assertEqual(ledger, (self.user, 45, 'failed_build_released'))
        self.assertIsNone(self.subs.release_failed(build_id=bid, actual_provider_cost_usd=Decimal('0.0267')))
        self.assertEqual(self.counters()[0], before[0])                                 # never refunded twice
        from tests.evidence_notice import notice
        notice('failed build release PASS', f'RESERVED -> RELEASED, credits_used {before[0]+45} -> {self.counters()[0]}, '
                                            f'ledger +45 failed_build_released')

    def test_negative_control_a_successful_build_settles_and_keeps_its_credits(self):
        before = self.counters()
        bid = self.reserve()
        self.subs.settle(build_id=bid, actual_provider_cost_usd=Decimal('0.20'))
        self.assertEqual(self.q('SELECT status FROM credit_reservations WHERE build_id=%s', bid)[0], 'SETTLED')
        self.assertEqual(self.counters()[0], before[0] + 45)
        self.assertIsNone(self.q('SELECT 1 FROM credit_ledger WHERE idempotency_key=%s', f'failed-build-release:{bid}'))
        self.assertIsNone(self.subs.release_failed(build_id=bid))                       # a SETTLED build is not released


if __name__ == '__main__':
    unittest.main()
