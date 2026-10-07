"""Provider overload is retried on the same route, boundedly and on the record.

Golden E2E #1 on Preview (2026-10-07): both Gemini routes answered HTTP 503
"This model is currently experiencing high demand" once each and the build
failed. A transient answer (429/5xx) is now retried on the same route with
backoff before escalating; each retry is a separate attempt, budget-checked
and written to the Attempt Ledger. Non-transient errors escalate at once.
"""
import io
import json
import unittest
from decimal import Decimal
from urllib import error

from omni_prod.model_catalog import parse_model_catalog
from omni_prod.model_gateway import ModelEndpoint, ModelGatewayError, ModelHTTPError, OpenAICompatibleGateway
from omni_prod.model_policy import ModelPolicyViolation, ModelUsePolicy
from omni_prod.model_router import RoutingPolicy
from omni_prod.routed_gateway import RoutedModelGateway

CATALOG = [
    {"name": "lite", "provider": "gemini", "base_url": "https://gemini.example/v1", "model": "g-lite",
     "api_key_env": "GEMINI_API_KEY", "quality": 70, "input_per_million": "0.25", "output_per_million": "1.50"},
    {"name": "flash", "provider": "gemini", "base_url": "https://gemini.example/v1", "model": "g-flash",
     "api_key_env": "GEMINI_API_KEY", "quality": 85, "input_per_million": "0.75", "output_per_million": "3.75"},
]
POLICY = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                        external_budget_usd=Decimal("0.50"), max_external_calls_per_build=40)
GEMINI_503 = json.dumps([{"error": {"code": 503, "message": "This model is currently experiencing high demand. "
                                    "Spikes in demand are usually temporary. Please try again later.",
                          "status": "UNAVAILABLE"}}]).encode()


class _Script:
    """Per-model scripted outcomes: an int is an HTTP status, 'ok' succeeds."""

    def __init__(self, outcomes):
        self.outcomes = {k: list(v) for k, v in outcomes.items()}
        self.calls = []

    def factory(self, endpoint):
        script = self

        class Gateway:
            last_usage = None

            def complete(self, **kw):
                script.calls.append(endpoint.model)
                outcome = script.outcomes[endpoint.model].pop(0)
                if outcome == "ok":
                    return "ok:" + endpoint.model
                if outcome == "policy":
                    raise ModelPolicyViolation("external model budget exceeded")
                raise ModelHTTPError(f"model request failed: HTTP {outcome}: overloaded", status=outcome,
                                     retry_after_seconds=None)
        return Gateway()


def _gateway(script, sleeps, retries=2):
    return RoutedModelGateway(ranked=parse_model_catalog(json.dumps(CATALOG), {"GEMINI_API_KEY": "k"}),
                              routing_policy=RoutingPolicy(minimum_quality=70), policy=POLICY,
                              gateway_factory=script.factory, transient_retries=retries, sleep=sleeps.append)


class RetryTests(unittest.TestCase):
    def test_overload_then_success_on_the_same_route(self):
        script, sleeps = _Script({"g-lite": [503, "ok"], "g-flash": []}), []
        gw = _gateway(script, sleeps)
        self.assertEqual(gw.complete(system="s", user="u"), "ok:g-lite")
        self.assertEqual(script.calls, ["g-lite", "g-lite"])
        self.assertEqual(sleeps, [2.0])
        self.assertEqual(gw.state.external_calls, 2)           # each attempt is budget-checked
        self.assertEqual(len(gw.recorder.records), 2)            # and recorded

    def test_retries_are_bounded_then_the_next_route_is_tried(self):
        script, sleeps = _Script({"g-lite": [503, 503, 503], "g-flash": [429, "ok"]}), []
        gw = _gateway(script, sleeps)
        self.assertEqual(gw.complete(system="s", user="u"), "ok:g-flash")
        self.assertEqual(script.calls, ["g-lite"] * 3 + ["g-flash"] * 2)
        self.assertEqual(sleeps, [2.0, 6.0, 2.0])

    def test_non_transient_errors_escalate_immediately(self):
        script, sleeps = _Script({"g-lite": [400], "g-flash": ["ok"]}), []
        self.assertEqual(_gateway(script, sleeps).complete(system="s", user="u"), "ok:g-flash")
        self.assertEqual(sleeps, [])

    def test_final_error_names_every_route_and_the_provider_reason(self):
        script, sleeps = _Script({"g-lite": [503] * 3, "g-flash": [503] * 3}), []
        with self.assertRaises(ModelGatewayError) as ctx:
            _gateway(script, sleeps).complete(system="s", user="u")
        self.assertIn("g-lite: model request failed: HTTP 503", str(ctx.exception))
        self.assertIn("g-flash: model request failed: HTTP 503", str(ctx.exception))

    def test_retries_stop_at_the_build_call_limit(self):
        script, sleeps = _Script({"g-lite": [503, "ok"], "g-flash": ["ok"]}), []
        gw = _gateway(script, sleeps)
        gw.policy = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                   external_budget_usd=Decimal("0.50"), max_external_calls_per_build=1)
        with self.assertRaises(ModelPolicyViolation):
            gw.complete(system="s", user="u")
        self.assertEqual(script.calls, ["g-lite"])               # the retry was refused by the budget policy

    def test_retries_can_be_disabled(self):
        script, sleeps = _Script({"g-lite": [503], "g-flash": ["ok"]}), []
        self.assertEqual(_gateway(script, sleeps, retries=0).complete(system="s", user="u"), "ok:g-flash")
        self.assertEqual(sleeps, [])


class HTTPErrorDetailTests(unittest.TestCase):
    def _gateway_raising(self, status, body, headers=None):
        def urlopen(req, timeout):
            raise error.HTTPError(req.full_url, status, "Service Unavailable", headers or {}, io.BytesIO(body))
        endpoint = ModelEndpoint(name="lite", base_url="https://gemini.example/v1", model="g-lite",
                                 api_key="secret-key-value", external=True)
        return OpenAICompatibleGateway(endpoint, urlopen=urlopen)

    def test_provider_message_status_and_retry_after(self):
        gw = self._gateway_raising(503, GEMINI_503, {"Retry-After": "7"})
        with self.assertRaises(ModelHTTPError) as ctx:
            gw.complete(system="s", user="u")
        exc = ctx.exception
        self.assertEqual((exc.status, exc.retry_after_seconds, exc.transient), (503, 7.0, True))
        self.assertIn("experiencing high demand", str(exc))
        self.assertNotIn("secret-key-value", str(exc))

    def test_client_errors_are_not_transient(self):
        with self.assertRaises(ModelHTTPError) as ctx:
            self._gateway_raising(400, b'{"error": {"message": "bad request"}}').complete(system="s", user="u")
        self.assertFalse(ctx.exception.transient)
        self.assertIn("bad request", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
