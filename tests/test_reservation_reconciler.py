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


if __name__ == '__main__':
    unittest.main()
