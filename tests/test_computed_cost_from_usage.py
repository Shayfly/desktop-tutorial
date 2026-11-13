"""Michael 2026-11-13 (#324 cost): Replicate reports no per-prediction cost, so actual_cost_usd stays NULL. For a model
billed per output only, the usage row carries a cost COMPUTED from measured usage (outputs x the versioned price),
labelled computed_from_usage, with its price version -- never written as actual."""
import unittest
from decimal import Decimal
from pathlib import Path

from omni_prod.providers.image_provider import ImageProviderConfig, computed_from_usage

REPLICATE = {'REPLICATE_API_TOKEN': 'x', 'OMNI_IMAGE_PROVIDER': 'replicate'}


class ComputedFromUsage(unittest.TestCase):
    def test_flux_schnell_is_billed_per_output_and_gets_a_computed_cost(self):
        c = ImageProviderConfig.from_env(REPLICATE)
        self.assertEqual(c.billing_unit, 'output')
        got = computed_from_usage(c, outputs=2, status='succeeded')
        self.assertEqual(got['cost_basis'], 'computed_from_usage')
        self.assertEqual(Decimal(got['computed_cost_usd']), Decimal('0.006'))
        self.assertEqual(got['unit_price_usd'], '0.003')
        self.assertEqual(got['price_source'], 'https://replicate.com/pricing#2026-10-06')
        self.assertNotIn('actual_cost_usd', got)

    def test_only_per_output_models_only_succeeded_outputs(self):
        c = ImageProviderConfig.from_env(REPLICATE)
        self.assertEqual(computed_from_usage(c, outputs=1, status='failed'), {})
        self.assertEqual(computed_from_usage(c, outputs=0, status='succeeded'), {})
        timed = ImageProviderConfig.from_env({**REPLICATE, 'OMNI_IMAGE_PROVIDER_BILLING_UNIT': 'time'})
        self.assertEqual(computed_from_usage(timed, outputs=1, status='succeeded'), {})
        ranged = ImageProviderConfig.from_env({**REPLICATE, 'OMNI_IMAGE_PROVIDER_ESTIMATED_USD_PER_IMAGE': '0.002',
                                               'OMNI_IMAGE_PROVIDER_MAXIMUM_USD_PER_IMAGE': '0.004'})
        self.assertEqual(computed_from_usage(ranged, outputs=1, status='succeeded'), {})   # no single price: none

    def test_the_cost_model_says_computed_is_not_actual(self):
        text = Path('COST_MODEL.md').read_text(encoding='utf-8')
        self.assertIn('Computed is not actual', text)
        self.assertIn('computed_from_usage', text)
        self.assertIn('10%', text)


if __name__ == '__main__':
    unittest.main()
