"""Founder 2026-10-22: LIGHT codegen uses its available quality-70 model and existing price ceiling.
Other cost classes retain mandatory 85 on codegen, including configured routes; unknown quality stays blocked.
"""
import unittest
from decimal import Decimal

from omni_prod.pricing import M5_BUILD_COST_CLASS, CostClass, m5_model_allowed
from tests.test_m5_plan_build_class import TASK, _gateway

OTHER_TASKS = ('repair', 'modification', 'architecture', 'review', 'classification', 'conversation', 'general')


def routes(cost_class, task):
    gw = _gateway()
    gw.restrict_to_cost_class(cost_class)
    return [(option.model, option.quality) for _, _, option in gw.ranked_routes(dict(TASK), task)]


def before_t5(cost_class, task):
    """The same router with the class list only (no task allowance): what each task had before."""
    gw = _gateway()
    gw.restrict_to_cost_class(cost_class)
    gw.task_extra_ranked = {}
    return [(option.model, option.quality) for _, _, option in gw.ranked_routes(dict(TASK), task)]


class CodegenHasARouteInEveryCostClass(unittest.TestCase):
    def test_every_class_a_plan_uses_has_codegen_at_its_decided_floor(self):
        for cc in sorted(set(M5_BUILD_COST_CLASS.values()) | {CostClass.ADVANCED}, key=lambda c: c.value):
            with self.subTest(cost_class=cc.value):
                r = routes(cc, 'codegen')
                self.assertTrue(r, f'{cc.value}: no codegen route')
                self.assertTrue(all(q >= (70 if cc == CostClass.LIGHT else 85) for _, q in r), r)              # the floor is mandatory, no escalation below

    def test_light_codegen_uses_its_available_quality_70_model(self):
        self.assertEqual(routes(CostClass.LIGHT, 'codegen'), [('gemini-3.1-flash-lite', 70)])

    def test_the_zero_class_has_no_external_route_for_any_task_by_design(self):
        # ZERO is the $0 class (no plan maps to it): no external model at all, for codegen or anything else.
        self.assertNotIn(CostClass.ZERO, set(M5_BUILD_COST_CLASS.values()))
        for task in ('codegen',) + OTHER_TASKS:
            self.assertEqual(routes(CostClass.ZERO, task), [], task)


class OnlyCodegenChangesInLight(unittest.TestCase):
    def test_every_other_task_in_light_routes_exactly_as_before(self):
        for task in OTHER_TASKS:
            with self.subTest(task=task):
                self.assertEqual(routes(CostClass.LIGHT, task), before_t5(CostClass.LIGHT, task))
                self.assertNotIn('gemini-3.8-flash', [m for m, _ in routes(CostClass.LIGHT, task)])

    def test_light_has_no_special_price_allowance_for_codegen(self):
        self.assertFalse(m5_model_allowed(CostClass.LIGHT, Decimal('3.75'), 'codegen'))
        self.assertFalse(m5_model_allowed(CostClass.LIGHT, Decimal('3.75'), 'repair'))
        self.assertFalse(m5_model_allowed(CostClass.LIGHT, Decimal('3.75')))
        self.assertFalse(m5_model_allowed(CostClass.LIGHT, Decimal('10.00'), 'codegen'))   # sol / sonnet stay out

    def test_other_classes_are_unchanged(self):
        for cc in (CostClass.STANDARD, CostClass.ADVANCED, CostClass.HEAVY, CostClass.EXTREME):
            for task in ('codegen',) + OTHER_TASKS:
                with self.subTest(cost_class=cc.value, task=task):
                    self.assertEqual(routes(cc, task), before_t5(cc, task))

    def test_luna_never_writes_code_in_any_class(self):
        for cc in CostClass:
            self.assertNotIn('gpt-6-luna', [m for m, _ in routes(cc, 'codegen')])


class LightConfiguredRoutes(unittest.TestCase):
    def test_declared_quality_70_primary_writes_only_in_light(self):
        from tests.test_t5_configured_routes_quality_floor import gateway, endpoint, CALL
        from omni_prod.routed_gateway import ProviderRoute
        from omni_prod.model_gateway import ModelGatewayError
        for cc in (CostClass.LIGHT, CostClass.STANDARD, CostClass.ADVANCED, CostClass.HEAVY, CostClass.EXTREME):
            with self.subTest(cost_class=cc.value):
                gw, contacted = gateway(primary=ProviderRoute(endpoint('local', 'local-coder', False), declared_quality=70))
                gw.restrict_to_cost_class(cc)
                if cc == CostClass.LIGHT:
                    self.assertEqual(gw.complete_json(task='codegen', **CALL), {'ok': 'local'})
                    self.assertEqual(contacted, ['local'])
                else:
                    with self.assertRaises(ModelGatewayError):
                        gw.complete_json(task='codegen', **CALL)
                    self.assertEqual(contacted, [])

    def test_declared_quality_70_fallback_is_contacted_only_in_light(self):
        from tests.test_t5_configured_routes_quality_floor import gateway, endpoint, CALL
        from omni_prod.routed_gateway import ProviderRoute
        from omni_prod.model_gateway import ModelGatewayError
        for cc in (CostClass.LIGHT, CostClass.STANDARD):
            with self.subTest(cost_class=cc.value):
                gw, contacted = gateway(fallback=[ProviderRoute(endpoint('fallback', 'weak'), Decimal('0.05'),
                                                               declared_quality=70)])
                gw.restrict_to_cost_class(cc)
                if cc == CostClass.LIGHT:
                    self.assertEqual(gw.complete_json(task='codegen', **CALL), {'ok': 'fallback'})
                    self.assertEqual(contacted, ['fallback'])
                else:
                    with self.assertRaises(ModelGatewayError):
                        gw.complete_json(task='codegen', **CALL)
                    self.assertEqual(contacted, [])

    def test_unknown_quality_primary_stays_blocked_in_light(self):
        from tests.test_t5_configured_routes_quality_floor import gateway, endpoint, CALL
        from omni_prod.routed_gateway import ProviderRoute
        from omni_prod.model_gateway import ModelGatewayError
        gw, contacted = gateway(primary=ProviderRoute(endpoint('local', 'unknown', False)))
        gw.restrict_to_cost_class(CostClass.LIGHT)
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(task='codegen', **CALL)
        self.assertEqual(contacted, [])


if __name__ == '__main__':
    unittest.main()
