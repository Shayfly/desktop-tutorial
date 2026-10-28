"""Emergency fix 2026-10-28 (fix/intake-approve-and-goal).

BLOCKER 1: the spec approval rode on the conversation route with message='' and was refused as `empty_message`; the
spec was never approved, so the build gate (spec_not_approved) stayed closed -- "לא ניתן להתחיל בבנייה כרגע".
BLOCKER 2: the goal came from the first sentence by rule and the model could not replace it; a pasted
"OMNI_REDIS_URL" became "Main action: OMNI_REDIS_URL".
BLOCKER 3: a brief-bound plan showed the architect's English build spec as its summary.
ARCHITECTURE: a refused model proposal is dropped with a reason; the turn continues.
"""
import json
import os
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import agent as A
from omni_prod.intake import approval_flow as AF
from omni_prod.intake.interpreter import (DeterministicInterpreter, Interpretation, Proposal, first_sentence,
                                          validate_model_output)
from tests.evidence_notice import notice
from tests.test_conversation_os import MemoryBriefs

BARBER = ('אני רוצה מערכת לניהול תורים למספרה שלי. הלקוחות יקבעו תור לפי שעות פנויות, ישאירו שם וטלפון, '
          'ואני אראה את כל התורים של היום. בלי התחברות ללקוחות.')
PASTED = 'OMNI_REDIS_URL\n' + BARBER
GOAL = 'אני רוצה מערכת לניהול תורים למספרה שלי.'


def first_turn(message):
    s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
    t = s.turn(project_id='p', account_id='a', message=message, lang='he')
    return s, t, s.briefs.latest('p').brief


class TheGoal(unittest.TestCase):
    def test_a_pasted_token_does_not_become_the_goal(self):                      # NC (a)
        _, _, b = first_turn(PASTED)
        self.assertEqual(b.fields['goal']['value'], GOAL)
        self.assertNotIn('OMNI_REDIS_URL', d.requirements_text(b).split('Main action:')[1].splitlines()[0])

    def test_with_the_model_off_the_deterministic_goal_still_appears(self):      # NC (b)
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'}):
            _, _, b = first_turn(BARBER)
        self.assertEqual((b.fields['goal']['value'], b.fields['goal']['source']), (GOAL, 'default'))

    def test_the_model_owns_the_goal_over_the_rule(self):
        _, _, b = first_turn(BARBER)
        model = Interpretation('he', 'web_app', [Proposal('goal', 'לקוחות קובעים תור לבד לפי שעות פנויות', 'medium',
                                                          'יקבעו תור', 'model')], False, [], 'model:x')
        self.assertEqual(A.apply(b, model).brief.fields['goal']['value'], 'לקוחות קובעים תור לבד לפי שעות פנויות')

    def test_a_model_goal_that_is_technical_text_is_dropped_with_a_reason(self):
        _, _, b = first_turn(BARBER)
        model = Interpretation('he', 'web_app', [Proposal('goal', 'OMNI_REDIS_URL', 'high', 'OMNI_REDIS_URL', 'model')],
                               False, [], 'model:x')
        r = A.apply(b, model)
        self.assertEqual(r.brief.fields['goal']['value'], GOAL)
        self.assertTrue(any('technical text' in x for x in r.dropped))

    def test_the_customers_own_goal_is_kept_over_the_model(self):
        _, _, b = first_turn(BARBER)
        b = A.answer_question(b, 'goal', 'קביעת תור בשתי לחיצות')
        model = Interpretation('he', 'web_app', [Proposal('goal', 'משהו אחר לגמרי', 'high', 'x', 'model')], False, [],
                               'model:x')
        r = A.apply(b, model)
        self.assertEqual(r.brief.fields['goal']['value'], 'קביעת תור בשתי לחיצות')     # asked back as a conflict
        self.assertEqual([c['field'] for c in r.conflicts], ['goal'])

    def test_first_sentence_skips_technical_lines(self):
        self.assertEqual(first_sentence(PASTED), GOAL)
        self.assertEqual(first_sentence('export OMNI_REDIS_URL=redis://x:6379\nI need a booking site for my salon.'),
                         'I need a booking site for my salon.')
        self.assertEqual(first_sentence('אתר תדמית לעסק שלי עם קישור https://x.co להזמנה'),
                         'אתר תדמית לעסק שלי עם קישור https://x.co להזמנה')    # a link inside a real sentence stays


class ValidationDegrades(unittest.TestCase):
    def test_a_proposal_without_evidence_is_dropped_and_the_answer_stays(self):
        raw = {'language': 'he', 'product_family': 'web_app', 'reply': 'הבנתי, מערכת תורים למספרה.',
               'proposals': [{'field': 'audience', 'value': 'public', 'confidence': 'high', 'evidence': 'לא נאמר כך'},
                             {'field': 'login', 'value': 'none', 'confidence': 'high', 'evidence': 'בלי התחברות'}]}
        interp, dropped = validate_model_output(raw, BARBER)
        self.assertIsNotNone(interp)                                             # the turn continues
        self.assertEqual(interp.reply, 'הבנתי, מערכת תורים למספרה.')            # a natural answer
        self.assertEqual([p.field for p in interp.proposals], ['login'])
        self.assertTrue(any('audience' in x and 'evidence' in x for x in dropped))   # dropped WITH its reason


def _api():
    try:
        import fastapi  # noqa: F401
        from fastapi.testclient import TestClient
    except Exception as exc:                                                     # v24-ci has fastapi
        raise unittest.SkipTest(f'fastapi not installed here ({exc})')
    from omni_prod import investor_app as IA
    return IA, TestClient(IA.app)


class TheApprovalIsAnAction(unittest.TestCase):
    """The real FastAPI routes over in-memory stores."""

    def setUp(self):
        self.IA, self.client = _api()
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        account = mock.Mock(id='a1')
        sup = ConversationSupervisor(briefs=self.briefs, store=self.store)
        patches = [mock.patch.object(self.IA, '_v28_bearer', lambda r: 'tok'),
                   mock.patch.object(self.IA._v28, 'resolve_project_key', lambda **kw: (account, 'k')),
                   mock.patch.object(self.IA, '_conversation_store', lambda: self.store),
                   mock.patch.object(self.IA, '_brief_repo', lambda: self.briefs),
                   mock.patch.object(self.IA, '_supervisor', lambda key, aid=None: sup),
                   mock.patch.object(self.IA, '_conversation_view',
                                     lambda pid, lang, turn=None: {'turn': turn.to_dict(lang) if turn else None})]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def post(self, path, body):
        return self.client.post(f'/api/v28/projects/p1/{path}?lang=en', json=body)

    def ready_spec(self):
        self.post('conversation', {'message': 'I need a simple internal tool for my team to track equipment loans, '
                                              'in English, no login, no personal data'})
        r = self.post('conversation', {'message': 'you decide'})
        acts = [a for a in r.json()['turn']['actions'] if a['type'] == 'approve_spec']
        self.assertTrue(acts, r.json())
        return acts[0]['brief_fingerprint']

    def test_an_empty_chat_turn_is_still_an_explicit_error(self):               # NC (b)
        r = self.post('conversation', {'message': ''})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()['detail']['error'], 'empty_message')
        notice('approve-action NC(b) PASS', 'POST conversation with message="" -> 422 empty_message (explicit)')

    def test_approve_with_an_empty_message_opens_the_build(self):              # NC (a)
        fp = self.ready_spec()
        r = self.post('spec-approval', {'brief_fingerprint': fp})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(AF.spec_approved(self.store.messages, fp))             # the build gate's own check
        self.assertIn('approve_build', [a['type'] for a in r.json()['turn']['actions']])
        notice('approve-action NC(a) PASS', f'POST spec-approval (no message) -> 200; spec_approved={fp[:12]} recorded; '
               'approve_build offered')

    def test_an_old_client_approving_on_the_conversation_route_is_not_empty_message(self):
        fp = self.ready_spec()
        r = self.post('conversation', {'message': '', 'approve_spec': fp})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(AF.spec_approved(self.store.messages, fp))

    def test_a_malformed_fingerprint_is_refused(self):
        self.assertEqual(self.post('spec-approval', {'brief_fingerprint': 'x'}).status_code, 422)


class ThePlanSpeaksTheCustomersLanguage(unittest.TestCase):
    def test_summary_and_questions_follow_the_customer(self):
        IA, _ = _api()
        _, _, b = first_turn(BARBER)
        preview = {'product': {'summary': 'M5 managed Web/SaaS contract for: ... Main action: x'},
                   'clarification_questions': [{'id': 'clarify-primary-workflow', 'question': 'What is the primary '
                                                'business workflow and who will use it?', 'reason': 'r'}]}
        IA._plan_in_customer_language(preview, b, 'he')
        self.assertEqual(preview['product']['summary'], GOAL)
        self.assertTrue(preview['product']['technical_summary'].startswith('M5 managed'))
        self.assertFalse(preview['clarification_questions'][0]['question'].isascii())


if __name__ == '__main__':
    unittest.main()
