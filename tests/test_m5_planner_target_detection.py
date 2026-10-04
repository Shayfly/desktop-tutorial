"""M5 remediation: token-aware product target detection (no naive substrings)."""
from __future__ import annotations

import unittest

from omni_prod.capability_planner import CapabilityPlanner
from omni_prod.capability_registry import CapabilityRegistry
from omni_prod.intent_terms import ai_agent_intent, has_term, mobile_intent
from omni_prod.media_pipeline import CreativeDirector
from omni_prod.product_architect import ProductArchitect
from omni_prod.unified_engine import UnifiedPromptPlanner


def targets(prompt):
    return UnifiedPromptPlanner().plan(prompt).targets


def capability_keys(prompt):
    unified = UnifiedPromptPlanner().plan(prompt)
    creative = CreativeDirector().plan(prompt, targets=unified.targets)
    plan = CapabilityPlanner(CapabilityRegistry()).plan(prompt=prompt, unified_plan=unified, creative_plan=creative)
    return {r.key for r in plan.requirements}


class MobileDetectionTests(unittest.TestCase):
    POSITIVE = ("build me a mobile app", "android app", "iOS application", "Build an iOS and Android booking app",
                "a booking app for barbers", "תבנה לי אפליקציה בסגנון Uber")
    NEGATIVE = ("appointment booking system", "appointments CRM", "mapping dashboard", "happening events website",
                "Build a web app for invoices", "a web application for clinics", "an internal application for HR",
                "community forum with delivery tracking", "approval workflow for purchase orders")

    def test_positive_prompts_add_mobile_target(self):
        for prompt in self.POSITIVE:
            with self.subTest(prompt=prompt):
                self.assertTrue(mobile_intent(prompt))
                self.assertIn("android", targets(prompt))

    def test_negative_prompts_stay_web_only(self):
        for prompt in self.NEGATIVE:
            with self.subTest(prompt=prompt):
                self.assertFalse(mobile_intent(prompt))
                self.assertEqual(targets(prompt), ("web",))

    def test_ios_still_adds_ios_target(self):
        self.assertIn("ios", targets("iOS application"))
        self.assertNotIn("ios", targets("appointments CRM"))

    def test_web_crm_with_appointments_contract_is_web_only(self):
        prompt = ("Build a barbershop booking SaaS for admin, barber and customer users. Customers book appointments, "
                  "barbers manage their calendar, data in Postgres, require login, file uploads, scheduled reminders "
                  "and outbound email notifications.")
        keys = capability_keys(prompt)
        self.assertNotIn("target.android.source", keys)
        self.assertNotIn("target.ios.source", keys)
        self.assertIn("target.web", keys)
        contract = ProductArchitect().compile(prompt, project_id="prj_web_only", contract_version=1)
        self.assertEqual(contract.target, "web")
        self.assertFalse({r.key for r in contract.capability_plan.requirements} & {"target.android.source", "target.ios.source"})


class OtherFalseTargetTests(unittest.TestCase):
    def test_substrings_no_longer_create_targets_or_capabilities(self):
        self.assertNotIn("game3d", targets("community platform for local clubs"))       # unity
        self.assertNotIn("maps", UnifiedPromptPlanner().plan("mapping dashboard").capabilities)
        self.assertNotIn("realtime", UnifiedPromptPlanner().plan("delivery scheduling portal").capabilities)
        self.assertNotIn("target.backend", capability_keys("rapid onboarding portal for capital investors"))  # api
        self.assertNotIn("target.database", capability_keys("customer feedback board"))  # db

    def test_real_terms_still_match_with_plurals(self):
        self.assertIn("maps", UnifiedPromptPlanner().plan("delivery app with maps").capabilities)
        self.assertIn("game3d", targets("Build a 3D football game in Unity"))
        self.assertTrue(has_term("customers and technicians", "customer", "technician"))
        self.assertTrue(has_term("tracking live orders", "live"))

    def test_human_agent_roles_are_not_ai_agents(self):
        prompt = "Build a travel agency CRM SaaS for admin and travel-agent users."
        self.assertFalse(ai_agent_intent(prompt))
        self.assertNotIn("target.agent", capability_keys(prompt))
        self.assertFalse(ai_agent_intent("CRM for real estate agents"))
        self.assertTrue(ai_agent_intent("Build an AI agent that answers support tickets"))
        self.assertTrue(ai_agent_intent("Build a realtime voice assistant"))
        self.assertIn("target.agent", capability_keys("Build an agent that books meetings"))


if __name__ == "__main__":
    unittest.main()
