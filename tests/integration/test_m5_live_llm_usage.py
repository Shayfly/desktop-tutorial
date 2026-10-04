"""M5 Task 8 gated integration: one real OpenAI-compatible model call.

SKIPs unless a real provider is supplied:
  M5_LIVE_LLM_BASE_URL   e.g. https://api.openai.com/v1 or any OpenAI-compatible endpoint
  M5_LIVE_LLM_MODEL      model id
  M5_LIVE_LLM_API_KEY    API key (read from the environment; never logged)
Optional: M5_LIVE_LLM_EXPECT_COST=1 when the provider returns usage.cost.
"""
from __future__ import annotations

import os
import unittest
from decimal import Decimal

_REQUIRED = ("M5_LIVE_LLM_BASE_URL", "M5_LIVE_LLM_MODEL", "M5_LIVE_LLM_API_KEY")
_MISSING = [name for name in _REQUIRED if not os.environ.get(name)]


@unittest.skipIf(bool(_MISSING), "real LLM provider not supplied: missing " + ", ".join(_MISSING))
class LiveLLMUsageTests(unittest.TestCase):
    def test_real_call_reports_request_id_and_usage(self):
        from omni_prod.model_gateway import ModelEndpoint
        from omni_prod.model_policy import ModelUsePolicy, ModelUseState
        from omni_prod.routed_gateway import ProviderRoute, RoutedModelGateway

        local = ModelEndpoint(name="unreachable-local", base_url="http://127.0.0.1:9/v1", model="none",
                              timeout_seconds=1)
        ext = ModelEndpoint(name="live-provider", base_url=os.environ["M5_LIVE_LLM_BASE_URL"],
                            model=os.environ["M5_LIVE_LLM_MODEL"], api_key=os.environ["M5_LIVE_LLM_API_KEY"],
                            external=True, timeout_seconds=60)
        gateway = RoutedModelGateway(
            primary=ProviderRoute(local), fallback=(ProviderRoute(ext, Decimal("0.05")),),
            policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                  external_budget_usd=Decimal("0.05"), max_external_calls_per_build=1),
            state=ModelUseState())
        text = gateway.complete(system="Reply with the single word: pong", user="ping", max_tokens=5)
        self.assertTrue(text.strip())
        usage = gateway.last_usage
        self.assertIsNotNone(usage)
        self.assertTrue(usage.request_id, "provider returned no request identity")
        self.assertTrue(usage.usage_reported, "provider returned no usage block")
        self.assertGreater(usage.input_tokens or 0, 0)
        summary = gateway.usage.summary(authorized_external_calls=gateway.state.external_calls,
                                        authorized_estimate_usd=gateway.state.external_spend_usd)
        if os.environ.get("M5_LIVE_LLM_EXPECT_COST") == "1":
            self.assertEqual(summary["actual_cost_basis"], "PROVIDER_REPORTED")
        else:
            self.assertIn(summary["actual_cost_basis"], {"PROVIDER_REPORTED", "UNKNOWN_PROVIDER_DID_NOT_REPORT_COST"})


if __name__ == "__main__":
    unittest.main()
