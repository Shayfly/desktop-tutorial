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


def r2_config_diagnostic(env, store):
    """Read-only fingerprints; callers must enforce authenticated Preview access."""
    from importlib.metadata import version
    from urllib.parse import urlsplit

    def fingerprint(value):
        value = value or ''
        return {'length': len(value), 'sha256_prefix':
            hashlib.sha256(value.encode()).hexdigest()[:12] if value else None}

    creds = store.client._request_signer._credentials.get_frozen_credentials()
    loaded = {'access_key': fingerprint(creds.access_key),
              'secret_key': fingerprint(creds.secret_key)}
    configured = {'access_key': fingerprint(env.get('OMNI_S3_ACCESS_KEY', '').strip()),
                  'secret_key': fingerprint(env.get('OMNI_S3_SECRET_KEY', '').strip())}
    meta = store.client.meta
    endpoint = urlsplit(meta.endpoint_url)
    return {
        'environment': configured, 'client': loaded,
        'environment_matches_client': configured == loaded,
        'configuration': {'endpoint_host': endpoint.hostname,
            'endpoint_has_path': endpoint.path not in ('', '/'),
            'region': meta.region_name, 'signature_version': meta.config.signature_version,
            'addressing_style': (meta.config.s3 or {}).get('addressing_style'),
            'request_checksum_calculation': meta.config.request_checksum_calculation,
            'session_token_present': bool(creds.token)},
        'versions': {'boto3': version('boto3'), 'botocore': version('botocore')},
        'ambient_variable_names': sorted(k for k in env if k.startswith('AWS_')
            or k.upper() in {'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY'}),
        'deployment': {k: env.get(k, '') for k in
            ('VERCEL_ENV', 'VERCEL_URL', 'VERCEL_GIT_COMMIT_SHA', 'VERCEL_GIT_COMMIT_REF')},
    }


class ReplicateImageTest:
    def __init__(self, *, env, journal, store, urlopen=None, fetcher=None):
        # This test always uses the publicly priced default model, irrespective
        # of custom build-provider settings. Never submit an unpriced model.
        self.provider = build_image_provider({'REPLICATE_API_TOKEN': env.get('REPLICATE_API_TOKEN', '')},
            journal=journal, urlopen=urlopen, fetcher=fetcher)
        self.journal = journal
        self.store = store
        self.env = env

    def key(self, account_id):
        return PREFIX + hashlib.sha256(str(account_id).encode()).hexdigest()

    def check_storage(self, account_id):
        # Verify precisely the object permissions needed for the result.
        # HeadBucket can fail on scoped credentials and hides the real error.
        operation = 'write'
        try:
            key = self.key(account_id) + '/storage-probe'
            payload = b'148AI image-test storage probe v1'
            self.store.put_bytes(key, payload)
            operation = 'read'
            if self.store.get_bytes(key) != payload:
                return {'verified': False, 'operation': operation, 'category': 'IntegrityMismatch'}
            return {'verified': True}
        except Exception as exc:
            code = getattr(exc, 'response', {}).get('Error', {}).get('Code')
            allowed = {'AccessDenied', 'InvalidAccessKeyId', 'SignatureDoesNotMatch',
                       'NoSuchBucket', 'NoSuchKey', 'ExpiredToken', '403', '404'}
            category = code if code in allowed else type(exc).__name__
            if category not in allowed | {'EndpointConnectionError', 'ConnectTimeoutError', 'ReadTimeoutError', 'NoCredentialsError'}:
                category = 'StorageError'
            return {'verified': False, 'operation': operation, 'category': category}

    def start(self, account_id, *, confirmed):
        if confirmed is not True:
            raise ValueError('Confirm one image at a maximum provider price of $0.003')
        if self.provider is None:
            raise ValueError('REPLICATE_API_TOKEN is missing')
        # C32 (2026-10-20): a paid call outside the build path must honour the kill switches too.
        from ..model_policy import SPEND_DISABLED, ModelPolicyViolation, external_spend_enabled
        if not external_spend_enabled(self.env):
            raise ModelPolicyViolation(SPEND_DISABLED)
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
