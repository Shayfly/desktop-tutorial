"""Issue #12: customer requirements survive multi-turn conversations. Confirmed
values are never silently overwritten, contradictions are surfaced, model
claims are validated, the Chief Architect gets the validated, versioned
intake-requirements/1 contract, and approvals stay bound to a revision."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import agent
from omni_prod.intake import contract as C
from omni_prod.intake.interpreter import DeterministicInterpreter, Interpretation, Proposal, validate_model_output
from tests.test_conversation_os import MemoryBriefs

AUTH = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.05',
        'OMNI_INTAKE_DAILY_BUDGET_USD': '0.5'}


class FakeModel:
    """Model-origin proposals layered on the deterministic interpretation (as the real merge does)."""
    def __init__(self, proposals=()):
        self.proposals, self.calls = list(proposals), []

    def interpret(self, message, brief=None):
        self.calls.append(message)
        base = DeterministicInterpreter().interpret(message, brief)
        fields = {p.field for p in base.proposals}
        extra = [Proposal(f, v, c, message[:20], 'model') for f, v, c in self.proposals if f not in fields]
        return Interpretation(base.language, base.product_family, base.proposals + extra, base.delegate_rest,
                              base.requirements, 'model:fake+deterministic', [], '0.001', 'ESTIMATED', 'irs_fake')


def confirmed_brief(**values):
    b = d.start('מערכת לניהול השאלת ציוד לצוות')
    return d.answer(b, values)


class ApplyTests(unittest.TestCase):
    def interp(self, *props):
        return Interpretation('he', 'web_app', [Proposal(f, v, c, 'x', o) for f, v, c, o in props])

    def test_model_never_overwrites_a_confirmed_value(self):
        b = confirmed_brief(login='none', languages='he')
        res = agent.apply(b, self.interp(('login', 'roles', 'high', 'model'), ('languages', 'en', 'high', 'model')))
        self.assertEqual(res.brief.fields['login']['value'], 'none')
        self.assertEqual(res.brief.fields['languages']['value'], 'he')
        self.assertEqual({c['field'] for c in res.conflicts}, {'login', 'languages'})
        self.assertIn('login', [q.id for q in res.asked])                       # asked back, not dropped

    def test_customer_words_change_non_material_but_not_material_confirmed(self):
        b = confirmed_brief(login='none', languages='he')
        res = agent.apply(b, self.interp(('languages', 'he_en', 'high', 'deterministic'),
                                         ('login', 'simple', 'high', 'deterministic')))
        self.assertEqual(res.brief.fields['languages']['value'], 'he_en')      # visible correction
        self.assertEqual(res.corrected, [{'field': 'languages', 'old': 'he', 'new': 'he_en'}])
        self.assertEqual(res.brief.fields['login']['value'], 'none')           # material: confirm first
        self.assertEqual([c['field'] for c in res.conflicts], ['login'])

    def test_defaults_may_be_replaced_but_confirmed_may_not(self):
        b = d.start('אתר לחנות פרחים')
        res = agent.apply(b, self.interp(('color', 'green', 'medium', 'model')))
        res2 = agent.apply(res.brief, self.interp(('color', 'blue', 'high', 'model')))
        self.assertEqual(res2.brief.fields['color']['value'], 'blue')          # default/inferred -> replaceable

    def test_sensitive_turn_never_applies_model_material_fields(self):
        b = d.start('מערכת לצוות')
        res = agent.apply(b, self.interp(('personal_data', 'yes', 'high', 'model')), require_confirmation=True)
        self.assertNotIn('personal_data', res.brief.fields)
        self.assertEqual(res.brief.hints.get('personal_data'), 'yes')           # pre-selected, asked
        self.assertEqual(res.conflicts[0]['reason'], 'sensitive turn: needs explicit confirmation')

    def test_unsupported_model_claims_never_reach_the_contract(self):
        msg = 'מערכת לניהול השאלת ציוד לצוות, בלי התחברות, בעברית'
        raw = {'language': 'he', 'product_family': 'web_app',
               'proposals': [{'field': 'login', 'value': 'roles', 'confidence': 'high', 'evidence': 'עם הרשאות'},
                             {'field': 'personal_data', 'value': 'yes', 'confidence': 'high', 'evidence': 'מידע אישי'}],
               'requirements': ['תשלומים באשראי', 123, 'x' * 400], 'delegate_rest': 'yes'}
        it, dropped = validate_model_output(raw, msg)
        self.assertEqual(it.proposals, [])                                       # evidence not in the message
        self.assertEqual(it.requirements, ['תשלומים באשראי'])                    # text only, never a field
        self.assertFalse(it.delegate_rest)
        self.assertTrue(any('delegate_rest' in x for x in dropped))
        for bad in ({'proposals': 'login'}, {'proposals': {'a': 1}}, {'requirements': 'x'}, [1], 'x', None):
            with self.subTest(raw=bad):
                self.assertIsNone(validate_model_output(bad, msg)[0])
        self.assertIsNone(validate_model_output({'proposals': [{}] * 10, 'x': 'y' * 60000}, msg)[0])


class MultiTurnTests(unittest.TestCase):
    def setUp(self):
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()

    def sup(self, model=None):
        return ConversationSupervisor(briefs=self.briefs, store=self.store, worker_interpreter=model)

    def say(self, sup, text, env=AUTH, answers=None):
        with mock.patch.dict(os.environ, env, clear=False):
            return sup.turn(project_id='p', account_id='a', message=text, answers=answers, lang='he')

    def test_requirements_survive_turns_and_reach_the_architect(self):
        model = FakeModel([('login', 'roles', 'high')])
        s = self.sup(model)
        t1 = self.say(s, 'מערכת לניהול השאלת ציוד לצוות שלי, בלי התחברות, בעברית')
        self.assertEqual(self.briefs.latest('p').brief.fields['login']['value'], 'none')
        t2 = self.say(s, 'add an English version too, and a weekly report')               # mixed language turn
        brief = self.briefs.latest('p').brief
        self.assertEqual(brief.fields['login']['value'], 'none')                 # the model 'roles' claim did not win
        self.assertEqual([(c['field'], c['current'], c['proposed'], c['origin']) for c in t2.interpretation['conflicts']],
                         [('login', 'none', 'roles', 'model')])
        self.assertIn('לא שיניתי', t2.reply)
        self.assertEqual(t2.reply.count('האם צריך התחברות'), 2)                  # once per side, not duplicated
        self.assertEqual(self.briefs.latest('p').revision, 1)                    # nothing changed -> no new revision
        # Chief Architect input: the validated contract of the latest revision
        contract = C.build(brief)
        self.assertEqual(contract.to_dict()['schema'], 'intake-requirements/1')
        self.assertEqual(contract.to_dict()['brief_fingerprint'], brief.fingerprint())
        self.assertEqual(model.calls[0], 'מערכת לניהול השאלת ציוד לצוות שלי, בלי התחברות, בעברית')
        del t1

    def test_complex_turns_escalate_and_ordinary_turns_stay_cheap(self):
        """Master directive stage 1: the lane's task reaches the reserved call."""
        class TaskRecordingModel(FakeModel):
            task = 'conversation'

            def interpret(self, message, brief=None):
                self.tasks = getattr(self, 'tasks', []) + [self.task]
                return super().interpret(message, brief)
        model = TaskRecordingModel()
        s = self.sup(model)
        self.say(s, 'מערכת לניהול השאלת ציוד לצוות שלי, בלי התחברות, בעברית')            # MEDIUM
        t = self.say(s, 'תוסיף סליקת אשראי והרשאות מנהלים עם נתונים רפואיים של לקוחות')   # RISKY
        self.assertEqual(model.tasks, ['conversation', 'conversation_complex'])
        self.assertEqual(t.interpretation['lane']['lane'], 'escalated')
        self.assertTrue(t.interpretation['lane']['requires_explicit_confirmation'])

    def test_conflict_is_asked_back_in_hebrew(self):
        s = self.sup(FakeModel([('languages', 'en', 'high')]))
        self.say(s, 'אתר תורים למספרה', answers=None)
        self.say(s, '', answers={'languages': 'he'})                              # customer confirms via button
        t = self.say(s, 'אתר תורים למספרה עם לוח זמנים')
        self.assertEqual(self.briefs.latest('p').brief.fields['languages']['value'], 'he')
        self.assertIn('לא שיניתי', t.reply)
        self.assertIn('languages', [q.id for q in t.questions])

    def test_short_yes_after_approval_prompt_is_risky_and_never_approves(self):
        s = self.sup(FakeModel())
        self.say(s, 'מערכת לניהול השאלת ציוד לצוות שלי, בלי התחברות, בעברית')
        self.store.add_message(project_id='p', account_id='a', role='assistant',
                               content='כדי להתחיל, אשרו את הסיכום והעלות בכפתור.',
                               interpretation={'actions': [{'type': 'show_plan', 'brief_revision': 1}]})
        t = self.say(s, 'כן')
        stored = self.store.messages_for('p')[-1]['interpretation']
        self.assertEqual(t.intent, 'requirements')
        self.assertEqual(stored['complexity']['level'], 'RISKY')
        self.assertTrue(stored['lane']['requires_explicit_confirmation'])
        self.assertFalse(any(a.get('type') in ('build_started', 'approved') for a in t.actions))

    def test_greeting_uses_no_model_and_costs_nothing(self):
        model = FakeModel()
        t = self.say(self.sup(model), 'שלום')
        self.assertEqual(model.calls, [])
        self.assertEqual((t.cost_usd, t.cost_state, t.reservation_id), (0, 'CONFIRMED_ZERO', None))

    def test_paid_turn_records_cost_state_and_reservation(self):
        t = self.say(self.sup(FakeModel()), 'מערכת לניהול מלאי למחסן קטן')
        row = self.store.messages_for('p')[-1]
        self.assertEqual((row['cost_state'], row['reservation_id'], row['cost_usd']), ('ESTIMATED', 'irs_fake', '0.001'))
        self.assertEqual(t.interpretation['lane']['quality_floor'], 70)


if __name__ == '__main__':
    unittest.main()
