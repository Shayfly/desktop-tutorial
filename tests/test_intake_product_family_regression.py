"""Regression for Hebrew website requests without the literal 'אתר תדמית'."""
import unittest
from omni_prod.intake.families import classify_family

class ProductFamilyRegression(unittest.TestCase):
    def test_travel_business_website(self):
        self.assertEqual(classify_family(
            "אני רוצה לבנות אתר לחברת נסיעות בשם Test Travel, עם דף בית, חיפוש חופשות, טופס יצירת קשר ועיצוב כחול ולבן."
        ), "website")

    def test_business_site(self):
        self.assertEqual(classify_family("אתר לעסק עם דף בית וצור קשר"), "website")

    def test_game_priority_preserved(self):
        self.assertEqual(classify_family("משחק דפדפן באתר לחברת משחקים"), "game")

if __name__ == "__main__":
    unittest.main()
