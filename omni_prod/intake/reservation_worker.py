"""Worker side of a reserved intake model call (Issue #12).

    claim (atomic) -> build bounded gateway -> mark EXECUTING (committed)
    -> ONE provider call, no DB transaction open -> meter -> settle

* A duplicate Redis delivery finds the reservation already claimed: no-op.
* The gateway is bound to the reservation: external budget = quoted amount,
  exactly one external call, no transient retry, allowed models only. A route
  whose worst case exceeds the quote is refused by the gateway before any
  contact.
* Metering never turns "no usage reported" into $0: an HTTP error, timeout or
  missing usage after the provider was contacted is UNKNOWN (actual NULL, the
  quote stays held). Provider-reported cost -> CONFIRMED; reported tokens x
  source-backed price -> ESTIMATED; provider never contacted (write-ahead
  ledger has no attempt) -> CONFIRMED_ZERO.
"""
from __future__ import annotations

import os
import socket
from decimal import Decimal

from . import budget as B

RQ_JOB = 'omni_prod.intake.reservation_worker.rq_execute'
INTAKE_QUEUE = 'omni-intake'



RESERVED_TASKS = ('conversation', 'conversation_complex')


def _reserved_task(payload: dict, quote: dict) -> str:
    """The task the reservation was QUOTED for -- never a different (pricier) one."""
    task = (quote or {}).get('task') or 'conversation'
    if task not in RESERVED_TASKS or payload.get('task', task) != task:
        raise ValueError(f'reserved task mismatch: quote {task!r}, payload {payload.get("task")!r}')
    return task

def build_gateway(quoted_usd: Decimal, models: tuple[str, ...]):
    from ..providers import venice_gateway
    if venice_gateway.selected():   # OMNI_INTAKE_PROVIDER=venice (C3); a missing key raises -> "no model route"
        return venice_gateway.VeniceIntakeGateway(quoted_usd)
    from ..model_policy import ModelUsePolicy
    from ..model_router import RoutingPolicy
    from ..model_runtime_config import ModelRuntimeConfig
    from ..routed_gateway import RoutedModelGateway
    cfg = ModelRuntimeConfig.from_env()
    ranked = tuple(m for m in cfg.catalog if m.option.model in models)
    policy = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True, external_budget_usd=quoted_usd,
                            max_external_calls_per_build=1)
    return RoutedModelGateway(ranked=ranked, routing_policy=RoutingPolicy(minimum_quality=70, prefer_cost=True),
                              policy=policy, transient_retries=0)


def meter(gateway, quote: dict) -> dict:
    """Cost state of everything this gateway sent, from its write-ahead attempt ledger."""
    records = [r for r in (getattr(getattr(gateway, 'recorder', None), 'records', None) or [])
               if getattr(r, 'kind', 'provider_call') == 'provider_call']
    if not records:
        return {'contacted': False, 'cost_state': B.CONFIRMED_ZERO, 'actual_usd': Decimal('0'),
                'reason': 'provider not contacted (no write-ahead attempt)'}
    bound = int(quote.get('max_tokens') or 0)
    states, total, overrun, why = [], Decimal('0'), False, []
    last = records[-1]
    for r in records:
        if r.provider_reported_cost_usd is not None:
            states.append(B.CONFIRMED_ZERO if r.provider_reported_cost_usd == 0 and r.input_tokens is not None
                          else B.CONFIRMED)
            total += Decimal(str(r.provider_reported_cost_usd))
        elif r.input_tokens is not None and r.output_tokens is not None and r.metered_cost_usd is not None:
            states.append(B.ESTIMATED)
            total += Decimal(str(r.metered_cost_usd))
        else:
            states.append(B.COST_UNKNOWN)
            why.append(f'{r.provider}/{r.model}: outcome {r.outcome}, no usage reported'
                       + (f' ({r.failure_reason[:200]})' if r.failure_reason else ''))
        if r.output_tokens is not None and bound and r.output_tokens > bound:
            overrun = True
    info = {'contacted': True, 'attempts': len(records), 'provider': last.provider, 'model': last.model,
            'provider_request_id': last.provider_request_id, 'input_tokens': last.input_tokens,
            'output_tokens': last.output_tokens, 'output_overrun': overrun}
    if B.COST_UNKNOWN in states:
        return {**info, 'cost_state': B.COST_UNKNOWN, 'actual_usd': None, 'reason': '; '.join(why)}
    if B.ESTIMATED in states:
        return {**info, 'cost_state': B.ESTIMATED, 'actual_usd': total}
    if all(s == B.CONFIRMED_ZERO for s in states):
        return {**info, 'cost_state': B.CONFIRMED_ZERO, 'actual_usd': Decimal('0')}
    return {**info, 'cost_state': B.CONFIRMED, 'actual_usd': total}


def execute_reservation(pool, reservation_id: str, *, worker_id: str | None = None, gateway_factory=None,
                        lease_seconds: int = 90, max_age_seconds: int = 120) -> dict:
    svc = B.ReservationService(pool)
    worker_id = worker_id or f'{socket.gethostname()}:{os.getpid()}'
    r = svc.claim(reservation_id, worker_id=worker_id, lease_seconds=lease_seconds, max_age_seconds=max_age_seconds)
    if r is None:
        current = svc.get(reservation_id)
        return {'ok': False, 'skipped': True, 'state': getattr(current, 'state', None)}
    payload = svc.payload(r.id)
    models = tuple(r.quote.get('allowed_models') or B.allowed_models())
    try:
        task = _reserved_task(payload, r.quote)
    except ValueError as exc:   # never call a task the quote did not price
        svc.release(r.id, reason=str(exc)[:200])
        return {'ok': False, 'error': 'reserved task mismatch', 'state': B.RELEASED}
    try:   # building the gateway never contacts a provider
        gateway = (gateway_factory or build_gateway)(r.quoted_usd, models)
    except Exception as exc:
        svc.release(r.id, reason=f'no model route: {type(exc).__name__}')
        return {'ok': False, 'error': 'no model route', 'state': B.RELEASED}
    if not svc.mark_executing(r, lease_seconds=lease_seconds):
        return {'ok': False, 'error': 'lease lost before execution'}
    raw, error = None, None
    try:   # no database transaction is open here
        raw = gateway.complete_json(system=payload['system'], user=payload['user'],
                                    max_tokens=int(payload['max_tokens']),
                                    task=task)
    except Exception as exc:
        error = f'{type(exc).__name__}: {str(exc)[:300]}'
    m = meter(gateway, r.quote)
    if m['cost_state'] == B.COST_UNKNOWN:
        reason = m.get('reason') or error or 'usage not reported'
    else:
        reason = None
    ok = error is None and isinstance(raw, dict)
    settled = svc.settle(r, cost_state=m['cost_state'], actual_usd=m['actual_usd'], failure_reason=reason,
                         provider=m.get('provider'), model=m.get('model'),
                         provider_request_id=m.get('provider_request_id'),
                         result={'ok': ok, 'raw': raw if ok else None, 'error': error,
                                 'prompt_version': payload.get('prompt_version')},
                         metering={k: v for k, v in m.items() if k not in ('actual_usd',)})
    return {'ok': ok, 'state': settled.state, 'cost_state': settled.cost_state,
            'actual_usd': None if settled.actual_usd is None else str(settled.actual_usd), 'model': settled.model}


def rq_execute(reservation_id: str) -> dict:
    """RQ entrypoint on the 'omni-intake' queue. Needs OMNI_DATABASE_URL."""
    if os.getenv('OMNI_INTAKE_MODEL') != '1':
        return {'ok': False, 'error': 'intake model disabled on the worker'}
    from ..db import DatabasePool
    pool = DatabasePool(os.environ['OMNI_DATABASE_URL'])
    try:
        return execute_reservation(pool, reservation_id)
    finally:
        pool.close()


def relay_main(argv: list[str] | None = None) -> int:
    """python -m omni_prod.intake.reservation_worker {relay|reconcile|maintain} [--loop SECONDS]
    maintain = relay pending outbox rows, then reconcile expired leases (one pass each loop)."""
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('relay', 'reconcile', 'maintain'))
    ap.add_argument('--loop', type=float, default=0.0)
    args = ap.parse_args(argv)
    db, redis_url = os.getenv('OMNI_DATABASE_URL', '').strip(), os.getenv('OMNI_REDIS_URL', '').strip()
    if not db or (args.cmd in ('relay', 'maintain') and not redis_url):
        print('OMNI_DATABASE_URL (and OMNI_REDIS_URL for relay) required', file=sys.stderr)
        return 2
    from ..db import DatabasePool
    pool = DatabasePool(db)
    svc = B.ReservationService(pool)

    def enqueue(rid):
        from ..queueing import enqueue_build
        enqueue_build(redis_url, RQ_JOB, rid, job_id=rid, queue_name=INTAKE_QUEUE, timeout=120)

    # SIGTERM = graceful stop (2026-10-19). As PID 1 in its container Python gets no default SIGTERM action, so
    # without this `docker compose stop` waited the whole drain deadline and then SIGKILLed it (exit 137). The
    # current pass is never interrupted: the flag is checked between passes and wakes the sleep immediately.
    import signal
    import threading
    stop = threading.Event()

    def _on_term(signum, _frame):
        stop.set()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _on_term)
        except ValueError:   # not the main thread (embedded use): keep the default handling
            pass
    try:
        while not stop.is_set():
            try:
                out = {}
                if args.cmd in ('relay', 'maintain'):
                    out['relayed'] = svc.relay_once(enqueue)
                if args.cmd in ('reconcile', 'maintain'):
                    out['reconciled'] = svc.reconcile()
                print(f'intake {args.cmd}: {out}', flush=True)
            except Exception as exc:
                print(f'intake {args.cmd} failed: {type(exc).__name__}: {exc}', file=sys.stderr, flush=True)
                if not args.loop:
                    return 1
            if not args.loop:
                return 0
            stop.wait(args.loop)
        print(f'intake {args.cmd}: stop signal received, exiting', flush=True)
        return 0
    finally:
        pool.close()


if __name__ == '__main__':
    raise SystemExit(relay_main())
