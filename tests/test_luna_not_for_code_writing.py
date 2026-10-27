"""gpt-6-luna does not write or repair code (founder 2026-10-20).

Paid run 39377332673 (inspect-build 39378559811): the light class admits two models, gemini-3.1-flash-lite ($1.50/M
out) and gpt-6-luna ($0.50/M out). Both are below the codegen floor (85), so the cost-first router took the cheaper,
luna, for every codegen/repair call. All 4 large answers were invalid JSON and were thrown away; flash-lite wrote
all of the code that was actually tested. Here the REAL deployed catalog and the REAL router decide.
"""
import unittest

from omni_prod.intelligence import task_policy
from omni_prod.pricing import CostClass

from tests.test_m5_plan_build_class import TASK, _gateway


def first_model(gw, task):
    routes = gw.ranked_routes(dict(TASK), task)
    return routes[0][2].model if routes else None


def models(gw, task):
    return [option.model for _, _, option in gw.ranked_routes(dict(TASK), task)]


class LunaOutOfCodeWritingTests(unittest.TestCase):
    def setUp(self):
        self.light = _gateway()
        self.light.restrict_to_cost_class(CostClass.LIGHT)

    def test_the_light_class_still_admits_luna(self):        # the allowlist is by price; it is not what changed
        self.assertIn('gpt-6-luna', {m.option.model for m in self.light.ranked})

    def test_codegen_repair_and_modification_never_go_to_luna_in_the_light_class(self):
        # Founder 2026-10-22: LIGHT keeps flash-lite for codegen; Luna remains excluded until measured.
        self.assertEqual(models(self.light, 'codegen'), ['gemini-3.1-flash-lite'])
        for task in ('repair', 'modification'):
            self.assertEqual(models(self.light, task), ['gemini-3.1-flash-lite'], task)

    def test_luna_is_never_offered_for_code_writing_in_any_class(self):
        for cc in CostClass:
            gw = _gateway()
            gw.restrict_to_cost_class(cc)
            for task in ('codegen', 'repair', 'modification'):
                self.assertNotIn('gpt-6-luna', models(gw, task), (cc, task))

    def test_small_tasks_keep_luna_where_it_answered_correctly(self):
        for task in ('architecture', 'review', 'conversation'):
            self.assertIn('gpt-6-luna', models(self.light, task), task)
        self.assertEqual(first_model(self.light, 'architecture'), 'gpt-6-luna')   # still the cheapest there

    def test_the_policy_records_why(self):
        rows = {r['task']: r for r in task_policy.describe()}
        for task in ('codegen', 'repair', 'modification'):
            self.assertEqual(rows[task]['deny_models'], ['gpt-6-luna'])
        self.assertEqual(rows['review']['deny_models'], [])
        self.assertFalse(task_policy.eligible('codegen', model_id='gpt-6-luna', quality=100))
        self.assertTrue(task_policy.eligible('review', model_id='gpt-6-luna', quality=70))


if __name__ == '__main__':
    unittest.main()
