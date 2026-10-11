"""Durable, concurrency-safe budget reservations for paid intake model calls
(Issue #12; migration 037). Accounting lives here; RoutedModelGateway stays the
execution and metering boundary.

Lifecycle:  QUOTE -> RESERVE -> CLAIM -> EXECUTE -> METER/SETTLE -> RECONCILE

  quote()          pure: worst-case cost of the whole permitted envelope
                   (1 provider call, no automatic retry or fallback, every
                   allowed model, input bound = prompt bytes + 64, output bound
                   = max_tokens, which includes reasoning tokens) from the
                   source-backed price table. No price / no model -> QuoteUnavailable.
  reserve()        one transaction: lock scope anchors in ascending order,
                   sum settled + outstanding per scope, check every cap, insert
                   reservation + scopes + outbox row + event. Idempotent per key.
  claim()          RESERVED -> CLAIMED (lease) -- single conditional UPDATE.
  mark_executing() CLAIMED -> EXECUTING, committed BEFORE the provider call.
  settle()         EXECUTING -> SETTLED (CONFIRMED / CONFIRMED_ZERO / ESTIMATED)
                   or UNKNOWN (actual NULL, full quote stays held).
  release()        RESERVED/CLAIMED -> RELEASED (provider certainly not contacted).
  reconcile()      expired EXECUTING -> UNKNOWN (never released, never replayed);
                   expired CLAIMED / stale RESERVED -> RELEASED.
  resolve_unknown() UNKNOWN -> SETTLED only with an amount and billing evidence.

Lock order (every transaction that changes an amount counted against a
scope): scope anchor rows in ascending `scope` text order, then the
reservation row. claim/mark_executing/expire-to-UNKNOWN lock only the single
reservation row and never request a scope lock afterwards, so no cycle exists.
No aggregate is read FOR UPDATE; no lock is held during the provider call.
"""
from __future__ import annotations

import json
import os
import secrets
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from pathlib import Path

PRODUCTION, CAMPAIGN = 'production', 'campaign'
RESERVED, CLAIMED, EXECUTING, SETTLED, UNKNOWN, RELEASED = (
    'RESERVED', 'CLAIMED', 'EXECUTING', 'SETTLED', 'UNKNOWN', 'RELEASED')
CONFIRMED, CONFIRMED_ZERO, ESTIMATED, COST_UNKNOWN = 'CONFIRMED', 'CONFIRMED_ZERO', 'ESTIMATED', 'UNKNOWN'
OPEN_STATES = (RESERVED, CLAIMED, EXECUTING, UNKNOWN)
DAILY_SCOPE = 'daily:global'
Q = Decimal('0.00000001')                      # NUMERIC(18, 8)
DEFAULT_ALLOWED_MODELS = ('gemini-3.1-flash-lite', 'gemini-3.5-flash-lite')
DEFAULT_CAMPAIGN_CAP = Decimal('10')            # Issue #12: acceptance-test campaign hard ceiling
CEILING_BASIS = ('output bound = max_tokens; reasoning/thinking tokens are billed as output and count against '
                 'max_tokens for the allowed OpenAI-compatible routes (catalog _thinking_basis notes); '
                 'metered output above the bound is flagged as an overrun at settlement')


class BudgetError(RuntimeError):
    pass


class QuoteUnavailable(BudgetError):
    """No reliable price or execution ceiling: fail closed (no model call)."""


class BudgetExceeded(BudgetError):
    def __init__(self, scope: str, cap: Decimal, counted: Decimal, quote: Decimal):
        super().__init__(f'{scope}: {counted} + {quote} > {cap}')
        self.scope, self.cap, self.counted, self.quote = scope, cap, counted, quote


class IdempotencyConflict(BudgetError):
    pass


class StaleClaim(BudgetError):
    pass


# ----------------------------------------------------------------- quoting --

@dataclass(frozen=True)
class Quote:
    amount_usd: Decimal
    envelope: dict

    def to_dict(self) -> dict:
        return {'amount_usd': str(self.amount_usd), **self.envelope}


def _catalog_items() -> list[dict]:
    raw = os.getenv('OMNI_MODEL_CATALOG_JSON', '').strip()
    if not raw:
        path = Path(__file__).resolve().parents[2] / 'infra' / 'worker-host' / 'model-catalog.json'
        try:
            raw = path.read_text(encoding='utf-8')
        except OSError as exc:
            raise QuoteUnavailable('model catalog unavailable on this host') from exc
    try:
        items = json.loads(raw)
    except ValueError as exc:
        raise QuoteUnavailable('model catalog is not valid JSON') from exc
    if not isinstance(items, list):
        raise QuoteUnavailable('model catalog must be a list')
    return [i for i in items if isinstance(i, dict)]


def allowed_models() -> tuple[str, ...]:
    raw = os.getenv('OMNI_INTAKE_ALLOWED_MODELS', '').strip()
    return tuple(m.strip() for m in raw.split(',') if m.strip()) if raw else DEFAULT_ALLOWED_MODELS


def quote(*, system: str, user: str, max_tokens: int, task: str = 'conversation',
          models: tuple[str, ...] | None = None, when=None, max_calls: int = 1) -> Quote:
    """Worst case of the permitted envelope, using the gateway's own bounds."""
    from ..intelligence.governance import govern
    from ..intelligence.task_policy import eligible
    if not isinstance(max_tokens, int) or max_tokens <= 0 or max_calls != 1:
        raise QuoteUnavailable('only a single bounded call is quotable (no automatic retry or fallback)')
    models = models or allowed_models()
    input_tokens = len(f'{system}{user}'.encode('utf-8')) + 64       # == RoutedModelGateway.ranked_routes
    priced = []
    for item in _catalog_items():
        model = str(item.get('model', ''))
        if model not in models or not item.get('enabled', True):
            continue
        try:
            quality = int(item.get('quality'))
            max_out = int(item.get('max_output_tokens', 8192))
            gov = govern(model=model, base_url=str(item.get('base_url', '')),
                         input_per_million=Decimal(str(item['input_per_million'])),
                         output_per_million=Decimal(str(item['output_per_million'])), when=when)
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
        if not gov.routable or not eligible(task, model_id=model, quality=quality):
            continue
        if gov.input_per_million is None or gov.output_per_million is None or \
                gov.input_per_million <= 0 or gov.output_per_million <= 0:
            raise QuoteUnavailable(f'{model}: no verified non-zero price')
        out_tokens = min(max_tokens, max_out)
        cost = (Decimal(input_tokens) * gov.input_per_million + Decimal(out_tokens) * gov.output_per_million) \
            / Decimal(1_000_000)
        priced.append({'model': model, 'quality': quality, 'input_tokens_bound': input_tokens,
                       'output_tokens_bound': out_tokens, 'input_per_million': str(gov.input_per_million),
                       'output_per_million': str(gov.output_per_million), 'price_source': gov.price_source,
                       'worst_case_usd': str(cost)})
    if not priced:
        raise QuoteUnavailable('no allowed, priced model is eligible for this task')
    amount = max(Decimal(p['worst_case_usd']) for p in priced).quantize(Q, rounding=ROUND_CEILING)
    return Quote(amount, {'task': task, 'max_calls': 1, 'transient_retries': 0, 'fallback_calls': 0,
                          'allowed_models': list(models),
                          'models': priced, 'ceiling_basis': CEILING_BASIS, 'max_tokens': max_tokens})


# --------------------------------------------------------------- reserving --

@dataclass(frozen=True)
class Caps:
    project_usd: Decimal
    daily_usd: Decimal | None = None             # production lane
    campaign_usd: Decimal | None = None          # campaign lane

    def __post_init__(self):
        for v in (self.project_usd, self.daily_usd, self.campaign_usd):
            if v is not None and (not isinstance(v, Decimal) or not v.is_finite() or v < 0):
                raise ValueError('caps must be finite non-negative Decimals')


@dataclass
class Reservation:
    id: str
    idempotency_key: str
    account_id: str
    project_id: str
    lane: str
    campaign_id: str | None
    quoted_usd: Decimal
    state: str
    cost_state: str | None = None
    actual_usd: Decimal | None = None
    failure_reason: str | None = None
    claim_token: str | None = None
    provider: str | None = None
    model: str | None = None
    result: dict | None = None
    quote: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d['quoted_usd'] = str(self.quoted_usd)
        d['actual_usd'] = None if self.actual_usd is None else str(self.actual_usd)
        d.pop('claim_token')
        return d


_COLS = ('id, idempotency_key, account_id, project_id, lane, campaign_id, quoted_usd, state, cost_state, actual_usd, '
         'failure_reason, claim_token, provider, model, result, quote')


def _res(row) -> Reservation:
    (rid, key, acct, proj, lane, camp, quoted, state, cstate, actual, why, token, prov, model, result, q) = row
    return Reservation(rid, key, acct, proj, lane, camp, Decimal(quoted), state, cstate,
                       None if actual is None else Decimal(actual), why, token, prov, model, result, q or {})


def scopes_for(account_id: str, project_id: str, lane: str, campaign_id: str | None, caps: Caps
               ) -> list[tuple[str, str, Decimal]]:
    """(scope, kind, cap) sorted by scope -- the global lock order."""
    for v in (account_id, project_id) + ((campaign_id,) if campaign_id else ()):
        if not isinstance(v, str) or not v or ':' in v or len(v) > 128:
            raise ValueError('ids must be non-empty, <=128 chars and contain no ":"')
    if lane == PRODUCTION:
        if campaign_id is not None or caps.daily_usd is None:
            raise ValueError('production lane needs a daily cap and no campaign')
        out = [(DAILY_SCOPE, 'daily', caps.daily_usd), (f'project:{account_id}:{project_id}', 'project', caps.project_usd)]
    elif lane == CAMPAIGN:
        if not campaign_id or caps.campaign_usd is None:
            raise ValueError('campaign lane needs a campaign id and cap')
        out = [(f'campaign:{campaign_id}', 'campaign', caps.campaign_usd),
               (f'campaign-test:{campaign_id}:{account_id}:{project_id}', 'project', caps.project_usd)]
    else:
        raise ValueError('unknown lane')
    return sorted(out)


_COUNTED = """
SELECT COALESCE(SUM(CASE r.state WHEN 'RELEASED' THEN 0 WHEN 'SETTLED' THEN r.actual_usd ELSE r.quoted_usd END), 0)
FROM intake_reservation_scopes s JOIN intake_reservations r ON r.id = s.reservation_id
WHERE s.scope = %s
  AND (%s = false OR r.state NOT IN ('SETTLED', 'RELEASED')
       OR r.reserved_at >= COALESCE(%s::timestamptz, now()) - interval '24 hours')
"""


class ReservationService:
    def __init__(self, pool, *, clock: datetime | None = None):
        self.pool = pool
        self.clock = clock          # tests: fixed "now" for the rolling window

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _event(cur, rid, frm, to, detail=None):
        cur.execute('INSERT INTO intake_reservation_events (reservation_id, from_state, to_state, detail) '
                    'VALUES (%s, %s, %s, %s::jsonb)', (rid, frm, to, json.dumps(detail or {}, default=str)))

    @staticmethod
    def _lock_scopes(cur, scopes: list[str]):
        for scope in sorted(scopes):                       # deterministic order, one row per statement
            cur.execute('SELECT scope FROM intake_budget_scopes WHERE scope = %s FOR UPDATE', (scope,))
            if cur.fetchone() is None:
                raise BudgetError(f'scope {scope} missing')

    def counted(self, scope: str, cur=None) -> Decimal:
        def run(c):
            c.execute(_COUNTED, (scope, scope == DAILY_SCOPE, self.clock))
            return Decimal(c.fetchone()[0])
        if cur is not None:
            return run(cur)
        with self.pool.connection() as conn, conn.cursor() as c:
            return run(c)

    def get(self, reservation_id: str, *, account_id: str | None = None) -> Reservation | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT {_COLS} FROM intake_reservations WHERE id = %s'
                        + (' AND account_id = %s' if account_id is not None else ''),
                        (reservation_id,) + ((account_id,) if account_id is not None else ()))
            row = cur.fetchone()
        return None if row is None else _res(row)

    # -- RESERVE -----------------------------------------------------------
    def reserve(self, *, idempotency_key: str, account_id: str, project_id: str, quote_: Quote, caps: Caps,
                payload: dict, lane: str = PRODUCTION, campaign_id: str | None = None) -> Reservation:
        if not isinstance(quote_.amount_usd, Decimal) or quote_.amount_usd <= 0:
            raise QuoteUnavailable('reservation needs a positive quote')
        if not idempotency_key or len(idempotency_key) > 300:
            raise ValueError('idempotency key required')
        scopes = scopes_for(account_id, project_id, lane, campaign_id, caps)
        with self.pool.connection() as conn:               # anchors exist before any lock is taken
            with conn.transaction(), conn.cursor() as cur:
                for scope, kind, _ in scopes:
                    cur.execute('INSERT INTO intake_budget_scopes (scope, kind) VALUES (%s, %s) '
                                'ON CONFLICT (scope) DO NOTHING', (scope, kind))
        with self.pool.connection() as conn:
            with conn.transaction(), conn.cursor() as cur:
                self._lock_scopes(cur, [s for s, _, _ in scopes])
                cur.execute(f'SELECT {_COLS} FROM intake_reservations WHERE idempotency_key = %s', (idempotency_key,))
                row = cur.fetchone()
                if row is not None:
                    existing = _res(row)
                    if (existing.account_id, existing.project_id, existing.lane, existing.campaign_id) != \
                            (account_id, project_id, lane, campaign_id):
                        raise IdempotencyConflict('idempotency key already used for another request')
                    return existing                         # duplicate request: the original reservation
                amount = quote_.amount_usd.quantize(Q, rounding=ROUND_CEILING)
                snapshot = {}
                for scope, _, cap in scopes:
                    used = self.counted(scope, cur)
                    snapshot[scope] = {'cap': str(cap), 'counted_before': str(used)}
                    if used + amount > cap:
                        raise BudgetExceeded(scope, cap, used, amount)
                rid = f'irs_{uuid.uuid4().hex[:24]}'
                q = {**quote_.to_dict(), 'caps': snapshot}
                cur.execute(
                    'INSERT INTO intake_reservations (id, idempotency_key, account_id, project_id, lane, campaign_id, '
                    'quoted_usd, quote, state) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)',
                    (rid, idempotency_key, account_id, project_id, lane, campaign_id, amount,
                     json.dumps(q, default=str), RESERVED))
                for scope, _, cap in scopes:
                    cur.execute('INSERT INTO intake_reservation_scopes (reservation_id, scope, cap_usd) '
                                'VALUES (%s, %s, %s)', (rid, scope, cap))
                cur.execute('INSERT INTO intake_outbox (reservation_id, payload) VALUES (%s, %s::jsonb)',
                            (rid, json.dumps(payload, ensure_ascii=False)))
                self._event(cur, rid, None, RESERVED, {'quoted_usd': str(amount), 'lane': lane})
        return Reservation(rid, idempotency_key, account_id, project_id, lane, campaign_id, amount, RESERVED, quote=q)

    # -- CLAIM / EXECUTE -----------------------------------------------------
    def claim(self, reservation_id: str, *, worker_id: str, lease_seconds: int = 90,
              max_age_seconds: int = 120) -> Reservation | None:
        """RESERVED -> CLAIMED. None when another delivery already claimed it,
        it was released, or it is too old to be useful (then it is released:
        the provider was certainly never contacted)."""
        token = secrets.token_hex(16)
        with self.pool.connection() as conn:
            with conn.transaction(), conn.cursor() as cur:
                cur.execute(
                    f"UPDATE intake_reservations SET state = 'CLAIMED', claim_token = %s, claimed_by = %s, "
                    f"claimed_at = now(), lease_expires_at = now() + make_interval(secs => %s), updated_at = now() "
                    f"WHERE id = %s AND state = 'RESERVED' AND reserved_at >= now() - make_interval(secs => %s) "
                    f"RETURNING {_COLS}", (token, worker_id[:120], lease_seconds, reservation_id, max_age_seconds))
                row = cur.fetchone()
                if row is not None:
                    self._event(cur, reservation_id, RESERVED, CLAIMED, {'worker': worker_id[:120]})
        if row is not None:
            return _res(row)
        current = self.get(reservation_id)
        if current is not None and current.state == RESERVED:          # too old: never invoked -> release
            self.release(reservation_id, reason='not claimed within its useful age')
        return None

    def mark_executing(self, reservation: Reservation, *, lease_seconds: int = 90) -> bool:
        """Committed write-ahead marker. After this, a crash means UNKNOWN cost."""
        with self.pool.connection() as conn:
            with conn.transaction(), conn.cursor() as cur:
                cur.execute("UPDATE intake_reservations SET state = 'EXECUTING', executing_at = now(), "
                            "lease_expires_at = now() + make_interval(secs => %s), updated_at = now() "
                            "WHERE id = %s AND state = 'CLAIMED' AND claim_token = %s AND lease_expires_at > now() "
                            "RETURNING id", (lease_seconds, reservation.id, reservation.claim_token))
                ok = cur.fetchone() is not None
                if ok:
                    self._event(cur, reservation.id, CLAIMED, EXECUTING)
        if ok:
            reservation.state = EXECUTING
        return ok

    def payload(self, reservation_id: str) -> dict:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute('SELECT payload FROM intake_outbox WHERE reservation_id = %s', (reservation_id,))
            row = cur.fetchone()
        if row is None:
            raise BudgetError('outbox payload missing')
        return row[0]

    # -- SETTLE ----------------------------------------------------------------
    def settle(self, reservation: Reservation, *, cost_state: str, actual_usd: Decimal | None,
               failure_reason: str | None = None, provider: str | None = None, model: str | None = None,
               provider_request_id: str | None = None, result: dict | None = None,
               metering: dict | None = None) -> Reservation:
        if cost_state == COST_UNKNOWN:
            if actual_usd is not None or not failure_reason:
                raise ValueError('UNKNOWN cost has no amount and needs a failure reason')
            to_state = UNKNOWN
        elif cost_state in (CONFIRMED, CONFIRMED_ZERO, ESTIMATED):
            if actual_usd is None or not isinstance(actual_usd, Decimal) or not actual_usd.is_finite() or actual_usd < 0:
                raise ValueError(f'{cost_state} needs a finite non-negative amount')
            if cost_state == CONFIRMED_ZERO and actual_usd != 0:
                raise ValueError('CONFIRMED_ZERO must be exactly 0')
            to_state = SETTLED
        else:
            raise ValueError('unknown cost state')
        actual = None if actual_usd is None else actual_usd.quantize(Q, rounding=ROUND_CEILING)
        detail = {'cost_state': cost_state, 'actual_usd': None if actual is None else str(actual),
                  'quoted_usd': str(reservation.quoted_usd), **(metering or {})}
        if actual is not None and actual > reservation.quoted_usd:
            detail['overrun_usd'] = str(actual - reservation.quoted_usd)
        with self.pool.connection() as conn:
            with conn.transaction(), conn.cursor() as cur:
                cur.execute('SELECT scope FROM intake_reservation_scopes WHERE reservation_id = %s', (reservation.id,))
                self._lock_scopes(cur, [r[0] for r in cur.fetchall()])
                cur.execute(
                    f'UPDATE intake_reservations SET state = %s, cost_state = %s, actual_usd = %s, failure_reason = %s, '
                    f'provider = %s, model = %s, provider_request_id = %s, result = %s::jsonb, settled_at = now(), '
                    f'updated_at = now() WHERE id = %s AND state = %s AND claim_token = %s RETURNING {_COLS}',
                    (to_state, cost_state, actual, (failure_reason or None) and failure_reason[:500], provider, model,
                     provider_request_id, None if result is None else json.dumps(result, ensure_ascii=False, default=str),
                     reservation.id, EXECUTING, reservation.claim_token))
                row = cur.fetchone()
                if row is not None:
                    self._event(cur, reservation.id, EXECUTING, to_state, detail)
        if row is not None:
            return _res(row)
        current = self.get(reservation.id)
        if current is not None and current.state == to_state and current.cost_state == cost_state and \
                current.actual_usd == actual:
            return current                                     # duplicate settlement of the same outcome
        raise StaleClaim(f'cannot settle {reservation.id}: state {getattr(current, "state", None)}')

    # -- RELEASE / RECONCILE ---------------------------------------------------
    def release(self, reservation_id: str, *, reason: str) -> bool:
        """Only when the provider was certainly not contacted (RESERVED/CLAIMED)."""
        with self.pool.connection() as conn:
            with conn.transaction(), conn.cursor() as cur:
                cur.execute('SELECT scope FROM intake_reservation_scopes WHERE reservation_id = %s', (reservation_id,))
                self._lock_scopes(cur, [r[0] for r in cur.fetchall()])
                cur.execute('SELECT state FROM intake_reservations WHERE id = %s FOR UPDATE', (reservation_id,))
                before = cur.fetchone()
                cur.execute("UPDATE intake_reservations SET state = 'RELEASED', updated_at = now(), "
                            "failure_reason = %s WHERE id = %s AND state IN ('RESERVED', 'CLAIMED') RETURNING id",
                            (reason[:500], reservation_id))
                ok = cur.fetchone() is not None
                if ok:
                    self._event(cur, reservation_id, before[0], RELEASED, {'reason': reason[:500]})
        return ok

    def reconcile(self, *, stale_reserved_seconds: int = 300, limit: int = 500) -> dict:
        """Expired leases and abandoned reservations. Never releases funds of an
        invocation that may have reached the provider."""
        out = {'unknown': [], 'released': []}
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT id, state FROM intake_reservations WHERE "
                        "(state IN ('CLAIMED', 'EXECUTING') AND lease_expires_at < now()) OR "
                        "(state = 'RESERVED' AND reserved_at < now() - make_interval(secs => %s)) "
                        "ORDER BY reserved_at LIMIT %s", (stale_reserved_seconds, limit))
            candidates = cur.fetchall()
        for rid, state in candidates:
            if state == EXECUTING:
                with self.pool.connection() as conn:
                    with conn.transaction(), conn.cursor() as cur:
                        cur.execute("UPDATE intake_reservations SET state = 'UNKNOWN', cost_state = 'UNKNOWN', "
                                    "failure_reason = 'lease expired during execution: provider outcome and billing "
                                    "unknown; quote held until reconciled with billing evidence', updated_at = now() "
                                    "WHERE id = %s AND state = 'EXECUTING' AND lease_expires_at < now() RETURNING id",
                                    (rid,))
                        if cur.fetchone() is not None:
                            self._event(cur, rid, EXECUTING, UNKNOWN, {'reason': 'lease expired'})
                            out['unknown'].append(rid)
            elif self.release(rid, reason='lease expired before the provider was contacted' if state == CLAIMED
                              else 'reservation never claimed'):
                out['released'].append(rid)
        return out

    def resolve_unknown(self, reservation_id: str, *, cost_state: str, actual_usd: Decimal, evidence: str,
                        resolved_by: str) -> Reservation:
        """UNKNOWN -> SETTLED, only with billing evidence (operator / billing export)."""
        if cost_state not in (CONFIRMED, CONFIRMED_ZERO) or not evidence.strip() or not resolved_by.strip():
            raise ValueError('resolution needs CONFIRMED/CONFIRMED_ZERO, evidence and who resolved it')
        if not isinstance(actual_usd, Decimal) or not actual_usd.is_finite() or actual_usd < 0 or \
                (cost_state == CONFIRMED_ZERO and actual_usd != 0):
            raise ValueError('invalid amount')
        with self.pool.connection() as conn:
            with conn.transaction(), conn.cursor() as cur:
                cur.execute('SELECT scope FROM intake_reservation_scopes WHERE reservation_id = %s', (reservation_id,))
                self._lock_scopes(cur, [r[0] for r in cur.fetchall()])
                cur.execute(f"UPDATE intake_reservations SET state = 'SETTLED', cost_state = %s, actual_usd = %s, "
                            f"failure_reason = NULL, settled_at = now(), updated_at = now() "
                            f"WHERE id = %s AND state = 'UNKNOWN' RETURNING {_COLS}",
                            (cost_state, actual_usd.quantize(Q, rounding=ROUND_CEILING), reservation_id))
                row = cur.fetchone()
                if row is None:
                    raise StaleClaim('only an UNKNOWN reservation can be resolved')
                self._event(cur, reservation_id, UNKNOWN, SETTLED,
                            {'cost_state': cost_state, 'actual_usd': str(actual_usd), 'evidence': evidence[:1000],
                             'resolved_by': resolved_by[:120]})
        return _res(row)

    # -- outbox ------------------------------------------------------------------
    def mark_enqueued(self, reservation_id: str) -> None:
        with self.pool.connection() as conn:
            with conn.transaction(), conn.cursor() as cur:
                cur.execute('UPDATE intake_outbox SET enqueued_at = now(), deliveries = deliveries + 1 '
                            'WHERE reservation_id = %s AND enqueued_at IS NULL', (reservation_id,))

    def relay_once(self, enqueue, *, older_than_seconds: int = 5, limit: int = 100) -> list[str]:
        """Deliver outbox rows whose immediate enqueue never happened (crash,
        Redis down). One row per transaction, SKIP LOCKED: concurrent relays
        never double-claim a row; a duplicate Redis job is harmless (claim)."""
        sent: list[str] = []
        for _ in range(max(0, int(limit))):
            with self.pool.connection() as conn:
                with conn.transaction(), conn.cursor() as cur:
                    cur.execute('SELECT o.reservation_id FROM intake_outbox o JOIN intake_reservations r '
                                'ON r.id = o.reservation_id WHERE o.enqueued_at IS NULL AND r.state = %s '
                                'AND o.created_at < now() - make_interval(secs => %s) ORDER BY o.id LIMIT 1 '
                                'FOR UPDATE OF o SKIP LOCKED', (RESERVED, int(older_than_seconds)))
                    row = cur.fetchone()
                    if not row:
                        return sent
                    enqueue(row[0])                     # raises -> rolls back, stays pending
                    cur.execute('UPDATE intake_outbox SET enqueued_at = now(), deliveries = deliveries + 1 '
                                'WHERE reservation_id = %s', (row[0],))
            sent.append(row[0])
        return sent


def caps_from_env(lane: str = PRODUCTION) -> Caps:
    def money(name, default='0'):
        try:
            v = Decimal(os.getenv(name, default) or default)
        except InvalidOperation:
            return Decimal('0')
        return v if v.is_finite() and v > 0 else Decimal('0')
    if lane == CAMPAIGN:
        return Caps(project_usd=money('OMNI_INTAKE_CAMPAIGN_TEST_BUDGET_USD'),
                    campaign_usd=min(money('OMNI_INTAKE_CAMPAIGN_BUDGET_USD', str(DEFAULT_CAMPAIGN_CAP)),
                                     DEFAULT_CAMPAIGN_CAP))
    return Caps(project_usd=money('OMNI_INTAKE_MODEL_BUDGET_USD'), daily_usd=money('OMNI_INTAKE_DAILY_BUDGET_USD'))
