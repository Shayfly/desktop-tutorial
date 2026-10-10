"""Durable provider health and circuit breakers (Wave A §11).

Before Wave A a route that answered "no credits" was skipped only for the rest
of that build (`RoutedModelGateway.unavailable`); every new build paid the
latency of asking again (OpenAI 18 + 10 and Anthropic 10 refused calls in
the ledger). Now the classified answer is stored (Postgres, migration 036)
and every gateway reads it before routing:

  CREDIT_EXHAUSTED / AUTH_INVALID   circuit OPEN until an explicit reset
                                    (`python -m omni_prod.intelligence.health reset <route>`)
                                    or a half-open trial after RECHECK (one call; a refusal
                                    is free: providers do not bill refused requests)
  RATE_LIMITED                      open until Retry-After (bounded) or RATE_COOLDOWN
  UNAVAILABLE (model not found)     open until reset
  DEGRADED (5xx/timeouts)           not blocking; bounded retries stay in the gateway
  HEALTHY                           any successful call closes the circuit

Never stores request bodies, keys or customer content: route name, state,
a short provider message (already redacted by the gateway), timestamps.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from . import states as S

RECHECK = timedelta(hours=24)
RATE_COOLDOWN = timedelta(minutes=15)
MAX_RATE_COOLDOWN = timedelta(hours=6)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def classify(exc) -> str | None:
    """Provider answer -> health state, or None when it says nothing about the route."""
    status = getattr(exc, 'status', None)
    text = str(exc).lower()
    if status in (401,) or 'invalid api key' in text or 'api key not valid' in text or 'incorrect api key' in text:
        return S.AUTH_INVALID
    # "no credits" (OpenAI 429), "credit balance is too low" (Anthropic 400),
    # 402 Payment Required. A plain "exceeded your current quota" is a quota
    # window (Gemini free tier daily quota, bld_ccd38bd0), not missing credit.
    if status == 402 or 'credit balance' in text or 'no credits' in text or 'insufficient_quota' in text \
            or 'insufficient balance' in text:
        return S.CREDIT_EXHAUSTED
    if status == 403:
        return S.AUTH_INVALID
    if status == 404 and ('model' in text and ('not found' in text or 'does not exist' in text)):
        return S.UNAVAILABLE
    if status == 429 and any(k in text for k in ('quota', 'resource_exhausted', 'rate limit', 'too many')):
        return S.RATE_LIMITED
    if status == 429:
        return S.RATE_LIMITED
    if status is not None and 500 <= status < 600:
        return S.DEGRADED
    if isinstance(exc, TimeoutError) or 'timed out' in text:
        return S.DEGRADED
    return None


@dataclass(frozen=True)
class RouteHealth:
    route: str
    state: str = S.HEALTHY
    detail: str = ''
    since: datetime | None = None
    open_until: datetime | None = None      # None with a blocking state = until reset/recheck
    recheck_at: datetime | None = None      # half-open trial allowed from here
    failures: int = 0
    reset_by: str = ''

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        for k in ('since', 'open_until', 'recheck_at'):
            d[k] = d[k].isoformat() if d[k] else None
        return d


class MemoryHealthStore:
    def __init__(self):
        self._rows: dict[str, RouteHealth] = {}
        self._lock = threading.Lock()

    def get(self, route: str) -> RouteHealth | None:
        with self._lock:
            return self._rows.get(route)

    def put(self, row: RouteHealth) -> None:
        with self._lock:
            self._rows[row.route] = row

    def all(self) -> list[RouteHealth]:
        with self._lock:
            return list(self._rows.values())


class PostgresHealthStore:
    """provider_health (migration 036). Writes are last-writer-wins per route;
    every write is a full classified observation, so ordering is harmless."""

    COLS = ('route', 'state', 'detail', 'since', 'open_until', 'recheck_at', 'failures', 'reset_by')

    def __init__(self, pool):
        self.pool = pool

    def get(self, route: str) -> RouteHealth | None:
        with self.pool.connection() as conn:
            row = conn.execute(f'SELECT {", ".join(self.COLS)} FROM provider_health WHERE route = %s', (route,)).fetchone()
        return RouteHealth(*row) if row else None

    def put(self, row: RouteHealth) -> None:
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute(
                    'INSERT INTO provider_health(route, state, detail, since, open_until, recheck_at, failures, reset_by, updated_at) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now()) ON CONFLICT (route) DO UPDATE SET state = EXCLUDED.state, '
                    'detail = EXCLUDED.detail, since = EXCLUDED.since, open_until = EXCLUDED.open_until, '
                    'recheck_at = EXCLUDED.recheck_at, failures = EXCLUDED.failures, reset_by = EXCLUDED.reset_by, '
                    'updated_at = now()',
                    (row.route, row.state, row.detail[:300], row.since, row.open_until, row.recheck_at, row.failures,
                     row.reset_by))

    def all(self) -> list[RouteHealth]:
        with self.pool.connection() as conn:
            rows = conn.execute(f'SELECT {", ".join(self.COLS)} FROM provider_health ORDER BY route').fetchall()
        return [RouteHealth(*r) for r in rows]


class HealthBook:
    """Reads/writes route health; decides whether a route may take a call now."""

    def __init__(self, store=None, *, clock=_now):
        self.store = store or MemoryHealthStore()
        self.clock = clock
        self.trials: set[str] = set()   # half-open trial granted in this process

    def _safe_get(self, route: str) -> RouteHealth | None:
        try:
            return self.store.get(route)
        except Exception:
            return None   # health is advisory for availability, never a reason to fail a build

    def state(self, route: str) -> RouteHealth:
        return self._safe_get(route) or RouteHealth(route, S.UNKNOWN)

    def admit(self, route: str) -> tuple[bool, str]:
        """(may call, reason). Grants at most one half-open trial per process per window."""
        h = self._safe_get(route)
        if h is None or h.state not in S.BLOCKING_HEALTH:
            return True, ''
        now = self.clock()
        if h.state == S.RETIRED:
            return False, f'{h.state}: {h.detail}'
        if h.state == S.RATE_LIMITED:
            if h.open_until and now >= h.open_until:
                return True, 'rate-limit window over'
            return False, f'RATE_LIMITED until {h.open_until.isoformat() if h.open_until else "?"}: {h.detail}'
        # CREDIT_EXHAUSTED / AUTH_INVALID / UNAVAILABLE: reset or one trial after recheck_at
        if h.recheck_at and now >= h.recheck_at and route not in self.trials:
            self.trials.add(route)
            return True, f'half-open trial after {h.state} since {h.since.isoformat() if h.since else "?"}'
        return False, f'{h.state} since {h.since.isoformat() if h.since else "?"}: {h.detail}'

    @staticmethod
    def classify(exc) -> str | None:
        return classify(exc)

    def record_failure(self, route: str, exc) -> str | None:
        state = classify(exc)
        if state is None or state == S.DEGRADED:
            return state   # transient: the gateway's bounded retries handle it; no durable block
        now = self.clock()
        prev = self._safe_get(route)
        failures = (prev.failures if prev and prev.state == state else 0) + 1
        open_until = recheck = None
        if state == S.RATE_LIMITED:
            hint = getattr(exc, 'retry_after_seconds', None)
            wait = timedelta(seconds=float(hint)) if hint else RATE_COOLDOWN * min(failures, 8)
            open_until = now + min(wait, MAX_RATE_COOLDOWN)
        else:
            recheck = now + RECHECK
        row = RouteHealth(route, state, str(exc)[:300], (prev.since if prev and prev.state == state and prev.since else now),
                          open_until, recheck, failures, '')
        try:
            self.store.put(row)
        except Exception:
            pass
        return state

    def record_success(self, route: str) -> None:
        prev = self._safe_get(route)
        if prev is not None and prev.state == S.HEALTHY:
            return
        try:
            self.store.put(RouteHealth(route, S.HEALTHY, '', self.clock(), None, None, 0, prev.reset_by if prev else ''))
        except Exception:
            pass
        self.trials.discard(route)

    def reset(self, route: str, *, by: str) -> RouteHealth:
        if not by.strip():
            raise ValueError('a reset names who reset it')
        row = RouteHealth(route, S.UNKNOWN, 'reset', self.clock(), None, None, 0, by.strip()[:80])
        self.store.put(row)
        return row

    def retire(self, route: str, detail: str) -> None:
        self.store.put(RouteHealth(route, S.RETIRED, detail[:300], self.clock()))


def main(argv=None) -> int:
    import argparse
    import json
    import os
    ap = argparse.ArgumentParser(prog='omni_prod.intelligence.health')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('show')
    r = sub.add_parser('reset')
    r.add_argument('route')
    r.add_argument('--by', required=True)
    args = ap.parse_args(argv)
    from ..db import DatabasePool
    pool = DatabasePool(os.environ['OMNI_DATABASE_URL'])
    book = HealthBook(PostgresHealthStore(pool))
    if args.cmd == 'show':
        print(json.dumps([h.to_dict() for h in book.store.all()], indent=1))
    else:
        print(json.dumps(book.reset(args.route, by=args.by).to_dict()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
