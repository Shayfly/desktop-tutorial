"""Warehouse 126 (a library of font pairs) and 129 (the script layer), on the real path: the registry and the library
(omni_prod/typography), the design contract (g_apple.contract.build), the section library's page, the content route's
decision on the owner's law-firm brief -- a production row read read-only (tests/fixtures/site_content_bld_b0eb47a5.json,
its sha256 asserted here as in test_site_content_render.py) -- the platform's render of that brief, and the G-APPLE
gate's install. That every pair really loads in a browser is tests/test_font_pairs_load.py.

What is NOT met here, said rather than implied: an Arabic brief does not reach the content route (site_content.decide
says 'not_hebrew', and the section library writes its own words in Hebrew), so 129.1 holds for the script layer, not
for a built Arabic page."""
import copy
import datetime
import hashlib
import json
import os
import re
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omni_prod import site_content as SC
from omni_prod import skill_units as U
from omni_prod import typography as T
from omni_prod import vertical_palettes as VP
from omni_prod.g_apple import contract as C
from omni_prod.g_apple import static
from omni_prod.section_library import DIRECTIONS
from omni_prod.section_library import demo_law_firm as D
from omni_prod.section_library import page
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import render as R

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))
PROMPT = FIXTURE['prompt']
OWNER = {'user_id': 'usr_owner_test'}
FOUR_COLOURS = PROMPT.replace('palette #1e3a5f, #ffffff;', 'palette #1e3a5f, #b45309, #f8fafc, #0f172a;')
ARABIC = ('أريد موقعا لمطعمي "بيت الزيتون" في الناصرة، الهاتف 04-6012345.\n--- Approved project brief (binding; '
          'fingerprint 0123456789abcdef) ---\nSign-in: NONE. Do not add login.\nDo not store personal or contact '
          'details of people.\nProduct kind: CONTENT-ONLY website.')
UNSUPPORTED = {'cyrillic': 'Привет, нам нужен сайт для пекарни', 'greek': 'Καλημέρα, θέλουμε ιστοσελίδα',
               'cjk': '你好，我们需要一个网站', 'indic': 'नमस्ते, हमें एक वेबसाइट चाहिए', 'thai': 'สวัสดีครับ เราต้องการเว็บไซต์'}


def decide(prompt=PROMPT):
    with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
        return SC.decide(prompt, OWNER, year='2026')


def demo_contract(fonts=None):
    return C.build(D.BRIEF_DESIGN, fonts)


class TheProductionRow(unittest.TestCase):
    def test_the_fixture_is_the_production_prompt(self):
        self.assertEqual(hashlib.sha256(PROMPT.encode('utf-8')).hexdigest(),
                         '41d10d6333900cf116de9da2e3ed38cffb58398fad8143132b4cab1d1eb5db61')


# ---- 129: the script layer ----------------------------------------------------------------------------------------------
class TheScriptRegistry(unittest.TestCase):
    def test_hebrew_and_arabic_pages_are_right_to_left_and_latin_left_to_right(self):
        self.assertEqual({n: T.script(n)['direction'] for n in ('hebrew', 'arabic', 'latin')},
                         {'hebrew': 'rtl', 'arabic': 'rtl', 'latin': 'ltr'})
        self.assertEqual(T.html_attrs('hebrew'), 'lang="he" dir="rtl"')
        self.assertEqual(T.html_attrs('arabic'), 'lang="ar" dir="rtl"')
        self.assertEqual(T.html_attrs('latin'), 'lang="en" dir="ltr"')

    def test_the_script_follows_the_customers_letters(self):
        self.assertEqual(T.detect_script('אני רוצה אתר למשרד שלי, Cohen & Co, office@cohen-law.co.il'), 'hebrew')
        self.assertEqual(T.detect_script('أريد موقعا لمطعمي في الناصرة'), 'arabic')
        self.assertEqual(T.detect_script(Fx.request_text(ARABIC)), 'arabic')
        self.assertEqual(T.detect_script('A website for my bakery in Haifa'), 'latin')
        self.assertEqual((T.script_for_language('he'), T.script_for_language('ar')), ('hebrew', 'arabic'))

    def test_a_declared_script_without_support_raises_and_never_falls_back_to_latin(self):
        for name, text in UNSUPPORTED.items():
            with self.subTest(script=name):
                with self.assertRaises(T.UnsupportedScript):
                    T.detect_script(text)
                with self.assertRaises(T.UnsupportedScript):
                    T.script(name)
                with self.assertRaises(T.UnsupportedScript):
                    T.html_attrs(name)
                with self.assertRaises(T.UnsupportedScript):
                    T.pair_for(name, category='bakeries', tone='warm', business='x')
                with self.assertRaises(T.UnsupportedScript):
                    T.format_date(name, datetime.date(2026, 11, 5))

    def test_an_unknown_script_or_language_or_text_raises(self):
        with self.assertRaises(T.UnknownScript):
            T.script('klingon')
        with self.assertRaises(T.UnknownScript):
            T.script_for_language('xx')
        with self.assertRaises(T.UnknownScript):
            T.detect_script('ქართული ენა')                 # Georgian: declared by no script
        with self.assertRaises(T.ScriptError):
            T.detect_script('050-1234567 !!')              # no letters
        with self.assertRaises(T.ScriptError):
            T.detect_script('ab שש')                       # as much Latin as Hebrew

    def test_the_registry_is_checked_when_it_is_loaded(self):
        broken = copy.deepcopy(T.DECLARED)
        broken['arabic']['direction'] = 'right'
        with mock.patch.object(T, 'DECLARED', broken), self.assertRaises(T.ScriptError):
            T._check()
        broken = copy.deepcopy(T.DECLARED)
        broken['hebrew']['date'] = 'DD/MM'
        with mock.patch.object(T, 'DECLARED', broken), self.assertRaises(T.ScriptError):
            T._check()
        broken = copy.deepcopy(T.DECLARED)
        broken['cyrillic']['lang'] = 'ru'                  # an unsupported script carries no formats
        with mock.patch.object(T, 'DECLARED', broken), self.assertRaises(T.ScriptError):
            T._check()


class TheFormats(unittest.TestCase):
    def test_a_hebrew_and_an_arabic_date_are_day_month_year(self):
        day = datetime.date(2026, 11, 5)
        self.assertEqual(T.format_date('hebrew', day), '05/11/2026')
        self.assertEqual(T.format_date('arabic', day), '05/11/2026')
        self.assertEqual(T.format_date('latin', day), '2026-11-05')

    def test_money_is_written_where_the_script_puts_its_symbol(self):
        self.assertEqual(T.format_money('hebrew', 1250, 'ILS'), '1,250 ₪')
        self.assertEqual(T.format_money('arabic', 250, 'ILS'), '250 ₪')
        self.assertEqual(T.format_money('arabic', 250, 'SAR'), '250 ر.س')
        self.assertEqual(T.format_money('latin', Decimal('19.9'), 'USD', 2), '$19.90')
        with self.assertRaises(T.ScriptError):
            T.format_money('hebrew', 250, 'SAR')           # a currency the script does not list: no default
        with self.assertRaises(TypeError):
            T.format_money('hebrew', 19.9, 'ILS')          # money is never a float

    def test_numbers_carry_the_scripts_marks(self):
        self.assertEqual(T.format_number('hebrew', 1234567), '1,234,567')
        self.assertEqual(T.format_number('arabic', Decimal('-1234.565'), 2), '-1,234.57')


# ---- 126: the font-pair library -------------------------------------------------------------------------------------------
class TheFontPairLibrary(unittest.TestCase):
    def test_a_range_of_pairs_per_script_with_the_contracts_two_weights_for_every_tone(self):
        # the owner, 2026-11-25 ("את כל המגוון"): at least three pairs for every tone of every script (it was two)
        self.assertEqual(set(T.TONES), set(DIRECTIONS['directions']))
        self.assertGreaterEqual(T.MIN_PAIRS_PER_TONE, 3)
        for name in ('hebrew', 'arabic', 'latin'):
            pairs = T.pairs(name)
            for p in pairs:
                self.assertEqual(p['body']['weights'], [400, 700], p['id'])
                self.assertIn(p['display']['weights'], ([400, 700], [400]), p['id'])
            for tone in T.TONES:
                self.assertGreaterEqual(len([p for p in pairs if tone in p['tones']]), T.MIN_PAIRS_PER_TONE, (name, tone))

    def test_hebrew_and_arabic_pages_never_share_a_font(self):
        self.assertEqual(T.families('hebrew') & T.families('arabic'), set())
        self.assertEqual(T.families('hebrew') & T.families('latin'), set())

    def test_an_arabic_business_gets_an_arabic_pair(self):
        for tone in T.TONES:
            for i in range(8):
                p = T.pair_for('arabic', category='restaurants', tone=tone, business=f'مطعم {i}')
                faces = {p['display']['family'], p['body']['family']}
                self.assertEqual(p['script'], 'arabic')
                self.assertLessEqual(faces, T.families('arabic'))
                self.assertEqual(faces & T.families('hebrew'), set())

    def test_the_same_business_always_gets_the_same_pair(self):
        first = T.pair_for('hebrew', category='lawyers', tone='formal', business='כהן ושות׳')
        for key in ('כהן ושות׳', ' כהן   ושות׳ ', 'כהן ושות׳'):
            self.assertEqual(T.pair_for('hebrew', category='lawyers', tone='formal', business=key)['id'], first['id'])
        self.assertEqual(T.pair_for('latin', category='lawyers', tone='formal', business='Cohen & Co')['id'],
                         T.pair_for('latin', category='lawyers', tone='formal', business='COHEN  & co')['id'])

    def test_two_businesses_in_one_category_get_different_pairs(self):
        a = T.pair_for('hebrew', category='lawyers', tone='formal', business='כהן ושות׳ – דיני עבודה')
        b = T.pair_for('hebrew', category='lawyers', tone='formal', business='לוי ושות׳ – דיני עבודה')
        self.assertNotEqual(a['id'], b['id'])
        # in every category, the business decides between the tone's pairs: thirty businesses use every one of them
        for category in sorted(VP.load()['categories']):
            tone = DIRECTIONS['palettes'][VP.palette_for(category)[0]]['direction']
            for name in ('hebrew', 'arabic'):
                used = {T.pair_for(name, category=category, tone=tone, business=f'עסק {i}')['id'] for i in range(30)}
                self.assertEqual(used, {p['id'] for p in T.pairs(name) if tone in p['tones']}, (category, name))

    def test_a_pair_needs_a_business_a_category_and_a_known_tone(self):
        for kw in ({'business': ''}, {'business': '   '}, {'category': ''}, {'tone': 'playful'}):
            args = {'category': 'lawyers', 'tone': 'formal', 'business': 'כהן', **kw}
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                T.pair_for('hebrew', **args)

    def test_a_font_not_in_the_library_fails(self):
        for stack, script in (("'Arial', sans-serif", 'hebrew'), ("'Cairo', system-ui, sans-serif", 'hebrew'),
                              ("'Heebo', sans-serif", 'arabic'), ('Comic Sans MS, cursive', 'hebrew'), ('', 'hebrew')):
            with self.subTest(stack=stack), self.assertRaises(T.FontNotInLibrary):
                T.check_stack(stack, script)
        T.check_stack("'Heebo', system-ui, sans-serif", 'hebrew')
        T.check_stack('system-ui, sans-serif', 'hebrew')            # a system stack loads nothing
        with self.assertRaises(T.FontNotInLibrary):
            T.pair('he-comic-sans')
        # the page refuses a contract that names a font outside the library
        outside = D.BRIEF_DESIGN.replace("font 'Heebo', system-ui", "font 'Open Sans', system-ui")
        with self.assertRaises(T.FontNotInLibrary):
            page(copy.deepcopy(D.CONTENT), C.build(outside))
        # and a contract whose pair is not the library's, or whose tokens are not its pair's
        locked = demo_contract(T.contract_fonts(T.pair('he-frank-heebo')))
        forged = copy.deepcopy(locked)
        forged['fonts']['pair'] = 'he-invented'
        with self.assertRaises(T.FontNotInLibrary):
            page(copy.deepcopy(D.CONTENT), forged)
        forged = copy.deepcopy(locked)
        forged['tokens']['--font-display'] = "'David Libre', serif"
        with self.assertRaises(T.FontNotInLibrary):
            page(copy.deepcopy(D.CONTENT), forged)

    def test_the_library_is_checked_when_it_is_loaded(self):
        shared = copy.deepcopy(T._LIBRARY)
        shared['pairs']['arabic'][0]['display']['family'] = 'Frank Ruhl Libre'    # an Arabic pair with a Hebrew font
        with mock.patch.object(T, '_LIBRARY', shared), self.assertRaises(T.FontNotInLibrary):
            T._check()
        one = copy.deepcopy(T._LIBRARY)
        formal = [p for p in one['pairs']['hebrew'] if 'formal' in p['tones']]
        for p in formal[T.MIN_PAIRS_PER_TONE - 1:]:                                 # 'formal' left one pair short
            p['tones'] = [t for t in p['tones'] if t != 'formal'] or ['warm']
        with mock.patch.object(T, '_LIBRARY', one), self.assertRaises(T.FontNotInLibrary):
            T._check()
        third = copy.deepcopy(T._LIBRARY)
        third['pairs']['latin'][0]['body']['weights'] = [300, 400, 700]
        with mock.patch.object(T, '_LIBRARY', third), self.assertRaises(T.FontNotInLibrary):
            T._check()


# ---- the contract and the page --------------------------------------------------------------------------------------------
class TheContract(unittest.TestCase):
    def test_without_a_pair_the_contract_is_what_it_was(self):
        plain = demo_contract()
        self.assertNotIn('fonts', plain)
        self.assertEqual((plain['tokens']['--font-family'], plain['tokens']['--font-display']),
                         ("'Heebo', system-ui, sans-serif", "'Frank Ruhl Libre', serif"))
        self.assertEqual(plain, C.build(D.BRIEF_DESIGN, None))

    def test_a_locked_pair_is_in_the_tokens_and_the_fingerprint(self):
        a = demo_contract(T.contract_fonts(T.pair('he-david-assistant')))
        b = demo_contract(T.contract_fonts(T.pair('he-secular-heebo')))
        self.assertNotEqual(a['fingerprint'], b['fingerprint'])
        self.assertEqual({k: v for k, v in a['tokens'].items() if not k.startswith('--font-')},
                         {k: v for k, v in demo_contract()['tokens'].items() if not k.startswith('--font-')})
        self.assertEqual(a['fonts'], {'pair': 'he-david-assistant', 'script': 'hebrew',
                                      'brief_font': "'Heebo', system-ui, sans-serif"})
        self.assertEqual((a['tokens']['--font-family'], a['tokens']['--font-display']),
                         ("'Assistant', system-ui, sans-serif", "'David Libre', serif"))
        with self.assertRaises(C.ContractError):
            demo_contract({'pair': 'he-david-assistant', 'body': "'Assistant', sans-serif"})


class ThePage(unittest.TestCase):
    def test_a_locked_pair_loads_exactly_its_faces_and_the_page_follows_its_script(self):
        for pair_id, regular in (('he-frank-heebo', False), ('he-secular-heebo', True)):
            with self.subTest(pair=pair_id):
                contract = demo_contract(T.contract_fonts(T.pair(pair_id)))
                doc, _ = page(copy.deepcopy(D.CONTENT), contract)
                links = re.findall(r'<link rel="stylesheet" href="([^"]+)"', doc)
                p = T.pair(pair_id)
                expected = (f"https://fonts.googleapis.com/css2?family={p['body']['family'].replace(' ', '+')}:wght@400;700"
                            f"&family={p['display']['family'].replace(' ', '+')}:wght@"
                            + ';'.join(map(str, p['display']['weights'])) + '&display=swap')
                self.assertEqual(links, [expected])
                self.assertIn('<html lang="he" dir="rtl">', doc)
                self.assertIn('<meta property="og:locale" content="he_IL">', doc)
                self.assertIn(f"--font-display: {T.stack(p['display'])};", doc)
                self.assertEqual('data-display-weight=regular' in doc, regular)
                self.assertEqual(static.check(doc, contract), [])
                for unit in ('rights_font_source', 'perf_font_display', 'perf_font_preconnect'):
                    self.assertEqual(U.run(unit, doc), {'status': 'pass'}, unit)

    def test_a_heading_longer_than_the_scripts_limit_fails_loudly(self):
        limit = T.script('hebrew')['heading_max_chars']
        content = copy.deepcopy(D.CONTENT)
        content['hero']['title'] = 'א' * limit['h1']
        page(content, demo_contract())                              # at the limit: rendered
        content['hero']['title'] = 'א' * (limit['h1'] + 1)
        with self.assertRaises(T.HeadingTooLong) as caught:
            page(content, demo_contract())
        self.assertIn(f"h1 of {limit['h1'] + 1} characters, the hebrew limit is {limit['h1']}", str(caught.exception))
        content = copy.deepcopy(D.CONTENT)
        content['services']['items'][0] = ('ב' * (limit['h3'] + 1), content['services']['items'][0][1])
        with self.assertRaises(T.HeadingTooLong) as caught:
            page(content, demo_contract())
        self.assertIn('h3 of', str(caught.exception))

    def test_a_heading_is_measured_as_the_visitor_reads_it(self):
        T.check_headings('<h2 class="title">' + 'א' * 66 + ' <bdi dir="ltr">&amp;</bdi> x</h2>', 'hebrew')  # 70
        with self.assertRaises(T.HeadingTooLong):
            T.check_headings('<h2>' + 'א' * 67 + ' &amp; x</h2>', 'hebrew')                             # 71
        with self.assertRaises(T.HeadingTooLong):
            T.check_headings('<h5>קצר</h5>', 'hebrew')            # a level the script sets no limit for
        with self.assertRaises(T.HeadingTooLong):
            T.check_headings('<h1>' + 'ب' * 61 + '</h1>', 'arabic')

    def test_a_page_for_another_script_is_refused_not_rendered_with_hebrew_around_it(self):
        contract = demo_contract(T.contract_fonts(T.pair('ar-amiri-plex')))
        with self.assertRaises(T.UnsupportedScript):
            page(copy.deepcopy(D.CONTENT), contract)


# ---- the content route ------------------------------------------------------------------------------------------------
class TheRoute(unittest.TestCase):
    def test_the_owners_brief_gets_a_pair_from_the_library(self):
        route = decide()
        self.assertEqual((route.route, route.category, route.direction, route.script),
                         ('section_library', 'lawyers', 'formal', 'hebrew'))
        p = T.pair(route.font_pair)
        self.assertIn(p['id'], {q['id'] for q in T.pairs('hebrew') if 'formal' in q['tones']})
        self.assertEqual(p, T.pair_for('hebrew', category='lawyers', tone='formal', business='כהן ושות׳ – דיני עבודה'))
        self.assertEqual((route.contract['tokens']['--font-family'], route.contract['tokens']['--font-display']),
                         (T.stack(p['body']), T.stack(p['display'])))
        self.assertEqual(route.contract['fonts'], {'pair': p['id'], 'script': 'hebrew',
                                                   'brief_font': "'Heebo', system-ui, sans-serif"})
        said = route.to_dict()
        self.assertEqual((said['script'], said['font_pair'], said['fonts']), ('hebrew', p['id'], route.contract['fonts']))

    def test_the_rendered_page_carries_the_pair(self):
        route = decide()
        doc, _ = R.render(FIXTURE['scripted_content'], Fx.fact_sheet(PROMPT), route.contract, expect_fp=route.contract_fp,
                          direction=route.direction, year='2026', outline_titles=route.outline_titles,
                          order=route.order, windows=route.windows)
        p = T.pair(route.font_pair)
        self.assertIn(T.font_link(p), doc)
        self.assertEqual(len(re.findall(r'fonts\.googleapis\.com/css2', doc)), 1)
        self.assertIn('<html lang="he" dir="rtl">', doc)
        self.assertIn(route.contract['css'], doc)
        self.assertNotIn('family=Heebo:wght@400;700&display=swap', doc)       # the brief's one font is not loaded alone
        self.assertEqual(static.check(doc, route.contract), [])

    def test_two_businesses_in_one_category_get_different_pairs_on_the_route(self):
        cohen, levi = decide(), decide(PROMPT.replace('כהן ושות׳', 'לוי ושות׳'))
        self.assertEqual((cohen.route, levi.route, cohen.category, levi.category),
                         ('section_library', 'section_library', 'lawyers', 'lawyers'))
        self.assertNotEqual(cohen.font_pair, levi.font_pair)
        self.assertEqual(decide().font_pair, cohen.font_pair)

    def test_an_arabic_brief_is_the_arabic_script_but_stays_on_the_legacy_path_by_name(self):
        self.assertEqual(T.detect_script(Fx.request_text(ARABIC)), 'arabic')
        route = decide(ARABIC)
        self.assertEqual((route.route, route.reason, route.script, route.font_pair), ('legacy', 'not_hebrew', None, None))

    def test_the_gate_holds_the_contract_the_page_is_rendered_with(self):
        from omni_prod import g_apple
        route = decide(FOUR_COLOURS)
        self.assertEqual((route.route, route.contract_source), ('section_library', 'brief'))
        with mock.patch.dict(os.environ, {'OMNI_GATE_APPLE': 'warn'}):
            core = SimpleNamespace(site_route=route, executor=SimpleNamespace())
            g_apple.install(core, prompt=FOUR_COLOURS)
            self.assertIs(core.design_contract, route.contract)
            self.assertEqual(core.design_contract['fonts']['pair'], route.font_pair)
            off_route = SimpleNamespace(executor=SimpleNamespace())
            g_apple.install(off_route, prompt=FOUR_COLOURS)
            self.assertEqual(off_route.design_contract, C.build(FOUR_COLOURS))          # no route: the brief's own
            two_colours = SimpleNamespace(site_route=decide(), executor=SimpleNamespace())
            g_apple.install(two_colours, prompt=PROMPT)
            self.assertIsNone(two_colours.design_contract)                              # NOT_RUN, as before
            forged = copy.deepcopy(route)
            forged.contract = copy.deepcopy(route.contract)
            forged.contract['tokens']['--color-primary'] = '#000000'
            with self.assertRaises(ValueError):
                g_apple.install(SimpleNamespace(site_route=forged, executor=SimpleNamespace()), prompt=FOUR_COLOURS)

    def test_the_schema_bounds_the_model_by_the_scripts_heading_limits(self):
        from omni_prod.site_content import schema as K
        limit = T.script('hebrew')['heading_max_chars']
        self.assertEqual((K.SECTIONS['hero']['title'].max, K.SECTIONS['services']['title'].max,
                          K.SECTIONS['cta']['title'].max, K.SECTIONS['services']['items'].item.fields['title'].max,
                          K.SECTIONS['pricelist']['groups'].item.fields['items'].item.fields['name'].max),
                         (limit['h1'], limit['h2'], limit['h2'], limit['h3'], limit['h4']))


if __name__ == '__main__':
    unittest.main()
