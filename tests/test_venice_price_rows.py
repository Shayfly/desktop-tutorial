"""Venice price rows (CEO 2026-10-19): a separate 'venice' provider with Venice's
own model ids (dashes) and prices. Gemini rows keep Google prices, because
148AI calls Google directly (infra/worker-host/model-catalog.json).

Values: docs.venice.ai/overview/pricing, 2026-10-19 (see docs/venice_prices_snapshot.md).
Lookups are keyed by (provider, model); Claude is sold by both Anthropic and Venice.
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

    def test_claude_via_venice_and_anthropic_coexist(self):
        # Same model id, two providers: the lookup is keyed by (provider, model).
        direct = prices.price_at('claude-sonnet-5-5', DAY, provider='anthropic')
        resold = prices.price_at('claude-sonnet-5-5', DAY, provider='venice')
        self.assertEqual((direct.provider, direct.source_url), ('anthropic', prices.ANTHROPIC))
        self.assertEqual((resold.provider, resold.source_url), ('venice', prices.VENICE))
        for m in ('claude-sonnet-5-5', 'claude-haiku-5-5', 'claude-opus-5-5'):
            self.assertIsNotNone(prices.price_at(m, DAY, provider='anthropic'), m)
            self.assertIsNotNone(prices.price_at(m, DAY, provider='venice'), m)

    def test_unscoped_lookup_of_a_shared_id_is_refused(self):
        # Collision: never silently pick one provider's price.
        with self.assertRaises(prices.AmbiguousPrice):
            prices.price_at('claude-sonnet-5-5', DAY)
        with self.assertRaises(prices.AmbiguousPrice):
            prices.require_price('claude-sonnet-5-5', DAY)

    def test_unscoped_lookup_of_a_unique_id_still_works(self):
        self.assertEqual(prices.price_at('gemini-3.8-flash', DAY).provider, 'gemini')
        self.assertEqual(prices.price_at('gemini-3-8-flash', DAY).provider, 'venice')

    def test_overlap_detection_is_per_provider(self):
        row = prices.price_at('claude-sonnet-5-5', DAY, provider='anthropic')
        twin = prices.PriceRow(**{**row.__dict__})
        self.assertTrue(any('anthropic/claude-sonnet-5-5' in p for p in prices.validate(prices.SCHEDULE + (twin,))))
        self.assertEqual(prices.validate(), [])

    def test_history_is_provider_scoped(self):
        self.assertEqual({r.provider for r in prices.history('claude-sonnet-5-5', provider='venice')}, {'venice'})


class ConnectedProvidersArePricedTests(unittest.TestCase):
    """CEO 2026-10-19: no connected provider without a price row."""

    def test_every_connection_tested_model_has_a_price_row(self):
        from omni_prod.intelligence.inventory import INVENTORY
        missing = [f'{e.provider_key}/{e.provider_model_id}' for e in INVENTORY
                   if getattr(e.connection_state, 'value', e.connection_state) == 'CONNECTION_TESTED'
                   and prices.price_at(e.provider_model_id, DAY, provider=e.provider_key) is None]
        self.assertEqual(missing, [])

    def test_replicate_flux_schnell_priced_per_image(self):
        row = prices.price_at('black-forest-labs/flux-schnell', DAY, provider='replicate')
        self.assertEqual(row.per_image, D('0.003'))
        self.assertEqual(row.source_url, prices.REPLICATE_PRICING)
        self.assertEqual(row.verified_at, '2026-10-19')

if __name__ == '__main__':
    unittest.main()
