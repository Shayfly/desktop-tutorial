"""Measuring cheap Venice models for the conversation agent (the owner, 2026-11-19), in the rehearsal only.

A candidate is one model from a closed list in the code, quoted at its own list price; the request goes through the real
worker gateway (build_gateway, VeniceIntakeGateway, select_model) and Venice's HTTP is the only fake. Production keeps
venice_profile(); the candidate list is never read by the quote the API makes.
"""
import inspect
import json
import os
import sys
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod.intake import budget as B
from omni_prod.intake import conversation_agent as agent
from omni_prod.intake import reservation_worker as W
from omni_prod.providers import venice_gateway as V

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_agent_sonnet import KEY, TheRehearsalMeasuresTheAgent, Venice   # noqa: E402

PROD = TheRehearsalMeasuresTheAgent.PROD


def listed(prices):
    return {'data': [{'id': m, 'model_spec': {'privacy': 'anonymized', 'pricing': {
        'input': {'usd': i}, 'output': {'usd': o}}}} for m, (i, o) in prices.items()]}


def sent(quote, venice):
    real = V.VeniceIntakeGateway
    with mock.patch.dict(os.environ, KEY), \
            mock.patch.object(V, 'VeniceIntakeGateway', lambda q, **kw: real(q, env=KEY, transport=venice, **kw)):
        g = W.build_gateway(Decimal('0.05'), tuple(quote['allowed_models']), quote=quote)
        g.complete_json(system='S', user='U', max_tokens=500, call_id='c1')
    return venice.sent_model


class ACandidateIsOneKnownModelAtItsOwnPrice(unittest.TestCase):
    def test_the_quote_names_only_the_candidate(self):
        q = R.agent_quote(PROD, 'deepseek-v4-flash')
        self.assertEqual(q['allowed_models'], ['venice:deepseek-v4-flash'])
        self.assertEqual(q['venice_ceiling_usd_per_m'], ['0.14', '0.28'])
        self.assertEqual((q['mode'], q['venice_select']), ('agent', 'order'))
        self.assertEqual(q['max_tokens'], PROD['quote']['max_tokens'])          # production's bounds are kept

    def test_an_unknown_name_raises(self):
        with self.assertRaises(ValueError):
            agent.candidate_profile('gpt-free-forever')

    def test_without_a_candidate_the_agent_profile_is_unchanged(self):
        self.assertEqual(R.agent_quote(PROD)['venice_allowed_models'], list(agent.VENICE_MODELS))


class TheRealGatewaySendsTheCandidate(unittest.TestCase):
    def test_the_candidate_answers_at_its_price(self):
        q = R.agent_quote(PROD, 'deepseek-v4-flash')
        venice = Venice(listed({'deepseek-v4-flash': (0.14, 0.28), 'claude-sonnet-5-5': (2, 10)}))
        self.assertEqual(sent(q, venice), ['deepseek-v4-flash'])

    def test_a_candidate_venice_now_prices_above_its_list_price_is_never_called(self):
        q = R.agent_quote(PROD, 'deepseek-v4-flash')
        # the agent's own model is listed at its price, so only the candidate's raised price can refuse the call
        venice = Venice(listed({'deepseek-v4-flash': (0.5, 2), 'claude-haiku-5-5': (0.1, 0.5),
                                'openai-gpt-6-luna': (0.1, 0.5)}))
        with self.assertRaises(Exception):
            sent(q, venice)
        self.assertEqual(venice.sent_model, [])                                 # refused before any request


class ProductionNeverReadsTheCandidates(unittest.TestCase):
    def test_the_api_quote_takes_the_agent_profile_only(self):
        self.assertNotIn('CANDIDATES', inspect.getsource(B))
        self.assertNotIn('candidate_profile', inspect.getsource(B))
        from omni_prod.conversation import supervisor
        self.assertNotIn('candidate_profile', inspect.getsource(supervisor))

    def test_a_candidate_on_another_path_is_refused(self):
        with mock.patch.dict(os.environ, {R.PATH_ENV: 'production', R.CANDIDATE_ENV: 'deepseek-v4-flash',
                                          'OMNI_DATABASE_URL': 'postgresql://unused'}), \
                mock.patch('omni_prod.db.DatabasePool') as pool, \
                mock.patch.object(R, 'production_quote', return_value=PROD):
            pool.return_value.open.return_value = pool.return_value
            with self.assertRaises(SystemExit) as e:
                R.main(['doors'])
        self.assertIn('agent path only', str(e.exception))


if __name__ == '__main__':
    unittest.main()
