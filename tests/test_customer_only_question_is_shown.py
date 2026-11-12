"""#330 (Michael 2026-11-12 19:36): while the conversation is "listening" the customer sees the model's own reply
(CEO 2026-11-08, no questionnaire). When the NEXT question is for a field only the customer may set
(delegable=False), that exact question and its buttons are shown TOO -- both, not one of them. Before this a
landing page could never reach the summary: content_only waited for a button the customer never saw, while the
model kept asking "anything else?" (production, 2026-11-12, the "בית קפה" project, 12 revisions)."""
import os
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake.interpreter import DeterministicInterpreter, merge, validate_model_output
from tests.test_conversation_os import MemoryBriefs

MODEL_SAYS = 'יש עוד משהו שחשוב לך?'
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

    def assert_both(self, t, qid):
        q = d.BY_ID[qid]
        self.assertFalse(q.delegable)
        self.assertEqual(t.interpretation['interpreter'], 'model:fake')        # the listening (model) path ran
        self.assertIn(MODEL_SAYS, t.reply)                                       # the model's words stay ...
        self.assertIn(q.he, t.reply)                                             # ... AND the exact question
        self.assertEqual([x.id for x in t.questions], [qid])                     # with its buttons
        self.assertTrue(q.options)

    def test_the_landing_page_question_is_shown_with_the_model_reply(self):
        self.assert_both(self.turn(message=LANDING), 'content_only')

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
        first = self.next_customer_only().questions[0].id                 # two missing: one of them is next ...
        self.assertIn(first, answer)
        self.assert_both(self.turn(message='בסדר'), first)                 # ... shown with the reply (and stays)
        self.turn(answers={first: answer[first]})
        second = ({'content_only', 'unavailable'} - {first}).pop()
        self.assertEqual([q.id for q in d.must_ask(self.brief())], [second])
        self.assert_both(self.next_customer_only(), second)                # then the other, also with the reply

    def test_a_field_held_open_after_a_typed_answer_is_still_asked(self):
        # production 2026-11-12: after an unsettled repeat content_only was "held open" and never asked again
        self.turn(message=LANDING)
        self.turn(message='כן, אתר תוכן בלבד — בלי שמירת נתונים.')
        self.assertIn('content_only', self.brief().open_material)
        self.assert_both(self.next_customer_only(), 'content_only')

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
