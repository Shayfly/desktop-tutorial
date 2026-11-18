"""Direct Google Nano Banana generation through the existing capability executor.

Selection is explicit via OMNI_GOOGLE_IMAGE_MODEL. The existing submission
journal and private artifact store retain each image across process restarts.
A request whose outcome is uncertain is never automatically paid for again.
"""
from __future__ import annotations

import base64
import hashlib
import json
from decimal import Decimal, InvalidOperation
from urllib import request, error

from ..provider_contracts import (ProviderArtifactPayload, ProviderCapability,
                                  ProviderExecutionResult, ProviderQuote,
                                  ProviderTaskHandle, ProviderTaskState)
from ..model_discovery import DIRECT_MEDIA_MODELS
from ..model_policy import ModelPolicyViolation, SPEND_DISABLED, external_spend_enabled

MODELS = frozenset(DIRECT_MEDIA_MODELS[:4])
MAX_BODY_BYTES = 32 * 1024 * 1024


def readiness(env):
    model = str(env.get('OMNI_GOOGLE_IMAGE_MODEL', '')).strip()
    missing = [name for name in ('GEMINI_API_KEY', 'OMNI_GOOGLE_IMAGE_MAXIMUM_USD',
                                'OMNI_GOOGLE_IMAGE_PRICE_SOURCE') if not str(env.get(name, '')).strip()]
    if not model or missing:
        return {'status': 'NOT_CONFIGURED', 'reason': 'Direct Google image configuration is incomplete'}
    if model not in MODELS:
        return {'status': 'BLOCKED', 'reason': 'Unsupported direct Google image model'}
    try:
        maximum = Decimal(str(env['OMNI_GOOGLE_IMAGE_MAXIMUM_USD']))
        valid_price = maximum.is_finite() and maximum > 0
    except InvalidOperation:
        valid_price = False
    source = str(env.get('OMNI_GOOGLE_IMAGE_PRICE_SOURCE', ''))
    if not valid_price or not source.startswith('https://'):
        return {'status': 'BLOCKED', 'reason': 'A positive, source-backed per-image maximum is required'}
    return {'status': 'PARTIAL', 'reason': 'Configured; direct generation is not live verified'}


class GoogleImageProvider:
    paid_external = True
    durable_idempotency = True
    durable_result_retrieval = True

    def __init__(self, env, *, journal, artifact_store=None, urlopen=None):
        if readiness(env)['status'] != 'PARTIAL':
            raise ValueError('Direct Google image provider is not configured')
        self.env = dict(env)
        self.model = str(env['OMNI_GOOGLE_IMAGE_MODEL']).strip()
        self.name = 'gemini-image-' + self.model
        self.journal = journal
        self.store = artifact_store
        from ..model_discovery import NoRedirect
        self.urlopen = urlopen or request.build_opener(NoRedirect()).open
        self.maximum = Decimal(str(env['OMNI_GOOGLE_IMAGE_MAXIMUM_USD']))
        self.price_source = str(env['OMNI_GOOGLE_IMAGE_PRICE_SOURCE'])

    def capabilities(self):
        return (ProviderCapability('media.image.generate', ('image/png', 'image/jpeg', 'image/webp'),
                                   str(self.env.get('OMNI_GOOGLE_IMAGE_COMMERCIAL_USE', '')).lower() == 'true'),)

    def health(self):
        return 'DEGRADED'  # configured by the operator; no live health probe claimed

    def quote(self, requirement):
        self._validate(requirement)
        count = Decimal(requirement.quantity)
        return ProviderQuote(self.name, requirement.key, self.maximum * count, self.maximum * count,
                             self.model + ':1K:' + str(self.maximum) + ':' + self.price_source, 'image', count)

    def _validate(self, requirement):
        if requirement.key != 'media.image.generate':
            raise LookupError('Unsupported Google image capability')
        if int(requirement.quantity) != requirement.quantity or not 1 <= requirement.quantity <= 3:
            raise ValueError('Direct Google image generation supports 1 to 3 images per requirement')
        from .image_provider import PredictionImageProvider
        prompt = PredictionImageProvider._prompt(self, requirement)
        if not prompt.strip() or len(prompt.encode('utf-8')) > 16000:
            raise ValueError('Image prompt must be nonempty and at most 16000 UTF-8 bytes')
        return prompt

    def _get(self, key):
        try:
            return json.loads(self.store.get_bytes(key))
        except (KeyError, FileNotFoundError):
            return None
        except Exception as exc:
            detail = getattr(exc, 'response', {})
            if isinstance(detail, dict) and detail.get('Error', {}).get('Code') in {'NoSuchKey', '404', 'NotFound'}:
                return None
            raise

    def _generate(self, prompt, ratio):
        if not external_spend_enabled(self.env):
            raise ModelPolicyViolation(SPEND_DISABLED)
        config = {'responseModalities': ['IMAGE'], 'candidateCount': 1,
                  'maxOutputTokens': 8192, 'imageConfig': {'imageSize': '1K', 'aspectRatio': ratio}}
        body = {'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'generationConfig': config}
        req = request.Request('https://generativelanguage.googleapis.com/v1beta/models/' + self.model + ':generateContent',
                              data=json.dumps(body).encode(), method='POST',
                              headers={'Content-Type': 'application/json', 'x-goog-api-key': self.env['GEMINI_API_KEY'],
                                       'User-Agent': '148AI-google-image/1'})
        try:
            with self.urlopen(req, timeout=180) as response:
                raw = response.read(MAX_BODY_BYTES + 1)
        except error.HTTPError as exc:
            # Even a rejected request is not retried here. The durable child
            # INTENT is retained for reconciliation and the error text is private.
            raise RuntimeError('Google image request failed (HTTP ' + str(exc.code) + ')') from None
        if len(raw) > MAX_BODY_BYTES:
            raise RuntimeError('Google image response exceeds byte limit')
        payload = json.loads(raw)
        candidates = payload.get('candidates') or []
        images = [part['inlineData'] for candidate in candidates
                  for part in (candidate.get('content') or {}).get('parts', [])
                  if isinstance(part, dict) and 'inlineData' in part]
        if len(images) != 1:
            raise RuntimeError('Google did not return exactly one image')
        image = images[0]
        data = base64.b64decode(image['data'], validate=True)
        from .image_provider import sniff_image
        mime, _, _ = sniff_image(data)
        if mime != image.get('mimeType'):
            raise RuntimeError('Google image MIME does not match its bytes')
        return {'data': image['data'], 'mime': mime, 'sha256': hashlib.sha256(data).hexdigest(),
                'usage': payload.get('usageMetadata') or {}}

    def submit(self, requirement, *, idempotency_key):
        prompt = self._validate(requirement)
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError('A nonempty image idempotency key is required')
        if self.store is None or not getattr(self.journal, 'durable', False):
            raise RuntimeError('Direct Google images require durable storage and submission journal')
        ratio = str(requirement.constraints.get('aspect_ratio') or '1:1')
        if ratio not in {'1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9'}:
            raise ValueError('Unsupported image aspect ratio')
        digest = hashlib.sha256(json.dumps([self.model, requirement.id, prompt, ratio, int(requirement.quantity)]).encode()).hexdigest()
        task = hashlib.sha256((self.name + '\0' + idempotency_key).encode()).hexdigest()
        manifest_key = 'provider-results/google-image/' + task + '/manifest.json'
        existing = self._get(manifest_key)
        if existing:
            if existing['request_hash'] != digest:
                raise ValueError('Image idempotency key reused for a different request')
            return ProviderTaskHandle(self.name, task, requirement.id, idempotency_key)
        if not external_spend_enabled(self.env):
            raise ModelPolicyViolation(SPEND_DISABLED)
        for index in range(int(requirement.quantity)):
            child_key = idempotency_key + ':' + str(index)
            result_key = 'provider-results/google-image/' + task + '/' + str(index) + '.json'
            image = self._get(result_key)
            if image:
                if image['request_hash'] != digest:
                    raise ValueError('Image idempotency key reused for a different request')
                continue
            record = self.journal.begin(child_key, provider=self.name)
            if record.preexisting:
                from .image_provider import AmbiguousSubmission
                raise AmbiguousSubmission('Previous Google image request needs reconciliation')
            image = {**self._generate(prompt, ratio), 'request_hash': digest}
            self.store.put_bytes(result_key, json.dumps(image).encode())
            self.journal.record_task(child_key, task)
        self.store.put_bytes(manifest_key, json.dumps({'request_hash': digest, 'quantity': int(requirement.quantity)}).encode())
        return ProviderTaskHandle(self.name, task, requirement.id, idempotency_key)

    def _check_handle(self, handle):
        expected = hashlib.sha256((self.name + '\0' + handle.idempotency_key).encode()).hexdigest()
        if handle.provider != self.name or handle.provider_task_id != expected:
            raise ValueError('Google image handle does not match its provider and idempotency key')

    def poll(self, handle):
        self._check_handle(handle)
        if self._get('provider-results/google-image/' + handle.provider_task_id + '/manifest.json') is None:
            raise RuntimeError('Google image result is incomplete; reconciliation required')
        return ProviderTaskState('SUCCEEDED', 1.0)

    def collect(self, handle):
        self._check_handle(handle)
        prefix = 'provider-results/google-image/' + handle.provider_task_id + '/'
        manifest = self._get(prefix + 'manifest.json')
        if not manifest:
            raise RuntimeError('Google image result is unavailable')
        payloads = []
        usage = []
        for index in range(manifest['quantity']):
            image = self._get(prefix + str(index) + '.json')
            if not image or image['request_hash'] != manifest['request_hash']:
                raise RuntimeError('Stored Google image result is incomplete')
            data = base64.b64decode(image['data'], validate=True)
            if hashlib.sha256(data).hexdigest() != image['sha256']:
                raise RuntimeError('Stored Google image checksum mismatch')
            from .image_provider import sniff_image
            mime, _, _ = sniff_image(data)
            if mime != image['mime']:
                raise RuntimeError('Stored Google image MIME mismatch')
            ext = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp'}[mime]
            payloads.append(ProviderArtifactPayload(mime, data, filename='image-' + str(index) + '.' + ext,
                                                   provenance={'provider': 'google', 'model': self.model,
                                                               'source': 'direct Google API'}))
            usage.append(image['usage'])
        return ProviderExecutionResult((), None, {'responses': usage},
                                       {'model': self.model, 'cost_basis': 'provider_cost_not_reported'}, tuple(payloads))

    def cancel(self, handle):
        # generateContent is synchronous. Completed results remain recoverable;
        # no cancellation endpoint or refund is invented.
        return None
