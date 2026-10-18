"""CEO 2026-10-19: an M5 build reserves under its plan's own cost class, so
reserve() never refuses a legitimate build after the Amateur/Pro/Studio
cost-class locks (Amateur LIGHT, Pro STANDARD, Studio HEAVY).

Also: renamed price env vars still honour the pre-rename names.
"""
import unittest
from decimal import Decimal
from unittest.mock import patch

from omni_prod.pricing import (
    PLAN_CATALOG, CostClass, PlanCode, M5_BUILD_COST_CLASS, _env_decimal_renamed, m5_build_cost_class,
)
from omni_prod.subscription_store import PostgresSubscriptionService

M5_BUILD_CREDITS = 60          # investor_app._M5_BUILD_CREDITS
TYPICAL_BUILD_ESTIMATE = Decimal('0.50')   # within every paid plan's margin-floor ceiling (~$0.60-0.77)


class _Cursor:
    """Minimal scripted cursor (same shape as tests/test_m5_build_economics.py)."""
    def __init__(self, rows):
        self.rows, self.calls, self.rowcount = list(rows), [], 1
    def execute(self, sql, params=None):
        self.calls.append((' '.join(sql.split()), params)); self.rowcount = 1
    def fetchone(self):
        return self.rows.pop(0) if self.rows else None


def _reserve(plan_value, cost_class):
    svc = PostgresSubscriptionService(pool=None)
    cur = _Cursor([(plan_value, svc._cycle_now(), 0, Decimal('0')), None])
    return svc.reserve(cur, build_id='b1', user_id='u1', project_id='p1', cost_class=cost_class,
                       credits=M5_BUILD_CREDITS, estimated_provider_cost_usd=TYPICAL_BUILD_ESTIMATE), cur


class PlanBuildClassTests(unittest.TestCase):
    def test_mapping_matches_decision(self):
        self.assertEqual(m5_build_cost_class(PlanCode.AMATEUR), CostClass.LIGHT)
        self.assertEqual(m5_build_cost_class(PlanCode.PRO), CostClass.STANDARD)
        self.assertEqual(m5_build_cost_class(PlanCode.STUDIO), CostClass.HEAVY)

    def test_build_class_is_allowed_by_its_plan(self):
        for code, cc in M5_BUILD_COST_CLASS.items():
            self.assertIn(cc, PLAN_CATALOG[code].allowed_cost_classes, code)

    def test_reserve_allows_first_build_on_every_paid_plan(self):
        for code in (PlanCode.AMATEUR, PlanCode.PRO, PlanCode.STUDIO):
            decision, cur = _reserve(code.value, m5_build_cost_class(code).value)
            self.assertTrue(decision.allowed, (code, decision.reason))
            self.assertTrue(any('INSERT INTO credit_reservations' in sql for sql, _ in cur.calls), code)

    def test_reserve_allows_legacy_persisted_plan_codes(self):
        # Subscriptions written before the rename still say 'basic' / 'business'.
        for legacy in ('basic', 'business'):
            code = PlanCode(legacy)
            decision, _ = _reserve(legacy, m5_build_cost_class(legacy).value)
            self.assertTrue(decision.allowed, (legacy, code, decision.reason))

    def test_old_hardcoded_standard_would_have_blocked_amateur(self):
        # Regression guard for the bug this change fixes (investor_app.py:2269).
        decision, _ = _reserve('amateur', CostClass.STANDARD.value)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, 'cost class not included in plan')

    def test_unlisted_plans_keep_standard(self):
        self.assertEqual(m5_build_cost_class(PlanCode.FREE), CostClass.STANDARD)
        self.assertEqual(m5_build_cost_class(PlanCode.ENTERPRISE), CostClass.STANDARD)


class RenamedEnvFallbackTests(unittest.TestCase):
    def test_new_name_wins(self):
        with patch.dict('os.environ', {'OMNI_PRICE_AMATEUR_USD': '31', 'OMNI_PRICE_BASIC_USD': '12'}):
            self.assertEqual(_env_decimal_renamed('OMNI_PRICE_AMATEUR_USD', 'OMNI_PRICE_BASIC_USD', '29'), Decimal('31'))

    def test_legacy_name_is_still_read(self):
        with patch.dict('os.environ', {'OMNI_PRICE_BASIC_USD': '12'}, clear=False):
            import os
            os.environ.pop('OMNI_PRICE_AMATEUR_USD', None)
            self.assertEqual(_env_decimal_renamed('OMNI_PRICE_AMATEUR_USD', 'OMNI_PRICE_BASIC_USD', '29'), Decimal('12'))

    def test_default_when_neither_set(self):
        import os
        with patch.dict('os.environ', {}, clear=False):
            os.environ.pop('OMNI_PRICE_STUDIO_USD', None); os.environ.pop('OMNI_PRICE_BUSINESS_USD', None)
            self.assertEqual(_env_decimal_renamed('OMNI_PRICE_STUDIO_USD', 'OMNI_PRICE_BUSINESS_USD', '299'), Decimal('299'))


if __name__ == '__main__':
    unittest.main()
