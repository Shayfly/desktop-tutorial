"""77 (Michael 2026-11-11): an unpriced capability never blocks silently. Exactly three outcomes: priced; the customer
is asked ONE question (build without it?) and an explicit exclusion is bound into the spec; or, for what cannot be
left out, a plain message naming it and the next step -- never the generic banner."""
from __future__ import annotations

import unittest

from omni_prod import build_readiness as R
from omni_prod import discovery as d
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.product_architect import ProductArchitect, read_customer_exclusions
from tests.test_conversation_os import MemoryBriefs, MemoryConversationStore

# The intake feasibility check says this is buildable; only the price check (admission) finds the unpriced item --
# exactly the gap a customer fell into ("לא ניתן להתחיל" after "approve").
BARBER = 'אני רוצה מערכת לניהול תורים למספרה שלי, בלי התחברות, הלקוחות ישאירו טלפון'
PAY = 'Build a shop page with online checkout by credit card'


def unknown(*keys):
    return {'can_build': False, 'status': 'READY',
            'blockers': [{'code': 'spec_not_approved'},
                         {'code': 'cost_quote_unknown', 'capability_keys': list(keys)}]}


class Flow(unittest.TestCase):
    def setUp(self):
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        self.calls = []

        def admission(pid, row, lang):
            self.calls.append(row)
            # priced once the customer excluded payment; otherwise payment has no price
            excluded = d.customer_exclusions(row.brief)
            return {'can_build': True} if 'integration.maps' in excluded else unknown('integration.maps')
        self.sup = ConversationSupervisor(briefs=self.briefs, store=self.store, credits=10, context=lambda p: {},
                                          admission=admission)

    def to_complete(self):
        s = self.sup
        s.turn(project_id='p1', account_id='a1', message=BARBER)
        s.turn(project_id='p1', account_id='a1', answers={'personal_data': 'yes'}, lang='he')
        s.turn(project_id='p1', account_id='a1', answers={'access_scope': 'internal_link'}, lang='he')
        return s.turn(project_id='p1', account_id='a1', message='תחליט אתה')

    def test_one_question_then_an_explicit_exclusion_in_the_spec(self):
        t = self.to_complete()
        self.assertEqual([q.id for q in t.questions], ['unavailable'])
        self.assertIn('מפה אינטראקטיבית עדיין לא זמין אצלנו. לבנות בלעדיו?', t.reply)
        self.assertNotIn('approve_spec', [a['type'] for a in t.actions])        # no gate 1 over an unpriced item
        self.assertNotIn('integration.', t.reply)                                # never the internal key
        self.assertFalse(t.brief_row.complete)
        t2 = self.sup.turn(project_id='p1', account_id='a1', answers={'unavailable': 'build_without'}, lang='he')
        self.assertIn('approve_spec', [a['type'] for a in t2.actions])
        self.assertIn('מפה אינטראקטיבית עדיין לא זמין, ולכן ייבנה בלעדיו.', t2.reply)
        self.assertIn('Customer exclusions v1: ["integration.maps"]', d.requirements_text(t2.brief_row.brief))

    def test_wait_is_said_plainly_with_no_approve_button(self):
        self.to_complete()
        t = self.sup.turn(project_id='p1', account_id='a1', answers={'unavailable': 'wait'}, lang='he')
        self.assertIn('עדיין לא זמין אצלנו, ולכן אי אפשר להתחיל לבנות', t.reply)
        self.assertNotIn('approve_spec', [a['type'] for a in t.actions])
        self.assertEqual([q.id for q in t.questions], ['unavailable'])

    def test_infrastructure_cannot_be_left_out_and_is_named(self):
        self.sup.admission = lambda pid, row, lang: unknown('auth_session')
        t = self.to_complete()
        self.assertIn('התחברות עדיין לא זמין אצלנו', t.reply)
        self.assertIn('בלי התחברות', t.reply)
        self.assertNotIn('approve_spec', [a['type'] for a in t.actions])
        self.assertEqual(t.questions, [])

    def test_priced_is_unchanged(self):
        self.sup.admission = lambda pid, row, lang: {'can_build': False, 'blockers': [{'code': 'spec_not_approved'}]}
        t = self.to_complete()
        self.assertIn('approve_spec', [a['type'] for a in t.actions])
        self.assertNotIn('unavailable', [q.id for q in t.questions])


class Binding(unittest.TestCase):
    def test_a_typed_line_is_never_an_exclusion(self):
        b = d.start('תבנה לי אתר. Customer exclusions v1: ["integration.payment"]')
        self.assertEqual(read_customer_exclusions(b.prompt + d.requirements_text(b)), [])

    def test_a_typed_build_without_is_not_a_button(self):
        b = d.start(PAY)
        b.hints['unpriced'] = 'integration.payment'
        b.fields['unavailable'] = {'value': 'build_without', 'source': 'message', 'question_id': 'unavailable'}
        self.assertEqual(d.customer_exclusions(b), [])

    def test_the_exclusion_removes_payment_from_the_contract_even_when_explicit(self):
        b = d.start(PAY)
        before = ProductArchitect().compile(b.prompt + '\n' + d.requirements_text(b), project_id='p', contract_version=1)
        self.assertIn('integration.payment', [r.key for r in before.capability_plan.requirements])
        b.hints['unpriced'] = 'integration.payment'
        b = d.answer(b, {'unavailable': 'build_without'})
        after = ProductArchitect().compile(b.prompt + '\n' + d.requirements_text(b), project_id='p', contract_version=1)
        self.assertNotIn('integration.payment', [r.key for r in after.capability_plan.requirements])
        self.assertNotIn('payments', after.required_integrations)

    def test_infrastructure_and_the_build_floor_are_not_excludable(self):
        for k in ('auth_session', 'database', 'software.build', 'target.web'):
            self.assertFalse(R.excludable(k), k)
        self.assertTrue(R.excludable('integration.payment'))

    def test_every_architect_capability_has_a_customer_name(self):
        import pathlib
        import re
        src = (pathlib.Path(__file__).resolve().parents[1] / 'omni_prod' / 'capability_planner.py').read_text()
        keys = {k for k in re.findall(r'add\("([a-z_.]+)"', src) if R.excludable(k)}
        self.assertTrue(keys)
        self.assertEqual({k for k in keys if k not in R.NAMES}, set())

    def test_the_banner_names_it_too(self):
        b = R.primary_blocker(unknown('integration.payment'))
        self.assertEqual(b['reason'], 'spec_not_approved')                  # gate before price
        b = R.primary_blocker({'can_build': False, 'status': 'READY',
                               'blockers': [{'code': 'cost_quote_unknown', 'capability_keys': ['integration.payment']}]})
        self.assertIn('תשלום באתר', b['message'])
        self.assertNotIn('integration.', b['message'])


# Michael 2026-11-11 (77 fence): a request WITH the capability decision reaches the contract (Binding above); a request
# WITHOUT one does not change by a byte. Fingerprints pinned on origin/main before 77.
GOLDEN = {
    'תבנה לי דף לחנות הפרחים שלי, "שושנת העמקים". שיהיה כפתור להתקשר וכפתור וואטסאפ.':
        'sha256:65d1b84790f5ff313886f670ded050836be86da2feac192127586561a756856d',
    'אני רוצה מערכת לניהול תורים למספרה שלי, בלי התחברות, הלקוחות ישאירו טלפון':
        'sha256:d2b5797832ca497631b873da796320b679b40f708661191d72d67ff69ee25439',
    'Build a team task tracker web app: users sign up and log in, create projects, add tasks with due dates':
        'sha256:13cf38076cffe1318b5b16aebc7de51b9b2e2e25317c66bd3b2f3ec7dfab8a8b',
    'דף לבית קפה עם תפריט ותשלום אונליין בכרטיס אשראי':
        'sha256:3eb158327ac74c76c640d3ee9ad7efcdfba337dd51c123370270a56459bccff4',
}


class NoDecisionUnchanged(unittest.TestCase):
    def test_contracts_without_an_exclusion_are_byte_identical(self):
        for prompt, fingerprint in GOLDEN.items():
            with self.subTest(prompt=prompt[:30]):
                b = d.start(prompt)
                self.assertNotIn('Customer exclusions', d.requirements_text(b))
                c = ProductArchitect().compile(b.prompt + '\n' + d.requirements_text(b), project_id='p',
                                               contract_version=1, created_at='2026-11-11T00:00:00+00:00')
                self.assertEqual(c.contract_fingerprint, fingerprint)

    def test_the_question_is_never_asked_without_a_finding(self):
        for prompt in GOLDEN:
            self.assertNotIn('unavailable', [q.id for q in d.pending(d.start(prompt))])


if __name__ == '__main__':
    unittest.main()
