"""The reconciler's rules without a database (the real-PostgreSQL proof is tests/test_reservation_reconciler_pg.py)."""
from __future__ import annotations

import unittest
from decimal import Decimal

from omni_prod.reservation_reconciler import verdict


class Cur:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, sql, params=None):
        self.sql = sql

    def fetchall(self):
        return self.rows


class TheVerdict(unittest.TestCase):
    def test_finished_and_unmetered_is_released(self):
        self.assertEqual(verdict(Cur([('error', None)]), 'b')[0], 'release')
        self.assertEqual(verdict(Cur([]), 'b')[0], 'release')                     # no call was ever made

    def test_metered_work_is_settled_on_its_total(self):
        action, total, _ = verdict(Cur([('ok', Decimal('0.10')), ('error', Decimal('0.02'))]), 'b')
        self.assertEqual((action, total), ('settle', Decimal('0.12')))

    def test_unknown_or_unmetered_success_is_held(self):
        self.assertEqual(verdict(Cur([('error', None), ('unknown', None)]), 'b')[0], 'hold')
        self.assertEqual(verdict(Cur([('ok', None)]), 'b')[0], 'hold')



class TheJanitorStep(unittest.TestCase):
    def test_a_test_double_never_enters_the_reconciler(self):
        """hasattr() is always true on a MagicMock: the janitor must run the reconciler on a real ledger only."""
        from unittest import mock
        from omni_prod import maintenance
        subs = mock.MagicMock()
        with mock.patch('omni_prod.reservation_reconciler.reconcile', side_effect=AssertionError('entered')) as rec:
            out = maintenance.run_once(pool=mock.MagicMock(), preview_repo=mock.MagicMock(mark_expired=lambda: 0),
                                       jobs=None, subscriptions=subs, stop_preview=None, runtime_host='h')
        rec.assert_not_called()
        self.assertFalse([e for e in out['errors'] if e.startswith('reservations')], out['errors'])
        self.assertNotIn('reservations', out)


if __name__ == '__main__':
    unittest.main()
