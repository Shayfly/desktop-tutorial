"""Enrollment crosses the real catalog and governance boundary; no provider call."""
import io
import json
from datetime import date
from email.message import Message
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import HTTPSHandler
from urllib.response import addinfourl

import pytest

from omni_prod.model_catalog import ModelCatalogError, parse_model_catalog
from omni_prod.intelligence.prices import price_at, validate
from omni_prod.model_discovery import MAX_PAGES, discover_provider

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'infra/worker-host/model-catalog.json').read_text())
ADDITIONS = [row for row in CATALOG if row.get('_activation_status') == 'PENDING_LIVE_VERIFICATION']
KEYS = {key: 'secret-test-value' for key in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY')}


def response(payload):
    return io.BytesIO(json.dumps(payload).encode())


def test_new_models_are_disabled_even_with_keys_and_governed_prices():
    assert len(ADDITIONS) == 10
    parsed = parse_model_catalog(json.dumps(CATALOG), KEYS, when=date(2026, 11, 18))
    assert sum(m.endpoint is not None for m in parsed) == 6
    assert all(not row['enabled'] for row in ADDITIONS)
    assert validate() == []
    for row in ADDITIONS:
        assert price_at(row['model'], date(2026, 11, 18)) is not None
        assert 'UNMEASURED' in row['_quality_basis']


@pytest.mark.parametrize('row', ADDITIONS, ids=lambda row: row['model'])
def test_explicit_enrollment_uses_existing_key_dialect_and_price_governance(row):
    activated = {**row, 'enabled': True, 'quality': 85}
    model = parse_model_catalog(json.dumps([activated]), KEYS, when=date(2026, 11, 18))[0]
    assert model.endpoint is not None
    assert model.endpoint.api_style == row['api']
    assert model.price_source.startswith('schedule ')
    assert 'secret-test-value' not in json.dumps(model.to_public_dict())
    assert parse_model_catalog(json.dumps([activated]), {}, when=date(2026, 11, 18))[0].endpoint is None
    del activated['enabled']
    assert parse_model_catalog(json.dumps([activated]), KEYS, when=date(2026, 11, 18))[0].endpoint is None


@pytest.mark.parametrize('row', ADDITIONS, ids=lambda row: row['model'])
def test_enabled_enrollment_rejects_unmeasured_quality(row):
    with pytest.raises(ModelCatalogError, match=r'explicit quality score 1\.\.100'):
        parse_model_catalog(json.dumps([{**row, 'enabled': True}]), KEYS, when=date(2026, 11, 18))


@pytest.mark.parametrize('model', ['gemini-4-carbon', 'gemini-4-argon'])
def test_announced_price_change_is_applied_by_the_real_catalog(model):
    row = next(r for r in ADDITIONS if r['model'] == model)
    activated = json.dumps([{**row, 'enabled': True, 'quality': 85}])
    november = parse_model_catalog(activated, KEYS, when=date(2026, 11, 30))[0]
    december = parse_model_catalog(activated, KEYS, when=date(2026, 12, 1))[0]
    assert december.option.output_per_million == november.option.output_per_million * 2


def test_discovery_follows_google_pages_with_get_and_header_only_key():
    requests = []
    def transport(req, **kwargs):
        requests.append(req)
        if len(requests) == 1:
            return response({'models': [{'name': 'models/gemini-4-carbon'}], 'nextPageToken': 'page/2'})
        return response({'models': [{'name': 'models/gemini-nano-banana-2.1'}]})
    result = discover_provider('gemini', KEYS, transport=transport)
    assert result['status'] == 'ACCOUNT_VISIBLE'
    assert len(result['models']) == 2
    assert all(r.get_method() == 'GET' and r.data is None for r in requests)
    assert all('secret-test-value' not in r.full_url for r in requests)
    assert requests[1].full_url.endswith('pageToken=page%2F2')
    assert not result['generation_verified']
    assert not result['billing_verified']


def test_missing_key_never_contacts_a_provider():
    transport = mock.Mock(side_effect=AssertionError('network forbidden'))
    result = discover_provider('openai', {}, transport=transport)
    assert result['status'] == 'NOT_CONFIGURED'
    transport.assert_not_called()


def test_partial_or_failed_listing_is_not_reported_as_complete_and_errors_are_redacted():
    def transport(req, **kwargs):
        raise HTTPError(req.full_url, 401, 'secret-test-value', {}, io.BytesIO(b'secret-test-value'))
    result = discover_provider('openai', KEYS, transport=transport)
    assert result['status'] == 'BLOCKED'
    assert 'secret-test-value' not in json.dumps(result)
    repeated = lambda *a, **k: response({'data': [{'id': 'claude-opus-5-5'}], 'has_more': True, 'last_id': 'repeat'})
    result = discover_provider('anthropic', KEYS, transport=repeated)
    assert result['status'] == 'UNVERIFIED'
    assert result['models'] == []


def test_discovery_does_not_follow_cross_origin_redirect_with_provider_headers():
    seen = []

    def https_open(self, req):
        seen.append((req.full_url, req.get_method()))
        headers = Message()
        if len(seen) == 1:
            headers['Location'] = 'https://other-origin.example.test/models'
            result = addinfourl(io.BytesIO(), headers, req.full_url, 302)
            result.msg = 'Found'
        else:
            result = addinfourl(response({'data': [{'id': 'other-origin-model'}]}), headers, req.full_url, 200)
            result.msg = 'OK'
        return result

    # Stub the wire only. The production opener and redirect handler dispatch the 302.
    with mock.patch.object(HTTPSHandler, 'https_open', https_open):
        result = discover_provider('openai', KEYS)
    assert seen == [('https://api.openai.com/v1/models', 'GET')]
    assert result['status'] == 'UNVERIFIED'
    assert result['models'] == []


def test_incomplete_listing_at_page_limit_is_unverified():
    pages = []

    def transport(req, **kwargs):
        pages.append(req.full_url)
        page = len(pages)
        return response({'models': [{'name': f'models/test-model-{page}'}],
                         'nextPageToken': f'page-{page}'})

    result = discover_provider('gemini', KEYS, transport=transport)
    assert len(pages) == MAX_PAGES
    assert result['status'] == 'UNVERIFIED'
    assert result['models'] == []
    assert not result['generation_verified']
    assert not result['billing_verified']
