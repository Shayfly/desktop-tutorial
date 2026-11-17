"""A content-only answer is not dropped in silence (production 2026-11-17, "148 דלתות": "אתר תוכן בלבד: כן", then
"פרטים אישיים: כן" -- the first answer disappeared and the site became a leads database). The conflict is asked
once, in words, through the real conversation; the customer's choice settles both answers."""
import unittest

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs

PROMPT = 'אתר לחברת דלתות מקצועית, טלפון 050-345-6723'


class TheConflictIsAsked(unittest.TestCase):
    def setUp(self):
        self.briefs = MemoryBriefs()
        self.sup = ConversationSupervisor(briefs=self.briefs, store=MemoryConversationStore(), credits=10,
                                          context=lambda p: {})

    def turn(self, **kw):
        return self.sup.turn(project_id='p', account_id='a', lang='he', **kw)

    def brief(self):
        return self.briefs.latest('p').brief

    def the_production_order(self):
        self.turn(message=PROMPT)
        self.turn(answers={'content_only': 'yes'})
        t = self.turn(answers={'personal_data': 'yes'})
        return t

    def test_the_question_is_asked_with_its_words_and_nothing_is_dropped(self):
        t = self.the_production_order()
        asked = []
        for _ in range(10):                                   # bounded: the other open questions come first
            ids = [q.id for q in t.questions]
            asked += ids
            if not ids or 'storage_intent' in ids:
                break
            q = t.questions[0]
            t = self.turn(answers={q.id: q.options[0].value if q.options else d.DELEGATE})
        self.assertIn('storage_intent', asked)
        self.assertIn('לא שומר כלום מהמבקרים', d.BY_ID['storage_intent'].he)
        self.assertEqual(self.brief().values().get('content_only'), 'yes')        # kept while it is asked
        self.assertFalse(self.briefs.latest('p').complete)                        # no approval before it is settled

    def test_business_details_only_is_a_content_site(self):
        self.the_production_order()
        self.turn(answers={'storage_intent': 'business'})
        v = self.brief().values()
        self.assertEqual((v.get('content_only'), v.get('personal_data')), ('yes', 'no'))
        text = d.requirements_text(self.brief())
        self.assertIn('"persistence":"none"', text)
        self.assertIn('CONTENT-ONLY website', text)

    def test_visitors_details_is_a_site_that_stores(self):
        self.the_production_order()
        self.turn(answers={'storage_intent': 'visitors'})
        self.assertIn('"persistence":"records"', d.requirements_text(self.brief()))
        self.assertNotIn('storage_conflict', self.brief().hints)

    def test_personal_details_first_is_not_a_conflict(self):
        b = d.answer(d.start(PROMPT), {'personal_data': 'yes'})
        self.assertNotIn('storage_conflict', b.hints)
        self.assertNotIn('storage_intent', [q.id for q in d.pending(b)])

    def test_it_cannot_be_delegated(self):
        b = d.answer(d.answer(d.start(PROMPT), {'content_only': 'yes'}), {'personal_data': 'yes'})
        with self.assertRaises(ValueError):
            d.answer(b, {'storage_intent': d.DELEGATE})


if __name__ == '__main__':
    unittest.main()
