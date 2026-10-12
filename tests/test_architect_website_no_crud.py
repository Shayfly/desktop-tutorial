"""Website architecture must not fabricate data entities or CRUD APIs."""
import unittest
from omni_prod import discovery
from omni_prod.intake.contract import from_brief
from omni_prod.planning.architect import ChiefArchitect

class WebsiteArchitectureRegression(unittest.TestCase):
    def test_no_unrequested_crud(self):
        brief = discovery.start(
            "אני רוצה לבנות אתר לחברת נסיעות בשם Test Travel עם דף בית, חיפוש חופשות וטופס יצירת קשר",
            mode=discovery.RECOMMEND)
        plan = ChiefArchitect().plan(from_brief(brief))
        self.assertEqual(plan["product_family"], "website")
        self.assertEqual(plan["data_model"], [])
        self.assertEqual(plan["api_contracts"], [])

if __name__ == "__main__":
    unittest.main()
