"""Warehouse 103 (released by the owner 2026-11-15), on real PostgreSQL: release_failed() writes the provider cost of a
failed build to company_loss_events, in the same transaction as the refund.

Measured 2026-10-27 -> 2026-11-13: 20 of 29 builds with a provider cost FAILED. Their cost stayed on the reservation
(settled_provider_cost_usd) and in the plan meter (#356), but never reached the loss ledger, so "how much did we lose on
failed builds" had no durable answer. Runs in intake-budget-pg (skipped elsewhere without M4D2_DATABASE_URL)."""
from __future__ import annotations

import json
import os
import pathlib
import unittest
import uuid
from decimal import Decimal

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
COST = Decimal('1.403646')       # the measured cost of the failed butcher-account build bld_cf406df6 (2026-11-12)


class FailedBuildsAreLossRows(unittest.TestCase):
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
        cls.dbname = f'clf_{uuid.uuid4().hex[:10]}'
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

    def reserve(self, funding_source=None):
        build_id = f'bld_{uuid.uuid4().hex}'
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    kw = {'internal_qa': True} if funding_source == 'internal_qa' else {}
                    d = self.subs.reserve(cur, build_id=build_id, user_id=self.user, project_id='prj_k', cost_class='standard',
                                          credits=500, estimated_provider_cost_usd=Decimal('2.003'), **kw)
                    self.assertTrue(d.allowed, d.reason)
        return build_id

    def rows(self, build_id):
        with self.pool.connection() as conn:
            return conn.execute('SELECT source, idempotency_key, account_id, project_id, quoted_usd, actual_usd, overrun_usd, '
                                'cause, evidence FROM company_loss_events WHERE build_id=%s', (build_id,)).fetchall()

    def test_a_failed_build_with_a_cost_is_one_loss_row_for_the_whole_cost(self):
        bid = self.reserve()
        out = self.subs.release_failed(build_id=bid, actual_provider_cost_usd=None, computed_provider_cost_usd=COST)
        self.assertEqual(out['credits_refunded'], 500)
        [row] = self.rows(bid)
        source, key, account, project, quoted, actual, overrun, cause, evidence = row
        self.assertEqual((source, key, account, project, cause), ('release_failed', f'failed-build:{bid}', self.user, 'prj_k', 'failed_build_refunded'))
        self.assertEqual((Decimal(str(quoted)), Decimal(str(actual)), Decimal(str(overrun))), (Decimal('0'), COST, COST))
        ev = evidence if isinstance(evidence, dict) else json.loads(evidence)
        self.assertEqual(ev['provider_cost_truth'], 'COMPUTED_FROM_USAGE')     # subscription_store._basis's own name
        self.assertTrue(out['loss_recorded'])
        # a retry changes nothing twice: the reservation is already RELEASED and the row is idempotent
        self.assertIsNone(self.subs.release_failed(build_id=bid, computed_provider_cost_usd=COST))
        self.assertEqual(len(self.rows(bid)), 1)

    def test_the_loss_ledger_equals_the_failed_builds_provider_cost(self):
        bids = [self.reserve() for _ in range(3)]
        for bid in bids:
            self.subs.release_failed(build_id=bid, computed_provider_cost_usd=COST)
        with self.pool.connection() as conn:
            losses = Decimal(str(conn.execute("SELECT COALESCE(SUM(overrun_usd),0) FROM company_loss_events WHERE account_id=%s "
                                              "AND cause='failed_build_refunded'", (self.user,)).fetchone()[0]))
            settled = Decimal(str(conn.execute("SELECT COALESCE(SUM(settled_provider_cost_usd),0) FROM credit_reservations "
                                               "WHERE account_id=%s AND status='RELEASED'", (self.user,)).fetchone()[0]))
        self.assertEqual(losses, COST * 3)
        self.assertEqual(losses, settled)                       # acceptance 103.2: the ledger equals the attempts' spend
        from omni_prod.company_loss import rollup
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                grouped = rollup(cur)['by_cause']['failed_build_refunded']
        # the roll-up is for the whole database (other tests of this class wrote rows too): at least this account's
        self.assertGreaterEqual(grouped['events'], 3)
        self.assertGreaterEqual(Decimal(grouped['loss_usd']), COST * 3)
        from tests.evidence_notice import notice
        notice('failed builds are loss rows', f'3 failed builds at {COST}: company_loss_events sum {losses} = settled {settled}')

    def test_a_failed_build_without_a_cost_writes_no_loss(self):
        bid = self.reserve()
        out = self.subs.release_failed(build_id=bid, actual_provider_cost_usd=Decimal('0'), computed_provider_cost_usd=Decimal('0'))
        self.assertEqual(self.rows(bid), [])
        self.assertFalse(out['loss_recorded'])

    def test_nothing_measured_writes_no_loss_the_ledger_never_records_an_estimate(self):
        # no actual, no computed usage: the basis is the reservation's estimate (CONSERVATIVE_RESERVATION)
        bid = self.reserve()
        out = self.subs.release_failed(build_id=bid, actual_provider_cost_usd=None, computed_provider_cost_usd=None)
        self.assertEqual(out['provider_cost_truth'], 'CONSERVATIVE_RESERVATION')
        self.assertEqual(Decimal(out['provider_cost_basis_usd']), Decimal('2.003'))   # kept on the reservation (numeric scale varies)
        self.assertFalse(out['loss_recorded'])
        self.assertEqual(self.rows(bid), [])

    def test_an_internal_qa_build_is_recorded_with_its_funding_source(self):
        bid = self.reserve(funding_source='internal_qa')
        out = self.subs.release_failed(build_id=bid, computed_provider_cost_usd=COST)
        self.assertEqual(out['funding_source'], 'internal_qa')
        [row] = self.rows(bid)
        ev = row[8] if isinstance(row[8], dict) else json.loads(row[8])
        self.assertEqual(ev['funding_source'], 'internal_qa')
        self.assertEqual(Decimal(str(row[6])), COST)


if __name__ == '__main__':
    unittest.main()
