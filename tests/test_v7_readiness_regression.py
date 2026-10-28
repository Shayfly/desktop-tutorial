"""V7 regressions: genuine cost gating, outbound intent and sign-in visibility.

These tests never enqueue jobs or call a model provider.
"""
from pathlib import Path
from types import SimpleNamespace
import unittest

from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.build_cost_plan import CostQuoteUnknown
from omni_prod.creator_plan import build_plan_preview
from omni_prod.product_architect import ProductArchitect

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "omni_prod" / "assets"
PROMPT = "Build a travel agency website with real destinations and responsive pages."


class V7ReadinessTests(unittest.TestCase):
    def preview(self, economics):
        return build_plan_preview(
            architect=ProductArchitect(),
            repository=MemoryBuildContractRepository(),
            project_id="prj_v7_test",
            prompt=PROMPT,
            economics=economics,
            durable_backend=True,
            infrastructure_readiness={"kinds": {
                "database": {"status": "PARTIAL", "reason": "configured"},
                "auth_session": {"status": "PARTIAL", "reason": "configured"},
            }},
            image_readiness={"status": "PARTIAL", "reason": "configured"},
        )

    def test_none_cost_quote_does_not_authorize_build(self):
        p = self.preview(lambda: None)
        self.assertFalse(p["can_build"])
        self.assertEqual(p["build_authorization"], "UNKNOWN")
        self.assertEqual(p["execution_readiness"], "BLOCKED_PROVIDER_OR_QUOTE")
        self.assertIn("cost_quote_unavailable", [b["code"] for b in p["blockers"]])
        self.assertFalse(p["paid_work_started"])

    def test_missing_price_lists_named_capability_without_guessing_cost(self):
        def unknown():
            raise CostQuoteUnknown(["capability integration.maps has no configured provider quote"])
        p = self.preview(unknown)
        self.assertFalse(p["can_build"])
        self.assertEqual(p["execution_readiness"], "BLOCKED_PROVIDER_OR_QUOTE")
        self.assertIn("integration.maps", [g["key"] for g in p["unavailable_requirements"]])
        self.assertNotIn("estimated_cost_usd", p)
        self.assertNotIn("maximum_authorized_cost_usd", p)

    def test_contact_email_not_promoted_to_outbound_delivery(self):
        from omni_prod.product_architect import _infer_infrastructure, ProductArchitect
        text = "Travel brochure site. Show our contact email address: hello@example.org."
        self.assertNotIn("outbound", {r.kind for r in _infer_infrastructure(text, ())})
        self.assertNotIn("email", ProductArchitect._infer_integrations(text, SimpleNamespace(requirements=())))

    def test_explicit_email_notifications_still_require_outbound(self):
        from omni_prod.product_architect import _infer_infrastructure, ProductArchitect
        text = "Send automatic email notifications after booking."
        self.assertIn("outbound", {r.kind for r in _infer_infrastructure(text, ())})
        self.assertIn("email", ProductArchitect._infer_integrations(text, SimpleNamespace(requirements=())))

    def test_password_toggle_is_accessible_and_never_a_submit(self):
        html = (ASSETS / "index.html").read_text(encoding="utf-8")
        js = (ASSETS / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="passwordToggle"', html)
        self.assertIn('type="button" aria-controls="password" aria-pressed="false"', html)
        self.assertIn("showPassword:'הצגת סיסמה'", js)
        self.assertIn("hidePassword:'הסתרת סיסמה'", js)
        self.assertIn("input.type = showing ? 'text' : 'password';", js)

    def test_project_readiness_strip_persists_outside_plan_panel(self):
        html = (ASSETS / "index.html").read_text(encoding="utf-8")
        js = (ASSETS / "app.js").read_text(encoding="utf-8")
        css = (ASSETS / "app.css").read_text(encoding="utf-8")
        self.assertIn('id="projectReadiness"', html)
        self.assertLess(html.index('id="projectReadiness"'), html.index('id="ctx"'))
        self.assertIn("function renderProjectReadiness()", js)
        self.assertIn("const mode = busy ? 'running' : !p ? 'unknown' : p.can_build ? 'ready' : 'blocked'", js)
        self.assertIn("strip.hidden = !S.projectId;", js)
        self.assertIn(".projectReadiness.blocked", css)

    def test_missing_quote_is_explained_without_bypassing_admission(self):
        js = (ASSETS / "app.js").read_text(encoding="utf-8")
        self.assertIn("p.blockers.some(b => b.code === 'cost_quote_unknown' || b.code === 'cost_quote_unavailable')", js)
        self.assertIn("היתרה המוצגת אינה אישור לבנייה", js)
        self.assertIn("disabled: !p.can_build", js)

    def test_project_quota_has_distinct_client_remedy(self):
        js = (ASSETS / "app.js").read_text(encoding="utf-8")
        self.assertIn("err.detail.code === 'project_limit_reached'", js)
        self.assertIn("זו אינה בעיית קרדיטים", js)
        self.assertIn("err.detail.active_projects", js)
        self.assertIn("err.detail.max_projects", js)

    def test_project_creation_is_not_limited_by_subscription_slots(self):
        source = (ROOT / "omni_prod" / "investor_app.py").read_text(encoding="utf-8")
        create = source.split("def v28_create_project(", 1)[1].split("@app.get('/api/v28/projects')", 1)[0]
        # 2026-10-28: the route also writes the two-gate flow mark after creating, so the call is no longer a bare
        # `return`; what this guards is unchanged -- creation is the plain call, with no slot limit around it.
        self.assertIn("_v28.create_project(token=token, title=req.title)", create)
        self.assertNotIn("max_projects", create)
        self.assertNotIn("project_limit_reached", create)

    def test_blocked_plan_is_not_presented_as_buildable(self):
        js = (ASSETS / "app.js").read_text(encoding="utf-8")
        self.assertIn("blockedByBuildGate ? t('readinessBlocked')", js)
        self.assertIn("class: `readinessStatus ${p.can_build ? 'ready' : 'blocked'}`", js)
        self.assertNotIn("f_FEASIBLE_WITH_CONSTRAINTS:'אפשר לבנות, עם מגבלות'", js)
        self.assertNotIn("': ', b.message", js)


if __name__ == "__main__":
    unittest.main()
