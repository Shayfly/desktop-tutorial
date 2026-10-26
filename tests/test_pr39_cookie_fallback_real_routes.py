"""PR #39 counter-review: cookie fallback on REAL routes, not the probe.

Expected on PR #39 head 67f6d77:
  RED  test_bad_bearer_plus_cookie_me_is_200                 (handler re-reads the bad Bearer)
  RED  test_bad_bearer_plus_cookie_projects_is_200           (same)
  RED  test_basic_auth_plus_cookie_middleware_only_is_401    (middleware silently uses the cookie)
  GREEN test_basic_auth_plus_cookie_me_is_401                 (handler rejects it anyway)
  GREEN test_auth_required_routes_reject_anonymous[*]
  RED/SKIP test_branch_is_not_behind_main                     (skips when origin/main is not fetched)
"""
import os
import subprocess
import uuid

import pytest
from fastapi.testclient import TestClient

from omni_prod import investor_app

COOKIE = '148ai_session'
SAME_ORIGIN = {'Origin': 'http://testserver'}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _platform_secret() -> str:
    # The secret the in-memory V28 account service signs with; the middleware
    # must verify with the same one.
    return getattr(investor_app._v28.accounts, '_secret', None) or investor_app._control_plane_secret()


@pytest.fixture
def user_token():
    client = TestClient(investor_app.app)
    r = client.post('/api/v28/auth/register',
                    json={'email': f'pr39-{uuid.uuid4().hex[:10]}@example.test', 'password': 'pr39-test-password'})
    assert r.status_code == 200, r.text[:300]
    return r.json()['token']


@pytest.fixture
def prod(monkeypatch):
    monkeypatch.setenv('OMNI_ENV', 'production')
    monkeypatch.setenv('OMNI_SECRET_KEY', _platform_secret())
    return TestClient(investor_app.app)


# --- א/ב: invalid Bearer + valid cookie on real routes -----------------------

def test_bad_bearer_plus_cookie_me_is_200(prod, user_token):
    prod.cookies.set(COOKIE, user_token)
    r = prod.get('/api/v28/me', headers={'Authorization': 'Bearer invalid'})
    assert r.status_code == 200, (r.status_code, r.text[:200])


def test_bad_bearer_plus_cookie_projects_is_200(prod, user_token):
    prod.cookies.set(COOKIE, user_token)
    r = prod.get('/api/v28/projects', headers={'Authorization': 'Bearer invalid'})
    assert r.status_code == 200, (r.status_code, r.text[:200])


def test_cookie_only_me_is_200(prod, user_token):
    # Control: the primary PR #39 goal (cookie-only browser session) on a real route.
    prod.cookies.set(COOKIE, user_token)
    r = prod.get('/api/v28/me')
    assert r.status_code == 200, (r.status_code, r.text[:200])


# --- ג: explicit non-Bearer credentials must not become the cookie identity ---

def test_basic_auth_plus_cookie_me_is_401(prod, user_token):
    prod.cookies.set(COOKIE, user_token)
    r = prod.get('/api/v28/me', headers={'Authorization': 'Basic dXNlcjpwYXNz'})
    assert r.status_code == 401, (r.status_code, r.text[:200])


def test_basic_auth_plus_cookie_middleware_only_is_401(prod, user_token):
    # /api/billing/classify has no auth in its handler: the middleware is the only gate.
    prod.cookies.set(COOKIE, user_token)
    r = prod.post('/api/billing/classify', json={'category': 'bug'},
                  headers={'Authorization': 'Basic dXNlcjpwYXNz', **SAME_ORIGIN})
    assert r.status_code == 401, (r.status_code, r.text[:200])


# --- auth-required routes under the public /api/v28/auth/ prefix ---------------

AUTH_REQUIRED = [
    ('GET', '/api/v28/auth/sessions', None),
    ('POST', '/api/v28/auth/sessions/s1/revoke', None),
    ('POST', '/api/v28/auth/consents', {'consent_type': 'terms', 'version': '1'}),
    ('POST', '/api/v28/auth/data-export', None),
    ('POST', '/api/v28/auth/account-deletion', None),
    ('POST', '/api/v28/auth/email-verification/request', None),
]


@pytest.mark.parametrize('method,path,body', AUTH_REQUIRED, ids=[p for _, p, _ in AUTH_REQUIRED])
def test_auth_required_routes_reject_anonymous(prod, method, path, body):
    r = prod.request(method, path, json=body, headers=SAME_ORIGIN)
    assert r.status_code == 401, (path, r.status_code, r.text[:200])


@pytest.mark.parametrize('method,path,body', AUTH_REQUIRED, ids=[p for _, p, _ in AUTH_REQUIRED])
def test_auth_required_routes_reject_bad_bearer(prod, method, path, body):
    r = prod.request(method, path, json=body, headers={'Authorization': 'Bearer invalid', **SAME_ORIGIN})
    assert r.status_code in (401, 403), (path, r.status_code, r.text[:200])


# --- ד: branch freshness -----------------------------------------------------

def _git(*args):
    return subprocess.run(['git', '-C', ROOT, *args], capture_output=True, text=True, timeout=30)


def test_branch_is_not_behind_main():
    if _git('rev-parse', '--verify', '-q', 'origin/main').returncode != 0:
        pytest.skip('origin/main not fetched (shallow CI checkout)')
    if _git('rev-parse', '--is-shallow-repository').stdout.strip() == 'true' \
            and _git('merge-base', 'origin/main', 'HEAD').returncode != 0:
        pytest.skip('shallow clone: merge-base unavailable')
    behind = _git('rev-list', '--count', 'HEAD..origin/main').stdout.strip()
    assert behind == '0', f'branch is {behind} commit(s) behind origin/main'
