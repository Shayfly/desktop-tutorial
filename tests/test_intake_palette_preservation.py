"""Requested palettes survive discovery, intake and the architecture contract."""
import unittest
from omni_prod import discovery as d
from omni_prod.intake.contract import from_brief
from omni_prod.intake.interpreter import DeterministicInterpreter

PROMPT = ('אני רוצה לבנות אתר לחברת נסיעות בשם Test Travel, עם דף בית, '
          'חיפוש חופשות, טופס יצירת קשר ועיצוב כחול ולבן.')


class PalettePreservationTests(unittest.TestCase):
    def test_discovery_retains_both_requested_colours(self):
        brief = d.start(PROMPT, mode=d.RECOMMEND)
        self.assertEqual(brief.values()['color'], 'כחול, לבן')
        self.assertEqual(brief.fields['color']['source'], 'message')

    def test_interpreter_and_contract_agree_on_valid_css_tokens(self):
        proposals = DeterministicInterpreter().interpret(PROMPT).proposals
        colour = next(p.value for p in proposals if p.field == 'color')
        self.assertEqual(colour, 'כחול, לבן')
        contract = from_brief(d.start(PROMPT, mode=d.RECOMMEND))
        self.assertEqual(contract.design_preferences['palette_css'], ['#1d4ed8', '#ffffff'])

    def test_builder_receives_valid_primary_and_full_palette(self):
        brief = d.answer(d.start('Build a website'), {'color': 'כחול ולבן'})
        text = d.requirements_text(brief)
        self.assertIn('primary colour #1d4ed8', text)
        self.assertIn('palette #1d4ed8, #ffffff', text)
        self.assertNotIn('primary colour כחול ולבן', text)

    def test_single_and_repeated_hex_colours_survive_conversation(self):
        for text, expected in [('Use white', 'white'), ('Use black', 'black'),
                               ('Use #123456', '#123456'),
                               ('Use #ffffff and blue', '#ffffff, blue')]:
            with self.subTest(text=text):
                proposals = DeterministicInterpreter().interpret(text).proposals
                self.assertEqual(next((p.value for p in proposals if p.field == 'color'), None), expected)


if __name__ == '__main__':
    unittest.main()
