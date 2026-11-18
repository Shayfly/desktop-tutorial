"""The routed rehearsal says which model answered each turn, which route refused and why, and prices each turn alone.

Run 44263232985 (2026-11-18, routed, `bare`) passed with provider_models=None: it was run to prove the Anthropic credit
and could not say whether Sonnet answered. Its cost, like every routed rehearsal cost to that day, summed the routed
gateway's whole-run ledger at every turn and is invalid (owner 2026-11-18). The routed gateway here is the real
RoutedModelGateway with its real route events, attempt ledger and health book, the real ModelInterpreter and the real
meter; only the provider transport is a fake."""
import json
import os
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod.intake.interpreter import ModelInterpreter
from omni_prod.model_catalog import parse_model_catalog
from omni_prod.model_gateway import ModelGatewayError
from omni_prod.model_policy import ModelUsePolicy
from omni_prod.model_router import RoutingPolicy
from omni_prod.provider_usage import ProviderUsage
from omni_prod.routed_gateway import RoutedModelGateway

CATALOG = [
    {"name": "first", "provider": "p1", "base_url": "https://a.example/v1", "model": "m-first",
     "api_key_env": "KEY_ONE", "quality": 90, "input_per_million": "1", "output_per_million": "2"},
    {"name": "second", "provider": "p2", "base_url": "https://b.example/v1", "model": "m-second",
     "api_key_env": "KEY_TWO", "quality": 90, "input_per_million": "1", "output_per_million": "2"},
]
POLICY = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                        external_budget_usd=Decimal("5"), max_external_calls_per_build=50)
CREDIT = 'model request failed: HTTP 400: Your credit balance is too low to access the Anthropic API.'


class _Transport:
    refuse: set = set()
    answered = 0

    def __init__(self, endpoint):
        self.endpoint, self.last_usage, self.last_response_model = endpoint, None, None

    def complete_json(self, **kw):
        if self.endpoint.name in _Transport.refuse:
            raise ModelGatewayError(CREDIT)
        _Transport.answered += 1                      # the n-th answer costs n/1000: a summed ledger cannot hide
        self.last_usage = ProviderUsage(
            provider=self.endpoint.name, model=self.endpoint.model, external=True, request_id='req',
            request_id_source='header', response_id=None, input_tokens=1000, output_tokens=500, cached_tokens=None,
            provider_reported_cost_usd=Decimal(_Transport.answered) / 1000, usage_reported=True)
        return {'language': 'he', 'product_family': 'website', 'proposals': [], 'requirements': []}


def _routed():
    _Transport.refuse, _Transport.answered = set(), 0
    return RoutedModelGateway(ranked=parse_model_catalog(json.dumps(CATALOG), {'KEY_ONE': 'a', 'KEY_TWO': 'b'}),
                              routing_policy=RoutingPolicy(minimum_quality=70), policy=POLICY,
                              gateway_factory=_Transport, transient_retries=0)


def _call(gw, call_id):
    return gw.complete_json(system='S', user='U', max_tokens=300, call_id=call_id)


def setUpModule():
    global _ENV
    _ENV = mock.patch.dict(os.environ, {'OMNI_MODEL_TASK_MIN_QUALITY': '{"conversation": 0}'})
    _ENV.start()


def tearDownModule():
    _ENV.stop()


class TheRoutedPathSaysWhoAnswered(unittest.TestCase):
    def test_the_route_that_answered_is_recorded(self):
        gw = R.RoutedPathGateway(_routed())
        _call(gw, 'call-1')
        self.assertEqual(len(gw.models_used), 1)
        self.assertRegex(gw.models_used[0], r'^(first:m-first|second:m-second)$')
        self.assertEqual(gw.route_failures, [])

    def test_a_route_that_refused_is_named_with_its_reason_and_the_fallback_that_answered(self):
        probe = R.RoutedPathGateway(_routed())
        _call(probe, 'call-1')
        chosen = probe.models_used[0].split(':')[0]
        other = 'second' if chosen == 'first' else 'first'
        routed = _routed()
        _Transport.refuse = {chosen}
        gw = R.RoutedPathGateway(routed)
        _call(gw, 'call-1')
        self.assertEqual([m.split(':')[0] for m in gw.models_used], [other])
        self.assertTrue(any(f.startswith(chosen + ':') and 'credit balance is too low' in f for f in gw.route_failures),
                        gw.route_failures)

    def test_each_turn_names_only_its_own_routes(self):
        gw = R.RoutedPathGateway(_routed())
        _call(gw, 'call-1')
        _call(gw, 'call-2')
        self.assertEqual(len(gw.models_used), 2)                 # turn 1's answer is not counted again in turn 2
        self.assertEqual(len(gw.routed.events), 2)

    def test_a_gateway_without_route_events_or_call_ids_is_loud(self):
        with self.assertRaises(SystemExit):
            R.RoutedPathGateway(object())

    def test_a_call_without_an_id_is_refused(self):
        gw = R.RoutedPathGateway(_routed())
        with self.assertRaises(ValueError):
            gw.complete_json(system='S', user='U', max_tokens=300, call_id='')


class EachTurnCostsOnlyItsOwnCall(unittest.TestCase):
    def test_three_turns_of_a_rehearsal_are_three_sums(self):
        gw = R.RoutedPathGateway(_routed())
        interp = ModelInterpreter(gw)
        costs = [interp.interpret(f'אתר לחנות פרחים, תור {i}').cost_usd for i in range(1, 4)]
        self.assertEqual(costs, ['0.001', '0.002', '0.003'])     # the summed ledger gave 0.001, 0.003, 0.006
        self.assertEqual(len(gw.routed.recorder.records), 3)      # the run's ledger still keeps all three


if __name__ == '__main__':
    unittest.main()
