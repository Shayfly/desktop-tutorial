"""One fixed, account-scoped Preview smoke test, independent of site builds.

The journal permits at most one successful submission per account. Ambiguous
network outcomes fail closed. Output is verified by the existing adapter and
stored privately in the existing artifact store, never ephemeral function disk.
"""
import hashlib
from .image_provider import build_image_provider, sniff_image
from ..capabilities import CapabilityRequirement
from ..provider_contracts import ProviderTaskHandle

PROMPT = 'Original landscape photograph of mountains and a calm lake at sunrise, no people, no text.'
PREFIX = 'replicate-smoke-v1-'


class ReplicateImageTest:
    def __init__(self, *, env, journal, store, urlopen=None, fetcher=None):
        # This test always uses the publicly priced default model, irrespective
        # of custom build-provider settings. Never submit an unpriced model.
        self.provider = build_image_provider({'REPLICATE_API_TOKEN': env.get('REPLICATE_API_TOKEN', '')},
            journal=journal, urlopen=urlopen, fetcher=fetcher)
        self.journal = journal
        self.store = store

    def key(self, account_id):
        return PREFIX + hashlib.sha256(str(account_id).encode()).hexdigest()

    def start(self, account_id, *, confirmed):
        if confirmed is not True:
            raise ValueError('Confirm one image at a maximum provider price of $0.003')
        if self.provider is None:
            raise ValueError('REPLICATE_API_TOKEN is missing')
        requirement = CapabilityRequirement(id='replicate-test', key='media.image.generate',
            purpose='single image connection test', required=True, quantity=1, constraints={'prompt': PROMPT})
        handle = self.provider.submit(requirement, idempotency_key=self.key(account_id))
        return {'status': 'SUBMITTED', 'task_id': handle.provider_task_id, 'maximum_usd': '0.003',
                'generation_verified': False}

    def status(self, account_id):
        record = self.journal.find(self.key(account_id))
        if record is None:
            return {'status': 'NOT_STARTED', 'generation_verified': False}
        if not record.provider_task_id:
            return {'status': 'UNKNOWN_SUBMISSION', 'generation_verified': False,
                    'reason': 'Submission outcome unknown; automatic paid retry is disabled'}
        if self.store is not None:
            try:
                data, _ = self.image(account_id)
                return {'status': 'SUCCEEDED', 'generation_verified': True,
                        'maximum_usd': '0.003', 'actual_cost_usd': None,
                        'sha256': hashlib.sha256(data).hexdigest(),
                        'image_url': '/api/v28/providers/replicate/image-test/image'}
            except KeyError:
                pass  # In-memory test store: no saved result yet.
            except Exception as exc:
                # S3 missing-object is expected before completion. All other
                # storage failures stay explicit; they cannot trigger a POST.
                code = getattr(exc, 'response', {}).get('Error', {}).get('Code')
                if code not in {'NoSuchKey', '404', 'NotFound'}:
                    raise
        if self.provider is None:
            raise ValueError('REPLICATE_API_TOKEN is missing')
        handle = ProviderTaskHandle(record.provider, record.provider_task_id, 'replicate-test', record.idempotency_key)
        state = self.provider.poll(handle)
        result = {'status': state.status, 'generation_verified': False, 'maximum_usd': '0.003'}
        if state.status == 'SUCCEEDED':
            output = self.provider.collect(handle)
            if len(output.payloads) != 1:
                raise ValueError('Expected exactly one image')
            payload = output.payloads[0]
            self.store.put_bytes(self.key(account_id) + '/image', payload.data)
            result.update(generation_verified=True, image_url='/api/v28/providers/replicate/image-test/image',
                          sha256=hashlib.sha256(payload.data).hexdigest(),
                          actual_cost_usd=str(output.actual_cost_usd) if output.actual_cost_usd is not None else None)
        return result

    def image(self, account_id):
        data = self.store.get_bytes(self.key(account_id) + '/image')
        mime, _, _ = sniff_image(data)
        return data, mime
