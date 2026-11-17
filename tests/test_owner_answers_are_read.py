"""The owner's own conversation, 2026-11-17 (prj_9GM6q4KQX-tu9A): two answers were misread before any model spoke.

1. "רק אני יכול לשנות מחירים או מבצעים" -- who EDITS the site -- was read as audience "internal team" (high
   confidence), and the conversation later asked "which is right?".
2. Asked "האם צריך התחברות עם סיסמה?", the owner typed "לא אני משנה את האתר דרך כאן בעתיד". A leading "לא" was not read,
   the model's guess (roles) stayed and became a blocker ("התחברות והרשאות ... אינן זמינות").
Real path for 2: ConversationSupervisor.turn with the agent on (the in-memory stores stand in for SQL only)."""
import os
import re
import sys
import unittest
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod import discovery as d
from omni_prod.intake import conversation_agent as agent
from omni_prod.intake.interpreter import RULES

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_rehearsal import Scripted  # noqa: E402

INTERNAL = next(rx for rx, field, value, conf in RULES if field == 'audience' and value == 'internal' and 'just for' in rx)


class OnlyIEditIsNotAnAudience(unittest.TestCase):
    def test_who_edits_is_not_who_reads(self):
        for text in ('רק אני יכול לשנות מחירים או מבצעים או כל דבר באתר', 'רק לי מותר לערוך', 'רק אני מעדכן את המחירים'):
            self.assertIsNone(re.search(INTERNAL, text), text)

    def test_only_for_me_is_still_internal(self):
        for text in ('אתר רק בשבילי', 'רק אני אשתמש בזה', 'לשימוש פנימי'):
            self.assertIsNotNone(re.search(INTERNAL, text), text)


class ALeadingNoAnswersTheLoginQuestion(unittest.TestCase):
    def test_the_owners_words(self):
        q = d.BY_ID['login']
        self.assertEqual(agent.typed_choice(q, 'לא אני משנה את האתר דרך כאן בעתיד'), 'none')
        self.assertEqual(agent.typed_choice(q, 'לא'), 'none')

    def test_what_is_not_a_no(self):
        q = d.BY_ID['login']
        for text in ('לא יודע', 'לא בטוח', 'לא משנה לי', 'no idea', 'כן'):
            self.assertIsNone(agent.typed_choice(q, text), text)

    def test_a_no_that_names_an_option_answers_with_that_option(self):
        self.assertEqual(agent.typed_choice(d.BY_ID['login'], 'לא, צריך הרשאות למנהל ועובד'), 'roles')

    def test_on_the_real_path(self):
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1'}):
            sup = R._Supervisor(Scripted())
            message = 'מערכת לניהול תורים למספרה שלי "תספורת טובה" בחולון'
            for _ in range(4):
                sup.turn(project_id='p', account_id='a', message=message, lang='he')
                if 'login' in (sup.store.messages_for('p')[-1].get('interpretation') or {}).get('asked', []):
                    break
                message = 'תחליטו אתם על השאר'
            else:
                self.fail('the login question was never asked')
            sup.turn(project_id='p', account_id='a', message='לא אני משנה את האתר דרך כאן בעתיד', lang='he')
            login = sup.briefs.latest('p').brief.fields.get('login') or {}
            self.assertEqual((login.get('value'), login.get('source')), ('none', 'answer'))


if __name__ == '__main__':
    unittest.main()
