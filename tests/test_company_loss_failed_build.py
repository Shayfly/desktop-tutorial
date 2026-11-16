"""Warehouse 103 (released by the owner 2026-11-15): the provider cost of a build that FAILED is a row in
company_loss_events -- the customer is refunded in full, the provider was paid, the money is ours to account for.

Offline part: the ledger writer with a recording cursor (the exact INSERT and its parameters), the cause registry, the
migration text, the rollback file and the staging bootstrap in sync. The real path -- release_failed() on PostgreSQL
writing the row inside the refund's transaction -- is tests/test_company_loss_failed_build_pg.py (intake-budget-pg).
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import unittest
from decimal import Decimal

from omni_prod import company_loss as L

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIGRATION = ROOT / 'infra' / 'postgres' / '044_company_loss_failed_build.sql'
ROLLBACK = ROOT / 'infra' / 'postgres' / 'rollback' / '044_company_loss_failed_build.down.sql'
COST = Decimal('1.403646')       # the measured cost of the failed butcher-account build bld_cf406df6 (2026-11-12)


class RecordingCursor:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))


class TheLedgerWriter(unittest.TestCase):
    def test_a_failed_build_with_a_provider_cost_is_one_loss_row_for_the_whole_cost(self):
        cur = RecordingCursor()
        loss = L.record_failed_build(cur, build_id='bld_x', account_id='usr_a', project_id='prj_p', actual_usd=COST,
                                     funding_source='plan', truth='computed')
        self.assertEqual(loss, COST)
        [(sql, params)] = cur.calls
        self.assertIn('INSERT INTO company_loss_events', sql)
        self.assertIn('ON CONFLICT (source, idempotency_key) DO NOTHING', sql)
        source, key, build_id, reservation_id, account_id, project_id, lane, provider, model, quoted, actual, overrun, cause, evidence = params
        self.assertEqual((source, key, build_id, account_id, project_id), ('release_failed', 'failed-build:bld_x', 'bld_x', 'usr_a', 'prj_p'))
        self.assertEqual((quoted, actual, overrun, cause), (Decimal('0'), COST, COST, 'failed_build_refunded'))
        self.assertIn('"funding_source": "plan"', evidence)

    def test_a_failed_build_without_a_provider_cost_writes_nothing(self):
        cur = RecordingCursor()
        self.assertIsNone(L.record_failed_build(cur, build_id='bld_free', account_id='u', project_id='p', actual_usd=0,
                                                funding_source='plan', truth='reported'))
        self.assertEqual(cur.calls, [])

    def test_the_cause_is_in_the_closed_set_and_the_migration_declares_it(self):
        self.assertIn('failed_build_refunded', L.CAUSES)
        self.assertEqual(L.FAILED_BUILD_REFUNDED, 'failed_build_refunded')
        text = MIGRATION.read_text(encoding='utf-8')
        self.assertIn("ADD CONSTRAINT company_loss_events_cause_known", text)
        for cause in L.CAUSES:
            self.assertIn(f"'{cause}'", text)
        self.assertTrue(ROLLBACK.exists())
        self.assertIn("'failed_build_refunded'", ROLLBACK.read_text(encoding='utf-8'))

    def test_the_staging_bootstrap_carries_the_migration(self):
        check = subprocess.run([sys.executable, str(ROOT / 'tools' / 'generate_neon_bootstrap.py'), '--check'],
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn('044_company_loss_failed_build', (ROOT / 'infra' / 'staging' / 'bootstrap_neon_empty.sql').read_text(encoding='utf-8'))

    def test_release_failed_writes_the_row_inside_the_refund_transaction(self):
        # a guard on the call site; the behaviour itself runs on PostgreSQL in test_company_loss_failed_build_pg.py
        text = (ROOT / 'omni_prod' / 'subscription_store.py').read_text(encoding='utf-8')
        body = text[text.index('def release_failed('):text.index('def release(')]
        self.assertRegex(body, r"record_failed_build\(cur, build_id=build_id, account_id=user_id, project_id=row\[5\], actual_usd=basis")
        self.assertLess(body.index('record_failed_build('), body.index("if row[4] == 'internal_qa'"),
                        'internal-QA builds are recorded too: the money left either way')


if __name__ == '__main__':
    unittest.main()
