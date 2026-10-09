"""Private preview access (autonomous completion directive §4).

Tokens are random (secrets.token_urlsafe), stored only as SHA-256 and checked
by the preview router against the database, so the API (Vercel) and the
router (worker host) need no shared signing key. Modes:

  PRIVATE  default. Only owner tokens, issued by the API to the authenticated
           owner of the project, valid OWNER_TTL.
  SHARED   owner tokens + share tokens the owner created (valid SHARE_TTL);
           switching back to PRIVATE revokes every share token.
  PUBLIC   anyone with the address.

The router accepts a token as `?__148ai_access=` (sets an HttpOnly cookie and
redirects to the clean URL), as the `omni_prv` cookie, or as the
`X-148ai-Preview-Access` header (API clients, checks). The token never
reaches the generated app (cookie and header are stripped before proxying).
"""
from __future__ import annotations

import hashlib
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

OWNER_TTL = timedelta(hours=8)
SHARE_TTL = timedelta(days=7)
MODES = ('PRIVATE', 'SHARED', 'PUBLIC')
QUERY_PARAM = '__148ai_access'
COOKIE = 'omni_prv'
HEADER = 'X-148ai-Preview-Access'


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _audit(cur, preview_id: str, event: str, detail: str = '') -> None:
    cur.execute('INSERT INTO preview_access_audit(preview_id, event, detail) VALUES (%s, %s, %s)',
                (preview_id, event, detail[:300]))


class PreviewAccess:
    def __init__(self, pool, *, clock=time.monotonic):
        self.pool = pool
        self._clock = clock
        self._cache: dict[tuple, tuple[float, object]] = {}
        self._lock = threading.Lock()
        self._denied: dict[str, int] = {}

    # ------------------------------------------------------------- API side
    def issue(self, preview_id: str, *, kind: str = 'owner', issued_to: str = '') -> tuple[str, str]:
        if kind not in ('owner', 'share'):
            raise ValueError('kind must be owner or share')
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + (OWNER_TTL if kind == 'owner' else SHARE_TTL)
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute('INSERT INTO preview_access_tokens(token_hash, preview_id, kind, issued_to, expires_at) '
                                'VALUES (%s, %s, %s, %s, %s)', (_hash(token), preview_id, kind, issued_to, expires))
                    _audit(cur, preview_id, 'issued', kind)
        return token, expires.isoformat()

    def set_mode(self, preview_id: str, mode: str) -> str:
        if mode not in MODES:
            raise ValueError('mode must be PRIVATE, SHARED or PUBLIC')
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute('UPDATE project_previews SET access_mode = %s WHERE id = %s', (mode, preview_id))
                    if mode == 'PRIVATE':
                        cur.execute("UPDATE preview_access_tokens SET revoked_at = now() WHERE preview_id = %s "
                                    "AND kind = 'share' AND revoked_at IS NULL", (preview_id,))
                        if cur.rowcount:
                            _audit(cur, preview_id, 'revoked', f'{cur.rowcount} share token(s)')
                    _audit(cur, preview_id, 'mode', mode)
        return mode

    def revoke_all(self, preview_id: str) -> int:
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute('UPDATE preview_access_tokens SET revoked_at = now() WHERE preview_id = %s '
                                'AND revoked_at IS NULL', (preview_id,))
                    n = cur.rowcount
                    _audit(cur, preview_id, 'revoked', f'{n} token(s)')
        return n

    # ---------------------------------------------------------- router side
    def _cached(self, key, ttl, compute):
        now = self._clock()
        with self._lock:
            hit = self._cache.get(key)
            if hit and now - hit[0] < ttl:
                return hit[1]
        value = compute()
        with self._lock:
            self._cache[key] = (now, value)
        return value

    def mode(self, preview_id: str) -> str:
        def load():
            with self.pool.connection() as conn:
                row = conn.execute('SELECT access_mode FROM project_previews WHERE id = %s', (preview_id,)).fetchone()
            return (row[0] if row and row[0] in MODES else 'PRIVATE')
        return self._cached(('mode', preview_id), 5.0, load)

    def allows(self, preview_id: str, token: str | None) -> bool:
        """True when this request may reach the preview."""
        mode = self.mode(preview_id)
        if mode == 'PUBLIC':
            return True
        if not token:
            return False
        h = _hash(token)

        def load():
            with self.pool.connection() as conn:
                with conn.transaction():
                    row = conn.execute(
                        'UPDATE preview_access_tokens SET last_used_at = now(), uses = uses + 1 '
                        'WHERE token_hash = %s AND preview_id = %s AND revoked_at IS NULL AND expires_at > now() '
                        'RETURNING kind', (h, preview_id)).fetchone()
            return row[0] if row else None
        kind = self._cached(('tok', preview_id, h), 30.0, load)
        if kind == 'owner':
            return True
        return kind == 'share' and mode == 'SHARED'

    def record_denied(self, preview_id: str) -> None:
        """Aggregated per preview and minute (scanners must not flood the audit)."""
        minute = int(time.time() // 60)
        key = f'{preview_id}:{minute}'
        with self._lock:
            first = key not in self._denied
            self._denied[key] = self._denied.get(key, 0) + 1
            if len(self._denied) > 5000:
                self._denied.clear()
        if first:
            try:
                with self.pool.connection() as conn:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            _audit(cur, preview_id, 'denied', 'request without a valid token')
            except Exception:
                pass
