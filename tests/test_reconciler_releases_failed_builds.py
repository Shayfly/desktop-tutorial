"""B2 (founder 2026-11-03): one path for one case.

reservation_reconciler SETTLEd a stuck reservation of a FAILED build with metered cost, while the worker's own path
(resolve_billing -> release_failed, #214) RELEASEs the same case. The settle path is deleted: the reconciler's metered
verdict is now 'release_metered' and goes through PostgresSubscriptionService.release_failed.

POSITIVE CONTROL (the gate -- must be green before the negative one counts): a build that SUCCEEDED is still SETTLED:
the reconciler never takes a READY build (not terminal), and the worker settles it.
NEGATIVE CONTROL: a failed reservation with metered cost > 0 -> RELEASED, exactly one credit_ledger row
failed-build-release:<build_id>, credits_used drops by the whole reservation, and provider_spend_usd keeps the metered
cost (the estimate is replaced by it; it is never just removed).
Scripted cursor over the real code; the same two controls on real PostgreSQL: tests/test_reservation_reconciler_pg.py.
"""
import unittest
from decimal import Decimal
from unittest.mock import MagicMock

from omni_prod import reservation_reconciler as rr
from omni_prod import worker_tasks
from omni_prod.subscription_store import PostgresSubscriptionService

ACCOUNT, BUILD = 'usr_owner', 'bld_failed_metered'
RESERVATION = (ACCOUNT, 'RESERVED', 45, Decimal('0.50'), 'customer_plan', 'prj_1')


class Cursor:
    """Answers the reconciler's and release_failed's SELECTs; records every statement."""

    def __init__(self, world):
        self.w, self._last = world, None

    def execute(self, sql, params=()):
        sql = ' '.join(sql.split())
        self.w['sql'].append((sql, params))
        if sql.startswith('SELECT account_id, status, credits_reserved'):
            r = self.w['reservation']
            self._last = ('one', None if r is None else (r[:5] if 'funding_source FROM' in sql and 'project_id' not in sql else r))
        elif sql.startswith('SELECT EXISTS (SELECT 1 FROM build_jobs'):
            self._last = ('one', (self.w['build_status'] in rr.TERMINAL_BUILD,))
        elif sql.startswith('SELECT outcome, metered_cost_usd FROM task_attempts'):
            self._last = ('all', self.w['attempts'])
        elif sql.startswith('UPDATE credit_reservations SET status=') and self.w['reservation']:
            self.w['reservation'] = (self.w['reservation'][0], 'RELEASED') + self.w['reservation'][2:]
        return self

    def fetchone(self):
        return self._last[1]

    def fetchall(self):
        return self._last[1]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Ctx:
    def __init__(self, obj=None):
        self.obj = obj

    def __enter__(self):
        return self.obj

    def __exit__(self, *a):
        return False


def service(build_status, attempts, reservation=RESERVATION):
    world = {'sql': [], 'build_status': build_status, 'attempts': attempts, 'reservation': reservation}
    conn = MagicMock()
    conn.cursor.side_effect = lambda: Cursor(world)
    conn.transaction.side_effect = lambda: _Ctx()
    pool = MagicMock()
    pool.connection.side_effect = lambda: _Ctx(conn)
    svc = PostgresSubscriptionService.__new__(PostgresSubscriptionService)
    svc._pool = pool
    return svc, world


def writes(world):
    return [(s, p) for s, p in world['sql'] if not s.startswith('SELECT')]


class PositiveControlSuccessfulBuildStillSettles(unittest.TestCase):
    """The gate. If this is not green, the negative control proves nothing."""

    def test_the_reconciler_never_takes_a_ready_build(self):
        self.assertNotIn('ready', rr.TERMINAL_BUILD)
        self.assertNotIn('READY', rr.TERMINAL_MODIFICATION)
        svc, world = service('ready', [('ok', Decimal('0.12'))])
        out = svc.reconcile_terminal_reservation(build_id=BUILD)
        print('\n[POSITIVE reconciler on a READY build]', out, '| writes:', writes(world))
        self.assertEqual((out['action'], out['applied']), ('hold', False))
        self.assertEqual(writes(world), [])                      # nothing released, nothing settled by the reconciler

    def test_the_worker_settles_a_successful_build(self):
        subs = MagicMock()
        billing = worker_tasks.resolve_billing(subs, build_id=BUILD, ready=True, spent=Decimal('0.12'), external_calls=2)
        print('[POSITIVE worker on a READY build]', billing, subs.method_calls)
        self.assertEqual(billing, 'settled')
        subs.settle.assert_called_once_with(build_id=BUILD, actual_provider_cost_usd=Decimal('0.12'))
        subs.release_failed.assert_not_called()
        subs.release.assert_not_called()


class NegativeControlFailedMeteredIsReleased(unittest.TestCase):
    def test_failed_with_metered_cost_is_released_in_full_with_one_ledger_row(self):
        svc, world = service('failed', [('ok', Decimal('0.10')), ('error', Decimal('0.02'))])
        out = svc.reconcile_terminal_reservation(build_id=BUILD)
        w = writes(world)
        print('\n[NEGATIVE reconciler on a failed metered build]', out)
        for s, p in w:
            print('   ', s[:110], p)
        self.assertEqual((out['action'], out['applied'], out['metered_usd']), ('release_metered', True, '0.12'))
        self.assertEqual(world['reservation'][1], 'RELEASED')
        self.assertFalse(any("'SETTLED'" in s for s, _ in w))                     # no settle anywhere
        sub = [(s, p) for s, p in w if s.startswith('UPDATE creator_subscriptions')]
        self.assertEqual(len(sub), 1)
        self.assertIn('credits_used = GREATEST(0, credits_used - %s)', sub[0][0])
        self.assertIn('provider_spend_usd = GREATEST(0, provider_spend_usd - %s + %s)', sub[0][0])
        self.assertEqual(sub[0][1], (45, Decimal('0.50'), Decimal('0.12'), ACCOUNT))   # whole 45 back; 0.12 kept
        ledger = [p for s, p in w if s.startswith('INSERT INTO credit_ledger')]
        self.assertEqual(ledger, [(ACCOUNT, 'prj_1', 45, 'failed_build_released', f'failed-build-release:{BUILD}')])

    def test_a_second_pass_changes_nothing(self):
        svc, world = service('failed', [('ok', Decimal('0.10'))])
        svc.reconcile_terminal_reservation(build_id=BUILD)
        n = len(writes(world))
        again = svc.reconcile_terminal_reservation(build_id=BUILD)
        self.assertEqual((again['action'], again['applied']), ('none', False))
        self.assertEqual(len(writes(world)), n)

    def test_the_verdict_has_no_settle_any_more(self):
        class Cur:
            def __init__(self, rows):
                self.rows = rows

            def execute(self, *a):
                pass

            def fetchall(self):
                return self.rows
        for rows in ([('ok', Decimal('0.10'))], [('error', None)], [('unknown', None)], [('ok', None)], []):
            self.assertNotEqual(rr.verdict(Cur(rows), 'b')[0], 'settle')


if __name__ == '__main__':
    unittest.main()
