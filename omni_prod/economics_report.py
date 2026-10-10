"""Unit economics from the immutable ledgers (issue #6 P3.5-6; Production
Assurance v2 §9). Read-only; internal only (never a customer API).

    python -m omni_prod.economics_report

Inputs: build_jobs (outcome, timing, repairs), credit_reservations (settled
amount, cost basis), task_attempts (per-call metered / authorized cost, task,
model, outcome). Rules:
  * metered = provider tokens x versioned catalog price (incl. thinking tokens
    since 20b4bcc); unknown stays unknown and is reported as exposure (the
    authorized worst case), never as zero;
  * revenue and infrastructure cost are NOT invented: with no paid customers and
    free-tier infrastructure, contribution margin is reported as UNKNOWN with
    the reason;
  * invoice reconciliation is BLOCKED until the provider billing export exists.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from decimal import Decimal


def _d(v) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def _pct(values, q):
    if not values:
        return None
    vals = sorted(values)
    k = max(0, min(len(vals) - 1, int(round(q * (len(vals) - 1)))))
    return vals[k]


def compute(builds: list[dict], attempts: list[dict]) -> dict:
    """builds: id, status, funding, user, day, seconds, repairs, settled, cost_basis
    attempts: build_id, task_type, model, outcome, metered, authorized"""
    per_build = defaultdict(lambda: {'metered': Decimal('0'), 'unknown_calls': 0, 'exposure': Decimal('0'),
                                     'repair_metered': Decimal('0'), 'calls': 0})
    models = defaultdict(lambda: {'calls': 0, 'ok': 0, 'error': 0, 'unknown': 0, 'metered': Decimal('0')})
    for a in attempts:
        pb = per_build[a['build_id']]
        pb['calls'] += 1
        m = _d(a.get('metered'))
        auth = _d(a.get('authorized')) or Decimal('0')
        if m is not None:
            pb['metered'] += m
            if a.get('task_type') == 'repair':
                pb['repair_metered'] += m
        elif auth > 0 and a.get('outcome') in ('ok', 'unknown'):
            pb['unknown_calls'] += 1
            pb['exposure'] += auth
        mm = models[a.get('model') or '?']
        mm['calls'] += 1
        mm[a.get('outcome') if a.get('outcome') in ('ok', 'error', 'unknown') else 'unknown'] += 1
        if m is not None:
            mm['metered'] += m

    rows, by_day, by_user = [], defaultdict(Decimal), defaultdict(Decimal)
    for b in builds:
        led = per_build.get(b['id'])
        cost = None if led is None else (None if led['unknown_calls'] else led['metered'])
        rows.append({**b, 'metered': led and led['metered'], 'unknown_calls': led['unknown_calls'] if led else 0,
                     'exposure': led and led['exposure'], 'repair_metered': led and led['repair_metered'], 'cost': cost})
        if led is not None:
            by_day[b.get('day') or '?'] += led['metered']
            by_user[b.get('user') or '?'] += led['metered']

    def costs(pred):
        return [r['cost'] for r in rows if pred(r) and r['cost'] is not None]

    measured = [r for r in rows if r['metered'] is not None]
    ready = [r for r in measured if r['status'] == 'ready']
    failed = [r for r in measured if r['status'] == 'failed']
    all_costs = costs(lambda r: True)
    total_metered = sum((r['metered'] for r in measured), Decimal('0'))
    total_repair = sum((r['repair_metered'] or Decimal('0') for r in measured), Decimal('0'))
    durations = [r['seconds'] for r in ready if r.get('seconds') is not None]
    out = {
        'builds_with_ledger': len(measured),
        'outcomes': {s: sum(1 for r in measured if r['status'] == s) for s in ('ready', 'failed', 'cancelled')},
        'success_rate': (round(len(ready) / len([r for r in measured if r['status'] in ('ready', 'failed')]), 3)
                         if [r for r in measured if r['status'] in ('ready', 'failed')] else None),
        'metered_total_usd': str(total_metered),
        'unknown_cost_builds': sum(1 for r in measured if r['unknown_calls']),
        'unknown_exposure_usd': str(sum((r['exposure'] or Decimal('0') for r in measured), Decimal('0'))),
        'cost_per_build_avg_usd': str(round(statistics.mean(all_costs), 6)) if all_costs else None,
        'cost_per_build_p50_usd': str(_pct(all_costs, 0.5)) if all_costs else None,
        'cost_per_build_p95_usd': str(_pct(all_costs, 0.95)) if all_costs else None,
        'cost_per_successful_build_usd': (str(round(sum((r['metered'] for r in measured), Decimal('0')) / len(ready), 6))
                                          if ready else None),
        'failed_build_cost_usd': str(sum((r['metered'] for r in failed), Decimal('0'))),
        'repair_share_of_spend': (str(round(total_repair / total_metered, 3)) if total_metered else None),
        'ready_build_seconds_p50': _pct(durations, 0.5), 'ready_build_seconds_p95': _pct(durations, 0.95),
        'spend_by_day_usd': {k: str(v) for k, v in sorted(by_day.items())},
        'spend_by_user_usd': {k: str(v) for k, v in sorted(by_user.items(), key=lambda kv: -kv[1])[:10]},
        'models': {k: {**v, 'metered': str(v['metered']),
                       'success_rate': round(v['ok'] / v['calls'], 3) if v['calls'] else None}
                   for k, v in sorted(models.items(), key=lambda kv: -kv[1]['metered'])},
        'contribution_margin': 'UNKNOWN: no customer revenue recorded (QA-funded builds only); '
                               'infrastructure runs on free tiers with no per-build allocation',
        'invoice_reconciliation': 'BLOCKED: needs the provider billing export (founder access)',
    }
    return out


_BUILDS_SQL = """
SELECT b.id, b.status, r.funding_source, br.user_id, to_char(b.created_at, 'YYYY-MM-DD'),
       EXTRACT(EPOCH FROM (b.finished_at - b.started_at)), b.repair_rounds, r.settled_provider_cost_usd,
       b.evidence_json->'economics_settlement'->'cost_basis'->>'llm'
FROM build_jobs b
LEFT JOIN credit_reservations r ON r.build_id = b.id
LEFT JOIN build_requests br ON br.build_id = b.id
WHERE b.created_at >= now() - interval '60 days'
"""
_ATTEMPTS_SQL = """
SELECT build_id, task_type, model, outcome, metered_cost_usd, authorized_cost_usd
FROM task_attempts WHERE kind = 'provider_call' AND created_at >= now() - interval '60 days'
"""


def main() -> int:
    from .investor_app import _v28_pool
    with _v28_pool.connection() as conn:
        b = conn.execute(_BUILDS_SQL).fetchall()
        a = conn.execute(_ATTEMPTS_SQL).fetchall()
    builds = [{'id': r[0], 'status': r[1], 'funding': r[2], 'user': (r[3] or '')[:8], 'day': r[4],
               'seconds': float(r[5]) if r[5] is not None else None, 'repairs': r[6], 'settled': r[7],
               'cost_basis': r[8]} for r in b]
    attempts = [{'build_id': r[0], 'task_type': r[1], 'model': r[2], 'outcome': r[3], 'metered': r[4],
                 'authorized': r[5]} for r in a]
    print('ECONOMICS ' + json.dumps(compute(builds, attempts), default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
