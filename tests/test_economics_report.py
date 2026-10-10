"""Unit economics from the ledgers (issue #6 P3): unknown stays unknown."""
import unittest
from decimal import Decimal

from omni_prod.economics_report import compute


def b(i, status, day='2026-10-09', user='u1', seconds=300):
    return {'id': i, 'status': status, 'funding': 'internal_qa', 'user': user, 'day': day, 'seconds': seconds,
            'repairs': 1, 'settled': None, 'cost_basis': None}


def a(build, task='codegen', metered='0.05', outcome='ok', authorized='0.10', model='gemini-3.8-flash'):
    return {'build_id': build, 'task_type': task, 'model': model, 'outcome': outcome,
            'metered': None if metered is None else Decimal(metered), 'authorized': Decimal(authorized)}


class EconomicsTests(unittest.TestCase):
    def setUp(self):
        builds = [b('b1', 'ready'), b('b2', 'failed'), b('b3', 'ready', seconds=600), b('b4', 'cancelled')]
        attempts = [a('b1'), a('b1', task='repair', metered='0.02'),
                    a('b2', metered='0.08'), a('b2', task='repair', metered='0.04', model='gemini-3.1-flash-lite'),
                    a('b3'), a('b3', metered=None, outcome='unknown', authorized='0.09')]   # crash: in flight
        self.r = compute(builds, attempts)

    def test_outcomes_and_success_rate_exclude_cancelled(self):
        self.assertEqual(self.r['outcomes'], {'ready': 2, 'failed': 1, 'cancelled': 0})
        self.assertEqual(self.r['success_rate'], round(2 / 3, 3))

    def test_unknown_cost_is_exposure_not_zero(self):
        self.assertEqual(self.r['unknown_cost_builds'], 1)
        self.assertEqual(Decimal(self.r['unknown_exposure_usd']), Decimal('0.09'))
        # b3's cost is unknown, so it is excluded from the per-build cost statistics
        self.assertEqual(Decimal(self.r['cost_per_build_p50_usd']), Decimal('0.07'))

    def test_failed_builds_and_repairs_are_costed(self):
        self.assertEqual(Decimal(self.r['failed_build_cost_usd']), Decimal('0.12'))
        self.assertEqual(Decimal(self.r['metered_total_usd']), Decimal('0.24'))
        self.assertEqual(Decimal(self.r['repair_share_of_spend']), Decimal('0.25'))
        # all metered spend (incl. failures) over successful builds
        self.assertEqual(Decimal(self.r['cost_per_successful_build_usd']), Decimal('0.12'))

    def test_margin_and_reconciliation_are_not_invented(self):
        self.assertTrue(self.r['contribution_margin'].startswith('UNKNOWN'))
        self.assertTrue(self.r['invoice_reconciliation'].startswith('BLOCKED'))

    def test_models_report_success_and_spend(self):
        m = self.r['models']['gemini-3.8-flash']
        self.assertEqual((m['calls'], m['ok'], m['unknown']), (5, 4, 1))


if __name__ == '__main__':
    unittest.main()
