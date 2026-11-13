"""#339 condition (Michael 2026-11-13): a limit on how often the SAME card (question + buttons) is shown unanswered --
not on the sentence. CARD_LIMIT = 3 shows; then:
  * a field with a privacy-safe answer (personal_data, access_scope) gets it as a default, said in THAT turn, marked
    on the gate-1 summary; the card is not shown again;
  * any other customer-only field (content_only, login, unavailable) is blocked: the card stops repeating, the turn
    says what is missing and carries a direct link to the "Requirements" tab."""
import os
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import CARD_LIMIT, ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs

PLAIN = 'דף נחיתה לבית קפה קטן עם תמונה ראשית, שעות פתיחה וכפתור שמחייג לטלפון. ללקוחות.'
IDLE = ('אולי', 'בסדר', 'נראה', 'לא יודע', 'מה?', 'אחר כך', 'טוב')


class CardLimit(unittest.TestCase):
    def setUp(self):
        self.s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'})
        p.start()
        self.addCleanup(p.stop)

    def turn(self, **kw):
        return self.s.turn(project_id='p', account_id='a', lang='he', **kw)

    def brief(self):
        return self.s.briefs.latest('p').brief

    def shows_until_it_stops(self, qid, first):
        """Idle replies until `qid`'s card stops being shown: (how many turns showed it, the turn after)."""
        shown = int([q.id for q in first.questions] == [qid])
        for words in IDLE * 2:
            t = self.turn(message=words)
            if [q.id for q in t.questions] == [qid]:
                shown += 1
            elif shown and qid not in [q.id for q in t.questions]:
                if qid in (t.blocked or []) or not d.needs_customer(d.BY_ID[qid], self.brief()):
                    return shown, t
        self.fail(f'{qid}: the card never stopped ({shown} shows)')

    def test_the_limit(self):
        self.assertEqual(CARD_LIMIT, 3)

    def test_a_blocked_field_stops_repeating_and_links_to_the_requirements_tab(self):
        self.turn(message=PLAIN)
        first = self.turn(answers={'personal_data': 'no'})            # the content_only card comes next
        shown, t = self.shows_until_it_stops('content_only', first)
        self.assertEqual(shown, CARD_LIMIT)
        self.assertEqual(t.questions, [])
        self.assertIn('חסרה החלטה על אתר תוכן בלבד', t.reply)
        self.assertIn('content_only', t.blocked)
        self.assertTrue(any(a['type'] == 'open_requirements' and a['field'] == 'content_only' for a in t.actions))
        self.assertIsNone(self.brief().fields.get('content_only'))   # never decided for the customer
        self.assertFalse(self.s.briefs.latest('p').complete)
        self.turn(answers={'content_only': 'yes'})                     # the decision still settles it
        self.assertTrue(d.confirmed(self.brief(), 'content_only'))

    def test_a_privacy_field_gets_the_safe_default_said_at_that_moment(self):
        first = self.turn(message=PLAIN)
        self.assertEqual([q.id for q in first.questions], ['personal_data'])
        self.turn(answers={'content_only': 'yes'})
        shown, t = self.shows_until_it_stops('personal_data', first)
        self.assertEqual(shown, CARD_LIMIT)
        self.assertIn('הפעלתי ברירת מחדל בטוחה: לא', t.reply)          # said in the turn it is applied
        f = self.brief().fields['personal_data']
        self.assertEqual((f['value'], f['confidence']), ('no', d.SAFE_DEFAULT_CONFIDENCE))
        self.assertFalse(d.needs_customer(d.BY_ID['personal_data'], self.brief()))
        later = self.turn(message='בסדר')
        self.assertNotIn('personal_data', [q.id for q in later.questions])   # the card is not shown again

    def test_the_gate_1_summary_marks_the_safe_default(self):
        self.test_a_privacy_field_gets_the_safe_default_said_at_that_moment()
        row = self.s.briefs.latest('p')
        if row.complete:
            from omni_prod.conversation.supervisor import Turn
            turn = Turn('requirements', 'he', '', row, [])
            parts = self.s._gate1(turn, row, 'he')
            self.assertIn('פרטים אישיים: לא (ברירת מחדל בטוחה)', ' '.join(parts))


if __name__ == '__main__':
    unittest.main()
