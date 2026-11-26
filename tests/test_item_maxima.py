"""How many items a section holds is not money (the owner, 2026-11-26, WAREHOUSE 136 option a): the content route's
maxima were raised so a real business fits; the minimums and the heading lengths (a layout rule the correction fixes)
stay. Then the one thing a longer page changes: it may run past the 45,000 characters the preview smoke returns, and a
page cut mid-fact must not read as an invented fact -- the route judges a long page up to its last complete section.

The real validator (validate._fields, the function validate() runs on every offered section), the real section
library, the real truth gate (skills_runtime._invented_contact), the real PreviewReadyExecutor.check with only the
sandbox transport scripted. The layout at the maxima is proven in a real browser in tests/test_section_library.py
(ItemMaxima). The brief is the owner's production row (bld_b0eb47a5, read only)."""
import copy
import json
import unittest

from tests.test_site_content_engine import CONTENT, PROMPT

from omni_prod import section_library as L
from omni_prod.fact_canon import build_canon
from omni_prod.preview_smoke import SERVED_CUT, PreviewReadyExecutor, served_cut
from omni_prod.section_library import demo_law_firm as D
from omni_prod.site_content import schema as K
from omni_prod.site_content import validate as V
from omni_prod.skills_runtime import _invented_contact

NEW = {('stats', 'items'): 6, ('services', 'items'): 24, ('about', 'paragraphs'): 6, ('about', 'facts'): 12,
       ('process', 'steps'): 12, ('faq', 'items'): 24, ('testimonials', 'items'): 12, ('pricelist', 'groups'): 12,
       ('pricelist', 'groups.items'): 30, ('contact', 'topics'): 12}
MINIMA = {('stats', 'items'): 2, ('services', 'items'): 2, ('about', 'paragraphs'): 1, ('about', 'facts'): 1,
          ('process', 'steps'): 2, ('faq', 'items'): 2, ('testimonials', 'items'): 1, ('pricelist', 'groups'): 1,
          ('pricelist', 'groups.items'): 1, ('contact', 'topics'): 2}
ITEM = {('stats', 'items'): {'value': '2008', 'label': 'פעילים מאז'},
        ('services', 'items'): {'title': 'פיטורים שלא כדין', 'desc': 'בדיקת ההליך שקדם לפיטורים.'},
        ('about', 'paragraphs'): 'משרד עורכי דין בתל אביב שעוסק בדיני עבודה.',
        ('about', 'facts'): {'label': 'מייצגים', 'value': 'עובדים ומעסיקים'},
        ('process', 'steps'): {'title': 'שיחת ייעוץ', 'desc': 'מספרים לנו מה קרה.'},
        ('faq', 'items'): {'q': 'כמה זמן לוקח הליך?', 'a': 'משך ההליך תלוי בסוג התיק.'},
        ('testimonials', 'items'): '@review:1', ('contact', 'topics'): 'פיטורים שלא כדין'}
SECTION = {'stats': {'items': []}, 'services': {'title': 'תחומי התמחות', 'items': []},
           'about': {'title': 'על המשרד', 'paragraphs': ['פסקה אחת.']},
           'process': {'title': 'איך זה עובד', 'steps': []}, 'faq': {'title': 'שאלות נפוצות', 'items': []},
           'testimonials': {'title': 'המלצות', 'items': []}, 'pricelist': {'title': 'מחירון', 'groups': []},
           'contact': {'title': 'צור קשר', 'topics': []}}
PRICE_ITEM = {'name': 'ייעוץ ראשון', 'price': '@price:1'}


def section_with(key, field, n):
    s = copy.deepcopy(SECTION[key])
    if (key, field) == ('pricelist', 'groups'):
        s['groups'] = [{'title': 'ייעוץ', 'items': [PRICE_ITEM]} for _ in range(n)]
    elif (key, field) == ('pricelist', 'groups.items'):
        s['groups'] = [{'title': 'ייעוץ', 'items': [PRICE_ITEM] * n}]
    else:
        s[field] = [copy.deepcopy(ITEM[(key, field)]) for _ in range(n)]
    return s


def shape_codes(key, section):
    out = []
    V._fields(section, K.spec_for(key, {}), f'sections.{key}', out)
    return {(p.path, p.code, p.why) for p in out}


def path_of(key, field):
    return f'sections.{key}.groups[0].items' if field == 'groups.items' else f'sections.{key}.{field}'


class TheMaxima(unittest.TestCase):
    def test_the_new_maxima_and_the_old_ones_are_side_by_side(self):
        self.assertEqual({k: new for k, (_, new) in K.ITEM_MAXIMA_2026_11_26.items()}, NEW)
        self.assertEqual(K.ITEM_MAXIMA_2026_11_26[('services', 'items')], (8, 24))
        self.assertEqual(K.ITEM_MAXIMA_2026_11_26[('pricelist', 'groups.items')], (12, 30))

    def test_a_list_at_its_new_maximum_passes_and_one_more_is_too_many(self):
        for (key, field), most in NEW.items():
            with self.subTest(f'{key}.{field}'):
                at = shape_codes(key, section_with(key, field, most))
                self.assertFalse([c for c in at if c[1] in ('TOO_MANY', 'TOO_FEW')], at)
                over = shape_codes(key, section_with(key, field, most + 1))
                self.assertIn((path_of(key, field), 'TOO_MANY', f'{most + 1} items; at most {most}'), over)

    def test_the_minimums_are_unchanged(self):
        for (key, field), least in MINIMA.items():
            if least < 1:
                continue
            with self.subTest(f'{key}.{field}'):
                under = shape_codes(key, section_with(key, field, least - 1))
                self.assertIn((path_of(key, field), 'TOO_FEW', f'{least - 1} item(s); at least {least}'), under)

    def test_a_heading_longer_than_its_script_allows_is_still_refused(self):
        s = section_with('services', 'items', 3)
        s['items'][0]['title'] = 'א' * (K._H['h3'] + 1)
        self.assertIn(('sections.services.items[0].title', 'TOO_LONG', f"{K._H['h3'] + 1} characters; at most "
                       f"{K._H['h3']}"), shape_codes('services', s))

    def test_the_model_is_told_the_new_bounds(self):
        offered = {k: 'required' for k in ('hero', 'services', 'faq', 'process', 'pricelist', 'contact')}
        model = K.schema_for_model(offered, {}, name_given=True, layouts=L.LAYOUTS)['sections']
        self.assertEqual(model['services']['items']['list'], '2 to 24 items')
        self.assertEqual(model['faq']['items']['list'], '2 to 24 items')
        self.assertEqual(model['process']['steps']['list'], '2 to 12 items')
        self.assertEqual(model['pricelist']['groups']['list'], '1 to 12 items')
        self.assertEqual(model['pricelist']['groups']['item']['items']['list'], '1 to 30 items')

    def test_the_owners_brief_at_24_services_validates_end_to_end(self):
        from omni_prod.site_content import facts as Fx
        sheet = Fx.fact_sheet(PROMPT)
        offered, _ = K.offered_sections(sheet, {'sections': ['hero', 'services', 'about', 'process', 'faq', 'contact']},
                                        None, {})
        doc = copy.deepcopy(CONTENT)
        doc['sections']['services']['items'] = (doc['sections']['services']['items'] * 24)[:24]
        problems = V.validate(doc, sheet, offered, {}, claim_mode='warn')
        self.assertFalse([p for p in problems if p.path.startswith('sections.services.items') and p.code == 'TOO_MANY'])
        doc['sections']['services']['items'].append(doc['sections']['services']['items'][0])
        problems = V.validate(doc, sheet, offered, {}, claim_mode='warn')
        self.assertIn(('sections.services.items', 'TOO_MANY'), {(p.path, p.code) for p in problems})


def long_page_cut_inside_the_footer_address():
    """The owner's law-firm page, padded in its head so that character 45,000 falls inside the footer's address, right
    after the first digit of its number ("דרך מנחם בגין 1" of "דרך מנחם בגין 132"): the case the 45,000 cut produced on
    a long page (scan of 2026-11-26: "רחוב הנביאים 1" read as an invented address)."""
    page = L.page(D.CONTENT, D.build()[1])[0]
    address = D.CONTENT['address']
    keep = address.index('132') + 1
    at = page.rfind(address)                                   # the footer's copy, after every section
    pad = SERVED_CUT - (at + keep)
    assert pad > 7, pad
    padded = page.replace('</head>', '<!--' + ' ' * (pad - 7) + '--></head>', 1)
    assert padded[SERVED_CUT - keep:SERVED_CUT] == address[:keep] and len(padded) > SERVED_CUT
    return padded


class TheServedCut(unittest.TestCase):
    def test_a_page_cut_in_the_middle_of_a_fact_reads_as_an_invented_fact(self):
        page = long_page_cut_inside_the_footer_address()
        ctx = {'request': PROMPT, 'canon': build_canon(PROMPT)}
        raw = [f.problem for f in _invented_contact({}, {**ctx, 'rendered_pages': {'/': page[:SERVED_CUT]}})
               if f.severity == 'blocking']
        self.assertTrue(any('invented' in p for p in raw), raw)          # the failure the trim prevents
        trimmed = [f.problem for f in _invented_contact({}, {**ctx, 'rendered_pages': {'/': served_cut(page)}})
                   if f.severity == 'blocking']
        self.assertEqual(trimmed, [])
        self.assertTrue(served_cut(page).endswith('</section>'))
        self.assertIn(D.CONTENT['address'], served_cut(page))            # the hero panel's copy, whole

    def test_the_cut_keeps_a_short_page_whole_and_is_stable(self):
        page = L.page(D.CONTENT, D.build()[1])[0]
        self.assertLess(len(page), SERVED_CUT)
        self.assertEqual(served_cut(page), page)
        long = long_page_cut_inside_the_footer_address()
        self.assertEqual(served_cut(served_cut(long)), served_cut(long))
        # the smoke's capture of the long page trims the same way, told the served page's length
        self.assertEqual(served_cut(long[:SERVED_CUT], full_length=len(long)), served_cut(long))
        exact = long[:SERVED_CUT]                                          # review nit: exactly 45,000 is whole
        self.assertEqual(served_cut(exact), exact)
        self.assertEqual(served_cut(exact, full_length=SERVED_CUT), exact)
        no_sections = '<p>' + 'א' * (SERVED_CUT + 10) + '</p>'
        self.assertEqual(served_cut(no_sections), '')                      # nothing whole to judge before the tag
        tagged = '<div>' + '<p>שלום</p>' * 6000
        self.assertTrue(served_cut(tagged).endswith('</p>'), served_cut(tagged)[-20:])

    def test_the_prepass_reads_a_long_page_as_the_review_stage_will_never_a_fact_cut_in_half(self):
        from types import SimpleNamespace
        from tests.test_site_content_agents import ThePrepass
        from omni_prod.site_content import agents as A
        from omni_prod.site_content import render as R
        ThePrepass.setUpClass()
        case = ThePrepass()
        html = case.render()
        address = 'דרך מנחם בגין 132'
        at = html.rfind(address)                                # the footer's copy
        self.assertGreater(at, html.find('</section>'))

        def long_and_cut_in_the_address(repository):            # the served page, its 45,000th character in the address
            page = repository[R.PAGE]
            pad = SERVED_CUT - (page.rfind(address) + len('דרך מנחם בגין 1'))
            return {**repository, R.PAGE: page.replace('</head>', '<!--' + ' ' * (pad - 7) + '--></head>', 1)}
        found = A.prepass(SimpleNamespace(repository_transform=long_and_cut_in_the_address), case.route, html,
                          case.sheet)
        review = [f for f in found['block'] if f['acceptance_id'] == 'REVIEW']
        self.assertEqual(review, [])

    def test_parity_holds_for_a_long_page_and_still_finds_another_page(self):
        from types import SimpleNamespace
        from omni_prod.autonomous_core import ExecutionReport
        from omni_prod.site_content import agents as A
        from omni_prod.site_content import render as R
        long = long_page_cut_inside_the_footer_address()

        def parity(served, page):
            preview = object.__new__(PreviewReadyExecutor)
            preview.last_pages = {'/': served}

            class Inner:
                def __init__(self):
                    self._inner = preview

                def execute(self, *, repository, spec):
                    return ExecutionReport(True, (), 'ok', tests_executed=5)
            core = SimpleNamespace(site_report={})
            A.SiteParityExecutor(Inner(), core, 'block').execute(repository={R.PAGE: page}, spec=None)
            return core.site_report['parity']['status']
        self.assertEqual(parity(served_cut(long), long), 'pass')          # the trimmed capture of the whole page
        self.assertEqual(parity(long[:SERVED_CUT], long), 'pass')         # a capture the stage did not trim
        self.assertEqual(parity(served_cut(long).replace('נשמח', 'נשמע', 1), long), 'fail')

    def test_the_route_switches_the_trim_on_for_its_preview_stage_and_only_there(self):
        import os
        from unittest import mock
        from tests.test_site_content_agents import Passing, routed
        from tests.test_site_content_engine import ScriptedGateway
        from omni_prod import site_content
        preview = PreviewReadyExecutor(Passing())
        routed(ScriptedGateway(), executor=preview)
        self.assertEqual(preview.trim_cut, 'public/index.html')
        other = PreviewReadyExecutor(Passing())
        engine = type('E', (), {})()
        engine.executor = other
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'off'}):
            site_content.install(engine, prompt=PROMPT, gateway=None, request={'user_id': 'u'})
        self.assertIsNone(other.trim_cut)

    def test_the_preview_stage_hands_the_checks_the_trimmed_page(self):
        from tests.test_content_corrections import SequenceGateway, generate
        from omni_prod.autonomous_core import ExecutionReport
        _, files = generate(SequenceGateway([CONTENT]))
        repository = {f.path: f.content for f in files}
        page = long_page_cut_inside_the_footer_address()
        repository['public/index.html'] = page                      # the page the smoke served

        class Sandbox:
            def execute(self, *, repository, spec):
                return ExecutionReport(True, (), 'ok', tests_executed=1)

            def _run(self, staged, argv, label):          # the sandbox transport: what the smoke prints, cut at 45,000
                line = 'PREVIEW-PAGE ' + json.dumps({'/': page[:SERVED_CUT], 'assets': ''}, ensure_ascii=False)
                return {'returncode': 0, 'stdout': 'PREVIEW-SMOKE OK\n' + line, 'stderr': ''}
        for trim, expected in ((True, served_cut(page)), (False, page[:SERVED_CUT])):
            with self.subTest(trim=trim):
                preview = PreviewReadyExecutor(Sandbox())
                preview.trim_cut = 'public/index.html' if trim else None
                report = preview.execute(repository=repository, spec=None)
                self.assertTrue(report.passed)
                self.assertEqual(preview.last_pages['/'], expected)
                if trim:                                       # whole sections only, short of the cut
                    self.assertTrue(preview.last_pages['/'].endswith('</section>'))
                    self.assertLess(len(preview.last_pages['/']), SERVED_CUT)


class TheWholePageIsReviewedEveryRound(unittest.TestCase):
    """Review S7 (2026-11-26): the review stage reads a long page up to its last complete section; copy a repair round
    rewrote past it is read whole every round by the same truth gate, so coverage is never narrower than on main."""

    def run_parity(self, page):
        from types import SimpleNamespace
        from omni_prod.autonomous_core import ExecutionReport
        from omni_prod.site_content import agents as A
        from omni_prod.site_content import render as R
        preview = object.__new__(PreviewReadyExecutor)
        preview.last_pages = {'/': served_cut(page)}

        class Inner:
            def __init__(self):
                self._inner = preview

            def execute(self, *, repository, spec):
                return ExecutionReport(True, (), 'ok', tests_executed=5)
        core = SimpleNamespace(site_report={}, site_route=SimpleNamespace(prompt=PROMPT))
        report = A.SiteParityExecutor(Inner(), core, 'warn').execute(repository={R.PAGE: page}, spec=None)
        return report, core.site_report

    def test_an_invented_phone_past_the_cut_fails_the_round(self):
        page = long_page_cut_inside_the_footer_address()
        planted = page.replace('</footer>', '<p>התקשרו 04-8123456</p></footer>', 1)
        self.assertGreater(planted.index('04-8123456'), SERVED_CUT)
        report, site_report = self.run_parity(planted)
        self.assertFalse(report.passed)
        self.assertTrue(any(f.acceptance_id == 'REVIEW' and 'invented' in f.message for f in report.failures))
        self.assertEqual(report.tests_executed, 5)
        self.assertTrue(site_report['whole_page_review']['blocking'])

    def test_a_clean_long_page_passes_and_a_short_one_is_left_to_the_review(self):
        report, site_report = self.run_parity(long_page_cut_inside_the_footer_address())
        self.assertTrue(report.passed)
        self.assertEqual(site_report['whole_page_review']['blocking'], [])
        report, site_report = self.run_parity(L.page(D.CONTENT, D.build()[1])[0])
        self.assertTrue(report.passed)
        self.assertNotIn('whole_page_review', site_report)


if __name__ == '__main__':
    unittest.main()
