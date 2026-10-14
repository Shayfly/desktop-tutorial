"""Replicate HTTP contract tests; no paid provider calls."""
import io
import json
from decimal import Decimal
from urllib.error import HTTPError

from omni_prod.providers.image_provider import (
    ImageProviderConfig, build_image_provider, MemorySubmissionJournal,
)
from omni_prod.capabilities import CapabilityRequirement


def test_saved_replicate_token_selects_priced_image_provider():
    config = ImageProviderConfig.from_env({'REPLICATE_API_TOKEN': 'test-only-token'})
    assert config.status()[0] == 'PARTIAL'
    assert config.api_key_ref == 'env:REPLICATE_API_TOKEN'
    assert config.model == 'black-forest-labs/flux-schnell'
    assert config.maximum_usd_per_image == Decimal('0.003')


def test_explicit_other_provider_is_preserved():
    config = ImageProviderConfig.from_env({
        'REPLICATE_API_TOKEN': 'test-only-token',
        'OMNI_IMAGE_PROVIDER_BASE_URL': 'https://other.example/v1',
    })
    assert config.base_url == 'https://other.example/v1'
    assert config.api_key_ref == ''


def test_replicate_official_model_submit_uses_input_only_and_resumes():
    calls = []

    def transport(req, timeout):
        calls.append(req)
        assert req.get_header('User-agent') == '148AI/1.0'
        assert req.full_url == 'https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions'
        assert json.loads(req.data) == {'input': {'prompt': 'Original blue bird icon', 'output_format': 'png', 'num_outputs': 1}}
        return io.BytesIO(b'{"id":"prediction-123","status":"starting"}')

    provider = build_image_provider({'REPLICATE_API_TOKEN': 'test-only-token'},
        journal=MemorySubmissionJournal(), urlopen=transport)
    assert provider is not None
    req = CapabilityRequirement(id='icon', key='media.image.generate', purpose='icon',
        required=True, constraints={'prompt': 'Original blue bird icon'})
    first = provider.submit(req, idempotency_key='build-icon')
    second = provider.submit(req, idempotency_key='build-icon')
    assert first.provider_task_id == second.provider_task_id == 'prediction-123'
    assert len(calls) == 1


def test_check_authenticates_without_generation_and_hides_account_data():
    from omni_prod.providers.replicate_connection import check_replicate_connection

    def transport(req, timeout):
        assert req.get_header('User-agent') == '148AI/1.0'
        assert req.get_header('Accept') == 'application/json'
        assert req.get_method() == 'GET'
        assert req.full_url == 'https://api.replicate.com/v1/account'
        assert req.get_header('Authorization') == 'Bearer test-only-token'
        return io.BytesIO(b'{"username":"private-owner","email":"private@example.com"}')

    result = check_replicate_connection({'REPLICATE_API_TOKEN': 'test-only-token'}, urlopen=transport)
    assert result['connection_verified'] is True
    assert result['generation_verified'] is False
    assert 'private-owner' not in json.dumps(result)
    assert 'test-only-token' not in json.dumps(result)


def test_missing_token_makes_no_network_call():
    from omni_prod.providers.replicate_connection import check_replicate_connection
    def transport(*args, **kwargs):
        raise AssertionError('must not call without a token')
    assert check_replicate_connection({}, urlopen=transport)['status'] == 'NOT_CONFIGURED'


def test_provider_error_body_and_token_are_never_returned():
    from omni_prod.providers.replicate_connection import check_replicate_connection
    def transport(req, timeout):
        raise HTTPError(req.full_url, 401, 'test-only-token', {}, io.BytesIO(b'private error'))
    result = check_replicate_connection({'REPLICATE_API_TOKEN': 'test-only-token'}, urlopen=transport)
    assert result['status'] == 'BLOCKED'
    assert result['http_status'] == 401
    assert 'test-only-token' not in json.dumps(result)


def test_check_route_requires_session_before_provider_call(monkeypatch):
    from fastapi.testclient import TestClient
    from omni_prod.investor_app import app
    from omni_prod.providers import replicate_connection
    def forbidden(*args, **kwargs):
        raise AssertionError('unauthenticated caller must never reach Replicate')
    monkeypatch.setattr(replicate_connection, 'check_replicate_connection', forbidden)
    client = TestClient(app)
    assert client.post('/api/v28/providers/replicate/check').status_code == 401
    assert client.get('/api/v28/providers/replicate/check').status_code == 401


def test_authenticated_route_returns_only_connection_result(monkeypatch):
    import uuid
    from fastapi.testclient import TestClient
    from omni_prod.investor_app import app
    from omni_prod.providers import replicate_connection
    client = TestClient(app)
    signup = client.post('/api/v28/auth/register', json={
        'email': 'replicate-' + uuid.uuid4().hex + '@example.com',
        'password': 'TestOnlyPassword123!',
    })
    assert signup.status_code == 200
    monkeypatch.delenv('REPLICATE_API_TOKEN', raising=False)
    result = client.post('/api/v28/providers/replicate/check',
        headers={'Authorization': 'Bearer ' + signup.json()['token']})
    assert result.status_code == 200
    assert result.json()['status'] == 'NOT_CONFIGURED'
    assert result.json()['generation_verified'] is False
    assert client.get('/api/v28/providers/replicate/check',
        headers={'Authorization': 'Bearer ' + signup.json()['token']}).json()['status'] == 'NOT_CONFIGURED'


def test_403_diagnostics_distinguish_edge_challenge_without_returning_body():
    from omni_prod.providers.replicate_connection import check_replicate_connection
    def transport(req, timeout):
        raise HTTPError(req.full_url, 403, 'Forbidden', {'Content-Type': 'text/html', 'cf-mitigated': 'challenge'}, io.BytesIO(b'<html>secret-test-token challenge private-owner</html>'))
    result = check_replicate_connection({'REPLICATE_API_TOKEN': 'secret-test-token'}, urlopen=transport)
    assert result['rejection_category'] == 'edge_challenge'
    assert result['token_format_valid'] is False
    assert 'secret-test-token' not in json.dumps(result)
    assert 'private-owner' not in json.dumps(result)


def test_403_diagnostics_identify_billing_json_without_returning_private_fields():
    from omni_prod.providers.replicate_connection import check_replicate_connection
    def transport(req, timeout):
        raise HTTPError(req.full_url, 403, 'Forbidden', {'Content-Type': 'application/json'}, io.BytesIO(b'{"detail":"Billing required for private-owner"}'))
    result = check_replicate_connection({'REPLICATE_API_TOKEN': 'test-only-token'}, urlopen=transport)
    assert result['rejection_category'] == 'billing'
    assert result['upstream_response_kind'] == 'json'
    assert 'private-owner' not in json.dumps(result)
