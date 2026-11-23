"""The first agent's summary and words (the owner, 2026-11-23: "לא רוצה בוט ... סוכן ... שידע להבין את הלקוח בשפה הכי פשוטה
ולהפוך את המלל בינהם לתוצאה מעולה").

On the real conversation path (the supervisor that production runs, with the scripted customer of the existing gate-1
tests):
  * the summary card leads with what the customer cares about -- goal, parts, content, look -- and never with
    "גופן: Heebo", "תאריכים: אין תאריכים" or "התחברות: בלי התחברות";
  * a site that keeps nothing says so in plain words;
"""
from __future__ import annotations

import os
import sys
import unittest

from omni_prod import discovery as d
from omni_prod.conversation.supervisor import SUMMARY_FIELDS, _PRIVACY_ROW, _TXT

sys.path.insert(0, os.path.dirname(__file__))
from test_spec_card import OnTheRealPath  # noqa: E402

REQUEST = ('שם העסק: סטודיו נועה. אתר תדמית למספרה. טלפון 03-5551234. כתובת: רחוב הרצל 12, חולון. '
           'שעות פעילות א׳–ה׳ 09:00–19:00. אתר תוכן בלבד, לא שומרים כלום.')


class TheSummaryLeadsWithWhatMatters(OnTheRealPath):
    def card(self):
        _, spec = self.gate1(REQUEST)
        return spec['card']

    def test_no_technical_rows(self):
        labels = [r['label'] for r in self.card()['rows']]
        for technical in ('גופן', 'תאריכים', 'התחברות', 'כפילויות', 'השראה'):
            self.assertNotIn(technical, labels)

    def test_the_rows_follow_the_customers_order(self):
        labels = [r['label'] for r in self.card()['rows']]
        order = ['מטרה', 'מסכים', 'תוכן התחלתי', 'צבע', 'סגנון', 'לוגו']
        shown = [x for x in order if x in labels]
        self.assertEqual(shown, [x for x in labels if x in order])
        self.assertIn('מטרה', labels)

    def test_a_site_that_keeps_nothing_says_so_plainly(self):
        rows = {r['label']: r['value'] for r in self.card()['rows']}
        self.assertEqual(rows.get(_PRIVACY_ROW['he'][0]), _PRIVACY_ROW['he'][1])

    def test_the_summary_fields_are_the_owners_order(self):
        self.assertEqual(SUMMARY_FIELDS, ('goal', 'screens', 'content', 'color', 'style', 'logo'))


class OneNaturalCheck(unittest.TestCase):
    def test_a_real_conflict_is_one_plain_question(self):
        self.assertNotIn('לא שיניתי', _TXT['he']['conflict'])
        self.assertNotIn('קודם נקבע', _TXT['he']['conflict'])
        self.assertIn('רק לוודא', _TXT['he']['conflict'])


class TheAgentSpeaksOnce(OnTheRealPath):
    """GOA, 16:39 (rev 5): the model's own words, then "הבנתי: צבע: צבעים בהשראת בוב מארלי.", then the summary. When the
    model already said what it understood, the field-label list is not said again under it."""

    REPLY = 'מעולה, אתר תדמית לסטודיו נועה עם הפרטים ששלחתם.'

    def test_no_field_list_under_the_models_own_words(self):
        from omni_prod import conversation_rehearsal as R
        from test_conversation_rehearsal import Scripted
        reply = self.REPLY

        from omni_prod.intake.interpreter import Proposal

        class WithWords(Scripted):
            # as the model in GOA rev 5: it reads the colour from the customer's words (origin 'model'), over the
            # default, and says what it understood in its own words
            def interpret(self, message, brief=None):
                out = super().interpret(message, brief)
                out.reply = reply
                if 'בוב מארלי' in message:
                    out.proposals = [x for x in out.proposals if x.field != 'color'] + [
                        Proposal('color', 'צבעים בהשראת בוב מארלי', 'high', message[:40], 'model')]
                return out

        sup = R._Supervisor(WithWords())
        t = sup.turn(project_id='p', account_id='a', message=REQUEST, lang='he')
        for _ in range(12):
            if any(a['type'] == 'approve_spec' for a in t.actions):
                break
            asked = list(getattr(t, 'asked_in_words', None) or [q.id for q in t.questions])
            t = sup.turn(project_id='p', account_id='a', lang='he',
                         message=self.ANSWERS.get(asked[0] if asked else None, 'תחליטו אתם על השאר'))
        self.assertTrue(any(a['type'] == 'approve_spec' for a in t.actions), 'never reached the summary')
        # as GOA: a detail said on the summary's turn (the colour), with the model's own words
        t = sup.turn(project_id='p', account_id='a', message='צבעים של בוב מארלי', lang='he')
        self.assertTrue(t.interpretation and t.interpretation.get('interpreter', '').startswith('model'))
        self.assertIn(reply, t.reply)
        self.assertNotIn(_TXT['he']['got'] + ': ', t.reply)


if __name__ == '__main__':
    unittest.main()
