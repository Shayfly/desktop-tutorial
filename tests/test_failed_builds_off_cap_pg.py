"""Michael 2026-11-14 (#356): "כשל לא נספר בתקרה, עד 3 בחודש." On real PostgreSQL.

Measured 2026-10-27 -> 2026-11-13: 20 of 29 builds with a provider cost FAILED, and release_failed() put each one's
cost on the customer's monthly plan budget -- the budget paid for our failures. Now the first three failed builds with
a cost in a calendar month (UTC, the subscription's cycle) do not count against it; the fourth does. The cost always
stays on the reservation (settled_provider_cost_usd), and a successful build always counts.
Runs in intake-budget-pg (skipped elsewhere without M4D2_DATABASE_URL)."""
from __future__ import annotations

import os
import pathlib
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
COST = Decimal('1.403646')       # the measured cost of the failed butcher-account build bld_cf406df6 (2026-11-12)


class FailedBuildsOffTheCap(unittest.TestCase):
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
        cls.dbname = f'foc_{uuid.uuid4().hex[:10]}'
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
                         "VALUES (%s, 'studio', %s, 0, 0)", (self.user, self.subs._cycle_now()))
            conn.commit()

    def spend(self):
        with self.pool.connection() as conn:
            return Decimal(str(conn.execute('SELECT provider_spend_usd FROM creator_subscriptions WHERE user_id=%s',
                                            (self.user,)).fetchone()[0]))

    def reserve(self):
        build_id = f'bld_{uuid.uuid4().hex}'
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    d = self.subs.reserve(cur, build_id=build_id, user_id=self.user, project_id='k', cost_class='standard',
                                          credits=500, estimated_provider_cost_usd=Decimal('2.003'))
                    self.assertTrue(d.allowed, d.reason)
        return build_id

    def fail(self):
        return self.subs.release_failed(build_id=self.reserve(), actual_provider_cost_usd=None,
                                        computed_provider_cost_usd=COST)

    def test_three_failures_are_free_and_the_fourth_counts(self):
        outs = [self.fail() for _ in range(3)]
        self.assertEqual([o['counted_against_plan_budget'] for o in outs], [False, False, False])
        self.assertEqual(self.spend(), Decimal('0'))
        fourth = self.fail()
        self.assertEqual((fourth['counted_against_plan_budget'], fourth['failed_builds_with_cost_this_month']), (True, 4))
        self.assertEqual(self.spend(), COST)
        with self.pool.connection() as conn:
            settled = [Decimal(str(r[0])) for r in conn.execute(
                "SELECT settled_provider_cost_usd FROM credit_reservations WHERE account_id=%s", (self.user,)).fetchall()]
        self.assertEqual(settled, [COST] * 4)                                   # every cost stays on record
        from tests.evidence_notice import notice
        notice('failed builds off cap', f'4 failed builds at {COST}: plan meter 0 after three, {self.spend()} after the fourth')

    def test_a_successful_build_always_counts(self):
        self.fail()
        bid = self.reserve()
        self.subs.settle(build_id=bid, actual_provider_cost_usd=Decimal('0.48'))
        self.assertEqual(self.spend(), Decimal('0.48'))

    def test_last_months_failures_do_not_use_this_months_places(self):
        for _ in range(3):
            self.fail()
        with self.pool.connection() as conn:
            conn.execute("UPDATE credit_reservations SET resolved_at = date_trunc('month', now()) - interval '1 day' "
                         "WHERE account_id=%s", (self.user,))
            conn.commit()
        self.assertFalse(self.fail()['counted_against_plan_budget'])

    def test_two_failures_at_once_cannot_both_take_the_last_place(self):
        self.fail()
        self.fail()                                                              # one free place left
        builds = [self.reserve(), self.reserve()]
        with ThreadPoolExecutor(2) as pool:
            outs = list(pool.map(lambda b: self.subs.release_failed(build_id=b, computed_provider_cost_usd=COST), builds))
        self.assertEqual(sorted(o['counted_against_plan_budget'] for o in outs), [False, True])
        self.assertEqual(self.spend(), COST)


if __name__ == '__main__':
    unittest.main()
