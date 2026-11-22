"""A website is not offered for approval before the customer named the business (2026-11-22).

The content route builds only under a name the CUSTOMER declared -- a "שם העסק:" line or a span they quoted
(site_content.facts: "the model never chooses the business name"). Production, 30 days to 2026-11-22 (read-only): 292
briefs, the conversation never asked for the name, shared.brand_name was filled in none, and a name written without
quotes sent the build to the old path as name_not_declared (the tutor rehearsal 45054886983: legacy, $0.38, one repair;
the same brief with quotes, 45055452214: the new engine, $0.065, first pass). The agent now asks for it, at most
twice; the answer, in the customer's own words, joins the request as a "שם העסק:" line.
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod import discovery as d
from omni_prod.intake import conversation_agent as agent
from omni_prod.site_content import facts as Fx

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_rehearsal import Scripted  # noqa: E402

REQUEST = 'אתר תדמית למורה פרטית למתמטיקה ברחובות, נועה ברק. טלפון 054-7712345. שיעורים ברחוב הרצל 30, רחובות.'
ANSWERS = {'personal_data': 'לא', 'content_only': 'כן, אתר תוכן בלבד, לא שומרים כלום'}


def converse(name_answers, request=REQUEST, turns=10):
    """Run the conversation, answering each question it asks; the name question takes the next of `name_answers`.
    Returns (supervisor, [(asked ids, approve offered)] per turn)."""
    sup, log, names = R._Supervisor(Scripted()), [], list(name_answers)
    t = sup.turn(project_id='p', account_id='a', message=request, lang='he')
    for _ in range(turns):
        asked = list(getattr(t, 'asked_in_words', None) or [q.id for q in t.questions])
        approve = any(a['type'] == 'approve_spec' for a in t.actions)
        log.append((asked, approve))
        if approve and not names:
            break
        if agent.NAME_ID in asked:
            message = names.pop(0) if names else 'תחליטו אתם על השאר'
        else:
            message = ANSWERS.get(asked[0] if asked else None, 'תחליטו אתם על השאר')
        t = sup.turn(project_id='p', account_id='a', message=message, lang='he')
    log.append((list(getattr(t, 'asked_in_words', None) or [q.id for q in t.questions]),
                any(a['type'] == 'approve_spec' for a in t.actions)))
    return sup, log


class AsksTheName(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1', 'OMNI_SITE_LIBRARY': 'on'})
        p.start()
        self.addCleanup(p.stop)

    def test_no_approval_before_the_name_and_the_answer_becomes_the_declared_name(self):
        sup, log = converse(['נועה ברק'])
        asked_at = next(i for i, (asked, _) in enumerate(log) if agent.NAME_ID in asked)
        self.assertFalse(any(approve for _, approve in log[:asked_at + 1]))       # never offered before the name
        self.assertTrue(log[-1][1])
        brief = sup.briefs.latest('p').brief
        self.assertIn('שם העסק: נועה ברק.', brief.prompt)
        sheet = Fx.fact_sheet(brief.prompt + '\n' + d.requirements_text(brief))
        self.assertEqual(sheet.name, 'נועה ברק')

    def test_a_handed_back_answer_is_not_a_name_and_the_question_stops_after_two(self):
        sup, log = converse(['תחליטו אתם על השאר', 'לא יודע'])
        self.assertEqual(sum(agent.NAME_ID in asked for asked, _ in log), agent.ASK_NAME_AT_MOST)
        self.assertTrue(log[-1][1])                                              # then the approval opens
        self.assertNotIn('שם העסק:', sup.briefs.latest('p').brief.prompt)       # and nothing was invented

    def test_a_declared_name_is_never_asked(self):
        for request in ('אתר תדמית למורה פרטית למתמטיקה "נועה ברק". טלפון 054-7712345. שיעורים ברחוב הרצל 30, רחובות.',
                        'שם העסק: נועה ברק. אתר תדמית למורה פרטית למתמטיקה. טלפון 054-7712345.'):
            with self.subTest(request[:30]):
                _, log = converse([], request=request)
                self.assertFalse(any(agent.NAME_ID in asked for asked, _ in log))


class TheAnswer(unittest.TestCase):
    def test_names(self):
        for answer, line in (('נועה ברק', 'שם העסק: נועה ברק.'), ('קוראים לעסק "זית ולימון"', 'שם העסק: זית ולימון.'),
                             ('השם הוא לוי את שחר.', 'שם העסק: לוי את שחר.'), ('Bloom Studio', 'שם העסק: Bloom Studio.')):
            with self.subTest(answer):
                self.assertEqual(agent.name_line(answer), line)

    def test_not_names(self):
        for answer in ('תחליטו אתם על השאר', 'לא יודע', 'כן', 'לא', 'בלי שם', 'מה שמתאים', '054-7712345', 'www.x.com',
                       'אני רוצה שהאתר יהיה יפה מאוד וגם יהיה בו הרבה דברים טובים', 'א'):
            with self.subTest(answer):
                self.assertIsNone(agent.name_line(answer))

    def test_what_counts_as_declared(self):
        self.assertFalse(agent.declares_a_name('אתר תדמית למורה פרטית, נועה ברק'))
        self.assertTrue(agent.declares_a_name('אתר תדמית למורה פרטית "נועה ברק"'))
        self.assertTrue(agent.declares_a_name('שם העסק: נועה ברק.'))


if __name__ == '__main__':
    unittest.main()
