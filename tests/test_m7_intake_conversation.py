"""M7 (founder 2026-10-24): intake as a conversation, every requirement sourced in the customer's words.

Acceptance:  T1 a showcase site -> no data_create.  T2 a booking "app" -> no Android.
Four negative controls (each must go RED on a deliberately broken input), USBR = 0.
"""
from __future__ import annotations

import unittest

from omni_prod.intake import skill as S
from omni_prod.intake.conversation_agent import IntakeConversationAgent as Agent
from omni_prod.intake.sources import ASSUMED, STATED, UNSOURCED, GateRefused, Ledger, Requirement, Span

RUN1 = ('לבנות אתר של מטפחות ראש מעוצבות לקהל הדתי , צניעות זה יופי אמיתי , השם של העסק חגית אוחנה ביוטי פלייס '
        'תספר קצת על העסק תעשה משהו מושך את העין תעשה תמונה של אישה דתיה צנועה עם שמלה יפה וכיסוי ראש מהודר')
T1 = 'אני רוצה אתר תדמית למשרד עורכי דין'
T2 = 'אני רוצה אפליקציה לקביעת תורים למספרה שלי'

CONVERSATIONS = [[RUN1], [T1], [T2], [T2, 'כן, צריך לשמור גם טלפון של הלקוח'],
                 ['אני רוצה אתר עם טופס הזמנה, בלי התחברות'], ['אפליקציה לקביעת תורים לאנדרואיד'],
                 ['I want a landing page for my bakery'], ['אני רוצה מערכת לניהול משימות לצוות, עם עריכה ומחיקה']]


def run(*messages):
    a = Agent()
    t = None
    for m in messages:
        t = a.say(m)
    return a, t


class TheSkillIsTheQuestions(unittest.TestCase):
    def test_every_discovery_question_is_a_skill_entry_and_nothing_else(self):
        self.assertEqual(S.coverage(), (set(), set()))

    def test_only_build_blocking_artifact_changing_entries_can_ever_be_asked(self):
        askable = {f for f, e in S.ENTRIES.items() if e.askable()}
        self.assertEqual(askable, {'login', 'personal_data', 'content_only', 'access_scope'})
        for f in askable:
            self.assertTrue(S.entry(f).propose_he.startswith(('הנחתי', 'הבנתי')), f)   # a proposal, not a quiz


class T1ShowcaseSiteHasNoDataCreate(unittest.TestCase):
    def test_t1_showcase_site(self):
        _, t = run(T1)
        self.assertEqual((t.product_kind, t.supported), ('website', True))
        self.assertNotIn('data_create', t.required_behaviors)
        self.assertEqual(t.required_behaviors, ['data_read'])
        content = [r for r in t.stated if r['key'] == 'content_only']
        self.assertEqual([(r['value'], r['source']['quote']) for r in content], [('yes', 'אתר תדמית')])

    def test_run1_text_is_a_site_and_requires_no_data_create(self):
        # The live run 1 request: classified as a data app, data_create was required, 5 of 7 QA failures followed.
        _, t = run(RUN1)
        self.assertEqual(t.product_kind, 'website')
        self.assertNotIn('data_create', t.required_behaviors)
        # "content only" was NOT said: it is shown as an assumption, and an assumption drives no gate
        self.assertIn('content_only', [r['key'] for r in t.assumed])
        self.assertNotIn('content_only', [r['key'] for r in t.stated])
        self.assertIn('הנחנו', t.reply)

    def test_a_site_with_a_saved_form_does_require_data_create_from_those_words(self):
        _, t = run('אני רוצה אתר עם טופס הזמנה, בלי התחברות')
        self.assertIn('data_create', t.required_behaviors)
        create = next(r for r in t.stated if r['key'] == 'behavior.data_create')
        self.assertEqual(create['source']['quote'], 'טופס')


class T2BookingAppIsNotAndroid(unittest.TestCase):
    def test_t2_app_word_is_a_web_app_and_android_is_never_required(self):
        _, t = run(T2)
        self.assertEqual((t.product_kind, t.supported), ('web_app', True))
        everything = t.stated + t.assumed + t.unsourced
        self.assertFalse([r for r in everything if str(r['value']).lower() in ('android', 'ios', 'mobile_app')])
        platform = next(r for r in t.assumed if r['key'] == 'platform')
        self.assertEqual(platform['value'], 'web')
        self.assertFalse(platform['binding'])
        self.assertIn('לא אפליקציה לחנות', t.reply)                       # said aloud as an assumption
        create = next(r for r in t.stated if r['key'] == 'behavior.data_create')
        self.assertEqual(create['source']['quote'], 'קביעת')

    def test_an_explicit_android_request_is_said_aloud_as_unsupported(self):
        _, t = run('אפליקציה לקביעת תורים לאנדרואיד')
        self.assertEqual((t.product_kind, t.supported), ('mobile_app', False))
        self.assertIn('כתבת "אנדרואיד"', t.reply)
        self.assertIn('לא אבטיח', t.reply)
        self.assertEqual(t.required_behaviors, [])                         # nothing is promised for it
        self.assertEqual(t.asked, [])                                      # the kind is settled first


class ProposeAndCorrect(unittest.TestCase):
    def test_the_reply_proposes_with_the_customers_words_and_tags_defaults(self):
        _, t = run(T2)
        self.assertTrue(t.reply.startswith('הבנתי ככה'))
        self.assertIn('ביקשת: ', t.reply)
        self.assertIn('("קביעת")', t.reply)
        self.assertIn('הנחנו: ', t.reply)
        self.assertLessEqual(len(t.asked), Agent.MAX_QUESTIONS)

    def test_a_correction_supersedes_and_the_new_words_bind(self):
        a, _ = run('אני רוצה אפליקציה לקביעת תורים, עם התחברות')
        a.say('בעצם בלי התחברות')
        led = a.ledger()
        self.assertEqual(led.gate_value('login'), 'none')
        old = [r for r in led.items if r.key == 'login' and r.superseded_by is not None]
        self.assertEqual([r.value for r in old], ['simple'])
        self.assertFalse(old[0].binding)

    def test_a_button_answer_is_sourced_by_its_label(self):
        a, _ = run(T2)
        t = a.answer('personal_data', 'yes')
        row = next(r for r in t.stated if r['key'] == 'personal_data')
        self.assertEqual((row['value'], row['source']['quote']), ('yes', 'כן'))
        self.assertEqual(t.verification['usbr'], 0.0)


class Rule7OnlyBlockingAmbiguousArtifactQuestions(unittest.TestCase):
    def test_booking_asks_only_about_personal_data(self):
        _, t = run(T2)
        self.assertEqual([q['field'] for q in t.asked], ['personal_data'])

    def test_a_showcase_site_asks_nothing(self):
        for msg in (T1, RUN1):
            self.assertEqual(run(msg)[1].asked, [], msg)

    def test_a_bare_site_without_any_signal_asks_the_product_kind(self):
        _, t = run('אני רוצה אתר למספרה')
        self.assertEqual([q['field'] for q in t.asked], ['content_only'])


class USBRIsZero(unittest.TestCase):
    def test_every_binding_requirement_verifies_against_the_words(self):
        for conv in CONVERSATIONS:
            a, t = run(*conv)
            with self.subTest(conv=conv[0][:30]):
                self.assertEqual(t.verification['usbr'], 0.0)
                self.assertGreater(t.verification['binding'], 0)
                for r in t.stated:
                    src = r['source']
                    self.assertEqual(a.messages[src['message']][src['start']:src['end']], src['quote'])

    def test_handoff_carries_only_sourced_requirements_as_binding(self):
        a, _ = run(T2)
        h = a.handoff()
        self.assertEqual(h['schema'], 'intake-handoff/1')
        self.assertTrue(all(r['binding'] and r['source'] for r in h['binding']))
        self.assertTrue(all(not r['binding'] for r in h['assumed'] + h['unsourced']))
        self.assertEqual(h['verification']['usbr'], 0.0)


class NegativeControls(unittest.TestCase):
    """Each control feeds a deliberately broken input; the check must go RED."""

    def test_nc1_a_fabricated_quote_is_not_binding_and_the_checker_catches_a_forced_one(self):
        led = Ledger(['אני רוצה אתר'])
        r = led.add(Requirement('login', 'simple', STATED, Span(0, 0, 5, 'סיסמה')))     # words never said
        self.assertEqual(r.status, UNSOURCED)
        self.assertEqual(led.verify()['usbr'], 0.0)
        # bypass add(): a binding requirement smuggled in with a broken span -> USBR > 0, checker red
        led.items.append(Requirement('personal_data', 'yes', STATED, Span(0, 0, 4, 'טלפו')))
        v = led.verify()
        self.assertGreater(v['usbr'], 0.0)
        self.assertEqual(v['unsourced_binding_keys'], ['personal_data'])
        with self.assertRaises(GateRefused):
            led.gate_value('personal_data')

    def test_nc2_an_assumption_never_drives_a_gate(self):
        a, t = run(RUN1)
        self.assertIn('content_only', [r['key'] for r in t.assumed])
        with self.assertRaises(GateRefused) as ctx:
            a.ledger().gate_value('content_only')
        self.assertIn('הנחנו', str(ctx.exception))

    def test_nc3_an_unsourced_claim_is_kept_flagged_and_gate_refused(self):
        a, _ = run(T1)
        a.claim('behavior.data_create', True, 'model reading')               # e.g. a model "thinks" there is a form
        t = a.turn()
        self.assertIn('behavior.data_create', [r['key'] for r in t.unsourced])   # not thrown away
        self.assertNotIn('data_create', t.required_behaviors)                    # and not required
        with self.assertRaises(GateRefused):
            a.ledger().gate_value('behavior.data_create')

    def test_nc4_a_question_that_is_not_build_blocking_or_not_ambiguous_is_refused(self):
        a, _ = run(T2)
        led = a.ledger()
        for field, reason in (('style', 'not build-blocking'), ('color', 'not build-blocking'),
                              ('login', 'already settle'), ('content_only', 'already settle')):
            ok, why = a.may_ask(field, led)
            self.assertFalse(ok, field)
            self.assertIn(reason, why)
        self.assertTrue(a.may_ask('personal_data', led)[0])                   # the positive control

    def test_positive_controls_the_same_checks_pass_on_good_input(self):
        a, _ = run(T2)
        led = a.ledger()
        self.assertIs(led.gate_value('behavior.data_create'), True)
        self.assertEqual(led.gate_value('product_kind'), 'web_app')


class SupervisorCarriesTheUnderstanding(unittest.TestCase):
    def test_turn_exposes_the_agents_understanding(self):
        try:
            from tests.test_conversation_os import _supervisor  # noqa: F401
        except Exception:
            _supervisor = None
        from omni_prod.conversation.supervisor import Turn
        t = Turn('requirements', 'he', 'x')
        t.understanding = Agent([T2]).turn().to_dict()
        d = t.to_dict('he')
        self.assertEqual(d['understanding']['verification']['usbr'], 0.0)
        self.assertEqual(d['understanding']['product_kind'], 'web_app')


if __name__ == '__main__':
    unittest.main()
