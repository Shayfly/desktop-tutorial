"""First agent, slice 1 (Michael 2026-11-15): tier-3 palettes by global category and the v0 price.

Palettes: 10 categories x 3 styles, 60/30/10, body 7:1, accent label 4.5:1, a failing tone replaced automatically and
listed in `adjusted` (never silent). Used only at tier 3 (no customer colours, no library examples).
Price: 25 NIS a section, +39 media, 99..399, always shown, always "הערכה", never blocking. The butcher of the sketch:
6 sections with one generated image = 189 NIS."""
import unittest

from omni_prod import design_palettes as P
from omni_prod.price_v0 import estimate


class Palettes(unittest.TestCase):
    def test_ten_categories_three_styles_and_conservative_by_default(self):
        self.assertEqual(len(P.CATEGORIES), 10)
        self.assertEqual(P.STYLES, ('conservative', 'warm', 'bold'))
        self.assertEqual(P.palette('restaurants').style, 'conservative')
        for c in P.CATEGORIES:
            self.assertEqual(set(P._RAW[c]), set(P.STYLES), c)

    def test_every_palette_meets_the_contrast_rules_and_is_60_30_10(self):
        for c in P.CATEGORIES:
            for s in P.STYLES:
                d = P.palette(c, s).to_dict()
                self.assertGreaterEqual(d['contrast_body'], 7.0, (c, s))
                self.assertGreaterEqual(d['contrast_accent_label'], 4.5, (c, s))
                self.assertEqual(d['shares'], [60, 30, 10])

    def test_a_failing_tone_is_replaced_and_said(self):
        p = P.build('retail', 'conservative', '#FFFFFF', '#9A9A9A', '#FFD84D')     # grey body 2.8:1, pale accent
        self.assertGreaterEqual(P.contrast(p.text, p.background), 7.0)
        self.assertNotEqual(p.text, '#9A9A9A')
        self.assertTrue(any(a.startswith('text #9A9A9A ->') for a in p.adjusted), p.adjusted)
        self.assertGreaterEqual(P.contrast(p.on_accent, p.accent), 4.5)
        clean = P.build('retail', 'conservative', '#FFFFFF', '#141414', '#1F5F8B')
        self.assertEqual(clean.adjusted, ())                                        # nothing to replace, nothing said

    def test_the_wcag_formula(self):
        self.assertAlmostEqual(P.contrast('#000000', '#FFFFFF'), 21.0, places=2)
        self.assertAlmostEqual(P.contrast('#777777', '#FFFFFF'), 4.48, places=2)

    def test_tiers_customer_then_library_then_category(self):
        self.assertEqual(P.resolve(customer_colours=['#123456'], example_palette={'background': '#fff'},
                                   category='retail')['tier'], 1)
        self.assertEqual(P.resolve(customer_colours=None, example_palette={'background': '#fff'},
                                   category='retail')['source'], 'library')
        t3 = P.resolve(customer_colours=None, example_palette=None, category='restaurants')
        self.assertEqual((t3['tier'], t3['source'], t3['palette']['style']), (3, 'category', 'conservative'))
        self.assertIsNone(P.resolve(customer_colours=[], example_palette=None, category=None)['palette'])

    def test_unknown_category_or_style_fails_loudly(self):
        with self.assertRaises(KeyError):
            P.palette('butchers')
        with self.assertRaises(KeyError):
            P.palette('retail', 'neon')
        with self.assertRaises(ValueError):
            P.contrast('#12345', '#FFFFFF')


class PriceV0(unittest.TestCase):
    def test_the_butcher_of_the_sketch(self):
        e = estimate(sections=6, media=True)
        self.assertEqual((e['amount_ils'], e['label_he'], e['estimate'], e['blocks']), (189, 'הערכה', True, False))

    def test_floor_and_ceiling_are_said(self):
        self.assertEqual((estimate(sections=2, media=False)['amount_ils'], estimate(sections=2, media=False)['clamped']),
                         (99, 'floor'))
        self.assertEqual((estimate(sections=20, media=True)['amount_ils'], estimate(sections=20, media=True)['clamped']),
                         (399, 'ceiling'))
        self.assertIsNone(estimate(sections=10, media=False)['clamped'])
        self.assertFalse(estimate(sections=20, media=True)['blocks'])                # out of range is shown, never blocks

    def test_bad_input_fails_loudly(self):
        for bad in (-1, 2.5, True, '6'):
            with self.assertRaises(ValueError):
                estimate(sections=bad, media=False)


if __name__ == '__main__':
    unittest.main()
