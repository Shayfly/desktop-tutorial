import unittest
from decimal import Decimal

from omni_prod.capabilities import CapabilityRequirement
from omni_prod.provider_contracts import ProviderQuote
from omni_prod.provider_pricing import (
    PriceStatus, ProviderPriceCatalog, ProviderPriceEntry,
    contribution_evidence, validate_live_quote_within_reservation,
)


class ProviderPriceCatalogTests(unittest.TestCase):
    def test_catalog_is_versioned_and_quotes_conservative_maximum(self):
        catalog = ProviderPriceCatalog(
            version='prices-2026-10-04',
            entries=(ProviderPriceEntry(
                provider='p', capability_key='media.image.generate', operation='generate',
                unit_name='image', estimated_unit_cost_usd=Decimal('0.08'),
                maximum_unit_cost_usd=Decimal('0.12'), status=PriceStatus.PUBLIC_LIST_PRICE,
                effective_from='2026-10-04',
            ),),
        )
        req = CapabilityRequirement('r1', 'media.image.generate', 'hero', True, quantity=3)
        quote = catalog.quote(provider='p', requirement=req)
        self.assertEqual(quote.pricing_version, 'prices-2026-10-04')
        self.assertEqual(quote.estimated_cost_usd, Decimal('0.24'))
        self.assertEqual(quote.maximum_cost_usd, Decimal('0.36'))
        self.assertEqual(quote.units, Decimal('3'))

    def test_unknown_price_is_never_treated_as_zero(self):
        catalog = ProviderPriceCatalog(
            version='v1',
            entries=(ProviderPriceEntry(
                provider='p', capability_key='media.video.generate', operation='generate',
                unit_name='second', estimated_unit_cost_usd=None, maximum_unit_cost_usd=None,
                status=PriceStatus.UNKNOWN_NOT_APPROVED, effective_from='2026-10-04',
            ),),
        )
        req = CapabilityRequirement('r1', 'media.video.generate', 'clip', True)
        with self.assertRaisesRegex(RuntimeError, 'UNKNOWN_NOT_APPROVED'):
            catalog.quote(provider='p', requirement=req)

    def test_customer_pays_direct_can_quote_zero_platform_provider_cost(self):
        catalog = ProviderPriceCatalog(
            version='v1',
            entries=(ProviderPriceEntry(
                provider='customer-api', capability_key='integration.external', operation='request',
                unit_name='request', estimated_unit_cost_usd=Decimal('0'), maximum_unit_cost_usd=Decimal('0'),
                status=PriceStatus.CUSTOMER_PAYS_DIRECTLY, effective_from='2026-10-04',
            ),),
        )
        req = CapabilityRequirement('r1', 'integration.external', 'customer connection', True)
        self.assertEqual(catalog.quote(provider='customer-api', requirement=req).maximum_cost_usd, Decimal('0'))

    def test_duplicate_provider_capability_operation_is_rejected(self):
        entry = ProviderPriceEntry(
            provider='p', capability_key='c', operation='generate', unit_name='unit',
            estimated_unit_cost_usd=Decimal('1'), maximum_unit_cost_usd=Decimal('1'),
            status=PriceStatus.PUBLIC_LIST_PRICE, effective_from='2026-10-04',
        )
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            ProviderPriceCatalog(version='v1', entries=(entry, entry))


class EconomicsGuardTests(unittest.TestCase):
    def test_live_quote_cannot_expand_beyond_pre_authorized_maximum(self):
        local = ProviderQuote('p', 'c', Decimal('1'), Decimal('2'), 'local-v1', 'unit', Decimal('1'))
        live = ProviderQuote('p', 'c', Decimal('1.5'), Decimal('2.01'), 'provider-v2', 'unit', Decimal('1'))
        with self.assertRaisesRegex(PermissionError, 'reservation'):
            validate_live_quote_within_reservation(local_quote=local, live_quote=live, reserved_maximum_usd=Decimal('2'))

    def test_live_quote_within_reservation_is_accepted(self):
        local = ProviderQuote('p', 'c', Decimal('1'), Decimal('2'), 'local-v1', 'unit', Decimal('1'))
        live = ProviderQuote('p', 'c', Decimal('1.2'), Decimal('1.8'), 'provider-v2', 'unit', Decimal('1'))
        self.assertIs(validate_live_quote_within_reservation(
            local_quote=local, live_quote=live, reserved_maximum_usd=Decimal('2')
        ), live)

    def test_contribution_marks_unknown_actual_as_conservative_not_actual(self):
        conservative = contribution_evidence(
            revenue_usd=Decimal('10'), actual_provider_cost_usd=None,
            conservative_provider_cost_usd=Decimal('2'), infra_cost_usd=Decimal('1'),
            payment_fee_usd=Decimal('0.5'), support_allocation_usd=Decimal('0.5'),
        )
        self.assertEqual(conservative['provider_cost_truth'], 'CONSERVATIVE')
        self.assertEqual(conservative['contribution_usd'], Decimal('6'))
        actual = contribution_evidence(
            revenue_usd=Decimal('10'), actual_provider_cost_usd=Decimal('1.5'),
            conservative_provider_cost_usd=Decimal('2'), infra_cost_usd=Decimal('1'),
            payment_fee_usd=Decimal('0.5'), support_allocation_usd=Decimal('0.5'),
        )
        self.assertEqual(actual['provider_cost_truth'], 'ACTUAL')
        self.assertEqual(actual['contribution_usd'], Decimal('6.5'))


if __name__ == '__main__':
    unittest.main()
