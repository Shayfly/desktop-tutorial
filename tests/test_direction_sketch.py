"""S6.3 slice 1: the direction sketch, pure (omni_prod/direction_sketch + section_library's `draft` keyword).

The sketch is the section library rendered from the build's own direction function on a DRAFT brief: no model, no cost.
All of this runs on the real functions: discovery (the brief), site_content.direction / decide, the font-pair library,
the G-APPLE design contract and section_library.page. Nothing is a double.

* parity: the direction a draft brief gets is the direction `decide()` takes for the same brief once approved;
* the page: the business name, the palette's colour, the pair's fonts, the menu, one block per section in the build's
  order, the draft ribbon; every placeholder it uses is listed;
* ready(): each of the nine conditions, by name; a flag value that is not off/accounts/on raises;
* a library page without `draft` is byte-identical to what it was (the demo page's sha256, taken on main)."""
import copy
import hashlib
import os
import re
import unittest
from unittest import mock

from omni_prod import direction_sketch as DS
from omni_prod import discovery as D
from omni_prod import section_library as L
from omni_prod import site_content as SC
from omni_prod import typography as T
from omni_prod.direction_sketch import render, structure
from omni_prod.section_library import demo_law_firm

ACCOUNT = 'usr_sketch_test'
SALON = 'אני רוצה אתר תדמית למספרה שלי בחיפה, קוראים לה "סטודיו נועה". טלפון 04-5551234'
SALON_NO_PHONE = 'אני רוצה אתר תדמית למספרה שלי בחיפה, קוראים לה "סטודיו נועה"'
PIZZA = 'אתר לפיצריה משפחתית ברמת גן בשם "פיצה רומא". טלפון 03-5551234'
ACCOUNTANT = 'אני רוצה אתר למשרד רואי חשבון "לוי ושות׳". טלפון 03-5557777'
FIXTURES = {'salon': SALON, 'pizza': PIZZA, 'accountant': ACCOUNTANT}
# sha256 of demo_law_firm.build()'s html, taken on origin/main a034c58 before the library gained `draft`
DEMO_SHA = '5fef8ccfee4adc591d3c6e685f56bb9829d20515fb58115223f486890a8d3097'


def on(**extra):
    return mock.patch.dict(os.environ, {'OMNI_DIRECTION_SKETCH': 'on', 'OMNI_SITE_LIBRARY': 'on', **extra})


def ready(text_or_brief, **kw):
    brief = D.start(text_or_brief) if isinstance(text_or_brief, str) else text_or_brief
    args = dict(account_id=ACCOUNT, has_version=False, has_open_build=False)
    args.update(kw)
    return DS.ready(brief, **args)


def approved(brief):
    """The same brief, completed as a customer would: a content-only site (what decide() requires)."""
    for field, value in (('content_only', 'yes'), ('personal_data', 'no'), ('login', 'none')):
        brief.fields[field] = {'value': value, 'source': 'answer', 'question_id': field, 'confidence': 'stated'}
    return brief


def sketch_of(text):
    with on():
        r = ready(text)
    assert r.ok, r.reason
    return r.direction


COPY = {'name': 'סטודיו נועה', 'tagline': 'מספרה בחיפה', 'description': 'מספרה בחיפה, סטודיו נועה.',
        'sections': {'hero': {'title': 'תספורת שמתאימה לכם', 'lead': 'מספרה בחיפה, עם תור שנוח לכם.',
                              'cta': 'לקביעת תור'},
                     'services': {'title': 'מה אנחנו עושים', 'nav': 'שירותים',
                                  'items': [{'title': 'תספורת', 'desc': 'תספורת לנשים ולגברים.'},
                                            {'title': 'צבע', 'desc': 'צבע לשיער.'}]}}}


class TheFlag(unittest.TestCase):
    def test_it_is_off_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_DIRECTION_SKETCH', None)
            self.assertEqual(DS.mode(), 'off')
            self.assertEqual((ready(SALON).ok, ready(SALON).reason), (False, 'flag_off'))

    def test_an_unknown_value_raises_and_never_reads_as_off(self):
        for value in ('yes', '1', 'true', 'owner'):
            with mock.patch.dict(os.environ, {'OMNI_DIRECTION_SKETCH': value}):
                with self.assertRaises(ValueError, msg=value):
                    DS.mode()
                with self.assertRaises(ValueError, msg=value):
                    ready(SALON)

    def test_accounts_reads_the_list_and_an_empty_list_raises(self):
        with mock.patch.dict(os.environ, {'OMNI_DIRECTION_SKETCH': 'accounts', 'OMNI_DIRECTION_SKETCH_ACCOUNTS': ''}):
            with self.assertRaises(ValueError):
                ready(SALON)
        env = {'OMNI_DIRECTION_SKETCH': 'accounts', 'OMNI_DIRECTION_SKETCH_ACCOUNTS': f'usr_other, {ACCOUNT}',
               'OMNI_SITE_LIBRARY': 'on'}
        with mock.patch.dict(os.environ, env):
            self.assertTrue(ready(SALON).ok)
            self.assertEqual(ready(SALON, account_id='usr_stranger').reason, 'account_not_listed')


class EveryReasonNamesItself(unittest.TestCase):
    def test_the_nine_conditions_in_order(self):
        def reason(text=SALON, *, sketch='on', library='on', design_line=True, **kw):
            with mock.patch.dict(os.environ, {'OMNI_DIRECTION_SKETCH': sketch, 'OMNI_SITE_LIBRARY': library,
                                              'OMNI_SITE_LIBRARY_ACCOUNTS': 'usr_somebody_else',
                                              'OMNI_DIRECTION_SKETCH_ACCOUNTS': ACCOUNT}):
                if design_line:
                    return ready(text, **kw).reason
                # a request whose brief carries no Design line (a brief always does; the build prompt of an older one might
                # not): the real prompt_of, with that one line taken out, as tests/test_site_content_route.py does
                real = DS.prompt_of
                with mock.patch.object(DS, 'prompt_of', lambda b: re.sub(r'(?m)^Design: .*\n?', '', real(b))):
                    return ready(text, **kw).reason
        english = 'I want a website for my law firm Cohen and Co. Phone 03-5551234.'
        stores = D.start(SALON)
        stores.fields['login'] = {'value': 'simple', 'source': 'answer', 'question_id': 'login', 'confidence': 'stated'}
        got = {
            'flag_off': reason(sketch='off'),
            'account_not_listed': reason(sketch='accounts', account_id='usr_stranger'),
            'library_route_off': reason(library='off'),
            'not_a_site': reason('אני רוצה אפליקציה לניהול מלאי עם התחברות ודוחות'),
            'not_hebrew': reason(english),
            'already_built': reason(has_version=True),
            'already_built (a build in flight)': reason(has_open_build=True),
            'no_name': reason('אני רוצה אתר למשרד רואי חשבון'),
            'no_subject': reason('אתר לחנות הקטנה שלי "אבי"'),
            'not_content_site': reason(stores),
            'no_design_contract': reason(SALON, design_line=False),
        }
        want = {k: k.split(' ')[0] for k in got}
        want['no_design_contract'] = 'no_design_contract'
        for case, said in got.items():
            with self.subTest(case=case):
                self.assertTrue(said == want[case] or (said or '').startswith(want[case] + ':'), said)

    def test_a_described_colour_is_the_builds_colour_too(self):
        # #551 (colour_roles): a colour description with no colour name no longer sends the site to the old path; the library
        # completes it. The sketch is ready, and its direction is exactly the one the build takes for the same brief approved.
        for word in ('כהה', 'כחול כהה', 'שחור וזהב'):
            with self.subTest(word=word):
                brief = D.start(SALON)
                brief.fields['color'] = {'value': word, 'source': 'answer', 'question_id': 'color', 'confidence': 'stated'}
                with on():
                    r = ready(brief)
                    route = SC.decide(D.build_prompt(approved(brief))[0], {'user_id': ACCOUNT}, year='2026')
                self.assertTrue(r.ok, r.reason)
                self.assertEqual(route.route, SC.ROUTE, route.reason)
                self.assertEqual(r.direction.contract['fingerprint'], route.contract_fp)
                self.assertEqual(r.direction.contract['tokens']['--color-primary'], route.contract['tokens']['--color-primary'])

    def test_a_customer_who_answered_the_colour_question_has_a_subject(self):
        brief = D.start('אתר לחנות הקטנה שלי "אבי". טלפון 03-5551234')
        with on():
            self.assertEqual(ready(brief).reason, 'no_subject')
            brief.fields['color'] = {'value': 'כחול', 'source': 'answer', 'question_id': 'color', 'confidence': 'stated'}
            self.assertTrue(ready(brief).ok, ready(brief).reason)

    def test_a_second_phone_is_not_ready_but_no_phone_at_all_is(self):
        with on():
            self.assertTrue(ready(SALON_NO_PHONE).ok)
            self.assertEqual(ready(SALON + ' טלפון נוסף: 04-8123456').reason, 'phone_not_one')


class TheSketchIsTheBuildsDirection(unittest.TestCase):
    def test_parity_with_decide_on_the_same_brief_approved(self):
        for name, text in FIXTURES.items():
            with self.subTest(fixture=name):
                brief = D.start(text)
                with on():
                    r = ready(brief)
                    self.assertTrue(r.ok, r.reason)
                    route = SC.decide(D.build_prompt(approved(brief))[0], {'user_id': ACCOUNT}, year='2026')
                self.assertEqual(route.route, SC.ROUTE, route.reason)
                d = r.direction
                self.assertEqual((d.palette, d.art_direction, d.pair, d.script),
                                 (route.palette, route.direction, route.font_pair, route.script))
                self.assertEqual(d.contract['fingerprint'], route.contract_fp)
                self.assertEqual(d.colours, SC.direction(D.build_prompt(brief)[0]).colours)
                self.assertEqual(route.order, None if route.order is None else [k for k in route.order if k in d.sections])
                expected = list(route.order) if route.order is not None else None
                if expected is not None:
                    self.assertEqual(d.sections[1:], [k for k in expected if k != 'hero'])

    def test_a_customer_named_colour_is_the_builds_colour(self):
        brief = D.start(SALON)
        brief.fields['color'] = {'value': 'כחול', 'source': 'answer', 'question_id': 'color', 'confidence': 'stated'}
        with on():
            r = ready(brief)
            route = SC.decide(D.build_prompt(approved(brief))[0], {'user_id': ACCOUNT}, year='2026')
        self.assertTrue(r.ok, r.reason)
        self.assertEqual(r.direction.contract['fingerprint'], route.contract_fp)
        self.assertEqual(r.direction.contract['tokens']['--color-primary'], route.contract['tokens']['--color-primary'])

    def test_the_sketch_asks_the_one_function_the_build_asks(self):
        calls = []
        real = SC.direction

        def spy(*a, **kw):
            calls.append(kw)
            return real(*a, **kw)
        with on(), mock.patch.object(SC, 'direction', spy):
            self.assertTrue(ready(SALON).ok)
        self.assertTrue(calls and all(kw.get('lang') == 'he' for kw in calls))


class ThePage(unittest.TestCase):
    def test_a_first_request_gives_a_page_in_its_own_colours_fonts_and_outline(self):
        d = sketch_of(SALON)
        content, placeholders = structure.content(d, year='2026')
        html, sha = render.render(d, content)
        self.assertEqual(sha, hashlib.sha256(html.encode('utf-8')).hexdigest())
        self.assertIn('סטודיו נועה', html)
        root = re.search(r':root\s*\{[^}]*\}', html).group(0)
        self.assertIn(d.contract['tokens']['--color-primary'], root)
        pair = T.pair(d.pair)
        for role in ('display', 'body'):
            self.assertIn(pair[role]['family'].replace(' ', '+'), re.search(r'<link rel="stylesheet" href="https://fonts\.googleapis[^>]+>', html).group(0))
        self.assertEqual(re.findall(r'<section[^>]* id="([a-z]+)"', html), ['top'] + [k for k in d.sections if k != 'hero'])
        self.assertIn('class="hero', html)        # the hero opens the page (id="top")
        for key, word in content['nav']:
            self.assertIn(f'href="#{key}"', html)
            self.assertIn(word, html)
        self.assertEqual(html.count('class="skeleton"'), len([k for k in d.sections if k != 'hero']))

    def test_the_page_says_it_is_a_draft_and_is_not_indexed(self):
        d = sketch_of(SALON)
        html, _ = render.render(d, structure.content(d, year='2026')[0])
        self.assertIn(f'<div class="draft-ribbon" role="note">{L.DRAFT_RIBBON}</div>', html)
        self.assertIn('<meta name=robots content=noindex>', html)
        self.assertIn('סקיצה', L.DRAFT_RIBBON)
        self.assertIn('טיוטה', L.DRAFT_RIBBON)

    def test_every_placeholder_used_is_listed_and_nothing_is_invented(self):
        d = sketch_of(SALON_NO_PHONE)
        content, placeholders = structure.content(d, year='2026')
        html, _ = render.render(d, content)
        self.assertEqual(content['phone'], structure.PHONE_LABEL)
        self.assertIn('phone', placeholders)
        for used, text in (('phone', structure.PHONE_LABEL), ('hero.lead', structure.HERO_LEAD),
                           ('hero.cta', structure.HERO_CTA)):
            self.assertIn(used, placeholders)
            self.assertIn(text, html)
        self.assertEqual(set(p for p in placeholders if p.startswith('skeleton:')),
                         {f'skeleton:{k}' for k in d.sections if k != 'hero'})
        self.assertIn('סטודיו נועה', re.search(r'<h1[^>]*>(.*?)</h1>', html).group(1))
        with_phone = structure.content(sketch_of(SALON), year='2026')
        self.assertNotIn('phone', with_phone[1])
        self.assertEqual(with_phone[0]['phone'], '04-5551234')

    def test_with_the_words_the_hero_and_the_services_are_real_and_their_placeholders_are_gone(self):
        d = sketch_of(SALON)
        content, placeholders = structure.content(d, copy.deepcopy(COPY), year='2026')
        html, _ = render.render(d, content)
        self.assertIn('תספורת שמתאימה לכם', html)
        self.assertIn('צבע לשיער.', html)
        for gone in (structure.HERO_LEAD, structure.HERO_CTA):
            self.assertNotIn(gone, html)
        self.assertEqual([p for p in placeholders if not p.startswith('skeleton:')], [])
        self.assertNotIn('skeleton:services', placeholders)
        self.assertEqual(html.count('class="skeleton"'), len([k for k in d.sections if k not in ('hero', 'services')]))
        self.assertIn('class="draft-ribbon"', html)

    def test_the_customers_text_is_escaped(self):
        brief = D.start('אתר למספרה "<script>alert(1)</script> נועה". טלפון 04-5551234')
        with on():
            r = ready(brief)
        if r.ok:
            html, _ = render.render(r.direction, structure.content(r.direction, year='2026')[0])
            self.assertNotIn('<script>alert(1)</script>', html)

    def test_a_heading_over_the_scripts_limit_raises_and_is_never_cut(self):
        d = sketch_of(SALON)
        content, _ = structure.content(d, year='2026')
        content = dict(content, hero=dict(content['hero'], title='א' * 400))
        with self.assertRaises(T.HeadingTooLong):
            render.render(d, content)

    def test_the_same_direction_gives_the_same_bytes(self):
        d = sketch_of(SALON)
        a = render.render(d, structure.content(d, year='2026')[0])
        b = render.render(sketch_of(SALON), structure.content(sketch_of(SALON), year='2026')[0])
        self.assertEqual(a, b)


class TheLibraryIsUnchangedWithoutDraft(unittest.TestCase):
    def test_a_real_page_is_byte_identical_to_main(self):
        html, _contract, _skipped = demo_law_firm.build()
        self.assertEqual(hashlib.sha256(html.encode('utf-8')).hexdigest(), DEMO_SHA)
        for needle in ('draft-ribbon', 'skeleton', 'noindex'):
            self.assertNotIn(needle, html)

    def test_draft_needs_its_ribbon(self):
        with self.assertRaises(ValueError):
            L.page(demo_law_firm.CONTENT, demo_law_firm.build()[1], draft={})

    def test_an_outline_without_draft_is_not_rendered_as_one(self):
        content = dict(demo_law_firm.CONTENT, process={'outline': True, 'title': 'איך זה עובד'})
        with self.assertRaises((KeyError, TypeError, ValueError)):
            L.page(content, demo_law_firm.build()[1])


class FingerprintsFollowTheirInputs(unittest.TestCase):
    def test_direction_fp_changes_with_the_direction_and_not_with_the_words(self):
        a, b = sketch_of(SALON), sketch_of(SALON)
        self.assertEqual(DS.direction_fp(a), DS.direction_fp(b))
        self.assertNotEqual(DS.direction_fp(a), DS.direction_fp(sketch_of(PIZZA)))
        brief = D.start(SALON)
        brief.fields['color'] = {'value': 'כחול', 'source': 'answer', 'question_id': 'color', 'confidence': 'stated'}
        with on():
            self.assertNotEqual(DS.direction_fp(a), DS.direction_fp(ready(brief).direction))
        self.assertEqual(DS.direction_fp(a), DS.direction_fp(sketch_of(SALON + ' ')))

    def test_copy_fp_changes_with_the_customers_words(self):
        a = sketch_of(SALON)
        self.assertEqual(DS.copy_fp(a), DS.copy_fp(sketch_of(SALON)))
        self.assertNotEqual(DS.copy_fp(a), DS.copy_fp(sketch_of(SALON + ' אנחנו פתוחים בערבים.')))
        self.assertNotEqual(DS.copy_fp(a), DS.copy_fp(sketch_of(PIZZA)))


class TheSketchTouchesNothingElse(unittest.TestCase):
    def test_it_imports_no_plan_approval_or_build_code(self):
        import importlib
        import pathlib
        imports = '\n'.join(l for p in pathlib.Path(DS.__file__).parent.glob('*.py')
                            for l in p.read_text(encoding='utf-8').splitlines() if re.match(r'\s*(from|import) ', l))
        for forbidden in ('approval', 'build_jobs', 'execution_plan', 'subscription', 'credit', 'investor_app',
                          'gateway', 'worker', 'store', 'intake'):
            self.assertNotIn(forbidden, imports, forbidden)
        self.assertTrue(importlib.import_module('omni_prod.direction_sketch'))


if __name__ == '__main__':
    unittest.main()
