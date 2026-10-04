"""M5 Task 6: provider-neutral generated-app infrastructure contracts.

These tests pin the contract layer only. No real infrastructure is touched:
the provisioners used here are deterministic test doubles defined in this
file, and nothing here may be read as evidence that any infrastructure is
LIVE in a real environment.
"""
from __future__ import annotations

import unittest
from decimal import Decimal

from omni_prod.build_contract import InfrastructureRequirement
from omni_prod.infrastructure_contracts import (
    BindingStatus,
    InfrastructureBinding,
    InfrastructureEnvironment,
    InfrastructureKind,
    InfrastructureQuote,
    deterministic_resource_name,
    evaluate_infrastructure_readiness,
    provisioning_idempotency_key,
)
from omni_prod.infrastructure_registry import (
    MANAGED_WEB_SAAS_V1,
    InfrastructureProfileRegistry,
    profile_for_contract,
)
from omni_prod.infrastructure_provisioner import (
    InfrastructureProvisioningService,
    InfrastructureStageBlocked,
    MemoryInfrastructureBindingRepository,
    UnconfiguredInfrastructureProvisioner,
)
from omni_prod.models import BuildStatus
from omni_prod.product_architect import ProductArchitect
try:
    from tests.m5_worker_harness import ContractBuildHarness
except ModuleNotFoundError:  # unittest discover -s tests puts tests/ itself on sys.path
    from m5_worker_harness import ContractBuildHarness


PROMPT = (
    "Build a travel agency CRM SaaS for admin and travel-agent users. "
    "Manage customers and bookings in Postgres, require login, file uploads, "
    "scheduled follow-ups and outbound email notifications."
)


class _CountingProvisioner:
    """Test double: records every external provision call."""

    name = "test-provisioner"
    profile_key = "managed_web_saas_v1"

    def __init__(self, *, status: BindingStatus = BindingStatus.LIVE, kinds=None):
        self.calls: list[tuple] = []
        self.revoked: list[str] = []
        self._status = status
        self.supported_kinds = tuple(kinds or InfrastructureKind)

    def quote(self, requirement, *, project_id, environment):
        return InfrastructureQuote(
            profile_key=self.profile_key, kind=InfrastructureKind(requirement.kind),
            environment=environment, estimated_monthly_usd=Decimal("0"),
            maximum_monthly_usd=Decimal("0"), basis="test",
        )

    def provision(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
        kind = InfrastructureKind(requirement.kind)
        self.calls.append((kind, project_id, environment, idempotency_key))
        name = deterministic_resource_name(project_id=project_id, environment=environment, kind=kind)
        refs = {}
        if self._status == BindingStatus.LIVE:
            refs = {"primary": f"vault:secret/data/148ai/test/{name}"}
        return InfrastructureBinding(
            binding_id="ib_" + idempotency_key[:20], profile_key=self.profile_key,
            tenant_id=tenant_id, project_id=project_id, environment=environment, kind=kind,
            status=self._status, resource_name=name, idempotency_key=idempotency_key,
            provisioner=self.name, secret_references=refs,
            public_config={"resource": name}, evidence={"double": True},
        )

    def status(self, binding):
        return binding

    def revoke(self, binding):
        self.revoked.append(binding.binding_id)
        return binding.revoked()

    def readiness(self):
        return {kind.value: self._status.value for kind in self.supported_kinds}


class InfrastructureKindAndProfileTests(unittest.TestCase):
    def test_canonical_kinds_match_build_contract_infrastructure(self):
        contract = ProductArchitect().compile(PROMPT, project_id="prj_a", contract_version=1)
        kinds = {item.kind for item in contract.infrastructure}
        self.assertEqual(kinds, {k.value for k in InfrastructureKind})

    def test_managed_web_saas_v1_requires_all_five_kinds(self):
        required = {r.kind for r in MANAGED_WEB_SAAS_V1.requirements if r.required}
        self.assertEqual(required, {"database", "auth_session", "object_storage", "scheduled_http", "outbound"})
        self.assertEqual(MANAGED_WEB_SAAS_V1.key, "managed_web_saas_v1")

    def test_dependency_closure_is_deterministic_and_dependency_first(self):
        closure_a = MANAGED_WEB_SAAS_V1.dependency_closure(("auth_session", "scheduled_http"))
        closure_b = MANAGED_WEB_SAAS_V1.dependency_closure(("scheduled_http", "auth_session"))
        self.assertEqual(closure_a[0], InfrastructureKind.DATABASE)
        self.assertIn(InfrastructureKind.AUTH_SESSION, closure_a)
        self.assertIn(InfrastructureKind.SCHEDULED_HTTP, closure_a)
        self.assertEqual(set(closure_a), set(closure_b))
        self.assertEqual(closure_a, MANAGED_WEB_SAAS_V1.dependency_closure(("auth_session", "scheduled_http")))
        self.assertEqual(len(closure_a), len(set(closure_a)))

    def test_full_profile_order_is_stable(self):
        full = MANAGED_WEB_SAAS_V1.dependency_closure(tuple(k.value for k in InfrastructureKind))
        self.assertEqual(full, MANAGED_WEB_SAAS_V1.ordered_kinds())
        self.assertLess(full.index(InfrastructureKind.DATABASE), full.index(InfrastructureKind.AUTH_SESSION))

    def test_unknown_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            MANAGED_WEB_SAAS_V1.dependency_closure(("quantum_cache",))

    def test_registry_rejects_vendor_names_in_canonical_keys(self):
        registry = InfrastructureProfileRegistry()
        self.assertIs(registry.get("managed_web_saas_v1"), MANAGED_WEB_SAAS_V1)
        with self.assertRaises(ValueError):
            registry.validate_canonical_key("supabase_saas_v1")
        with self.assertRaises(ValueError):
            registry.validate_canonical_key("vercel_web_v1")
        registry.validate_canonical_key("managed_web_saas_v2")

    def test_profile_for_contract(self):
        contract = ProductArchitect().compile(PROMPT, project_id="prj_a", contract_version=1)
        self.assertIs(profile_for_contract(contract), MANAGED_WEB_SAAS_V1)


class BindingContractTests(unittest.TestCase):
    def _binding(self, **overrides):
        data = dict(
            binding_id="ib_1", profile_key="managed_web_saas_v1", tenant_id="usr_1",
            project_id="prj_1", environment=InfrastructureEnvironment.PREVIEW,
            kind=InfrastructureKind.DATABASE, status=BindingStatus.LIVE,
            resource_name="ga_x_preview_database", idempotency_key="k" * 64,
            provisioner="p", secret_references={"database_url": "vault:secret/data/148ai/x"},
            public_config={"schema": "ga_x"}, evidence={},
        )
        data.update(overrides)
        return InfrastructureBinding(**data)

    def test_secret_values_are_rejected_only_references_allowed(self):
        with self.assertRaises(ValueError):
            self._binding(secret_references={"database_url": "postgresql://u:pw@h/db"})
        with self.assertRaises(ValueError):
            self._binding(secret_references={"token": "env:"})
        self._binding(secret_references={"database_url": "env:GENAPP_DB_URL"})

    def test_public_config_cannot_carry_secret_material(self):
        with self.assertRaises(ValueError):
            self._binding(public_config={"password": "hunter2"})
        with self.assertRaises(ValueError):
            self._binding(public_config={"dsn": "postgresql://u:pw@host/db"})
        with self.assertRaises(ValueError):
            self._binding(public_config={"note": "Bearer abc.def"})

    def test_live_binding_requires_secret_reference_or_explicit_none(self):
        with self.assertRaises(ValueError):
            self._binding(secret_references={}, public_config={})

    def test_public_dict_never_contains_reference_targets(self):
        public = self._binding().to_public_dict()
        self.assertNotIn("vault:secret/data/148ai/x", repr(public))
        self.assertEqual(public["secret_reference_names"], ["database_url"])
        self.assertEqual(public["status"], "LIVE")

    def test_revoked_binding_is_not_live(self):
        revoked = self._binding().revoked(at="2026-10-04T00:00:00Z")
        self.assertEqual(revoked.status, BindingStatus.REVOKED)
        self.assertEqual(revoked.revoked_at, "2026-10-04T00:00:00Z")


class NamingAndIdempotencyTests(unittest.TestCase):
    def test_resource_names_are_deterministic_and_environment_scoped(self):
        a = deterministic_resource_name(project_id="prj_1", environment="preview", kind="database")
        b = deterministic_resource_name(project_id="prj_1", environment="preview", kind="database")
        c = deterministic_resource_name(project_id="prj_1", environment="production", kind="database")
        d = deterministic_resource_name(project_id="prj_2", environment="preview", kind="database")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(a, d)
        self.assertRegex(a, r"^[a-z][a-z0-9_]{0,62}$")
        self.assertNotIn("prj_1", a)  # project ids are hashed, never embedded verbatim

    def test_idempotency_key_binds_profile_project_environment_kind(self):
        base = dict(profile_key="managed_web_saas_v1", project_id="prj_1", environment="preview", kind="database")
        k1 = provisioning_idempotency_key(**base)
        self.assertEqual(k1, provisioning_idempotency_key(**base))
        for field, value in (("profile_key", "managed_web_saas_v2"), ("project_id", "prj_2"),
                             ("environment", "production"), ("kind", "object_storage")):
            changed = dict(base, **{field: value})
            self.assertNotEqual(k1, provisioning_idempotency_key(**changed))


class ReadinessGateTests(unittest.TestCase):
    def setUp(self):
        self.contract = ProductArchitect().compile(PROMPT, project_id="prj_gate", contract_version=1)

    def _live(self, provisioner, environment="preview", project_id="prj_gate"):
        repo = MemoryInfrastructureBindingRepository()
        service = InfrastructureProvisioningService(provisioner=provisioner, repository=repo)
        return service, repo, service.ensure(
            self.contract, tenant_id="usr_1", project_id=project_id, environment=environment)

    def test_all_required_live_bindings_make_infrastructure_ready(self):
        _, _, result = self._live(_CountingProvisioner())
        self.assertTrue(result.ready)
        self.assertEqual(result.missing_kinds, ())
        self.assertEqual(result.profile_key, "managed_web_saas_v1")
        self.assertEqual(set(result.to_dict()["bindings"]), {k.value for k in InfrastructureKind})

    def test_missing_required_binding_blocks_ready(self):
        bindings = ()
        result = evaluate_infrastructure_readiness(
            self.contract.infrastructure, bindings, project_id="prj_gate", environment="preview")
        self.assertFalse(result.ready)
        self.assertEqual(set(result.missing_kinds), {k for k in InfrastructureKind})

    def test_not_configured_provisioner_blocks_with_explicit_status(self):
        service = InfrastructureProvisioningService(
            provisioner=UnconfiguredInfrastructureProvisioner(reason="no generated-app infrastructure configured"),
            repository=MemoryInfrastructureBindingRepository())
        result = service.ensure(self.contract, tenant_id="usr_1", project_id="prj_gate", environment="preview")
        self.assertFalse(result.ready)
        self.assertEqual({b["status"] for b in result.to_dict()["bindings"].values()}, {"NOT_CONFIGURED"})
        with self.assertRaises(InfrastructureStageBlocked) as ctx:
            service.require_ready(self.contract, tenant_id="usr_1", project_id="prj_gate", environment="preview")
        self.assertIn("NOT_CONFIGURED", str(ctx.exception))
        self.assertFalse(ctx.exception.evidence["ready"])

    def test_optional_missing_binding_does_not_block(self):
        reqs = (
            InfrastructureRequirement("database", "data"),
            InfrastructureRequirement("outbound", "email", required=False),
        )
        prov = _CountingProvisioner(kinds=(InfrastructureKind.DATABASE,))
        repo = MemoryInfrastructureBindingRepository()
        binding = prov.provision(reqs[0], tenant_id="t", project_id="p", environment="preview",
                                 idempotency_key=provisioning_idempotency_key(
                                     profile_key="managed_web_saas_v1", project_id="p",
                                     environment="preview", kind="database"))
        repo.save(binding)
        result = evaluate_infrastructure_readiness(reqs, (binding,), project_id="p", environment="preview")
        self.assertTrue(result.ready)

    def test_binding_owned_by_other_project_or_environment_is_rejected(self):
        _, repo, _ = self._live(_CountingProvisioner(), project_id="prj_other")
        foreign = repo.list_for(project_id="prj_other", environment="preview")
        result = evaluate_infrastructure_readiness(
            self.contract.infrastructure, foreign, project_id="prj_gate", environment="preview")
        self.assertFalse(result.ready)
        self.assertTrue(result.ownership_violations)
        _, repo2, _ = self._live(_CountingProvisioner(), environment="production")
        prod = repo2.list_for(project_id="prj_gate", environment="production")
        result = evaluate_infrastructure_readiness(
            self.contract.infrastructure, prod, project_id="prj_gate", environment="preview")
        self.assertFalse(result.ready)

    def test_provisioning_is_idempotent(self):
        prov = _CountingProvisioner()
        repo = MemoryInfrastructureBindingRepository()
        service = InfrastructureProvisioningService(provisioner=prov, repository=repo)
        first = service.ensure(self.contract, tenant_id="usr_1", project_id="prj_gate", environment="preview")
        calls_after_first = len(prov.calls)
        second = service.ensure(self.contract, tenant_id="usr_1", project_id="prj_gate", environment="preview")
        self.assertEqual(calls_after_first, len(InfrastructureKind))
        self.assertEqual(len(prov.calls), calls_after_first)  # no second external provision
        self.assertEqual(first.to_dict()["bindings"], second.to_dict()["bindings"])

    def test_not_configured_binding_is_retried_once_configured(self):
        repo = MemoryInfrastructureBindingRepository()
        InfrastructureProvisioningService(
            provisioner=UnconfiguredInfrastructureProvisioner(reason="absent"), repository=repo,
        ).ensure(self.contract, tenant_id="usr_1", project_id="prj_gate", environment="preview")
        prov = _CountingProvisioner()
        result = InfrastructureProvisioningService(provisioner=prov, repository=repo).ensure(
            self.contract, tenant_id="usr_1", project_id="prj_gate", environment="preview")
        self.assertTrue(result.ready)
        self.assertEqual(len(prov.calls), len(InfrastructureKind))

    def test_preview_and_production_get_distinct_bindings(self):
        prov = _CountingProvisioner()
        repo = MemoryInfrastructureBindingRepository()
        service = InfrastructureProvisioningService(provisioner=prov, repository=repo)
        service.ensure(self.contract, tenant_id="usr_1", project_id="prj_gate", environment="preview")
        service.ensure(self.contract, tenant_id="usr_1", project_id="prj_gate", environment="production")
        preview = {b.kind: b for b in repo.list_for(project_id="prj_gate", environment="preview")}
        prod = {b.kind: b for b in repo.list_for(project_id="prj_gate", environment="production")}
        for kind in InfrastructureKind:
            self.assertNotEqual(preview[kind].resource_name, prod[kind].resource_name)
            self.assertNotEqual(preview[kind].idempotency_key, prod[kind].idempotency_key)
            self.assertFalse(set(preview[kind].secret_references.values())
                             & set(prod[kind].secret_references.values()))

    def test_revoke_makes_project_not_ready(self):
        prov = _CountingProvisioner()
        service, repo, result = self._live(prov)
        self.assertTrue(result.ready)
        service.revoke_all(project_id="prj_gate", environment="preview")
        self.assertEqual(len(prov.revoked), len(InfrastructureKind))
        again = evaluate_infrastructure_readiness(
            self.contract.infrastructure, repo.list_for(project_id="prj_gate", environment="preview"),
            project_id="prj_gate", environment="preview")
        self.assertFalse(again.ready)

    def test_tenant_cannot_take_over_existing_binding(self):
        prov = _CountingProvisioner()
        repo = MemoryInfrastructureBindingRepository()
        service = InfrastructureProvisioningService(provisioner=prov, repository=repo)
        service.ensure(self.contract, tenant_id="usr_1", project_id="prj_gate", environment="preview")
        with self.assertRaises(PermissionError):
            service.ensure(self.contract, tenant_id="usr_2", project_id="prj_gate", environment="preview")


class WorkerInfrastructureGateTests(unittest.TestCase):
    """A bound durable build must not become READY without required infrastructure."""

    def test_worker_fails_closed_before_generation_when_infrastructure_missing(self):
        contract = ProductArchitect().compile(PROMPT, project_id="prj_gate", contract_version=1)
        harness = ContractBuildHarness(contract)
        stage = InfrastructureProvisioningService(
            provisioner=UnconfiguredInfrastructureProvisioner(reason="absent"),
            repository=MemoryInfrastructureBindingRepository(),
        )
        with self.assertRaises(InfrastructureStageBlocked):
            harness.run(infrastructure_stage=stage)
        final = harness.jobs.transitions[-1]
        self.assertEqual(final["target"], BuildStatus.FAILED)
        self.assertEqual(final["error_code"], "infrastructure_not_configured")
        self.assertFalse(final["evidence_json"]["infrastructure"]["ready"])
        self.assertEqual(harness.engine_builds, 0)  # no paid generation attempted

    def test_worker_reaches_ready_with_live_infrastructure(self):
        contract = ProductArchitect().compile(PROMPT, project_id="prj_gate", contract_version=1)
        harness = ContractBuildHarness(contract)
        stage = InfrastructureProvisioningService(
            provisioner=_CountingProvisioner(), repository=MemoryInfrastructureBindingRepository())
        result = harness.run(infrastructure_stage=stage)
        self.assertEqual(result, "ready")
        evidence = harness.jobs.transitions[-1]["evidence_json"]
        self.assertTrue(evidence["infrastructure"]["ready"])
        self.assertEqual(evidence["infrastructure"]["environment"], "preview")


if __name__ == "__main__":
    unittest.main()
