"""Read-only account discovery for the three direct model APIs.

Run on the worker with its existing environment: python -m omni_prod.model_discovery.
Only GET /models is used. Listing a model proves visibility, never generation,
billing availability, image support in our adapter, or production readiness.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib import error, parse, request
from typing import Mapping

MAX_PAGES = 20
MAX_RESPONSE_BYTES = 4 * 1024 * 1024

DIRECT_IMAGE_MODELS = (
    'gemini-nano-banana-2.1', 'gemini-3.1-flash-image',
    'gemini-3.1-flash-lite-image', 'gemini-3-pro-image',
)
DIRECT_MEDIA_MODELS = DIRECT_IMAGE_MODELS + (
    'gemini-omni-1.2-flash', 'gemini-omni-1.1-flash',
    'lyria-3.5', 'lyria-3-clip-preview', 'lyria-3-pro-preview', 'lyria-realtime-exp',
    'gemini-3.8-flash-lite-tts', 'gemini-3.5-transcribe',
    'gemini-3.5-transcribe-live', 'gemini-3.5-live-translate-preview',
)
PROVIDERS = {
    'anthropic': ('ANTHROPIC_API_KEY', 'https://api.anthropic.com/v1/models?limit=100'),
    'openai': ('OPENAI_API_KEY', 'https://api.openai.com/v1/models'),
    'gemini': ('GEMINI_API_KEY', 'https://generativelanguage.googleapis.com/v1beta/models?pageSize=100'),
}


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Credentials are scoped to the fixed provider origin, including on error.
        raise ValueError('model discovery refuses redirects')


def _get(url, headers, transport):
    req = request.Request(url, headers=headers, method='GET')
    with transport(req, timeout=15) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError('model list exceeds response limit')
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('model list must be an object')
    return data


def _page(provider, payload):
    key = 'models' if provider == 'gemini' else 'data'
    rows = payload.get(key)
    if not isinstance(rows, list):
        raise ValueError('model list is missing')
    models = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('invalid model entry')
        model = row.get('name' if provider == 'gemini' else 'id')
        if not isinstance(model, str) or not model.strip():
            raise ValueError('model id is missing')
        model = model.removeprefix('models/') if provider == 'gemini' else model
        models.append(model)
    cursor = payload.get('nextPageToken') if provider == 'gemini' else (
        payload.get('last_id') if provider == 'anthropic' and payload.get('has_more') else None)
    if provider == 'anthropic' and payload.get('has_more') and not cursor:
        raise ValueError('pagination cursor is missing')
    if cursor is not None and (not isinstance(cursor, str) or not cursor):
        raise ValueError('invalid pagination cursor')
    return models, cursor


def discover_provider(provider: str, env: Mapping[str, str], *, transport=None) -> dict:
    key_name, base_url = PROVIDERS[provider]
    key = str(env.get(key_name) or '').strip()
    result = {'provider': provider, 'key_present': bool(key), 'models': [],
              'generation_verified': False, 'billing_verified': False}
    if not key:
        return {**result, 'status': 'NOT_CONFIGURED'}
    headers = {'User-Agent': '148AI-model-discovery/1', 'Accept': 'application/json'}
    if provider == 'anthropic':
        headers.update({'x-api-key': key, 'anthropic-version': '2023-06-01'})
    elif provider == 'gemini':
        headers['x-goog-api-key'] = key
    else:
        headers['Authorization'] = 'Bearer ' + key
    transport = transport or request.build_opener(NoRedirect()).open
    models = set()
    seen = set()
    url = base_url
    try:
        for _ in range(MAX_PAGES):
            rows, cursor = _page(provider, _get(url, headers, transport))
            models.update(rows)
            if cursor is None:
                return {**result, 'status': 'ACCOUNT_VISIBLE', 'models': sorted(models)}
            if cursor in seen:
                raise ValueError('pagination repeated')
            seen.add(cursor)
            parameter = 'pageToken' if provider == 'gemini' else 'after_id'
            url = base_url + '&' + parse.urlencode({parameter: cursor})
    except error.HTTPError as exc:
        return {**result, 'status': 'BLOCKED', 'http_status': exc.code}
    except Exception:
        # No provider error text, exception message, raw response, key or cursor
        # is logged. Incomplete pagination never presents itself as a full list.
        return {**result, 'status': 'UNVERIFIED', 'reason': 'model list could not be completed'}
    return {**result, 'status': 'UNVERIFIED', 'reason': 'model list page limit reached'}


def discover(env: Mapping[str, str] | None = None, *, transport=None) -> dict:
    env = os.environ if env is None else env
    return {'schema': 'direct-model-discovery/1',
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'source_commit': env.get('OMNI_SOURCE_COMMIT', 'unknown'),
            'providers': [discover_provider(p, env, transport=transport) for p in PROVIDERS],
            'google_media_targets': list(DIRECT_MEDIA_MODELS),
            'media_adapter_status': 'PARTIAL: direct Google image adapter; generation unverified',
            'note': 'Account visibility is not generation or billing verification.'}


def main() -> int:
    result = discover()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(p['status'] == 'ACCOUNT_VISIBLE' for p in result['providers']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
