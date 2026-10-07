"""Build status, plan view and modification status never expose internal unit
economics to the customer (founder decision 2026-10-07 #29, extended).

The internal evidence below mirrors what the worker actually writes (see
worker_tasks._run_live_build_job and resolve_m5_billing); the customer view
must keep verification evidence and the billing outcome, and drop every cost,
margin, budget, reservation, QA-funding and provider-routing detail.
"""
import ast
import importlib.util
import json
import re
import unittest
import uuid
from decimal import Decimal
from pathlib import Path

from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.build_cost_plan import CostQuoteUnknown
from omni_prod.creator_plan import build_plan_preview
from omni_prod.customer_views import is_internal_key, strip_internal_economics, unpriced_capabilities
from omni_prod.product_architect import ProductArchitect

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TEXT = re.compile(r"margin|revenue|markup|subsid|reservation|budget|provider[_ ]cost|_usd|OMNI_", re.I)
PROMPT = ("Build a team task tracker web app: users sign up and log in, create projects, add tasks with "
          "title, due date and status, assign tasks to teammates, and see a dashboard of overdue tasks.")

INTERNAL_EVIDENCE = {
    "gates": {"verification": {"passed": True, "failures": []}, "quality": {"score": 91}},
    "release_ready": True,
    "build_contract": {"id": "bc_1", "fingerprint": "sha256:x", "binding": "BOUND"},
    "capabilities": {"status": "VERIFIED", "requirements": [{"key": "media.image.generate", "status": "VERIFIED",
                                                            "estimated_cost_usd": "0.003", "pricing_version": "p1"}],
                     "usage": [{"actual_cost_usd": "0.002", "provider": "replicate"}]},
    "infrastructure": {"ready": True, "bindings": [], "quotes": [{"maximum_usd": "0.05"}],
                       "self_contained": {"embedded": {"database": "SELF_CONTAINED"}}},
    "repair_rounds": 1, "repair_stop_reason": "passed", "build_log_tail": "1 passed",
    "asset_capabilities": {"media.image.generate": "NOT_REQUIRED"},
    "model_route_events": [{"route": "cheap", "max_estimated_cost_usd": "0.01"}],
    "provider_usage": {"input_tokens": 100, "actual_cost_usd": None, "request_ids": ["req_1"]},
    "provider_spend_usd": "0.0123", "external_model_calls": 4, "provider_spend_basis": "AUTHORIZED_ESTIMATE",
    "model_budget_binding": {"effective_budget_usd": "0.50"},
    "economics_quote": {"total_authorized_variable_usd": "0.50", "revenue_usd": "2.00", "conservative_margin": "0.75",
                        "minimum_margin": "0.20", "components": {"reservation_usd": "0.50"},
                        "funding": {"funding_source": "internal_qa", "qa_total_usd": "10", "qa_used_before_usd": "3"}},
    "economics_settlement": {"action": "settled", "settled_provider_cost_usd": "0.40", "contribution_margin": "0.8"},
    "billing": "settled",
}


def _all_keys(value, path="$"):
    if isinstance(value, dict):
        for k, v in value.items():
            yield f"{path}.{k}", k
            yield from _all_keys(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _all_keys(v, f"{path}[{i}]")


class BuildStatusEvidenceTests(unittest.TestCase):
    def test_internal_economics_never_reach_the_customer(self):
        view = strip_internal_economics(INTERNAL_EVIDENCE)
        leaked = [p for p, k in _all_keys(view) if is_internal_key(k)]
        self.assertEqual(leaked, [])
        text = json.dumps(view)
        for value in ("0.75", "2.00", "qa_total", "internal_qa", "req_1", "0.0123", "max_estimated"):
            self.assertNotIn(value, text)

    def test_customer_visible_evidence_is_kept(self):
        view = strip_internal_economics(INTERNAL_EVIDENCE)
        self.assertEqual(view["gates"], INTERNAL_EVIDENCE["gates"])
        self.assertEqual((view["billing"], view["repair_rounds"], view["build_log_tail"]), ("settled", 1, "1 passed"))
        self.assertEqual(view["build_contract"], INTERNAL_EVIDENCE["build_contract"])
        self.assertEqual(view["capabilities"]["requirements"][0]["status"], "VERIFIED")
        self.assertEqual(view["asset_capabilities"], {"media.image.generate": "NOT_REQUIRED"})

    def test_internal_evidence_object_is_not_mutated(self):
        before = json.dumps(INTERNAL_EVIDENCE, sort_keys=True)
        strip_internal_economics(INTERNAL_EVIDENCE)
        self.assertEqual(json.dumps(INTERNAL_EVIDENCE, sort_keys=True), before)

    def test_customer_endpoints_use_the_filter(self):
        tree = ast.parse((ROOT / "omni_prod/investor_app.py").read_text())
        funcs = {n.name: ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for name in ("v28_build_status", "v28_modification_status"):
            self.assertIn("strip_internal_economics(", funcs[name], name)
        self.assertNotIn("'economics':", funcs["v28_build_async"].replace('"', "'"))
        self.assertNotIn("model_route_events", (ROOT / "omni_prod/investor_app.py").read_text())


class _Quote:
    total_estimated_variable_usd = Decimal("0.40")
    total_authorized_variable_usd = Decimal("1.25")

    def to_dict(self):
        return {"revenue_usd": "2.00", "conservative_margin": "0.75"}


def _preview(economics):
    return build_plan_preview(
        architect=ProductArchitect(), repository=MemoryBuildContractRepository(), project_id="prj_cv", prompt=PROMPT,
        economics=economics, durable_backend=True, infrastructure_readiness={"kinds": {}},
        image_readiness={"status": "NOT_CONFIGURED", "reason": "x"})


class PlanViewTests(unittest.TestCase):
    def _assert_clean(self, preview):
        leaked = [p for p, k in _all_keys(preview) if is_internal_key(k)]
        self.assertEqual(leaked, [])
        for blocker in preview["blockers"]:
            self.assertIsNone(FORBIDDEN_TEXT.search(blocker["message"]), blocker["message"])

    def test_priced_plan(self):
        preview = _preview(lambda: _Quote())
        self.assertEqual(preview["build_authorization"], "PRICED")
        self._assert_clean(preview)
        self.assertNotIn("0.75", json.dumps(preview))

    def test_unknown_quote_names_the_capability_without_internal_basis(self):
        def unknown():
            raise CostQuoteUnknown(["infrastructure outbound provisioning cost is unknown (provisioning cost not "
                                    "configured (OMNI_GENAPP_PROVISIONING_MAXIMUM_USD); unknown, not zero)"])
        preview = _preview(unknown)
        self.assertEqual(preview["build_authorization"], "UNKNOWN")
        self._assert_clean(preview)
        self.assertIn("outbound", next(b for b in preview["blockers"] if b["code"] == "cost_quote_unknown")["message"])

    def test_margin_refusal_does_not_reveal_margins(self):
        def refuse():
            raise PermissionError("build variable-cost margin below floor: 0.05 < 0.20")
        preview = _preview(refuse)
        self.assertEqual(preview["build_authorization"], "NOT_AUTHORIZED")
        self._assert_clean(preview)
        self.assertNotIn("0.20", json.dumps(preview))

    def test_unpriced_capability_names(self):
        self.assertEqual(unpriced_capabilities([
            "capability media.image.generate has no configured provider quote",
            "infrastructure outbound provisioning cost is unknown (x)", "something else"]),
            ["media.image.generate", "outbound"])


@unittest.skipUnless(importlib.util.find_spec("fastapi"), "FastAPI not installed")
class HTTPPlanViewTests(unittest.TestCase):
    def test_plan_endpoint_returns_credits_not_provider_economics(self):
        from fastapi.testclient import TestClient
        from omni_prod.investor_app import app
        c = TestClient(app)
        reg = c.post("/api/v28/auth/register", json={"email": f"cv-{uuid.uuid4().hex[:10]}@example.com",
                                                      "password": "StrongPass123!"}).json()
        h = {"Authorization": "Bearer " + reg["token"]}
        pid = c.post("/api/v28/projects", headers=h, json={"title": "Economics view"}).json()["id"]
        r = c.post(f"/api/v28/projects/{pid}/build-contracts", headers=h, json={"prompt": PROMPT})
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual([p for p, k in _all_keys(body) if is_internal_key(k)], [])
        self.assertIn("credits_required", body)
        self.assertIn("credits_remaining", body["allowance"])


if __name__ == "__main__":
    unittest.main()
