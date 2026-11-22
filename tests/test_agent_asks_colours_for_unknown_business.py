"""A business we do not know is asked about colours (the owner, 2026-11-22).

The owner's tutor brief named no catalogue category: its short version had nothing near (score 0), so the Design line
said "choose a palette" and the build left the new engine (no design contract). The owner decided: for any business we
do not recognise, the agent asks in plain words which colours the customer likes, which should take the most space and
which less -- or to leave it to us; left to us, the palette is always one we have (the nearest category, else the
neutral one). The answer is the brief's "color" field with source "answer", so the choice stays in the evidence.
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod import discovery as d
from omni_prod import vertical_palettes as V
from omni_prod.intake import conversation_agent as agent

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_rehearsal import Scripted  # noqa: E402

TUTOR = 'אתר תדמית למורה פרטית למתמטיקה "נועה ברק". טלפון 054-7712345. שיעורים ברחוב הרצל 30, רחובות.'
LAWYER = 'אתר תדמית למשרד עורכי דין "לוי ושות׳". טלפון 03-5551234. רחוב הרצל 5, תל אביב.'
ANSWERS = {'personal_data': 'לא', 'content_only': 'כן, אתר תוכן בלבד, לא שומרים כלום'}


def converse(colour_answer, request=TUTOR, turns=10):
    sup, log = R._Supervisor(Scripted()), []
    t = sup.turn(project_id='p', account_id='a', message=request, lang='he')
    for _ in range(turns):
        asked = list(getattr(t, 'asked_in_words', None) or [q.id for q in t.questions])
        approve = any(a['type'] == 'approve_spec' for a in t.actions)
        log.append((asked, approve, t.reply))
        if approve:
            break
        message = colour_answer if agent.COLOUR_ID in asked else ANSWERS.get(asked[0] if asked else None,
                                                                              'תחליטו אתם על השאר')
        t = sup.turn(project_id='p', account_id='a', message=message, lang='he')
    return sup, log


class AsksColours(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1', 'OMNI_SITE_LIBRARY': 'on'})
        p.start()
        self.addCleanup(p.stop)

    def test_unknown_business_is_asked_once_before_the_approval_and_the_colours_bind(self):
        sup, log = converse('מעט כתום, בעיקר ירוק')     # the interpreter alone would put orange first
        asked_at = [i for i, (asked, _, _) in enumerate(log) if agent.COLOUR_ID in asked]
        self.assertEqual(len(asked_at), 1)
        self.assertIn(agent.COLOUR_QUESTION['he'], log[asked_at[0]][2])
        self.assertFalse(any(approve for _, approve, _ in log[:asked_at[0] + 1]))
        self.assertTrue(log[-1][1])
        brief = sup.briefs.latest('p').brief
        self.assertEqual(brief.fields['color']['value'], 'ירוק, כתום')
        self.assertIn(brief.fields['color']['source'], ('answer', 'message'))   # the customer's words, both stated
        design = next(x for x in d.requirements_text(brief).splitlines() if x.startswith('Design:'))
        self.assertIn(f"primary colour {d.palette_css('ירוק')[0]}", design)

    def test_left_to_us_takes_a_palette_we_have(self):
        sup, log = converse('תבחרו אתם')
        self.assertTrue(log[-1][1])
        brief = sup.briefs.latest('p').brief
        self.assertEqual(brief.fields['color']['value'], 'category')
        self.assertEqual(brief.fields['color']['source'], 'answer')    # "you choose" is recorded as the customer's choice
        design = next(x for x in d.requirements_text(brief).splitlines() if x.startswith('Design:'))
        self.assertIn('primary colour #', design)
        self.assertNotIn('choose a palette', design)

    def test_a_known_business_is_never_asked(self):
        _, log = converse('כחול', request=LAWYER)
        self.assertFalse(any(agent.COLOUR_ID in asked for asked, _, _ in log))

    def test_a_stated_colour_is_never_asked(self):
        _, log = converse('כחול', request=TUTOR + ' צבעים: סגול ולבן.')
        self.assertFalse(any(agent.COLOUR_ID in asked for asked, _, _ in log))

    def test_an_answer_that_is_neither_does_not_ask_again(self):
        sup, log = converse('כן')
        self.assertEqual(sum(agent.COLOUR_ID in asked for asked, _, _ in log), 1)
        self.assertTrue(log[-1][1])
        self.assertNotEqual((sup.briefs.latest('p').brief.fields.get('color') or {}).get('source'), 'answer')


class TheAnswer(unittest.TestCase):
    def test_colours_most_space_first(self):
        for answer, value in (('כחול וזהב', 'כחול, זהב'), ('בעיקר ירוק, וקצת כתום', 'ירוק, כתום'),
                              ('מעט זהב, בעיקר כחול כהה', 'כחול כהה, זהב'), ('#ff0000 ולבן', '#ff0000, לבן')):
            with self.subTest(answer):
                self.assertEqual(agent.colour_answer(answer), value)

    def test_left_to_us(self):
        for answer in ('תבחרו אתם', 'לא משנה לי', 'מה שמתאים', 'you choose', 'אין לי העדפה'):
            with self.subTest(answer):
                self.assertEqual(agent.colour_answer(answer), 'category')

    def test_neither(self):
        for answer in ('כן', 'אוקיי', 'משהו יפה'):
            with self.subTest(answer):
                self.assertIsNone(agent.colour_answer(answer))


class NothingNear(unittest.TestCase):
    def test_nothing_near_takes_the_neutral_palette_said_as_such(self):
        text = 'אתר ללהקת "גל ים". הופעות בכל הארץ.'
        self.assertEqual(V.nearest_category(text), (V.NO_SIGNAL, 0.0))
        clause = V.design_colours(text)
        name, p = V.palette_for(V.NO_SIGNAL)
        self.assertTrue(clause.startswith(f'primary colour {p["primary"]};'))
        self.assertIn(f'neutral "{name}" palette', clause)
        self.assertNotIn('choose a palette', clause)


if __name__ == '__main__':
    unittest.main()
