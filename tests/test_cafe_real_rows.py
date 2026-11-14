"""#335, the real path (Michael 2026-11-13: "the test is the bug -- now it runs on the real database").

The rows are the production cafe project (prj_tEyyuyyWNZRpiw, 2026-11-12) exported read-only from the production
database: the brief at revision 15 and all 40 conversation rows (tests/fixtures/cafe_prj_tEyyuyyWNZRpiw.json; the
brief reproduces the stored fingerprint, checked below). The customer GAVE the phone and the hours in messages 2-4;
the "מה נכון?" loop lost them, the spec was approved without them, and the build invented hours and a dead button.

Expected now (Michael): the phone and hours come from the stored messages, no repeated question, no invention --
and the approval made on 2026-11-12 no longer admits a build.

VARIANT rows (labelled): the same rows without the customer's fact messages -- a customer who really never gave
them. There the gate asks, the tick records the waiver, and only then the spec says to omit."""
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.fact_canon import MISSING_PREFIX, needs_customer_input
from omni_prod.intake import approval_flow as AF
from omni_prod.skills_runtime import _invented_contact
from tests.test_conversation_os import MemoryBriefs

FX = json.loads((Path(__file__).parent / 'fixtures' / 'cafe_prj_tEyyuyyWNZRpiw.json').read_text(encoding='utf-8'))
FACT_MESSAGES = ('03-1234567', '07:00–19:00')          # the customer messages that state the phone / the hours
SPANS = ['03-1234567', 'א׳–ה׳ 07:00–19:00', 'ו׳ 07:00–14:00', 'שבת סגור']
# what build bld_cf406df6 served for this project on 2026-11-12
BUILT = ('<html dir="rtl"><body><h1>בית קפה קטן</h1><a href="#">הזמנת שולחן</a><h2>שעות פתיחה</h2>'
         '<p>ראשון - חמישי</p><p>07:30 - 18:00</p><p>שישי</p><p>07:30 - 14:00</p><p>שבת</p><p>08:00 - 16:00</p></body></html>')
RIGHT = ('<html dir="rtl"><body><h1>בית קפה קטן</h1><a href="tel:03-1234567">הזמנת שולחן</a><h2>שעות פתיחה</h2>'
         '<p>א׳–ה׳ 07:00–19:00</p><p>ו׳ 07:00–14:00</p><p>שבת סגור</p></body></html>')


class Rows(unittest.TestCase):
    drop = ()

    def setUp(self):
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        self.briefs.rows['p'] = [MemoryBriefs.Row(FX['revision'], d.Brief.from_dict(FX['brief']))]
        for m in FX['messages']:
            if m['role'] == 'customer' and any(x in m['content'] for x in self.drop):
                continue
            self.store.add_message(project_id='p', account_id='a', role=m['role'], content=m['content'],
                                   interpretation=m['interpretation'])
        self.s = ConversationSupervisor(briefs=self.briefs, store=self.store)
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'})
        p.start()
        self.addCleanup(p.stop)

    def row(self):
        return self.briefs.latest('p')

    def messages(self):
        return self.store.messages_for('p', limit=500)

    def approve(self, fingerprint=None, **kw):
        return self.s.approve_spec(project_id='p', account_id='a', lang='he',
                                   brief_fingerprint=fingerprint or self.row().fingerprint, **kw)

    def spec_lines(self):
        return d.requirements_text(self.row().brief).splitlines()


class TheCafeAsItIsInProduction(Rows):
    def test_the_rows_are_the_production_rows(self):
        self.assertEqual(self.row().fingerprint, FX['fingerprint'])              # the export is faithful
        self.assertEqual(len(FX['messages']), 40)
        self.assertTrue(AF.spec_approved(self.messages(), FX['fingerprint']))    # approved on 2026-11-12 ...
        self.assertIsNone(self.row().brief.assets.get('facts'))                  # ... with the facts lost

    def test_the_old_approval_does_not_admit_a_build(self):
        # build admission (investor_app._bind_execution_plan) and the conversation use this one rule
        self.assertEqual(AF.spec_invalid_reason(self.row().brief, self.messages(), FX['fingerprint']),
                         'facts_not_collected')
        self.assertFalse(self.s._spec_ok('p', self.row()))

    def test_the_facts_come_from_the_stored_messages_and_nothing_is_asked_again(self):
        t = self.approve(FX['fingerprint'])                  # the customer presses the old "approve" again
        facts = self.row().brief.assets['facts']
        self.assertEqual(facts['spans'], SPANS)
        self.assertEqual(facts['needs'], ['phone'])          # "יפתח חיוג" was said in message 2, not in the request
        self.assertEqual(self.row().revision, FX['revision'] + 1)
        self.assertNotEqual(self.row().fingerprint, FX['fingerprint'])
        self.assertIn('טלפון: 03-1234567', t.reply)          # gate 1 again, with the customer's own facts
        self.assertIn('שעות: א׳–ה׳ 07:00–19:00, ו׳ 07:00–14:00, שבת סגור', t.reply)
        for question in ('מה מספר הטלפון?', 'מה שעות הפתיחה?', 'לא כתבתם'):
            self.assertNotIn(question, t.reply)              # no repeated question to a customer who answered
        [action] = [a for a in t.actions if a['type'] == 'approve_spec']
        self.assertEqual(action['canon']['status'], 'OK')    # no box to tick: nothing is missing
        self.assertFalse(self.s._spec_ok('p', self.row()))   # not approved until the customer approves THIS spec

    def test_after_approving_the_current_spec_it_builds_from_the_customers_facts(self):
        self.approve(FX['fingerprint'])
        self.approve()
        self.assertIsNone(AF.spec_invalid_reason(self.row().brief, self.messages(), self.row().fingerprint))
        lines = self.spec_lines()
        [facts] = [ln for ln in lines if ln.startswith(d.CUSTOMER_FACTS_PREFIX)]
        for span in SPANS:
            self.assertIn(span, facts)
        self.assertTrue(any(ln.startswith('Call button:') and 'tel: link to +97231234567' in ln for ln in lines))
        self.assertFalse(any(ln.startswith((MISSING_PREFIX, 'Not given by the customer')) for ln in lines))

    def test_zero_inventions_the_page_of_2026_11_12_is_blocked_and_the_right_page_passes(self):
        self.approve(FX['fingerprint'])
        request = self.row().brief.prompt + '\n' + d.requirements_text(self.row().brief)
        found = [f.problem for f in _invented_contact({'index.html': BUILT}, {'request': request})
                 if f.severity == 'blocking']
        self.assertTrue(any('contradict' in p and 'שבת: הדף 08:00-16:00, הלקוח סגור' in p for p in found), found)
        self.assertEqual(_invented_contact({'index.html': RIGHT}, {'request': request}), [])

    def test_collecting_is_done_once(self):
        self.approve(FX['fingerprint'])
        revision = self.row().revision
        self.approve(FX['fingerprint'])                      # a second pass over the same messages changes nothing
        self.s.turn(project_id='p', account_id='a', lang='he', message='מה המצב?')
        self.assertEqual(self.row().brief.assets['facts']['spans'], SPANS)
        self.assertLessEqual(self.row().revision, revision + 1)


class VariantTheCustomerNeverGaveThem(Rows):
    """VARIANT of the production rows: without the customer's fact messages (a customer who never gave them)."""
    drop = FACT_MESSAGES

    def test_the_gate_asks_and_the_old_approval_does_not_stand(self):
        t = self.approve(FX['fingerprint'])                  # pressing the old "approve" again, without the tick
        self.assertEqual(d.missing_facts(self.row().brief)[0], ['hours'])
        self.assertIn('מה שעות הפתיחה?', t.reply)
        self.assertIn('סמנו את התיבה', t.reply)              # cannot approve without the fact or the tick
        self.assertFalse(self.s._spec_ok('p', self.row()))   # the 2026-11-12 approval is still not valid

    def test_without_a_waiver_the_spec_never_says_omit_and_the_old_approval_is_invalid(self):
        self.assertEqual(AF.spec_invalid_reason(self.row().brief, self.messages(), FX['fingerprint']),
                         'missing_facts_not_waived')
        lines = self.spec_lines()
        self.assertTrue(any(ln.startswith(MISSING_PREFIX) and 'hours' in ln for ln in lines))
        self.assertFalse(any(ln.startswith('Not given by the customer') for ln in lines))
        # (d) on the spec the build would really get: QA refusing invented hours stops the repairs and asks
        prompt = self.row().brief.prompt + '\n' + d.requirements_text(self.row().brief)
        invented = 'QA review (skill.copy_quality): opening hours the customer never gave (invented): שבת 08:00-16:00'
        self.assertEqual(needs_customer_input([invented], prompt), ['hours'])

    def test_the_tick_records_the_waiver_and_only_then_the_spec_omits(self):
        self.approve(FX['fingerprint'])
        before = self.row().fingerprint
        self.approve(canon_ack=True)                          # the customer ticks "build without"
        self.assertEqual(self.row().brief.assets['facts']['waived'], ['hours'])
        self.assertNotEqual(self.row().fingerprint, before)   # the waiver is part of the approved spec
        approval = [m for m in self.messages() if (m.get('interpretation') or {}).get('spec_approved')][-1]
        self.assertEqual(approval['interpretation']['spec_approved'], self.row().fingerprint)
        self.assertEqual(approval['interpretation']['waived'], ['hours'])
        self.assertIsNone(AF.spec_invalid_reason(self.row().brief, self.messages(), self.row().fingerprint))
        lines = self.spec_lines()
        self.assertTrue(any(ln.startswith('Not given by the customer') and 'opening hours' in ln for ln in lines))
        self.assertFalse(any(ln.startswith(MISSING_PREFIX) for ln in lines))
        prompt = self.row().brief.prompt + '\n' + d.requirements_text(self.row().brief)
        invented = 'QA review (skill.copy_quality): opening hours the customer never gave (invented): שבת 08:00-16:00'
        self.assertEqual(needs_customer_input([invented], prompt), [])     # waived: repaired (removed), not asked

    def test_giving_the_fact_later_answers_it(self):
        self.approve(FX['fingerprint'])
        self.s.turn(project_id='p', account_id='a', lang='he', message='שעות: א׳–ה׳ 07:00–19:00, שבת סגור')
        self.assertEqual(d.missing_facts(self.row().brief), ([], []))


if __name__ == '__main__':
    unittest.main()
