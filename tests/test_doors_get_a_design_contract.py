"""A doors company gets a palette and therefore a design contract (production 2026-11-17, "148 דלתות", bld_a875456f:
"the business category is not recognised" -- no palette, so G-APPLE had no contract and reported NOT_RUN, and the
model chose the colours unchecked). Doors are a trade: installation work, the palette of renovation."""
import unittest

from omni_prod import rehearsal as R
from omni_prod import vertical_palettes as V
from omni_prod.g_apple import contract as C

# the production request's own opening lines (intake_messages, read only)
DOORS = ('שם העסק: 148 דלתות בהנהלת: נסים אוחנה טלפון: 050-345-6723 אזור שירות: אשקלון, אשדוד, קרית גת, שדרות '
         'והסביבה מה זה: התקנת דלתות ממד פולימריות ודלתות פנים.')


class DoorsAreATrade(unittest.TestCase):
    def test_the_production_request_is_recognised(self):
        self.assertEqual(V.category_of(DOORS), 'renovation')
        for text in ('אתר לחנות דלתות באשדוד', 'התקנת דלתות פנים', 'דלת ממד במבצע', 'interior doors installer'):
            self.assertEqual(V.category_of(text), 'renovation', text)

    def test_the_brief_carries_a_palette_and_g_apple_locks_a_contract(self):
        prompt = R.approved_prompt(DOORS, {'content_only': 'yes', 'personal_data': 'no', 'login': 'none'})
        _, palette = V.palette_for('renovation')
        self.assertIn(f"primary colour {palette['primary']}", prompt)
        contract = C.build(prompt)                                    # raised ContractError before
        self.assertEqual(contract['tokens']['--color-primary'], palette['primary'])

    def test_a_door_in_another_trade_does_not_make_it_a_door_shop(self):
        self.assertEqual(V.category_of('דלת הכניסה של האטליז השכונתי ברחוב הרצל'), 'butcher')
        self.assertIsNone(V.category_of('דף לחנות פרחים קטנה'))       # an unknown business is still said, not guessed


class TheMeasureRuleKeepsItsOwnCheck(unittest.TestCase):
    def test_the_rule_gives_a_fixed_width_not_a_ch_value(self):
        """Rehearsal 44057019675: the rule said "about 52ch" and the page it produced measured 53 characters a line,
        under the check's 55. The rule and the check must agree; a ch width depends on the font."""
        prompt = R.approved_prompt(DOORS, {'content_only': 'yes', 'personal_data': 'no', 'login': 'none'})
        rules = C.rules(C.build(prompt))
        self.assertIn('max-width: 35rem', rules)
        self.assertNotIn('52ch', rules)
        from omni_prod.g_apple import render
        self.assertEqual((render.MEASURE_MIN, render.MEASURE_MAX), (55, 75))   # the check is unchanged


if __name__ == '__main__':
    unittest.main()
