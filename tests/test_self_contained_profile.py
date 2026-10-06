"""self_contained_web_v1: the Golden E2E #1 infrastructure profile (founder
decision 2026-10-07 #27). Self-contained is not fake: nothing is provisioned or
reported LIVE, embedded kinds count only through real tests/acceptance, and
out-of-scope kinds stay NOT_VERIFIED."""
import json
import unittest
from decimal import Decimal

from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.build_cost_plan import CostQuoteUnknown, collect_build_cost_inputs
from omni_prod.creator_plan import build_plan_preview
from omni_prod.infrastructure_provisioner import (InfrastructureProvisioningService, InfrastructureStageBlocked,
                                                  MemoryInfrastructureBindingRepository)
from omni_prod.infrastructure_registry import (DEFAULT_INFRASTRUCTURE_PROFILES, MANAGED_WEB_SAAS_V1,
                                               SELF_CONTAINED_OUT_OF_SCOPE, SELF_CONTAINED_WEB_V1, selected_profile)
from omni_prod.product_architect import ProductArchitect
from omni_prod.providers.managed_web_saas import build_managed_web_saas_provisioner
from omni_prod.web_saas_acceptance import HttpResponse, WebSaaSAcceptanceRunner
from omni_prod.worker_tasks import _PROFILE_FOR_VERSION_SQL, infrastructure_profile_for_version

PROMPT = ("Build a team task tracker web app: users sign up and log in, create projects, add tasks with "
          "title, due date and status, assign tasks to teammates, and see a dashboard of overdue tasks.")


def _contract(profile=None):
    return ProductArchitect(infrastructure_profile=profile).compile(PROMPT, project_id="prj_sc", contract_version=1)


def _service():
    return InfrastructureProvisioningService(provisioner=build_managed_web_saas_provisioner(env={}),
                                             repository=MemoryInfrastructureBindingRepository())


class ProfileSelectionTests(unittest.TestCase):
    def test_registry_and_selection(self):
        self.assertIs(DEFAULT_INFRASTRUCTURE_PROFILES.get("self_contained_web_v1"), SELF_CONTAINED_WEB_V1)
        self.assertIs(selected_profile({}), MANAGED_WEB_SAAS_V1)                      # default unchanged
        self.assertIs(selected_profile({"OMNI_BUILD_INFRA_PROFILE": "self_contained_web_v1"}), SELF_CONTAINED_WEB_V1)
        with self.assertRaises(KeyError):                                              # never a silent fallback
            selected_profile({"OMNI_BUILD_INFRA_PROFILE": "something_v9"})

    def test_profile_contents(self):
        self.assertEqual([(r.kind, r.connection_mode) for r in SELF_CONTAINED_WEB_V1.requirements],
                         [("database", "SELF_CONTAINED"), ("auth_session", "SELF_CONTAINED")])
        self.assertEqual(SELF_CONTAINED_OUT_OF_SCOPE, ("object_storage", "scheduled_http", "outbound"))


class ContractTests(unittest.TestCase):
    def test_self_contained_contract(self):
        c = _contract("self_contained_web_v1")
        self.assertEqual(c.product_family, "self_contained_web_v1")
        self.assertEqual({r.kind for r in c.infrastructure}, {"database", "auth_session"})
        self.assertIn("SQLite (sqlite3)", c.product_spec.stack)
        self.assertNotIn("FastAPI", " ".join(c.product_spec.stack))            # consistent with stdlib-only #25
        data = next(r for r in c.product_spec.requirements if r.id == "platform-data")
        self.assertIn("embedded SQLite", data.text)
        self.assertIn("self_contained_web_v1", c.defaults_applied)

    def test_managed_contract_is_unchanged_by_default(self):
        default, explicit = _contract(None), _contract("managed_web_saas_v1")
        self.assertEqual(default.contract_fingerprint, explicit.contract_fingerprint)
        self.assertEqual(default.product_family, "managed_web_saas_v1")
        self.assertEqual(len(default.infrastructure), 5)


class QuoteAndInfrastructureStageTests(unittest.TestCase):
    def test_self_contained_quote_is_priced_without_provisioning(self):
        c = _contract("self_contained_web_v1")
        quotes = _service().cost_quotes(c, tenant_id="t", project_id="prj_sc", environment="preview")
        self.assertEqual(quotes, [])
        inputs = collect_build_cost_inputs(c, capability_assignments={}, infrastructure_quotes=quotes,
                                           require_capability_quotes=True, require_infrastructure_quotes=True)
        self.assertEqual(inputs.infrastructure, ())

    def test_managed_quote_still_fails_closed_when_unpriced(self):
        c = _contract(None)
        with self.assertRaises(CostQuoteUnknown):
            collect_build_cost_inputs(c, capability_assignments={},
                                      infrastructure_quotes=_service().cost_quotes(c, tenant_id="t", project_id="p",
                                                                                   environment="preview"),
                                      require_infrastructure_quotes=True)

    def test_infrastructure_stage_reports_truthfully(self):
        evidence = _service().require_ready(_contract("self_contained_web_v1"), tenant_id="t",
                                            project_id="prj_sc", environment="preview")
        self.assertTrue(evidence["ready"])
        self.assertFalse(evidence["bindings"])                   # nothing provisioned
        sc = evidence["self_contained"]
        self.assertEqual(set(sc["embedded"]), {"database", "auth_session"})
        self.assertTrue(all("not provisioned" in v for v in sc["embedded"].values()))
        self.assertEqual(sc["out_of_scope"], {k: "NOT_VERIFIED" for k in SELF_CONTAINED_OUT_OF_SCOPE})
        self.assertNotIn("LIVE", json.dumps(sc))

    def test_managed_infrastructure_stage_still_blocks(self):
        with self.assertRaises(InfrastructureStageBlocked):
            _service().require_ready(_contract(None), tenant_id="t", project_id="p", environment="preview")


class _Quote:
    total_estimated_variable_usd = Decimal("0.01")
    total_authorized_variable_usd = Decimal("0.40")

    def to_dict(self):
        return {}


class PlanPreviewTests(unittest.TestCase):
    def test_no_infrastructure_blockers_and_explicit_out_of_scope(self):
        preview = build_plan_preview(
            architect=ProductArchitect(infrastructure_profile="self_contained_web_v1"),
            repository=MemoryBuildContractRepository(), project_id="prj_sc", prompt=PROMPT,
            economics=lambda: _Quote(), durable_backend=True,
            infrastructure_readiness={"kinds": {}},                                  # nothing configured
            image_readiness={"status": "NOT_CONFIGURED", "reason": "no key"})
        self.assertEqual(preview["blockers"], [])
        self.assertTrue(preview["can_build"])
        self.assertEqual({r["readiness"] for r in preview["infrastructure"]}, {"SELF_CONTAINED"})
        self.assertEqual([o["kind"] for o in preview["infrastructure_out_of_scope"]], list(SELF_CONTAINED_OUT_OF_SCOPE))
        self.assertEqual({o["status"] for o in preview["infrastructure_out_of_scope"]}, {"NOT_VERIFIED"})


class _Transport:
    def __init__(self):
        self.paths = []

    def request(self, *, method, url, headers=None, json_body=None, timeout_seconds=10.0):
        self.paths.append(url.rsplit("/", 1)[-1])
        return HttpResponse(status=200, headers={"content-type": "application/json"}, body=b"{}")


KINDS = ("auth", "role", "data_create", "data_read", "data_update", "data_delete", "responsive", "api_smoke")


def _personas(integration_ids=("A2",)):
    steps = [{"id": f"s-{k}", "kind": k, "acceptance_ids": ["A1"], "method": "GET", "path": f"/{k}",
              "expect_status": 200} for k in KINDS]
    steps.append({"id": "s-int", "kind": "integration", "acceptance_ids": list(integration_ids), "method": "GET",
                  "path": "/integration", "expect_status": 200})
    return [{"id": "p1", "role": "admin", "steps": steps}]


PREVIEW = {"preview_url": "https://preview.example"}


class AcceptanceScopeTests(unittest.TestCase):
    def test_self_contained_never_executes_or_counts_integration(self):
        t = _Transport()
        runner = WebSaaSAcceptanceRunner(transport=t, required_kinds=("integration",), profile_key="self_contained_web_v1")
        self.assertNotIn("integration", runner.required_kinds)   # even when generated metadata asks for it
        report = runner.verify(PREVIEW, {"acceptance": [{"id": "A1"}]}, _personas(integration_ids=("A1",)))
        self.assertNotIn("integration", t.paths)
        self.assertEqual(report.status, "PASS")
        self.assertNotIn("integration", report.covered_kinds)
        self.assertEqual(report.out_of_scope_kinds, ("integration",))
        self.assertEqual(report.not_verified_steps, ("p1:s-int",))

    def test_acceptance_needing_integration_cannot_pass_self_contained(self):
        report = WebSaaSAcceptanceRunner(transport=_Transport(), profile_key="self_contained_web_v1").verify(
            PREVIEW, {"acceptance": [{"id": "A1"}, {"id": "A2"}]}, _personas())
        self.assertEqual(report.status, "FAIL")
        self.assertIn("A2", report.missing_acceptance_ids)

    def test_unknown_or_missing_profile_uses_the_strict_floor(self):
        for profile in (None, "unknown_v1"):
            runner = WebSaaSAcceptanceRunner(transport=_Transport(), profile_key=profile)
            self.assertIn("integration", runner.required_kinds)
            self.assertEqual(runner.out_of_scope_kinds, ())


class ProfileLookupTests(unittest.TestCase):
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

    def test_lookup_reads_the_contract_through_lineage_scoped_to_the_project(self):
        pool = self._Pool(row=("self_contained_web_v1",))
        self.assertEqual(infrastructure_profile_for_version(pool, project_id="prj", version_id="v1"),
                         "self_contained_web_v1")
        self.assertEqual(pool.calls[0][1], ("v1", "prj", "prj"))
        for fragment in ("WITH RECURSIVE", "modification_requests", "m5_build_contracts", "product_family"):
            self.assertIn(fragment, _PROFILE_FOR_VERSION_SQL)

    def test_failure_or_absence_means_strict_floor(self):
        self.assertIsNone(infrastructure_profile_for_version(self._Pool(row=None), project_id="p", version_id="v"))
        self.assertIsNone(infrastructure_profile_for_version(self._Pool(error=RuntimeError("db down")),
                                                             project_id="p", version_id="v"))


if __name__ == "__main__":
    unittest.main()
