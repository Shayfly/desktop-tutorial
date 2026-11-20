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
        self.assertGreaterEqual(self.doc.count('https://wa.me/972505551234'), 3)

    def test_the_library_css_uses_only_the_contracts_tokens(self):
        self.assertIsNone(re.search(r'#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(', L.CSS))
        self.assertIsNone(re.search(r'(^|[;{\s])--[\w-]+\s*:', L.CSS))           # it defines no custom property
        used = set(re.findall(r'var\((--[\w-]+)\)', L.CSS))
        self.assertEqual(used - set(self.contract['tokens']), set())

    def test_a_section_with_no_content_is_skipped_and_said_never_invented(self):
        content = copy.deepcopy(D.CONTENT)
        del content['faq'], content['stats']
        doc, skipped = L.page(content, self.contract)
        self.assertEqual(skipped, ['stats', 'pricelist', 'gallery', 'team', 'testimonials', 'faq'])   # not in the brief
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


class ImagesTeamAndTestimonials(unittest.TestCase):
    """Real images when the customer gives them; a team and testimonials only when given (synthetic test data)."""
    def setUp(self):
        self.contract = D.build()[1]
        self.c = copy.deepcopy(D.CONTENT)
        self.c['hero']['image'] = {'src': '/assets/office.webp', 'alt': 'משרדי כהן ושות׳', 'width': 1200, 'height': 900}
        self.c['about']['image'] = {'src': '/assets/team.webp', 'alt': 'צוות המשרד', 'width': 1200, 'height': 900}
        self.c['team'] = {'eyebrow': 'הצוות', 'title': 'עורכי הדין', 'members': [
            {'name': 'דנה כהן', 'role': 'שותפה'}, {'name': 'יוסי לוי', 'role': 'עורך דין'},
            {'name': 'מיכל רז', 'role': 'עורכת דין', 'photo': {'src': '/assets/m.webp', 'alt': 'מיכל רז'}}]}
        self.c['testimonials'] = {'eyebrow': 'לקוחות', 'title': 'מה אומרים', 'items': [
            {'text': 'ליווי מקצועי.', 'name': 'א׳'}, {'text': 'זמינות.', 'name': 'ב׳'}, {'text': 'תוצאה.', 'name': 'ג׳'}]}
        self.doc, self.skipped = L.page(self.c, self.contract)

    def test_the_richer_page_still_passes_the_contract_and_every_unit(self):
        self.assertEqual(static.check(self.doc, self.contract), [])
        units = [d for d in os.listdir(os.path.dirname(U.__file__))
                 if os.path.isdir(os.path.join(os.path.dirname(U.__file__), d)) and not d.startswith('_')]
        self.assertEqual({u: U.run(u, self.doc) for u in units if U.run(u, self.doc).get('status') != 'pass'}, {})

    def test_the_first_screen_image_is_eager_and_every_other_is_lazy(self):
        imgs = re.findall(r'<img\b[^>]*>', self.doc)
        self.assertIn('loading="eager" fetchpriority="high"', imgs[0])
        self.assertTrue(all('loading="lazy"' in i for i in imgs[1:]), imgs)

    def test_an_image_without_alt_text_is_refused(self):
        self.c['about']['image'] = {'src': '/assets/x.webp', 'alt': ''}
        with self.assertRaises(ValueError):
            L.page(self.c, self.contract)

    def test_a_team_of_three_is_not_a_row_of_three_icon_cards(self):
        # the heading is first in the markup; CSS shows the face on top
        self.assertIn('<article class="member"><h3>דנה כהן</h3>', self.doc)
        self.assertNotIn('THREE_ICON_CARDS', [f['code'] for f in static.check(self.doc, self.contract)])


class WiringReadiness(unittest.TestCase):
    """What the content-document route needs from the library (the wiring judges, 2026-11-20)."""
    def setUp(self):
        self.contract = D.build()[1]
        self.c = copy.deepcopy(D.CONTENT)

    def test_quotes_in_the_customers_text_appear_as_typed_and_are_escaped_inside_attributes(self):
        self.c['name'] = 'כהן ושות\' בע"מ'
        doc, _ = L.page(self.c, self.contract)
        self.assertIn('<b>כהן ושות\' בע"מ</b>', doc)                         # text node: as typed
        self.assertIn('aria-label="כהן ושות&#x27; בע&quot;מ במספרים"', doc)   # attribute: escaped

    def test_the_form_reaches_whatsapp_even_without_javascript_and_never_the_sites_server(self):
        form = re.search(r'<form\b[^>]*>', L.page(self.c, self.contract)[0]).group(0)
        self.assertIn('action="https://wa.me/972505551234"', form)
        self.assertIn('method="get"', form)

    def test_the_panel_facts_come_before_the_hero_photo_in_the_markup(self):
        # the truth gate reads the first 45,000 characters; an inlined photo must not push the facts past them
        self.c['hero']['image'] = {'src': 'data:image/webp;base64,' + 'A' * 60_000, 'alt': 'המשרד'}
        doc, _ = L.page(self.c, self.contract)
        self.assertLess(doc.index('דרך מנחם בגין 132'), doc.index('data:image/webp'))
        self.assertLess(doc.index('09:00'), doc.index('data:image/webp'))

    def test_the_customers_outline_sets_the_order_and_leaves_out_what_it_does_not_name(self):
        doc, skipped = L.page(self.c, self.contract, order=['faq', 'services', 'contact'])
        ids = re.findall(r'<section[^>]*\bid="(\w+)"', doc)
        self.assertEqual(ids, ['top', 'faq', 'services', 'contact'])
        self.assertIn('about', skipped)
        self.assertNotIn('href="#about"', doc)                               # no link to a section left out
        with self.assertRaises(ValueError):
            L.page(self.c, self.contract, order=['services', 'blog'])

    def test_a_number_the_hero_panel_shows_is_not_repeated_in_the_strip_and_the_drop_is_said(self):
        self.c['stats'] = [('+1,500', 'תיקים'), ('3', 'עורכי דין'), ('2008', 'פעילים מאז')]   # the panel shows +1,500
        doc, skipped = L.page(self.c, self.contract)
        strip = re.search(r'<section class="stats".*?</section>', doc).group(0)
        self.assertNotIn('+1,500', strip)
        self.assertIn('stats:+1,500 (shown in the hero panel)', skipped)

    def test_the_page_carries_the_library_fingerprint_and_fits_the_truth_gate_window(self):
        doc = L.page(self.c, self.contract)[0]
        self.assertIn(f'data-148-kit="section-library/{L.LIBRARY_VERSION}"', doc)
        self.assertLess(len(doc), 45_000)
        self.assertNotIn('/*', L.CSS)


if __name__ == '__main__':
    unittest.main()
