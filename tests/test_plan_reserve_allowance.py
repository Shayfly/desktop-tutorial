from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase

from omni_prod.creator_plan import build_plan_preview
from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.product_architect import ProductArchitect
from omni_prod.subscription_store import PostgresSubscriptionService
from omni_prod.pricing import PLAN_CATALOG, PlanCode
from tests.test_m5_build_economics import Pool, ScriptedCursor


class PlanReserveAllowanceTests(TestCase):
    def preview(self, *, spend, used=0):
        quote = SimpleNamespace(total_authorized_variable_usd=Decimal('0.35'))
        service = PostgresSubscriptionService(pool=Pool(ScriptedCursor([])))
        cur = ScriptedCursor([('basic', service._cycle_now(), used, Decimal(spend))])
        service = PostgresSubscriptionService(pool=Pool(cur))
        def authorize(q):
            return service.authorize(user_id='u1', cost_class='light', credits=60,
                                     estimated_provider_cost_usd=q.total_authorized_variable_usd)
        preview = build_plan_preview(
            architect=ProductArchitect(), repository=MemoryBuildContractRepository(), project_id='p',
            prompt='Build a simple static page for a flower shop, no login, no personal data.',
            economics=lambda: quote, authorize_quote=authorize,
            durable_backend=True, infrastructure_readiness={'kinds': {}}, image_readiness={'status': 'PARTIAL'})
        self.assertFalse(any('credit_reservations' in sql for sql, _ in cur.calls))
        self.assertFalse(any('provider_spend_usd=' in sql for sql, _ in cur.calls))
        return preview

    def test_positive_balance_smaller_than_full_reserve_blocks_preview(self):
        p = self.preview(spend='2.30')
        self.assertFalse(p['can_build'])
        self.assertIn('plan_cannot_authorize_cost', [b['code'] for b in p['blockers']])

    def test_exact_reserve_and_larger_balance_are_admissible(self):
        for spend in ('2.15', '2.00'):
            with self.subTest(spend=spend):
                self.assertTrue(self.preview(spend=spend)['can_build'])

    def test_exhausted_credits_block_even_when_provider_budget_remains(self):
        p = self.preview(spend='0', used=PLAN_CATALOG[PlanCode.AMATEUR].included_credits)
        self.assertFalse(p['can_build'])
