"""The conversation rehearsal runs on the PRODUCTION intake path (the owner's human test, 2026-11-17): the first version
ran on the routed gateway and passed on Sonnet, while every real conversation ran through Venice on Haiku. The gateway
is the one the intake worker builds for a reservation, from the newest settled production quote (read from the
database); every call's real model is recorded. Fakes stand in for the database and the provider only."""
import os
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from omni_prod import conversation_rehearsal as R

QUOTE = {'provider': 'venice', 'allowed_models': ['venice:claude-haiku-5-5', 'venice:qwen3-235b-a22b-instruct-2507'],
         'venice_allowed_models': ['claude-haiku-5-5', 'qwen3-235b-a22b-instruct-2507'],
         'venice_ceiling_usd_per_m': ['0.18', '0.9'], 'max_tokens': 2400}


class _Pool:
    def __init__(self, row):
        self.row, self.sql = row, []

    def connection(self):
        pool = self

        class C:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, sql, *a):
                pool.sql.append(sql)
                return SimpleNamespace(fetchone=lambda: pool.row)
        return C()


class _Venice:
    def __init__(self, amount):
        self.amount = amount
        self.recorder = SimpleNamespace(records=[])

    def complete_json(self, *, call_id, **kw):
        self.recorder.records.append(SimpleNamespace(model='claude-haiku-5-5', kind='provider_call', call_id=call_id))
        return {'reply': 'שלום'}


class TheProductionPath(unittest.TestCase):
    def test_the_newest_settled_production_quote_is_read(self):
        pool = _Pool(('ires_1', Decimal('0.0036'), QUOTE))
        got = R.production_quote(pool)
        self.assertEqual((got['reservation_id'], got['quote']['provider']), ('ires_1', 'venice'))
        self.assertIn("state = 'SETTLED'", pool.sql[0])
        self.assertIn('ORDER BY settled_at DESC', pool.sql[0])

    def test_no_production_reservation_is_loud(self):
        with self.assertRaises(SystemExit):
            R.production_quote(_Pool(None))

    def test_the_worker_gateway_is_built_from_the_quote_and_the_real_model_is_recorded(self):
        built = []

        def build(amount, models, quote):
            built.append((amount, models, quote))
            return _Venice(amount)
        g = R.ProductionPathGateway(QUOTE)
        with mock.patch('omni_prod.intake.reservation_worker.build_gateway', build):
            g.complete_json(system='s' * 1000, user='u' * 936, max_tokens=2400, call_id='c1')
        amount, models, quote = built[0]
        self.assertEqual(g.recorder.records[0].call_id, 'c1')             # the worker's gateway got THIS call's id
        self.assertIs(quote, QUOTE)
        self.assertEqual(models, tuple(QUOTE['allowed_models']))
        # (1936 bytes + 64) = 2000 input tokens at $0.18/M + 2400 output at $0.90/M -- the same bound as budget.quote
        self.assertEqual(amount, Decimal('0.00252000'))
        self.assertEqual(g.models_used, ['claude-haiku-5-5'])

    def test_the_default_path_is_production_and_an_unknown_one_is_refused(self):
        with mock.patch.dict(os.environ, {R.PATH_ENV: 'staging'}):
            with self.assertRaises(SystemExit):
                R.main(['doors'])
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(R.PATH_ENV, None)
            os.environ.pop('OMNI_DATABASE_URL', None)
            with self.assertRaises(KeyError):          # production needs the database: never a silent other path
                R.main(['doors'])


if __name__ == '__main__':
    unittest.main()
