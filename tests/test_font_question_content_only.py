"""The owner, 2026-11-25, on the font question: "א. צריך שיהיה את כל המגוון" (DECISIONS.md). Option (א): a content-only
site no longer asks the customer which font -- 148AI picks a pair that suits the business from its font-pair library.
On the real path (omni_prod.discovery, the conversation supervisor's own filter, the server's discovery view, the
content route):

* a content-only site is not asked which font -- not by the questionnaire, not by the chat's gap detector, not in what
  the server sends the screen -- and an app still is, with the same four options;
* a content-only site's Design line names no customer font (148AI's, and it says so), and the summary the customer
  approves claims no font choice; an app's Design line carries the customer's font as before;
* "content-only" is the content route's own test: for every combination of the answers that decide it, the question is
  skipped exactly when the approved brief block passes product_architect.content_only_approved;
* a brief built here reaches the content route and its design contract locks a pair from the library.
The screen (omni_prod/assets/app.js) draws the font sample only inside the card of a font question the server sent, so
a question that is not sent has no sample."""
import itertools
import os
import re
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import discovery as d
from omni_prod import site_content as SC
from omni_prod import typography as T
from omni_prod.brief_repository import BriefRow
from omni_prod.conversation.supervisor import ConversationSupervisor as Sup
from omni_prod.g_apple import contract as C
from omni_prod.intake.gaps import Spec
from omni_prod.product_architect import content_only_approved

ROOT = Path(__file__).resolve().parent.parent
LANDING = 'אתר תדמית למספרה "תספורת דני" בתל אביב. טלפון 050-1234567. כתובת: הרצל 10, תל אביב.'
APP = 'מערכת לניהול תורים למספרה "תספורת דני": לקוחות קובעים תור, ואני רואה את היומן.'
CONTENT_ONLY = {'login': 'none', 'personal_data': 'no', 'content_only': 'yes'}
APP_ANSWERS = {'login': 'none', 'personal_data': 'no', 'content_only': 'no'}
HEEBO = "'Heebo', system-ui, sans-serif"


def walk(brief: d.Brief, rounds: int = 20) -> tuple[d.Brief, list[str]]:
    """Answer the questionnaire group by group as a customer who leaves every choice to 148AI; the ids asked, in order."""
    asked = []
    for _ in range(rounds):
        _, qs = d.next_group(brief)
        if not qs:
            return brief, asked
        asked += [q.id for q in qs]
        brief = d.answer(brief, {q.id: d.DELEGATE if q.delegable and q.recommended is not None else q.options[0].value
                                 for q in qs})
    raise AssertionError(f'the questionnaire did not end in {rounds} rounds: {asked}')


def design_line(brief: d.Brief) -> str:
    return next(line for line in d.requirements_text(brief).splitlines() if line.startswith('Design: '))


class TheQuestion(unittest.TestCase):
    def test_a_content_only_site_is_never_asked_which_font(self):
        brief, asked = walk(d.answer(d.start(LANDING), CONTENT_ONLY))
        self.assertNotIn('font', asked)
        self.assertTrue(d.complete(brief))
        self.assertNotIn('font', brief.fields)
        self.assertIn('style', asked)                                  # the design group itself is still asked
        # the brief led by the gap detector: its fallback never names it either
        brief.detector = True
        self.assertNotIn('font', [q.id for q in d.must_ask(brief)])
        self.assertNotIn('font', [q.id for q in d.panel_group(brief)[1]])

    def test_a_font_chosen_before_the_site_was_content_only_goes_with_the_question(self):
        # the recommend mode fills the font before content-only is known; the customer's "content only" then drops it
        early = d.start(LANDING, d.RECOMMEND)
        self.assertEqual(early.fields['font']['value'], 'heebo')
        self.assertNotIn('font', d.answer(early, CONTENT_ONLY).fields)
        answered = d.answer(d.start(LANDING), {'font': 'rubik'})
        self.assertEqual(answered.fields['font']['value'], 'rubik')
        self.assertNotIn('font', d.answer(answered, CONTENT_ONLY).fields)
        # and a site that stops being content-only is asked again
        back = d.answer(d.answer(answered, CONTENT_ONLY), {'content_only': 'no'})
        self.assertIn('font', [q.id for q in d.pending(back)])

    def test_an_app_is_still_asked_which_font_with_the_same_four_options(self):
        _, asked = walk(d.answer(d.start(APP), APP_ANSWERS))
        self.assertIn('font', asked)
        q = d.BY_ID['font']
        self.assertEqual(([o.value for o in q.options], q.recommended), (['heebo', 'assistant', 'rubik', 'system'], 'heebo'))
        _, asked = walk(d.answer(d.start(APP), {'login': 'simple'}))        # sign-in: never content-only
        self.assertIn('font', asked)

    def test_the_chat_does_not_ask_it_even_when_the_request_makes_it_material(self):
        # "לקשישים" makes the typeface material (intake.artifact_fields: _READABLE), so the detector lists it; the
        # supervisor asks only outside what the brief closed, and a content-only brief closes the font
        spec = Spec('website')
        spec.hear(LANDING + ' האתר מיועד לקשישים.')
        site = d.answer(d.start(LANDING + ' האתר מיועד לקשישים.'), CONTENT_ONLY)
        app = d.answer(d.start(APP + ' לקשישים.'), APP_ANSWERS)
        missing = spec.detect([q.field for q in d.pending(site)])['missing_material']
        self.assertIn('font', missing)
        self.assertNotIn('font', Sup._askable(missing, Sup._closed_in_brief(site), None))
        self.assertIn('font', Sup._askable(missing, Sup._closed_in_brief(app), None))


class WhatTheBriefSays(unittest.TestCase):
    def test_a_content_only_design_line_names_no_customer_font(self):
        brief = d.answer(d.answer(d.start(LANDING), {'font': 'rubik'}), CONTENT_ONLY)
        brief.fields['font'] = {'value': 'rubik', 'source': 'answer', 'question_id': 'font', 'confidence': 'confirmed'}
        line = design_line(brief)                    # even a font left in the brief by an older path is not used
        self.assertIn(f'font {HEEBO} ({d.PLATFORM_FONT_NOTE})', line)
        self.assertNotIn('Rubik', d.requirements_text(brief))
        self.assertIn('not by the customer', line)
        # the design contract still reads its one font from the line: the platform's, until the route locks a pair
        self.assertEqual(C.build(brief.prompt + '\n' + d.requirements_text(brief))['tokens']['--font-family'], HEEBO)

    def test_an_apps_design_line_carries_the_customers_font_as_before(self):
        brief = d.answer(d.answer(d.start(APP), APP_ANSWERS), {'font': 'rubik'})
        self.assertIn("font 'Rubik', system-ui, sans-serif (load it from Google Fonts with a system fallback); define",
                      design_line(brief))
        self.assertNotIn(d.PLATFORM_FONT_NOTE, d.requirements_text(brief))

    def test_the_summary_the_customer_approves_claims_no_font_choice(self):
        brief, _ = walk(d.answer(d.start(LANDING), CONTENT_ONLY))
        brief.fields['font'] = {'value': 'assistant', 'source': 'delegated', 'question_id': 'font', 'confidence': 'x'}
        s = d.summary(brief)
        shown = [x['field'] for items in s['sections'].values() for x in items] + [x['field'] for x in s['assumptions']]
        self.assertNotIn('font', shown)
        self.assertIn('style', shown)
        app, _ = walk(d.answer(d.answer(d.start(APP), APP_ANSWERS), {'font': 'rubik'}))
        design = d.summary(app)['sections']['design']
        self.assertIn(('font', 'Rubik — מעוגל וידידותי'), [(x['field'], x['value']) for x in design])

    def test_content_only_is_the_content_routes_own_test(self):
        decided = {True: 0, False: 0}
        for content_only, login, personal, scope in itertools.product(
                ('yes', 'no', None), ('none', 'simple', 'roles', None), ('yes', 'no', None),
                (None, 'internal_link', 'add_login', 'no_personal')):
            fields = {k: {'value': v, 'source': 'answer', 'question_id': k, 'confidence': 'confirmed'}
                      for k, v in (('content_only', content_only), ('login', login), ('personal_data', personal),
                                   ('access_scope', scope)) if v is not None}
            brief = d.Brief(LANDING, d.GUIDED, fields)
            route = content_only_approved(brief.prompt + '\n' + d.requirements_text(brief))
            with self.subTest(content_only=content_only, login=login, personal=personal, scope=scope):
                self.assertEqual(d.fonts_by_platform(brief.values()), route)
                self.assertEqual(d.BY_ID['font'].ask_if(d._ctx(brief)), not route)
                self.assertEqual(d.PLATFORM_FONT_NOTE in design_line(brief), route)
            decided[route] += 1
        # content-only: "yes", sign-in none or not asked (2), no personal data, any scope but add_login (3)
        self.assertEqual(decided, {True: 6, False: 138})


class TheRoute(unittest.TestCase):
    def test_a_brief_built_here_gets_a_library_pair_on_the_content_route(self):
        brief, _ = walk(d.answer(d.start(LANDING), CONTENT_ONLY))
        prompt = brief.prompt + '\n' + d.requirements_text(brief)
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
            route = SC.decide(prompt, {'user_id': 'usr_font_question'}, year='2026')
        self.assertEqual((route.route, route.script), ('section_library', 'hebrew'), route.reason)
        p = T.pair(route.font_pair)
        self.assertIn(route.direction, p['tones'])
        self.assertEqual(p, T.pair_for('hebrew', category=route.category, tone=route.direction, business='תספורת דני'))
        self.assertEqual(route.contract['fonts'], {'pair': p['id'], 'script': 'hebrew', 'brief_font': HEEBO})
        self.assertEqual((route.contract['tokens']['--font-family'], route.contract['tokens']['--font-display']),
                         (T.stack(p['body']), T.stack(p['display'])))


class TheScreen(unittest.TestCase):
    def view_ids(self, brief: d.Brief) -> tuple[list[str], list[str]]:
        from omni_prod.investor_app import _discovery_view
        row = BriefRow('brf_test', 'prj_test', 1, brief, d.complete(brief), brief.fingerprint())
        view = _discovery_view(row, 'he')
        return [q['id'] for q in view['questions']], [a['id'] for a in view['answered']]

    def test_the_server_never_sends_a_content_only_site_the_font_question(self):
        brief, sent = d.answer(d.start(LANDING), CONTENT_ONLY), []
        for _ in range(20):
            questions, answered = self.view_ids(brief)
            self.assertNotIn('font', answered)
            if not questions:
                break
            sent += questions
            brief = d.answer(brief, {q: d.DELEGATE for q in questions})
        self.assertNotIn('font', sent)
        self.assertIn('style', sent)
        app, sent = d.answer(d.start(APP), APP_ANSWERS), []
        for _ in range(20):
            questions, _ = self.view_ids(app)
            if not questions:
                break
            sent += questions
            app = d.answer(app, {q: d.DELEGATE for q in questions})
        self.assertIn('font', sent)

    def test_the_screen_draws_a_font_sample_only_in_a_font_question_the_server_sent(self):
        js = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
        card = js.index('function questionCard(q, current) {')
        start = js.index("  if (q.id === 'font') {", card)
        end = js.index("  } else if (q.kind === 'choice') {", start)
        samples = [m.start() for m in re.finditer(r"class:`fontSample ", js)]
        loads = [m.start() for m in re.finditer(r'document\.fonts\.load\(', js)]
        self.assertEqual(len(samples), 1)
        self.assertTrue(all(start < i < end for i in samples + loads), 'a font sample drawn outside the font question')
        # its only callers draw what the server's discovery view sent: the open questions and the answered ones
        self.assertEqual(len(re.findall(r'questionCard\(', js)), 3)
        self.assertEqual(re.findall(r'\.\.\.d\.(\w+)\.map\(\s*\w+\s*=>\s*questionCard\(', js), ['answered', 'questions'])


if __name__ == '__main__':
    unittest.main()
