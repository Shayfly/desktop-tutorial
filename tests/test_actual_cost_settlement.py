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


if __name__ == '__main__':
    unittest.main()
