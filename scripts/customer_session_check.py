"""Warehouse 107 (owner 2026-11-16; was 82): the stored customer session is checked on production, and it fails out loud.

A logged-in non-founder customer session (a Playwright storage_state JSON) is kept in the GitHub secret
CUSTOMER_STORAGE_STATE. Browser checks that act as a customer load it. This check is their guard: it opens
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
DEFAULT_BASE = 'https://148aiv28.vercel.app'
REFRESH = ('log in as the test customer, save the browser storage_state (Playwright context.storage_state()) '
           f'and put the JSON in the repository secret {STORED_SESSION_VAR}')


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


def check(raw: str | None, base: str = DEFAULT_BASE, get=_get) -> dict:
    """Returns {'account_id', 'email_domain'} for a live non-founder customer session. Raises SessionProblem."""
    cookie = session_cookie(raw, base)
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
    try:
        who = check(os.environ.get(STORED_SESSION_VAR), base)
    except SessionProblem as p:
        print(f'::error title=customer session {p.code}::{p}')
        return 1
    print(f"::notice title=customer session::PASS account {who['account_id']} (@{who['email_domain']}) is a live "
          f'non-founder session on {base}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
