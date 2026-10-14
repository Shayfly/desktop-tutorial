"""Durable ledger of money 148AI itself lost.

A reservation is a *quote*: the customer is charged the quote, the provider is
paid the actual. Three things leave 148AI paying more than it collected:

  metered_overrun          the provider billed above the worst-case quote
                           (output past the ceiling, or a price change)
  budget_capped_shortfall  a real cost above the plan's paid-provider budget,
                           which cannot be pushed onto the customer mid-build
  unreconciled_unknown     an UNKNOWN liability resolved by billing evidence
                           at an amount above what was reserved

Every one of these must be a row, not a log line: `company_loss_events` is the
only durable answer to "how much did we lose, and on what". The ledger is
idempotent per (source, idempotency_key), so a retried settlement never
double-counts, and the amount is always actual - quoted, never an estimate.

Truth rules:
* only a positive overrun is written (a saving is not a loss);
* quoted_usd and actual_usd are both stored, so the loss is auditable;
* cause is a closed set, so the roll-up can be grouped without guessing.
"""
from __future__ import annotations

import json
from decimal import ROUND_CEILING, Decimal

Q = Decimal('0.00000001')

METERED_OVERRUN = 'metered_overrun'
BUDGET_CAPPED_SHORTFALL = 'budget_capped_shortfall'
UNRECONCILED_UNKNOWN = 'unreconciled_unknown'
CAUSES = (METERED_OVERRUN, BUDGET_CAPPED_SHORTFALL, UNRECONCILED_UNKNOWN)

def _q(value) -> Decimal:
    return Decimal(str(value)).quantize(Q, rounding=ROUND_CEILING)

def record_overrun(cur, *, source: str, idempotency_key: str, quoted_usd, actual_usd, cause: str,
                   build_id: str | None = None, reservation_id: str | None = None,
                   account_id: str | None = None, project_id: str | None = None,
                   lane: str | None = None, provider: str | None = None, model: str | None = None,
                   evidence: dict | None = None) -> Decimal | None:
    """Insert one company-loss row. Returns the overrun, or None when there is
    none (actual <= quoted). Idempotent per (source, idempotency_key).

    Takes an already-open cursor/transaction, so the loss commits atomically
    with the settlement that discovered it -- a settlement can never land
    without its loss row, and a retried settlement never writes it twice.
    """
    if cause not in CAUSES:
        raise ValueError(f'unknown company-loss cause {cause!r}')
    if not source or not idempotency_key:
        raise ValueError('source and idempotency_key are required')
    quoted, actual = _q(quoted_usd), _q(actual_usd)
    if quoted < 0 or actual < 0:
        raise ValueError('amounts must be non-negative')
    overrun = actual - quoted
    if overrun <= 0:
        return None
    cur.execute(
        'INSERT INTO company_loss_events (source, idempotency_key, build_id, reservation_id, account_id, '
        'project_id, lane, provider, model, quoted_usd, actual_usd, overrun_usd, cause, evidence) '
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) "
        'ON CONFLICT (source, idempotency_key) DO NOTHING',
        (source, idempotency_key, build_id, reservation_id, account_id, project_id, lane, provider, model,
         quoted, actual, overrun, cause, json.dumps(evidence or {}, default=str, ensure_ascii=False)),
    )
    return overrun

def rollup(cur, *, since: str | None = None) -> dict:
    """Company loss grouped by cause. `since` is a timestamptz text or None."""
    cur.execute(
        'SELECT cause, COUNT(*), COALESCE(SUM(overrun_usd),0) FROM company_loss_events '
        'WHERE (%s::timestamptz IS NULL OR occurred_at >= %s::timestamptz) GROUP BY cause ORDER BY cause',
        (since, since))
    rows = cur.fetchall()
    by_cause = {c: {'events': int(n), 'loss_usd': str(_q(total))} for c, n, total in rows}
    total = sum((_q(r[2]) for r in rows), Decimal('0'))
    return {'since': since, 'by_cause': by_cause,
            'total_events': sum(v['events'] for v in by_cause.values()), 'total_loss_usd': str(total)}

__all__ = ['record_overrun', 'rollup', 'CAUSES',
           'METERED_OVERRUN', 'BUDGET_CAPPED_SHORTFALL', 'UNRECONCILED_UNKNOWN']
