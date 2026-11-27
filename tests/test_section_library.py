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
        sections = [k for k in skipped if ':' not in k]
        self.assertEqual(sections, ['stats', 'pricelist', 'gallery', 'team', 'testimonials', 'faq'])   # not in the brief
        # round 2: an about fact the hero panel already showed (the address) is not said again, and the drop is said
        self.assertEqual([k for k in skipped if ':' in k], ['about.facts:מיקום (already shown)'])
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
            over, narrow = {}, {}
            for w in (320, 390, 1440):
                pg = b.new_page(viewport={'width': w, 'height': 800})
                pg.set_content(page_html)
                over[w] = pg.evaluate('document.documentElement.scrollWidth - window.innerWidth')
                # 2026-11-22 (CI run 44987201290): whether a field at its default width overflows a 320px phone depends
                # on the fonts of the machine -- on CI's Chromium it did not, so a page whose fields had lost their
                # width rule still passed. The rule itself is read: every form field fills its row, on every width.
                narrow[w] = pg.evaluate('''[...document.querySelectorAll(".field input, .field select, .field textarea")]
                    .filter(e => Math.abs(e.getBoundingClientRect().width - e.parentElement.clientWidth) > 1)
                    .map(e => e.tagName + (e.name ? "[" + e.name + "]" : ""))''')
            b.close()
        self.assertEqual(narrow, {320: [], 390: [], 1440: []})      # the rule, independent of the machine's fonts
        self.assertEqual(over, {320: 0, 390: 0, 1440: 0})

    def test_the_production_visual_check_finds_nothing_it_enforces_on_a_phone_or_a_desktop(self):
        # the content route's real chain (2026-11-21): visual_qa's enforced rules failed the page on a phone -- the
        # closed menu's links were measured off-screen and over the hero, and the fixed action bar covered the hero
        # panel's phone link. The same audit, in the same viewports, after the same settle time.
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:  # pragma: no cover
            self.skipTest('playwright is required to render the page')
        from omni_prod import visual_qa as VQ
        audit_js = re.search(r'AUDIT = r"""(.*?)"""', VQ.SCRIPT, re.S).group(1)       # the sandbox script's own audit
        page_html = re.sub(r'<link[^>]+fonts\.g[^>]+>', '', self.doc)
        found = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            for name, v in VQ.VIEWPORTS.items():
                ctx = b.new_context(viewport={'width': v['width'], 'height': v['height']}, is_mobile=v['mobile'],
                                    has_touch=v['mobile'], device_scale_factor=1, locale='he-IL')
                pg = ctx.new_page()
                pg.set_content(page_html)
                pg.wait_for_timeout(1200)
                audit = pg.evaluate(audit_js, v['mobile'])
                found[name] = [f"{f['kind']} {f['at']} {f['detail']}" for f in audit['findings']
                               if f['kind'] in VQ.DEFAULT_ENFORCED]
                ctx.close()
            b.close()
        self.assertEqual(found, {'desktop': [], 'mobile': []})

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

    def test_a_whatsapp_number_of_its_own_is_shown_as_written_and_can_be_dialled(self):
        # the content route: the customer's WhatsApp number (050-5551234) is a fact the page must show as written
        contact = re.search(r'<dl class="contact-list">.*?</dl>', L.page(self.c, self.contract)[0]).group(0)
        self.assertIn('<a href="tel:0505551234">050-5551234</a>', contact)
        self.assertIn('https://wa.me/972505551234', contact)
        self.c['whatsapp'] = self.c['phone']                                 # the same number: said once
        contact = re.search(r'<dl class="contact-list">.*?</dl>', L.page(self.c, self.contract)[0]).group(0)
        self.assertNotIn('וואטסאפ</dt>', contact)

    def test_the_panel_facts_come_before_the_hero_photo_in_the_markup(self):
        # the truth gate reads the first 45,000 characters; an inlined photo must not push the facts past them
        self.c['hero']['image'] = {'src': 'data:image/webp;base64,' + 'A' * 60_000, 'alt': 'המשרד'}
        self.c['layout'] = {'hero': 'split'}        # the boxed panel; the photo-led heroes are tests/test_hero_photo_led.py's
        doc, _ = L.page(self.c, self.contract)
        body = doc[doc.index('<body'):]            # the head's structured data carries the facts too; the page is the body
        self.assertLess(body.index('דרך מנחם בגין 132'), body.index('data:image/webp'))
        self.assertLess(body.index('09:00'), body.index('data:image/webp'))

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


class RoundTwo(unittest.TestCase):
    """Round 2 of the design critique (seven businesses, 20 fixes the design editor measured), 2026-11-21."""
    def setUp(self):
        self.contract = D.build()[1]
        self.c = copy.deepcopy(D.CONTENT)

    def test_the_numbers_strip_is_the_first_tinted_beat_and_no_two_neighbours_share_a_tone(self):
        keys = ['hero', 'stats', 'services', 'about', 'process', 'cta', 'faq', 'contact']
        t = L.tones(keys, 'formal')
        self.assertEqual(t['services'].split()[:1], [])                       # plain right after the tinted strip
        bands = ['section--tint'] + [t[k].replace(' section--flush', '') for k in keys[2:]]
        pairs = [(a, b) for a, b in zip(bands, bands[1:]) if a == b and a]
        self.assertEqual(pairs, [])

    def test_opening_hours_are_kept_whole_per_day(self):
        self.c['hours'] = 'א׳–ה׳ 09:00–18:00 · ו׳ 09:00–13:00'
        doc, _ = L.page(self.c, self.contract)
        self.assertIn('<span class="hours-seg">ו׳ <bdi dir="ltr">09:00–13:00</bdi></span>', doc)
        self.assertRegex(L.CSS, r'bdi,\s*\.hours-seg\{white-space:\s*nowrap')

    def test_the_elegant_hero_carries_the_numbers_in_one_row_and_says_so(self):
        self.c['direction'] = 'elegant'
        doc, skipped = L.page(self.c, self.contract)
        self.assertIn('<dl class="panel-stats">', doc)
        self.assertNotIn('<section class="stats"', doc)
        self.assertIn('stats:merged into the hero panel (elegant)', skipped)

    def test_the_menu_toggle_is_an_icon_not_a_third_button_or_the_word_menu(self):
        doc = L.page(self.c, self.contract)[0]
        self.assertIn('<summary aria-label="ניווט באתר"><svg', doc)
        self.assertNotIn('<summary>תפריט</summary>', doc)

    def test_no_drawing_puts_a_circle_on_an_arch_head_like_a_person(self):
        for name, art in L.ARTS.items():
            apexes = [(float(x) + 70, float(y) - 70) for x, y in re.findall(r'M(\d+) \d+V(\d+)a70', art)]
            for cx, cy, r in re.findall(r'<circle cx="(\d+)" cy="(\d+)" r="(\d+)"', art):
                for ax, ay in apexes:
                    with self.subTest(name=name, circle=(cx, cy)):
                        self.assertGreater(abs(float(cx) - ax), float(r) + 40)

    def test_the_footer_carries_the_hours_and_whatsapp_when_given(self):
        doc = L.page(self.c, self.contract)[0]
        footer = re.search(r'<footer.*?</footer>', doc).group(0)
        self.assertIn('wa.me/972505551234', footer)
        self.assertIn('09:00–18:00', footer)


def words(n: int, seed: str = 'מילה') -> str:
    """Hebrew prose of exactly n characters (words of several lengths, so lines wrap as real copy does)."""
    pool = (seed, 'אחרת', 'ארוכה', 'קצר', 'משפט', 'שירות', 'מקצועי', 'בתל אביב', 'ללקוחות')
    out, i = [], 0
    while len(' '.join(out)) < n:
        out.append(pool[i % len(pool)])
        i += 1
    return ' '.join(out)[:n].rstrip() or seed


def content_at_maxima(direction: str) -> dict:
    """The library's content with every list of the content route at its maximum (site_content.schema.SECTIONS, raised
    by the owner on 2026-11-26) and every list item's strings at their longest -- the largest page the route can
    render. Synthetic test data; the facts are the owner's law-firm brief (demo_law_firm)."""
    from omni_prod.site_content import schema as K
    S, H = K.SECTIONS, K._H
    most = lambda key, field: S[key][field].max                                        # noqa: E731
    c = copy.deepcopy(D.CONTENT)
    c['direction'] = direction
    # every layout variant is drawn: two directions take each axis's first variant, two its second
    pick = 0 if direction in ('formal', 'bold') else 1
    c['layout'] = {axis: opts[pick] for axis, opts in L.LAYOUTS.items()}
    c['hero'].update(title=words(H['h1']), lead=words(220), cta=words(30), note=words(90), panel_label=words(40),
                     panel_caption=words(40))
    c['stats'] = [(str(1990 + i), words(30, 'שנים')) for i in range(most('stats', 'items'))]
    c['services'] = {'eyebrow': words(40), 'title': words(H['h2']), 'lead': words(220),
                     'items': [(words(H['h3'], f'שירות{i}'), words(220)) for i in range(most('services', 'items'))]}
    c['about'] = {'eyebrow': words(40), 'title': words(H['h2']), 'lead': words(220),
                  'paragraphs': [words(400) for _ in range(most('about', 'paragraphs'))],
                  'facts': [(words(20, f'פרט{i}'), words(80, 'ערך')) for i in range(S['about']['facts'].max)]}
    c['process'] = {'eyebrow': words(40), 'title': words(H['h2']),
                    'steps': [(words(H['h3'], f'שלב{i}'), words(200)) for i in range(most('process', 'steps'))]}
    c['faq'] = {'eyebrow': words(40), 'title': words(H['h2']),
                'items': [(words(90, f'שאלה{i}'), words(400)) for i in range(most('faq', 'items'))]}
    c['testimonials'] = {'eyebrow': words(40), 'title': words(H['h2']),
                         'items': [{'text': words(300), 'name': words(20, 'לקוחה')}
                                   for _ in range(most('testimonials', 'items'))]}
    groups, per_group = S['pricelist']['groups'].max, S['pricelist']['groups'].item.fields['items'].max
    c['pricelist'] = {'eyebrow': words(40), 'title': words(H['h2']), 'groups': [
        {'title': words(H['h3'], f'קבוצה{g}'), 'items': [
            {'name': words(H['h4'], f'פריט{i}'), 'price': '1,390 ₪', 'desc': words(120)} for i in range(per_group)]}
        for g in range(groups)]}
    c['cta'] = {'title': words(H['h2']), 'text': words(200)}
    c['contact'] = dict(c['contact'], eyebrow=words(40), title=words(H['h2']), lead=words(220),
                        topics=[words(30, f'נושא{i}') for i in range(S['contact']['topics'].max)])
    # The menu labels and the hero button keep the owner's own lengths: at their schema maxima (7 labels of 24
    # characters, a 30-character button) the page overflows already with the demo's item counts -- 27 px at 1440 and
    # 16 px at 320 (measured 2026-11-26, caps-a; a defect on main, reported, not caused by the item counts). This test
    # proves the item counts.
    c['hero']['cta'] = D.CONTENT['hero']['cta']
    c['nav'] = list(D.CONTENT['nav']) + [('pricelist', 'מחירון'), ('testimonials', 'המלצות')]
    return c


READABLE = """() => {
  const text = 'h1,h2,h3,h4,p,li,dd,dt,summary,figcaption,blockquote,label,.btn';
  const clipped = [...document.querySelectorAll(text)].filter(e => e.offsetParent !== null
      && e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflowX !== 'visible')
    .map(e => e.tagName + '.' + e.className).slice(0, 5);
  const wider = [...document.querySelectorAll('main *')].filter(e => {
      const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > innerWidth + 1 || r.left < -1); })
    .map(e => e.tagName + '.' + e.className).slice(0, 5);
  const small = [...document.querySelectorAll('main p, main li, main dd, main dt, main summary, main figcaption, main label')]
    .filter(e => e.offsetParent !== null && parseFloat(getComputedStyle(e).fontSize) < 14)
    .map(e => e.tagName + '.' + e.className + ' ' + getComputedStyle(e).fontSize).slice(0, 5);
  return {over: document.documentElement.scrollWidth - innerWidth, clipped, wider, small}; }"""


class ItemMaxima(unittest.TestCase):
    """The owner, 2026-11-26 (WAREHOUSE 136 option a): the content route's item maxima were raised (24 services and
    questions, 12 steps, testimonials, facts and topics, 12 groups of 30 prices, 6 numbers and paragraphs). The largest
    page the route can render, in every art direction, in a real browser: nothing scrolls sideways at 320-1440 px,
    no text is clipped or pushed off the screen, body text stays at least 14 px, every item is on the page, and the
    production visual check finds nothing on it that it does not find on the owner's normal page."""
    maxDiff = None

    def test_the_largest_page_fits_every_width_and_stays_readable(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:  # pragma: no cover
            self.skipTest('playwright is required to render the page')
        from omni_prod import visual_qa as VQ
        from omni_prod.site_content import schema as K
        contract = D.build()[1]
        audit_js = re.search(r'AUDIT = r"""(.*?)"""', VQ.SCRIPT, re.S).group(1)
        offline = lambda doc: re.sub(r'<link[^>]+fonts\.g[^>]+>', '', doc)             # noqa: E731
        problems, sizes, audits = {}, {}, {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={'width': 320, 'height': 800})
            for direction in ('formal', 'warm', 'bold', 'elegant'):
                doc, skipped = L.page(content_at_maxima(direction), contract)
                sizes[direction] = len(doc)
                steps = re.search(r'<ol class="steps[^"]*">(.*?)</ol>', doc, re.S).group(1)
                counts = {'services': doc.count('<article class="card">'), 'steps': steps.count('<li>'),
                          'faq': doc.count('<details><summary>'), 'quotes': doc.count('<figure class="quote">'),
                          'price items': doc.count('<div class="item-head">'),
                          'price groups': doc.count('<div class="price-group">')}
                if 'svc-list' in doc:                       # the editorial list layout: rows, not cards
                    counts['services'] = re.search(r'<ol class="svc-list">(.*?)</ol>', doc, re.S).group(1).count('<li>')
                expected = {'services': K.SECTIONS['services']['items'].max, 'steps': K.SECTIONS['process']['steps'].max,
                            'faq': K.SECTIONS['faq']['items'].max, 'quotes': K.SECTIONS['testimonials']['items'].max,
                            'price items': K.SECTIONS['pricelist']['groups'].max
                            * K.SECTIONS['pricelist']['groups'].item.fields['items'].max,
                            'price groups': K.SECTIONS['pricelist']['groups'].max}
                if counts != expected:
                    problems[f'{direction} counts'] = (counts, expected)
                pg.set_content(offline(doc))
                for w in (320, 390, 768, 1024, 1440):
                    pg.set_viewport_size({'width': w, 'height': 800})
                    m = pg.evaluate(READABLE)
                    found = {k: v for k, v in m.items() if v}
                    if found:
                        problems[f'{direction}/{w}'] = found
            for name, v in VQ.VIEWPORTS.items():
                ctx = b.new_context(viewport={'width': v['width'], 'height': v['height']}, is_mobile=v['mobile'],
                                    has_touch=v['mobile'], device_scale_factor=1, locale='he-IL')
                kinds = {}
                for label, doc in (('normal', self.doc_normal()), ('maxima', L.page(content_at_maxima('formal'),
                                                                                    contract)[0])):
                    page = ctx.new_page()
                    page.set_content(offline(doc))
                    page.wait_for_timeout(1200)                  # the production audit's settle time
                    kinds[label] = {f['kind'] for f in page.evaluate(audit_js, v['mobile'])['findings']}
                    page.close()
                audits[name] = sorted(kinds['maxima'] - kinds['normal'])
                ctx.close()
            b.close()
        self.assertEqual(problems, {})
        self.assertEqual(audits, {'desktop': [], 'mobile': []})
        self.assertGreater(min(sizes.values()), 45_000)            # past the preview's cut: preview_smoke.served_cut

    def doc_normal(self):
        return L.page(D.CONTENT, D.build()[1])[0]


if __name__ == '__main__':
    unittest.main()
