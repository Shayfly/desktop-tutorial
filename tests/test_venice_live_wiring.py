"""Venice wired into the live conversation (owner decision 2026-10-26): two gates.

free conversation -> spec + cost range ("Step 1 of 2") -> gate 1: spec approved by fingerprint -> plan -> the separate
verifier -> only then the customer sees the plan ("Step 2 of 2") -> gate 2: the exact cost next to the range, an
overrun said in full -> build. The real ChiefArchitect, verifier and supervisor run; only the stores are in memory."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import approval_flow as AF
from omni_prod.planning.architect import ChiefArchitect
from tests.test_conversation_os import MemoryBriefs

REQUEST = 'I need a simple internal tool for my team to track equipment loans, in English, no login, no personal data'


class CountingArchitect(ChiefArchitect):
    """The real architect; counts calls, and can hand out a plan that breaks the spec the first N times."""
    def __init__(self, corrupt_first=0):
        super().__init__()
        self.calls, self.corrupt_first = 0, corrupt_first

    def plan(self, contract, **kw):
        self.calls += 1
        plan = super().plan(contract, **kw)
        if self.calls <= self.corrupt_first:
            plan = copy.deepcopy(plan)
            plan['security_boundaries'][0] = 'sign-in: roles'          # the spec says no login
        return plan


class TwoGates(unittest.TestCase):
    def make(self, credits=200, corrupt_first=0):
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        self.arch = CountingArchitect(corrupt_first)
        self.sup = ConversationSupervisor(briefs=self.briefs, store=self.store, architect=self.arch, credits=credits)

    def say(self, msg='', answers=None, lang='en'):
        return self.sup.turn(project_id='p', account_id='a', message=msg, answers=answers, lang=lang)

    def to_gate1(self, msg=REQUEST, lang='en'):
        t = self.say(msg, lang=lang)
        for _ in range(10):
            if any(a['type'] == 'approve_spec' for a in t.actions):
                return t
            self.assertTrue(t.questions or t.gaps, t.reply)
            q = t.questions[0] if t.questions else None
            t = self.say(answers={q.id: q.options[0].value if q.kind == 'choice' else d.DELEGATE}, lang=lang) if q \
                else self.say('you decide' if lang == 'en' else 'תחליט אתה', lang=lang)
        self.fail('never reached gate 1')

    def approve(self, t, lang='en', fp=None):
        return self.sup.approve_spec(project_id='p', account_id='a', brief_fingerprint=fp or t.brief_row.fingerprint,
                                     lang=lang)

    # --- no plan before the spec is approved
    def test_no_plan_before_spec_approval(self):
        self.make()
        t = self.to_gate1()
        for extra in ('how much will it cost?', 'go ahead and build it', 'what is missing?'):
            r = self.say(extra)
            self.assertIsNone(r.plan_id, extra)
            self.assertNotIn('approve_build', [a['type'] for a in r.actions], extra)
        self.assertEqual(self.arch.calls, 0)                      # the architect was never asked
        self.assertEqual(self.store.plans, {})
        self.assertIn('Step 1 of 2', t.reply)
        self.assertIn('Cost estimate: 45–200 credits', t.reply)  # the range is said while listening
        self.assertEqual(t.venice['cost_range_credits'], [45, 200])
        self.assertTrue(AF.on_two_gate_flow(self.store.messages_for('p')))
        self.assertFalse(AF.spec_approved(self.store.messages_for('p'), t.brief_row.fingerprint))

    def test_approval_of_another_spec_version_makes_no_plan(self):
        self.make()
        t = self.to_gate1()
        r = self.approve(t, fp='0' * 64)
        self.assertIsNone(r.plan)
        self.assertEqual(self.arch.calls, 0)
        self.assertEqual([a['type'] for a in r.actions], ['approve_spec'])
        self.assertEqual(r.actions[0]['brief_fingerprint'], t.brief_row.fingerprint)   # the current spec, shown again
        self.assertFalse(AF.spec_approved(self.store.messages_for('p'), t.brief_row.fingerprint))

    def test_after_approval_the_verified_plan_and_gate2(self):
        self.make(credits=200)
        r = self.approve(self.to_gate1())
        self.assertEqual(self.arch.calls, 1)
        self.assertIn('Step 2 of 2', r.reply)
        self.assertEqual([a['type'] for a in r.actions], ['show_plan', 'approve_build'])
        gate = r.plan['spec_gate']
        self.assertTrue(gate['verification']['accepted'])
        self.assertFalse(gate['verification']['corrected'])
        self.assertEqual(gate['cost'], {'range': [45, 200], 'exact': 200, 'outside_range': None})
        self.assertIn('Exact cost: 200 credits (the range I gave: 45–200)', r.reply)
        self.assertNotIn('above the range', r.reply)
        self.assertEqual(self.store.plan_for('p', r.brief_row.fingerprint)['plan']['spec_gate'], gate)

    # --- the verifier runs before the customer sees the plan
    def test_a_plan_the_verifier_refuses_is_never_shown(self):
        self.make(corrupt_first=2)                                 # the first plan AND the re-plan break the spec
        r = self.approve(self.to_gate1())
        self.assertIsNone(r.plan)
        self.assertIsNone(r.plan_id)
        self.assertEqual(self.store.plans, {})
        self.assertEqual([a['type'] for a in r.actions], ['edit_requirements'])
        self.assertIn('did not pass the verifier', r.reply)
        self.assertIn('auth_mode', r.reply)
        saved = self.store.messages_for('p')[-1]['interpretation']['verification']
        self.assertFalse(saved['accepted'])

    def test_a_verifier_correction_is_a_visible_line(self):
        self.make(corrupt_first=1)                                 # first plan breaks the spec, the re-plan is right
        r = self.approve(self.to_gate1())
        self.assertIsNotNone(r.plan)
        self.assertTrue(r.plan['spec_gate']['verification']['corrected'])
        self.assertIn('The verifier found and fixed: auth_mode', r.reply)
        self.assertEqual(self.arch.calls, 2)
        self.assertEqual(AF._auth(r.plan), 'none')                 # the plan shown is the corrected one

    def test_the_hebrew_correction_line(self):
        self.make(corrupt_first=1)
        t = self.to_gate1('אני רוצה כלי פנימי לצוות שלי למעקב השאלת ציוד, בלי התחברות, בלי מידע אישי', lang='he')
        self.assertIn('שלב 1 מתוך 2', t.reply)
        r = self.approve(t, lang='he')
        self.assertIn('המאמת מצא ותיקן', r.reply)
        self.assertIn('שלב 2 מתוך 2', r.reply)

    # --- an exact cost outside the range is said in full
    def test_an_exact_cost_above_the_range_is_flagged_with_the_reason(self):
        self.make(credits=500)
        r = self.approve(self.to_gate1())
        self.assertEqual(r.plan['spec_gate']['cost']['outside_range'], 'above')
        self.assertEqual(r.actions[-1]['cost']['outside_range'], 'above')
        self.assertIn('above the range I gave (45–200) by 300 credits', r.reply)
        self.assertIn('Why:', r.reply)

    def test_an_exact_cost_below_the_range_is_said_too(self):
        self.make(credits=20)
        r = self.approve(self.to_gate1())
        self.assertEqual(r.plan['spec_gate']['cost']['outside_range'], 'below')
        self.assertIn('below the range I gave (45–200) by 25 credits', r.reply)

    def test_unknown_exact_cost_is_not_invented(self):
        self.make(credits=None)
        r = self.approve(self.to_gate1())
        self.assertIsNone(r.plan['spec_gate']['cost']['exact'])
        self.assertIn('I will calculate the exact cost when you approve the budget', r.reply)

    # --- a change after approval goes back to step 1
    def test_a_change_after_approval_needs_a_new_spec_approval(self):
        self.make()
        t = self.to_gate1()
        self.assertIsNotNone(self.approve(t).plan)
        r = self.say(answers={'languages': 'he_en'})                # the customer changes the spec after gate 1
        self.assertNotEqual(r.brief_row.fingerprint, t.brief_row.fingerprint)
        self.assertFalse(AF.spec_approved(self.store.messages_for('p'), r.brief_row.fingerprint))
        go = self.say('go ahead and build it')
        self.assertNotIn('approve_build', [a['type'] for a in go.actions])
        self.assertIsNone(go.plan_id)


class EarlierProjectsKeepWorking(unittest.TestCase):
    def test_a_project_that_never_saw_gate1_is_not_on_the_two_gate_flow(self):
        legacy = [{'role': 'assistant', 'interpretation': {'intent': 'requirements', 'actions': [{'type': 'show_plan'}],
                                                           'plan_id': 'pln_old'}}]
        self.assertFalse(AF.on_two_gate_flow(legacy))             # the server gate does not apply to it

    def test_a_plan_saved_before_the_gates_does_not_hide_the_verified_one(self):
        store, plan = MemoryConversationStore(), {'graph_fingerprint': 'g' * 64, 'requirements_fingerprint': 'r' * 64,
                                                   'schema': 's'}
        store.save_plan(project_id='p', brief_revision=1, brief_fingerprint='f', plan=plan)
        gated = {**plan, 'spec_gate': {'approved_fingerprint': 'f', 'verification': {'accepted': True, 'corrected': True}}}
        store.save_plan(project_id='p', brief_revision=1, brief_fingerprint='f', plan=gated)
        self.assertEqual(store.plan_for('p', 'f')['plan'], gated)
        self.assertEqual(len(store.plans), 2)


try:
    from omni_prod import investor_app
except ModuleNotFoundError:          # fastapi missing outside CI
    investor_app = None


@unittest.skipIf(investor_app is None, 'needs fastapi (CI)')
class ServerGate(unittest.TestCase):
    """Build admission refuses on the two-gate flow without the spec approval or the verified plan."""
    def setUp(self):
        self.store, row = MemoryConversationStore(), SimpleNamespace(fingerprint='f' * 64, revision=1, brief=None)
        self.patches = [patch('omni_prod.conversation.store.schema_ready', return_value=True),
                        patch.object(investor_app, '_conversation_store', return_value=self.store),
                        patch.object(investor_app, '_brief_repo', return_value=SimpleNamespace(latest=lambda p: row))]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def note(self, **interp):
        self.store.add_message(project_id='p', account_id='a', role='assistant', content='x', interpretation=interp)

    def bind(self):
        with self.assertRaises(investor_app.HTTPException) as ctx:
            investor_app._bind_execution_plan('p', 'f' * 64)
        return ctx.exception

    def test_no_spec_approval_no_build(self):
        self.note(gate='spec')
        exc = self.bind()
        self.assertEqual((exc.status_code, exc.detail['error']), (409, 'spec_not_approved'))

    def test_approved_spec_without_a_verified_plan_is_refused(self):
        self.note(gate='spec')
        self.note(spec_approved='f' * 64)
        self.assertEqual(self.bind().detail['error'], 'plan_not_verified')

    def test_the_quote_shows_it_as_a_blocker_not_a_server_error(self):
        preview = {'can_build': True, 'blockers': []}
        self.note(gate='spec')
        investor_app._apply_execution_plan_gate(preview, 'p', SimpleNamespace(fingerprint='f' * 64))
        self.assertFalse(preview['can_build'])
        self.assertEqual(preview['blockers'][0]['code'], 'spec_not_approved')


if __name__ == '__main__':
    unittest.main()
