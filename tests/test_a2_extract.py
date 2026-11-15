"""A2 step 5: deterministic extraction (omni_prod/a2/extract.py) on pages served offline (tests/a2_offline_sites.py).

What it reads is measured from the rendered DOM by fixed rules -- no model, no network -- and every result is checked
against reference_card.schema.json (skeleton + the extraction block). Text, logos, images and code are not taken.
"""
import json
import os
import unittest

from omni_prod.a2 import extract as X
from tests.a2_offline_sites import Sites, url
from tests.test_a2_collect import READY, REQUIRED


class TheRulesWithoutABrowser(unittest.TestCase):
    MEASURES = {'sections': [{'kind': k, 'top': i * 100, 'height': 90, 'padTop': 0, 'padBottom': 0}
                             for i, k in enumerate(['nav', 'hero', 'products', 'hero', 'faq', 'footer', None])],
                'sectionGaps': [96, 128, 0], 'inner': [8, 16, 24, 40], 'sizes': {'64': 1, '30': 2, '18': 9, '13': 4},
                'hero': {'type': 'split', 'img': [640, 480], 'headline_lines': 2, 'cta_count': 1},
                'area': {'bg': {'rgb(251, 247, 242)': 10}, 'text': {'rgb(28, 25, 23)': 8, 'rgb(87, 83, 78)': 1},
                         'muted': {'rgb(28, 25, 23)': 5, 'rgb(87, 83, 78)': 3}, 'accent': {'rgba(0, 0, 0, 0.5)': 9}},
                'radii': [8, 8, 999], 'forms': [{'fields': 3, 'types': ['tel', 'text', 'password']}], 'photos': 2,
                'svgs': 0, 'fullBleed': 0, 'components': ['form', 'age_gate'], 'row': 4, 'dark': False}

    def test_the_mapping_is_deterministic_and_inside_the_schema(self):
        a, b = X.from_measures(self.MEASURES), X.from_measures(json.loads(json.dumps(self.MEASURES)))
        self.assertEqual(a, b)
        X._check('skeleton', a['skeleton'])
        X._check('extraction', a['extraction'])
        self.assertEqual(a['skeleton']['section_order'], ['nav', 'hero', 'products', 'faq', 'footer'])  # once each
        self.assertEqual(a['skeleton']['hero']['image_ratio'], '4:3')
        self.assertEqual(a['skeleton']['type_scale_px'], [64, 30, 18, 13])
        self.assertEqual(a['skeleton']['rhythm']['section_gap_px'], [96, 128])

    def test_muted_is_never_the_text_colour_and_a_translucent_colour_is_not_observed(self):
        p = X.from_measures(self.MEASURES)['extraction']['palette']
        self.assertEqual((p['text']['hex'], p['muted']['hex']), ('#1c1917', '#57534e'))
        self.assertNotIn('accent', p)                         # rgba(..., 0.5) is not a colour we can claim we saw

    def test_only_closed_values_leave_the_page(self):
        e = X.from_measures(self.MEASURES)['extraction']
        self.assertEqual(e['forms'], [{'fields': 3, 'types': ['tel', 'text']}])    # 'password' is not in the list
        self.assertNotIn('tone', e)                                               # the model's field: absent, not guessed


@unittest.skipUnless(READY, 'needs Chromium and Playwright (the a2-offline CI job requires them)')
class OnRenderedPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from omni_prod.a2 import browser
        cls.sites = Sites()
        cls._cm = browser.session(offline_origin=cls.sites.origin)
        cls.session = cls._cm.__enter__()
        cls.out = {n: X.extract(cls.session, url(n)) for n in ('rich-butcher', 'wine-bar', 'good-0', 'good-2')}

    @classmethod
    def tearDownClass(cls):
        cls._cm.__exit__(None, None, None)
        cls.sites.close()

    def test_sections_in_page_order(self):
        self.assertEqual(self.out['rich-butcher']['skeleton']['section_order'],
                         ['nav', 'hero', 'products', 'hours', 'location', 'contact', 'footer'])

    def test_hero_and_rhythm(self):
        k = self.out['rich-butcher']['skeleton']
        self.assertEqual(k['hero'], {'type': 'split', 'image_ratio': '4:3', 'headline_lines': 1, 'cta_count': 1})
        self.assertEqual(k['rhythm']['section_gap_px'], [96, 96])            # nav and footer are not the rhythm
        self.assertEqual(self.out['wine-bar']['skeleton']['hero']['type'], 'full_bleed')
        self.assertEqual(self.out['good-2']['skeleton']['hero']['type'], 'centered')

    def test_palette_by_role_is_observed(self):
        p = self.out['rich-butcher']['extraction']['palette']
        self.assertEqual({r: v['hex'] for r, v in p.items()},
                         {'bg': '#fbf7f2', 'surface': '#ffffff', 'line': '#e7ded3', 'text': '#1c1917',
                          'muted': '#57534e', 'accent': '#9a3412', 'accent_text': '#ffffff'})
        self.assertTrue(all(v['provenance'] == 'observed' for v in p.values()))

    def test_windows_are_found_and_kept_out_of_the_palette(self):
        self.assertEqual(self.out['wine-bar']['extraction']['components'], ['age_gate', 'promo_bar'])
        self.assertNotIn('#0c0a09', [v['hex'] for v in self.out['wine-bar']['extraction']['palette'].values()])
        self.assertEqual(self.out['rich-butcher']['extraction']['components'],
                         ['cookie_banner', 'floating_call_button', 'form', 'map_embed', 'table'])

    def test_dark_and_light_hero(self):
        self.assertIn('dark_hero', self.out['wine-bar']['skeleton']['traits'])
        self.assertIn('light_hero', self.out['good-0']['skeleton']['traits'])
        self.assertIn('dark_hero', self.out['good-2']['skeleton']['traits'])

    def test_no_text_of_the_site_is_kept(self):
        dumped = json.dumps(self.out, ensure_ascii=False)
        for words in ('קצביית השכונה', 'בשר טרי', 'בר היין', 'האם מלאו לך', 'עוגיות', '07:00'):
            self.assertNotIn(words, dumped)

    def test_nothing_left_the_machine(self):
        self.assertEqual(sorted(set(self.session.blocked)), ['maps.example.com'])

    # ---- 109 / 110 (the owner, 2026-11-15 23:26) ------------------------------------------------------------------
    def test_a_page_with_no_style_of_its_own_is_rejected_no_styles(self):
        with self.assertRaises(X.ExtractRejected) as caught:
            X.extract(self.session, url('bare'))
        self.assertEqual(caught.exception.reason_code, 'no_styles')

    def test_a_linked_stylesheet_that_did_not_load_is_rejected_not_measured(self):
        with self.assertRaises(X.ExtractRejected) as caught:
            X.extract(self.session, url('broken-css'))
        self.assertEqual(caught.exception.reason_code, 'stylesheet_missing')

    def test_every_field_says_who_set_it(self):
        rich = self.out['rich-butcher']['extraction']['field_source']
        self.assertEqual({k: rich[k] for k in ('bg', 'text', 'accent', 'type_scale_px', 'rhythm', 'hero')},
                         {'bg': 'authored', 'text': 'authored', 'accent': 'authored', 'type_scale_px': 'authored',
                          'rhythm': 'authored', 'hero': 'authored'})
        thin = X.extract(self.session, url('margin-only'))['extraction']['field_source']
        self.assertEqual((thin.get('text'), thin['type_scale_px']), ('ua-default', 'ua-default'))


if __name__ == '__main__':
    unittest.main()
