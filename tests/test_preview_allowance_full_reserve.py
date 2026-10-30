"""Item 3 follow-up (2026-10-30): the PREVIEW route itself must check the customer's remaining allowance against the
FULL build reserve -- quote.total_authorized_variable_usd, the amount POST .../builds reserves -- not a partial one
such as quote.provider_maximum_usd (the model part only).

tests/test_plan_reserve_allowance.py proves creator_plan.build_plan_preview with an injected authorize; its NC mutates
creator_plan.py only. Nothing proved the wiring in investor_app.v28_build_contract_preview: had it passed
provider_maximum_usd, every existing test stayed green. This drives the real FastAPI route with the real
PostgresSubscriptionService.authorize over a scripted cursor (no reservation, no write).

Numbers: Amateur ('basic') paid-provider budget 2.50, spend 2.30 -> remaining 0.20. The quote's model part is 0.10
(fits), the full reserve 0.35 (does not): the preview must be blocked."""
from __future__ import annotations

import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from tests.test_m5_build_economics import Pool, ScriptedCursor

PARTIAL = Decimal('0.10')        # provider_maximum_usd: the model budget only
FULL = Decimal('0.35')           # total_authorized_variable_usd: what admission reserves


def _api():
    try:
        import fastapi  # noqa: F401
        from fastapi.testclient import TestClient
    except Exception as exc:                                                     # v24-ci has fastapi
        raise unittest.SkipTest(f'fastapi not installed here ({exc})')
    from omni_prod import investor_app as IA
    return IA, TestClient(IA.app)


def quote_fixture():
    """The two amounts differ on purpose: only the full reserve exceeds the remaining allowance."""
    return SimpleNamespace(provider_estimated_usd=Decimal('0.05'), provider_maximum_usd=PARTIAL,
                           infrastructure_estimated_usd=Decimal('0.10'), infrastructure_maximum_usd=Decimal('0.20'),
                           retry_reserve_usd=Decimal('0.05'), total_estimated_variable_usd=Decimal('0.20'),
                           total_authorized_variable_usd=FULL)


class ThePreviewRouteChecksTheFullReserve(unittest.TestCase):
    def preview(self, spend):
        from omni_prod.pricing import PLAN_CATALOG, PlanCode
        from omni_prod.subscription_store import PostgresSubscriptionService
        IA, client = _api()
        cycle = PostgresSubscriptionService(pool=Pool(ScriptedCursor([])))._cycle_now()
        cur = ScriptedCursor([('basic', cycle, 0, Decimal(spend))])
        service = PostgresSubscriptionService(pool=Pool(cur))
        self.seen = []

        def authorize(**kw):
            self.seen.append(kw['estimated_provider_cost_usd'])
            return service.authorize(**kw)
        subs = SimpleNamespace(plan_for=lambda uid: PLAN_CATALOG[PlanCode.AMATEUR], authorize=authorize)
        with mock.patch.object(IA, '_v28_bearer', lambda r: 'tok'), \
                mock.patch.object(IA._v28, 'resolve_project_key', lambda **kw: (mock.Mock(id='u1'), 'k')), \
                mock.patch.object(IA._v28, 'subscriptions', subs), \
                mock.patch.object(IA._v28, 'subscription', lambda token: {}), \
                mock.patch.object(IA, '_internal_qa_funding', lambda aid: (None, False)), \
                mock.patch.object(IA, '_m5_cost_inputs', lambda *a, **kw: ()), \
                mock.patch.object(IA, '_m5_build_economics_quote', lambda *a, **kw: quote_fixture()), \
                mock.patch.object(IA, '_async_build_mode', lambda: True):
            r = client.post('/api/v28/projects/p/build-contracts',
                            json={'prompt': 'Build a simple static page for a flower shop, no login, no personal data.'})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertFalse(any('credit_reservations' in sql or 'provider_spend_usd=' in sql for sql, _ in cur.calls),
                         'the preview reserved or wrote')
        return r.json()

    def test_the_route_authorizes_the_full_reserve_not_the_model_part(self):
        self.preview('0')
        self.assertEqual(self.seen, [FULL])

    def test_remaining_below_the_full_reserve_blocks_the_preview_even_if_the_model_part_fits(self):
        p = self.preview('2.30')                                   # remaining 0.20: 0.10 fits, 0.35 does not
        self.assertFalse(p['can_build'])
        self.assertIn('plan_cannot_authorize_cost', [b['code'] for b in p['blockers']])

    def test_remaining_that_covers_the_full_reserve_is_admissible(self):
        self.assertNotIn('plan_cannot_authorize_cost',
                         [b['code'] for b in self.preview('2.15')['blockers']])   # remaining 0.35 == reserve


if __name__ == '__main__':
    unittest.main()
