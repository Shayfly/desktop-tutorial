"""T5 (founder 2026-10-21/22): codegen's floor 85 is mandatory, AND every cost class has a codegen route.

The REAL deployed catalog (infra/worker-host/model-catalog.json) and the REAL router decide. LIGHT (Free, Amateur)
admits no model of quality 85 by its price cap, so it gets gemini-3.8-flash FOR CODEGEN ONLY; every other task in
LIGHT routes exactly as before (the cost of the other stages does not change).
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
    def test_every_class_a_plan_uses_has_codegen_at_85_or_more(self):
        for cc in sorted(set(M5_BUILD_COST_CLASS.values()) | {CostClass.ADVANCED}, key=lambda c: c.value):
            with self.subTest(cost_class=cc.value):
                r = routes(cc, 'codegen')
                self.assertTrue(r, f'{cc.value}: no codegen route')
                self.assertTrue(all(q >= 85 for _, q in r), r)              # the floor is mandatory, no escalation below

    def test_light_codegen_is_flash_3_8_and_nothing_else(self):
        self.assertEqual(routes(CostClass.LIGHT, 'codegen'), [('gemini-3.8-flash', 85)])

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

    def test_the_allowance_is_codegen_only_by_price(self):
        self.assertTrue(m5_model_allowed(CostClass.LIGHT, Decimal('3.75'), 'codegen'))
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


if __name__ == '__main__':
    unittest.main()
