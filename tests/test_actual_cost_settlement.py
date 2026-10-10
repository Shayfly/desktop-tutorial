"""Settlement charges metered usage, not the reservation ceiling (autonomous
completion directive §3; real-server: $0.1209 used, $0.50 settled)."""
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from omni_prod import worker_tasks


def rec(metered, version='pc-1', authorized='0.05'):
    return SimpleNamespace(kind='provider_call', authorized_cost_usd=Decimal(authorized),
                           metered_cost_usd=None if metered is None else Decimal(metered),
                           price_catalog_version=version)


def gateway(records):
    return SimpleNamespace(recorder=SimpleNamespace(records=records), usage=None,
                           state=SimpleNamespace(external_spend_usd=sum((r.metered_cost_usd or Decimal('0.05')
                                                                         for r in records), Decimal('0'))))


class MeteredCostTests(unittest.TestCase):
    def test_all_calls_metered_gives_the_exact_sum_and_catalog_version(self):
        cost, basis = worker_tasks.metered_llm_cost(gateway([rec('0.01'), rec('0.0209'), rec('0')]), 3)
        self.assertEqual(cost, Decimal('0.0309'))
        self.assertEqual(basis['llm'], 'METERED_USAGE_X_PRICE_CATALOG')
        self.assertEqual(basis['price_catalog_versions'], ['pc-1'])

    def test_one_call_without_usage_makes_the_cost_unknown_not_zero(self):
        cost, basis = worker_tasks.metered_llm_cost(gateway([rec('0.01'), rec(None)]), 2)
        self.assertIsNone(cost)
        self.assertEqual(basis['llm'], 'UNKNOWN_USAGE_NOT_REPORTED')

    def test_a_call_missing_from_the_records_makes_it_unknown(self):
        cost, basis = worker_tasks.metered_llm_cost(gateway([rec('0.01')]), 2)
        self.assertIsNone(cost)

    def test_local_calls_are_not_counted(self):
        local = rec('0', authorized='0')
        cost, _ = worker_tasks.metered_llm_cost(gateway([local, rec('0.02')]), 1)
        self.assertEqual(cost, Decimal('0.02'))


class SettlementTests(unittest.TestCase):
    def _settle(self, records, calls):
        subs = MagicMock()
        subs.settle.return_value = {'settled_provider_cost_usd': 'x'}
        gw = gateway(records)
        from unittest.mock import patch
        with patch.object(worker_tasks, 'spend_snapshot', return_value=(Decimal('0.03'), calls)):
            out = worker_tasks.resolve_m5_billing(subs, build_id='b', ready=True, gateway=gw, capability_evidence=None,
                                                  economics_quote={'infrastructure_maximum_usd': '0', 'revenue_usd': '1.00'})
        return subs, out

    def test_metered_actual_is_settled_and_the_rest_released(self):
        subs, (billing, evidence, actual) = self._settle([rec('0.0121'), rec('0.0088')], 2)
        self.assertEqual(actual, Decimal('0.0209'))
        subs.settle.assert_called_once()
        self.assertEqual(subs.settle.call_args.kwargs['actual_provider_cost_usd'], Decimal('0.0209'))
        self.assertEqual(evidence['cost_basis']['llm'], 'METERED_USAGE_X_PRICE_CATALOG')

    def test_unknown_usage_keeps_the_conservative_policy_explicitly(self):
        subs, (billing, evidence, actual) = self._settle([rec('0.0121'), rec(None)], 2)
        self.assertIsNone(actual)
        self.assertIsNone(subs.settle.call_args.kwargs['actual_provider_cost_usd'])
        self.assertEqual(evidence['cost_basis']['llm'], 'UNKNOWN_USAGE_NOT_REPORTED')


class RecoveredBuildSettlementTests(unittest.TestCase):
    """Crash run 37951691638: the killed worker's calls never reached the
    ledger, so settlement counted only the recovering worker's calls."""

    def _settle(self, records, calls, prior):
        subs = MagicMock()
        subs.settle.return_value = {}
        gw = gateway(records)
        gw.prior_metered = prior
        from unittest.mock import patch
        with patch.object(worker_tasks, 'spend_snapshot', return_value=(Decimal('0.03'), calls)):
            return subs, worker_tasks.resolve_m5_billing(subs, build_id='b', ready=True, gateway=gw, capability_evidence=None,
                                                         economics_quote={'infrastructure_maximum_usd': '0'})

    def test_earlier_workers_metered_calls_are_added(self):
        subs, (_, evidence, actual) = self._settle([rec('0.05')], 1,
                                                   {'calls': 2, 'metered_usd': Decimal('0.012'), 'unknown_calls': 0})
        self.assertEqual(actual, Decimal('0.062'))
        self.assertEqual(evidence['cost_basis']['earlier_workers']['metered_usd'], '0.012')

    def test_unmetered_earlier_call_makes_the_actual_unknown(self):
        _, (_, _, actual) = self._settle([rec('0.05')], 1, {'calls': 1, 'metered_usd': Decimal('0'), 'unknown_calls': 1})
        self.assertIsNone(actual)

    def test_spend_by_a_lost_worker_is_settled_not_released(self):
        subs = MagicMock()
        gw = gateway([])
        gw.prior_metered = {'calls': 1, 'metered_usd': Decimal('0.01'), 'unknown_calls': 0}
        from unittest.mock import patch
        with patch.object(worker_tasks, 'spend_snapshot', return_value=(Decimal('0'), 0)):
            billing, _, actual = worker_tasks.resolve_m5_billing(subs, build_id='b', ready=False, gateway=gw, capability_evidence=None,
                                                                 economics_quote={'infrastructure_maximum_usd': '0'})
        self.assertEqual(billing, 'settled')
        self.assertEqual(actual, Decimal('0.01'))
        subs.release.assert_not_called()


class LedgerFlushTests(unittest.TestCase):
    def test_attempts_are_flushed_at_every_model_call_and_check(self):
        from omni_prod.build_control import BuildControl, ControlledExecutor
        flushed = []
        control = BuildControl(MagicMock(checkpoint=MagicMock(return_value=False)), 'b')
        control.flush = lambda: flushed.append(1)
        control.before_model_call('codegen')
        inner = SimpleNamespace(execute=lambda **k: SimpleNamespace(passed=True, failures=()))
        ControlledExecutor(inner, control).execute(repository={}, spec=None)
        self.assertEqual(len(flushed), 2)

    def test_a_failing_flush_never_fails_the_build(self):
        from omni_prod.build_control import BuildControl
        control = BuildControl(MagicMock(checkpoint=MagicMock(return_value=False)), 'b')
        control.flush = MagicMock(side_effect=OSError('db down'))
        control.before_model_call('codegen')
        self.assertEqual(control.model_calls, 1)



class ThinkingTokenMeteringTests(unittest.TestCase):
    """Gemini's OpenAI-compatible usage leaves thinking out of
    completion_tokens (only in total_tokens) but bills it as output."""

    def _usage(self, usage):
        from omni_prod.provider_usage import parse_openai_compatible_usage
        return parse_openai_compatible_usage({'id': 'r', 'usage': usage}, {}, provider='p', model='m', external=True)

    def test_hidden_thinking_is_billed_as_output(self):
        u = self._usage({'prompt_tokens': 12000, 'completion_tokens': 3700, 'total_tokens': 29500})
        self.assertEqual(u.output_tokens, 17500)

    def test_openai_style_usage_is_not_double_counted(self):
        u = self._usage({'prompt_tokens': 100, 'completion_tokens': 900, 'total_tokens': 1000,
                         'completion_tokens_details': {'reasoning_tokens': 700}})
        self.assertEqual(u.output_tokens, 900)

    def test_usage_without_total_is_unchanged(self):
        self.assertEqual(self._usage({'input_tokens': 10, 'output_tokens': 20}).output_tokens, 20)



@unittest.skipUnless(__import__('os').environ.get('M4D2_DATABASE_URL'), 'live PostgreSQL not configured')
class WriteAheadLedgerLivePostgresTests(unittest.TestCase):
    """Issue #6 P3.3: the call in flight at a worker crash is UNKNOWN cost
    exposure bounded by its authorization -- not zero, not exact."""

    def setUp(self):
        import os
        from pathlib import Path
        from omni_prod.db import DatabasePool
        self.pool = DatabasePool(os.environ['M4D2_DATABASE_URL'])
        sql = (Path(__file__).resolve().parents[1] / 'infra/postgres/027_task_attempts.sql').read_text()
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute(sql)

    def _rec(self, **kw):
        from omni_prod.attempt_ledger import AttemptRecord
        base = dict(task_type='codegen', attempt_seq=0, kind='provider_call', outcome='unknown', provider='p', model='m',
                    authorized_cost_usd=Decimal('0.07'))
        base.update(kw)
        return AttemptRecord(**base)

    def test_in_flight_row_is_completed_later_and_never_overwritten(self):
        import uuid
        from omni_prod.attempt_ledger import persist_attempts
        bid = f'bld_{uuid.uuid4().hex[:10]}'
        r = self._rec()
        persist_attempts(self.pool, [r], build_id=bid)                       # written ahead, before the call
        r.outcome, r.metered_cost_usd, r.input_tokens, r.output_tokens = 'ok', Decimal('0.012'), 1000, 2000
        persist_attempts(self.pool, [r], build_id=bid)                       # completed after the call
        r.metered_cost_usd = None
        persist_attempts(self.pool, [r], build_id=bid, final_outcome='ready')  # a later flush cannot erase it
        with self.pool.connection() as conn:
            row = conn.execute('SELECT outcome, metered_cost_usd, output_tokens, final_outcome FROM task_attempts '
                               'WHERE attempt_id = %s', (r.attempt_id,)).fetchone()
        self.assertEqual((row[0], Decimal(str(row[1])), row[2], row[3]), ('ok', Decimal('0.012'), 2000, 'ready'))

    def test_a_crash_leaves_bounded_unknown_exposure(self):
        import uuid
        from omni_prod.attempt_ledger import persist_attempts
        bid = f'bld_{uuid.uuid4().hex[:10]}'
        done = self._rec(outcome='ok', metered_cost_usd=Decimal('0.01'), attempt_seq=0)
        in_flight = self._rec(attempt_seq=1, authorized_cost_usd=Decimal('0.09'))
        persist_attempts(self.pool, [done, in_flight], build_id=bid)          # then the worker is killed
        prior = worker_tasks.prior_worker_metered_cost(self.pool, bid)
        self.assertEqual(prior['unknown_calls'], 1)
        self.assertEqual(prior['unknown_exposure_usd'], Decimal('0.09'))
        gw = gateway([rec('0.05')])
        gw.prior_metered = prior
        from unittest.mock import patch
        with patch.object(worker_tasks, 'spend_snapshot', return_value=(Decimal('0.05'), 1)):
            _, evidence, actual = worker_tasks.resolve_m5_billing(MagicMock(), build_id=bid, ready=True, gateway=gw,
                                                                  capability_evidence=None,
                                                                  economics_quote={'infrastructure_maximum_usd': '0'})
        self.assertIsNone(actual)                                            # unknown, settled conservatively
        self.assertEqual(Decimal(evidence['cost_basis']['earlier_workers']['unknown_exposure_usd']), Decimal('0.09'))

if __name__ == '__main__':
    unittest.main()
