"""CEO 2026-10-19: the intake chat quotes the credits and model cap of the
customer's own plan (pricing.m5_build_terms / m5_llm_budget), not a fixed 60."""
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from omni_prod import investor_app
from omni_prod.pricing import PLAN_CATALOG, PlanCode


class IntakeCreditsByPlanTests(unittest.TestCase):
    def _supervisor_for(self, code):
        v28 = MagicMock()
        v28.subscriptions.plan_for.return_value = PLAN_CATALOG[code]
        with patch.object(investor_app, '_v28', v28), \
             patch.object(investor_app, '_project_context', return_value=None), \
             patch.object(investor_app, '_brief_repo', return_value=MagicMock()), \
             patch.object(investor_app, '_conversation_store', return_value=MagicMock()):
            return investor_app._supervisor('tenant-key', 'usr_1')

    def test_chat_quotes_the_plan_class_credits_and_cap(self):
        expected = {PlanCode.FREE: (45, '0.35'), PlanCode.AMATEUR: (45, '0.35'), PlanCode.PRO: (200, '1.60'),
                    PlanCode.STUDIO: (500, '5.50'), PlanCode.ENTERPRISE: (1200, '18.00')}
        for code, (credits, cap) in expected.items():
            sup = self._supervisor_for(code)
            self.assertEqual(sup.credits, credits, code)
            self.assertEqual(Decimal(str(sup.budget_usd)), Decimal(cap), code)

    def test_never_the_old_fixed_60(self):
        for code in (PlanCode.AMATEUR, PlanCode.PRO, PlanCode.STUDIO):
            self.assertNotEqual(self._supervisor_for(code).credits, 60, code)


if __name__ == '__main__':
    unittest.main()
