"""One call, one sum: the meter prices a call by its id, never by the whole ledger (owner 2026-11-18).

`reservation_worker.meter` summed every provider attempt in the gateway's ledger. The routed gateway's ledger keeps
every attempt of its life, so on a gateway shared by many turns turn k paid for turns 1..k: every routed rehearsal
cost to 2026-11-18 (runs 44126201300, 44141955553, 44263232985) is invalid. Production was not hit: there each turn is
one reservation on a fresh gateway.

The owner's rule: the meter takes a call id and sums only the attempts carrying it; ten turns give ten sums, and the
mutation stays (tests/negative_controls/meter_by_call_id.json). Everything below runs the real RoutedModelGateway,
the real ModelInterpreter and the real meter; only the provider transport is a fake, and each call it answers costs a
different amount, so a cumulative sum cannot pass for a per-call one.
"""
import json
import os
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from omni_prod.intake import budget as B
from omni_prod.intake import reservation_worker as W
from omni_prod.intake.interpreter import ModelInterpreter
from omni_prod.intake.reservation_worker import MeterError, meter
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
                        external_budget_usd=Decimal("5"), max_external_calls_per_build=100)
ANSWER = {'language': 'he', 'product_family': 'website', 'proposals': [], 'requirements': []}


class _Transport:
    """The n-th answered call reports cost n/1000 (0.001, 0.002, ...). `fail` names routes that error without usage."""
    answered = 0
    fail: set = set()

    def __init__(self, endpoint):
        self.endpoint, self.last_usage, self.last_response_model = endpoint, None, None

    def _answer(self):
        if self.endpoint.name in _Transport.fail:
            raise ModelGatewayError('model request failed: HTTP 503')
        _Transport.answered += 1
        self.last_usage = ProviderUsage(
            provider=self.endpoint.name, model=self.endpoint.model, external=True,
            request_id=f'req-{_Transport.answered}', request_id_source='header', response_id=None,
            input_tokens=1000, output_tokens=500, cached_tokens=None,
            provider_reported_cost_usd=Decimal(_Transport.answered) / 1000, usage_reported=True)

    def complete_json(self, **kw):
        self._answer()
        return dict(ANSWER)

    def complete(self, **kw):
        self._answer()
        return 'ok'


def _routed():
    _Transport.answered, _Transport.fail = 0, set()
    return RoutedModelGateway(ranked=parse_model_catalog(json.dumps(CATALOG), {'KEY_ONE': 'a', 'KEY_TWO': 'b'}),
                              routing_policy=RoutingPolicy(minimum_quality=70), policy=POLICY,
                              gateway_factory=_Transport, transient_retries=0)


def setUpModule():
    global _ENV
    _ENV = mock.patch.dict(os.environ, {'OMNI_MODEL_TASK_MIN_QUALITY': '{"conversation": 0}'})
    _ENV.start()


def tearDownModule():
    _ENV.stop()


class TenTurnsTenSums(unittest.TestCase):
    def test_ten_turns_on_one_gateway_give_ten_sums_each_its_own_call(self):
        gw = _routed()
        interp = ModelInterpreter(gw)
        costs = [interp.interpret(f'אתר לחנות פרחים, תור {i}').cost_usd for i in range(1, 11)]
        # each turn is exactly its own call: 0.001 .. 0.010. The cumulative sum gave 0.001, 0.003, 0.006, ... 0.055.
        self.assertEqual(costs, [str(Decimal(i) / 1000) for i in range(1, 11)])
        self.assertEqual(len(gw.recorder.records), 10)                    # the ledger still keeps all ten
        self.assertEqual(len({r.call_id for r in gw.recorder.records}), 10)  # one id per turn

    def test_a_call_that_fell_back_counts_both_its_attempts_and_nothing_else(self):
        gw = _routed()
        gw.complete_json(system='S', user='earlier turn', max_tokens=300, call_id='call-earlier')  # costs 0.001
        first = next(e.provider for e in gw.events if e.ok)
        _Transport.fail = {first}
        gw.complete_json(system='S', user='this turn', max_tokens=300, call_id='call-now')
        m = meter(gw, {'max_tokens': 300}, call_id='call-now')
        # the failed attempt reported no usage: the call's cost is UNKNOWN (held), never the earlier turn's 0.001
        self.assertEqual((m['attempts'], m['cost_state'], m['actual_usd']), (2, B.COST_UNKNOWN, None))
        self.assertEqual(meter(gw, {'max_tokens': 300}, call_id='call-earlier')['actual_usd'], Decimal('0.001'))


class EveryAttemptCarriesItsCall(unittest.TestCase):
    def test_the_routed_gateway_stamps_every_attempt_and_event_of_a_call(self):
        gw = _routed()
        _Transport.fail = {'first', 'second'}
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(system='S', user='U', max_tokens=300, call_id='call-x')
        self.assertEqual({r.call_id for r in gw.recorder.records}, {'call-x'})
        self.assertTrue(gw.events and all(e.call_id == 'call-x' for e in gw.events))

    def test_a_call_without_an_id_still_gets_its_own_one(self):
        gw = _routed()                                                     # a build names no call: one id per call
        gw.complete(system='S', user='a')
        gw.complete(system='S', user='b')
        ids = [r.call_id for r in gw.recorder.records]
        self.assertTrue(all(i and i.startswith('call_') for i in ids))
        self.assertEqual(len(set(ids)), 2)


class TheMeterIsLoud(unittest.TestCase):
    def test_no_call_id_is_refused(self):
        gw = _routed()
        for bad in ('', None):
            with self.subTest(call_id=bad), self.assertRaises(MeterError):
                meter(gw, {'max_tokens': 300}, call_id=bad)

    def test_a_gateway_without_a_ledger_is_refused(self):
        with self.assertRaises(MeterError):
            meter(SimpleNamespace(), {'max_tokens': 300}, call_id='call-1')

    def test_an_attempt_without_a_call_id_is_refused_never_priced_as_zero(self):
        gw = SimpleNamespace(recorder=SimpleNamespace(records=[SimpleNamespace(
            kind='provider_call', provider='p', model='m', provider_reported_cost_usd=Decimal('0.004'),
            input_tokens=10, output_tokens=10, metered_cost_usd=None, outcome='ok', failure_reason=None,
            provider_request_id='r')]))
        with self.assertRaises(MeterError):
            meter(gw, {'max_tokens': 300}, call_id='call-1')

    def test_a_call_with_no_attempt_is_not_contacted(self):
        gw = _routed()
        gw.complete_json(system='S', user='U', max_tokens=300, call_id='call-other')
        m = meter(gw, {'max_tokens': 300}, call_id='call-never-sent')
        self.assertEqual((m['contacted'], m['cost_state'], m['actual_usd']), (False, B.CONFIRMED_ZERO, Decimal('0')))


class TheInterpreterPricesEachTurnAlone(unittest.TestCase):
    def test_a_gateway_that_cannot_carry_a_call_id_is_refused_when_built(self):
        class Untagged:
            recorder = SimpleNamespace(records=[])

            def complete_json(self, **kw):
                return dict(ANSWER)
        with self.assertRaises(TypeError):
            ModelInterpreter(Untagged())

    def test_an_unattributable_turn_is_unknown_and_says_why_not_zero(self):
        class Broken:                       # claims call ids but writes an attempt without one
            accepts_call_id = True

            def __init__(self):
                self.recorder = SimpleNamespace(records=[])

            def complete_json(self, **kw):
                self.recorder.records.append(SimpleNamespace(
                    kind='provider_call', provider='p', model='m', provider_reported_cost_usd=Decimal('0.004'),
                    input_tokens=10, output_tokens=10, metered_cost_usd=None, outcome='ok', failure_reason=None,
                    provider_request_id='r', call_id=None))
                return dict(ANSWER)
        it = ModelInterpreter(Broken()).interpret('אתר לחנות פרחים')
        self.assertEqual((it.cost_usd, it.cost_state), (None, B.COST_UNKNOWN))
        self.assertTrue(any(x.startswith('cost unknown:') for x in it.dropped), it.dropped)


class TheReservationIsTheCall(unittest.TestCase):
    def _execute(self, gateway):
        settled = {}

        class Svc:
            def __init__(self, pool): pass
            def claim(self, rid, **kw):
                return mock.Mock(id=rid, quote={'task': 'conversation', 'max_tokens': 300}, quoted_usd=Decimal('0.05'))
            def payload(self, rid): return {'system': 'S', 'user': 'U', 'max_tokens': 300, 'task': 'conversation'}
            def mark_executing(self, r, **kw): return True
            def release(self, rid, **kw): settled['released'] = kw
            def settle(self, r, **kw):
                settled.update(kw)
                return mock.Mock(state='SETTLED', cost_state=kw['cost_state'], actual_usd=kw['actual_usd'],
                                 model=kw.get('model'))
        with mock.patch.object(B, 'ReservationService', Svc), \
                mock.patch.dict(os.environ, {}):
            W.execute_reservation(None, 'irs_7', worker_id='w', gateway_factory=lambda quoted, models: gateway)
        return settled

    def test_the_worker_prices_the_reservation_by_its_own_id(self):
        gw = _routed()
        gw.complete_json(system='S', user='an earlier call on the same ledger', max_tokens=300, call_id='call-old')
        settled = self._execute(gw)
        self.assertEqual((settled['cost_state'], settled['actual_usd']), (B.CONFIRMED, Decimal('0.002')))
        self.assertEqual(settled['metering']['call_id'], 'irs_7')
        self.assertEqual([r.call_id for r in gw.recorder.records], ['call-old', 'irs_7'])

    def test_an_unattributable_cost_is_settled_unknown_never_zero(self):
        class Broken:
            def __init__(self):
                self.recorder = SimpleNamespace(records=[])

            def complete_json(self, **kw):
                self.recorder.records.append(SimpleNamespace(kind='provider_call', provider='p', model='m'))
                return dict(ANSWER)
        settled = self._execute(Broken())
        self.assertEqual((settled['cost_state'], settled['actual_usd']), (B.COST_UNKNOWN, None))
        self.assertIn('meter:', settled['failure_reason'])


if __name__ == '__main__':
    unittest.main()
