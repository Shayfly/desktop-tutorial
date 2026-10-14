"""M5 remediation: one conservative quote covers LLM + required capabilities +
generated-app infrastructure + retry before any paid external effect.

All providers are in-test doubles; this proves the money path, not that any
real provider was called.
"""
from __future__ import annotations

import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from omni_prod import worker_tasks
from omni_prod.build_cost_plan import (
    CostQuoteUnknown,
    build_economics_quote,
    collect_build_cost_inputs,
    reserve_and_enqueue,
)
from omni_prod.capability_executor import CapabilityExecutionAssignment
from omni_prod.capability_repository import MemoryCapabilityRepository
from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.capability_worker import CapabilityStageBlocked, DurableCapabilityBuildStage
from omni_prod.infrastructure_contracts import (
    BindingStatus, InfrastructureBinding, InfrastructureKind, InfrastructureQuote, deterministic_resource_name,
    provisioning_idempotency_key)
from omni_prod.infrastructure_provisioner import InfrastructureProvisioningService, MemoryInfrastructureBindingRepository
from omni_prod.model_gateway import ModelEndpoint
from omni_prod.model_policy import ModelPolicyViolation, ModelUsePolicy, ModelUseState, authorize_model_call
from omni_prod.product_architect import ProductArchitect
from omni_prod.provider_contracts import ProviderQuote
from omni_prod.provider_pricing import enforce_margin_floor
from omni_prod.subscription_store import PostgresSubscriptionService

PROMPT = ("Build a barbershop booking SaaS for admin, barber and customer users. Customers book appointments, "
          "barbers manage their calendar, data in Postgres, require login, file uploads, scheduled reminders "
          "and outbound email notifications, with a generated logo and hero image.")
# The product explicitly asks for generated visuals: image generation is a
# requirement only when the product asks for it (decision 2026-10-07 #28).

D = Decimal


def llm_quote(maximum="0.30"):
    return ProviderQuote("model-router", "software.code.generate", D("0"), D(maximum), "runtime-model-policy-v1",
                         "build-budget", D("1"))


def image_assignment(requirement_id="cap-media-image-generate", est="0.003", maximum="0.01"):
    quote = ProviderQuote("image-predictions", "media.image.generate", D(est), D(maximum), "operator-config:p", "image", D("1"))
    return {requirement_id: CapabilityExecutionAssignment(provider="image-predictions", quote=quote)}


def infra_quotes(contract, est="0.02", maximum="0.05"):
    return [InfrastructureQuote(profile_key="managed_web_saas_v1", kind=r.kind, environment="preview",
                                estimated_monthly_usd=None, maximum_monthly_usd=None, basis="test",
                                provisioning_estimated_usd=D(est), provisioning_maximum_usd=D(maximum))
            for r in contract.infrastructure]


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.contract = ProductArchitect().compile(PROMPT, project_id="prj_econ", contract_version=1)
        self.image_req = next(r for r in self.contract.capability_plan.requirements if r.key == "media.image.generate")

    def quote(self, *, assignments=None, infra=None, retry="0.05", revenue="2.00", margin="0.20", platform="0"):
        inputs = collect_build_cost_inputs(
            self.contract, capability_assignments=assignments or {}, infrastructure_quotes=infra or [],
            require_capability_quotes=assignments is not None)
        return build_economics_quote(
            llm_quotes=(llm_quote(),), cost_inputs=inputs, platform_infrastructure_estimated_usd=D(platform),
            platform_infrastructure_maximum_usd=D(platform), retry_reserve_usd=D(retry),
            revenue_usd=None if revenue is None else D(revenue), minimum_margin=None if margin is None else D(margin))


class QuoteCompositionTests(_Fixture):
    def test_1_llm_only(self):
        quote, components = self.quote()
        self.assertEqual(quote.total_authorized_variable_usd, D("0.35"))
        self.assertEqual(components["llm_maximum_usd"], "0.30")
        self.assertEqual(components["capability_maximum_usd"], "0")
        self.assertEqual(components["generated_app_infrastructure_maximum_usd"], "0")

    def test_2_llm_plus_image(self):
        quote, components = self.quote(assignments=image_assignment(self.image_req.id))
        self.assertEqual(quote.total_authorized_variable_usd, D("0.36"))
        self.assertEqual(components["capability_maximum_usd"], "0.01")
        self.assertEqual(components["capabilities"][0]["capability_key"], "media.image.generate")

    def test_3_llm_plus_infrastructure(self):
        quote, components = self.quote(infra=infra_quotes(self.contract))
        self.assertEqual(components["generated_app_infrastructure_maximum_usd"], "0.25")  # 5 kinds x 0.05
        self.assertEqual(quote.total_authorized_variable_usd, D("0.60"))

    def test_4_llm_plus_image_plus_infrastructure(self):
        quote, components = self.quote(assignments=image_assignment(self.image_req.id), infra=infra_quotes(self.contract))
        self.assertEqual(quote.total_authorized_variable_usd, D("0.61"))
        self.assertEqual(D(components["capability_authorization_usd"]), D("0.01"))
        self.assertEqual(sum(D(components[k]) for k in ("llm_maximum_usd", "capability_maximum_usd",
                                                        "generated_app_infrastructure_maximum_usd",
                                                        "platform_infrastructure_maximum_usd",
                                                        "retry_reserve_usd")), quote.total_authorized_variable_usd)

    def test_required_capability_without_quote_blocks(self):
        with self.assertRaises(CostQuoteUnknown) as ctx:
            collect_build_cost_inputs(self.contract, capability_assignments={}, infrastructure_quotes=[],
                                      require_capability_quotes=True)
        self.assertIn("media.image.generate", str(ctx.exception))

    def test_unknown_infrastructure_quote_blocks(self):
        unknown = [InfrastructureQuote(profile_key="managed_web_saas_v1", kind="database", environment="preview",
                                       estimated_monthly_usd=None, maximum_monthly_usd=None, basis="unknown")]
        with self.assertRaises(CostQuoteUnknown) as ctx:
            collect_build_cost_inputs(self.contract, capability_assignments={}, infrastructure_quotes=unknown)
        self.assertIn("database", str(ctx.exception))

    def test_optional_unassigned_capability_is_not_priced(self):
        optional = CapabilityRequirement(id="cap-ai-agent-eval", key="ai.agent.eval", purpose="eval", required=False)
        plan = CapabilityPlan(requirements=self.contract.capability_plan.requirements + (optional,), target_keys=())
        contract = SimpleNamespace(capability_plan=plan, infrastructure=self.contract.infrastructure)
        inputs = collect_build_cost_inputs(contract, capability_assignments=image_assignment(self.image_req.id),
                                           infrastructure_quotes=[], require_capability_quotes=True)
        self.assertIn("cap-ai-agent-eval", inputs.skipped_optional)
        self.assertEqual([c[1] for c in inputs.capability_quotes], ["media.image.generate"])

    def test_live_bindings_are_reused_at_zero_cost(self):
        repo = MemoryInfrastructureBindingRepository()
        for r in self.contract.infrastructure:
            key = provisioning_idempotency_key(profile_key="managed_web_saas_v1", project_id="prj_econ",
                                               environment="preview", kind=r.kind)
            repo.save(InfrastructureBinding(
                binding_id="ib_" + key[:10], profile_key="managed_web_saas_v1", tenant_id="usr_1",
                project_id="prj_econ", environment="preview", kind=r.kind, status=BindingStatus.LIVE,
                resource_name=deterministic_resource_name(project_id="prj_econ", environment="preview", kind=r.kind),
                idempotency_key=key, provisioner="p", secret_references={"x": "vault:secret/data/x"}))
        provisioner = MagicMock()
        service = InfrastructureProvisioningService(provisioner=provisioner, repository=repo)
        quotes = service.cost_quotes(self.contract, tenant_id="usr_1", project_id="prj_econ", environment="preview")
        self.assertEqual({q.provisioning_maximum_usd for q in quotes}, {D("0")})
        provisioner.quote.assert_not_called()


class MarginAndReservationTests(_Fixture):
    def test_5_image_quote_pushes_build_over_margin_floor_before_any_provider_call(self):
        expensive = image_assignment(self.image_req.id, est="0.80", maximum="1.40")
        quote, _ = self.quote(assignments=expensive, revenue="2.00", margin="0.20")
        submit = MagicMock()
        enqueue = MagicMock()
        reserve = MagicMock()
        with self.assertRaises(PermissionError):
            reserve_and_enqueue(quote=enforce_margin_floor(quote), reserve=reserve, enqueue=enqueue)
        reserve.assert_not_called(); enqueue.assert_not_called(); submit.assert_not_called()

    def test_9_no_paid_provider_is_called_if_total_reservation_fails(self):
        quote, _ = self.quote(assignments=image_assignment(self.image_req.id), infra=infra_quotes(self.contract))
        reserve = MagicMock(return_value=SimpleNamespace(allowed=False, reason="paid-provider budget exhausted"))
        enqueue = MagicMock()
        with self.assertRaises(PermissionError) as ctx:
            reserve_and_enqueue(quote=quote, reserve=reserve, enqueue=enqueue)
        self.assertIn("budget exhausted", str(ctx.exception))
        reserve.assert_called_once_with(quote.total_authorized_variable_usd)  # the full total, in one reservation
        enqueue.assert_not_called()

    def test_successful_reservation_covers_the_full_total_once(self):
        quote, _ = self.quote(assignments=image_assignment(self.image_req.id), infra=infra_quotes(self.contract))
        reserve = MagicMock(return_value=SimpleNamespace(allowed=True, reason="authorized"))
        enqueue = MagicMock()
        reserve_and_enqueue(quote=quote, reserve=reserve, enqueue=enqueue)
        reserve.assert_called_once_with(D("0.61"))
        enqueue.assert_called_once()


class WorkerAuthorizationTests(_Fixture):
    def test_capability_stage_receives_only_its_priced_slice_not_the_llm_reservation(self):
        quote, components = self.quote(assignments=image_assignment(self.image_req.id))
        request = {"authorized_provider_cost_usd": quote.total_authorized_variable_usd,
                   "economics_quote": {**quote.to_dict(), "components": components}}
        self.assertEqual(worker_tasks.capability_authorization_ceiling(request), D("0.01"))
        legacy = {"authorized_provider_cost_usd": D("0.30"), "economics_quote": quote.to_dict()}
        self.assertEqual(worker_tasks.capability_authorization_ceiling(legacy), D("0.30"))

    def test_8_retries_cannot_exceed_authorized_ceiling(self):
        # model: the whole-build external budget is the reserved LLM maximum
        policy = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                external_budget_usd=D("0.30"), max_external_calls_per_build=10)
        state = ModelUseState()
        ext = ModelEndpoint(name="ext", base_url="https://api.example", model="m", api_key="k", external=True)
        for _ in range(3):
            authorize_model_call(endpoint=ext, policy=policy, state=state, estimated_cost_usd=D("0.10"))
        with self.assertRaises(ModelPolicyViolation):
            authorize_model_call(endpoint=ext, policy=policy, state=state, estimated_cost_usd=D("0.10"))
        # capability: a runtime assignment above the reserved slice is refused before submit
        stage = DurableCapabilityBuildStage(
            repository=MemoryCapabilityRepository(), executor=MagicMock(),
            assignments_resolver=lambda plan: image_assignment(self.image_req.id, maximum="0.02"))
        plan = CapabilityPlan(requirements=(self.image_req,), target_keys=())
        with self.assertRaises(CapabilityStageBlocked):
            stage.prepare(build_id="b1", project_id="p", plan=plan, authorized_maximum_usd=D("0.01"), now=0.0)
        stage.executor.execute_plan.assert_not_called()


class SettlementTests(_Fixture):
    def _gateway(self, calls=0):
        return SimpleNamespace(state=SimpleNamespace(external_spend_usd=D("0"), external_calls=calls))

    def test_6_missing_image_actual_keeps_actual_null(self):
        subs = MagicMock(); subs.settle.return_value = {}
        evidence = {"usage": [{"actual_cost_usd": None, "estimated_cost_usd": D("0.003")}]}
        _, _, actual = worker_tasks.resolve_m5_billing(
            subs, build_id="b", ready=True, gateway=self._gateway(), capability_evidence=evidence,
            economics_quote={"revenue_usd": "2.00", "infrastructure_maximum_usd": "0"})
        self.assertIsNone(actual)
        self.assertIsNone(subs.settle.call_args.kwargs["actual_provider_cost_usd"])

    def test_unknown_infrastructure_actual_keeps_total_actual_null(self):
        subs = MagicMock(); subs.settle.return_value = {}
        evidence = {"usage": [{"actual_cost_usd": D("0.004")}]}
        _, _, actual = worker_tasks.resolve_m5_billing(
            subs, build_id="b", ready=True, gateway=self._gateway(), capability_evidence=evidence,
            economics_quote={"revenue_usd": "2.00", "infrastructure_maximum_usd": "0.25"})
        self.assertIsNone(actual)  # infra provisioning actual is not reported
        self.assertIsNone(subs.settle.call_args.kwargs["revenue_usd"])  # no contribution from estimates

    def test_7_actual_lower_than_reserved_releases_unused_reservation(self):
        class Cur:
            def __init__(self): self.calls = []; self.rows = [("u1", "RESERVED", D("0.61"), "customer_plan")]
            def execute(self, sql, params=None): self.calls.append((" ".join(sql.split()), params))
            def fetchone(self): return self.rows.pop(0) if self.rows else None
            def __enter__(self): return self
            def __exit__(self, *a): return False
        cur = Cur()

        class Ctx:
            def __enter__(self_): return self_
            def __exit__(self_, *a): return False
            def cursor(self_): return cur
            def transaction(self_): return Ctx()

        pool = SimpleNamespace(connection=lambda: Ctx())
        result = PostgresSubscriptionService(pool=pool).settle(build_id="b", actual_provider_cost_usd=D("0.014"))
        refund = next(c for c in cur.calls if c[0].startswith("UPDATE creator_subscriptions SET provider_spend_usd = GREATEST"))
        self.assertEqual(refund[1][0], D("0.596"))  # 0.61 reserved - 0.014 actual is released
        self.assertEqual(result["provider_cost_truth"], "ACTUAL")


if __name__ == "__main__":
    unittest.main()
