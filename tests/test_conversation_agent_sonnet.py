"""Sonnet for the conversation agent only (owner 2026-11-18), with decision 10's fallback, on the real Venice path.

On Venice the cheapest listed model always won, so listing Sonnet beside Haiku never ran Sonnet, and listing it alone
moved every account onto it. Now the agent's turns are quoted with the agent's own profile (conversation_agent:
claude-sonnet-5-5 then claude-haiku-5-5, ceiling 2,10 = Sonnet's live list price) and the worker picks the FIRST listed
model Venice offers within the ceiling -- Sonnet, and Haiku only when Venice does not offer Sonnet (decision 10). The
choice is made before any request, so it is not a second paid call. Every other account is quoted exactly as before.
Real budget.quote, real build_gateway, real VeniceIntakeGateway and select_model; only Venice's HTTP is a fake.
"""
import json
import os
import sys
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import budget as B
from omni_prod.intake import conversation_agent as agent
from omni_prod.intake import reservation_worker as W
from omni_prod.intake.interpreter import ModelInterpreter
from omni_prod.providers import venice_gateway as V

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_os import MemoryBriefs                       # noqa: E402
from test_venice_in_conversation import ANSWER, OPEN                 # noqa: E402

KEY = {'VENICE_API_KEY1': 'test-key', **OPEN}
GLOBAL = {'OMNI_INTAKE_PROVIDER': 'venice', 'OMNI_VENICE_PRICE_CEILING_USD_PER_M': '0.18,0.9',
          'OMNI_VENICE_ALLOWED_MODELS': 'claude-haiku-5-5,qwen3-235b-a22b-instruct-2507'}


def models(*present):
    prices = {'openai-gpt-6-luna': (0.1, 0.5), 'claude-sonnet-5-5': (2, 10), 'claude-haiku-5-5': (0.1, 0.5), 'qwen3-235b-a22b-instruct-2507': (0.15, 0.6)}
    return {'data': [{'id': m, 'model_spec': {'privacy': 'anonymized', 'pricing': {
        'input': {'usd': prices[m][0]}, 'output': {'usd': prices[m][1]}}}} for m in present]}


class Venice:
    def __init__(self, listed):
        self.listed, self.calls = listed, []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append((method, body))
        if method == 'GET':
            return 200, self.listed
        return 200, {'choices': [{'message': {'content': json.dumps(ANSWER, ensure_ascii=False)}}],
                     'usage': {'prompt_tokens': 900, 'completion_tokens': 120}, 'cost': {'usd': '0.0040'}}

    @property
    def sent_model(self):
        return [b['model'] for m, b in self.calls if m == 'POST']


def agent_quote():
    with mock.patch.dict(os.environ, GLOBAL):
        return B.quote(system='S', user='אתר לחנות פרחים', max_tokens=2400, venice_profile=agent.venice_profile())


def run(quote, venice):
    real = V.VeniceIntakeGateway
    with mock.patch.dict(os.environ, KEY), \
            mock.patch.object(V, 'VeniceIntakeGateway', lambda q, **kw: real(q, env=KEY, transport=venice, **kw)):
        g = W.build_gateway(quote.amount_usd, tuple(quote.envelope['allowed_models']), quote=quote.envelope)
        g.complete_json(system='S', user='U', max_tokens=500, call_id='c1')
    return venice.sent_model


class TheAgentRunsOnSonnet(unittest.TestCase):
    def test_the_agent_quote_carries_its_own_profile(self):
        e = agent_quote().envelope
        self.assertEqual((e['mode'], e['venice_select']), ('agent', 'order'))
        self.assertEqual(e['venice_allowed_models'], ['openai-gpt-6-luna', 'claude-sonnet-5-5'])
        self.assertEqual(e['venice_ceiling_usd_per_m'], ['2', '10'])

    def test_luna_answers_when_venice_offers_it(self):                 # the owner, 2026-11-19, after the measurement
        self.assertEqual(run(agent_quote(), Venice(models('claude-sonnet-5-5', 'openai-gpt-6-luna'))),
                         ['openai-gpt-6-luna'])

    def test_sonnet_answers_when_luna_is_not_offered(self):          # decision 10: the next model, before any call
        self.assertEqual(run(agent_quote(), Venice(models('claude-haiku-5-5', 'claude-sonnet-5-5'))),
                         ['claude-sonnet-5-5'])

    def test_the_list_order_wins_over_the_price(self):
        # luna is first AND cheapest, so the agent profile alone cannot tell order from price: a profile whose first
        # model is the dearer one proves the worker chooses by order (the mechanism the fallback relies on)
        with mock.patch.dict(os.environ, GLOBAL):
            q = B.quote(system='S', user='אתר לחנות פרחים', max_tokens=2400, venice_profile={
                'models': ('claude-sonnet-5-5', 'claude-haiku-5-5'),
                'ceiling': (Decimal('2'), Decimal('10')), 'select': 'order'})
        self.assertEqual(run(q, Venice(models('claude-haiku-5-5', 'claude-sonnet-5-5'))), ['claude-sonnet-5-5'])

    def test_every_other_account_is_quoted_and_served_exactly_as_before(self):
        with mock.patch.dict(os.environ, GLOBAL):
            plain = B.quote(system='S', user='אתר לחנות פרחים', max_tokens=2400)
        e = plain.envelope
        self.assertEqual((e['mode'], e['venice_select']), ('plain', 'cheapest'))
        self.assertEqual(e['venice_ceiling_usd_per_m'], ['0.18', '0.9'])
        # with Sonnet offered too, the plain quote still runs the cheapest listed model (Sonnet is not on its list)
        self.assertEqual(run(plain, Venice(models('claude-haiku-5-5', 'claude-sonnet-5-5',
                                                  'qwen3-235b-a22b-instruct-2507'))), ['claude-haiku-5-5'])

    def test_the_profile_is_never_priced_off_venice(self):
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_PROVIDER': ''}), self.assertRaises(B.QuoteUnavailable):
            B.quote(system='S', user='U', max_tokens=500, venice_profile=agent.venice_profile())

    def test_a_quote_the_worker_does_not_understand_is_refused(self):
        q = dict(agent_quote().envelope, venice_select='random')
        with mock.patch.dict(os.environ, KEY), self.assertRaises(ValueError):
            W.build_gateway(Decimal('0.05'), (), quote=q)


class OnlyTheAgent(unittest.TestCase):
    AUTH = {**GLOBAL, 'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.15',
            'OMNI_INTAKE_DAILY_BUDGET_USD': '1.00', 'OMNI_INTAKE_AGENT': 'accounts', 'OMNI_INTAKE_AGENT_ACCOUNTS': 'owner'}

    def profile_for(self, account, env=None):
        class Svc:
            def counted(self, scope):
                return Decimal('0')
        with mock.patch.dict(os.environ, env or self.AUTH):
            sup = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore(), reservations=Svc(),
                                         enqueue=lambda rid: None)
            token = agent.for_account(account)
            try:
                return sup._interpreter('p', account).venice_profile
            finally:
                agent.release(token)

    def test_the_agent_account_gets_the_sonnet_profile_and_no_one_else(self):
        self.assertEqual(self.profile_for('owner')['models'], ('openai-gpt-6-luna', 'claude-sonnet-5-5'))
        self.assertIsNone(self.profile_for('someone-else'))

    def test_off_venice_the_agent_gets_no_venice_profile(self):
        self.assertIsNone(self.profile_for('owner', {**self.AUTH, 'OMNI_INTAKE_PROVIDER': 'routed'}))


class TheRehearsalMeasuresTheAgent(unittest.TestCase):
    PROD = {'reservation_id': 'irs_x', 'quoted_usd': Decimal('0.0036'), 'quote': {
        'provider': 'venice', 'venice_allowed_models': ['claude-haiku-5-5'], 'venice_ceiling_usd_per_m': ['0.18', '0.9'],
        'allowed_models': ['venice:claude-haiku-5-5'], 'max_tokens': 2400, 'task': 'conversation',
        'caps': {'daily:global': {'cap': '1.00'}, 'project:acct:p': {'cap': '0.15'}}}}

    def test_the_agent_quote_is_production_s_with_the_profile_from_the_code(self):
        q = R.agent_quote(self.PROD)
        self.assertEqual((q['mode'], q['venice_select'], q['venice_allowed_models'][0]),
                         ('agent', 'order', 'openai-gpt-6-luna'))
        self.assertEqual(R.project_cap(self.PROD['quote']), Decimal('0.15'))

    def test_the_production_path_never_measures_an_agent_quote_by_chance(self):
        import inspect
        self.assertIn("COALESCE(quote->>'mode', 'plain') = 'plain'", inspect.getsource(R.production_quote))

    def test_a_cap_is_never_guessed(self):
        with self.assertRaises(SystemExit):
            R.project_cap({'caps': {'daily:global': {'cap': '1.00'}}})

    def test_each_conversation_is_held_to_its_turns_and_its_cap_as_typed_limits(self):
        g = R.ProductionPathGateway(R.agent_quote(self.PROD), cap_usd=Decimal('0.15'), max_turns=2)
        venice = Venice(models('openai-gpt-6-luna', 'claude-sonnet-5-5'))
        real = V.VeniceIntakeGateway
        with mock.patch.dict(os.environ, KEY), \
                mock.patch.object(V, 'VeniceIntakeGateway', lambda q, **kw: real(q, env=KEY, transport=venice, **kw)):
            interp = ModelInterpreter(g)
            first, second, third = (interp.interpret('אתר לחנות פרחים בחיפה') for _ in range(3))
        self.assertEqual(venice.sent_model, ['openai-gpt-6-luna', 'openai-gpt-6-luna'])
        self.assertEqual((first.limit, second.limit), (None, None))
        self.assertEqual(third.limit, {'kind': 'turns', 'source': 'reserve'})
        g.reset()
        g.cap_usd = Decimal('0.001')                                       # below one turn's worst case
        with mock.patch.dict(os.environ, KEY):
            self.assertEqual(ModelInterpreter(g).interpret('אתר').limit, {'kind': 'budget', 'source': 'reserve'})



class TheBuilderStaysOnItsModel(unittest.TestCase):
    """The owner: "the builder stays on its current model until measured". The agent profile is read in three places
    only -- the agent module, the supervisor's quote for agent accounts, and the rehearsal -- never by the builder."""

    def test_only_the_conversation_reads_the_agent_profile(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1] / 'omni_prod'
        readers = sorted(str(f.relative_to(root)) for f in root.rglob('*.py')
                         if 'venice_profile()' in f.read_text(encoding='utf-8', errors='replace'))
        self.assertEqual(readers, ['conversation/supervisor.py', 'conversation_rehearsal.py',
                                   'intake/conversation_agent.py'])


if __name__ == '__main__':
    unittest.main()


class TheRehearsalSaysWhyACallFailed(unittest.TestCase):
    """Run 44445874611 (2026-11-19): 9 of 10 agent calls failed and the rehearsal printed only "model call failed".
    Each failed call's reason is now kept on the gateway and printed, with keys masked."""

    def test_a_failed_call_is_recorded_with_its_reason_and_keys_masked(self):
        class Refusing(Venice):
            def __call__(self, method, url, headers, body, timeout):
                if method == 'POST':
                    raise RuntimeError('HTTP 429 rate limited for key vn-abcdefghijklmnop')
                return super().__call__(method, url, headers, body, timeout)
        g = R.ProductionPathGateway(R.agent_quote(TheRehearsalMeasuresTheAgent.PROD), cap_usd=Decimal('0.15'),
                                    max_turns=8)
        venice = Refusing(models('claude-sonnet-5-5', 'claude-haiku-5-5'))
        real = V.VeniceIntakeGateway
        with mock.patch.dict(os.environ, KEY), \
                mock.patch.object(V, 'VeniceIntakeGateway', lambda q, **kw: real(q, env=KEY, transport=venice, **kw)):
            it = ModelInterpreter(g).interpret('אתר לחנות פרחים בחיפה')
        self.assertTrue(it.interpreter.startswith('deterministic'), it.interpreter)
        self.assertEqual(len(g.call_errors), 1)
        self.assertIn('429 rate limited', g.call_errors[0])
        self.assertNotIn('abcdefghijklmnop', g.call_errors[0])
        g.reset()
        self.assertEqual(g.call_errors, [])
