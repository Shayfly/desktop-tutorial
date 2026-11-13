"""#335 part 2 (c), Michael 2026-11-13: at gate 1, a fact the page needs and the customer never gave is asked once;
"build without it" omits that part of the page, never invents it.

Production bld_cf406df6 ("בית קפה", 2026-11-12): a call button with no phone (a dead button) and an hours section
with invented hours. Here: a call button needs a phone, an opening-hours section needs hours."""
import os
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.fact_canon import build_canon, gate_view, missing_needed
from omni_prod.skills_runtime import _invented_contact
from tests.test_conversation_os import MemoryBriefs

NO_FACTS = 'דף נחיתה לבית קפה קטן ברחוב הרצל 12 חיפה, עם כפתור שמחייג לטלפון ואזור שעות פתיחה. דף תוכן בלבד.'
WITH_FACTS = NO_FACTS + ' טלפון 04-8123456. שעות: א׳–ה׳ 07:00–19:00, שבת סגור.'


class WhatThePageNeeds(unittest.TestCase):
    def test_a_call_button_needs_a_phone_an_hours_section_needs_hours(self):
        self.assertEqual(missing_needed(NO_FACTS, build_canon(NO_FACTS)), ['phone', 'hours'])
        self.assertEqual(missing_needed(WITH_FACTS, build_canon(WITH_FACTS)), [])

    def test_no_need_no_question(self):
        text = 'דף נחיתה לסטודיו ליוגה ברחוב הרצל 12 חיפה, עם גלריה וטופס הרשמה.'
        self.assertEqual(missing_needed(text, build_canon(text)), [])

    def test_gate_1_asks_once_per_missing_fact_and_needs_the_box(self):
        view = gate_view(NO_FACTS, customer_text=NO_FACTS, family='website')
        self.assertEqual(view['status'], 'CANON_INCOMPLETE')
        self.assertEqual(view['missing_needed'], ['phone', 'hours'])
        asks = [line for line in view['lines'] if line.startswith('ביקשתם')]
        self.assertEqual(len(asks), 2)
        self.assertIn('מה מספר הטלפון?', asks[0])
        self.assertIn('לא נמציא', asks[0])
        self.assertEqual(gate_view(WITH_FACTS, customer_text=WITH_FACTS, family='website')['status'], 'OK')

    def test_build_without_omits_the_part_and_the_truth_gate_blocks_an_invention(self):
        brief = d.start(NO_FACTS)
        text = d.requirements_text(brief)
        self.assertIn('Not given by the customer (approved without it; never invent it)', text)
        self.assertIn('show no call or WhatsApp button', text)
        self.assertIn('leave out the opening-hours section', text)
        invented = '<html dir="rtl"><body><a href="tel:04-9999999">התקשרו</a><p>שבת 09:00-13:00</p></body></html>'
        found = [f for f in _invented_contact({'index.html': invented}, {'request': NO_FACTS})
                 if f.severity == 'blocking']
        self.assertTrue(any('contact details' in f.problem and '+97249999999' in f.problem for f in found))
        self.assertTrue(any('hours' in f.problem for f in found))
        self.assertNotIn('Not given by the customer', d.requirements_text(d.start(WITH_FACTS)))


class ThroughTheConversation(unittest.TestCase):
    def test_gate_1_question_then_a_message_with_the_phone_answers_it(self):
        s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
        say = lambda **kw: s.turn(project_id='p', account_id='a', lang='he', **kw)
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'}):
            t = say(message=NO_FACTS)
            for _ in range(6):
                if not t.questions:
                    break
                q = t.questions[0]
                t = say(answers={q.id: {'content_only': 'yes', 'personal_data': 'no'}.get(
                    q.id, q.recommended or q.options[0].value)})
            self.assertIn('מה מספר הטלפון?', t.reply)                         # asked at gate 1
            row = s.briefs.latest('p')
            refused = s.approve_spec(project_id='p', account_id='a', brief_fingerprint=row.fingerprint, lang='he')
            self.assertNotIn('spec_approved', str(s.store.messages_for('p')[-1].get('interpretation')))
            self.assertIn('סמנו את התיבה', refused.reply)                   # no box, no approval
            t = say(message='הטלפון 04-8123456, שעות א׳–ה׳ 07:00–19:00')       # the customer answers in a message
            self.assertNotIn('מה מספר הטלפון?', t.reply)
            self.assertNotIn('מה שעות הפתיחה?', t.reply)


if __name__ == '__main__':
    unittest.main()
