"""Code writing and repair prefer the stronger model (rehearsal 2026-10-08)."""
import os
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod.model_catalog import CatalogModel
from omni_prod.model_gateway import ModelEndpoint
from omni_prod.model_policy import ModelUsePolicy
from omni_prod.model_router import ModelOption, RoutingPolicy
from omni_prod.routed_gateway import RoutedModelGateway


def _model(name, quality, inp, out):
    return CatalogModel(endpoint=ModelEndpoint(name=name, base_url='https://x.invalid', model=name, api_key='k', external=True),
                        option=ModelOption('gemini', name, quality, 1000, Decimal(inp), Decimal(out)), max_output_tokens=16384, api_key_env='K')


class TaskRoutingTests(unittest.TestCase):
    def setUp(self):
        self.gw = RoutedModelGateway(primary=None, fallback=(), ranked=(_model('lite', 70, '0.25', '1.5'), _model('flash', 85, '0.75', '3.75')),
                                     routing_policy=RoutingPolicy(minimum_quality=70, prefer_cost=True),
                                     policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                           external_budget_usd=Decimal('1'), max_external_calls_per_build=10))
        self.kw = {'system': 's', 'user': 'u', 'max_tokens': 1000}

    def order(self, task):
        return [r.endpoint.name for r, _, _ in self.gw.ranked_routes(self.kw, task)]

    def test_codegen_and_repair_prefer_quality_with_cheaper_escalation(self):
        self.assertEqual(self.order('codegen'), ['flash', 'lite'])
        self.assertEqual(self.order('repair'), ['flash', 'lite'])

    def test_planning_stays_cost_first(self):
        self.assertEqual(self.order('architecture'), ['lite', 'flash'])

    def test_env_override(self):
        with mock.patch.dict(os.environ, {'OMNI_MODEL_TASK_MIN_QUALITY': '{"codegen": 0}'}):
            self.assertEqual(self.order('codegen'), ['lite', 'flash'])


if __name__ == '__main__':
    unittest.main()


class SettlementTests(unittest.TestCase):
    """Rehearsal 2026-10-08: worst-case reservations exhausted the budget."""

    def _gw(self, usage):
        from types import SimpleNamespace

        class _Fake:
            def __init__(self, endpoint):
                self.last_usage = usage
                self.last_response_model = endpoint.model

            def complete_json(self, **kw):
                return {'ok': True}
        return RoutedModelGateway(ranked=(_model('flash', 85, '0.75', '3.75'),), routing_policy=RoutingPolicy(minimum_quality=70),
                                  policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                        external_budget_usd=Decimal('1'), max_external_calls_per_build=10),
                                  gateway_factory=_Fake)

    def test_reported_usage_settles_the_reservation_down(self):
        from omni_prod.provider_usage import ProviderUsage
        gw = self._gw(ProviderUsage(provider='gemini', model='flash', external=True, request_id='r', request_id_source='header', response_id='x', input_tokens=1000, output_tokens=1000, cached_tokens=0, provider_reported_cost_usd=None, usage_reported=True))
        gw.complete_json(system='s', user='u', max_tokens=16000)
        expected = (Decimal(1000) * Decimal('0.75') + Decimal(1000) * Decimal('3.75')) / Decimal(1_000_000)
        self.assertEqual(gw.state.external_spend_usd, expected)

    def test_no_reported_usage_keeps_the_worst_case(self):
        gw = self._gw(None)
        gw.complete_json(system='s', user='u', max_tokens=16000)
        self.assertGreater(gw.state.external_spend_usd, Decimal('0.05'))
