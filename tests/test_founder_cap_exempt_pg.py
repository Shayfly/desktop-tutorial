"""Michael 2026-11-14 (a), CEO 2026-11-08 (a), Shai 2026-11-15, on real PostgreSQL: the founder account is not stopped
by the plan's monthly paid-provider budget nor by its monthly credits; every other account is, the flag turns both
exemptions off, and the $2 per-build cap stays.

The reproduction is the butcher block of 2026-11-14: Studio, cap $25, spend 24.916146, next build estimated 2.003.
Runs in intake-budget-pg (skipped elsewhere without M4D2_DATABASE_URL)."""
from __future__ import annotations

import os
import pathlib
import unittest
import uuid
from decimal import Decimal
from unittest import mock

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
FOUNDER = 'usr_GCWlMxENgr9vpwph'          # pricing._FOUNDER_DEFAULT (not a secret)
SPEND = Decimal('24.916146')              # creator_subscriptions row of 2026-11-14 19:12
ESTIMATE = Decimal('2.003')               # credit_reservations.estimated_provider_cost_usd of the bakery builds


class FounderCapExempt(unittest.TestCase):
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
        cls.dbname = f'fce_{uuid.uuid4().hex[:10]}'
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
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop('OMNI_FOUNDER_CAP_EXEMPT', None)
        os.environ.pop('OMNI_FOUNDER_ACCOUNT_IDS', None)
        os.environ.pop('OMNI_PROVIDER_CAP_STUDIO_USD', None)
        os.environ.pop('OMNI_FOUNDER_BUILD_LLM_USD', None)

    def tearDown(self):
        self.env.stop()

    def account(self, user):
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO creator_accounts (id, email, password_hash, salt_b64) VALUES (%s,%s,%s,%s) '
                         'ON CONFLICT DO NOTHING', (user, f'{user}@example.com', 'x', 'x'))
            conn.execute("INSERT INTO creator_subscriptions(user_id, plan_code, cycle, credits_used, provider_spend_usd) "
                         "VALUES (%s, 'studio', %s, 3545, %s) ON CONFLICT (user_id) DO UPDATE SET "
                         "plan_code='studio', cycle=EXCLUDED.cycle, credits_used=3545, provider_spend_usd=EXCLUDED.provider_spend_usd",
                         (user, self.subs._cycle_now(), SPEND))
            conn.commit()

    def spend(self, user):
        with self.pool.connection() as conn:
            return Decimal(str(conn.execute('SELECT provider_spend_usd FROM creator_subscriptions WHERE user_id=%s',
                                            (user,)).fetchone()[0]))

    def reserve(self, user):
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    return self.subs.reserve(cur, build_id=f'bld_{uuid.uuid4().hex}', user_id=user, project_id='k',
                                             cost_class='standard', credits=500, estimated_provider_cost_usd=ESTIMATE)

    def test_the_butcher_block_is_reproduced_for_a_customer(self):
        user = f'usr_{uuid.uuid4().hex[:10]}'
        self.account(user)
        pre = self.subs.authorize(user_id=user, cost_class='standard', credits=500, estimated_provider_cost_usd=ESTIMATE)
        self.assertEqual((pre.allowed, pre.reason), (False, 'paid-provider budget exhausted'))
        d = self.reserve(user)
        self.assertEqual((d.allowed, d.reason), (False, 'paid-provider budget exhausted'))
        self.assertEqual(self.spend(user), SPEND)                       # nothing reserved

    def test_the_founder_builds_and_the_spend_is_still_metered(self):
        self.account(FOUNDER)
        pre = self.subs.authorize(user_id=FOUNDER, cost_class='standard', credits=500, estimated_provider_cost_usd=ESTIMATE)
        self.assertTrue(pre.allowed, pre.reason)
        d = self.reserve(FOUNDER)
        self.assertTrue(d.allowed, d.reason)
        self.assertEqual(self.spend(FOUNDER), SPEND + ESTIMATE)         # metered, not hidden
        from tests.evidence_notice import notice
        notice('founder cap exempt', f'founder reserved {ESTIMATE} at spend {SPEND} over the $25 Studio cap; '
                                     f'meter now {self.spend(FOUNDER)}')

    def test_the_flag_turns_the_exemption_off(self):
        os.environ['OMNI_FOUNDER_CAP_EXEMPT'] = '0'
        self.account(FOUNDER)
        d = self.reserve(FOUNDER)
        self.assertEqual((d.allowed, d.reason), (False, 'paid-provider budget exhausted'))

    def test_an_unknown_flag_value_fails_loudly(self):
        os.environ['OMNI_FOUNDER_CAP_EXEMPT'] = 'yes'
        self.account(FOUNDER)
        with self.assertRaises(ValueError):
            self.subs.authorize(user_id=FOUNDER, cost_class='standard', credits=500, estimated_provider_cost_usd=ESTIMATE)

    def credits_used(self, user):
        with self.pool.connection() as conn:
            return int(conn.execute('SELECT credits_used FROM creator_subscriptions WHERE user_id=%s', (user,)).fetchone()[0])

    def set_credits(self, user, used):
        with self.pool.connection() as conn:
            conn.execute('UPDATE creator_subscriptions SET credits_used=%s WHERE user_id=%s', (used, user))
            conn.commit()

    def test_credits_no_longer_bind_the_founder_and_are_still_counted(self):
        """Shai 2026-11-15: the founder is exempt from monthly credits too. The founder row of 2026-11-15 01:12 had
        4,045 of Studio's 10,000; a 7,000-credit build crosses the limit. Every path is exercised: authorize, reserve
        (the build path) and consume."""
        self.account(FOUNDER)
        self.set_credits(FOUNDER, 4045)
        pre = self.subs.authorize(user_id=FOUNDER, cost_class='standard', credits=7000, estimated_provider_cost_usd=ESTIMATE)
        self.assertTrue(pre.allowed, pre.reason)
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    d = self.subs.reserve(cur, build_id=f'bld_{uuid.uuid4().hex}', user_id=FOUNDER, project_id='k',
                                          cost_class='standard', credits=7000, estimated_provider_cost_usd=ESTIMATE)
        self.assertTrue(d.allowed, d.reason)
        self.assertEqual(self.credits_used(FOUNDER), 11045)                      # counted, not hidden
        self.subs.consume(user_id=FOUNDER, decision=pre)
        self.assertEqual(self.credits_used(FOUNDER), 18045)
        from tests.evidence_notice import notice
        notice('founder credits exempt', f'founder at 4045/10000 reserved 7000 credits; counter now {self.credits_used(FOUNDER)}')

    def test_credits_still_bind_a_customer(self):
        user = f'usr_{uuid.uuid4().hex[:10]}'
        self.account(user)
        self.set_credits(user, 4045)
        d = self.subs.authorize(user_id=user, cost_class='standard', credits=7000, estimated_provider_cost_usd=ESTIMATE)
        self.assertEqual((d.allowed, d.reason), (False, 'monthly credits exhausted'))
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    r = self.subs.reserve(cur, build_id=f'bld_{uuid.uuid4().hex}', user_id=user, project_id='k',
                                          cost_class='standard', credits=7000, estimated_provider_cost_usd=ESTIMATE)
        self.assertEqual((r.allowed, r.reason), (False, 'monthly credits exhausted'))
        self.assertEqual(self.credits_used(user), 4045)
        allowed = self.subs.authorize(user_id=user, cost_class='standard', credits=500, estimated_provider_cost_usd=Decimal('0'))
        with self.assertRaises(PermissionError):
            self.set_credits(user, 9800)
            self.subs.consume(user_id=user, decision=allowed)

    def test_the_flag_turns_the_credit_exemption_off_too(self):
        os.environ['OMNI_FOUNDER_CAP_EXEMPT'] = '0'
        self.account(FOUNDER)
        self.set_credits(FOUNDER, 4045)
        d = self.subs.authorize(user_id=FOUNDER, cost_class='standard', credits=7000, estimated_provider_cost_usd=ESTIMATE)
        self.assertEqual((d.allowed, d.reason), (False, 'monthly credits exhausted'))

    def test_the_per_build_cap_is_untouched(self):
        from omni_prod.pricing import m5_founder_build_budget
        self.assertEqual(m5_founder_build_budget(), Decimal('2.00'))

if __name__ == '__main__':
    unittest.main()
