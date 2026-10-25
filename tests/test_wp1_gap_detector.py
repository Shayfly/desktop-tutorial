"""WP1 / QUESTIONS-001: gap detector and free-language questions. Mandatory tests 1-5 and 8, plus the six
model conditions (fallback kept, one call, only what is missing, mapped to a field, unfocused refused and
focused accepted, not ASCII-only for Hebrew/Arabic)."""
from __future__ import annotations

import json
import unittest
from types import SimpleNamespace as P

from omni_prod.intake.artifact_fields import ARTIFACT_FIELDS
from omni_prod.intake.gaps import FALLBACK, Questioner, Spec, fallback_text, language_of

OPENING = {'he': 'אני רוצה אתר למספרה שלי', 'ar': 'أريد موقعًا لصالون الحلاقة الخاص بي', 'en': 'I want a website for my barbershop'}
YOU_DECIDE = {'he': 'תחליט אתה', 'ar': 'قرر أنت', 'en': 'you decide'}


def prop(field, value, evidence):
    return P(field=field, value=value, evidence=evidence)


class FakeModel:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def __call__(self, *, system, user):
        self.calls.append(json.loads(user))
        return self.answer(self.calls[-1]) if callable(self.answer) else self.answer


class Declarations(unittest.TestCase):
    def test_every_field_has_an_explicit_default_and_a_phrased_reason_when_material(self):
        for kind, fields in ARTIFACT_FIELDS.items():
            for f in fields:
                self.assertTrue(f.default, (kind, f.name))
                if f.material:
                    for lang in FALLBACK:
                        self.assertIn(f.reason, FALLBACK[lang], (lang, f.name))


class MandatoryBehaviour(unittest.TestCase):
    def test_1_missing_material_gives_one_free_question_with_a_reason(self):
        s = Spec('website')
        s.hear(OPENING['he'])
        q = Questioner().next(s)
        self.assertEqual(q.field, 'audience')                       # the first missing material field, one only
        self.assertIn('כי', q.text)                                 # with a reason
        self.assertIn('תחליט אתה', q.text)                          # "you decide" always offered
        self.assertEqual(len(s.log), 1)

    def test_2_missing_non_material_is_not_asked_and_is_an_assumption_with_its_default(self):
        s = Spec('website')
        s.hear(OPENING['en'])
        g = s.detect()
        self.assertEqual(g['assumed'], {'color': 'blue', 'font': 'heebo', 'logo': 'text', 'references': 'none'})
        asked = []
        while (q := Questioner().next(s)) is not None:              # answer every material field
            asked.append(q.field)
            s.hear(YOU_DECIDE['en'])
        self.assertEqual(asked, ['audience', 'languages', 'style'])
        self.assertFalse(set(asked) & set(g['assumed']))

    def test_3_known_from_history_even_in_passing_is_not_asked(self):
        s = Spec('website')
        msg = 'אני רוצה אתר למספרה שלי, בעיקר לסטודנטים מהשכונה'
        s.hear(msg, [prop('audience', 'public', 'לסטודנטים מהשכונה')])
        self.assertEqual(s.detect()['known'], {'audience': 'public'})
        self.assertNotEqual(Questioner().next(s).field, 'audience')

    def test_3b_a_proposal_whose_quote_is_not_in_the_words_does_not_count_as_known(self):
        s = Spec('website')
        s.hear(OPENING['he'], [prop('audience', 'public', 'לקהל הרחב')])          # words never said
        self.assertEqual(Questioner().next(s).field, 'audience')

    def test_4_you_decide_continues_and_is_tagged_as_an_assumption(self):
        s = Spec('web_app')
        s.hear('אני רוצה אפליקציה לקביעת תורים')
        q = Questioner().next(s)
        s.hear(YOU_DECIDE['he'])
        cur = s.ledger.current(q.field)
        self.assertEqual((cur.status, cur.why), ('assumed', 'delegated'))
        self.assertFalse(cur.binding)                                # an assumption, never binding
        self.assertNotEqual(Questioner().next(s).field, q.field)     # the conversation moves on

    def test_5_hebrew_arabic_english_behave_the_same(self):
        traces = {}
        for lang, opening in OPENING.items():
            s = Spec('website')
            s.hear(opening)
            asked = []
            while (q := Questioner().next(s)) is not None:
                self.assertEqual(q.language, lang)
                asked.append(q.field)
                s.hear(YOU_DECIDE[lang])
            traces[lang] = (asked, s.resolved()['color'], s.metrics()['unmapped'])
        self.assertEqual(traces['he'], (['audience', 'languages', 'style'], 'blue', 0))
        self.assertEqual(traces['ar'], traces['he'])
        self.assertEqual(traces['en'], traces['he'])
        self.assertEqual(language_of(OPENING['ar']), 'ar')

    def test_5b_delegated_language_is_the_customers_language_not_hebrew(self):
        s = Spec('website')
        s.hear(OPENING['ar'])
        for _ in range(4):
            q = Questioner().next(s)
            s.hear(YOU_DECIDE['ar'])
            if q.field == 'languages':
                break
        self.assertEqual(s.resolved()['languages'], 'ar')

    def test_8_every_question_is_logged_with_its_field_and_measured(self):
        s = Spec('website')
        s.hear(OPENING['he'])
        Questioner().next(s)
        before = s.fingerprint()
        s.hear('ללקוחות פרטיים', [prop('audience', 'internal', 'ללקוחות פרטיים')])
        e = s.log[0]
        self.assertEqual((e.field, e.filled, e.changed_artifact), ('audience', True, s.fingerprint() != before))
        self.assertTrue(e.changed_artifact)                          # internal != the default "public"
        Questioner().next(s)
        s.hear('לא יודע')                                          # an answer that fills nothing
        self.assertEqual(s.metrics()['redundant'], 1)
        self.assertEqual(s.metrics()['unmapped'], 0)


class ModelPhrasing(unittest.TestCase):
    def ask(self, answer, lang='he'):
        s = Spec('website')
        s.hear(OPENING[lang])
        m = FakeModel(answer)
        return Questioner(m).next(s), m

    def test_focused_answer_is_accepted_with_one_call_and_only_what_is_missing(self):
        q, m = self.ask({'field': 'audience', 'question': 'למי מיועד האתר — לקוחות קבועים או חדשים? אפשר גם "תחליט אתה".'})
        self.assertEqual((q.source, q.field, q.rejected), ('model', 'audience', ''))
        self.assertEqual(len(m.calls), 1)                            # one call, no loop
        self.assertEqual(m.calls[0]['missing'], {'field': 'audience', 'why_it_matters': 'who_reads'})
        self.assertNotIn('questions', json.dumps(m.calls[0]))      # what is missing, not a question list

    def test_unfocused_answer_is_detected_and_the_fallback_asks(self):
        q, m = self.ask({'field': 'color', 'question': 'איזה צבע תרצה?'})
        self.assertEqual((q.source, q.field), ('fallback', 'audience'))
        self.assertTrue(q.rejected.startswith('unfocused'))
        self.assertEqual(q.text, fallback_text('who_reads', 'he'))
        self.assertEqual(len(m.calls), 1)

    def test_an_ascii_only_question_to_a_hebrew_or_arabic_customer_is_refused(self):
        for lang in ('he', 'ar'):
            q, _ = self.ask({'field': 'audience', 'question': 'Who is the site for?'}, lang)
            self.assertEqual((q.source, q.rejected), ('fallback', 'ascii_only'), lang)
            self.assertFalse(q.text.isascii(), lang)
        q, _ = self.ask({'field': 'audience', 'question': 'Who is the site for?'}, 'en')
        self.assertEqual(q.source, 'model')

    def test_malformed_or_failing_model_falls_back(self):
        def boom(_):
            raise RuntimeError('budget')
        for answer in ('not json', {'field': 'audience'}, boom):
            q, _ = self.ask(answer)
            self.assertEqual(q.source, 'fallback')
            self.assertEqual(len(q.text) > 0, True)


if __name__ == '__main__':
    unittest.main()
