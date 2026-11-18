"""The owner's butcher builds, 2026-11-17 (bld_6323468a, bld_c0b2b43b): rounds were verified, then no model route
answered the repair with valid JSON. The exception ended the whole build -- the verified work was thrown away and the
customer read "no check ran". Now the repair stops ('repair_model_unavailable') and the build ends on its best version
with its real checks. Real loop (AutonomousProductEngine) and the real release-gate verdict; the model and the sandbox
are fakes."""
import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.model_gateway import ModelGatewayError
from omni_prod.repository_patch import parse_patch
from omni_prod.worker_tasks import evaluate_release_gates

ROOT = Path(__file__).resolve().parents[1]
NO_ROUTE = ModelGatewayError("all model routes failed: gemini-3.8-flash: model did not return valid JSON (content "
                             "before the JSON value ...); gpt-6.1-sol: skipped (CREDIT_EXHAUSTED ...)")


def engine(repair_errors):
    class Architect:
        def create_spec(self, prompt): return 'spec'

    class Generator:
        def generate(self, spec): return parse_patch({'files': [{'path': 'app.py', 'content': 'v0'}]})

    class Repairer:
        def __init__(self): self.calls = 0
        def repair(self, **kw):
            self.calls += 1
            err = repair_errors.pop(0) if repair_errors else None
            if err is not None:
                raise err
            return parse_patch({'files': [{'path': 'app.py', 'content': f'v{self.calls}'}]})

    class Executor:
        def execute(self, *, repository, spec):
            return ExecutionReport(False, (AcceptanceFailure('BROWSER', f"uncaught JavaScript error in {repository['app.py']}"),))

    rep = Repairer()
    return AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=rep, executor=Executor(),
                                   max_repair_rounds=3), rep


class NoRouteAnsweredTheRepair(unittest.TestCase):
    def test_the_build_ends_on_its_verified_version_with_its_checks(self):
        eng, rep = engine([None, NO_ROUTE])                  # round 1 repaired, round 2: no route answered
        result = eng.build('p')
        self.assertEqual((result.status, result.stop_reason), ('failed', 'repair_model_unavailable'))
        self.assertEqual(result.repository['app.py'], 'v1')                     # the work of round 1 is kept
        self.assertEqual([f.acceptance_id for f in result.report.failures], ['BROWSER'])   # the real check
        self.assertIn('all model routes failed', eng.repair_model_error)

    def test_the_customer_reads_a_verification_failure_not_no_check_ran(self):
        eng, _ = engine([NO_ROUTE])
        result = eng.build('p')
        ok, code, message = evaluate_release_gates(result=result, quality=None, security=None, rights=None)
        self.assertEqual((ok, code), (False, 'verification_failed'))
        self.assertIn('stopped repairing: no model returned a valid repair', message)
        self.assertIn('BROWSER', message)

    def test_any_other_error_still_ends_the_build(self):
        eng, _ = engine([RuntimeError('a bug')])
        with self.assertRaises(RuntimeError):
            eng.build('p')
        eng, _ = engine([ModelGatewayError('budget exceeded for this build')])
        with self.assertRaises(ModelGatewayError):
            eng.build('p')

    def test_the_screen_says_why_the_repair_stopped(self):
        js = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
        self.assertEqual(len(re.findall(r"repair_model_unavailable:'", js)), 2)             # Hebrew and English



class NoRouteAnsweredBecauseOfCredit(unittest.TestCase):
    """2026-11-18: a route that answered "no credit" in the call makes the router raise ProviderQuotaUnavailable,
    whose message lacks "all model routes failed"; the catch above missed it. Real RoutedModelGateway: one route has no
    credit (Anthropic's own HTTP 400 text), the other answers prose instead of JSON; only the transport is a fake."""

    def _routed_repairer(self):
        import json as _json
        import os
        from decimal import Decimal
        from unittest import mock
        from omni_prod.model_catalog import parse_model_catalog
        from omni_prod.model_gateway import ModelHTTPError
        from omni_prod.model_policy import ModelUsePolicy
        from omni_prod.model_router import RoutingPolicy
        from omni_prod.routed_gateway import RoutedModelGateway
        catalog = [{"name": n, "provider": n, "base_url": f"https://{n}.example/v1", "model": f"m-{n}",
                    "api_key_env": "KEY_REPAIR", "quality": 90, "input_per_million": "1", "output_per_million": "2"}
                   for n in ("nocredit", "prose")]

        class Transport:
            def __init__(self, endpoint):
                self.endpoint, self.last_usage, self.last_response_model = endpoint, None, None

            def complete_json(self, **kw):
                if self.endpoint.name == 'nocredit':
                    raise ModelHTTPError('model request failed: HTTP 400: Your credit balance is too low to access '
                                         'the Anthropic API.', status=400)
                raise ModelGatewayError('model did not return valid JSON (content before the JSON value)')
        env = mock.patch.dict(os.environ, {'OMNI_MODEL_TASK_MIN_QUALITY': '{"repair": 0}'})
        env.start()
        self.addCleanup(env.stop)
        gw = RoutedModelGateway(ranked=parse_model_catalog(_json.dumps(catalog), {"KEY_REPAIR": "k"}),
                                routing_policy=RoutingPolicy(minimum_quality=70),
                                policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                      external_budget_usd=Decimal('5'), max_external_calls_per_build=50),
                                gateway_factory=Transport, transient_retries=0)

        class Repairer:
            def __init__(self): self.calls = 0
            def repair(self, **kw):
                self.calls += 1
                if self.calls == 1:
                    return parse_patch({'files': [{'path': 'app.py', 'content': 'v1'}]})
                gw.complete_json(system='S', user='U', max_tokens=300, task='repair')
        return Repairer()

    def test_a_credit_failure_in_the_repair_call_keeps_the_verified_version(self):
        from omni_prod.model_gateway import ProviderQuotaUnavailable
        eng, _ = engine([])
        eng.repairer = self._routed_repairer()
        result = eng.build('p')
        self.assertEqual((result.status, result.stop_reason), ('failed', 'repair_model_unavailable'))
        self.assertEqual(result.repository['app.py'], 'v1')                     # round 1's work is kept
        self.assertIn('quota/credits unavailable', eng.repair_model_error)    # the router raised the quota error
        ok, code, _ = evaluate_release_gates(result=result, quality=None, security=None, rights=None)
        self.assertEqual((ok, code), (False, 'verification_failed'))
        with self.assertRaises(ProviderQuotaUnavailable):                     # and that is the type it raises
            eng.repairer.repair()

    def test_any_other_model_error_still_ends_the_build(self):
        eng, _ = engine([ModelGatewayError('model request failed: something else')])
        with self.assertRaises(ModelGatewayError):
            eng.build('p')


if __name__ == '__main__':
    unittest.main()
