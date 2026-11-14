"""Michael 2026-11-14 (b5): gate 1 is not shown while the build contract compiled from the brief still has an open
question.

Real rows: the butcher's brief at revision 4, exported from production (tests/fixtures/butcher_prj_fV8kB7FwuNimGw.json,
fingerprint checked below). On 2026-11-13 13:35 discovery had nothing pending (personal_data stayed "yes" after
access_scope "no_personal", so content_only was never asked), gate 1 was shown, the customer approved three times, and
gate 2 refused each time with "האם האתר שומר מידע? ענו על השאלה בשיחה" -- with no card to answer. The contract the
admission compiles (ProductArchitect on investor_app._brief_prompt) was NEEDS_CLARIFICATION all along.

Expected now: gate 1 is held and the question is asked; the approve button from the old turn plans nothing; after the
customer's two answers of 13:41 (personal_data: no, then the content_only card: yes) gate 1 comes, and its approval plans."""
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs

FX = json.loads((Path(__file__).parent / 'fixtures' / 'butcher_prj_fV8kB7FwuNimGw.json').read_text(encoding='utf-8'))
REV4 = FX['revision_4']


def kinds(turn):
    return [a['type'] for a in turn.actions]


class Gate1WaitsForTheContract(unittest.TestCase):
    def setUp(self):
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        self.briefs.rows['p'] = [MemoryBriefs.Row(REV4['revision'], d.Brief.from_dict(REV4['brief']))]
        self.s = ConversationSupervisor(briefs=self.briefs, store=self.store)
        patcher = mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'})
        patcher.start()
        self.addCleanup(patcher.stop)

    def turn(self, **kw):
        return self.s.turn(project_id='p', account_id='a', lang='he', **kw)

    def approve(self, fingerprint):
        return self.s.approve_spec(project_id='p', account_id='a', lang='he', brief_fingerprint=fingerprint)

    def test_the_export_is_faithful_and_reproduces_the_gap(self):
        row = self.briefs.latest('p')
        self.assertEqual(row.fingerprint, REV4['fingerprint'])
        self.assertTrue(row.complete)                                         # discovery: nothing pending
        self.assertEqual([q.id for q in self.s._contract_open(row)], ['persistence'])   # the contract: open

    def test_gate1_is_held_while_the_contract_asks(self):
        t = self.turn(answers={'style': 'warm'})                              # the 13:35 turn
        self.assertIsNone(t.gate)
        self.assertNotIn('approve_spec', kinds(t))
        self.assertNotIn('שלב 1 מתוך 2', t.reply)
        self.assertIn('האם האתר שומר מידע?', t.reply)
        self.assertEqual(t.interpretation.get('gate1_held'), ['persistence'])

    def test_the_old_approve_button_plans_nothing(self):
        t = self.approve(REV4['fingerprint'])                                 # the button of 13:35, pressed at 13:35:14
        self.assertIsNone(t.plan_id)
        self.assertNotIn('show_plan', kinds(t))
        self.assertNotIn('approve_build', kinds(t))
        self.assertIn('האם האתר שומר מידע?', t.reply)
        stored = self.store.messages_for('p', limit=10)[-2]
        self.assertIn('spec_approval_refused', stored['interpretation'])

    def test_after_the_customers_answers_gate1_comes_and_plans(self):
        self.turn(answers={'style': 'warm'})
        t = self.turn(answers={'personal_data': 'no'})                         # 13:41:01
        self.assertEqual([q.id for q in t.questions], ['content_only'])        # with its card
        t = self.turn(answers={'content_only': 'yes'})                         # 13:41:14
        row = self.briefs.latest('p')
        self.assertEqual(self.s._contract_open(row), [])
        self.assertEqual(t.gate, 'spec')
        self.assertIn('approve_spec', kinds(t))
        t = self.approve(row.fingerprint)
        self.assertIsNotNone(t.plan_id)
        self.assertNotIn('ענו על השאלה בשיחה', t.reply)


if __name__ == '__main__':
    unittest.main()
