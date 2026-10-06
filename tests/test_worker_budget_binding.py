"""The worker may never spend more on models than admission reserved for the build.

Admission (Vercel) and the worker (VPS) read their budgets from separate
environments. The durable quote's `components.llm_maximum_usd` is the
authorization; the worker's gateway budget is lowered to it, never raised.
"""
import json
import unittest
from decimal import Decimal

from omni_prod.model_catalog import parse_model_catalog
from omni_prod.model_policy import ModelUsePolicy
from omni_prod.model_router import RoutingPolicy
from omni_prod.routed_gateway import RoutedModelGateway
from omni_prod.worker_tasks import bind_model_budget_to_reservation

CATALOG = [{"name": "cheap", "provider": "p1", "base_url": "https://a.example/v1", "model": "m",
            "api_key_env": "KEY_ONE", "quality": 80, "input_per_million": "1", "output_per_million": "2"}]


class _Fake:
    calls = 0

    def __init__(self, endpoint):
        self.endpoint, self.last_usage, self.last_response_model = endpoint, None, None

    def complete(self, **kw):
        _Fake.calls += 1
        return "ok"


def _gw(budget):
    _Fake.calls = 0
    policy = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                            external_budget_usd=Decimal(budget), max_external_calls_per_build=50)
    return RoutedModelGateway(ranked=parse_model_catalog(json.dumps(CATALOG), {"KEY_ONE": "k"}),
                              routing_policy=RoutingPolicy(minimum_quality=70), policy=policy,
                              gateway_factory=_Fake)


def _request(llm_max):
    return {"economics_quote": {"components": {"llm_maximum_usd": llm_max}}}


class BudgetBindingTests(unittest.TestCase):
    def test_worker_budget_is_lowered_to_reservation(self):
        gw = _gw("5")
        before = gw.policy_version
        ev = bind_model_budget_to_reservation(gw, _request("0.50"))
        self.assertEqual(ev["binding"], "bound")
        self.assertEqual(gw.policy.external_budget_usd, Decimal("0.50"))
        self.assertEqual((ev["worker_env_budget_usd"], ev["effective_budget_usd"]), ("5", "0.50"))
        self.assertNotEqual(gw.policy_version, before)

    def test_never_raised_above_worker_env(self):
        gw = _gw("0.50")
        ev = bind_model_budget_to_reservation(gw, _request("5"))
        self.assertEqual(gw.policy.external_budget_usd, Decimal("0.50"))
        self.assertEqual(ev["effective_budget_usd"], "0.50")

    def test_zero_reservation_blocks_every_paid_call(self):
        gw = _gw("5")
        bind_model_budget_to_reservation(gw, _request("0"))
        with self.assertRaises(Exception):
            gw.complete(system="s", user="u", max_tokens=100)
        self.assertEqual(_Fake.calls, 0)
        self.assertEqual(gw.state.external_spend_usd, Decimal("0"))

    def test_legacy_request_without_components_is_marked_unbound(self):
        gw = _gw("5")
        self.assertEqual(bind_model_budget_to_reservation(gw, {"economics_quote": {}}), {"binding": "legacy_unbound"})
        self.assertEqual(gw.policy.external_budget_usd, Decimal("5"))

    def test_gateway_without_binding_support(self):
        self.assertEqual(bind_model_budget_to_reservation(object(), _request("1")), {"binding": "not_applicable"})


if __name__ == "__main__":
    unittest.main()
