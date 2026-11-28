"""Warehouse 129 (the owner, 2026-11-22; the standing release of 2026-11-27), the part the first slice (faa4899) left: the
section library writes its OWN words, and spaces its page, in the script of the page -- Hebrew or Arabic -- instead of
refusing every script but Hebrew.

  * words.json: one table per script, the same keys (a missing key fails when the library is imported, nothing falls back
    to Hebrew), the Hebrew table being the text the library always wrote;
  * an Arabic contract (a pair from the Arabic library) renders `lang="ar" dir="rtl"`, with the pair's fonts, and not one
    Hebrew letter around the customer's Arabic;
  * spacing (ריווח): Arabic letters connect, so a page of that script gets no letter-spacing at all and taller lines;
    a Hebrew page is byte for byte what it was (no override is written);
  * a script the words table lacks (Latin, a declared-but-unsupported one) is refused, never rendered with Hebrew around it.

What is NOT met, said: an Arabic BRIEF still goes to the legacy path ('not_hebrew', tests/test_typography_scripts.py): the
content route's validators (invented numbers, claims, always-open hours, contact words) are written for Hebrew, and a
route opened to Arabic without Arabic ones would pass copy the gates cannot judge. So 129.1 holds for the library's
page, the fonts, the direction and the formats (tests/test_typography_scripts.py), not yet for a built Arabic site."""
import copy
import json
import os
import re
import unittest
from pathlib import Path

from omni_prod import section_library as L
from omni_prod import skill_units as U
from omni_prod import typography as T
from omni_prod.g_apple import contract as C
from omni_prod.section_library import demo_law_firm as D

HEBREW_LETTER = re.compile('[֐-׿]')
ARABIC_LETTER = re.compile('[؀-ۿ]')
BUSINESS = 'بيت الزيتون'


def arabic_pair():
    return T.pair_for('arabic', category='restaurants', tone='warm', business=BUSINESS)


def hebrew_pair():
    return T.pair_for('hebrew', category='restaurants', tone='warm', business='בית הזית')


def contract(pair):
    return C.build(D.BRIEF_DESIGN, T.contract_fonts(pair))


def arabic_content():
    """The same page as the demo law firm's, written in Arabic by the customer (the library's own words are not in it)."""
    c = copy.deepcopy(D.CONTENT)
    c.update(
        title='بيت الزيتون – مطعم في الناصرة', description='مطعم عائلي في الناصرة يقدم المأكولات المحلية منذ عام 2008.',
        name=BUSINESS, tagline='مطعم · الناصرة', phone='04-6012345', whatsapp='050-5551234',
        address='شارع بولس السادس 12، الناصرة', hours='الأحد–الخميس 09:00–18:00',
        nav=[('services', 'الأطباق'), ('about', 'عن المطعم'), ('contact', 'تواصلوا معنا')], schema_type='Restaurant')
    c['hero'] = {'eyebrow': 'مطعم عائلي', 'title': 'مأكولات محلية في قلب الناصرة', 'lead': 'طعام طازج كل يوم، من مطبخ عائلتنا إليكم',
                 'cta': 'احجزوا طاولة', 'note': 'الحجز مسبقاً للمجموعات', 'panel_label': 'المطعم باختصار', 'art': 'lines',
                 'panel_facts': [('الساعات', 'الأحد–الخميس 09:00–18:00'), ('العنوان', 'شارع بولس السادس 12، الناصرة')]}
    c['stats'] = [('2008', 'نعمل منذ'), ('3', 'فروع')]
    c['services'] = {'eyebrow': 'الأطباق', 'title': 'ما نقدمه', 'items': [('المقلوبة', 'طبق الأرز واللحم على الطريقة المحلية.'),
                                                                   ('الفتة', 'فتة الحمص والزبادي.')]}
    c['about'] = {'eyebrow': 'عن المطعم', 'title': 'مطعم عائلي منذ 2008',
                  'paragraphs': ['بيت الزيتون مطعم عائلي في الناصرة.', 'نطبخ كل يوم من مكونات طازجة.'],
                  'facts': [('المطبخ', 'محلي')]}
    c['process'] = {'eyebrow': 'كيف نعمل', 'title': 'ثلاث خطوات', 'steps': [('تختارون', 'من قائمة الأطباق.'),
                                                                         ('نطبخ', 'الطعام طازجاً.')]}
    c['faq'] = {'eyebrow': 'أسئلة شائعة', 'title': 'ما يسألونه قبل الزيارة',
                'items': [('هل يلزم الحجز؟', 'للمجموعات فقط.'), ('هل يوجد موقف؟', 'نعم، أمام المطعم.')]}
    c['cta'] = {'title': 'تريدون طاولة؟', 'text': 'اتصلوا أو اكتبوا لنا على واتساب.'}
    c['contact'] = {'eyebrow': 'تواصلوا معنا', 'title': 'يسعدنا سماعكم', 'lead': 'اكتبوا لنا بضع تفاصيل.',
                    'topics': ['حجز طاولة', 'مناسبة خاصة']}
    c['team'] = {'title': 'الفريق', 'members': [{'name': 'الدكتور سامي حداد', 'role': 'الشيف'}, {'name': 'منى خوري', 'role': 'المديرة'}]}
    return c


class TheWordsTable(unittest.TestCase):
    def test_every_script_has_the_same_keys_and_a_text_for_each(self):
        self.assertEqual(sorted(L.WORDS), ['arabic', 'hebrew'])
        self.assertEqual(set(L.WORDS['arabic']), set(L.WORDS['hebrew']))
        self.assertTrue(all(isinstance(v, str) and v for t in L.WORDS.values() for v in t.values()))
        self.assertEqual(set(L.TITLES), set(L.WORDS))

    def test_the_hebrew_table_is_the_text_the_library_always_wrote(self):
        h = L.WORDS['hebrew']
        self.assertEqual(h['form_note'], 'השליחה פותחת את וואטסאפ עם ההודעה מוכנה. היא נשלחת רק כשתלחצו שם על שליחה, ולא נשמרת באתר.')
        self.assertEqual(h['cookie_text'], 'האתר עשוי להשתמש בעוגיות. בחרו אם לאשר את כולן או רק את ההכרחיות לפעולתו.')
        self.assertEqual((h['skip'], h['whatsapp'], h['contact_us']), ('דלגו לתוכן', 'וואטסאפ', 'יצירת קשר'))
        self.assertEqual((L.FORM_NOTE, L.COOKIE_TEXT), (h['form_note'], h['cookie_text']))
        self.assertIn('ד״ר', L.TITLES['hebrew'])

    def test_no_script_table_carries_the_letters_of_another(self):
        for key, text in L.WORDS['arabic'].items():
            with self.subTest(arabic=key):
                self.assertIsNone(HEBREW_LETTER.search(text))
                self.assertIsNotNone(ARABIC_LETTER.search(text))
        for key, text in L.WORDS['hebrew'].items():
            with self.subTest(hebrew=key):
                self.assertIsNone(ARABIC_LETTER.search(text))

    def test_a_table_that_misses_a_key_or_names_an_unknown_script_fails_the_import_check(self):
        saved = L.WORDS
        try:
            broken = copy.deepcopy(saved)
            del broken['arabic']['skip']
            L.WORDS = broken
            with self.assertRaises(ValueError):
                L._check_words()
            odd = copy.deepcopy(saved)
            odd['klingon'] = dict(odd['hebrew'])
            L.WORDS = odd
            with self.assertRaises(T.UnknownScript):
                L._check_words()
        finally:
            L.WORDS = saved
        L._check_words()

    def test_an_unknown_key_raises_and_never_falls_back_to_hebrew(self):
        with self.assertRaises(KeyError):
            L._w('no_such_word')


class TheArabicPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pair = arabic_pair()
        cls.contract = contract(cls.pair)
        cls.html, cls.skipped = L.page(arabic_content(), cls.contract, windows=('cookie_banner',))

    def test_it_is_right_to_left_arabic_with_the_pairs_fonts(self):
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertIn('property="og:locale" content="ar_AR"', self.html)
        self.assertIn(T.font_link(self.pair), self.html)
        self.assertEqual((self.contract['tokens']['--font-family'], self.contract['tokens']['--font-display']),
                         (T.stack(self.pair['body']), T.stack(self.pair['display'])))
        self.assertTrue(self.pair['id'].startswith('ar-'))

    def test_not_one_hebrew_letter_is_left_on_the_page(self):
        self.assertIsNone(HEBREW_LETTER.search(self.html), HEBREW_LETTER.findall(self.html)[:10])

    def test_the_librarys_own_words_are_arabic(self):
        a = L.WORDS['arabic']
        for key in ('skip', 'nav_main', 'contact_us', 'cookie_accept', 'cookie_necessary', 'quick_actions', 'form_aria',
                    'full_name', 'cookie_region'):
            with self.subTest(key):
                self.assertIn(a[key], self.html)
        self.assertIn(L.e(a['form_note']), self.html)                       # the form's note, when the customer gave none
        self.assertIn(L.e(a['cookie_text']), self.html)
        self.assertIn(f'var d=new FormData(f),t="{a["js_hello"]}"', self.html)  # the message the form hands to WhatsApp
        self.assertIn(L.ea(a['stats_label'].format(name=BUSINESS)), self.html)                 # the numbers strip's label

    def test_a_member_without_a_photo_gets_initials_without_the_title(self):
        self.assertIn('<span class="member-initials" aria-hidden="true">سح</span>', self.html)    # الدكتور سامي حداد
        self.assertIn('<span class="member-initials" aria-hidden="true">مخ</span>', self.html)    # منى خوري

    def test_the_spacing_override_is_there_once_and_comes_after_the_librarys_css(self):
        css = T.spacing_css('arabic')
        self.assertEqual(self.html.count(css), 1)
        self.assertIn('letter-spacing:0!important', css)
        self.assertGreater(self.html.index(css), self.html.index('.skip'))

    def test_hebrew_and_arabic_pages_never_share_a_font_family(self):
        he = L.page(D.CONTENT, contract(hebrew_pair()))[0]
        used = lambda pair: {pair[r]['family'] for r in ('display', 'body')}      # noqa: E731
        self.assertEqual(used(hebrew_pair()) & used(self.pair), set())
        for family in used(self.pair):
            self.assertNotIn(family.replace(' ', '+'), he)
        for family in used(hebrew_pair()):
            self.assertNotIn(family.replace(' ', '+'), self.html)

    def test_a_hebrew_page_has_no_override_and_no_arabic_word(self):
        he, _ = L.page(D.CONTENT, contract(hebrew_pair()), windows=('cookie_banner',))
        self.assertNotIn('letter-spacing:0!important', he)
        self.assertEqual(T.spacing_css('hebrew'), '')
        self.assertIsNone(ARABIC_LETTER.search(he))
        self.assertIn('<html lang="he" dir="rtl">', he)

    def test_a_heading_longer_than_the_arabic_limit_fails_naming_the_script(self):
        content = arabic_content()
        content['hero']['title'] = 'م' * (T.script('arabic')['heading_max_chars']['h1'] + 1)
        with self.assertRaises(T.HeadingTooLong) as caught:
            L.page(content, self.contract)
        self.assertIn('the arabic limit is 60', str(caught.exception))

    def test_every_skill_unit_that_judges_a_page_passes_on_it(self):
        names = [d for d in os.listdir(os.path.dirname(U.__file__))
                 if os.path.isdir(os.path.join(os.path.dirname(U.__file__), d)) and not d.startswith('_')]
        failed = {u: U.run(u, self.html) for u in names if U.run(u, self.html).get('status') != 'pass'}
        self.assertEqual(failed, {})


class TheScriptsTheLibraryHasNoWordsFor(unittest.TestCase):
    def test_a_latin_page_is_refused_not_rendered_with_hebrew_around_it(self):
        latin = contract(T.pair_for('latin', category='restaurants', tone='warm', business='Olive House'))
        with self.assertRaises(T.UnsupportedScript) as caught:
            L.page(copy.deepcopy(D.CONTENT), latin)
        self.assertIn('latin', str(caught.exception))

    def test_a_pair_that_is_not_in_the_library_is_refused(self):
        bad = T.contract_fonts(arabic_pair())
        bad['pair'] = 'ar-no-such-pair'
        with self.assertRaises(T.FontNotInLibrary):
            L.page(arabic_content(), C.build(D.BRIEF_DESIGN, bad))


class TheSpacingSchema(unittest.TestCase):
    OVERRIDE = {'mode': 'override', 'connected': True, 'letter_spacing': '0', 'word_spacing': '0.05em',
                'body_line_height': 1.85, 'heading_line_height': 1.4}

    def test_the_shipped_registry_says_arabic_overrides_and_hebrew_and_latin_do_not(self):
        self.assertEqual({n: T.script(n)['spacing']['mode'] for n in ('hebrew', 'arabic', 'latin')},
                         {'hebrew': 'library', 'arabic': 'override', 'latin': 'library'})
        self.assertTrue(T.script('arabic')['spacing']['connected'])

    def test_a_connected_script_with_letter_spacing_fails(self):
        with self.assertRaises(T.ScriptError) as caught:
            T._check_spacing('arabic', {**self.OVERRIDE, 'letter_spacing': '-0.01em'})
        self.assertIn('letters connect', str(caught.exception))

    def test_a_connected_script_on_the_librarys_own_css_fails(self):
        with self.assertRaises(T.ScriptError):
            T._check_spacing('arabic', {'mode': 'library', 'connected': True})

    def test_a_malformed_spacing_fails(self):
        for bad in ({'mode': 'library'}, {'mode': 'tight', 'connected': False}, {'mode': 'library', 'connected': False, 'x': 1},
                    {**self.OVERRIDE, 'body_line_height': 0.9}, {**self.OVERRIDE, 'word_spacing': 'wide'},
                    {k: v for k, v in self.OVERRIDE.items() if k != 'heading_line_height'}):
            with self.subTest(bad), self.assertRaises(T.ScriptError):
                T._check_spacing('x', bad)

    def test_a_valid_override_passes(self):
        T._check_spacing('arabic', self.OVERRIDE)
        T._check_spacing('hebrew', {'mode': 'library', 'connected': False})


def chromium():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            path = p.chromium.executable_path
        return path if path and os.path.exists(path) else None
    except Exception:  # pragma: no cover
        return None


@unittest.skipUnless(chromium(), 'the browser check needs a local Chromium (playwright)')
class InABrowser(unittest.TestCase):
    """What a visitor's browser computes: the direction, the fonts asked for, no letter-spacing on an Arabic heading
    (the library tracks Hebrew headings tighter than normal), and a taller line on it."""

    PROBE = """() => {
      const cs = (el) => getComputedStyle(el);
      const h1 = document.querySelector('h1'), body = document.body;
      return {direction: cs(document.documentElement).direction, lang: document.documentElement.lang,
              h1_letter_spacing: cs(h1).letterSpacing, h1_font_size: parseFloat(cs(h1).fontSize),
              h1_line_height: parseFloat(cs(h1).lineHeight), body_font: cs(body).fontFamily,
              h1_font: cs(h1).fontFamily, body_line_height: parseFloat(cs(body).lineHeight),
              body_font_size: parseFloat(cs(body).fontSize),
              overflow_x: document.documentElement.scrollWidth - document.documentElement.clientWidth};
    }"""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(args=['--no-sandbox'])
        cls.measured = {}
        for name, html in (('arabic', L.page(arabic_content(), contract(arabic_pair()))[0]),
                           ('hebrew', L.page(D.CONTENT, contract(hebrew_pair()))[0])):
            page = cls.browser.new_page(viewport={'width': 390, 'height': 844})
            page.route('**/*', lambda route: route.abort() if route.request.url.startswith('http') else route.continue_())
            page.set_content(html)
            cls.measured[name] = page.evaluate(cls.PROBE)
            page.close()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def test_the_arabic_page_is_computed_right_to_left_with_the_arabic_fonts_first(self):
        m = self.measured['arabic']
        self.assertEqual((m['direction'], m['lang']), ('rtl', 'ar'))
        pair = arabic_pair()
        self.assertTrue(m['body_font'].startswith(f'"{pair["body"]["family"]}"') or pair['body']['family'] in m['body_font'], m)
        self.assertIn(pair['display']['family'], m['h1_font'])

    def test_an_arabic_heading_has_no_letter_spacing_and_a_taller_line_than_a_hebrew_one(self):
        ar, he = self.measured['arabic'], self.measured['hebrew']
        self.assertIn(ar['h1_letter_spacing'], ('normal', '0px'))
        self.assertNotIn(he['h1_letter_spacing'], ('normal', '0px'))               # Hebrew: the library's own tracking
        self.assertGreaterEqual(ar['h1_line_height'] / ar['h1_font_size'], 1.39)
        self.assertGreaterEqual(ar['body_line_height'] / ar['body_font_size'], 1.84)

    def test_neither_page_overflows_a_phone(self):
        self.assertEqual((self.measured['arabic']['overflow_x'], self.measured['hebrew']['overflow_x']), (0, 0))


if __name__ == '__main__':
    unittest.main()
