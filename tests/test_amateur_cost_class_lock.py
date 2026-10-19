"""CEO decision 2026-10-19: Amateur is locked to economy/light cost classes;
STANDARD and above start at Pro. Without it Amateur ($29, 86.8% margin,
~$2.48/month AI budget) goes negative after ~3 standard builds
(docs/PRICING.md).

Code mapping of "economy/light": CostClass.ZERO + CostClass.LIGHT.
Amateur is the renamed Basic tier (docs/PLANS.md); it is located by its
display name so the test holds whether or not PlanCode is renamed.

Expected RED on main @ 1f744ae: the tier is still named "Basic" and allows
STANDARD (omni_prod/pricing.py:112-118).
"""
import unittest

from omni_prod.pricing import PLAN_CATALOG, CostClass, PlanCode

ALLOWED_AMATEUR = {CostClass.ZERO, CostClass.LIGHT}
STANDARD_AND_ABOVE = {CostClass.STANDARD, CostClass.ADVANCED, CostClass.HEAVY, CostClass.EXTREME}


def _by_name(name):
    hits = [p for p in PLAN_CATALOG.values() if p.name == name]
    return hits[0] if hits else None


class AmateurCostClassLockTests(unittest.TestCase):
    def test_amateur_tier_exists(self):
        self.assertIsNotNone(_by_name('Amateur'), 'no plan named "Amateur" in PLAN_CATALOG')

    def test_amateur_allows_only_zero_and_light(self):
        plan = _by_name('Amateur')
        self.assertIsNotNone(plan, 'no plan named "Amateur"')
        self.assertEqual(set(plan.allowed_cost_classes), ALLOWED_AMATEUR)

    def test_amateur_cannot_use_standard_or_above(self):
        plan = _by_name('Amateur')
        self.assertIsNotNone(plan, 'no plan named "Amateur"')
        self.assertFalse(set(plan.allowed_cost_classes) & STANDARD_AND_ABOVE)

    def test_standard_starts_at_pro(self):
        self.assertIn(CostClass.STANDARD, PLAN_CATALOG[PlanCode.PRO].allowed_cost_classes)

    def test_free_is_zero_and_light(self):
        # CEO 2026-10-19 (later decision): Free = ZERO + LIGHT, 150 credits.
        self.assertEqual(set(PLAN_CATALOG[PlanCode.FREE].allowed_cost_classes), {CostClass.ZERO, CostClass.LIGHT})


if __name__ == '__main__':
    unittest.main()
