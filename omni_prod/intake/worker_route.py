"""Real-model intake interpretation routed through the worker, with a durable
budget reservation before any provider contact (Issue #12).

    API (Vercel)                                  worker host (intake-worker)
    ReservedWorkerInterpreter.interpret()
      QUOTE   worst case of the bounded call
      RESERVE reservation + outbox row (1 txn)  ->  RQ 'omni-intake', job id = reservation id
      enqueue (fast path; relay is the backstop)    reservation_worker.execute_reservation():
      wait <= OMNI_INTAKE_WAIT_SECONDS                claim -> EXECUTING -> one call -> settle
      validate the stored result AGAIN against
      the message; deterministic fallback otherwise

The worker holds the provider key; nothing is copied to Vercel. There is no
unreserved path: the legacy message-only job refuses to run.
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid

from . import budget as B
from .interpreter import (MAX_MESSAGE_CHARS, MAX_OUTPUT_TOKENS, PROMPT_VERSION, SYSTEM, DeterministicInterpreter,
                          Interpretation, merge, validate_model_output)

INTAKE_QUEUE = 'omni-intake'
JOB = 'omni_prod.intake.reservation_worker.rq_execute'
LEGACY_JOB = 'omni_prod.worker_tasks.execute_intake_interpretation'


def execute(message: str, **_ignored) -> dict:
    """Legacy unreserved job (Wave A2). Refuses: every paid call needs a reservation."""
    return {'ok': False, 'error': 'unreserved intake model calls are disabled (Issue #12); use reservations'}


class ReservedWorkerInterpreter:
    name = 'model-via-worker'

    def __init__(self, service: B.ReservationService, enqueue, *, account_id: str, project_id: str,
                 request_key: str | None, caps: B.Caps, lane: str = B.PRODUCTION, campaign_id: str | None = None,
                 wait_seconds: float | None = None, sleep=time.sleep, clock=time.monotonic):
        self.svc, self.enqueue = service, enqueue
        self.account_id, self.project_id, self.request_key = account_id, project_id, request_key
        self.caps, self.lane, self.campaign_id = caps, lane, campaign_id
        self.wait = float(os.getenv('OMNI_INTAKE_WAIT_SECONDS', '8')) if wait_seconds is None else wait_seconds
        self.sleep, self.clock = sleep, clock
        self.fallback = DeterministicInterpreter()

    def _key(self, message: str) -> str:
        digest = hashlib.sha256(message.encode('utf-8')).hexdigest()[:24]
        tail = self.request_key or uuid.uuid4().hex
        return f'intake:{self.account_id}:{self.project_id}:{tail}:{digest}'[:300]

    def interpret(self, message: str, brief=None) -> Interpretation:
        base = self.fallback.interpret(message, brief)
        user = message[:MAX_MESSAGE_CHARS]
        try:
            quote = B.quote(system=SYSTEM, user=user, max_tokens=MAX_OUTPUT_TOKENS)
        except B.QuoteUnavailable as exc:
            base.dropped.append(f'model not used: {exc}')
            return base
        try:
            r = self.svc.reserve(idempotency_key=self._key(message), account_id=self.account_id,
                                 project_id=self.project_id, quote_=quote, caps=self.caps, lane=self.lane,
                                 campaign_id=self.campaign_id,
                                 payload={'system': SYSTEM, 'user': user, 'max_tokens': MAX_OUTPUT_TOKENS,
                                          'prompt_version': PROMPT_VERSION})
        except B.BudgetExceeded as exc:
            base.dropped.append(f'model not used: budget {exc.scope.split(":")[0]} exhausted')
            return base
        except Exception as exc:   # BudgetError, ValueError, schema/DB errors: fail closed, no paid call
            base.dropped.append(f'model not used: {type(exc).__name__}')
            return base
        if r.state == B.RESERVED:
            try:
                self.enqueue(r.id)
                self.svc.mark_enqueued(r.id)
            except Exception as exc:    # queue down: nothing was sent, so give the money back now
                self.svc.release(r.id, reason=f'enqueue failed: {type(exc).__name__}')
                base.dropped.append('model not used: intake queue unavailable')
                base.reservation_id = r.id
                return base
        deadline = self.clock() + self.wait
        current = self.svc.get(r.id, account_id=self.account_id)
        while current is not None and current.state not in (B.SETTLED, B.UNKNOWN, B.RELEASED) and \
                self.clock() < deadline:
            self.sleep(0.3)
            current = self.svc.get(r.id, account_id=self.account_id)
        base.reservation_id = r.id
        if current is None or current.state not in (B.SETTLED, B.UNKNOWN, B.RELEASED):
            base.dropped.append('model reply not available in time; cost settles on the reservation')
            base.cost_usd, base.cost_state = None, 'PENDING'
            return base
        if current.state == B.RELEASED:
            base.dropped.append('model not used: ' + (current.failure_reason or 'released'))
            return base
        cost = None if current.actual_usd is None else str(current.actual_usd)
        result = current.result or {}
        if current.state == B.UNKNOWN or not result.get('ok'):
            base.dropped.append('model reply not available: ' + str(result.get('error') or current.failure_reason)[:200])
            base.cost_usd, base.cost_state = cost, current.cost_state
            return base
        model, _ = validate_model_output(result.get('raw'), message)
        if model is None:
            base.dropped.append('model output malformed; deterministic result used')
            base.cost_usd, base.cost_state = cost, current.cost_state
            return base
        return merge(base, model, interpreter=f'model:{current.model or "?"}+deterministic', cost_usd=current.actual_usd,
                     cost_state=current.cost_state, reservation_id=r.id)


def rq_enqueue(redis_url: str):
    from ..queueing import enqueue_build

    def enqueue(reservation_id: str):
        enqueue_build(redis_url, JOB, reservation_id, job_id=reservation_id, queue_name=INTAKE_QUEUE, timeout=120)
    return enqueue
