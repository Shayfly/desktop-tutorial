"""Phase 1 of the conversation agent (the owner, 2026-11-17: no ready-made questionnaire). With OMNI_INTAKE_AGENT=1
the customer never sees a question card: every question is in the reply, in words, and a typed answer settles it --
only for the question just asked, only when the words name one option. The real supervisor runs the whole
conversation; the approvals stay buttons."""
import os
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import conversation_agent as A
from tests.test_conversation_os import MemoryBriefs

REQUEST = 'אתר תדמית לחברת דלתות "148 דלתות" באשקלון, טלפון 050-345-6723. התקנת דלתות ממד ודלתות פנים.'
# what a customer types to each question, in their own words
TYPED = {'content_only': 'כן, רק להציג מידע ומחירים', 'audience': 'לקוחות שלי, בעלי דירות באזור',
         'personal_data': 'לא, רק הטלפון שלי מופיע', 'login': 'בלי התחברות',
         'storage_intent': 'רק פרטי העסק', 'access_scope': 'לא לשמור פרטים'}


class NoCards(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {A.FLAG: '1'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        self.sup = ConversationSupervisor(briefs=self.briefs, store=self.store, credits=10, context=lambda p: {})

    def say(self, message):
        return self.sup.turn(project_id='p', account_id='a', message=message, lang='he')

    def converse(self):
        turns = [self.say(REQUEST)]
        for _ in range(15):                                   # bounded
            t = turns[-1]
            if any(a['type'] == 'approve_spec' for a in t.actions):
                break
            asked = (self.store.messages_for('p')[-1].get('interpretation') or {}).get('asked') or []
            qid = next((x for x in asked if x in TYPED), None)
            turns.append(self.say(TYPED[qid] if qid else 'תחליטו אתם'))
        return turns

    def test_the_whole_conversation_has_no_card_and_reaches_the_approval(self):
        turns = self.converse()
        self.assertTrue(all(t.questions == [] for t in turns), [t.questions for t in turns])
        self.assertTrue(any(a['type'] == 'approve_spec' for a in turns[-1].actions), turns[-1].reply)
        v = self.briefs.latest('p').brief.values()
        self.assertEqual(v.get('content_only'), 'yes')
        self.assertIn('"persistence":"none"', d.requirements_text(self.briefs.latest('p').brief))

    def test_each_question_is_in_the_reply_in_words(self):
        t = self.say(REQUEST)
        asked = (self.store.messages_for('p')[-1].get('interpretation') or {}).get('asked') or []
        self.assertTrue(asked)
        self.assertIn(d.BY_ID[asked[0]].he[:20], t.reply)
        self.assertEqual(t.questions, [])

    def test_a_typed_answer_counts_only_for_the_question_just_asked(self):
        self.say(REQUEST)
        asked = (self.store.messages_for('p')[-1].get('interpretation') or {}).get('asked') or []
        other = next(q for q in ('login', 'personal_data', 'content_only') if q not in asked)
        before = self.briefs.latest('p').brief.fields.get(other)
        self.say('כן')                                         # "yes" -- to the question asked, not to `other`
        after = self.briefs.latest('p').brief.fields.get(other)
        self.assertEqual(before, after)                         # an unasked question is never answered by "yes"
        answered = self.briefs.latest('p').brief.fields.get(d.BY_ID[asked[0]].field) or {}
        if A.typed_choice(d.BY_ID[asked[0]], 'כן'):
            self.assertEqual(answered.get('source'), 'answer')   # the asked one is

    def test_words_that_name_no_option_or_two_set_nothing(self):
        q = d.BY_ID['personal_data']
        self.assertIsNone(A.typed_choice(q, 'מה זאת אומרת?'))
        self.assertIsNone(A.typed_choice(q, 'כן... לא, לא יודע'))
        self.assertEqual(A.typed_choice(q, 'לא, רק הטלפון שלי מופיע'), 'no')
        self.assertIsNone(A.typed_choice(d.BY_ID['login'], 'בלי התחברות, או אולי עם הרשאות'))   # two options named

    def test_the_flag_is_strict(self):
        with mock.patch.dict(os.environ, {A.FLAG: 'yes'}):
            with self.assertRaises(ValueError):
                A.enabled()
        with mock.patch.dict(os.environ, {A.FLAG: '0'}):
            self.assertFalse(A.enabled())

    def test_without_the_flag_the_cards_are_as_before(self):
        with mock.patch.dict(os.environ, {A.FLAG: '0'}):
            sup = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), credits=10,
                                         context=lambda p: {})
            turns = [sup.turn(project_id='q', account_id='a', message=REQUEST, lang='he')]
            for _ in range(4):
                if turns[-1].questions:
                    break
                turns.append(sup.turn(project_id='q', account_id='a', message='תחליטו אתם', lang='he'))
        self.assertTrue(any(t.questions for t in turns))


if __name__ == '__main__':
    unittest.main()
