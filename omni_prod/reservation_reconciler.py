"""Resolve credit reservations that release() left RESERVED for ever (P0, 2026-10-30).

PostgresSubscriptionService.release() returns WITHOUT releasing when provider_exposure() sees an attempt with
authorized cost and no metered cost -- correct while the build may still be calling the provider, wrong once the
build is over: nothing came back to it, so a cancelled build kept its whole reservation (credits and provider
budget) for ever, although v28_build_cancel tells the customer only used work is charged.

Once the build or modification is TERMINAL, its provider-call attempts decide (under the reservation lock):
  * every attempt finished (outcome ok/error) and nothing was metered      -> RELEASE (counters restored)
  * every attempt finished, every completed call metered, total > 0          -> SETTLE on the metered total
  * an attempt still 'unknown', or a completed call with no metered cost    -> HOLD (real, unknown liability)
A READY build is never touched (its settlement is the build's own). Internal-QA reservations release without
touching customer counters, exactly as release() does.

    python -m omni_prod.reservation_reconciler            # dry run: what each RESERVED terminal row would get
    python -m omni_prod.reservation_reconciler --apply    # resolve them
The janitor (omni_prod.maintenance) runs it on every pass.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal

TERMINAL_BUILD = ('failed', 'cancelled')
TERMINAL_MODIFICATION = ('FAILED', 'CANCELLED', 'REJECTED', 'CONFLICT')
MIN_AGE_MINUTES = 10


def candidates(cur, *, older_than_minutes: int = MIN_AGE_MINUTES, limit: int = 50) -> list[str]:
    cur.execute(
        "SELECT cr.build_id FROM credit_reservations cr WHERE cr.status = 'RESERVED' "
        "AND cr.created_at < now() - make_interval(mins => %s) AND ("
        "  EXISTS (SELECT 1 FROM build_jobs b WHERE b.id = cr.build_id AND b.status = ANY(%s))"
        "  OR EXISTS (SELECT 1 FROM modification_requests m WHERE m.id = cr.build_id AND m.status = ANY(%s))"
        ") ORDER BY cr.created_at LIMIT %s",
        (int(older_than_minutes), list(TERMINAL_BUILD), list(TERMINAL_MODIFICATION), int(limit)))
    return [r[0] for r in cur.fetchall()]


def is_terminal(cur, build_id: str) -> bool:
    cur.execute("SELECT EXISTS (SELECT 1 FROM build_jobs WHERE id = %s AND status = ANY(%s)) "
                "OR EXISTS (SELECT 1 FROM modification_requests WHERE id = %s AND status = ANY(%s))",
                (build_id, list(TERMINAL_BUILD), build_id, list(TERMINAL_MODIFICATION)))
    return bool(cur.fetchone()[0])


def verdict(cur, build_id: str) -> tuple[str, Decimal, str]:
    """('release'|'settle'|'hold', metered_total, reason) from the build's provider-call attempts."""
    cur.execute("SELECT outcome, metered_cost_usd FROM task_attempts WHERE build_id = %s AND kind = 'provider_call'",
                (build_id,))
    rows = cur.fetchall()
    if any(outcome == 'unknown' for outcome, _ in rows):
        return 'hold', Decimal('0'), 'a provider call has outcome unknown'
    if any(outcome == 'ok' and metered is None for outcome, metered in rows):
        return 'hold', Decimal('0'), 'a completed provider call has no metered cost'
    total = sum((Decimal(str(m)) for _, m in rows if m is not None), Decimal('0'))
    if total > 0:
        return 'settle', total, f'{len(rows)} finished call(s), metered {total}'
    return 'release', total, f'{len(rows)} finished call(s), nothing metered'


def reconcile(subscriptions, pool, *, apply: bool, older_than_minutes: int = MIN_AGE_MINUTES,
              limit: int = 50) -> list[dict]:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            ids = candidates(cur, older_than_minutes=older_than_minutes, limit=limit)
    out = []
    for build_id in ids:
        if apply:
            out.append(subscriptions.reconcile_terminal_reservation(build_id=build_id))
        else:
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    action, total, reason = verdict(cur, build_id)
            out.append({'build_id': build_id, 'action': action, 'metered_usd': str(total), 'reason': reason,
                        'applied': False})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--apply', action='store_true', help='resolve the reservations (default: dry run)')
    parser.add_argument('--older-than', type=int, default=MIN_AGE_MINUTES)
    parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args(argv)
    from .investor_app import _v28, _v28_pool
    if _v28_pool is None:
        print('reservation_reconciler requires OMNI_CREATOR_PERSISTENCE=postgres', file=sys.stderr)
        return 2
    results = reconcile(_v28.subscriptions, _v28_pool, apply=args.apply, older_than_minutes=args.older_than,
                        limit=args.limit)
    for r in results:
        print(json.dumps(r, default=str), flush=True)
    print(f'reservation_reconciler: {len(results)} terminal RESERVED row(s), apply={args.apply}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
