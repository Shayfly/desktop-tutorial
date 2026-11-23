"""The spec the customer approves, as a card (the owner's example, 2026-11-23: "זה מה שנבנה").

Production, the owner's screenshot (2026-11-22 23:47, project "בדיקה 118 – סטודיו נועה"): the approval was one paragraph
and every business detail appeared twice -- the starting-content field repeated the phone and the hours, and the canon
line listed them again. The card carries every part of the message once: fields as rows, business details from the
canon (the customer's words), warnings, the price line and the next step.
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod.conversation import spec_card as C

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_rehearsal import Scripted  # noqa: E402

# the owner's screenshot, word for word
CONTENT = 'טלפון 03-5551234; שעות פעילות א׳–ה׳ 09:00–19:00, ו׳ 08:00–13:00; שירותים: תספורת, פן וצבע'
CANON = ('פרטי העסק שיופיעו באתר (מתוך מה שכתבתם): טלפון: 03-5551234; טלפון: 0503456723; '
         'כתובת: רחוב הרצל 12, חולון; שעות: א׳–ה׳ 09:00–19:00, ו׳ 08:00–13:00.')
WARNING = 'אזהרה: לא כתבתם טלפון או כתובת. בלי זה הם לא יופיעו באתר (לא נמציא אותם). אפשר להוסיף עכשיו בהודעה, או לאשר בלעדיהם.'


def owner_card(canon_lines=(CANON,)):
    return C.card(stage='שלב 1 מתוך 2', lang='he', excluded=[], canon_lines=list(canon_lines),
                  price='הבנייה הזו תוריד 500 מהיתרה שלכם.', next_step='אם זה נכון, לחצו על "כן, זה נכון".',
                  rows=[('שם העסק', 'סטודיו נועה', False), ('תוכן התחלתי', CONTENT, False), ('צבע', 'ורוד', True)])


def shown_text(card):
    return ' | '.join([*(r['value'] for r in card['rows']), *(f['value'] for f in card['facts']), *card['notes']])


class EachDetailOnce(unittest.TestCase):
    def test_the_owners_screenshot_shows_each_detail_once(self):
        card = owner_card()
        self.assertEqual([f['label'] for f in card['facts']], ['טלפון', 'טלפון', 'כתובת', 'שעות'])
        text = shown_text(card)
        for detail in ('03-5551234', '0503456723', 'רחוב הרצל 12, חולון', 'א׳–ה׳ 09:00–19:00'):
            self.assertEqual(text.count(detail), 1, detail)
        content = next(r for r in card['rows'] if r['label'] == 'תוכן התחלתי')
        self.assertEqual(content['value'], 'שירותים: תספורת, פן וצבע')     # what is not a detail stays

    def test_nothing_the_message_says_is_lost(self):
        card = owner_card()
        self.assertEqual([r['label'] for r in card['rows']], ['שם העסק', 'תוכן התחלתי', 'צבע'])
        self.assertTrue(card['rows'][2]['default'])                         # "(ברירת מחדל בטוחה)" becomes a tag
        self.assertEqual(card['price'], 'הבנייה הזו תוריד 500 מהיתרה שלכם.')
        self.assertIn('כן, זה נכון', card['next'])

    def test_a_warning_is_never_dropped(self):
        card = owner_card(canon_lines=(WARNING,))
        self.assertEqual(card['facts'], [])
        self.assertEqual(card['notes'], [WARNING])
        self.assertIn('03-5551234', shown_text(card))                       # no canon facts: the content keeps them

    def test_a_line_of_another_shape_stays_text(self):
        self.assertIsNone(C._facts_from_line('פרטי העסק שיופיעו באתר (מתוך מה שכתבתם): משהו בלי תווית.', 'he'))
        card = owner_card(canon_lines=('שורה אחרת.',))
        self.assertEqual(card['notes'], ['שורה אחרת.'])


class OnTheRealPath(unittest.TestCase):
    """The conversation, run to gate 1: the approve_spec action carries the card, and the card says what the
    message says."""

    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1', 'OMNI_SITE_LIBRARY': 'on'})
        p.start()
        self.addCleanup(p.stop)

    ANSWERS = {'personal_data': 'לא', 'content_only': 'כן, אתר תוכן בלבד, לא שומרים כלום'}
    maxDiff = None

    def gate1(self, request):
        """Answers each question the conversation asks (as tests/test_agent_asks_the_business_name.py does)."""
        sup = R._Supervisor(Scripted())
        t = sup.turn(project_id='p', account_id='a', message=request, lang='he')
        for _ in range(12):
            spec = next((a for a in t.actions if a['type'] == 'approve_spec'), None)
            if spec:
                return t, spec
            asked = list(getattr(t, 'asked_in_words', None) or [q.id for q in t.questions])
            t = sup.turn(project_id='p', account_id='a', lang='he',
                         message=self.ANSWERS.get(asked[0] if asked else None, 'תחליטו אתם על השאר'))
        self.fail('the conversation never reached gate 1')

    def test_the_approval_carries_the_card(self):
        t, spec = self.gate1('שם העסק: סטודיו נועה. אתר תדמית למספרה. טלפון 03-5551234. כתובת: רחוב הרצל 12, חולון. '
                             'שעות פעילות א׳–ה׳ 09:00–19:00. אתר תוכן בלבד, לא שומרים כלום.')
        card = spec.get('card')
        self.assertIsNotNone(card)
        message = t.reply
        self.assertEqual(card['stage'], 'שלב 1 מתוך 2')
        self.assertTrue(card['rows'])
        self.assertIn('03-5551234', [f['value'] for f in card['facts']])
        self.assertEqual(shown_text(card).count('03-5551234'), 1)
        self.assertIn(card['price'], message)                               # the card says what the message says
        self.assertIn(card['next'], message)
        for note in card['notes']:
            self.assertIn(note, message)



class TheScreensFixture(unittest.TestCase):
    """tests/spec_card_browser.cjs shows the card the server builds: its fixture is this module's owner_card()."""

    def test_the_fixture_is_what_the_server_builds(self):
        import json
        from pathlib import Path
        fixture = json.loads((Path(__file__).parent / 'fixtures' / 'spec_card_owner.json').read_text(encoding='utf-8'))
        self.assertEqual(fixture['card'], owner_card())


class PlainWords(unittest.TestCase):
    def test_the_builders_default_is_said_in_plain_words(self):
        default = 'אזורים בהתאם לבקשת הלקוח; אין להוסיף מסכי ניהול או CRUD שלא התבקשו'
        card = C.card(stage='שלב 1 מתוך 2', lang='he', excluded=[], canon_lines=[], price='', next_step='',
                      rows=[('מסכים', default, False)])
        self.assertEqual(card['rows'][0]['value'], 'רק החלקים שביקשתם, בלי מסכי ניהול שלא ביקשתם')
        self.assertNotIn('CRUD', shown_text(card))


class TheMessageToo(OnTheRealPath):
    """The owner's screenshot was the MESSAGE: its summary now says each business detail once as well, because it is
    built from the card's rows. The details themselves stay in the canon line of the same message. Inherits
    OnTheRealPath's setUp and gate1 (and re-runs its own case, which is cheap and proves the card is still there)."""

    def test_the_message_says_each_detail_once_and_loses_nothing(self):
        request = ('שם העסק: סטודיו נועה. אתר תדמית למספרה. טלפון 03-5551234. כתובת: רחוב הרצל 12, חולון. '
                   'שעות פעילות א׳–ה׳ 09:00–19:00, ו׳ 08:00–13:00. אתר תוכן בלבד, לא שומרים כלום.')
        t, spec = self.gate1(request)
        for detail in ('03-5551234', 'רחוב הרצל 12', '09:00–19:00'):
            self.assertEqual(t.reply.count(detail), 1, detail)       # once, not twice
            self.assertIn(detail, t.reply)                           # and never lost
        self.assertNotIn('CRUD', t.reply)
        for row in spec['card']['rows']:                             # every row of the card is in the message
            self.assertIn(f"{row['label']}: {row['value']}", t.reply)


class TheBrowserCheckRuns(unittest.TestCase):
    def test_the_browser_check_runs_in_ci(self):
        from pathlib import Path
        ci = (Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8')
        self.assertIn('      - run: node tests/spec_card_browser.cjs\n', ci)
        self.assertIn('node --check tests/spec_card_browser.cjs', ci)


if __name__ == '__main__':
    unittest.main()
