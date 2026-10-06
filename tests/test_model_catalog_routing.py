"""Cost-aware multi-provider routing over a priced model catalog."""
import io
import json
import os
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod.model_catalog import ModelCatalogError, parse_model_catalog
from omni_prod.model_gateway import ModelGatewayError, OpenAICompatibleGateway
from omni_prod.model_policy import ModelPolicyViolation, ModelUsePolicy
from omni_prod.model_router import RoutingPolicy
from omni_prod.model_runtime_config import ModelRuntimeConfig
from omni_prod.routed_gateway import RoutedModelGateway

CATALOG = [
    {"name": "cheap-low", "provider": "cheap", "base_url": "https://cheap.example/v1", "model": "c-small",
     "api_key_env": "CHEAP_API_KEY", "quality": 50, "input_per_million": "0.01", "output_per_million": "0.02"},
    {"name": "groq-mid", "provider": "groq", "base_url": "https://api.groq.com/openai/v1", "model": "g-model",
     "api_key_env": "GROQ_API_KEY", "quality": 80, "input_per_million": "0.15", "output_per_million": "0.60",
     "max_output_tokens": 2000},
    {"name": "openai-top", "provider": "openai", "base_url": "https://api.openai.com/v1", "model": "o-model",
     "api_key_env": "OPENAI_API_KEY", "quality": 95, "input_per_million": "2", "output_per_million": "8"},
    {"name": "gemini-nokey", "provider": "gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
     "model": "gem", "api_key_env": "GEMINI_API_KEY", "quality": 90, "input_per_million": "0.1", "output_per_million": "0.4"},
]
KEYS = {"CHEAP_API_KEY": "k1", "GROQ_API_KEY": "k2", "OPENAI_API_KEY": "k3"}
OPEN_POLICY = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                             external_budget_usd=Decimal("1.00"), max_external_calls_per_build=20)


class _FakeGateway:
    calls = []
    failing = set()

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.last_usage = None

    def complete(self, **kw):
        _FakeGateway.calls.append((self.endpoint.name, kw["max_tokens"]))
        if self.endpoint.name in _FakeGateway.failing:
            raise ModelGatewayError("boom")
        return "ok:" + self.endpoint.name

    def complete_json(self, **kw):
        return {"via": self.complete(**kw)}


def _gateway(policy=OPEN_POLICY, routing=None, catalog=CATALOG, env=KEYS):
    _FakeGateway.calls = []
    _FakeGateway.failing = set()
    return RoutedModelGateway(ranked=parse_model_catalog(json.dumps(catalog), env),
                              routing_policy=routing or RoutingPolicy(minimum_quality=70),
                              policy=policy, gateway_factory=_FakeGateway)


class CatalogParsingTests(unittest.TestCase):
    def test_missing_key_is_not_configured_and_never_routed(self):
        models = {m.option.model: m for m in parse_model_catalog(json.dumps(CATALOG), KEYS)}
        self.assertEqual(models["gem"].status, "NOT_CONFIGURED")
        self.assertIsNone(models["gem"].endpoint)
        self.assertEqual(models["g-model"].status, "CONFIGURED")

    def test_public_dict_never_contains_key_value(self):
        for m in parse_model_catalog(json.dumps(CATALOG), KEYS):
            self.assertNotIn("k2", json.dumps(m.to_public_dict()))

    def test_rejects_inline_key_missing_price_and_http(self):
        base = dict(CATALOG[1])
        for bad in ({**base, "api_key": "x"},
                    {k: v for k, v in base.items() if k != "output_per_million"},
                    {**base, "base_url": "http://api.groq.com/openai/v1"},
                    {**base, "quality": 101},
                    {**base, "input_per_million": "-1"}):
            with self.assertRaises(ModelCatalogError):
                parse_model_catalog(json.dumps([bad]), KEYS)

    def test_duplicate_names_rejected(self):
        with self.assertRaises(ModelCatalogError):
            parse_model_catalog(json.dumps([CATALOG[1], CATALOG[1]]), KEYS)


class CostAwareRoutingTests(unittest.TestCase):
    def test_cheapest_model_meeting_quality_is_used(self):
        gw = _gateway()
        self.assertEqual(gw.complete(system="s", user="u", max_tokens=500), "ok:groq-mid")
        self.assertEqual(_FakeGateway.calls, [("groq-mid", 500)])

    def test_quality_preference_picks_best(self):
        gw = _gateway(routing=RoutingPolicy(minimum_quality=70, prefer_cost=False))
        self.assertEqual(gw.complete(system="s", user="u"), "ok:openai-top")

    def test_failure_falls_through_to_next_cheapest(self):
        gw = _gateway()
        _FakeGateway.failing = {"groq-mid"}
        self.assertEqual(gw.complete(system="s", user="u", max_tokens=100), "ok:openai-top")
        self.assertEqual([c[0] for c in _FakeGateway.calls], ["groq-mid", "openai-top"])

    def test_max_tokens_clamped_to_model_limit(self):
        gw = _gateway()
        gw.complete(system="s", user="u", max_tokens=9000)
        self.assertEqual(_FakeGateway.calls[0], ("groq-mid", 2000))

    def test_authorized_cost_is_conservative_upper_bound(self):
        gw = _gateway()
        user = "x" * 1000
        gw.complete(system="", user=user, max_tokens=1000)
        expected = (Decimal(1000 + 64) * Decimal("0.15") + Decimal(1000) * Decimal("0.60")) / Decimal(1_000_000)
        self.assertEqual(gw.state.external_spend_usd, expected)

    def test_zero_cost_mode_blocks_external_catalog(self):
        gw = _gateway(policy=ModelUsePolicy())
        with self.assertRaises(ModelPolicyViolation):
            gw.complete(system="s", user="u")
        self.assertEqual(_FakeGateway.calls, [])

    def test_budget_exhaustion_stops_before_request(self):
        tiny = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                              external_budget_usd=Decimal("0.000001"), max_external_calls_per_build=5)
        gw = _gateway(policy=tiny)
        with self.assertRaises(ModelPolicyViolation):
            gw.complete(system="s", user="u" * 100, max_tokens=1000)
        self.assertEqual(_FakeGateway.calls, [])

    def test_no_eligible_model_is_explicit_failure(self):
        gw = _gateway(routing=RoutingPolicy(minimum_quality=99))
        with self.assertRaises(ModelGatewayError):
            gw.complete(system="s", user="u")

    def test_no_routes_at_all_rejected(self):
        with self.assertRaises(ValueError):
            RoutedModelGateway(ranked=parse_model_catalog(json.dumps(CATALOG), {}), policy=OPEN_POLICY)


class RoutingEvidenceTests(unittest.TestCase):
    def test_events_record_model_reason_and_cap(self):
        gw = _gateway()
        _FakeGateway.failing = {"groq-mid"}
        gw.complete(system="s", user="u", max_tokens=100)
        first, second = gw.events
        self.assertEqual((first.provider, first.ok, first.model, first.call), ("groq-mid", False, "g-model", "complete"))
        self.assertIn("cheapest", first.reason)
        self.assertIn("escalation #1", second.reason)
        self.assertTrue(second.ok)
        self.assertGreater(Decimal(second.max_estimated_cost_usd), 0)
        json.dumps([e.__dict__ for e in gw.events])  # build evidence stays JSON-safe


class RuntimeConfigTests(unittest.TestCase):
    def test_catalog_without_local_url_has_no_local_primary(self):
        env = {"OMNI_MODEL_CATALOG_JSON": json.dumps(CATALOG), **KEYS}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = ModelRuntimeConfig.from_env()
        self.assertIsNone(cfg.primary)
        self.assertEqual(sum(1 for m in cfg.catalog if m.status == "CONFIGURED"), 3)

    def test_no_catalog_keeps_local_primary_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = ModelRuntimeConfig.from_env()
        self.assertIsNotNone(cfg.primary)
        self.assertFalse(cfg.primary.external)
        self.assertEqual(cfg.catalog, ())


class GatewayHeaderTests(unittest.TestCase):
    def test_requests_identify_platform_user_agent(self):
        from omni_prod.model_gateway import ModelEndpoint
        seen = {}

        class _Resp:
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self):
                return json.dumps({"choices": [{"message": {"content": "hi"}}]}).encode()

        def opener(req, timeout):
            seen.update({k.lower(): v for k, v in req.header_items()})
            return _Resp()

        ep = ModelEndpoint(name="g", base_url="https://api.groq.com/openai/v1", model="m", api_key="k", external=True)
        OpenAICompatibleGateway(ep, urlopen=opener).complete(system="s", user="u")
        self.assertTrue(seen["user-agent"].startswith("148AI"))


if __name__ == "__main__":
    unittest.main()
