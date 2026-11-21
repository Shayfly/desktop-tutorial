"""Warehouse 107 (owner 2026-11-16; was 82): the stored customer session is checked on production, and it fails out loud.

2026-11-21 (owner: "only you work"; finding: a login session lives 7 days, identity_lifecycle.SESSION_TTL, so a stored
session turns this job red every week until someone refreshes it by hand): the check now logs in BY ITSELF when the
secrets CUSTOMER_TEST_EMAIL and CUSTOMER_TEST_PASSWORD exist. It calls the official POST /api/v28/auth/register, which
creates the account on the first run and logs in on every later one (investor_app.py: an existing account with the
right password is logged in; a wrong password is 409), checks /api/v28/me with that fresh session exactly as below, and
revokes it with POST /api/v28/auth/logout. Neither the address nor the password is ever printed.
The older way still works when the two secrets are absent: a logged-in non-founder customer session (a Playwright
storage_state JSON) kept in the GitHub secret CUSTOMER_STORAGE_STATE. Browser checks that act as a customer load it. This check is their guard: it opens
GET /api/v28/me on production with that session's cookie and says, as a readable ::error, exactly what is wrong:

  - the secret is missing or empty               -> MISSING      (a failure, never a skip)
  - the secret is not a storage_state with the session cookie for the host -> MALFORMED
  - production answers 401 (expired or revoked)   -> UNAUTHORIZED
  - the session is the founder's account          -> FOUNDER      (the founder is built without plan limits; a customer check
                                                                     on it proves nothing about customers)
  - any other answer, or no answer                -> UNEXPECTED

The cookie value is never printed. Standard library only, so it runs on a bare runner.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from omni_prod.browser_session import COOKIE_NAME  # noqa: E402
from omni_prod.pricing import m5_founder_account  # noqa: E402

STORED_SESSION_VAR = 'CUSTOMER_STORAGE_STATE'   # the name of the GitHub secret, not a value
EMAIL_VAR, PASSWORD_VAR = 'CUSTOMER_TEST_EMAIL', 'CUSTOMER_TEST_PASSWORD'   # names of GitHub secrets, not values
DEFAULT_BASE = 'https://148aiv28.vercel.app'
REFRESH = ('log in as the test customer, save the browser storage_state (Playwright context.storage_state()) '
           f'and put the JSON in the repository secret {STORED_SESSION_VAR}')
LOGIN_HOW = (f'create the repository secrets {EMAIL_VAR} (a test customer address, not the founder\'s) and {PASSWORD_VAR} '
             '(a password used only for it); the check registers that account on its first run and logs in fresh every day')


class SessionProblem(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def session_cookie(raw: str | None, base: str) -> str:
    """The session cookie's value for `base`'s host, from a storage_state JSON. Raises SessionProblem."""
    if raw is None or not raw.strip():
        raise SessionProblem('MISSING', f'the secret {STORED_SESSION_VAR} is not set or is empty; to set it: {REFRESH}')
    try:
        state = json.loads(raw)
    except ValueError as exc:
        raise SessionProblem('MALFORMED', f'{STORED_SESSION_VAR} is not JSON ({exc.msg}); expected a Playwright storage_state') from None
    cookies = state.get('cookies') if isinstance(state, dict) else None
    if not isinstance(cookies, list):
        raise SessionProblem('MALFORMED', f'{STORED_SESSION_VAR} has no "cookies" list; expected a Playwright storage_state')
    host = urlsplit(base).hostname or ''
    for c in cookies:
        if (isinstance(c, dict) and c.get('name') == COOKIE_NAME and c.get('value')
                and host.endswith(str(c.get('domain', '')).lstrip('.'))):
            return str(c['value'])
    raise SessionProblem('MALFORMED', f'{STORED_SESSION_VAR} has no {COOKIE_NAME} cookie for {host}; {REFRESH}')


def _get(url: str, cookie: str, timeout: float = 25):
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'Cookie': f'{COOKIE_NAME}={cookie}'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode('utf-8', 'replace')


def _post(url: str, payload: dict, cookie: str | None = None, timeout: float = 25):
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    if cookie:
        headers['Cookie'] = f'{COOKIE_NAME}={cookie}'
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode('utf-8', 'replace')


def _detail(body: str) -> str:
    try:
        return str(json.loads(body).get('detail', ''))[:200]
    except (ValueError, AttributeError):
        return body[:200]


def login(email: str, password: str, base: str = DEFAULT_BASE, post=_post) -> tuple[str, bool]:
    """A fresh session token for the test customer, and whether this call created the account. Raises SessionProblem."""
    url = base.rstrip('/') + '/api/v28/auth/register'
    try:
        status, body = post(url, {'email': email, 'password': password})
    except OSError as exc:
        raise SessionProblem('UNEXPECTED', f'no answer from {base}/api/v28/auth/register ({type(exc).__name__})') from None
    if status == 409:
        raise SessionProblem('UNAUTHORIZED', f'the test customer already exists and {PASSWORD_VAR} does not match it; '
                                             f'set its right password, or a new address in {EMAIL_VAR}')
    if status != 200:
        raise SessionProblem('UNEXPECTED', f'production answered HTTP {status} to /api/v28/auth/register (expected 200): '
                                           f'{_detail(body)}')
    try:
        data = json.loads(body)
        token = str(data['token'])
    except (ValueError, KeyError, TypeError):
        raise SessionProblem('UNEXPECTED', '/api/v28/auth/register answered 200 without a session token') from None
    if not token:
        raise SessionProblem('UNEXPECTED', '/api/v28/auth/register answered 200 with an empty session token')
    return token, not data.get('existing_account')


def logout(base: str, cookie: str, post=_post) -> bool:
    """Revoke the session this check opened. True when production confirmed it."""
    try:
        status, _ = post(base.rstrip('/') + '/api/v28/auth/logout', {}, cookie=cookie)
    except OSError:
        return False
    return status == 200


def check(raw: str | None, base: str = DEFAULT_BASE, get=_get) -> dict:
    """Returns {'account_id', 'email_domain'} for a live non-founder customer session. Raises SessionProblem."""
    return check_cookie(session_cookie(raw, base), base, get)


def check_cookie(cookie: str, base: str = DEFAULT_BASE, get=_get) -> dict:
    """The same answer for a session cookie value (stored, or just opened by login)."""
    try:
        status, body = get(base.rstrip('/') + '/api/v28/me', cookie)
    except OSError as exc:
        raise SessionProblem('UNEXPECTED', f'no answer from {base}/api/v28/me ({type(exc).__name__})') from None
    if status == 401:
        raise SessionProblem('UNAUTHORIZED', f'production answered 401 to the stored customer session: it expired or was '
                                             f'revoked; refresh it: {REFRESH}')
    if status != 200:
        raise SessionProblem('UNEXPECTED', f'production answered HTTP {status} to /api/v28/me (expected 200)')
    try:
        me = json.loads(body)
        account_id = str(me['id'])
    except (ValueError, KeyError, TypeError):
        raise SessionProblem('UNEXPECTED', '/api/v28/me answered 200 without an account id') from None
    if m5_founder_account(account_id):
        raise SessionProblem('FOUNDER', f'the stored session is the founder account ({account_id}), which is built without '
                                        f'plan limits; store a non-founder customer instead')
    return {'account_id': account_id, 'email_domain': str(me.get('email', '')).rpartition('@')[2]}


def main() -> int:
    base = os.environ.get('BASE_URL', DEFAULT_BASE)
    email = os.environ.get(EMAIL_VAR, '').strip()
    password = os.environ.get(PASSWORD_VAR, '')
    raw = os.environ.get(STORED_SESSION_VAR)
    try:
        if email and password:                            # preferred: a fresh login every run, nothing to expire
            token, created = login(email, password, base)
            try:
                who = check_cookie(token, base)
            finally:
                revoked = logout(base, token)
            how = ('logged in fresh' + ('; the account was created on this run' if created else '')
                   + ('; the session was revoked' if revoked else '; the session could NOT be revoked'))
        elif email or password:
            raise SessionProblem('MISSING', f'only one of {EMAIL_VAR} and {PASSWORD_VAR} is set; set both')
        elif raw is None or not raw.strip():
            raise SessionProblem('MISSING', f'the secret {STORED_SESSION_VAR} is not set or is empty, and neither are '
                                            f'{EMAIL_VAR} and {PASSWORD_VAR}; to fix it: {LOGIN_HOW} (the older way, a '
                                            f'stored session that expires after 7 days: {REFRESH})')
        else:
            who, how = check(raw, base), 'stored session'
    except SessionProblem as p:
        print(f'::error title=customer session {p.code}::{p}')
        return 1
    print(f"::notice title=customer session::PASS account {who['account_id']} (@{who['email_domain']}) is a live "
          f'non-founder session on {base} ({how})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
