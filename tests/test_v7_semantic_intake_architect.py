"""Acceptance tests for AI-understood customer intent through the EXISTING build path.

No model call, database mutation, payment or preview claim is made by these tests.
"""
import unittest

from omni_prod import discovery
from omni_prod.intake.interpreter import validate_model_output
from omni_prod.semantic_capabilities import (
    encode_approved, read_approved, updated_decisions, validate_decisions,
)
from omni_prod.product_architect import ProductArchitect

LANDING = (
    "אני מבקש דף נחיתה בנושא גידול ירקות בעציצים במרפסת. "
    "שלב ראשון: בחירת המיקום של העציצים לפי אור השמש. "
    "פונטים קריאים בעברית כמו Assistant או Rubik. "
    "טופס הרשמה לקבלת טיפים שבועיים באימייל. "
    "אתר ללא התחברות למבקרים."
)
DECISIONS = [
    {"key": "target.agent", "decision": "not_required",
     "evidence": "פונטים קריאים בעברית כמו Assistant", "reason": "Assistant is a typeface"},
    {"key": "media.audio.tts", "decision": "not_required",
     "evidence": "פונטים קריאים בעברית כמו Assistant", "reason": "No narrated audio was requested"},
    {"key": "integration.maps", "decision": "not_required",
     "evidence": "בחירת המיקום של העציצים לפי אור השמש", "reason": "Plant placement is not map routing"},
]


def brief_with_approved_semantics():
    b = discovery.start(LANDING)
    b.fields["login"] = {"value": "none", "source": "answer", "question_id": "login",
                         "confidence": "stated"}
    b.semantic_decisions = list(DECISIONS)
    return b


class SemanticIntakeIntegrationTests(unittest.TestCase):
    def test_model_decisions_require_literal_customer_evidence(self):
        accepted, errors = validate_decisions(DECISIONS, customer_text=LANDING)
        self.assertEqual(len(accepted), 3)
        self.assertEqual(errors, [])
        rejected, errors = validate_decisions([
            {"key": "integration.maps", "decision": "not_required",
             "evidence": "a map the customer never mentioned", "reason": "unsupported"},
        ], customer_text=LANDING)
        self.assertEqual(rejected, [])
        self.assertTrue(errors)

    def test_model_output_carries_semantic_decisions_and_rejects_untrusted_keys(self):
        raw = {"language": "he", "product_family": "website",
               "proposals": [], "requirements": [], "delegate_rest": False,
               "reply": "הבנתי, Assistant הוא גופן.",
               "semantic_decisions": DECISIONS + [
                   {"key": "software.test", "decision": "not_required",
                    "evidence": "דף נחיתה", "reason": "attempt to bypass checks"}]}
        interpreted, errors = validate_model_output(raw, LANDING)
        self.assertIsNotNone(interpreted)
        self.assertEqual({x["key"] for x in interpreted.semantic_decisions},
                         {"target.agent", "media.audio.tts", "integration.maps"})
        self.assertTrue(errors)

    def test_brief_serialization_and_fingerprint_include_semantic_evidence(self):
        b = brief_with_approved_semantics()
        restored = discovery.Brief.from_dict(b.to_dict())
        self.assertEqual(restored.semantic_decisions, b.semantic_decisions)
        self.assertEqual(restored.fingerprint(), b.fingerprint())
        original = discovery.start(LANDING)
        self.assertNotEqual(restored.fingerprint(), original.fingerprint())
        prompt = LANDING + "\n" + discovery.requirements_text(restored)
        self.assertEqual(len(read_approved(prompt)), 3)

    def test_followup_revision_keeps_old_decisions_and_updates_named_choice(self):
        updated = updated_decisions(DECISIONS, [
            {"key": "integration.maps", "decision": "required",
             "evidence": "תוסיף מפת סניפים", "reason": "Customer added branch locator"}
        ])
        self.assertEqual(len(updated), 3)
        self.assertEqual(next(d["decision"] for d in updated if d["key"] == "integration.maps"), "required")

    def test_real_architect_contract_excludes_unrequested_ai_voice_maps_and_login(self):
        brief = brief_with_approved_semantics()
        prompt = LANDING + "\n" + discovery.requirements_text(brief)
        contract = ProductArchitect().compile(prompt, project_id="semantic-plant-site",
                                              contract_version=1)
        cap = {r.key for r in contract.capability_plan.requirements if r.required}
        kinds = {r.kind for r in contract.infrastructure}
        self.assertNotIn("target.agent", cap)
        self.assertNotIn("ai.agent.tools", cap)
        self.assertNotIn("media.audio.tts", cap)
        self.assertNotIn("integration.maps", cap)
        self.assertNotIn("auth_session", kinds)
        self.assertIn("target.web", cap)
        required = {r.id for r in contract.product_spec.requirements}
        self.assertNotIn("platform-auth", required)
        self.assertNotIn("platform-rbac", required)
        self.assertTrue(contract.verify_fingerprint())

    def test_fallback_cannot_add_ambiguous_agent_voice_or_map_capabilities(self):
        # Even if the routed worker is down, rules must not turn a Hebrew font
        # or the location of pots on a balcony into a paid provider dependency.
        contract = ProductArchitect().compile(LANDING, project_id="safe-fallback",
                                              contract_version=1)
        cap = {r.key for r in contract.capability_plan.requirements if r.required}
        self.assertFalse({"target.agent", "media.audio.tts", "integration.maps"} & cap)

    def test_explicit_customer_ai_agent_maps_and_narration_remain_required(self):
        prompt = ("תבנה סוכן AI עם כלים משלו, מפות אינטראקטיביות "
                  "וקריינות קולית לכל שיעור")
        contract = ProductArchitect().compile(prompt, project_id="explicit",
                                              contract_version=1)
        keys = {r.key for r in contract.capability_plan.requirements if r.required}
        self.assertTrue({"target.agent", "ai.agent.tools", "integration.maps",
                         "media.audio.tts"}.issubset(keys))

    def test_malformed_semantic_line_is_ignored_without_guessing(self):
        payload = LANDING + "\n--- Approved project brief ---\n" + (
            'Semantic capability decisions v1: {"version":1,"decisions":"unsafe"}')
        self.assertEqual(read_approved(payload), [])


if __name__ == "__main__":
    unittest.main()
