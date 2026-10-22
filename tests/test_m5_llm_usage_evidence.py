"""M5 Task 8: real LLM provider usage and code-generation evidence.

Uses an in-test HTTP double for the OpenAI-compatible endpoint, so this proves
parsing, propagation and settlement rules -- not that any real provider was
called. The real-provider proof is tests/integration/test_m5_live_llm_usage.py.
"""
from __future__ import annotations

import json
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from omni_prod import worker_tasks
from omni_prod.autonomous_agents import ArchitectAgent, GeneratorAgent, RepairAgent
from omni_prod.autonomous_core import AutonomousProductEngine
from omni_prod.model_gateway import ModelEndpoint, ModelGatewayError, OpenAICompatibleGateway
from omni_prod.model_policy import ModelUsePolicy, ModelUseState
from omni_prod.models import BuildStatus
from omni_prod.provider_usage import ProviderUsage, ProviderUsageLedger
from omni_prod.providers.llm_provider import LLMCapabilityProvider
from omni_prod.capabilities import CapabilityRequirement
from omni_prod.provider_contracts import ProviderQuote
from omni_prod.routed_gateway import ProviderRoute, RoutedModelGateway

try:
    from tests.m5_worker_harness import ContractBuildHarness
except ModuleNotFoundError:
    from m5_worker_harness import ContractBuildHarness


class _Resp:
    def __init__(self, payload, headers=None, status=200):
        self._body = json.dumps(payload).encode()
        self.headers = headers or {}
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _completion(content="ok", usage=None, rid="chatcmpl-abc"):
    payload = {"id": rid, "choices": [{"message": {"content": content}}]}
    if usage is not None:
        payload["usage"] = usage
    return payload


def _gateway(payload, headers=None, *, external=False):
    endpoint = ModelEndpoint(name="ext" if external else "local", base_url="https://api.example/v1",
                             model="model-x", api_key="k" if external else None, external=external)
    return OpenAICompatibleGateway(endpoint, urlopen=lambda req, timeout: _Resp(payload, headers))


class NormalizationTests(unittest.TestCase):
    def test_known_token_usage_is_normalized(self):
        gw = _gateway(_completion(usage={"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}),
                      headers={"x-request-id": "req_123"})
        self.assertEqual(gw.complete(system="s", user="u"), "ok")  # API unchanged
        usage = gw.last_usage
        self.assertIsInstance(usage, ProviderUsage)
        self.assertEqual((usage.input_tokens, usage.output_tokens), (120, 30))
        self.assertIsNone(usage.cached_tokens)  # not reported -> unknown, never 0
        self.assertIsNone(usage.provider_reported_cost_usd)
        self.assertEqual(usage.request_id, "req_123")
        self.assertEqual(usage.request_id_source, "header:x-request-id")
        self.assertEqual(usage.response_id, "chatcmpl-abc")
        self.assertEqual((usage.provider, usage.model), ("local", "model-x"))
        self.assertTrue(usage.usage_reported)
        self.assertEqual(usage.source, "provider_response")

    def test_cached_tokens_both_dialects(self):
        gw = _gateway(_completion(usage={"prompt_tokens": 100, "completion_tokens": 5,
                                         "prompt_tokens_details": {"cached_tokens": 64}}))
        gw.complete(system="s", user="u")
        self.assertEqual(gw.last_usage.cached_tokens, 64)
        gw = _gateway(_completion(usage={"input_tokens": 10, "output_tokens": 2, "cache_read_input_tokens": 7}))
        gw.complete(system="s", user="u")
        self.assertEqual((gw.last_usage.input_tokens, gw.last_usage.output_tokens, gw.last_usage.cached_tokens),
                         (10, 2, 7))

    def test_provider_reported_cost_only_when_present(self):
        gw = _gateway(_completion(usage={"prompt_tokens": 1, "completion_tokens": 1, "cost": 0.00042}))
        gw.complete(system="s", user="u")
        self.assertEqual(gw.last_usage.provider_reported_cost_usd, Decimal("0.00042"))
        for bad in (-1, "free", True):
            gw = _gateway(_completion(usage={"prompt_tokens": 1, "completion_tokens": 1, "cost": bad}))
            gw.complete(system="s", user="u")
            self.assertIsNone(gw.last_usage.provider_reported_cost_usd, bad)

    def test_missing_usage_block_stays_unknown(self):
        gw = _gateway(_completion(usage=None), headers={})
        gw.complete(system="s", user="u")
        usage = gw.last_usage
        self.assertFalse(usage.usage_reported)
        self.assertEqual((usage.input_tokens, usage.output_tokens, usage.cached_tokens), (None, None, None))
        self.assertIsNone(usage.provider_reported_cost_usd)
        self.assertEqual(usage.request_id, "chatcmpl-abc")
        self.assertEqual(usage.request_id_source, "response_id")

    def test_estimates_cannot_be_synthesized_into_usage(self):
        with self.assertRaises(ValueError):
            ProviderUsage(provider="p", model="m", external=True, request_id="r", request_id_source="header:x",
                          response_id=None, input_tokens=1, output_tokens=1, cached_tokens=None,
                          provider_reported_cost_usd=None, usage_reported=True, source="estimate")
        with self.assertRaises(ValueError):
            ProviderUsage(provider="p", model="m", external=True, request_id="r", request_id_source="header:x",
                          response_id=None, input_tokens=-5, output_tokens=1, cached_tokens=None,
                          provider_reported_cost_usd=None, usage_reported=True)

    def test_usage_is_captured_even_when_content_is_invalid(self):
        gw = _gateway(_completion(content="", usage={"prompt_tokens": 9, "completion_tokens": 0}),
                      headers={"x-request-id": "req_empty"})
        with self.assertRaises(ModelGatewayError):
            gw.complete(system="s", user="u")
        self.assertEqual(gw.last_usage.request_id, "req_empty")  # billed call is still evidenced
        self.assertEqual(gw.last_usage.input_tokens, 9)


class LedgerTests(unittest.TestCase):
    def _usage(self, rid, cost=None, external=True):
        return ProviderUsage(provider="ext", model="m", external=external, request_id=rid,
                             request_id_source="header:x-request-id", response_id=None,
                             input_tokens=10, output_tokens=5, cached_tokens=None,
                             provider_reported_cost_usd=cost, usage_reported=True)

    def test_retry_or_rerecord_does_not_duplicate_rows(self):
        ledger = ProviderUsageLedger()
        u = self._usage("req_1", Decimal("0.01"))
        ledger.record(u)
        ledger.record(u)
        ledger.record(self._usage("req_1", Decimal("0.01")))
        self.assertEqual(len(ledger.events()), 1)

    def test_actual_cost_known_only_when_every_external_call_reported_cost(self):
        ledger = ProviderUsageLedger()
        ledger.record(self._usage("req_1", Decimal("0.01")))
        ledger.record(self._usage("req_2", Decimal("0.02")))
        self.assertEqual(ledger.actual_external_cost_usd(authorized_external_calls=2), Decimal("0.03"))
        # a third authorized call left no usage (e.g. network failure after dispatch)
        self.assertIsNone(ledger.actual_external_cost_usd(authorized_external_calls=3))
        ledger.record(self._usage("req_3", None))
        self.assertIsNone(ledger.actual_external_cost_usd(authorized_external_calls=3))

    def test_summary_separates_estimates_from_actuals(self):
        ledger = ProviderUsageLedger()
        ledger.record(self._usage("req_1", None))
        summary = ledger.summary(authorized_external_calls=1, authorized_estimate_usd=Decimal("0.25"))
        self.assertIsNone(summary["actual_cost_usd"])
        self.assertEqual(summary["authorized_estimate_usd"], "0.25")
        self.assertEqual(summary["actual_cost_basis"], "UNKNOWN_PROVIDER_DID_NOT_REPORT_COST")
        self.assertEqual(summary["input_tokens"], 10)
        self.assertEqual(summary["request_ids"], ["req_1"])


def _routed(responses, *, external_fallback=True):
    """Primary local route fails, external fallback answers with the given responses."""
    seq = list(responses)

    def factory(endpoint):
        if not endpoint.external:
            def _fail(req, timeout):
                raise OSError("local model down")
            return OpenAICompatibleGateway(endpoint, urlopen=_fail)
        return OpenAICompatibleGateway(endpoint, urlopen=lambda req, timeout: seq.pop(0))

    local = ModelEndpoint(name="local", base_url="http://127.0.0.1:1/v1", model="m-local")
    ext = ModelEndpoint(name="ext", base_url="https://api.example/v1", model="m-ext", api_key="k", external=True)
    policy = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=external_fallback,
                            external_budget_usd=Decimal("5"), max_external_calls_per_build=10)
    return RoutedModelGateway(primary=ProviderRoute(local, declared_quality=90),
                              fallback=(ProviderRoute(ext, Decimal("0.25"), declared_quality=90),),
                              policy=policy, state=ModelUseState(), gateway_factory=factory)


class RoutedGatewayTests(unittest.TestCase):
    def test_routed_gateway_collects_usage_and_request_ids(self):
        gw = _routed([_Resp(_completion(usage={"prompt_tokens": 50, "completion_tokens": 10, "cost": 0.003}),
                            headers={"x-request-id": "req_ext_1"})])
        self.assertEqual(gw.complete(system="s", user="u"), "ok")
        events = gw.usage.events()
        self.assertEqual([e.request_id for e in events], ["req_ext_1"])
        self.assertTrue(events[0].external)
        self.assertEqual(gw.events[-1].request_id, "req_ext_1")
        self.assertEqual(gw.usage.actual_external_cost_usd(authorized_external_calls=gw.state.external_calls),
                         Decimal("0.003"))
        self.assertEqual(gw.last_usage.request_id, "req_ext_1")


class LLMCapabilityProviderTests(unittest.TestCase):
    def test_provider_reports_usage_and_actual_cost_only_when_reported(self):
        gw = _routed([_Resp(_completion(usage={"prompt_tokens": 5, "completion_tokens": 5, "cost": 0.001}),
                            headers={"x-request-id": "req_cap"})])
        provider = LLMCapabilityProvider(
            name="model-router", gateway=gw, capability_keys=("software.plan",),
            quote_factory=lambda r: ProviderQuote("model-router", r.key, Decimal("0"), Decimal("0.25"), "v1", "call", Decimal("1")))
        req = CapabilityRequirement(id="cap-1", key="software.plan", purpose="plan", required=True)
        handle = provider.submit(req, idempotency_key="idem_1")
        result = provider.collect(handle)
        self.assertEqual(result.actual_cost_usd, Decimal("0.001"))
        self.assertEqual(result.usage["request_id"], "req_cap")
        self.assertEqual(result.usage["input_tokens"], 5)

        gw2 = _routed([_Resp(_completion(usage={"prompt_tokens": 5, "completion_tokens": 5}))])
        provider2 = LLMCapabilityProvider(
            name="model-router", gateway=gw2, capability_keys=("software.plan",),
            quote_factory=lambda r: ProviderQuote("model-router", r.key, Decimal("0"), Decimal("0.25"), "v1", "call", Decimal("1")))
        result2 = provider2.collect(provider2.submit(req, idempotency_key="idem_2"))
        self.assertIsNone(result2.actual_cost_usd)  # never the quote estimate


class WorkerEvidenceTests(unittest.TestCase):
    def test_request_ids_survive_into_build_evidence(self):
        gw = _routed([_Resp(_completion(usage={"prompt_tokens": 70, "completion_tokens": 20, "cost": 0.004}),
                            headers={"x-request-id": "req_build_1"})])
        gw.complete(system="s", user="u")  # what the engine would do during generation
        harness = ContractBuildHarness(gateway=gw)
        harness.jobs.request["economics_quote"] = {"revenue_usd": "1.00", "infrastructure_maximum_usd": "0"}
        harness.subs.settle.return_value = {"settled": True}
        self.assertEqual(harness.run(), "ready")
        evidence = harness.final["evidence_json"]
        self.assertEqual(evidence["provider_usage"]["request_ids"], ["req_build_1"])
        self.assertEqual(evidence["provider_usage"]["input_tokens"], 70)
        self.assertEqual(evidence["model_route_events"][-1]["request_id"], "req_build_1")
        # every authorized external call reported its cost -> settlement uses the real actual
        harness.subs.settle.assert_called_once()
        self.assertEqual(harness.subs.settle.call_args.kwargs["actual_provider_cost_usd"], Decimal("0.004"))
        self.assertEqual(harness.final["actual_provider_cost_usd"], Decimal("0.004"))

    def test_unknown_provider_cost_settles_as_null_not_estimate(self):
        gw = _routed([_Resp(_completion(usage={"prompt_tokens": 70, "completion_tokens": 20}),
                            headers={"x-request-id": "req_build_2"})])
        gw.complete(system="s", user="u")
        harness = ContractBuildHarness(gateway=gw)
        harness.jobs.request["economics_quote"] = {"revenue_usd": "1.00", "infrastructure_maximum_usd": "0"}
        harness.subs.settle.return_value = {}
        harness.run()
        self.assertIsNone(harness.subs.settle.call_args.kwargs["actual_provider_cost_usd"])
        self.assertIsNone(harness.final["actual_provider_cost_usd"])
        self.assertEqual(harness.final["evidence_json"]["provider_usage"]["actual_cost_basis"],
                         "UNKNOWN_PROVIDER_DID_NOT_REPORT_COST")

    def test_provider_failure_is_explicit_failure_not_fake_app(self):
        def factory(endpoint):
            def boom(req, timeout):
                raise OSError("provider unavailable")
            return OpenAICompatibleGateway(endpoint, urlopen=boom)

        local = ModelEndpoint(name="local", base_url="http://127.0.0.1:1/v1", model="m")
        gw = RoutedModelGateway(primary=ProviderRoute(local, declared_quality=90), gateway_factory=factory)
        engine = AutonomousProductEngine(architect=ArchitectAgent(gw), generator=GeneratorAgent(gw),
                                         repairer=RepairAgent(gw), executor=MagicMock(), max_repair_rounds=1)
        harness = ContractBuildHarness(gateway=gw)
        harness.engine = engine
        with self.assertRaises(ModelGatewayError):
            harness.run()
        final = harness.final
        self.assertEqual(final["target"], BuildStatus.FAILED)
        # A provider outage is reported as such, not as an internal error.
        self.assertEqual(final["error_code"], "model_unavailable")
        self.assertIn("all model routes failed", final["error_message"])
        harness.workspace.commit.assert_not_called()  # no repository, deterministic or otherwise
        self.assertIsNone(final["result_version_id"])
        self.assertEqual(final["evidence_json"]["provider_usage"]["usage_events"], [])


if __name__ == "__main__":
    unittest.main()
