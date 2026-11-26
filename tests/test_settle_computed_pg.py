"""Michael 2026-11-14 (b1), on real PostgreSQL with the production rows: a build whose actual cost is unknown is
settled at computed_from_usage, not at the whole reservation estimate.

Fixture: tests/fixtures/settlement_unknown_actual_2026_11.json -- three of the four builds of the founder account
(Studio) that were settled at ~$2.00 while the measured cost was $0.48-$1.55; their task_attempts, image usage events
and gateway spend, exactly as stored. The fourth (bld_5a37...) is the same case as bld_0909 (image without price).
The worker's own settlement function runs (worker_tasks.resolve_m5_billing) against the real subscription store.
Runs in intake-budget-pg (skipped elsewhere without M4D2_DATABASE_URL)."""
from __future__ import annotations

import json
import os
import pathlib
import unittest
import uuid
from decimal import Decimal
from types import SimpleNamespace

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
FIXTURE = pathlib.Path(__file__).resolve().parent / 'fixtures' / 'settlement_unknown_actual_2026_11.json'
BUILDS = {b['build_id']: b for b in json.loads(FIXTURE.read_text())['builds']}
IMAGE_UNPRICED = 'bld_0909524012764f29a578174ec7df4e91'     # model calls metered, image has no reported price
USAGE_UNREPORTED = 'bld_b90585c0ebf245d2953b82f30f0a8af8'   # one model call without reported usage
FAILED = 'bld_cf406df69b4b453eafaeb3a1c11d8412'             # failed build: released, cost kept on record


def gateway(build):
    records = [SimpleNamespace(kind='provider_call', authorized_cost_usd=Decimal(a['authorized_cost_usd']),
                               metered_cost_usd=None if a['metered_cost_usd'] is None else Decimal(a['metered_cost_usd']),
                               price_catalog_version=a['price_catalog_version']) for a in build['attempts']]
    return SimpleNamespace(recorder=SimpleNamespace(records=records), usage=None,
                           state=SimpleNamespace(external_spend_usd=Decimal(build['provider_spend_usd']),
                                                 external_calls=build['external_calls']))


class SettleAtComputedCost(unittest.TestCase):
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
        cls.dbname = f'stl_{uuid.uuid4().hex[:10]}'
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

    def row(self, build_id):
        with self.pool.connection() as conn:
            r = conn.execute('SELECT status, actual_provider_cost_usd, settled_provider_cost_usd FROM credit_reservations '
                             'WHERE build_id=%s', (build_id,)).fetchone()
            s = conn.execute('SELECT provider_spend_usd FROM creator_subscriptions WHERE user_id=%s', (self.user,)).fetchone()
        return r[0], r[1], Decimal(str(r[2])), Decimal(str(s[0]))

    def run_build(self, name):
        from omni_prod import worker_tasks
        b = BUILDS[name]
        build_id = f"{name}_{uuid.uuid4().hex[:6]}"
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    d = self.subs.reserve(cur, build_id=build_id, user_id=self.user, project_id='k', cost_class='standard',
                                          credits=500, estimated_provider_cost_usd=Decimal(b['estimate']))
                    self.assertTrue(d.allowed, d.reason)
        billing, evidence, actual = worker_tasks.resolve_m5_billing(
            self.subs, build_id=build_id, ready=b['ready'], gateway=gateway(b),
            capability_evidence={'usage': b['capability_usage']}, economics_quote={'infrastructure_maximum_usd': '0'})
        return build_id, billing, evidence, actual

    def check(self, name, status):
        b = BUILDS[name]
        build_id, billing, evidence, actual = self.run_build(name)
        got_status, stored_actual, settled, spend = self.row(build_id)
        self.assertEqual(got_status, status)
        self.assertIsNone(actual)                       # computed is never relabelled as actual
        self.assertIsNone(stored_actual)
        self.assertEqual(settled, Decimal(b['settled_after']))
        # #356: a failed build (the first of the month here) is not counted against the plan budget
        self.assertEqual(spend, Decimal(b['settled_after']) if status == 'SETTLED' else Decimal('0'))
        self.assertEqual(evidence['provider_cost_truth'], 'COMPUTED_FROM_USAGE')
        self.assertEqual(evidence['cost_basis']['settlement']['basis'], 'computed_from_usage')
        from tests.evidence_notice import notice
        notice('settle computed', f"{name}: reserved {b['estimate']}, settled {settled} (was {b['settled_before']} "
                                  f"in production), actual NULL, plan meter {spend}")

    def test_an_unpriced_image_no_longer_settles_the_whole_estimate(self):
        self.check(IMAGE_UNPRICED, 'SETTLED')

    def test_unreported_usage_settles_at_the_gateway_ledger(self):
        self.check(USAGE_UNREPORTED, 'SETTLED')

    def test_a_failed_build_keeps_the_computed_cost_not_the_estimate(self):
        self.check(FAILED, 'RELEASED')

    def test_no_number_at_all_settles_at_the_reservation_loudly(self):
        # The owner 2026-11-26: an image with NO number (no price configured) is no longer settled at the whole
        # reservation -- that recorded the reservation as the build's cost. It is left out of the measured sum and
        # named (cost_data_missing); the reservation remains only for liability that cannot be bounded (below).
        b = dict(BUILDS[IMAGE_UNPRICED])
        b['capability_usage'] = [{**b['capability_usage'][0], 'estimated_cost_usd': None, 'maximum_cost_usd': None}]
        BUILDS['no_number'] = b
        try:
            build_id, _, evidence, _ = self.run_build('no_number')
        finally:
            del BUILDS['no_number']
        _, _, settled, _ = self.row(build_id)
        self.assertLess(settled, Decimal(b['estimate']))
        self.assertEqual(evidence['provider_cost_truth'], 'COMPUTED_FROM_USAGE')
        self.assertEqual(evidence['cost_basis']['settlement']['cost_data_missing'], ['capability:cap-media-image-generate'])
        self.assertFalse(evidence['cost_record']['complete'])

    def test_an_earlier_call_without_exposure_settles_at_the_reservation_loudly(self):
        b = dict(BUILDS[IMAGE_UNPRICED])
        BUILDS['lost_worker'] = b
        try:
            g = gateway(b)
            g.prior_metered = {'calls': 1, 'metered_usd': Decimal('0'), 'unknown_calls': 1,
                               'unknown_exposure_usd': Decimal('0')}
            with self.assertLogs('omni_prod.worker_tasks', level='ERROR') as logs:
                from omni_prod import worker_tasks
                build_id = f"lost_{uuid.uuid4().hex[:6]}"
                with self.pool.connection() as conn:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            self.subs.reserve(cur, build_id=build_id, user_id=self.user, project_id='k',
                                              cost_class='standard', credits=500,
                                              estimated_provider_cost_usd=Decimal(b['estimate']))
                _, evidence, _ = worker_tasks.resolve_m5_billing(
                    self.subs, build_id=build_id, ready=b['ready'], gateway=g,
                    capability_evidence={'usage': b['capability_usage']},
                    economics_quote={'infrastructure_maximum_usd': '0'})
        finally:
            del BUILDS['lost_worker']
        _, _, settled, _ = self.row(build_id)
        self.assertEqual(settled, Decimal(b['estimate']))
        self.assertEqual(evidence['provider_cost_truth'], 'CONSERVATIVE_RESERVATION')
        self.assertEqual(evidence['cost_basis']['settlement']['missing'], ['earlier_worker_unknown_call_without_exposure'])
        self.assertIn('SETTLEMENT_WITHOUT_MEASUREMENT', ' '.join(logs.output))


if __name__ == '__main__':
    unittest.main()
