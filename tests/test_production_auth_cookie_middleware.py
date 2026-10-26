import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from omni_prod import investor_app
from omni_prod.auth import issue_token

SECRET = 'cookie-middleware-test-secret-0123456789'
PROTECTED = '/api/_cookie_mw_probe'
COOKIE = '148ai_session'


@investor_app.app.get(PROTECTED)
@investor_app.app.post(PROTECTED)
async def _probe(request: Request):
    auth = getattr(request.state, 'auth', None)
    return {'user_id': getattr(auth, 'user_id', None)}


def _token(user_id='u1'):
    return issue_token(secret=SECRET, user_id=user_id, org_id='o1', role='owner')


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('OMNI_ENV', 'production')
    monkeypatch.setenv('OMNI_SECRET_KEY', SECRET)
    return TestClient(investor_app.app)


def test_no_credentials_is_401(client):
    r = client.get(PROTECTED)
    assert r.status_code == 401 and r.json() == {'detail': 'authentication required'}


def test_bearer_passes_sets_state_and_wins_over_cookie(client):
    client.cookies.set(COOKIE, 'garbage')
    r = client.get(PROTECTED, headers={'Authorization': f'Bearer {_token("bearer-user")}'})
    assert r.status_code == 200 and r.json()['user_id'] == 'bearer-user'


def test_cookie_get_passes(client):
    client.cookies.set(COOKIE, _token('cookie-user'))
    r = client.get(PROTECTED)
    assert r.status_code == 200 and r.json()['user_id'] == 'cookie-user'


def test_invalid_bearer_uses_valid_cookie(client):
    client.cookies.set(COOKIE, _token('cookie-user'))
    r = client.get(PROTECTED, headers={'Authorization': 'Bearer invalid'})
    assert r.status_code == 200 and r.json()['user_id'] == 'cookie-user'


def test_malformed_authorization_uses_valid_cookie(client):
    client.cookies.set(COOKIE, _token('cookie-user'))
    r = client.get(PROTECTED, headers={'Authorization': 'Basic garbage'})
    assert r.status_code == 200 and r.json()['user_id'] == 'cookie-user'


def test_bad_bearer_cookie_fallback_enforces_csrf(client):
    client.cookies.set(COOKIE, _token('cookie-user'))
    r = client.post(PROTECTED, headers={'Authorization': 'Bearer invalid',
                                        'Origin': 'https://evil.example'})
    assert r.status_code == 403
    r = client.post(PROTECTED, headers={'Authorization': 'Bearer invalid',
                                        'Origin': 'http://testserver'})
    assert r.status_code == 200 and r.json()['user_id'] == 'cookie-user'


def test_invalid_bearer_and_invalid_cookie_is_401(client):
    client.cookies.set(COOKIE, 'invalid-cookie')
    r = client.get(PROTECTED, headers={'Authorization': 'Bearer invalid'})
    assert r.status_code == 401


def test_cookie_post_same_origin_passes(client):
    client.cookies.set(COOKIE, _token())
    r = client.post(PROTECTED, headers={'Origin': 'http://testserver'})
    assert r.status_code == 200
    r = client.post(PROTECTED, headers={'Sec-Fetch-Site': 'same-origin'})
    assert r.status_code == 200


def test_cookie_post_cross_origin_is_403(client):
    client.cookies.set(COOKIE, _token())
    r = client.post(PROTECTED, headers={'Origin': 'https://evil.example'})
    assert r.status_code == 403
    assert r.json()['detail'].startswith('cross-site request refused')


def test_garbage_token_is_401(client):
    r = client.get(PROTECTED, headers={'Authorization': 'Bearer not-a-token'})
    assert r.status_code == 401 and r.json() == {'detail': 'invalid authentication'}
    client.cookies.set(COOKIE, 'not-a-token')
    r = client.get(PROTECTED)
    assert r.status_code == 401 and r.json() == {'detail': 'invalid authentication'}


def test_public_prefixes_bypass(client):
    assert client.get('/api/status').status_code == 200
    assert client.get('/api/v28/launch/readiness').status_code == 200
    assert client.get('/api/v28/pricing').status_code != 401


def test_inert_outside_production(monkeypatch):
    monkeypatch.setenv('OMNI_ENV', 'development')
    r = TestClient(investor_app.app).get(PROTECTED)
    assert r.status_code == 200 and r.json()['user_id'] is None
