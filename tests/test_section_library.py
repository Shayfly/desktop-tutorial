"""The section library (the owner, 2026-11-20: "תכין את הסקשנים אתה אבל ברמה הכי גבוהה שיש"): the owner's own
law-firm brief assembled from designed sections passes every gate that judges a page -- the G-APPLE design contract
and refusal list, the professional minimum (PRO), every skill unit, the right-to-left time ranges -- and invents
nothing: a section with no content is skipped and said."""
import copy
import os
import re
import unittest

from omni_prod import skill_units as U
from omni_prod import section_library as L
from omni_prod.bidi_ranges import unwrapped_ranges
from omni_prod.g_apple import static
from omni_prod.section_library import demo_law_firm as D


class TheLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.contract, cls.skipped = D.build()

    def test_the_owners_page_passes_the_design_contract_and_its_refusal_list(self):
        self.assertEqual(static.check(self.doc, self.contract), [])

    def test_it_passes_the_professional_minimum_and_every_skill_unit(self):
        self.assertEqual(U.run('design_minimum', self.doc), {'status': 'pass'})
        units = [d for d in os.listdir(os.path.dirname(U.__file__))
                 if os.path.isdir(os.path.join(os.path.dirname(U.__file__), d)) and not d.startswith('_')]
        self.assertGreaterEqual(len(units), 30)
        failed = {u: U.run(u, self.doc) for u in units if U.run(u, self.doc).get('status') != 'pass'}
        self.assertEqual(failed, {})

    def test_time_ranges_keep_their_order_on_a_right_to_left_page(self):
        self.assertEqual(unwrapped_ranges(self.doc), [])
        self.assertIn('<bdi dir="ltr">09:00–18:00</bdi>', self.doc)

    def test_one_h1_and_the_main_action_at_the_top_and_again_at_the_end(self):
        self.assertEqual(len(re.findall(r'<h1\b', self.doc)), 1)
        self.assertGreaterEqual(self.doc.count('href="tel:035551234"'), 3)
        self.assertGreaterEqual(self.doc.count('https://wa.me/97235551234'), 3)

    def test_the_library_css_uses_only_the_contracts_tokens(self):
        self.assertIsNone(re.search(r'#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(', L.CSS))
        self.assertIsNone(re.search(r'(^|[;{\s])--[\w-]+\s*:', L.CSS))           # it defines no custom property
        used = set(re.findall(r'var\((--[\w-]+)\)', L.CSS))
        self.assertEqual(used - set(self.contract['tokens']), set())

    def test_a_section_with_no_content_is_skipped_and_said_never_invented(self):
        content = copy.deepcopy(D.CONTENT)
        del content['faq'], content['stats']
        doc, skipped = L.page(content, self.contract)
        self.assertEqual(skipped, ['stats', 'faq'])
        self.assertNotIn('id="faq"', doc)

    def test_the_customers_text_is_escaped(self):
        content = copy.deepcopy(D.CONTENT)
        content['hero']['title'] = '<script>alert(1)</script>'
        doc, _ = L.page(content, self.contract)
        self.assertNotIn('<script>alert(1)</script>', doc)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', doc)

    def test_nothing_scrolls_sideways_on_a_phone_or_a_wide_screen(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:  # pragma: no cover
            self.skipTest('playwright is required to render the page')
        page_html = re.sub(r'<link[^>]+fonts\.g[^>]+>', '', self.doc)      # offline: the fallback font, same layout rules
        with sync_playwright() as p:
            b = p.chromium.launch()
            over = {}
            for w in (320, 390, 1440):
                pg = b.new_page(viewport={'width': w, 'height': 800})
                pg.set_content(page_html)
                over[w] = pg.evaluate('document.documentElement.scrollWidth - window.innerWidth')
            b.close()
        self.assertEqual(over, {320: 0, 390: 0, 1440: 0})

    def test_the_render_check_sees_every_element_settled_after_300ms(self):
        # g_apple/render.py screenshots 300ms after load: the hero entrance must be over by then, and nothing below the
        # first screen may wait for a scroll to appear (the platform's own reviewers would see a blank page)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:  # pragma: no cover
            self.skipTest('playwright is required to render the page')
        page_html = re.sub(r'<link[^>]+fonts\.g[^>]+>', '', self.doc)
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={'width': 1440, 'height': 900})
            pg.set_content(page_html)
            pg.wait_for_timeout(300)
            faded = pg.evaluate("""[...document.querySelectorAll('main *')].filter(el => {
                const s = getComputedStyle(el); return parseFloat(s.opacity) < 0.99 && !el.closest('.panel-art'); })
                .map(el => el.tagName + '.' + el.className).slice(0, 5)""")
            b.close()
        self.assertEqual(faded, [])


if __name__ == '__main__':
    unittest.main()
