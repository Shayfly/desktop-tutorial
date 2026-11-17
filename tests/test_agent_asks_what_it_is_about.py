"""Rehearsal 44126201300 (2026-11-17, the live model): "אתר" alone reached the approval in three turns. The agent now
asks what the product is about first, never offers the approval of a request that does not say it, and the answer
joins the request the build starts from. The agent also never points at a button it does not show."""
import os
import sys
import unittest
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod.intake import conversation_agent as agent

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_rehearsal import Scripted  # noqa: E402


class AsksWhatItIsAbout(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1'})
        p.start()
        self.addCleanup(p.stop)

    def test_a_bare_request_is_asked_its_subject_first(self):
        r = R.run_scenario('bare', Scripted())
        self.assertEqual(r['transcript'][0]['asked'], [agent.SUBJECT_ID])
        self.assertIn(agent.SUBJECT_QUESTION['he'], r['transcript'][0]['agent'])
        self.assertNotIn('לשונית', r['transcript'][0]['agent'])

    def test_the_answer_joins_the_request(self):
        sup = R._Supervisor(Scripted())
        sup.turn(project_id='p', account_id='a', message='אתר', lang='he')
        sup.turn(project_id='p', account_id='a', message='למספרה שלי "תספורת טובה" בחולון', lang='he')
        self.assertIn('תספורת טובה', sup.briefs.latest('p').brief.prompt)

    def test_no_approval_without_a_subject(self):
        sup = R._Supervisor(Scripted())
        for m in ['אתר', 'כן, רק להציג מידע ומחירים, לא שומרים כלום מהמבקרים', 'לא, רק הטלפון שלי מופיע באתר',
                  'תחליטו אתם על השאר', 'תחליטו אתם על השאר', 'תחליטו אתם על השאר']:
            t = sup.turn(project_id='q', account_id='a', message=m, lang='he')
            if agent.names_a_subject(sup.briefs.latest('q').brief.prompt):
                break
            self.assertFalse(any(a['type'] == 'approve_spec' for a in t.actions), m)

    def test_a_named_business_is_not_asked(self):
        r = R.run_scenario('butcher', Scripted())
        self.assertNotIn(agent.SUBJECT_ID, [x for t in r['transcript'] for x in t['asked']])

    def test_the_subject_rule(self):
        for text in ['אתר', 'תבנה לי אתר', 'אתר תדמית לעסק', 'דף נחיתה, טלפון 050-1234567', 'build me a 2d game']:
            self.assertFalse(agent.names_a_subject(text), text)
        for text in ['אתר למספרה שלי בחולון', 'אתר לאטליז', 'אתר לחנות "ורד"', 'Build a team task tracker web app']:
            self.assertTrue(agent.names_a_subject(text), text)

    def test_no_button_in_agent_words(self):
        from omni_prod.conversation.supervisor import _TXT as _TEXT
        for lang in ('he', 'en'):
            self.assertNotIn('כפתור', _TEXT[lang]['confirm_sensitive_words'])
            self.assertNotIn('button', _TEXT[lang]['confirm_sensitive_words'])


if __name__ == '__main__':
    unittest.main()
