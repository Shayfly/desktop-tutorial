"""#324, production 2026-11-13 (build bld_5a37dc27..., "מאפייה"): the brief described the image --
"תמונה ראשית גדולה בראש הדף: כיכרות לחם מחמצת טריות על מדף עץ במאפייה, אור בוקר חם" -- but describe() cut the clause
at the colon. The constraint was subject="תמונה ראשית גדולה בראש הדף", prompt_en="A large main image at the top of the
page." and FLUX drew mountains. The style and colours ("סגנון חמים וכפרי, צבעים: חום קרמל, שמנת ולבן") never reached it.
"""
import unittest

from omni_prod import generated_images as G
from omni_prod.capability_planner import CapabilityPlanner
from omni_prod.image_prompt import source_text

BAKERY = '''דף נחיתה בעברית למאפייה "לחם הבית", רחוב הרצל 40, רחובות.
טלפון להזמנות: 08-9461234. כפתור "התקשרו להזמנה" מחייג למספר הזה.
שעות פתיחה: א׳–ה׳ 07:00–19:00, ו׳ 07:00–14:00, שבת סגור.
תמונה ראשית גדולה בראש הדף: כיכרות לחם מחמצת טריות על מדף עץ במאפייה, אור בוקר חם.
סגנון חמים וכפרי, צבעים: חום קרמל, שמנת ולבן.
חלקים: כותרת עם התמונה, על המאפייה (אופים כל בוקר במקום מאז 1998), מוצרים (לחם מחמצת, חלות, מאפי בוקר), שעות פתיחה, כתובת וטלפון.
דף תוכן בלבד: בלי התחברות, בלי תשלומים, בלי טופס.'''
DESCRIBED = 'כיכרות לחם מחמצת טריות על מדף עץ במאפייה, אור בוקר חם'


class TheDescriptionAfterTheColon(unittest.TestCase):
    def test_the_production_brief(self):
        self.assertEqual(G.describe(BAKERY, 'hero/brand visual'), DESCRIBED)        # commas belong to it

    def test_the_constraints_carry_the_description_style_and_colours(self):
        c = CapabilityPlanner._image_constraints('media.image.generate', 'hero/brand visual', BAKERY)
        self.assertEqual(c, {'aspect_ratio': '16:9', 'subject': DESCRIBED, 'style': 'חמים וכפרי',
                             'colours': 'חום קרמל, שמנת ולבן'})
        source = source_text(c)                                    # what is translated for FLUX
        for words in ('כיכרות לחם מחמצת', 'מדף עץ', 'אור בוקר חם', 'חמים וכפרי', 'חום קרמל'):
            self.assertIn(words, source)
        self.assertNotIn('בראש הדף', source)                       # the label is not the picture

    def test_the_alt_is_the_description(self):
        self.assertEqual(G.alt_text(BAKERY, 'hero/brand visual', subject=DESCRIBED), DESCRIBED)

    def test_a_line_break_ends_the_description(self):
        self.assertEqual(G.describe('תמונה ראשית: כוס קפה על שולחן עץ\nסגנון נקי', 'hero'), 'כוס קפה על שולחן עץ')

    def test_a_label_with_nothing_after_it_keeps_the_label(self):
        self.assertEqual(G.describe('דף נחיתה. תמונה ראשית גדולה:', 'hero'), 'תמונה ראשית גדולה')

    def test_the_plans_design_line_still_wins(self):
        prompt = BAKERY + "\n--- Approved project brief ---\nDesign: style rustic; requested colour description 'caramel'"
        c = CapabilityPlanner._image_constraints('media.image.generate', 'hero/brand visual', prompt)
        self.assertEqual((c['style'], c['colours']), ('rustic', 'caramel'))
        self.assertEqual(c['subject'], DESCRIBED)


if __name__ == '__main__':
    unittest.main()
