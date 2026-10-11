"""Conversation UX (founder directive 2026-10-11, task 1): short, material-only,
never the same sentence twice, uses what the customer already said, and never
changes approved requirements silently (preservation itself: test_intake_requirements_preservation)."""
import unittest

from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor, _label
from tests.test_conversation_os import MemoryBriefs

FIRST = 'אני רוצה מערכת לניהול תורים למספרה שלי, בלי התחברות, הלקוחות ישאירו טלפון. בצבע ירוק'


class ConversationUXTests(unittest.TestCase):
    def setUp(self):
        self.s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())

    def say(self, m=None, answers=None, lang='he'):
        return self.s.turn(project_id='p', account_id='a', message=m or '', answers=answers, lang=lang)

    def test_decisions_are_named_shortly_not_by_repeating_the_question(self):
        self.assertEqual(_label('personal_data', 'yes', 'he'), 'פרטים אישיים: כן')
        t = self.say(FIRST)
        self.assertNotIn('?  →', t.reply)
        self.assertNotIn('מי ישתמש במערכת?', t.reply)                 # the question text is not echoed
        self.assertLess(len(t.reply), 320)

    def test_a_value_taken_from_the_request_is_verified_not_asked_from_scratch(self):
        t = self.say(FIRST)                                             # "phone" -> personal data, sensitive
        self.assertEqual([q.id for q in t.questions], ['personal_data'])
        self.assertIn('רק לוודא', t.reply)
        self.assertIn('פרטים אישיים: כן', t.reply)

    def test_unsure_answers_get_a_reason_then_the_options_never_the_same_text(self):
        self.say(FIRST)
        replies = [self.say(m).reply for m in ('מה?', 'לא יודע', 'לא יודע')]
        self.assertIn('למה אני שואל', replies[0])
        self.assertIn('בחרו עבורי', replies[0])                        # a way out, with the recommendation
        self.assertIn('אפשרויות', replies[1])
        for a, b in zip(replies, replies[1:]):
            self.assertNotEqual(a, b)

    def test_english_is_handled_the_same_way(self):
        self.say('I need a booking tool for my barbershop, no login, customers leave a phone number', lang='en')
        r = self.say('why?', lang='en').reply
        self.assertTrue(r.startswith('Why I ask:'))

    def test_answering_moves_on_without_repeating(self):
        t = self.say(FIRST)
        t2 = self.say(answers={t.questions[0].id: 'yes'})
        self.assertNotEqual(t.reply, t2.reply)
        self.assertNotIn('personal_data', [q.id for q in t2.questions])


if __name__ == '__main__':
    unittest.main()
