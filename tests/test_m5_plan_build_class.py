"""CEO 2026-10-19: an M5 build's cost class is real, not a label.

The plan's class decides three things, each exercised here through the code
that enforces it:
  a. which models may run   -> RoutedModelGateway.restrict_to_cost_class (worker)
  b. the build's model budget -> pricing.m5_llm_budget (class cap, clipped to the
                                 60% margin floor; used by the M5 quote)
  c. the credits it costs   -> pricing.m5_build_terms (reserve())

MANDATORY (CEO): the same task costs less on Amateur than on Studio, and the
margin holds on all three paid tiers (worst case: the whole cap is spent).
Worst-case margin targets: Amateur 72%, Pro 63%, Studio 62%.
"""
import json
import pathlib
import unittest
from decimal import Decimal
from unittest.mock import patch

from omni_prod.pricing import (
    PLAN_CATALOG, CostClass, PlanCode, M5_BUILD_COST_CLASS, M5_CLASS_BUILD_CREDITS, _env_decimal_renamed,
    llm_overage, m5_build_cost_class, m5_build_terms, m5_class_llm_cap, m5_llm_budget, m5_model_allowed,
    m5_revenue_basis,
)
from omni_prod.subscription_store import PostgresSubscriptionService

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG = (ROOT / 'infra' / 'worker-host' / 'model-catalog.json').read_text(encoding='utf-8')
PAID = (PlanCode.AMATEUR, PlanCode.PRO, PlanCode.STUDIO)
WORST_CASE_MARGIN_TARGET = {PlanCode.AMATEUR: Decimal('0.72'), PlanCode.PRO: Decimal('0.63'),
                            PlanCode.STUDIO: Decimal('0.62')}
# One concrete task, identical for every tier (a codegen call of a mid-size build).
TASK = {'system': 'You write production code.', 'user': 'x' * 6000, 'max_tokens': 8000}


class _Cursor:
    """Minimal scripted cursor (same shape as tests/test_m5_build_economics.py)."""
    def __init__(self, rows):
        self.rows, self.calls, self.rowcount = list(rows), [], 1
    def execute(self, sql, params=None):
        self.calls.append((' '.join(sql.split()), params)); self.rowcount = 1
    def fetchone(self):
        return self.rows.pop(0) if self.rows else None


def _reserve(plan_value, cost_class, credits, estimate):
    svc = PostgresSubscriptionService(pool=None)
    cur = _Cursor([(plan_value, svc._cycle_now(), 0, Decimal('0')), None])
    return svc.reserve(cur, build_id='b1', user_id='u1', project_id='p1', cost_class=cost_class,
                       credits=credits, estimated_provider_cost_usd=estimate)


def _gateway():
    from omni_prod.model_catalog import load_model_catalog
    from omni_prod.routed_gateway import RoutedModelGateway
    env = {'OMNI_MODEL_CATALOG_JSON': CATALOG}
    for item in json.loads(CATALOG):
        env[item['api_key_env']] = 'test-placeholder-not-a-key'
    with patch.dict('os.environ', env, clear=False):
        return RoutedModelGateway(ranked=load_model_catalog(env))


def _cheapest_call_cost(gw, task='codegen'):
    routes = gw.ranked_routes(dict(TASK), task)
    return routes[0][0].max_estimated_cost_usd if routes else None


class DecisionMappingTests(unittest.TestCase):
    def test_every_plan_has_a_class_inside_its_allowance(self):
        expected = {PlanCode.FREE: CostClass.LIGHT, PlanCode.AMATEUR: CostClass.LIGHT, PlanCode.PRO: CostClass.STANDARD,
                    PlanCode.STUDIO: CostClass.HEAVY, PlanCode.ENTERPRISE: CostClass.EXTREME}
        self.assertEqual(M5_BUILD_COST_CLASS, expected)
        for code, cc in expected.items():
            self.assertIn(cc, PLAN_CATALOG[code].allowed_cost_classes, code)

    def test_credits_per_class_and_per_plan(self):
        self.assertEqual({k.value: v for k, v in M5_CLASS_BUILD_CREDITS.items()},
                         {'zero': 20, 'light': 45, 'standard': 200, 'advanced': 300, 'heavy': 500, 'extreme': 1200})
        self.assertEqual({c.value: PLAN_CATALOG[c].included_credits for c in (PlanCode.FREE, *PAID)},
                         {'free': 150, 'amateur': 1000, 'pro': 4500, 'studio': 10000})
        self.assertEqual(PLAN_CATALOG[PlanCode.FREE].included_credits // M5_CLASS_BUILD_CREDITS[CostClass.LIGHT], 3)

    def test_class_caps(self):
        caps = {cc.value: m5_class_llm_cap(cc) for cc in CostClass}
        self.assertEqual(caps, {'zero': Decimal('0.05'), 'light': Decimal('0.35'), 'standard': Decimal('1.60'),
                                'advanced': Decimal('3.00'), 'heavy': Decimal('5.50'), 'extreme': Decimal('18.00')})

    def test_cap_env_override_per_class(self):
        with patch.dict('os.environ', {'OMNI_BUILD_LLM_CAP_LIGHT_USD': '0.20'}):
            self.assertEqual(m5_class_llm_cap(CostClass.LIGHT), Decimal('0.20'))


class SameTaskTierTests(unittest.TestCase):
    """MANDATORY: the same task is cheaper on Amateur than on Studio; margin holds."""

    def setUp(self):
        self.terms = {code: m5_build_terms(code) for code in PAID}
        self.budget = {code: m5_llm_budget(PLAN_CATALOG[code], *self.terms[code])[0] for code in PAID}

    def test_amateur_costs_less_than_studio_for_the_same_task(self):
        a_cc, a_credits = self.terms[PlanCode.AMATEUR]
        s_cc, s_credits = self.terms[PlanCode.STUDIO]
        # (b) worst-case model spend the company can incur on the build
        self.assertLess(self.budget[PlanCode.AMATEUR], self.budget[PlanCode.STUDIO])
        # (c) credits the customer is charged for the build
        self.assertLess(a_credits, s_credits)
        # (a) the models the same task may run on
        amateur, studio = _gateway(), _gateway()
        amateur.restrict_to_cost_class(a_cc)
        studio.restrict_to_cost_class(s_cc)
        a_models = {m.endpoint.name for m in amateur.ranked}
        s_models = {m.endpoint.name for m in studio.ranked}
        self.assertTrue(a_models, 'Amateur must keep at least one routable model')
        self.assertTrue(a_models < s_models, (a_models, s_models))
        a_max = max(m.option.output_per_million for m in amateur.ranked)
        s_max = max(m.option.output_per_million for m in studio.ranked)
        self.assertLess(a_max, s_max)
        # cheapest admissible call for the same task never costs more on Amateur
        self.assertLessEqual(_cheapest_call_cost(amateur), _cheapest_call_cost(studio))

    def test_margin_holds_on_every_paid_tier_in_the_worst_case(self):
        for code in PAID:
            cc, credits = self.terms[code]
            revenue = m5_revenue_basis(PLAN_CATALOG[code], credits)
            margin = (revenue - self.budget[code]) / revenue
            self.assertGreaterEqual(margin, Decimal('0.60'), code)                       # floor
            self.assertGreaterEqual(margin, WORST_CASE_MARGIN_TARGET[code], (code, margin))   # CEO target

    def test_budget_is_clipped_never_refused_when_a_cap_breaks_the_floor(self):
        with patch.dict('os.environ', {'OMNI_BUILD_LLM_CAP_STANDARD_USD': '100'}):
            budget, basis = m5_llm_budget(PLAN_CATALOG[PlanCode.PRO], *m5_build_terms(PlanCode.PRO))
        revenue = m5_revenue_basis(PLAN_CATALOG[PlanCode.PRO], 200)
        self.assertEqual(basis, 'clipped_to_margin_floor')
        self.assertLessEqual(budget, revenue * Decimal('0.40'))

    def test_reserve_allows_a_full_budget_first_build_on_every_paid_tier(self):
        for code in PAID:
            cc, credits = self.terms[code]
            d = _reserve(code.value, cc.value, credits, self.budget[code])
            self.assertTrue(d.allowed, (code, d.reason))
            self.assertEqual(d.credits, credits)


class OtherPlanTests(unittest.TestCase):
    def test_free_can_run_a_paid_build_up_to_the_light_cap(self):
        # CEO 2026-10-19 02:22: Free is margin-floor exempt like Enterprise; the cap stays.
        cc, credits = m5_build_terms(PlanCode.FREE)
        self.assertEqual((cc, credits), (CostClass.LIGHT, 45))
        budget, basis = m5_llm_budget(PLAN_CATALOG[PlanCode.FREE], cc, credits)
        self.assertEqual((budget, basis), (Decimal('0.35'), 'class_cap'))
        d = _reserve('free', cc.value, credits, budget)
        self.assertTrue(d.allowed, d.reason)
        self.assertEqual(d.credits, 45)

    def test_free_cannot_exceed_the_light_cap_or_three_builds(self):
        self.assertFalse(_reserve('free', 'standard', 200, Decimal('0.35')).allowed)      # class lock
        plan = PLAN_CATALOG[PlanCode.FREE]
        self.assertEqual(plan.paid_provider_budget_usd, Decimal('1.05'))                  # 3 x $0.35 per month
        svc = PostgresSubscriptionService(pool=None)
        cur = _Cursor([('free', svc._cycle_now(), 135, Decimal('1.05')), None])          # after 3 builds
        d = svc.reserve(cur, build_id='b4', user_id='u1', project_id='p1', cost_class='light', credits=45,
                        estimated_provider_cost_usd=Decimal('0.35'))
        self.assertFalse(d.allowed)

    def test_enterprise_is_extreme_and_margin_exempt(self):
        cc, credits = m5_build_terms(PlanCode.ENTERPRISE)
        self.assertEqual((cc, credits), (CostClass.EXTREME, 1200))
        self.assertEqual(m5_llm_budget(PLAN_CATALOG[PlanCode.ENTERPRISE], cc, credits),
                         (Decimal('18.00'), 'class_cap'))

    def test_internal_qa_gets_the_plain_cap(self):
        self.assertEqual(m5_llm_budget(PLAN_CATALOG[PlanCode.FREE], CostClass.LIGHT, 45, internal_qa=True)[0],
                         Decimal('0.35'))

    def test_legacy_persisted_codes_reserve_as_their_new_plan(self):
        for legacy in ('basic', 'business'):
            cc, credits = m5_build_terms(legacy)
            budget, _ = m5_llm_budget(PLAN_CATALOG[PlanCode(legacy)], cc, credits)
            self.assertTrue(_reserve(legacy, cc.value, credits, budget).allowed, legacy)

    def test_old_hardcoded_standard_would_have_blocked_amateur(self):
        d = _reserve('amateur', CostClass.STANDARD.value, 60, Decimal('0.30'))
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, 'cost class not included in plan')


class AllowlistAndOverageTests(unittest.TestCase):
    def test_allowlist_thresholds(self):
        self.assertTrue(m5_model_allowed(CostClass.LIGHT, '1.50'))
        self.assertFalse(m5_model_allowed(CostClass.LIGHT, '1.51'))
        self.assertTrue(m5_model_allowed(CostClass.STANDARD, '10.00'))
        self.assertFalse(m5_model_allowed(CostClass.STANDARD, '10.01'))
        self.assertTrue(m5_model_allowed(CostClass.HEAVY, '50'))
        self.assertFalse(m5_model_allowed(CostClass.ZERO, '0.01'))

    def test_soft_cap_records_overage_and_alerts_above_2x(self):
        self.assertEqual(llm_overage('0.30', '0.35')['status'], 'WITHIN_CAP')
        self.assertEqual(llm_overage('0.50', '0.35')['status'], 'OVER_CAP')
        self.assertEqual(llm_overage('0.71', '0.35')['status'], 'OVER_2X_CAP')


class RenamedEnvFallbackTests(unittest.TestCase):
    def test_new_name_wins(self):
        with patch.dict('os.environ', {'OMNI_PRICE_AMATEUR_USD': '31', 'OMNI_PRICE_BASIC_USD': '12'}):
            self.assertEqual(_env_decimal_renamed('OMNI_PRICE_AMATEUR_USD', 'OMNI_PRICE_BASIC_USD', '29'), Decimal('31'))

    def test_legacy_name_is_still_read(self):
        import os
        with patch.dict('os.environ', {'OMNI_PRICE_BASIC_USD': '12'}, clear=False):
            os.environ.pop('OMNI_PRICE_AMATEUR_USD', None)
            self.assertEqual(_env_decimal_renamed('OMNI_PRICE_AMATEUR_USD', 'OMNI_PRICE_BASIC_USD', '29'), Decimal('12'))

    def test_default_when_neither_set(self):
        import os
        with patch.dict('os.environ', {}, clear=False):
            os.environ.pop('OMNI_PRICE_STUDIO_USD', None); os.environ.pop('OMNI_PRICE_BUSINESS_USD', None)
            self.assertEqual(_env_decimal_renamed('OMNI_PRICE_STUDIO_USD', 'OMNI_PRICE_BUSINESS_USD', '299'), Decimal('299'))


if __name__ == '__main__':
    unittest.main()
