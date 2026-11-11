"""P0 2026-10-30, on real PostgreSQL: release() never released a reservation whose attempts showed authorized-but-
unmetered cost, and nothing reconciled afterwards -- a cancelled build kept its whole reservation RESERVED for ever.

The reconciler resolves RESERVED rows whose work is terminal: RELEASE when every call finished and nothing was metered
(counters back to their pre-reservation values), SETTLE on the metered total, HOLD while a call is still 'unknown'.
Runs in intake-budget-pg (no skip there)."""
from __future__ import annotations

import os
import pathlib
import unittest
import uuid
from decimal import Decimal

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()


class TheReservationReconciler(unittest.TestCase):
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
        cls.dbname = f'rec_{uuid.uuid4().hex[:10]}'
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

    def counters(self):
        with self.pool.connection() as conn:
            row = conn.execute('SELECT credits_used, provider_spend_usd FROM creator_subscriptions WHERE user_id = %s',
                               (self.user,)).fetchone()
        return int(row[0]), Decimal(str(row[1]))

    def status(self, build_id):
        with self.pool.connection() as conn:
            return conn.execute('SELECT status FROM credit_reservations WHERE build_id = %s', (build_id,)).fetchone()[0]

    def reserved_build(self, *, build_status, attempts):
        """A real reservation (90 credits, 0.70 USD -- the two stuck in production), a build in `build_status`,
        and provider-call attempts given as (outcome, authorized, metered). Aged past the reconciler's floor."""
        build_id = f'bld_{uuid.uuid4().hex}'
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    decision = self.subs.reserve(cur, build_id=build_id, user_id=self.user, project_id='k',
                                                 cost_class='standard', credits=90,
                                                 estimated_provider_cost_usd=Decimal('0.70'))
                    self.assertTrue(decision.allowed, decision.reason)
                    cur.execute("INSERT INTO build_jobs(id, project_id, version_id, status) VALUES (%s, 'k', 'pending', %s)",
                                (build_id, build_status))
                    for i, (outcome, authorized, metered) in enumerate(attempts):
                        cur.execute("INSERT INTO task_attempts(attempt_id, build_id, task_id, task_type, attempt_seq, kind, "
                                    "authorized_cost_usd, metered_cost_usd, outcome) "
                                    "VALUES (%s, %s, 't', 'code', %s, 'provider_call', %s, %s, %s)",
                                    (f'att_{uuid.uuid4().hex}', build_id, i, authorized, metered, outcome))
                    cur.execute("UPDATE credit_reservations SET created_at = now() - interval '1 hour' WHERE build_id = %s",
                                (build_id,))
        return build_id

    def reconcile(self):
        from omni_prod.reservation_reconciler import reconcile
        return {r['build_id']: r for r in reconcile(self.subs, self.pool, apply=True)}

    def test_a_cancelled_build_with_an_authorized_unmetered_attempt_ends_released_and_counters_return(self):
        before = self.counters()
        bid = self.reserved_build(build_status='cancelled', attempts=[('error', Decimal('0.05'), None)])
        self.assertEqual(self.counters(), (before[0] + 90, before[1] + Decimal('0.70')))
        self.subs.release(build_id=bid)                                    # the old path: still held
        self.assertEqual(self.status(bid), 'RESERVED')
        result = self.reconcile()[bid]
        self.assertEqual((result['action'], result['applied']), ('release', True))
        self.assertEqual(self.status(bid), 'RELEASED')
        self.assertEqual(self.counters(), before)
        from tests.evidence_notice import notice
        notice('reservation reconciler PASS', f'cancelled build, 1 authorized-unmetered attempt: RESERVED -> RELEASED; '
                                              f'counters before={before} after={self.counters()}')

    def test_a_metered_terminal_build_settles_on_what_was_used(self):
        bid = self.reserved_build(build_status='failed', attempts=[('ok', Decimal('0.30'), Decimal('0.12'))])
        result = self.reconcile()[bid]
        self.assertEqual((result['action'], result['applied']), ('settle', True))
        self.assertEqual(self.status(bid), 'SETTLED')
        with self.pool.connection() as conn:
            settled = conn.execute('SELECT settled_provider_cost_usd FROM credit_reservations WHERE build_id = %s',
                                   (bid,)).fetchone()[0]
        self.assertEqual(Decimal(str(settled)), Decimal('0.12'))

    def test_an_unknown_outcome_or_a_running_build_is_held(self):
        unknown = self.reserved_build(build_status='cancelled', attempts=[('unknown', Decimal('0.05'), None)])
        ok_unmetered = self.reserved_build(build_status='failed', attempts=[('ok', Decimal('0.05'), None)])
        running = self.reserved_build(build_status='running', attempts=[])
        out = self.reconcile()
        self.assertEqual(out[unknown]['action'], 'hold')
        self.assertEqual(out[ok_unmetered]['action'], 'hold')
        self.assertNotIn(running, out)                                     # not terminal: never a candidate
        for bid in (unknown, ok_unmetered, running):
            self.assertEqual(self.status(bid), 'RESERVED')

    def test_a_fresh_reservation_is_left_alone(self):
        bid = self.reserved_build(build_status='cancelled', attempts=[])
        with self.pool.connection() as conn:
            conn.execute("UPDATE credit_reservations SET created_at = now() WHERE build_id = %s", (bid,))
            conn.commit()
        self.assertNotIn(bid, self.reconcile())
        self.assertEqual(self.status(bid), 'RESERVED')


if __name__ == '__main__':
    unittest.main()
