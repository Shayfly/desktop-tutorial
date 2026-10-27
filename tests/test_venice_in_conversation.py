"""C3 (2026-10-27): Venice wired into the intake conversation.

Evidence test: a customer message the deterministic catalog does not understand ("משלוחים לאילת", "מזומן בלבד")
reaches Venice through the same reservation/ModelInterpreter path as any paid turn, and the answer the customer
reads -- reply, requirements and the `screens` decision in the saved brief -- is derived from the customer's own
words. The negative control runs the identical message without the model and shows none of it appears: the catalog
alone cannot produce that answer. No network: Venice is a fake transport speaking the real API shape.
"""
from __future__ import annotations

import json
import os
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import budget as B
from omni_prod.intake import reservation_worker as W
from omni_prod.intake.interpreter import ModelInterpreter
from omni_prod.providers import venice_gateway as V
from omni_prod.providers.venice import VeniceBudgetExceeded, VeniceKeyMissing
from tests.test_conversation_os import MemoryBriefs

KEY = {'VENICE_API_KEY1': 'test-key'}
AUTH = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.05',
        'OMNI_INTAKE_DAILY_BUDGET_USD': '0.5'}
MSG = 'אתר לחנות פרחים עם משלוחים לאילת ותשלום במזומן בלבד'
SCREENS = 'קטלוג פרחים, טופס הזמנה עם כתובת למשלוח באילת, ותשלום במזומן בלבד בעת המסירה'
ANSWER = {'language': 'he', 'product_family': 'website',
          'proposals': [{'field': 'screens', 'value': SCREENS, 'confidence': 'high', 'evidence': 'משלוחים לאילת'}],
          'requirements': ['משלוחים לאילת', 'תשלום במזומן בלבד, ללא סליקה באתר'],
          'reply': 'הבנתי: חנות פרחים שמשלוחיה לאילת, והתשלום במזומן בלבד, כך שלא אוסיף סליקה באתר.'}
MODELS = {'data': [
    {'id': 'anon-cheap', 'model_spec': {'privacy': 'anonymized', 'pricing': {'input': {'usd': 0.01}, 'output': {'usd': 0.01}}}},
    {'id': 'private-e2ee', 'model_spec': {'privacy': 'private', 'capabilities': {'supportsE2EE': True},
                                          'pricing': {'input': {'usd': 0.5}, 'output': {'usd': 2}}}}]}


class FakeVenice:
    """The real Venice API shape; records every request so tests can see what was (not) sent."""
    def __init__(self, content=None, *, cost='0.0007', usage=True, chat_status=200, models_status=200):
        self.content = json.dumps(ANSWER, ensure_ascii=False) if content is None else content
        self.cost, self.usage, self.chat_status, self.models_status = cost, usage, chat_status, models_status
        self.calls = []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append((method, url.rsplit('/api/v1', 1)[-1], body))
        if method == 'GET':
            return self.models_status, (MODELS if self.models_status == 200 else {})
        if self.chat_status != 200:
            return self.chat_status, {}
        out = {'choices': [{'message': {'content': self.content}}]}
        if self.usage:
            out['usage'] = {'prompt_tokens': 900, 'completion_tokens': 120}
        if self.cost is not None:
            out['cost'] = {'usd': self.cost}
        return 200, out

    @property
    def chats(self):
        return [c for c in self.calls if c[0] == 'POST']


def gateway(fake, quoted='0.05', env=KEY):
    return V.VeniceIntakeGateway(Decimal(quoted), env=env, transport=fake)


class GatewayTests(unittest.TestCase):
    def test_selected_only_by_env(self):
        self.assertTrue(V.selected({'OMNI_INTAKE_PROVIDER': 'venice'}))
        for env in ({}, {'OMNI_INTAKE_PROVIDER': ''}, {'OMNI_INTAKE_PROVIDER': 'openrouter'}):
            self.assertFalse(V.selected(env))
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_PROVIDER': 'venice', **KEY}):
            self.assertIsInstance(W.build_gateway(Decimal('0.05'), ()), V.VeniceIntakeGateway)

    def test_missing_key_fails_when_built_so_the_reservation_is_released(self):
        with self.assertRaises(VeniceKeyMissing):
            gateway(FakeVenice(), env={})
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_PROVIDER': 'venice'}, clear=True):
            with self.assertRaises(VeniceKeyMissing):
                W.build_gateway(Decimal('0.05'), ())

    def test_call_shape_private_model_no_venice_prompt_no_retries(self):
        fake = FakeVenice()
        out = gateway(fake).complete_json(system='SYS', user=MSG, max_tokens=500, task='conversation')
        self.assertEqual(out, ANSWER)
        (_, path, body), = fake.chats
        self.assertEqual(path, '/chat/completions')
        self.assertEqual(body['model'], 'private-e2ee')                     # never the cheaper non-private one
        self.assertEqual(body['venice_parameters'], {'include_venice_system_prompt': False})
        self.assertEqual([m['content'] for m in body['messages'][1:]], ['SYS', MSG])
        self.assertEqual(body['max_tokens'], 500)
        fake503 = FakeVenice(chat_status=503)
        with self.assertRaises(Exception):
            gateway(fake503).complete_json(system='S', user=MSG, max_tokens=100)
        self.assertEqual(len(fake503.chats), 1)                             # one paid attempt, never a second

    def test_metering_states(self):
        g = gateway(FakeVenice())
        g.complete_json(system='S', user=MSG, max_tokens=500)
        m = W.meter(g, {'max_tokens': 500})
        self.assertEqual((m['cost_state'], m['actual_usd'], m['provider'], m['model']),
                         (B.CONFIRMED, Decimal('0.0007'), 'venice', 'private-e2ee'))
        g = gateway(FakeVenice(cost=None))                                  # usage but no cost.usd
        g.complete_json(system='S', user=MSG, max_tokens=500)
        self.assertEqual(W.meter(g, {'max_tokens': 500})['cost_state'], B.COST_UNKNOWN)
        g = gateway(FakeVenice(chat_status=500))                            # contacted, then failed
        with self.assertRaises(Exception):
            g.complete_json(system='S', user=MSG, max_tokens=500)
        self.assertEqual(W.meter(g, {'max_tokens': 500})['cost_state'], B.COST_UNKNOWN)   # never "free"

    def test_quote_too_small_is_refused_before_the_prompt_leaves(self):
        fake = FakeVenice()
        g = gateway(fake, quoted='0.0001')
        with self.assertRaises(VeniceBudgetExceeded):
            g.complete_json(system='S' * 2000, user=MSG, max_tokens=800)
        self.assertEqual(fake.chats, [])
        m = W.meter(g, {'max_tokens': 800})
        self.assertEqual((m['contacted'], m['cost_state']), (False, B.CONFIRMED_ZERO))

    def test_models_list_failure_is_not_a_paid_contact(self):
        g = gateway(FakeVenice(models_status=503))
        with self.assertRaises(Exception):
            g.complete_json(system='S', user=MSG, max_tokens=100)
        self.assertFalse(W.meter(g, {'max_tokens': 100})['contacted'])

    def test_answer_must_be_exactly_one_json_object(self):
        body = json.dumps(ANSWER, ensure_ascii=False)
        self.assertEqual(V.parse_json_object('```json\n' + body + '\n```'), ANSWER)
        for bad in (body + '\nאגב, הוספתי גם סליקה.', 'הנה: ' + body, '[1, 2]', 'not json', ''):
            with self.subTest(bad=bad[:30]):
                with self.assertRaises(V.VeniceOutputInvalid):
                    V.parse_json_object(bad)

    def test_each_call_is_metered_alone(self):
        g = gateway(FakeVenice())
        for _ in range(3):
            g.complete_json(system='S', user=MSG, max_tokens=500)
        self.assertEqual(W.meter(g, {'max_tokens': 500})['actual_usd'], Decimal('0.0007'))

    def test_worker_executes_a_reservation_on_venice(self):
        """execute_reservation is unchanged; only the factory differs."""
        fake, real = FakeVenice(), V.VeniceIntakeGateway
        calls = {}

        class Svc:
            def __init__(self, pool): pass
            def claim(self, rid, **kw):
                return mock.Mock(id=rid, quote={'max_tokens': 500, 'allowed_models': ['x']}, quoted_usd=Decimal('0.05'))
            def payload(self, rid): return {'system': 'S', 'user': MSG, 'max_tokens': 500, 'task': 'conversation'}
            def mark_executing(self, r, **kw): return True
            def release(self, rid, **kw): calls['released'] = kw
            def settle(self, r, **kw):
                calls.update(kw)
                return mock.Mock(state='SETTLED', cost_state=kw['cost_state'], actual_usd=kw['actual_usd'],
                                 model=kw['model'])
        with mock.patch.object(B, 'ReservationService', Svc), \
                mock.patch.object(W, '_reserved_task', lambda payload, quote: 'conversation'), \
                mock.patch.dict(os.environ, {'OMNI_INTAKE_PROVIDER': 'venice', **KEY}), \
                mock.patch.object(V, 'VeniceIntakeGateway', lambda q: real(q, env=KEY, transport=fake)):
            out = W.execute_reservation(None, 'irs_1', worker_id='w')
        self.assertTrue(out['ok'])
        self.assertEqual((calls['cost_state'], calls['actual_usd'], calls['provider'], calls['model']),
                         (B.CONFIRMED, Decimal('0.0007'), 'venice', 'private-e2ee'))
        self.assertEqual(calls['result']['raw'], ANSWER)


class CustomerWordsEvidence(unittest.TestCase):
    """The answer comes from what the customer wrote, not from the catalog."""

    def run_turn(self, interpreter):
        briefs = MemoryBriefs()
        s = ConversationSupervisor(briefs=briefs, store=MemoryConversationStore(), worker_interpreter=interpreter)
        with mock.patch.dict(os.environ, AUTH):
            t = s.turn(project_id='p', account_id='a', message=MSG, lang='he')
        return t, briefs.latest('p').brief

    def test_venice_answer_is_derived_from_the_customer_words(self):
        fake = FakeVenice()
        t, brief = self.run_turn(ModelInterpreter(gateway(fake)))
        self.assertEqual(len(fake.chats), 1)
        self.assertIn(MSG, fake.chats[0][2]['messages'][-1]['content'])     # Venice saw the customer's words
        self.assertEqual(t.interpretation['interpreter'], 'model+deterministic')
        self.assertEqual((t.interpretation['cost_state'], t.interpretation['cost_usd']), (B.CONFIRMED, '0.0007'))
        self.assertTrue(t.reply.startswith(ANSWER['reply']))
        for words in ('אילת', 'מזומן'):
            self.assertIn(words, t.reply)
        self.assertEqual(t.interpretation['requirements'], ANSWER['requirements'])
        self.assertEqual(brief.fields['screens']['value'], SCREENS)         # a decision in the saved brief

    def test_negative_control_catalog_alone_cannot_produce_it(self):
        t, brief = self.run_turn(None)                                       # same message, no model route
        self.assertNotEqual(t.interpretation['interpreter'], 'model+deterministic')
        for words in ('אילת', 'מזומן'):
            self.assertNotIn(words, t.reply)
        self.assertNotEqual(brief.fields['screens']['value'], SCREENS)

    def test_ungrounded_model_claims_do_not_reach_the_brief(self):
        bad = dict(ANSWER, proposals=[{'field': 'screens', 'value': 'מערכת CRM מלאה', 'confidence': 'high',
                                       'evidence': 'מערכת CRM'}])
        t, brief = self.run_turn(ModelInterpreter(gateway(FakeVenice(json.dumps(bad, ensure_ascii=False)))))
        self.assertNotEqual(brief.fields['screens']['value'], 'מערכת CRM מלאה')
        self.assertIn('screens: evidence not found in the message', t.interpretation['dropped'])

    def test_venice_down_the_conversation_continues_deterministically(self):
        t, brief = self.run_turn(ModelInterpreter(gateway(FakeVenice(chat_status=500))))
        self.assertEqual(t.interpretation['interpreter'], 'deterministic (model call failed)')
        self.assertEqual(t.interpretation['cost_state'], B.COST_UNKNOWN)
        self.assertTrue(t.reply)


if __name__ == '__main__':
    unittest.main()
