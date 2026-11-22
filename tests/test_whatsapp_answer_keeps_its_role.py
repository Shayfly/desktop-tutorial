"""A WhatsApp number keeps its role (task 62; the owner's build prj_9c357UySW645bg, 2026-11-22).

Production transcript (intake_messages, read-only; the question and the answer below are verbatim, the earlier turns in TRANSCRIPT are shortened):
  09:40:41 assistant  "... עם כפתורי וואטסאפ והתקשרות, בלי טופס ובלי שמירת מידע. מה מספר הוואטסאפ שתרצו שיופיע באתר?"
  09:44:37 customer   "0503456723"
The bare answer was stored as a bare span, so the content route saw two main phones (03-5551234 and 050-...), said
phone_not_one, and the build went to the old path. A bare number answering a question about WhatsApp is now stored as
"וואטסאפ: <number>", and a mobile number the customer labelled WhatsApp keeps the label.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod import discovery as d
from omni_prod.site_content import facts as Fx

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_rehearsal import Scripted  # noqa: E402

FIX = Path(__file__).resolve().parent / 'fixtures' / 'owner_brief_noa' / 'brief.json'
REQUEST = ('אתר תדמית למספרה "סטודיו נועה", רחוב הרצל 12, חולון. טלפון 03-5551234. שעות: א׳–ה׳ 09:00–19:00, '
           'ו׳ 08:00–13:00. שירותים: תספורת, פן, צבע. כפתור להתקשרות. תמונה ראשית: מספרה מוארת עם כיסא עבודה ומראה גדולה.')
ASKED = ('הבנתי: אתר תוכן בלבד ל״סטודיו נועה״, עם כפתורי וואטסאפ והתקשרות, בלי טופס ובלי שמירת מידע. '
         'מה מספר הוואטסאפ שתרצו שיופיע באתר?')
TRANSCRIPT = [
    {'role': 'customer', 'content': REQUEST},
    {'role': 'assistant', 'content': 'הבנתי שאתם רוצים אתר תדמית ל״סטודיו נועה״... האם יישמרו פרטים אישיים של אנשים (שם, טלפון, מייל)?'},
    {'role': 'customer', 'content': 'לא'},
    {'role': 'assistant', 'content': 'האם זה אתר תוכן בלבד — מציג מידע, מחירים וקישורים, ולא שומר כלום מהמבקרים?'},
    {'role': 'customer', 'content': 'כן — אתר תוכן בלבד. כפתור וואטסאפ וטלפון, בלי טופס ובלי שמירה.'},
    {'role': 'assistant', 'content': ASKED},
    {'role': 'customer', 'content': '0503456723'},
]


def owners_brief(spans):
    raw = json.loads(FIX.read_text(encoding='utf-8'))
    raw['assets']['facts']['spans'] = spans
    return d.Brief.from_dict(raw)


def sheet(brief):
    with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
        return Fx.fact_sheet(brief.prompt + '\n' + d.requirements_text(brief))


class TheOwnersConversation(unittest.TestCase):
    def test_the_answer_is_stored_as_the_whatsapp_number(self):
        brief = owners_brief([])
        d.note_customer_texts(brief, d.customer_messages(TRANSCRIPT))
        spans = brief.assets['facts']['spans']
        self.assertIn('וואטסאפ: 0503456723', spans)
        self.assertNotIn('0503456723', spans)

    def test_the_route_has_one_main_phone_and_the_whatsapp_number(self):
        brief = owners_brief([])
        d.note_customer_texts(brief, d.customer_messages(TRANSCRIPT))
        s = sheet(brief)
        self.assertEqual(s.problems, [])
        self.assertEqual((s.phone, s.whatsapp, s.whatsapp_basis), ('03-5551234', '0503456723', 'labelled'))

    def test_a_brief_stored_before_the_fix_is_corrected_by_collecting_again(self):
        stored = json.loads(FIX.read_text(encoding='utf-8'))['assets']['facts']['spans']
        brief = owners_brief(list(stored))                       # holds the bare "0503456723" from production
        self.assertEqual(sheet(brief).problems, ['phone_not_one'])
        self.assertTrue(d.note_customer_texts(brief, d.customer_messages(TRANSCRIPT)))
        self.assertEqual(sheet(brief).problems, [])

    def test_the_turn_and_the_stored_messages_agree(self):
        # the supervisor stores each message as it arrives; the approval check collects all stored ones again -- the
        # two must give the same spans, or every approval reads "facts_not_collected"
        one = owners_brief([])
        asked = None
        for m in TRANSCRIPT:
            if m['role'] == 'assistant':
                asked = m['content']
            else:
                d.note_customer_texts(one, [d.answer_in_context(m['content'], asked)])
        self.assertFalse(d.note_customer_texts(one, d.customer_messages(TRANSCRIPT)))


class TheSupervisorTurn(unittest.TestCase):
    def test_the_typed_answer_is_read_against_the_question_before_it(self):
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1', 'OMNI_SITE_LIBRARY': 'on'}):
            sup = R._Supervisor(Scripted())
            sup.turn(project_id='p', account_id='a', message=REQUEST, lang='he')
            sup.store.add_message(project_id='p', account_id='a', role='assistant', content=ASKED)
            sup.turn(project_id='p', account_id='a', message='0503456723', lang='he')
        spans = sup.briefs.latest('p').brief.assets['facts']['spans']
        self.assertIn('וואטסאפ: 0503456723', spans)
        self.assertNotIn('0503456723', spans)


class TheReading(unittest.TestCase):
    def test_answers(self):
        for message, asked, read in (
                ('0503456723', ASKED, 'וואטסאפ: 0503456723'),
                ('050-3456723.', ASKED, 'וואטסאפ: 050-3456723'),
                ('0503456723', 'עם כפתור וואטסאפ. מה מספר הטלפון?', '0503456723'),     # the question is about the phone
                ('0503456723', 'מה מספר הטלפון והוואטסאפ?', '0503456723'),             # both: not guessed
                ('בטח, 0503456723', ASKED, 'בטח, 0503456723'),                           # not only a number
                ('0503456723', None, '0503456723')):
            with self.subTest(message=message, asked=asked):
                self.assertEqual(d.answer_in_context(message, asked), read)

    def test_labels(self):
        self.assertEqual(d._labelled_spans('וואטסאפ: 050-3456723, טלפון 03-5551234', ['050-3456723', '03-5551234']),
                         ['וואטסאפ: 050-3456723', '03-5551234'])
        self.assertEqual(d._labelled_spans('טלפון 050-3456723 וגם וואטסאפ', ['050-3456723']), ['050-3456723'])
        self.assertEqual(d._labelled_spans('וואטסאפ 03-5551234', ['03-5551234']), ['03-5551234'])   # a landline


if __name__ == '__main__':
    unittest.main()
