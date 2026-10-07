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
