"""A failed build releases its credits; a successful one settles (founder 2026-11-02 20:32).

bld_96ab03c8, bld_99ea49df and bld_2a75e300 all failed, made model calls, and were settle()d: the owner account lost
135 credits for three builds that delivered nothing. Now a failed build goes through release_failed(): the reservation
is RELEASED (never SETTLED), credits_used drops by the reserved credits, the real provider cost stays on record, and a
credit_ledger row is written once per build. The negative control: a READY build still settles and is not released.
"""
import unittest
from decimal import Decimal
from unittest.mock import MagicMock

from omni_prod import worker_tasks
from omni_prod.subscription_store import PostgresSubscriptionService


class ScriptedCursor:
    def __init__(self, row):
        self.row, self.sql = row, []

    def execute(self, sql, params=()):
        self.sql.append((' '.join(sql.split()), params))

    def fetchone(self):
        return self.row

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Ctx:
    def __init__(self, obj):
        self.obj = obj

    def __enter__(self):
        return self.obj

    def __exit__(self, *a):
        return False


def service(row):
    cur = ScriptedCursor(row)
    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.transaction.return_value = _Ctx(None)
    pool = MagicMock()
    pool.connection.return_value = _Ctx(conn)
    svc = PostgresSubscriptionService.__new__(PostgresSubscriptionService)
    svc._pool = pool
    return svc, cur


ROW = ('usr_owner', 'RESERVED', 45, Decimal('0.50'), 'plan', 'prj_1')   # account, status, credits, estimate, funding, project


class ReleaseFailed(unittest.TestCase):
    def test_a_failed_build_gives_back_all_its_credits_and_records_it(self):
        svc, cur = service(ROW)
        out = svc.release_failed(build_id='bld_x', actual_provider_cost_usd=Decimal('0.0267'))
        print('\n[release_failed]', out)
        self.assertEqual(out['credits_refunded'], 45)
        self.assertEqual(out['action'], 'released_failed')
        sql = [s for s, _ in cur.sql]
        self.assertTrue(any("SET status='RELEASED'" in s for s in sql))
        self.assertFalse(any("'SETTLED'" in s for s in sql))
        sub = next(p for s, p in cur.sql if s.startswith('UPDATE creator_subscriptions'))
        self.assertIn('credits_used = GREATEST(0, credits_used - %s)', next(s for s, _ in cur.sql
                                                                            if s.startswith('UPDATE creator_subscriptions')))
        self.assertEqual(sub, (45, Decimal('0.50'), Decimal('0.0267'), 'usr_owner'))   # estimate replaced by the real cost
        ledger = next(p for s, p in cur.sql if s.startswith('INSERT INTO credit_ledger'))
        self.assertEqual(ledger, ('usr_owner', 'prj_1', 45, 'failed_build_released', 'failed-build-release:bld_x'))
        self.assertIn('ON CONFLICT (idempotency_key) DO NOTHING',
                      next(s for s, _ in cur.sql if s.startswith('INSERT INTO credit_ledger')))

    def test_nothing_changes_twice_or_for_a_missing_reservation(self):
        for row in (None, ('usr_owner', 'SETTLED', 45, Decimal('0.5'), 'plan', 'prj_1'),
                    ('usr_owner', 'RELEASED', 45, Decimal('0.5'), 'plan', 'prj_1')):
            with self.subTest(row=row):
                svc, cur = service(row)
                self.assertIsNone(svc.release_failed(build_id='bld_x', actual_provider_cost_usd=Decimal('0.01')))
                self.assertEqual(len(cur.sql), 1)                               # only the SELECT ... FOR UPDATE

    def test_internal_qa_releases_without_touching_the_plan(self):
        svc, cur = service(('usr_owner', 'RESERVED', 45, Decimal('0.5'), 'internal_qa', 'prj_1'))
        out = svc.release_failed(build_id='bld_x')
        self.assertEqual(out['credits_refunded'], 0)
        self.assertFalse(any(s.startswith(('UPDATE creator_subscriptions', 'INSERT INTO credit_ledger')) for s, _ in cur.sql))

    def test_unknown_cost_keeps_the_conservative_estimate_on_record(self):
        svc, cur = service(ROW)
        out = svc.release_failed(build_id='bld_x', actual_provider_cost_usd=None)
        self.assertEqual(out['provider_cost_truth'], 'CONSERVATIVE_RESERVATION')
        self.assertEqual(next(p for s, p in cur.sql if s.startswith('UPDATE credit_reservations')),
                         (None, Decimal('0.50'), 'bld_x'))


class Routing(unittest.TestCase):
    def test_failed_with_spend_is_released_not_settled(self):
        subs = MagicMock()
        self.assertEqual(worker_tasks.resolve_billing(subs, build_id='b', ready=False, spent=Decimal('0.0267'),
                                                      external_calls=3), 'released')
        subs.release_failed.assert_called_once_with(build_id='b', actual_provider_cost_usd=Decimal('0.0267'))
        subs.settle.assert_not_called()

    def test_negative_control_a_ready_build_settles_and_is_not_released(self):
        subs = MagicMock()
        self.assertEqual(worker_tasks.resolve_billing(subs, build_id='b', ready=True, spent=Decimal('0.2'),
                                                      external_calls=3), 'settled')
        subs.settle.assert_called_once_with(build_id='b', actual_provider_cost_usd=Decimal('0.2'))
        subs.release_failed.assert_not_called()
        subs.release.assert_not_called()


if __name__ == '__main__':
    unittest.main()
