"""Rate limits on the platform API, shared by every serverless instance (the owner's approval, 2026-11-26 08:56 UTC).

Until this module no route had a limit: the password login, registration, password reset and e-mail verification could
be called without bound -- password guessing, account enumeration by volume. omni_prod/rate_limit.py and
omni_prod/limits.py existed and were imported by nothing but two tests (tests/test_v24_native_remote.py,
tests/test_v13_core.py); they are not used here and stay as they were.

What is limited, by how much and why: the named Limit constants below, each with its reason, and ROUTES, the only place
that binds a route to its limits. Social sign-in (another branch) uses the same store through enforce().

Only routes that protect an account are limited. The owner, 2026-11-26 10:01 ("(א)"): every customer limit that is not
money is cancelled, and his own builds have no limit -- so the conversation, builds and change requests carry none here
(a first draft of this module limited them per account; that was removed before it merged).

Nobody can lock someone else out (review of fed6427, B1). A counter of one e-mail fed by everybody's attempts let anyone
keep any e-mail out of sign-in and password reset by knocking every 90 s. So the strict counters are per (e-mail,
address): an attacker fills only his own. The counter of the e-mail alone counts FAILED sign-ins only and is loose; when
it is over, the password is still checked -- the right one signs in (if that address is within its own limits), a wrong
one gets 429. The trade-off, said in STATUS.md: guessing spread over many addresses is bounded by the per-address limits
and by that loose counter, not by a strict per-account one.

The store. One PostgreSQL table, infra/postgres/047_rate_limits.sql: a row per (limit, subject, window) and one atomic
INSERT ... ON CONFLICT DO UPDATE that adds the hit and returns the count, so every Vercel instance reads the same count in
one statement. PostgreSQL rather than Redis: the database is there wherever the app keeps accounts (Production and each
Preview's own Neon branch), while OMNI_REDIS_URL is Production-only (investor_app._preview_without_queue); and the routes
that need the strictest limits -- sign-in -- already depend on that database for the account itself, so the limiter
adds no new way for them to fail. A subject is stored as an HMAC-SHA256 keyed from OMNI_SECRET_KEY, never as the
address, the e-mail or the account id. A flood writes a bounded number of rows (review S4): the address counters are
asked first and nothing else is written once one refuses, and a counter stops at twice its limit.

The window. A sliding-window counter: estimate = previous window's count x the share of it still inside the window +
this window's count. It smooths the double burst a fixed window allows across its edge. Refused attempts count (up to
twice the limit): a client that keeps knocking stays out longer; a person who waits the Retry-After gets in.

When the store cannot answer (database down, table missing, a statement over STATEMENT_TIMEOUT_MS) every limited
route fails CLOSED: 503, a sentence in Hebrew, Arabic and English, Retry-After, and an ERROR log line. An unlimited
sign-in is the hole this closes, and sign-in needs the same database for the account anyway. A missing table means
migration 047 was not applied: the log line and GET /api/v28/deployment ("rate_limits") name it. After a failure the
store is not asked again for STORE_RETRY_SECONDS, so an outage is answered at once, not after a timeout per request.
Memory mode (no database; development only -- production refuses it at start in investor_app._build_v28_platform) has
no store every instance sees: off Vercel the limits are not enforced and that is logged once; on Vercel it counts as an
unavailable store.

The client address. On Vercel (VERCEL=1, a system variable present at build and run time) it is the x-real-ip header.
Vercel's edge sets it: its documentation says x-real-ip is identical to x-forwarded-for, which Vercel overwrites and
does not forward from the client "to prevent IP spoofing"; Vercel's own Python SDK reads exactly this header (package
vercel 0.3.8, vercel/headers.py: IP_HEADER_NAME = "x-real-ip"); and a function is reachable only through that edge. Off
Vercel every forwarded header is the client's own word, so the socket peer is used (the Dockerfile's uvicorn trusts
forwarded headers from 127.0.0.1 only). An IPv6 address counts by its /64 (one customer's allocation).

Account enumeration (the same change): a login with an unknown e-mail runs the same password hash as a wrong password
(identity_lifecycle.IdentityService.login, account_tenant.AccountService.login), and a password-reset request answers in
no less than RESET_ANSWER_SECONDS whether a reset token was written or not (answers_no_sooner_than). The counters are
kept for any e-mail typed, so a refusal says nothing about whether an account exists either.
"""
from __future__ import annotations

import asyncio
import functools
import hashlib
import hmac
import ipaddress
import json
import logging
import math
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping

from .auth import AuthError, verify_token
from .browser_session import COOKIE_NAME

_log = logging.getLogger('omni_prod.rate_limits')

SUBJECTS = ('ip', 'identifier', 'identifier_ip', 'account')
MINUTE, HOUR = 60, 3600


@dataclass(frozen=True)
class Limit:
    """At most `limit` requests per `window_seconds` per subject (sliding window). `subject` is what is counted: the
    client address, the e-mail typed (`identifier`), the pair (`identifier_ip`) or the signed-in account (an unsigned
    request is counted by its address)."""
    name: str
    limit: int
    window_seconds: int
    subject: str
    reason: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', self.name):
            raise ValueError(f'limit name {self.name!r}: lower-case letters, digits and _ only (a database value)')
        if self.subject not in SUBJECTS:
            raise ValueError(f'limit {self.name}: subject {self.subject!r} is not one of {SUBJECTS}')
        if self.limit < 1 or self.window_seconds < 1:
            raise ValueError(f'limit {self.name}: the limit and the window must be at least 1')
        if not self.reason.strip():
            raise ValueError(f'limit {self.name} has no reason')


# ---- the account routes (every one fails closed when the store cannot answer) ---------------------------------------
LOGIN_PER_IDENTIFIER_AND_IP = Limit(
    'login_identifier_ip', 10, 15 * MINUTE, 'identifier_ip',
    'A person who mistypes or forgot a password tries a few times; 10 tries in 15 minutes from one address covers that '
    'and caps guessing from that address at 40 an hour against one account. Per (e-mail, address), so an attacker fills '
    'his own counter and never the owner\'s (review B1). Counted for any e-mail typed, known or not. Registration counts '
    'here too: given an e-mail that has an account, it signs in with the password typed.')
LOGIN_FAILURES_PER_IDENTIFIER = Limit(
    'login_failures_identifier', 100, HOUR, 'identifier',
    'Failed sign-ins of one e-mail from every address together; loose, because everybody can feed it. Over it, the '
    'password is still checked: the right one signs in, a wrong one gets 429 -- so it slows guessing spread over many '
    'addresses and never locks the owner out (review B1, the coordinator\'s decision).')
LOGIN_PER_IP = Limit(
    'login_ip', 50, 15 * MINUTE, 'ip',
    'One address trying many accounts (password spraying, leaked password lists) stops after 50 tries in 15 minutes; '
    '50 leaves room for an office or a school behind one address where several people sign in at once.')
REGISTER_PER_IP = Limit(
    'register_ip', 10, HOUR, 'ip',
    'A household or an office opens a few accounts; 10 an hour from one address stops a script opening free accounts in '
    'bulk to use the free conversation, and bounds the password hashing a flood of sign-ups costs.')
PASSWORD_RESET_PER_IDENTIFIER_AND_IP = Limit(
    'password_reset_identifier_ip', 5, HOUR, 'identifier_ip',
    'A reset link is valid for an hour (IdentityService.PASSWORD_RESET_TTL); 5 requests an hour from one address is more '
    'than a person needs. Per (e-mail, address): the reset e-mail is the owner\'s way back in, so a reset asked from an '
    'address within its limits always goes out, whatever others ask for the same e-mail (review B1).')
PASSWORD_RESET_PER_IP = Limit(
    'password_reset_ip', 20, HOUR, 'ip',
    'One address asking resets for many e-mails is probing for accounts or flooding inboxes; 20 an hour leaves room for '
    'a shared address.')
VERIFICATION_SEND_PER_ACCOUNT = Limit(
    'verification_send_account', 5, HOUR, 'account',
    'A verification link is valid for 24 hours (IdentityService.EMAIL_VERIFICATION_TTL); 5 sends an hour covers a lost '
    'e-mail and stops one account flooding its inbox or the token table. Only the signed-in account itself feeds it.')
VERIFICATION_SEND_PER_IP = Limit(
    'verification_send_ip', 20, HOUR, 'ip',
    'Many verification e-mails asked from one address is a script; 20 an hour leaves room for a shared address.')
ONE_TIME_TOKEN_PER_IP = Limit(
    'one_time_token_ip', 30, 15 * MINUTE, 'ip',
    'A person opens a verification or a reset link once or twice. The tokens are 256 random bits, so guessing one is '
    'hopeless anyway; 30 in 15 minutes bounds the database lookups one address can cause.')
PASSWORD_CHANGE_PER_ACCOUNT = Limit(
    'password_change_account', 10, 15 * MINUTE, 'account',
    'Changing the password asks for the current one; with a stolen session that is a way to guess it (two reviewers, '
    '2026-11-26: 25 wrong guesses in 1.3 s, all answered). 10 tries in 15 minutes per account, as for a login; only '
    'a session of that account feeds it.')
PASSWORD_CHANGE_PER_IP = Limit(
    'password_change_ip', 50, 15 * MINUTE, 'ip',
    'One address trying the current password of many sessions stops after 50 in 15 minutes, as for a login.')
OAUTH_START_PER_IP = Limit(
    'oauth_start_ip', 20, 10 * MINUTE, 'ip',
    'Social sign-in (branch claude/practical-hopper-oi3qj2-social-login; its START_LIMIT and START_WINDOW): a person '
    'starts it once or twice; 20 in 10 minutes from one address stops a script filling the state table. Its route calls '
    'enforce() and presents the refusal as its sign-in card does.')
OAUTH_CALLBACK_PER_IP = Limit(
    'oauth_callback_ip', 30, MINUTE, 'ip',
    'A provider calls back once per sign-in; 30 a minute from one address, counted by every instance together (that '
    'branch counts callbacks per instance). Its route calls enforce().')

LIMITS = (LOGIN_PER_IDENTIFIER_AND_IP, LOGIN_FAILURES_PER_IDENTIFIER, LOGIN_PER_IP, REGISTER_PER_IP,
          PASSWORD_RESET_PER_IDENTIFIER_AND_IP, PASSWORD_RESET_PER_IP, VERIFICATION_SEND_PER_ACCOUNT,
          VERIFICATION_SEND_PER_IP, ONE_TIME_TOKEN_PER_IP, PASSWORD_CHANGE_PER_ACCOUNT, PASSWORD_CHANGE_PER_IP,
          OAUTH_START_PER_IP, OAUTH_CALLBACK_PER_IP)

# A password-reset request answers in at least this long, so its time does not say which e-mails have an account: above
# its two database statements (a lookup, and a token row only for a known e-mail), below what a person notices.
RESET_ANSWER_SECONDS = 0.5
STORE_RETRY_SECONDS = 5             # after a store failure, the store is not asked again for 5 s
STATEMENT_TIMEOUT_MS = 2000         # one counter statement waits 2 s at most (a lock, a slow database), then fails
COUNT_CAP = 2                       # a counter stops at twice its limit: a flood updates one row, never grows it
SWEEP_INTERVAL_SECONDS = 60         # each instance deletes expired rows at most once a minute ...
SWEEP_BATCH = 500                   # ... at most 500 rows a statement ...
SWEEP_MAX_BATCHES = 4               # ... and 4 statements a sweep: every loop has a bound
HEALTH_CACHE_SECONDS = 60           # GET /api/v28/deployment asks the table at most once a minute per instance
IPV6_PREFIX = 64                    # an IPv6 address counts by its /64, one customer's allocation
UNIDENTIFIED = 'unidentified'       # on Vercel, a request without a valid x-real-ip: one shared counter


@dataclass(frozen=True)
class Route:
    method: str
    path: re.Pattern
    limits: tuple
    failures: Limit | None = None             # counted after the handler, only when it answers one of failure_statuses
    failure_statuses: frozenset = frozenset()


def _route(method: str, path: str, *limits: Limit, failures: Limit | None = None, on: tuple = ()) -> Route:
    return Route(method, re.compile(path), limits, failures, frozenset(on))


# The only binding of routes to limits. A path is matched whole against the route path (the ASGI path without its
# root_path), as the router matches it. /api/v28/auth/oauth/ is deliberately absent: those routes answer a browser
# navigation with a redirect to the sign-in card, so they call enforce() and present the refusal themselves.
ROUTES = (
    _route('POST', r'/api/v2[678]/auth/login', LOGIN_PER_IP, LOGIN_PER_IDENTIFIER_AND_IP,
           failures=LOGIN_FAILURES_PER_IDENTIFIER, on=(401,)),
    # registering an existing e-mail signs in with the password typed; a wrong one answers 409
    _route('POST', r'/api/v28/auth/register', REGISTER_PER_IP, LOGIN_PER_IDENTIFIER_AND_IP,
           failures=LOGIN_FAILURES_PER_IDENTIFIER, on=(409,)),
    _route('POST', r'/api/v2[67]/auth/register', REGISTER_PER_IP),
    _route('POST', r'/api/v28/auth/password-reset/request', PASSWORD_RESET_PER_IP, PASSWORD_RESET_PER_IDENTIFIER_AND_IP),
    _route('POST', r'/api/v28/auth/email-verification/request', VERIFICATION_SEND_PER_IP, VERIFICATION_SEND_PER_ACCOUNT),
    _route('POST', r'/api/v28/auth/(?:verify-email|password-reset/confirm)', ONE_TIME_TOKEN_PER_IP),
    _route('POST', r'/api/v28/me/password', PASSWORD_CHANGE_PER_IP, PASSWORD_CHANGE_PER_ACCOUNT),
)
# Routes bound above that are not on main yet: they are limited from the moment they merge, with no change here.
PENDING_ROUTES = {
    '/api/v28/me/password': 'the password change of the platform shell branch (claude/practical-hopper-oi3qj2-sidebar), '
                            'not on main f675730 (2026-11-26)',
}


def route_for(method: str, path: str) -> Route | None:
    for route in ROUTES:
        if route.method == method and route.path.fullmatch(path):
            return route
    return None


def limits_for(method: str, path: str) -> tuple:
    route = route_for(method, path)
    if route is None:
        return ()
    return route.limits + ((route.failures,) if route.failures else ())


# ---- who is asking ----------------------------------------------------------------------------------------------------
_noted: set = set()


def _note_once(key: str, message: str, *args) -> None:
    if key not in _noted:
        _noted.add(key)
        _log.warning(message, *args)


def _address(raw: str) -> str | None:
    try:
        ip = ipaddress.ip_address(raw.strip())
        if ip.version == 6:
            if ip.ipv4_mapped is not None:
                return str(ip.ipv4_mapped)
            return str(ipaddress.ip_network(f'{ip.exploded}/{IPV6_PREFIX}', strict=False))
        return str(ip)
    except ValueError:
        return None


def client_address(headers: Mapping[str, str], peer: str | None, environ: Mapping[str, str] | None = None) -> str | None:
    """The address a request is counted by. On Vercel (VERCEL=1): x-real-ip, which Vercel's edge sets (module docstring).
    Off Vercel: the socket peer; a forwarded header there is the client's own word and is never read. On Vercel a missing
    or malformed x-real-ip counts under UNIDENTIFIED -- one counter for every such request, logged at ERROR each time,
    so it fails toward limiting. None only off Vercel, for a peer that is not an IP address (the in-process test client,
    a Unix socket): address limits do not apply to it, which is logged once per process."""
    environ = os.environ if environ is None else environ
    if environ.get('VERCEL') == '1':
        raw = str(headers.get('x-real-ip') or '')
        address = _address(raw)
        if address is None:
            _log.error('rate limits: a request on Vercel without a valid x-real-ip (%r) is counted as %r',
                       raw[:64], UNIDENTIFIED)
            return UNIDENTIFIED
        return address
    address = _address(peer or '')
    if address is None:
        _note_once('peer', 'rate limits: off Vercel, a peer that is not an IP address (%r) has no address to count; '
                           'address limits do not apply to it', (peer or '')[:64])
    return address


def identifier_of(body: bytes) -> str | None:
    """The e-mail of a sign-in body, normalized as the identity service normalizes it (strip, lower case). Any size is
    read: padding a body must not skip the per-e-mail count. None when the body has no e-mail (the route refuses it)."""
    try:
        data = json.loads(body) if body else None
    except ValueError:                         # not JSON, not UTF-8: the route answers 422 by itself
        return None
    value = data.get('email') if isinstance(data, dict) else None
    if not isinstance(value, str):
        return None
    return value.strip().lower() or None


def account_of(headers: Mapping[str, str], cookies: Mapping[str, str], secret: str) -> str | None:
    """The account of a signed session (the Bearer header or the 148ai_session cookie), by its signature only -- no
    database. None for no session or a bad one: the request is then counted by its address, and the route refuses it."""
    raw = str(headers.get('authorization') or '').strip()
    token = raw[7:].strip() if raw.startswith('Bearer ') else str(cookies.get(COOKIE_NAME) or '')
    if not token:
        return None
    try:
        return verify_token(token, secret=secret).user_id
    except AuthError:
        return None


# ---- the sliding window -----------------------------------------------------------------------------------------------
def refusal_seconds(limit: Limit, elapsed: float, current: int, previous: int) -> int:
    """0 when a request is within `limit`, else the whole seconds until a new request would be (the Retry-After).
    `current` counts this request; `elapsed` is the time since this window began; nothing else is assumed to arrive."""
    n, window = limit.limit, float(limit.window_seconds)
    if previous * (window - elapsed) / window + current <= n:
        return 0
    waits = []
    if previous > 0 and current + 1 < n:       # later in this window, once enough of the previous one has faded
        waits.append(window - elapsed - window * (n - current - 1) / previous)
    if current <= n - 1:                        # at the start of the next window
        waits.append(window - elapsed)
    else:                                       # in the next window, where this window's count is the previous one
        waits.append(window - elapsed + window * (1 - (n - 1) / current))
    return max(1, math.ceil(min(w for w in waits if w > 0)))


# ---- stores -----------------------------------------------------------------------------------------------------------
def _ts(seconds: float) -> datetime:
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


# One statement per phase: every row is counted -- up to its cap, twice its limit -- and returned with its previous
# window's count. ORDER BY: concurrent requests lock their rows in the same order, so two of them never deadlock.
_HIT_SQL = """
WITH incoming(bucket, key_hash, window_start, expires_at, previous_start, cap) AS (
    SELECT * FROM unnest(%(buckets)s::text[], %(keys)s::text[], %(starts)s::timestamptz[],
                         %(expires)s::timestamptz[], %(previous)s::timestamptz[], %(caps)s::integer[])
), counted AS (
    INSERT INTO rate_limit_counters AS c (bucket, key_hash, window_start, hits, expires_at)
    SELECT bucket, key_hash, window_start, 1, expires_at FROM incoming ORDER BY bucket, key_hash
    ON CONFLICT (bucket, key_hash, window_start) DO UPDATE SET hits = LEAST(c.hits + 1, (
        SELECT i.cap FROM incoming i WHERE i.bucket = c.bucket AND i.key_hash = c.key_hash))
    RETURNING c.bucket, c.key_hash, c.hits
)
SELECT i.bucket, i.key_hash, n.hits, COALESCE(p.hits, 0)
FROM incoming i
JOIN counted n ON n.bucket = i.bucket AND n.key_hash = i.key_hash
LEFT JOIN rate_limit_counters p
       ON p.bucket = i.bucket AND p.key_hash = i.key_hash AND p.window_start = i.previous_start
"""

_SWEEP_SQL = """
DELETE FROM rate_limit_counters c
USING (SELECT bucket, key_hash, window_start FROM rate_limit_counters
       WHERE expires_at < %(now)s ORDER BY expires_at LIMIT %(batch)s FOR UPDATE SKIP LOCKED) old
WHERE c.bucket = old.bucket AND c.key_hash = old.key_hash AND c.window_start = old.window_start
"""


class PostgresRateLimitStore:
    """The counters every instance shares (infra/postgres/047_rate_limits.sql), on the app's account database pool."""
    kind = 'postgres'

    def __init__(self, pool) -> None:
        self._pool = pool

    def hit(self, rows: list) -> dict:
        """rows: (bucket, key_hash, window_start, expires_at, previous_start, cap), times in seconds since the epoch, one
        per counter. Returns {(bucket, key_hash): (count in this window including this hit, at most cap; count in the
        previous window)}."""
        buckets, keys, starts, expires, previous, caps = (list(col) for col in zip(*rows))
        with self._pool.connection() as conn:
            with conn.transaction():
                conn.execute(f'SET LOCAL statement_timeout = {int(STATEMENT_TIMEOUT_MS)}')
                found = conn.execute(_HIT_SQL, {
                    'buckets': buckets, 'keys': keys, 'starts': [_ts(s) for s in starts],
                    'expires': [_ts(s) for s in expires], 'previous': [_ts(s) for s in previous],
                    'caps': [int(c) for c in caps]}).fetchall()
        counts = {(b, k): (int(c), int(p)) for b, k, c, p in found}
        if len(counts) != len(rows):
            raise RuntimeError(f'the counter statement returned {len(counts)} rows for {len(rows)} counters')
        return counts

    def sweep(self, now: float, *, batch: int, max_batches: int) -> int:
        removed = 0
        for _ in range(max_batches):
            with self._pool.connection() as conn:
                with conn.transaction():
                    conn.execute(f'SET LOCAL statement_timeout = {int(STATEMENT_TIMEOUT_MS)}')
                    n = conn.execute(_SWEEP_SQL, {'now': _ts(now), 'batch': int(batch)}).rowcount
            removed += max(0, n)
            if n < batch:
                break
        return removed

    def table_present(self) -> bool:
        with self._pool.connection() as conn:
            return bool(conn.execute("SELECT to_regclass('rate_limit_counters') IS NOT NULL").fetchone()[0])


MIGRATION = '047_rate_limits'
MISSING_TABLE = (f'MISSING: migration {MIGRATION} (infra/postgres/{MIGRATION}.sql) is not applied to this database; '
                 'every sign-in route answers 503 until it is')


def _missing_table_hint(exc) -> str:
    return f' -- {MISSING_TABLE}' if 'rate_limit_counters' in str(exc) and 'not exist' in str(exc) else ''


class MemoryRateLimitStore:
    """One process's counters, for unit tests. store_for() never returns it: several instances would each count alone
    (negative control rate_limits NC2 swaps it in to prove the two-instance test sees exactly that)."""
    kind = 'memory'

    def __init__(self) -> None:
        self._rows: dict = {}
        self._lock = threading.Lock()

    def hit(self, rows: list) -> dict:
        out = {}
        with self._lock:
            for bucket, key, start, expires, previous, cap in rows:
                row = self._rows.setdefault((bucket, key, start), [0, expires])
                row[0] = min(row[0] + 1, cap)
                out[(bucket, key)] = (row[0], self._rows.get((bucket, key, previous), [0])[0])
        return out

    def sweep(self, now: float, *, batch: int, max_batches: int) -> int:
        with self._lock:
            old = sorted((exp, k) for k, (_, exp) in self._rows.items() if exp < now)[:batch * max_batches]
            for _, k in old:
                del self._rows[k]
        return len(old)


def store_for(pool):
    """The store every instance shares: the account database. None in memory mode (no database; development only)."""
    if pool is None:
        return None
    return PostgresRateLimitStore(pool)


# ---- the limiter ------------------------------------------------------------------------------------------------------
class StoreUnavailable(RuntimeError):
    """The counter store could not answer: a limited route is refused with 503 (fail closed)."""


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    retry_after: int = 0
    limit: Limit | None = None
    subject_digest: str = ''
    enforced: bool = True


class RateLimited(Exception):
    """Raised by RateLimiter.enforce: `verdict.limit` was exceeded; try again after `verdict.retry_after` seconds."""

    def __init__(self, verdict: Verdict) -> None:
        super().__init__(f'{verdict.limit.name if verdict.limit else "?"}: retry after {verdict.retry_after} s')
        self.verdict = verdict


class RateLimiter:
    """Counts requests against limits in the shared store. Built once per process; the store and the secret are taken
    on the first limited request (the app makes its database pool after the middleware is installed)."""

    def __init__(self, *, store_factory: Callable, secret_factory: Callable[[], str],
                 clock: Callable[[], float] = time.time) -> None:
        self._store_factory, self._secret_factory = store_factory, secret_factory
        self.clock = clock
        self._resolved = False
        self._store = None
        self._secret = ''
        self._key = b''
        self._down_until = float('-inf')
        self._next_sweep = float('-inf')
        self._health: tuple = (float('-inf'), None)
        self._lock = threading.Lock()

    def _ready(self):
        if not self._resolved:
            with self._lock:
                if not self._resolved:
                    self._secret = self._secret_factory()
                    self._key = hashlib.sha256(b'148ai-rate-limits\0' + self._secret.encode('utf-8')).digest()
                    self._store = self._store_factory()
                    self._resolved = True
                    if self._store is None:
                        _log.warning('rate limits: no shared store (OMNI_CREATOR_PERSISTENCE=memory, development only): '
                                     'off Vercel the limits are not enforced in this process; on Vercel the sign-in '
                                     'routes answer 503')
        return self._store

    @property
    def store_kind(self) -> str:
        store = self._ready()
        return getattr(store, 'kind', 'none')

    def health(self) -> dict:
        """For GET /api/v28/deployment: the store, and whether its table exists -- a missing one names migration 047.
        Read-only (one to_regclass), asked at most once per HEALTH_CACHE_SECONDS per instance (a missing table is logged
        once per interval, not on every call); a database that cannot answer is reported as such, never as healthy."""
        now = time.monotonic()
        asked, cached = self._health
        if cached is not None and now - asked < HEALTH_CACHE_SECONDS:
            return dict(cached)
        result = self._health_now()
        self._health = (now, result)
        return dict(result)

    def _health_now(self) -> dict:
        try:
            store = self._ready()
        except Exception as exc:
            return {'store': 'unknown', 'status': 'UNAVAILABLE', 'error': type(exc).__name__}
        if store is None:
            return {'store': 'none', 'status': 'NOT_ENFORCED' if os.environ.get('VERCEL') != '1' else 'UNAVAILABLE',
                    'reason': 'memory mode: no counter store every instance shares'}
        if not hasattr(store, 'table_present'):
            return {'store': store.kind, 'status': 'OK'}
        try:
            present = store.table_present()
        except Exception as exc:
            return {'store': store.kind, 'status': 'UNAVAILABLE', 'error': type(exc).__name__}
        if not present:
            _log.error('rate limits: %s', MISSING_TABLE)
            return {'store': store.kind, 'status': 'MIGRATION_MISSING', 'migration': MIGRATION, 'detail': MISSING_TABLE}
        return {'store': store.kind, 'status': 'OK', 'migration': MIGRATION}

    def _digest(self, limit: Limit, subject: str) -> str:
        return hmac.new(self._key, f'{limit.name}\0{subject}'.encode('utf-8'), hashlib.sha256).hexdigest()

    def subjects(self, limits, *, headers: Mapping[str, str], cookies: Mapping[str, str], peer: str | None,
                 body: bytes = b'', identifier: str | None = None, environ: Mapping[str, str] | None = None) -> list:
        """(limit, subject) for every limit whose subject this request has. A subject is typed ('ip:', 'e:', 'ei:',
        'a:'), so two kinds never share a counter. `identifier` overrides the body's e-mail (enforce())."""
        self._ready()
        resolved: dict = {}

        def address():
            if 'ip' not in resolved:
                resolved['ip'] = client_address(headers, peer, environ)
            return resolved['ip']

        def email():
            if 'e' not in resolved:
                resolved['e'] = identifier if identifier is not None else identifier_of(body)
            return resolved['e']

        hits = []
        for limit in limits:
            if limit.subject == 'identifier':
                if email():
                    hits.append((limit, 'e:' + email()))
                continue
            if limit.subject == 'identifier_ip':
                if email() and address():
                    hits.append((limit, 'ei:' + email() + '\0' + address()))
                continue
            if limit.subject == 'account':
                account = account_of(headers, cookies, self._secret)
                if account:
                    hits.append((limit, 'a:' + account))
                    continue
            if address():
                hits.append((limit, 'ip:' + address()))
        return hits

    def check(self, hits: list, environ: Mapping[str, str] | None = None) -> Verdict:
        """Counts one request. The address counters first; when one refuses, nothing else is written (a flood from one
        address adds no row per e-mail it tries). Raises StoreUnavailable when the store cannot answer or failed less than
        STORE_RETRY_SECONDS ago."""
        environ = os.environ if environ is None else environ
        store = self._ready()
        if not hits:
            return Verdict(True)
        if store is None:
            if environ.get('VERCEL') == '1':
                raise StoreUnavailable('no counter store that every instance shares (memory mode on Vercel)')
            return Verdict(True, enforced=False)
        now = float(self.clock())
        if now < self._down_until:
            raise StoreUnavailable(f'the counter store failed less than {STORE_RETRY_SECONDS} s ago; not asked again yet')
        first = [h for h in hits if h[1].startswith('ip:')]
        rest = [h for h in hits if not h[1].startswith('ip:')]
        verdict = Verdict(True)
        for phase in (first, rest):
            if phase:
                verdict = self._count(store, phase, now)
                if not verdict.allowed:
                    break
        self._maybe_sweep(store, now)
        return verdict

    def _count(self, store, hits: list, now: float) -> Verdict:
        counters: dict = {}
        for limit, subject in hits:
            start = int(now // limit.window_seconds) * limit.window_seconds
            counters[(limit.name, self._digest(limit, subject))] = (limit, start)
        rows = sorted((name, key, start, start + 2 * limit.window_seconds, start - limit.window_seconds,
                       COUNT_CAP * limit.limit) for (name, key), (limit, start) in counters.items())
        try:
            counts = store.hit(rows)
            seen = [counts[c] for c in counters]
        except Exception as exc:
            self._down_until = now + STORE_RETRY_SECONDS
            raise StoreUnavailable(f'{type(exc).__name__}: {str(exc)[:200]}') from exc
        refused = []
        for ((name, key), (limit, start)), (current, previous) in zip(counters.items(), seen):
            wait = refusal_seconds(limit, now - start, current, previous)
            if wait:
                refused.append((wait, name, limit, key))
        if not refused:
            return Verdict(True)
        wait, _, limit, key = max(refused, key=lambda r: (r[0], r[1]))
        return Verdict(False, retry_after=wait, limit=limit, subject_digest=key[:12])

    def _maybe_sweep(self, store, now: float) -> None:
        if now < self._next_sweep:
            return
        self._next_sweep = now + SWEEP_INTERVAL_SECONDS
        try:
            removed = store.sweep(now, batch=SWEEP_BATCH, max_batches=SWEEP_MAX_BATCHES)
        except Exception as exc:                # the counts above are already decided; the next sweep runs in a minute
            _log.warning('rate limits: deleting expired counters failed (%s: %s)', type(exc).__name__, str(exc)[:200])
            return
        if removed:
            _log.info('rate limits: %d expired counters deleted', removed)

    def enforce(self, request, *limits: Limit, identifier: str | None = None) -> None:
        """For a route that presents a refusal its own way (social sign-in redirects to its card). Counts `request`
        against `limits` exactly as the middleware would; raises RateLimited when one is exceeded and StoreUnavailable
        when the store cannot answer -- a sign-in route then refuses, as the middleware does."""
        client = getattr(request, 'client', None)
        hits = self.subjects(limits, headers=request.headers, cookies=request.cookies,
                             peer=client.host if client else None, identifier=identifier)
        verdict = self.check(hits)
        if not verdict.allowed:
            raise RateLimited(verdict)


# ---- what the customer reads ------------------------------------------------------------------------------------------
LANGS = ('he', 'ar', 'en')
TEXT = {
    'he': {'rate_limited': 'יותר מדי בקשות בזמן קצר, אז עצרנו לרגע כדי לשמור על החשבון. אפשר לנסות שוב {wait}.',
           'unavailable': 'כרגע אי אפשר לוודא שהפעולה הזו בטוחה, אז עצרנו אותה לרגע. זה אצלנו, לא אצלכם. '
                          'אפשר לנסות שוב בעוד דקה.'},
    'ar': {'rate_limited': 'طلبات كثيرة جدًا في وقت قصير، لذلك توقفنا للحظة لحماية الحساب. يمكنكم المحاولة مرة أخرى {wait}.',
           'unavailable': 'لا يمكننا الآن التأكد من أن هذه العملية آمنة، لذلك أوقفناها للحظة. هذا من جهتنا وليس من جهتكم. '
                          'يمكنكم المحاولة مرة أخرى بعد دقيقة.'},
    'en': {'rate_limited': 'Too many requests in a short time, so we paused for a moment to keep the account safe. '
                           'You can try again {wait}.',
           'unavailable': 'We cannot make sure this is safe right now, so we paused it for a moment. This is on our side, '
                          'not yours. You can try again in a minute.'},
}
UNAVAILABLE_RETRY_SECONDS = 60      # the 503's Retry-After, as its sentence says ("in a minute")


def wait_words(lang: str, seconds: int) -> str:
    minutes = max(1, math.ceil(seconds / 60))
    if lang == 'he':
        return 'בעוד דקה' if minutes == 1 else 'בעוד שתי דקות' if minutes == 2 else f'בעוד {minutes} דקות'
    if lang == 'ar':
        return ('بعد دقيقة' if minutes == 1 else 'بعد دقيقتين' if minutes == 2 else
                f'بعد {minutes} دقائق' if minutes <= 10 else f'بعد {minutes} دقيقة')
    return 'in a minute' if minutes == 1 else f'in {minutes} minutes'


def refusal_messages(retry_after: int) -> dict:
    return {lang: TEXT[lang]['rate_limited'].format(wait=wait_words(lang, retry_after)) for lang in LANGS}


def unavailable_messages() -> dict:
    return {lang: TEXT[lang]['unavailable'] for lang in LANGS}


def language_of(query_lang: str | None, accept_language: str | None) -> str:
    """The language of `message`: ?lang= read as investor_app._lang reads it, else the first of Hebrew, Arabic or English
    in Accept-Language, else Hebrew (investor_app._lang's default). `messages` always carries all three."""
    lang = (query_lang or '').strip().lower()
    if lang:
        return 'en' if lang.startswith('en') else 'ar' if lang.startswith('ar') else 'he'
    for part in (accept_language or '').split(','):
        tag = part.split(';')[0].strip().lower()
        for code in LANGS:
            if tag == code or tag.startswith(code + '-'):
                return code
    return 'he'


def refusal_body(verdict: Verdict, lang: str) -> dict:
    messages = refusal_messages(verdict.retry_after)
    return {'detail': {'error': 'rate_limited', 'limit': verdict.limit.name if verdict.limit else None,
                       'retry_after_seconds': verdict.retry_after, 'message': messages[lang], 'messages': messages}}


def unavailable_body(lang: str) -> dict:
    messages = unavailable_messages()
    return {'detail': {'error': 'rate_limit_unavailable', 'retry_after_seconds': UNAVAILABLE_RETRY_SECONDS,
                       'message': messages[lang], 'messages': messages}}


# ---- the middleware ---------------------------------------------------------------------------------------------------
async def _buffered(receive):
    """The whole request body, and a receive() that gives it to the app again (a pure ASGI middleware reads it once)."""
    chunks, disconnect = [], None
    while True:
        message = await receive()
        if message['type'] == 'http.disconnect':
            disconnect = message
            break
        chunks.append(message.get('body', b''))
        if not message.get('more_body', False):
            break
    body = b''.join(chunks)
    replayed = False

    async def replay():
        nonlocal replayed
        if replayed:
            return await receive()
        replayed = True
        return disconnect if disconnect is not None else {'type': 'http.request', 'body': body, 'more_body': False}
    return body, replay


class RateLimitMiddleware:
    """A pure ASGI middleware: a request that matches no route in ROUTES passes untouched; one that does is counted
    before its handler runs, refused with 429 over a limit, and with 503 when the store cannot answer. On a route with a
    failure counter (sign-in) the answer is held until it is known: a failure is counted, and a failure over that
    counter's limit becomes a 429 -- a success is never turned away by it."""

    def __init__(self, app, limiter: RateLimiter) -> None:
        self.app, self.limiter = app, limiter

    async def __call__(self, scope, receive, send):
        if scope.get('type') != 'http':
            return await self.app(scope, receive, send)
        from starlette._utils import get_route_path
        method, path = scope.get('method', ''), get_route_path(scope)
        route = route_for(method, path)
        if route is None:
            return await self.app(scope, receive, send)
        from starlette.concurrency import run_in_threadpool
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        request = Request(scope)
        body = b''
        if route.failures or any(limit.subject in ('identifier', 'identifier_ip') for limit in route.limits):
            body, receive = await _buffered(receive)
        client = scope.get('client')
        peer = client[0] if client else None
        lang = language_of(request.query_params.get('lang'), request.headers.get('accept-language'))
        names = ', '.join(limit.name for limit in route.limits)

        def refusal(verdict):
            _log.warning('rate limits: %s %s refused, %s exceeded (subject %s), retry after %d s',
                         method, path, verdict.limit.name, verdict.subject_digest, verdict.retry_after)
            return JSONResponse(refusal_body(verdict, lang), status_code=429,
                                headers={'Retry-After': str(verdict.retry_after), 'Cache-Control': 'no-store'})
        try:
            verdict = await run_in_threadpool(self._decide, route.limits, request, peer, body)
        except StoreUnavailable as exc:
            _log.error('rate limits: the counter store is unavailable (%s); %s %s refused with 503 (fail closed: %s)%s',
                       exc, method, path, names, _missing_table_hint(exc))
            response = JSONResponse(unavailable_body(lang), status_code=503,
                                    headers={'Retry-After': str(UNAVAILABLE_RETRY_SECONDS), 'Cache-Control': 'no-store'})
            return await response(scope, receive, send)
        if not verdict.allowed:
            return await refusal(verdict)(scope, receive, send)
        if route.failures is None:
            return await self.app(scope, receive, send)
        held: list = []

        async def hold(message):
            held.append(message)
        await self.app(scope, receive, hold)
        status = next((m['status'] for m in held if m['type'] == 'http.response.start'), None)
        if status in route.failure_statuses:
            try:
                over = await run_in_threadpool(self._count_failure, route.failures, request, peer, body)
            except StoreUnavailable as exc:   # the handler already refused this attempt; its own answer stands
                _log.error('rate limits: the counter store is unavailable (%s); the failure of %s %s was not counted%s',
                           exc, method, path, _missing_table_hint(exc))
                over = Verdict(True)
            if not over.allowed:
                return await refusal(over)(scope, receive, send)
        for message in held:
            await send(message)

    def _decide(self, limits, request, peer, body) -> Verdict:
        hits = self.limiter.subjects(limits, headers=request.headers, cookies=request.cookies, peer=peer, body=body)
        return self.limiter.check(hits)

    def _count_failure(self, limit, request, peer, body) -> Verdict:
        hits = self.limiter.subjects((limit,), headers=request.headers, cookies=request.cookies, peer=peer, body=body)
        return self.limiter.check(hits)


def install(app, *, store_factory: Callable, secret_factory: Callable[[], str],
            clock: Callable[[], float] = time.time) -> RateLimiter:
    """Adds the middleware to `app` and returns its limiter. Starlette puts the last middleware added outermost, so the
    app adds this one first: a 429 or 503 then still passes through the request id, CORS and the security headers."""
    limiter = RateLimiter(store_factory=store_factory, secret_factory=secret_factory, clock=clock)
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
    return limiter


def answers_no_sooner_than(seconds: float):
    """Every call of the wrapped (synchronous) route takes at least `seconds`, answered or raised. Used where the work
    differs by whether an account exists (a password-reset request writes a token row only for a known e-mail): the time
    of the answer must not say which. The route becomes asynchronous: its work runs in the thread pool and the wait is an
    `await asyncio.sleep`, so the floor holds no pool thread (review N1)."""
    def wrap(fn):
        @functools.wraps(fn)
        async def inner(*args, **kwargs):
            from starlette.concurrency import run_in_threadpool
            started = time.monotonic()
            try:
                return await run_in_threadpool(fn, *args, **kwargs)
            finally:
                left = seconds - (time.monotonic() - started)
                if left > 0:
                    await asyncio.sleep(left)
        return inner
    return wrap
