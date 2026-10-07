"""Capabilities are demand-driven, not product-family defaults (founder
principle 2026-10-07). A Web/SaaS contract includes only the infrastructure the
product asks for; nothing unrequired is quoted, provisioned or reserved; a
required but unpriceable/unconfigured kind blocks explicitly; nothing is faked.

Founder acceptance cases:
  1 self-contained Web/SaaS   2 product requiring Postgres
  3 product requiring email   4 mixed requirements
"""
import json
import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.build_cost_plan import CostQuoteUnknown, collect_build_cost_inputs
from omni_prod.creator_plan import build_plan_preview
from omni_prod.infrastructure_provisioner import (InfrastructureProvisioningService, InfrastructureStageBlocked,
                                                  MemoryInfrastructureBindingRepository)
from omni_prod.product_architect import ProductArchitect
from omni_prod.providers.managed_web_saas import build_managed_web_saas_provisioner
from omni_prod.web_saas_acceptance import HttpResponse, WebSaaSAcceptanceRunner, acceptance_scope
from omni_prod.worker_tasks import _CONTRACT_SCOPE_FOR_VERSION_SQL, contract_scope_for_version

TASK_TRACKER = ("Build a team task tracker web app: users sign up and log in, create projects, add tasks with "
                "title, due date and status, assign tasks to teammates, and see a dashboard of overdue tasks.")
POSTGRES = "Build a team task tracker web app with login, projects and tasks, storing all data in Postgres."
EMAIL = "Build a team task tracker web app with login, projects and tasks that sends an email when a task is assigned."
MIXED = ("Build a team task tracker web app with login, projects and tasks, file uploads on tasks and "
         "email notifications when a task is assigned.")


def _contract(prompt):
    return ProductArchitect().compile(prompt, project_id="prj_dd", contract_version=1)


def _modes(contract):
    return {r.kind: r.connection_mode for r in contract.infrastructure}


def _service(repo=None):
    # Real production provisioner wiring with nothing configured (the Preview
    # situation): no provisioning price, no secret store.
    return InfrastructureProvisioningService(provisioner=build_managed_web_saas_provisioner(env={}),
                                             repository=repo or MemoryInfrastructureBindingRepository())


def _quote(contract, service=None):
    service = service or _service()
    return collect_build_cost_inputs(
        contract, capability_assignments={}, require_capability_quotes=True, require_infrastructure_quotes=True,
        infrastructure_quotes=service.cost_quotes(contract, tenant_id="t", project_id="prj_dd", environment="preview"))


class Case1SelfContained(unittest.TestCase):
    def test_plan_requires_no_managed_infrastructure(self):
        c = _contract(TASK_TRACKER)
        self.assertEqual(_modes(c), {"database": "SELF_CONTAINED", "auth_session": "SELF_CONTAINED"})
        self.assertEqual(c.product_family, "self_contained_web_v1")
        self.assertIn("SQLite (sqlite3)", c.product_spec.stack)
        self.assertNotIn("FastAPI", " ".join(c.product_spec.stack))                  # consistent with stdlib-only #25

    def test_quote_succeeds_without_provisioning_price_and_nothing_is_provisioned(self):
        self.assertNotIn("OMNI_GENAPP_PROVISIONING_MAXIMUM_USD", os.environ)
        c, repo = _contract(TASK_TRACKER), MemoryInfrastructureBindingRepository()
        inputs = _quote(c, _service(repo))
        self.assertEqual(inputs.infrastructure, ())                                  # no provisioning reservation
        evidence = _service(repo).require_ready(c, tenant_id="t", project_id="prj_dd", environment="preview")
        self.assertTrue(evidence["ready"])
        self.assertEqual(repo.list_for(project_id="prj_dd", environment="preview"), ())  # nothing provisioned
        self.assertEqual(evidence["self_contained"]["not_required"],
                         {k: "NOT_REQUIRED" for k in ("object_storage", "scheduled_http", "outbound")})
        self.assertNotIn("LIVE", json.dumps(evidence["self_contained"]))


class Case2Postgres(unittest.TestCase):
    def test_managed_postgres_is_required_and_blocks_explicitly(self):
        c = _contract(POSTGRES)
        self.assertEqual(_modes(c), {"database": "PLATFORM_MANAGED", "auth_session": "PLATFORM_MANAGED"})
        with self.assertRaises(CostQuoteUnknown) as ctx:
            _quote(c)
        self.assertTrue(all("database" in u or "auth_session" in u for u in ctx.exception.unknown))
        with self.assertRaises(InfrastructureStageBlocked):                           # never continues as if it exists
            _service().require_ready(c, tenant_id="t", project_id="prj_dd", environment="preview")


class Case3Email(unittest.TestCase):
    def test_email_is_required_and_not_faked(self):
        c = _contract(EMAIL)
        self.assertEqual(_modes(c), {"database": "SELF_CONTAINED", "auth_session": "SELF_CONTAINED",
                                     "outbound": "PLATFORM_MANAGED"})
        with self.assertRaises(CostQuoteUnknown) as ctx:
            _quote(c)
        self.assertEqual([u.split()[1] for u in ctx.exception.unknown], ["outbound"])
        preview = build_plan_preview(
            architect=ProductArchitect(), repository=MemoryBuildContractRepository(), project_id="prj_dd",
            prompt=EMAIL, economics=_economics, durable_backend=True,
            infrastructure_readiness={"kinds": {}}, image_readiness={"status": "NOT_CONFIGURED", "reason": "x"})
        codes = {b["code"] for b in preview["blockers"]}
        self.assertIn("infrastructure_outbound_not_configured", codes)
        self.assertIn("cost_quote_unknown", codes)
        self.assertFalse(preview["can_build"])


class Case4Mixed(unittest.TestCase):
    def test_quote_includes_only_required_capabilities(self):
        c = _contract(MIXED)
        self.assertEqual(_modes(c), {"database": "SELF_CONTAINED", "auth_session": "SELF_CONTAINED",
                                     "object_storage": "PLATFORM_MANAGED", "outbound": "PLATFORM_MANAGED"})
        quotes = _service().cost_quotes(c, tenant_id="t", project_id="prj_dd", environment="preview")
        self.assertEqual({getattr(q.kind, "value", q.kind) for q in quotes}, {"object_storage", "outbound"})
        with self.assertRaises(CostQuoteUnknown) as ctx:
            _quote(c)
        self.assertEqual(sorted(u.split()[1] for u in ctx.exception.unknown), ["object_storage", "outbound"])


class StorageSeparationTests(unittest.TestCase):
    def test_platform_artifact_storage_never_adds_product_storage(self):
        platform_r2 = {"OMNI_S3_ENDPOINT": "https://example.r2.cloudflarestorage.com", "OMNI_S3_BUCKET": "omni-artifacts"}
        with patch.dict(os.environ, platform_r2):
            self.assertNotIn("object_storage", _modes(_contract(TASK_TRACKER)))


class ManagedContractsUnchangedTests(unittest.TestCase):
    def test_fully_managed_prompt_keeps_all_five_kinds_in_canonical_order(self):
        c = _contract("Build a booking SaaS for admins and customers with Postgres, login, uploads, "
                      "scheduled reminders and outbound email.")
        self.assertEqual(c.product_family, "managed_web_saas_v1")
        self.assertEqual([r.kind for r in c.infrastructure],
                         ["database", "auth_session", "object_storage", "scheduled_http", "outbound"])
        self.assertEqual(set(_modes(c).values()), {"PLATFORM_MANAGED"})


class _Transport:
    def __init__(self):
        self.paths = []

    def request(self, *, method, url, headers=None, json_body=None, timeout_seconds=10.0):
        self.paths.append(url.rsplit("/", 1)[-1])
        return HttpResponse(status=200, headers={"content-type": "application/json"}, body=b"{}")


KINDS = ("auth", "role", "data_create", "data_read", "data_update", "data_delete", "responsive", "api_smoke")
PREVIEW = {"preview_url": "https://preview.example"}


def _personas(integration_ids=("A2",)):
    steps = [{"id": f"s-{k}", "kind": k, "acceptance_ids": ["A1"], "method": "GET", "path": f"/{k}",
              "expect_status": 200} for k in KINDS]
    steps.append({"id": "s-int", "kind": "integration", "acceptance_ids": list(integration_ids), "method": "GET",
                  "path": "/integration", "expect_status": 200})
    return [{"id": "p1", "role": "admin", "steps": steps}]


def _scope(contract):
    return {"infrastructure": [r.to_dict() for r in contract.infrastructure],
            "required_integrations": list(contract.required_integrations)}


class AcceptanceScopeTests(unittest.TestCase):
    def test_integration_not_required_for_self_contained_contract(self):
        floor, not_required = acceptance_scope(_scope(_contract(TASK_TRACKER)))
        self.assertNotIn("integration", floor)
        self.assertEqual(not_required, ("integration",))
        t = _Transport()
        runner = WebSaaSAcceptanceRunner(transport=t, required_kinds=("integration",),
                                         build_contract=_scope(_contract(TASK_TRACKER)))
        report = runner.verify(PREVIEW, {"acceptance": [{"id": "A1"}]}, _personas(integration_ids=("A1",)))
        self.assertNotIn("integration", t.paths)                   # never executed
        self.assertEqual(report.status, "PASS")
        self.assertNotIn("integration", report.covered_kinds)      # never counted
        self.assertEqual(report.not_verified_steps, ("p1:s-int",))

    def test_acceptance_needing_an_unrequired_kind_cannot_pass(self):
        report = WebSaaSAcceptanceRunner(transport=_Transport(), build_contract=_scope(_contract(TASK_TRACKER))).verify(
            PREVIEW, {"acceptance": [{"id": "A1"}, {"id": "A2"}]}, _personas())
        self.assertEqual(report.status, "FAIL")
        self.assertIn("A2", report.missing_acceptance_ids)

    def test_integration_required_when_the_product_needs_it_or_contract_is_unknown(self):
        for scope in (_scope(_contract(EMAIL)), _scope(_contract(MIXED)), None):
            runner = WebSaaSAcceptanceRunner(transport=_Transport(), build_contract=scope)
            self.assertIn("integration", runner.required_kinds)
            self.assertEqual(runner.not_required_kinds, ())


class ContractScopeLookupTests(unittest.TestCase):
    class _Pool:
        def __init__(self, row=None, error=None):
            self.row, self.error, self.calls = row, error, []

        def connection(self):
            pool = self

            class C:
                def __enter__(self): return self
                def __exit__(self, *a): return False
                def cursor(self): return self
                def execute(self, sql, params):
                    pool.calls.append((sql, params))
                    if pool.error:
                        raise pool.error
                def fetchone(self): return pool.row
            return C()

    def test_reads_the_contract_through_lineage_scoped_to_the_project(self):
        infra = [{"kind": "database", "required": True, "connection_mode": "SELF_CONTAINED"}]
        pool = self._Pool(row=(infra, []))
        self.assertEqual(contract_scope_for_version(pool, project_id="prj", version_id="v1"),
                         {"infrastructure": infra, "required_integrations": []})
        self.assertEqual(pool.calls[0][1], ("v1", "prj", "prj"))
        for fragment in ("WITH RECURSIVE", "modification_requests", "m5_build_contracts", "'infrastructure'"):
            self.assertIn(fragment, _CONTRACT_SCOPE_FOR_VERSION_SQL)

    def test_failure_or_absence_means_strict_floor(self):
        self.assertIsNone(contract_scope_for_version(self._Pool(row=None), project_id="p", version_id="v"))
        self.assertIsNone(contract_scope_for_version(self._Pool(error=RuntimeError("db down")),
                                                     project_id="p", version_id="v"))


class _PricedQuote:
    total_estimated_variable_usd = Decimal("0.01")
    total_authorized_variable_usd = Decimal("0.40")

    def to_dict(self):
        return {}


def _economics(contract):
    _quote(contract)                     # real cost-input collection; raises when something is unpriceable
    return _PricedQuote()


class PlanPreviewTests(unittest.TestCase):
    def test_self_contained_plan_has_no_infrastructure_blockers(self):
        preview = build_plan_preview(
            architect=ProductArchitect(), repository=MemoryBuildContractRepository(), project_id="prj_dd",
            prompt=TASK_TRACKER, economics=_economics, durable_backend=True,
            infrastructure_readiness={"kinds": {}}, image_readiness={"status": "NOT_CONFIGURED", "reason": "x"})
        self.assertEqual(preview["blockers"], [])
        self.assertTrue(preview["can_build"])
        self.assertEqual({r["readiness"] for r in preview["infrastructure"]}, {"SELF_CONTAINED"})
        self.assertEqual({(o["kind"], o["status"]) for o in preview["infrastructure_not_required"]},
                         {("object_storage", "NOT_REQUIRED"), ("scheduled_http", "NOT_REQUIRED"),
                          ("outbound", "NOT_REQUIRED")})


if __name__ == "__main__":
    unittest.main()
