import hashlib
import unittest
from decimal import Decimal

from omni_prod.capabilities import CapabilityRequirement
from omni_prod.credential_binding import (
    CredentialBinding,
    CredentialBindingBroker,
    CredentialMode,
    CredentialStatus,
)
from omni_prod.media_gateway import GeneratedAsset
from omni_prod.provider_contracts import ProviderArtifactPayload
from omni_prod.providers.http_media_provider import HTTPMediaCapabilityProvider
from omni_prod.providers.llm_provider import LLMCapabilityProvider


class FakeResolver:
    def __init__(self): self.seen = []
    def resolve(self, reference): self.seen.append(reference); return 'resolved-secret'


class CredentialBindingTests(unittest.TestCase):
    def test_binding_never_accepts_inline_secret_value(self):
        with self.assertRaisesRegex(ValueError, 'secret reference'):
            CredentialBinding(
                binding_id='b1', provider='meshy', mode=CredentialMode.BYOK,
                status=CredentialStatus.CONFIGURED, tenant_id='tenant-1',
                secret_reference='sk-live-plaintext',
            )

    def test_customer_modes_require_tenant_scope(self):
        with self.assertRaisesRegex(ValueError, 'tenant_id'):
            CredentialBinding(
                binding_id='b1', provider='meshy', mode=CredentialMode.BYOK,
                status=CredentialStatus.CONFIGURED, tenant_id=None,
                secret_reference='vault:tenants/t1/meshy',
            )

    def test_public_view_redacts_secret_reference(self):
        binding = CredentialBinding(
            binding_id='b1', provider='meshy', mode=CredentialMode.BYOK,
            status=CredentialStatus.CONFIGURED, tenant_id='tenant-1',
            secret_reference='vault:tenants/tenant-1/meshy',
        )
        public = binding.to_public_dict()
        self.assertNotIn('secret_reference', public)
        self.assertNotIn('tenants/tenant-1/meshy', repr(public))
        self.assertTrue(public['configured'])

    def test_broker_blocks_cross_tenant_and_resolves_only_reference(self):
        resolver = FakeResolver()
        broker = CredentialBindingBroker(resolvers={'vault': resolver})
        binding = CredentialBinding(
            binding_id='b1', provider='runway', mode=CredentialMode.CUSTOMER_CONNECTED,
            status=CredentialStatus.CONFIGURED, tenant_id='tenant-1',
            secret_reference='vault:connections/c-1',
        )
        with self.assertRaisesRegex(PermissionError, 'tenant'):
            broker.resolve(binding, tenant_id='tenant-2')
        self.assertEqual(broker.resolve(binding, tenant_id='tenant-1'), 'resolved-secret')
        self.assertEqual(resolver.seen, ['vault:connections/c-1'])

    def test_not_configured_binding_fails_closed(self):
        broker = CredentialBindingBroker(resolvers={'env': FakeResolver()})
        binding = CredentialBinding(
            binding_id='platform-meshy', provider='meshy', mode=CredentialMode.PLATFORM_MANAGED,
            status=CredentialStatus.NOT_CONFIGURED, tenant_id=None,
            secret_reference='env:MESHY_API_KEY',
        )
        with self.assertRaisesRegex(RuntimeError, 'not configured'):
            broker.resolve(binding, tenant_id='tenant-x')


class FakeMediaGateway:
    class Endpoint:
        name = 'media-test'
    endpoint = Endpoint()
    def __init__(self): self.calls = []
    def generate(self, request, *, idempotency_key=None):
        self.calls.append((request, idempotency_key))
        return GeneratedAsset(
            asset_id=request.id,
            mime_type='image/png',
            data=b'\x89PNG\r\n\x1a\nasset',
            provider='media-test',
            metadata={'usage_units': 1},
        )


def media_quote(req):
    from omni_prod.provider_contracts import ProviderQuote
    return ProviderQuote('media-test', req.key, Decimal('0.10'), Decimal('0.20'), 'v1', 'image', Decimal('1'))


class ProviderAdapterTests(unittest.TestCase):
    def test_media_adapter_passes_idempotency_and_returns_raw_payload_for_storage_layer(self):
        gateway = FakeMediaGateway()
        provider = HTTPMediaCapabilityProvider(
            gateway=gateway,
            capability_keys=('media.image.generate',),
            output_formats=('image/png',),
            quote_factory=media_quote,
            durable_idempotency=True,
        )
        req = CapabilityRequirement('r1', 'media.image.generate', 'hero', True, constraints={'prompt': 'hero'})
        handle = provider.submit(req, idempotency_key='idem-77')
        self.assertEqual(gateway.calls[0][1], 'idem-77')
        self.assertEqual(provider.poll(handle).status, 'SUCCEEDED')
        result = provider.collect(handle)
        self.assertEqual(len(result.payloads), 1)
        self.assertIsInstance(result.payloads[0], ProviderArtifactPayload)
        self.assertEqual(result.payloads[0].data, b'\x89PNG\r\n\x1a\nasset')
        self.assertIsNone(result.actual_cost_usd)

    def test_media_adapter_rejects_wrong_capability_without_provider_call(self):
        gateway = FakeMediaGateway()
        provider = HTTPMediaCapabilityProvider(
            gateway=gateway,
            capability_keys=('media.image.generate',), output_formats=('image/png',),
            quote_factory=media_quote, durable_idempotency=True,
        )
        req = CapabilityRequirement('r1', 'media.video.generate', 'video', True)
        with self.assertRaisesRegex(LookupError, 'capability'):
            provider.submit(req, idempotency_key='x')
        self.assertEqual(gateway.calls, [])

    def test_paid_media_adapter_must_explicitly_support_durable_idempotency(self):
        with self.assertRaisesRegex(ValueError, 'durable idempotency'):
            HTTPMediaCapabilityProvider(
                gateway=FakeMediaGateway(), capability_keys=('media.image.generate',),
                output_formats=('image/png',), quote_factory=media_quote,
                durable_idempotency=False, paid_external=True,
            )


class FakeLLM:
    def complete(self, **kwargs): return 'hello world'


class LLMAdapterTests(unittest.TestCase):
    def test_llm_adapter_exposes_result_as_payload_without_actual_cost_guess(self):
        provider = LLMCapabilityProvider(
            name='llm-local', gateway=FakeLLM(), capability_keys=('software.code.generate',),
            quote_factory=lambda req: __import__('omni_prod.provider_contracts', fromlist=['ProviderQuote']).ProviderQuote(
                'llm-local', req.key, Decimal('0'), Decimal('0'), 'local-v1', 'request', Decimal('1')
            ),
        )
        req = CapabilityRequirement('r1', 'software.code.generate', 'code', True, constraints={'prompt': 'build it'})
        handle = provider.submit(req, idempotency_key='idem')
        result = provider.collect(handle)
        self.assertEqual(result.payloads[0].mime_type, 'text/plain')
        self.assertEqual(result.payloads[0].data, b'hello world')
        self.assertIsNone(result.actual_cost_usd)


if __name__ == '__main__':
    unittest.main()
