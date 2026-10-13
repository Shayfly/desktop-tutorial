"""Approval-bound no-login semantics and private lead-admin regression tests."""
import unittest
from omni_prod.product_architect import ProductArchitect


class VisitorLoginApprovalTests(unittest.TestCase):
    def compile(self, prompt: str):
        return ProductArchitect().compile(prompt, project_id="visitor-auth-test",
                                         contract_version=1)

    def test_explicit_no_login_plain_task_app_has_no_sessions_or_roles(self):
        contract = self.compile("מערכת משימות בעברית בלי התחברות")
        infrastructure = {x.kind for x in contract.infrastructure}
        ids = {r.id for r in contract.product_spec.requirements}
        self.assertNotIn("auth_session", infrastructure)
        # The platform-level operator protections remain mandatory even
        # though no product visitor accounts or sessions are created.
        self.assertIn("platform-auth", ids)
        self.assertIn("platform-rbac", ids)
        auth = next(r.text for r in contract.product_spec.requirements if r.id == "platform-auth")
        self.assertIn("no generated-product visitor sign-in or sessions", auth)

    def test_no_public_login_with_lead_form_keeps_private_admin_protection(self):
        contract = self.compile(
            "דף נחיתה על עציצים. טופס הרשמה לקבלת טיפים שבועיים במייל. "
            "ללא התחברות למבקרים.")
        infrastructure = {x.kind for x in contract.infrastructure}
        reqs = {r.id: r.text for r in contract.product_spec.requirements}
        self.assertIn("auth_session", infrastructure)
        self.assertIn("platform-auth", reqs)
        self.assertIn("Admin-only", reqs["platform-auth"])
        self.assertIn("no public visitor sign-in", reqs["platform-auth"])

    def test_plain_contact_email_does_not_force_admin_auth(self):
        contract = self.compile(
            "אתר תדמית בלי התחברות. הציגו פרטי קשר: hello@example.org.")
        self.assertNotIn("auth_session", {x.kind for x in contract.infrastructure})


if __name__ == "__main__":
    unittest.main()
