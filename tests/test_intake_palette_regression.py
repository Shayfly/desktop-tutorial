"""Regression: multi-colour customer briefs must not become CSS values."""
import unittest

from omni_prod.intake.interpreter import DeterministicInterpreter


class IntakePaletteRegression(unittest.TestCase):
    def test_travel_brief_extracts_palette_without_product_text(self):
        prompt = ("אני רוצה לבנות אתר לחברת נסיעות בשם Test Travel, "
                  "עם דף בית, חיפוש חופשות, טופס יצירת קשר ועיצוב כחול ולבן.")
        result = DeterministicInterpreter().interpret(prompt)
        colour = next(p.value for p in result.proposals if p.field == "color")
        self.assertEqual(colour, "כחול, לבן")
        self.assertNotIn("חברת נסיעות", colour)
        self.assertNotIn("טופס", colour)

    def test_single_colour_still_works(self):
        result = DeterministicInterpreter().interpret("אתר בצבע כחול")
        colour = next(p.value for p in result.proposals if p.field == "color")
        self.assertEqual(colour, "blue")

    def test_palette_is_bounded(self):
        result = DeterministicInterpreter().interpret(
            "צבעים כחול לבן אדום ירוק צהוב שחור סגול כתום")
        colour = next(p.value for p in result.proposals if p.field == "color")
        self.assertLessEqual(len(colour.split(", ")), 6)


if __name__ == "__main__":
    unittest.main()
