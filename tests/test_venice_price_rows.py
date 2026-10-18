"""Venice price rows (CEO 2026-10-19): a separate 'venice' provider with Venice's
own model ids (dashes) and prices. Gemini rows keep Google prices, because
148AI calls Google directly (infra/worker-host/model-catalog.json).

Values: docs.venice.ai/overview/pricing, 2026-10-19 (see docs/venice_prices_snapshot.md).
"""
import unittest
from datetime import date
from decimal import Decimal as D

from omni_prod.intelligence import prices

VENICE_GEMINI = {
    'gemini-3-flash-preview': ('0.70', '0.07', '3.75'),
    'gemini-3-1-pro-preview': ('2.50', '0.50', '15.00'),
    'gemini-3-5-flash': ('1.55', '0.15', '9.45'),
    'gemini-3-5-flash-lite': ('0.38', '0.04', '3.13'),
    'gemini-3-6-flash': ('0.94', '0.09', '4.69'),
    'gemini-3-7-flash': ('0.94', '0.09', '4.69'),
    'gemini-3-8-flash': ('0.94', '0.09', '4.69'),
    'gemini-4-argon': ('2.50', '0.13', '12.50'),
}
DAY = date(2026, 10, 19)


class VenicePriceRowTests(unittest.TestCase):
    def test_schedule_is_valid(self):
        self.assertEqual(prices.validate(), [])

    def test_venice_rows_use_venice_ids_and_prices(self):
        for model, (inp, cached, out) in VENICE_GEMINI.items():
            row = prices.price_at(model, DAY)
            self.assertIsNotNone(row, model)
            self.assertEqual(row.provider, 'venice', model)
            self.assertNotIn('.', model.replace('gemini-', ''), 'Venice ids use dashes')
            self.assertEqual((row.input_per_million, row.cached_input_per_million, row.output_per_million),
                             (D(inp), D(cached), D(out)), model)
            self.assertEqual(row.source_url, prices.VENICE)
            self.assertEqual(row.verified_at, '2026-10-19')

    def test_google_gemini_rows_unchanged(self):
        row = prices.price_at('gemini-3.8-flash', DAY)
        self.assertEqual(row.provider, 'gemini')
        self.assertEqual((row.input_per_million, row.cached_input_per_million, row.output_per_million),
                         (D('0.75'), D('0.075'), D('3.75')))
        self.assertEqual(row.source_url, prices.GOOGLE)

    def test_no_venice_row_shadows_a_direct_provider(self):
        # price_at keys on model id only: a Venice row with the same id as a
        # direct provider row would make that model unpriceable (overlap).
        direct = {r.model for r in prices.SCHEDULE if r.provider != 'venice'}
        venice = {r.model for r in prices.SCHEDULE if r.provider == 'venice'}
        self.assertEqual(direct & venice, set())
        self.assertEqual(prices.price_at('claude-sonnet-5-5', DAY).provider, 'anthropic')


if __name__ == '__main__':
    unittest.main()
