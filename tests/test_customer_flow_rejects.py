"""Founder screenshots 2026-10-12: regression tests, no paid/live claims."""
import unittest
from unittest.mock import patch
from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake.interpreter import DeterministicInterpreter, ModelInterpreter
from tests.test_conversation_os import MemoryBriefs


class CustomerFlowTests(unittest.TestCase):
    def setUp(self):
        self.briefs = MemoryBriefs()
        self.store = MemoryConversationStore()
        self.s = ConversationSupervisor(briefs=self.briefs, store=self.store)

    def say(self, text='', answers=None):
        return self.s.turn(project_id='p', account_id='a', message=text, answers=answers, lang='he')

    def blocked(self, personal='no'):
        self.say('אתר ללקוחות למכירת מטפחות, עם התחברות והרשאות שונות')
        return self.say(answers={'personal_data': personal, 'login': 'roles'})

    def test_blocked_request_keeps_review_and_edit_actions(self):
        t = self.blocked()
        # owner 2026-10-26: no plan before the spec is approved (gate 1), so the review control is editing the spec
        self.assertNotIn('show_plan', [a['type'] for a in t.actions])
        self.assertIsNone(t.plan_id)
        self.assertIn('edit_requirements', [a['type'] for a in t.actions])
        self.assertNotIn('approve_build', [a['type'] for a in t.actions])
        self.assertNotIn('an internal tool', t.reply)

    def test_contextual_withdrawal_changes_login_but_keeps_other_requirements(self):
        before = self.blocked()
        t = self.say('אז תוותר על זה כרגע')
        self.assertEqual(t.brief_row.brief.values()['login'], 'none')
        self.assertEqual(t.brief_row.brief.values()['audience'], before.brief_row.brief.values()['audience'])
        self.assertGreater(t.brief_row.revision, before.brief_row.revision)
        self.assertNotIn('sign-in (roles)', t.reply)

    def test_withdrawal_keeps_personal_data_access_decision(self):
        self.blocked('yes')
        t = self.say('אז תוותר על זה כרגע')
        self.assertEqual(t.brief_row.brief.values()['login'], 'none')
        self.assertEqual(t.brief_row.brief.values()['personal_data'], 'yes')
        self.assertIn('access_scope', [q.id for q in t.questions])
        self.assertNotIn('approve_build', [a['type'] for a in t.actions])

    def test_what_next_has_action_even_while_blocked(self):
        self.blocked()
        t = self.say('מה עושים עכשיו?')
        self.assertIn('edit_requirements', [a['type'] for a in t.actions])

    def test_free_colour_combination_is_preserved_in_binding(self):
        b = d.answer(d.start('אתר מטפחות'), {'color': 'ורוד עדין עם שמנת וזהב'})
        self.assertEqual(b.values()['color'], 'ורוד עדין עם שמנת וזהב')
        self.assertIn('ורוד עדין עם שמנת וזהב', d.requirements_text(b))

    def test_multi_colour_message_keeps_the_full_palette(self):
        p = DeterministicInterpreter().interpret('הצבעים יהיו כחול כהה וטורקיז עם לבן').proposals
        colour = next(x for x in p if x.field == 'color')
        self.assertIn('טורקיז', colour.value)
        self.assertIn('לבן', colour.value)

    def test_model_prompt_receives_current_requirements_without_treating_them_as_new_evidence(self):
        class Gateway:
            last_usage = None
            def complete_json(self, **kw):
                self.call = kw
                return {'language': 'he', 'product_family': 'website', 'proposals': [], 'requirements': []}
        g = Gateway()
        b = d.answer(d.start('אתר מטפחות'), {'login': 'roles'})
        ModelInterpreter(g).interpret('איזה עיצוב כדאי?', b)
        self.assertIn('roles', g.call['user'])
        self.assertIn('אתר מטפחות', g.call['user'])

    def test_model_can_answer_in_hebrew_with_validated_operational_proposals(self):
        from omni_prod.intake.interpreter import validate_model_output
        raw={'language':'he','product_family':'website','proposals':[], 'requirements':[],
             'reply':'לאתר המטפחות הייתי מציע גוונים עדינים וטקסט קריא.'}
        out,_=validate_model_output(raw,'איזה עיצוב כדאי?')
        self.assertEqual(out.reply,raw['reply'])


if __name__ == '__main__':
    unittest.main()
