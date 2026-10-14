"""Regression: a customer website request must not become an internal CRUD application."""
import unittest
from omni_prod import discovery as d
from omni_prod.intake.contract import from_brief

PROMPT = ("אני רוצה לבנות אתר לחברת נסיעות בשם Test Travel, עם דף בית, "
          "חיפוש חופשות, טופס יצירת קשר ועיצוב כחול ולבן.")


class WebsiteRequirementsRegression(unittest.TestCase):
    def test_website_defaults_derive_requested_sections(self):
        brief = d.start(PROMPT, mode=d.RECOMMEND)
        self.assertEqual(d.is_website(brief), True)
        self.assertEqual(brief.values()["audience"], "public")
        screens = brief.values()["screens"]
        for section in ("דף בית", "חיפוש חופשות", "טופס יצירת קשר"):
            self.assertIn(section, screens)
        self.assertNotIn("טופס הוספה", screens)
        self.assertNotIn("רשימה", screens)

    def test_contract_family_and_screens(self):
        brief = d.start(PROMPT, mode=d.RECOMMEND)
        contract = from_brief(brief)
        self.assertEqual(contract.product_family, "website")
        self.assertIn("חיפוש חופשות", contract.functional_requirements[1].text)
        self.assertNotIn("rides", str(contract.to_dict()))

if __name__ == "__main__":
    unittest.main()
