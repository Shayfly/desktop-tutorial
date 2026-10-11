"""Worker-routed intake (Issue #12): no unreserved path exists; the API-side
interpreter reserves before enqueueing and degrades to deterministic on every
failure. Unit level with a fake reservation service -- real PostgreSQL
end-to-end coverage is in tests/test_intake_budget_pg.py. No provider calls."""
import os
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod.intake import budget as B
from omni_prod.intake import worker_route as W

MSG = 'אני צריך אתר תורים בלי התחברות'


class LegacyPathTests(unittest.TestCase):
    def test_unreserved_execution_is_refused_whatever_the_env(self):
        env = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_CALL_BUDGET_USD': '1'}
        with mock.patch.dict(os.environ, env):
            out = W.execute(MSG, gateway_factory=lambda cap: self.fail('gateway must not be built'))
        self.assertFalse(out['ok'])
        self.assertIn('reservation', out['error'])
        from omni_prod import worker_tasks
        with mock.patch.dict(os.environ, env):
            self.assertFalse(worker_tasks.execute_intake_interpretation(MSG)['ok'])


class FakeService:
    def __init__(self, *, reserve_exc=None, final=None, never_settles=False):
        self.reserve_exc, self.final, self.never = reserve_exc, final, never_settles
        self.released, self.enqueued, self.reserved = [], [], []

    def reserve(self, **kw):
        if self.reserve_exc:
            raise self.reserve_exc
        self.reserved.append(kw)
        return B.Reservation('irs_1', kw['idempotency_key'], kw['account_id'], kw['project_id'], kw['lane'], None,
                             kw['quote_'].amount_usd, B.RESERVED)

    def mark_enqueued(self, rid):
        self.enqueued.append(rid)

    def release(self, rid, *, reason):
        self.released.append((rid, reason))
        return True

    def get(self, rid, account_id=None):
        if self.never or self.final is None:
            return B.Reservation(rid, 'k', 'acct', 'p', 'production', None, Decimal('0.004'), B.EXECUTING)
        return self.final


def interp(service, enqueue=lambda rid: None, wait=1.0):
    ticks = iter([0.0] + [0.1 * i for i in range(1, 200)])
    return W.ReservedWorkerInterpreter(service, enqueue, account_id='acct', project_id='p', request_key='rk',
                                       caps=B.Caps(Decimal('1'), Decimal('1')), wait_seconds=wait,
                                       sleep=lambda s: None, clock=lambda: next(ticks))


def settled(state, cost_state, actual, result, model='gemini-3.1-flash-lite'):
    return B.Reservation('irs_1', 'k', 'acct', 'p', 'production', None, Decimal('0.004'), state, cost_state, actual,
                         None if state != B.UNKNOWN else 'timeout', None, 'gemini', model, result)


class ApiSideTests(unittest.TestCase):
    RAW = {'language': 'he', 'product_family': 'web_app', 'proposals': [
        {'field': 'login', 'value': 'none', 'confidence': 'high', 'evidence': 'בלי התחברות'},
        {'field': 'login_methods', 'value': 'email', 'confidence': 'high', 'evidence': 'מייל'}]}   # not in message

    def test_settled_result_is_revalidated_merged_and_costed(self):
        svc = FakeService(final=settled(B.SETTLED, B.ESTIMATED, Decimal('0.0012'), {'ok': True, 'raw': self.RAW}))
        it = interp(svc).interpret(MSG)
        self.assertEqual(svc.enqueued, ['irs_1'])
        self.assertIn('login', {p.field for p in it.proposals})
        self.assertNotIn('login_methods', {p.field for p in it.proposals})   # hallucinated evidence dropped
        self.assertEqual((it.cost_usd, it.cost_state, it.reservation_id), ('0.0012', 'ESTIMATED', 'irs_1'))
        self.assertTrue(it.interpreter.startswith('model:gemini-3.1-flash-lite'))
        self.assertTrue(svc.reserved[0]['idempotency_key'].startswith('intake:acct:p:rk:'))

    def test_unknown_cost_is_never_zero(self):
        svc = FakeService(final=settled(B.UNKNOWN, B.COST_UNKNOWN, None, {'ok': False, 'error': 'TimeoutError'}))
        it = interp(svc).interpret(MSG)
        self.assertEqual((it.cost_usd, it.cost_state, it.interpreter), (None, 'UNKNOWN', 'deterministic'))

    def test_timeout_leaves_cost_pending_on_the_reservation(self):
        it = interp(FakeService(never_settles=True), wait=0.5).interpret(MSG)
        self.assertEqual((it.cost_usd, it.cost_state, it.reservation_id), (None, 'PENDING', 'irs_1'))

    def test_enqueue_failure_releases_immediately(self):
        def down(rid):
            raise ConnectionError('redis down')
        svc = FakeService()
        it = interp(svc, enqueue=down).interpret(MSG)
        self.assertEqual(svc.released[0][0], 'irs_1')
        self.assertEqual((it.interpreter, it.cost_state), ('deterministic', 'CONFIRMED_ZERO'))

    def test_budget_quote_and_db_failures_fall_back(self):
        for exc in (B.BudgetExceeded('daily:global', Decimal('1'), Decimal('1'), Decimal('0.004')),
                    B.IdempotencyConflict('x'), RuntimeError('relation "intake_reservations" does not exist')):
            with self.subTest(exc=type(exc).__name__):
                it = interp(FakeService(reserve_exc=exc)).interpret(MSG)
                self.assertEqual(it.interpreter, 'deterministic')
                self.assertTrue(any('model not used' in x for x in it.dropped))
        with mock.patch.object(B, 'quote', side_effect=B.QuoteUnavailable('no price')):
            it = interp(FakeService()).interpret(MSG)
        self.assertIn('model not used: no price', it.dropped)

    def test_malformed_model_output_falls_back_but_keeps_cost(self):
        bad = {'ok': True, 'raw': {'proposals': 'not a list'}}
        it = interp(FakeService(final=settled(B.SETTLED, B.CONFIRMED, Decimal('0.0009'), bad))).interpret(MSG)
        self.assertEqual((it.interpreter, it.cost_usd, it.cost_state), ('deterministic', '0.0009', 'CONFIRMED'))


if __name__ == '__main__':
    unittest.main()
