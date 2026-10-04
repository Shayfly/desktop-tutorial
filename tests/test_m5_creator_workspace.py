"""M5-UX01: backend support for the creator golden-path workspace.

Covers the pure pieces the UI relies on (plan + quote preview, real worker
phases, preview frame policy, honest copy) and static checks on the shipped
workspace assets. The rendered UI itself is checked in a browser separately.
"""
from __future__ import annotations

import re
import unittest
from decimal import Decimal
from pathlib import Path

from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.creator_plan import build_plan_preview
from omni_prod.preview_runtime import preview_frame_source
from omni_prod.product_architect import ProductArchitect
from omni_prod.ui_translations import UI_COPY

try:
    from tests.m5_worker_harness import ContractBuildHarness
except ModuleNotFoundError:
    from m5_worker_harness import ContractBuildHarness

ASSETS = Path(__file__).resolve().parents[1] / "omni_prod" / "assets"
PROMPT = ("Build a travel agency CRM SaaS for admin and travel-agent users. Manage customers and bookings "
          "in Postgres, require login, file uploads, scheduled follow-ups and outbound email notifications.")


class _Quote:
    def __init__(self):
        self.total_estimated_variable_usd = Decimal("0.40")
        self.total_authorized_variable_usd = Decimal("1.25")
    def to_dict(self):
        return {"total_estimated_variable_usd": "0.40", "total_authorized_variable_usd": "1.25"}


class PlanPreviewTests(unittest.TestCase):
    def _preview(self, prompt=PROMPT, quote=lambda: _Quote(), infra=None, image=None, durable=True):
        repo = MemoryBuildContractRepository()
        return repo, build_plan_preview(
            architect=ProductArchitect(), repository=repo, project_id="prj_plan", prompt=prompt,
            economics=quote, durable_backend=durable,
            infrastructure_readiness=infra or {"kinds": {k: {"status": "PARTIAL", "reason": "configured"} for k in
                                                         ("database", "auth_session", "object_storage", "scheduled_http", "outbound")}},
            image_readiness=image or {"status": "PARTIAL", "reason": "configured"},
        )

    def test_ready_plan_shows_product_capabilities_infrastructure_and_cost(self):
        repo, preview = self._preview()
        self.assertEqual(preview["status"], "READY")
        self.assertTrue(preview["build_contract_id"])
        self.assertEqual(repo.get(preview["build_contract_id"], project_id="prj_plan").status.value, "READY")
        self.assertIn("customers", preview["product"]["data_requirements"])
        self.assertTrue(any(c["key"] == "software.code.generate" for c in preview["capabilities"]))
        self.assertEqual({i["kind"] for i in preview["infrastructure"]},
                         {"database", "auth_session", "object_storage", "scheduled_http", "outbound"})
        self.assertEqual(preview["estimated_cost_usd"], "0.40")
        self.assertEqual(preview["maximum_authorized_cost_usd"], "1.25")
        self.assertTrue(preview["can_build"])
        self.assertEqual(preview["blockers"], [])
        self.assertFalse(preview["paid_work_started"])

    def test_vague_prompt_returns_questions_and_cannot_build(self):
        _, preview = self._preview(prompt="Build me an app")
        self.assertEqual(preview["status"], "NEEDS_CLARIFICATION")
        self.assertTrue(preview["clarification_questions"])
        self.assertFalse(preview["can_build"])

    def test_missing_infrastructure_or_backend_is_a_named_blocker(self):
        infra = {"kinds": {"database": {"status": "NOT_CONFIGURED", "reason": "admin DSN missing"}}}
        _, preview = self._preview(infra=infra, image={"status": "NOT_CONFIGURED", "reason": "no key"}, durable=False)
        self.assertFalse(preview["can_build"])
        joined = " ".join(b["code"] for b in preview["blockers"])
        self.assertIn("durable_backend_not_configured", joined)
        self.assertIn("infrastructure_database_not_configured", joined)
        self.assertIn("image_provider_not_configured", joined)
        db = next(i for i in preview["infrastructure"] if i["kind"] == "database")
        self.assertEqual(db["readiness"], "NOT_CONFIGURED")

    def test_unaffordable_quote_is_reported_not_hidden(self):
        def deny():
            raise PermissionError("zero/unknown revenue plan cannot authorize paid variable build cost")
        _, preview = self._preview(quote=deny)
        self.assertIsNone(preview["economics"])
        self.assertIn("cannot authorize", preview["economics_error"])
        self.assertIsNone(preview["maximum_authorized_cost_usd"])
        self.assertIn("plan_cannot_authorize_cost", [b["code"] for b in preview["blockers"]])


class WorkerPhaseTests(unittest.TestCase):
    def test_worker_reports_real_phases_in_order(self):
        class PhasedJobs(ContractBuildHarness(None).jobs.__class__):
            def __init__(self, request):
                super().__init__(request)
                self.phases = []
            def update_phase(self, build_id, phase, message=""):
                self.phases.append(phase)

        harness = ContractBuildHarness()
        harness.jobs = PhasedJobs(harness.jobs.request)
        self.assertEqual(harness.run(), "ready")
        self.assertEqual(harness.jobs.phases, ["PLANNING", "GENERATING", "VERIFYING"])

    def test_phase_reporting_failure_never_breaks_a_build(self):
        harness = ContractBuildHarness()

        def broken(*a, **k):
            raise RuntimeError("db hiccup")
        harness.jobs.update_phase = broken
        self.assertEqual(harness.run(), "ready")


class PreviewFramePolicyTests(unittest.TestCase):
    def test_frame_source_is_the_preview_wildcard_only(self):
        self.assertEqual(preview_frame_source("https://{preview_id}.preview.148ailabs.com"),
                         "https://*.preview.148ailabs.com")
        self.assertIsNone(preview_frame_source(None))
        self.assertIsNone(preview_frame_source("https://preview.example.com/{preview_id}"))
        self.assertIsNone(preview_frame_source("https://{preview_id}.localhost"))


class HonestCopyAndAssetTests(unittest.TestCase):
    def test_hero_no_longer_promises_anything(self):
        for locale, copy in UI_COPY.items():
            self.assertNotRegex(copy["hero"].lower(), r"anything|כל דבר", locale)
        self.assertIn("ווב", UI_COPY["he"]["lead"])
        self.assertIn("web app", UI_COPY["en"]["lead"].lower())

    def test_workspace_assets_keep_contract_and_drop_fake_claims(self):
        html = (ASSETS / "index.html").read_text(encoding="utf-8")
        js = (ASSETS / "app.js").read_text(encoding="utf-8")
        self.assertIn("/assets/app.css", html)
        self.assertIn("/assets/app.js", html)
        self.assertIn('dir="rtl"', html)
        self.assertIn('lang="he"', html)
        lowered = (html + js).lower()
        self.assertNotIn("build anything", lowered)
        self.assertNotIn("games & 3d", lowered)
        # canonical durable endpoints only, no invented v2 routes
        for path in ("/api/v28/projects/${", "/builds", "/build-contracts", "/previews", "/modifications",
                     "/rollback", "/export", "/api/v28/auth/login", "/api/v28/auth/logout"):
            self.assertIn(path, js)
        self.assertIsNone(re.search(r"/api/v28/[a-z-]*v2|/creator2|/preview-new|/new-build", js))
        # no social login button unless a real route exists
        self.assertNotIn("google", lowered.replace("fonts.google", ""))
        # publish is honest
        self.assertIn("publishNotConfigured", js)
        # no deterministic demo build path in the workspace
        self.assertNotIn("/api/demo/build", js)
        self.assertNotIn("/api/v28/projects/${encodeURIComponent(pid)}/build`", js)

    def test_service_worker_cache_is_bumped(self):
        sw = (ASSETS / "sw.js").read_text(encoding="utf-8")
        self.assertIn("148ai-v28-static", sw)
        self.assertNotIn("148ai-v28-static-1'", sw)


if __name__ == "__main__":
    unittest.main()
