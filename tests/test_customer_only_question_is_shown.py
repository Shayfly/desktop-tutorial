"""#330 (Michael 2026-11-12 19:36): while the conversation is "listening" the customer sees the model's own reply
(CEO 2026-11-08, no questionnaire). When the NEXT question is for a field only the customer may set
(delegable=False), that exact question and its buttons are shown TOO -- both, not one of them. Before this a
landing page could never reach the summary: content_only waited for a button the customer never saw, while the
model kept asking "anything else?" (production, 2026-11-12, the "בית קפה" project, 12 revisions).

Michael 2026-11-13 (production, "מאפייה"): the model asked in its own words and the card asked again. Now the
question comes from the card ONLY: the reply keeps the model's context and never asks (no question sentence), and
a sentence of the question is never written out -- so there is no repeat count to keep any more."""
import os
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake.interpreter import DeterministicInterpreter, merge, validate_model_output
from tests.test_conversation_os import MemoryBriefs

MODEL_CONTEXT = 'בית קפה קטן עם תמונה ראשית — נשמע מצוין.'
MODEL_SAYS = MODEL_CONTEXT + ' יש עוד משהו שחשוב לך?'
ENV = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.05',
       'OMNI_INTAKE_DAILY_BUDGET_USD': '0.50', 'OMNI_INTAKE_CALL_BUDGET_USD': '0.005'}
LANDING = ('דף נחיתה לבית קפה קטן עם תמונה ראשית, שעות פתיחה וכפתור שמחייג לטלפון. '
           'בלי טפסים, בלי התחברות, בלי שמירת פרטים אישיים. ללקוחות.')


class FakeModel:
    """The production pattern: a friendly reply that never asks the customer-only question itself."""

    def interpret(self, message, brief=None):
        model, _ = validate_model_output({'language': 'he', 'product_family': 'web_app', 'reply': MODEL_SAYS,
                                          'proposals': []}, message)
        return merge(DeterministicInterpreter().interpret(message, brief), model, interpreter='model:fake',
                     cost_usd='0', cost_state='CONFIRMED_ZERO')


class CustomerOnlyQuestion(unittest.TestCase):
    def setUp(self):
        self.s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(),
                                        worker_interpreter=FakeModel())
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)

    def turn(self, **kw):
        return self.s.turn(project_id='p', account_id='a', lang='he', **kw)

    def brief(self):
        return self.s.briefs.latest('p').brief

    def assert_card_only(self, t, qid):
        q = d.BY_ID[qid]
        self.assertFalse(q.delegable)
        self.assertEqual(t.interpretation['interpreter'], 'model:fake')        # the listening (model) path ran
        self.assertIn(MODEL_CONTEXT, t.reply)                                    # the model's context stays ...
        self.assertNotIn('?', t.reply)                                           # ... it asks nothing itself
        self.assertNotIn(q.he, t.reply)                                          # ... not this question either
        self.assertEqual([x.id for x in t.questions], [qid])                     # the card asks, with its buttons
        self.assertTrue(q.options)

    def test_the_landing_page_question_is_shown_with_the_model_reply(self):
        self.assert_card_only(self.turn(message=LANDING), 'content_only')

    def test_the_button_settles_it_and_the_conversation_moves_on(self):
        self.turn(message=LANDING)
        t = self.turn(answers={'content_only': 'yes'})
        f = self.brief().fields['content_only']
        self.assertEqual((f['value'], f['source']), ('yes', 'answer'))
        self.assertNotIn('content_only', [q.id for q in d.must_ask(self.brief())])
        self.assertNotIn('content_only', [q.id for q in t.questions])

    def test_typed_text_still_does_not_set_it(self):
        # unchanged rule (discovery.py: never delegable, never defaulted); the follow-up item is separate from #330
        self.turn(message=LANDING)
        self.turn(message='כן, אתר תוכן בלבד — בלי שמירת נתונים.')
        self.assertIsNone(self.brief().fields.get('content_only'))

    def next_customer_only(self, turns=3):
        """Plain messages until a customer-only question is the next one (a delegable one may come first)."""
        for _ in range(turns):
            t = self.turn(message='בסדר')
            if any(not q.delegable for q in t.questions or []):
                return t
        self.fail('no customer-only question was shown in %d turns' % turns)

    def test_two_customer_only_fields_open_each_is_shown_in_turn(self):
        # Michael: the condition is "the next question is delegable=False", not "the only missing field"
        self.turn(message=LANDING)
        self.brief().hints['unpriced'] = 'integration.maps'          # 77: an unpriced capability -> "unavailable"
        self.assertEqual([q.id for q in d.must_ask(self.brief())], ['content_only', 'unavailable'])   # both open
        answer = {'content_only': 'yes', 'unavailable': 'build_without'}
        t = self.next_customer_only()                                      # two missing: one of them is next ...
        first = t.questions[0].id
        self.assertIn(first, answer)
        self.assertEqual([q.id for q in t.questions], [first])             # ... with its buttons
        self.turn(answers={first: answer[first]})
        second = ({'content_only', 'unavailable'} - {first}).pop()
        self.assertEqual([q.id for q in d.must_ask(self.brief())], [second])
        t = self.next_customer_only()                                      # then the other one, with its buttons
        self.assertEqual([q.id for q in t.questions], [second])
        self.assertIn(MODEL_CONTEXT, t.reply)                              # ... and the model's context
        for qid in answer:                                                 # the card asked each; the text never did
            self.assertFalse(any(d.BY_ID[qid].he in (m.get('content') or '') for m in self.s.store.messages_for('p')
                                 if m['role'] == 'assistant'), qid)

    def test_a_field_held_open_after_a_typed_answer_is_still_asked(self):
        # production 2026-11-12: after an unsettled repeat content_only was "held open" and never asked again
        self.turn(message=LANDING)
        self.turn(message='כן, אתר תוכן בלבד — בלי שמירת נתונים.')
        self.assertIn('content_only', self.brief().open_material)
        self.assert_card_only(self.next_customer_only(), 'content_only')

    def test_irrelevant_answers_the_card_stays_and_the_text_never_asks(self):
        # Michael 19:45 (irrelevant answers in a row) + 2026-11-13 (the card asks, the text does not)
        q = d.BY_ID['content_only']
        replies = [self.turn(message=LANDING)]
        for words in ('מה שלומך?', 'איזה יום היום?', 'אני חושב על זה', 'נראה', 'אולי', 'לא יודע'):   # irrelevant
            replies.append(self.turn(message=words))
        for t in replies:
            if [x.id for x in t.questions] == ['content_only']:
                self.assertNotIn(q.he, t.reply)
                self.assertNotIn('?', t.reply)
        self.assertEqual([x.id for x in replies[-1].questions], ['content_only'])   # the buttons stay
        self.turn(answers={'content_only': 'yes'})                   # and the button still settles it
        self.assertEqual(self.brief().fields['content_only']['source'], 'answer')

    # --- class 3 (Michael 2026-11-12 20:11): sensitive, inferable, but counts only once CONFIRMED -----------------
    PLAIN = 'דף נחיתה לבית קפה קטן עם תמונה ראשית, שעות פתיחה וכפתור שמחייג לטלפון. ללקוחות.'

    def test_the_three_classes(self):
        self.assertEqual(d.CONFIRM_REQUIRED, ('personal_data', 'login', 'access_scope'))
        b = d.Brief(prompt='x')
        self.assertFalse(d.needs_customer(d.BY_ID['style'], b))                  # class 1
        self.assertTrue(d.needs_customer(d.BY_ID['content_only'], b))            # class 2, unanswered
        b.fields['content_only'] = {'value': 'yes', 'source': 'answer', 'confidence': 'confirmed'}
        self.assertFalse(d.needs_customer(d.BY_ID['content_only'], b))           # class 2, answered by button
        for f in d.CONFIRM_REQUIRED:                                             # class 3
            q = d.BY_ID[f]
            b.fields[f] = {'value': 'x', 'source': 'message', 'confidence': 'stated'}
            self.assertTrue(d.needs_customer(q, b), f)                           # stated is not confirmed
            b.fields[f] = {'value': 'x', 'source': 'default', 'confidence': 'inferred'}
            self.assertTrue(d.needs_customer(q, b), f)                           # inferred is not confirmed
            b.fields[f] = {'value': 'x', 'source': 'answer', 'confidence': 'confirmed'}
            self.assertFalse(d.needs_customer(q, b), f)

    def test_a_held_sensitive_field_is_asked_with_its_buttons(self):
        # production 2026-11-12 after #331: personal_data held open by the detector, never asked, "nothing new"
        self.turn(message=self.PLAIN)
        self.turn(answers={'content_only': 'yes'})
        self.turn(message='אולי')                                    # an unsettled reply: the detector holds it
        self.assertIn('personal_data', self.brief().open_material)
        t = self.turn(message='בסדר')
        self.assertEqual([q.id for q in t.questions], ['personal_data'])       # asked, with its buttons
        self.assertTrue(d.BY_ID['personal_data'].options)

    def test_its_sentence_is_never_written_out(self):
        q = d.BY_ID['personal_data']
        self.turn(message=self.PLAIN)
        self.turn(answers={'content_only': 'yes'})
        replies = [self.turn(message=w) for w in ('אולי', 'בסדר', 'נראה', 'לא יודע', 'מה?')]
        self.assertFalse(any(q.he in t.reply for t in replies))
        self.assertTrue(all([x.id for x in t.questions] == ['personal_data'] for t in replies[1:]))  # buttons stay

    def test_a_button_confirms_it_releases_the_hold_and_the_brief_completes(self):
        self.turn(message=self.PLAIN)
        self.turn(answers={'content_only': 'yes'})
        self.turn(message='אולי')
        self.assertIn('personal_data', self.brief().open_material)
        t = self.turn(answers={'personal_data': 'no'})
        self.assertTrue(d.confirmed(self.brief(), 'personal_data'))
        self.assertNotIn('personal_data', self.brief().open_material)            # the hold no longer blocks it
        self.assertTrue(self.s.briefs.latest('p').complete)                      # the summary is reachable
        self.assertEqual(t.questions, [])

    def test_the_hold_never_blocks_a_confirmed_value(self):
        from types import SimpleNamespace
        spec = SimpleNamespace(value=lambda name: None)              # the detector has no value of its own
        b = d.Brief(prompt='x')
        b.fields['personal_data'] = {'value': 'no', 'source': 'answer', 'confidence': 'confirmed'}
        b.fields['login'] = {'value': 'none', 'source': 'message', 'confidence': 'stated'}
        self.assertEqual(ConversationSupervisor._still_held({'personal_data', 'login'}, spec, b), {'login'})

    def test_after_a_button_turn_the_held_field_is_asked_not_nothing_new(self):
        # production 2026-11-12 20:06, reproduced exactly on main: the content_only button turn answered
        # "לא זיהיתי פרטים חדשים" with no question while personal_data was held open
        self.turn(message=self.PLAIN + ' עיצוב חם וכפרי.')
        self.turn(message='אולי')
        self.turn(message='בסדר')
        t = self.turn(answers={'content_only': 'yes'})               # a button turn: no model reply
        self.assertEqual(self.brief().open_material, ['personal_data'])
        self.assertEqual([q.id for q in t.questions], ['personal_data'])       # asked, with its buttons
        self.assertNotIn('לא זיהיתי פרטים חדשים', t.reply)
        self.turn(answers={'personal_data': 'no'})
        self.assertTrue(self.s.briefs.latest('p').complete)                      # and the summary is reachable

    def test_a_delegable_next_question_keeps_the_model_reply_only(self):
        self.turn(message=LANDING)
        t = self.turn(answers={'content_only': 'yes'})              # next: style (delegable)
        t = self.turn(message='תודה')
        asked = [q for q in (t.questions or [])]
        self.assertTrue(all(getattr(q, 'delegable', True) for q in asked))
        if t.interpretation and t.interpretation.get('interpreter') == 'model:fake':
            self.assertEqual(t.questions, [])                       # the CEO 2026-11-08 rule is unchanged here

    def test_the_rule_is_the_next_question_itself(self):
        pick = ConversationSupervisor._customer_only_question
        self.assertIs(pick([d.BY_ID['content_only'], d.BY_ID['style']]), d.BY_ID['content_only'])
        self.assertIsNone(pick([d.BY_ID['style'], d.BY_ID['content_only']]))   # next is delegable: not forced
        self.assertIsNone(pick([]))
        self.assertIsNone(pick(None))


if __name__ == '__main__':
    unittest.main()
