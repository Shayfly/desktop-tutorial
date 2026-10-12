"""Explicit product intent must outrank incidental feature words."""
import unittest
from omni_prod.intake.families import classify_family


class ExplicitIntentRegression(unittest.TestCase):
    def test_website_with_integration_terms(self):
        self.assertEqual(classify_family(
            "אני רוצה לבנות אתר לחברת נסיעות עם API לחיפוש חופשות"), "website")

    def test_game_with_site(self):
        self.assertEqual(classify_family(
            "אני רוצה לבנות משחק עם אתר תדמית"), "game")

    def test_native_app(self):
        self.assertEqual(classify_family(
            "אני רוצה לבנות אפליקציה לנייד עם אתר תדמית"), "mobile_app")


if __name__ == "__main__":
    unittest.main()
