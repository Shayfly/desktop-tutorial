"""WP1 / QUESTIONS-001: gap detector and free-language questions. Mandatory tests 1-5 and 8; materiality and
order derived from THIS request (owner review 2026-10-25 20:05); the supervisor driven by the detector; and the six
model conditions (fallback kept, one call, only what is missing, mapped to a field, unfocused refused and focused
accepted, not ASCII-only for Hebrew/Arabic)."""
from __future__ import annotations

import json
import unittest
from types import SimpleNamespace as P

from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake.artifact_fields import ARTIFACT_FIELDS, CONDITIONAL, fields_for
from omni_prod.intake.gaps import FALLBACK, MATERIAL, Questioner, Spec, fallback_text, language_of
from tests.test_conversation_os import MemoryBriefs

SALON = {'he': 'אני רוצה אתר למספרה שלי', 'ar': 'أريد موقعًا لصالون الحلاقة الخاص بي', 'en': 'I want a website for my barbershop'}
BARE = {'he': 'אני רוצה אתר', 'ar': 'أريد موقعًا', 'en': 'I want a website'}
YOU_DECIDE = {'he': 'תחליט אתה', 'ar': 'قرر أنت', 'en': 'you decide'}


def prop(field, value, evidence, confidence='high'):
    return P(field=field, value=value, evidence=evidence, confidence=confidence)


def spec(kind, msg):
    s = Spec(kind)
    s.hear(msg)
    return s


def declared_index(kind, name):
    return [f.name for f in fields_for(kind)].index(name)


class FakeModel:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def __call__(self, *, system, user):
        self.calls.append(json.loads(user))
        return self.answer(self.calls[-1]) if callable(self.answer) else self.answer


class Declarations(unittest.TestCase):
    def test_every_field_has_an_explicit_default_and_a_phrased_reason_when_material(self):
        for f in [f for fs in ARTIFACT_FIELDS.values() for f in fs] + list(CONDITIONAL.values()):
            self.assertTrue(f.default, f.name)
            if f.base >= MATERIAL or f.raises or f.confirm:          # can be material for some request
                for lang in FALLBACK:
                    self.assertIn(f.reason, FALLBACK[lang], (lang, f.name))


class TheOrderComesFromTheRequest(unittest.TestCase):
    """The deciding test: the fixed declaration order would ask X first, the request makes Y more material -> Y."""

    def test_tourists_make_language_more_material_than_audience(self):
        self.assertLess(declared_index('website', 'audience'), declared_index('website', 'languages'))
        plain = spec('website', 'אני רוצה אתר')
        self.assertIn('audience', plain.detect()['missing_material'])          # X is open in the plain request
        self.assertNotIn('languages', plain.detect()['missing_material'])      # Y is implied by the conversation
        tourists = spec('website', 'אני רוצה אתר לתיירים שמגיעים לעיר')
        q = Questioner().next(tourists)
        self.assertEqual(q.field, 'languages')                               # Y, although X is declared first
        self.assertEqual(tourists.detect()['order'][0]['because'], 'תיירים')
        self.assertNotIn('audience', tourists.detect()['missing_material'])  # "tourists" already says who

    def test_counterfactual_the_fixed_order_would_ask_x_the_detector_asks_y(self):
        s = spec('website', 'אני רוצה אתר לתיירים שמגיעים לעיר')
        open_now = set(s.detect()['missing_material'])
        fixed = next(f.name for f in fields_for('website') if f.name in open_now | {'audience'})   # a questionnaire
        self.assertEqual(fixed, 'audience')                                    # X
        self.assertEqual(Questioner().next(s).field, 'languages')              # Y

    def test_a_booking_app_asks_about_stored_personal_details_first(self):
        s = spec('web_app', 'אני רוצה אפליקציה לקביעת תורים')
        for earlier in ('audience', 'style', 'login'):
            self.assertLess(declared_index('web_app', earlier), declared_index('web_app', 'personal_data'))
        self.assertEqual(Questioner().next(s).field, 'personal_data')


class MaterialityComesFromTheRequest(unittest.TestCase):
    def test_a_field_the_request_implies_is_not_material_here(self):
        for lang in ('he', 'ar', 'en'):
            g = spec('website', SALON[lang]).detect()
            self.assertEqual(g['implied']['languages']['value'], lang)       # LANG-001: the customer's language
            self.assertEqual(g['implied']['audience']['value'], 'public')    # "for my salon" says who reads it
            self.assertNotIn('audience', g['missing_material'])
        team = spec('web_app', 'I need an internal tool for my team to track loans').detect()
        self.assertEqual(team['implied']['audience']['value'], 'internal')

    def test_the_same_field_becomes_material_when_the_request_raises_it(self):
        self.assertNotIn('login', spec('website', 'אני רוצה אתר למספרה').detect()['missing_material'])
        self.assertIn('login', spec('website', 'אני רוצה אתר למספרה עם אזור אישי ללקוחות').detect()['missing_material'])

    def test_a_sensitive_implication_is_proposed_and_still_confirmed(self):
        s = Spec('web_app')
        s.hear('אפליקציה לתורים, הלקוחות ישאירו טלפון', [prop('personal_data', 'yes', 'טלפון', 'medium')])
        g = s.detect()
        self.assertEqual(g['proposed'], {'personal_data': 'yes'})
        self.assertEqual(g['missing_material'][0], 'personal_data')
        self.assertNotIn('personal_data', g['known'])                        # implied is not stated


class NoFieldIsMaterialByDeclaration(unittest.TestCase):
    def test_the_declaration_has_no_material_flag(self):
        for f in [f for fs in ARTIFACT_FIELDS.values() for f in fs] + list(CONDITIONAL.values()):
            self.assertFalse(hasattr(f, 'material'), f.name)

    def test_a_button_colour_is_not_material_unless_this_request_makes_it_so(self):
        plain = spec('website', 'אני רוצה אתר למספרה שלי')
        self.assertEqual(plain.detect()['assumed']['color'], 'blue')
        self.assertNotIn('color', plain.detect()['missing_material'])
        brand = spec('website', 'אני רוצה אתר למספרה שלי בצבעי המותג')
        self.assertIn('color', brand.detect()['missing_material'])             # material for THIS request
        self.assertNotIn('color', brand.detect()['assumed'])


class MandatoryBehaviour(unittest.TestCase):
    def test_1_missing_material_gives_one_free_question_with_a_reason(self):
        s = spec('website', SALON['he'])
        q = Questioner().next(s)
        self.assertEqual(q.field, s.detect()['missing_material'][0])
        self.assertIn('כי', q.text)
        self.assertIn('תחליט אתה', q.text)
        self.assertEqual(len(s.log), 1)

    def test_2_missing_non_material_is_not_asked_and_is_an_assumption_with_its_default(self):
        s = spec('website', SALON['en'])
        g = s.detect()
        self.assertEqual(g['assumed'], {'color': 'blue', 'font': 'heebo', 'logo': 'text', 'references': 'none'})
        asked = []
        while (q := Questioner().next(s)) is not None:
            asked.append(q.field)
            s.hear(YOU_DECIDE['en'])
        self.assertFalse(set(asked) & set(g['assumed']))
        self.assertFalse(set(asked) & set(g['implied']))

    def test_3_known_from_history_even_in_passing_is_not_asked(self):
        s = Spec('website')
        s.hear('אני רוצה אתר, אגב בסגנון חם ומזמין', [prop('style', 'warm', 'חם ומזמין')])
        self.assertEqual(s.detect()['known'], {'style': 'warm'})
        while (q := Questioner().next(s)) is not None:
            self.assertNotEqual(q.field, 'style')
            s.hear(YOU_DECIDE['he'])

    def test_3b_a_proposal_whose_quote_is_not_in_the_words_does_not_count_as_known(self):
        s = Spec('website')
        s.hear(BARE['he'], [prop('style', 'warm', 'חם ומזמין')])                  # words never said
        self.assertIn('style', s.detect()['missing_material'])

    def test_4_you_decide_continues_and_is_tagged_as_an_assumption(self):
        s = spec('web_app', 'אני רוצה אפליקציה לקביעת תורים')
        q = Questioner().next(s)
        s.hear(YOU_DECIDE['he'])
        cur = s.ledger.current(q.field)
        self.assertEqual((cur.status, cur.why), ('assumed', 'delegated'))
        self.assertFalse(cur.binding)
        self.assertNotEqual(Questioner().next(s).field, q.field)

    def test_5_hebrew_arabic_english_behave_the_same(self):
        traces = {}
        for lang, opening in SALON.items():
            s = spec('website', opening)
            asked = []
            while (q := Questioner().next(s)) is not None:
                self.assertEqual(q.language, lang)
                asked.append(q.field)
                s.hear(YOU_DECIDE[lang])
            traces[lang] = (asked, s.resolved()['color'], s.metrics()['unmapped'])
        self.assertEqual(traces['ar'], traces['he'])
        self.assertEqual(traces['en'], traces['he'])
        self.assertEqual(language_of(SALON['ar']), 'ar')

    def test_8_every_question_is_logged_with_its_field_and_measured(self):
        s = spec('website', BARE['he'])
        q = Questioner().next(s)
        before = s.fingerprint()
        s.hear('רק מציג מידע', [prop(q.field, 'no' if q.field == 'content_only' else 'internal', 'רק מציג מידע')])
        e = s.log[0]
        self.assertEqual((e.field, e.filled), (q.field, True))
        self.assertEqual(e.changed_artifact, s.fingerprint() != before)
        Questioner().next(s)
        s.hear('אממ')                                                          # an answer that fills nothing
        self.assertEqual(s.metrics()['redundant'], 1)
        self.assertEqual(s.metrics()['unmapped'], 0)


class TheSupervisorIsDrivenByTheDetector(unittest.TestCase):
    def test_the_one_question_asked_is_the_detectors_not_the_questionnaires(self):
        sup = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
        t = sup.turn(project_id='p', account_id='a', message='אני רוצה אתר לתיירים שמגיעים לעיר')
        self.assertEqual([q.field for q in t.questions], [t.gaps['question']['field']])
        self.assertEqual(t.gaps['question']['field'], 'languages')
        self.assertIn(t.gaps['question']['text'], t.reply)
        shown = t.to_dict('he')                                                   # what the customer's app receives
        self.assertEqual(shown['gaps']['question']['field'], 'languages')
        self.assertEqual([q['field'] for q in shown['questions']], ['languages'])


class ModelPhrasing(unittest.TestCase):
    def ask(self, answer, lang='he'):
        s = spec('website', SALON[lang])
        m = FakeModel(answer(s.detect()['missing_material'][0]) if callable(answer) else answer)
        return Questioner(m).next(s), m, s

    def test_focused_answer_is_accepted_with_one_call_and_only_what_is_missing(self):
        q, m, s = self.ask(lambda f: {'field': f, 'question': 'מה האתר צריך לעשות? אפשר גם "תחליט אתה".'})
        self.assertEqual((q.source, q.rejected), ('model', ''))
        self.assertEqual(len(m.calls), 1)
        # the model is given the ordered list of what is missing and chooses one field from it (2026-10-28)
        self.assertEqual(m.calls[0]['missing'][0]['field'], q.field)
        self.assertIn(q.field, s.detect()['missing_material'])
        self.assertNotIn('questions', json.dumps(m.calls[0]))

    def test_unfocused_answer_is_detected_and_the_fallback_asks(self):
        q, m, s = self.ask({'field': 'color', 'question': 'איזה צבע תרצה?'})
        self.assertEqual(q.source, 'fallback')
        self.assertTrue(q.rejected.startswith('unfocused'))
        reason = next(f.reason for f in list(s.fields) + list(CONDITIONAL.values()) if f.name == q.field)
        self.assertEqual(q.text, fallback_text(reason, 'he'))

    def test_an_ascii_only_question_to_a_hebrew_or_arabic_customer_is_refused(self):
        for lang in ('he', 'ar'):
            q, _, _ = self.ask(lambda f: {'field': f, 'question': 'What should the site do?'}, lang)
            self.assertEqual((q.source, q.rejected), ('fallback', 'ascii_only'), lang)
            self.assertFalse(q.text.isascii(), lang)
        q, _, _ = self.ask(lambda f: {'field': f, 'question': 'What should the site do?'}, 'en')
        self.assertEqual(q.source, 'model')

    def test_malformed_or_failing_model_falls_back(self):
        def boom(_):
            raise RuntimeError('budget')
        for answer in ('not json', {'field': 'audience'}):
            q, _, _ = self.ask(answer)
            self.assertEqual(q.source, 'fallback')
        s = spec('website', SALON['he'])
        q = Questioner(FakeModel(boom)).next(s)
        self.assertEqual(q.source, 'fallback')
        self.assertTrue(q.rejected.startswith('error'))


if __name__ == '__main__':
    unittest.main()
