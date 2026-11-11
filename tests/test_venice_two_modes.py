"""agent.venice: one person, two modes -- understanding, then planning -- with a hard buffer, and a separate plan
verifier (owner decision 2026-10-26). (a) no plan before an approved spec; (b) the mode switch is a visible stage;
(c) an external verifier rejects a plan that does not answer the spec; (d) a cost range is shown while understanding."""
import unittest
from types import SimpleNamespace as P

from omni_prod.intake.gaps import Spec
from omni_prod.intake.plan_verifier import PlanVerifier
from omni_prod.intake.venice import PLANNING, UNDERSTANDING, PlanningBeforeApproval, Venice

SITE = 'אני רוצה אתר למספרה שלי'


def listening(message=SITE, reply='תחליט אתה'):
    """Venice listens until nothing material is open: each question is answered with "you decide"."""
    from omni_prod.intake.gaps import Questioner
    v = Venice(Spec('website'))
    v.hear(message)
    while v.spec.detect()['missing_material']:
        Questioner().next(v.spec)
        v.hear(reply)
    return v


class A_NoPlanBeforeApprovedSpec(unittest.TestCase):
    def test_no_plan_while_listening(self):
        v = Venice(Spec('website'))
        v.hear(SITE)
        with self.assertRaises(PlanningBeforeApproval):
            v.plan()

    def test_no_freeze_while_a_material_field_is_open(self):
        v = Venice(Spec('website'))
        v.hear(SITE)
        with self.assertRaises(PlanningBeforeApproval):
            v.freeze()

    def test_frozen_but_not_approved_is_still_no_plan(self):
        v = listening()
        v.freeze()
        with self.assertRaises(PlanningBeforeApproval):
            v.plan()

    def test_approval_of_another_fingerprint_is_refused(self):
        v = listening()
        v.freeze()
        with self.assertRaises(PlanningBeforeApproval):
            v.approve('0' * 16)

    def test_a_change_after_approval_drops_back_to_listening(self):
        v = listening()
        v.approve(v.freeze())
        v.hear('בעצם בסגנון חם', [P(field='style', value='warm', evidence='בסגנון חם', confidence='high')])
        self.assertEqual(v.mode, UNDERSTANDING)
        with self.assertRaises(PlanningBeforeApproval):
            v.plan()


class B_TheSwitchIsAVisibleStage(unittest.TestCase):
    def test_stages_are_shown_to_the_customer_as_one_person(self):
        v = listening()
        self.assertEqual([s['mode'] for s in v.stages], [UNDERSTANDING])
        self.assertIn('שלב 1 מתוך 2', v.view()['stage']['text'])
        v.approve(v.freeze())
        self.assertEqual([s['mode'] for s in v.stages], [UNDERSTANDING, PLANNING])
        self.assertIn('שלב 2 מתוך 2', v.view()['stage']['text'])
        self.assertEqual(v.view()['agent'], 'agent.venice')                    # one person, not two agents
        self.assertEqual(v.plan()['agent'], 'agent.venice')


class C_AnExternalVerifierRejectsAPlanThatDoesNotAnswerTheSpec(unittest.TestCase):
    def setUp(self):
        self.v = listening()
        self.fp = self.v.freeze()
        self.v.approve(self.fp)
        self.plan = self.v.plan()
        self.values = self.v.spec.resolved()

    def check(self, plan):
        return PlanVerifier().verify(spec_fingerprint=self.fp, spec_values=self.values, plan=plan)

    def test_the_plan_venice_made_is_accepted(self):
        self.assertTrue(self.check(self.plan).accepted, self.check(self.plan).problems)

    def test_missing_extra_changed_unsourced_or_wrong_spec_are_rejected(self):
        dropped = {**self.plan, 'items': self.plan['items'][1:]}
        extra = {**self.plan, 'items': self.plan['items'] + [{'requirement': 'payments', 'value': 'yes', 'source': 'customer'}]}
        changed = {**self.plan, 'items': [{**self.plan['items'][0], 'value': 'something else'}] + self.plan['items'][1:]}
        unsourced = {**self.plan, 'items': [{**self.plan['items'][0], 'source': None}] + self.plan['items'][1:]}
        other = {**self.plan, 'spec_fingerprint': 'f' * 16}
        for name, plan in (('dropped', dropped), ('extra', extra), ('changed', changed), ('unsourced', unsourced),
                           ('other spec', other)):
            with self.subTest(name):
                verdict = self.check(plan)
                self.assertFalse(verdict.accepted)
                self.assertTrue(verdict.problems)

    def test_the_verifier_is_a_separate_agent(self):
        self.assertEqual(PlanVerifier.agent, 'agent.plan_verifier')
        import omni_prod.intake.plan_verifier as pv
        self.assertNotIn('venice', pv.__dict__)                               # it reads data, not Venice


class D_CostRangeWhileUnderstanding(unittest.TestCase):
    def test_a_range_is_said_on_the_first_turn_in_the_customers_language(self):
        for msg, word in ((SITE, 'קרדיטים'), ('أريد موقعًا لصالون الحلاقة الخاص بي', 'رصيدًا'),
                          ('I want a website for my barbershop', 'credits')):
            v = Venice(Spec('website'))
            view = v.hear(msg)
            self.assertEqual(view['mode'], UNDERSTANDING)
            lo, hi = view['cost_range_credits']
            self.assertLess(lo, hi)                                           # a range, not a single "easy"
            self.assertIn(f'{lo}–{hi}', view['cost_text'])
            self.assertIn(word, view['cost_text'])

    def test_the_range_widens_when_the_request_needs_more(self):
        simple = Venice(Spec('web_app'))
        simple.hear('I need an internal tool for my team')
        stored = Venice(Spec('web_app'))
        stored.hear('I need a booking app where customers leave a phone number',
                    [P(field='personal_data', value='yes', evidence='phone number', confidence='high')])
        self.assertGreater(stored.view()['cost_range_credits'][1], simple.view()['cost_range_credits'][0])


class TheRegistrySaysOnePersonAndASeparateVerifier(unittest.TestCase):
    def test_registry(self):
        from omni_prod.agents_registry import build_canonical_agents_registry
        from omni_prod.capability_registry import CapabilityRegistry
        from omni_prod.skills_registry import build_canonical_skills_registry
        keys = {a.key for a in build_canonical_agents_registry(build_canonical_skills_registry(CapabilityRegistry())).all()}
        self.assertIn('agent.venice', keys)
        self.assertIn('agent.plan_verifier', keys)
        self.assertNotIn('agent.product_architect', keys)


if __name__ == '__main__':
    unittest.main()
