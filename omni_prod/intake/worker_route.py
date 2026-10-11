"""Real-model intake interpretation routed through the worker (founder
directive 2026-10-11 §4: the worker already holds the Gemini credential, so no
API key is copied to Vercel).

    API (Vercel)                         worker host (intake-worker service)
    WorkerInterpreter.interpret()  ->    RQ queue 'omni-intake'  ->  execute_intake_interpretation()
      waits <= OMNI_INTAKE_WAIT_SECONDS        ModelInterpreter over the routed gateway,
      validates the result AGAIN               task class 'conversation', per-call budget cap
      falls back to deterministic              returns the interpretation dict + metered cost

Everything is OFF unless all of these are set (founder authorization):
  API:    OMNI_INTAKE_MODEL=1, OMNI_INTAKE_VIA_WORKER=1, OMNI_INTAKE_MODEL_BUDGET_USD>0 (per project)
  worker: OMNI_INTAKE_MODEL=1, OMNI_INTAKE_CALL_BUDGET_USD>0 (per message)
The intake queue is separate from builds, so a running build never delays a
customer's reply; the intake worker has no Docker socket and no sandbox.
"""
from __future__ import annotations

import os
import time
from decimal import Decimal

from .interpreter import DeterministicInterpreter, Interpretation, ModelInterpreter, Proposal, validate_model_output

INTAKE_QUEUE = 'omni-intake'
JOB = 'omni_prod.worker_tasks.execute_intake_interpretation'


def execute(message: str, *, gateway_factory=None) -> dict:
    """Worker side. Returns {'ok', 'raw', 'cost_usd', 'model', 'error'} -- the
    raw model JSON is returned so the API validates it against the message."""
    if os.getenv('OMNI_INTAKE_MODEL') != '1':
        return {'ok': False, 'error': 'intake model disabled on the worker'}
    cap = Decimal(os.getenv('OMNI_INTAKE_CALL_BUDGET_USD', '0') or '0')
    if cap <= 0:
        return {'ok': False, 'error': 'no per-message intake budget configured'}
    if gateway_factory is None:
        from ..model_policy import ModelUsePolicy
        from ..model_runtime_config import ModelRuntimeConfig
        from ..routed_gateway import RoutedModelGateway
        cfg = ModelRuntimeConfig.from_env()
        policy = ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True, external_budget_usd=cap,
                                max_external_calls_per_build=2)
        gateway = RoutedModelGateway(ranked=cfg.catalog, routing_policy=cfg.routing, policy=policy)
    else:
        gateway = gateway_factory(cap)
    from .interpreter import SYSTEM
    try:
        raw = gateway.complete_json(system=SYSTEM, user=message[:6000], max_tokens=1200, task='conversation')
    except Exception as exc:
        return {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:200]}'}
    usage = getattr(gateway, 'last_usage', None)
    records = getattr(getattr(gateway, 'recorder', None), 'records', []) or []
    metered = sum((r.metered_cost_usd or Decimal('0') for r in records), Decimal('0'))
    return {'ok': True, 'raw': raw, 'cost_usd': str(metered),
            'model': getattr(usage, 'model', None) or (records[-1].model if records else None)}


class WorkerInterpreter:
    name = 'model-via-worker'

    def __init__(self, enqueue, fetch, *, wait_seconds: float | None = None, sleep=time.sleep, clock=time.monotonic):
        self.enqueue, self.fetch = enqueue, fetch          # injected: RQ in production, doubles in tests
        self.wait = float(os.getenv('OMNI_INTAKE_WAIT_SECONDS', '8')) if wait_seconds is None else wait_seconds
        self.sleep, self.clock = sleep, clock
        self.fallback = DeterministicInterpreter()

    def interpret(self, message: str, brief=None) -> Interpretation:
        base = self.fallback.interpret(message, brief)
        try:
            job_id = self.enqueue(message)
        except Exception as exc:
            base.dropped.append(f'intake queue unavailable: {type(exc).__name__}')
            return base
        deadline = self.clock() + self.wait
        result = None
        while self.clock() < deadline:
            result = self.fetch(job_id)
            if result is not None:
                break
            self.sleep(0.4)
        if not result or not result.get('ok'):
            base.dropped.append('model reply not available: ' + (result or {}).get('error', 'timeout'))
            return base
        model, dropped = validate_model_output(result.get('raw'), message)
        if model is None:
            base.dropped.append('model output malformed; deterministic result used')
            return base
        merged = {p.field: p for p in model.proposals}
        for p in base.proposals:
            m = merged.get(p.field)
            if m is None or (p.confidence == 'high' and m.value != p.value):
                merged[p.field] = p
        return Interpretation(model.language, model.product_family, list(merged.values()),
                              model.delegate_rest or base.delegate_rest, model.requirements or base.requirements,
                              f'model:{result.get("model") or "?"}+deterministic', dropped, str(result.get('cost_usd') or '0'))


def rq_worker_interpreter(redis_url: str) -> WorkerInterpreter:
    from ..queueing import queue
    q = queue(redis_url, INTAKE_QUEUE)

    def enqueue(message):
        return q.enqueue(JOB, message, job_timeout=60, result_ttl=300, failure_ttl=300).id

    def fetch(job_id):
        from rq.job import Job
        job = Job.fetch(job_id, connection=q.connection)
        status = job.get_status(refresh=True)
        if status == 'finished':
            return job.return_value()
        if status in ('failed', 'stopped', 'canceled'):
            return {'ok': False, 'error': f'job {status}'}
        return None

    return WorkerInterpreter(enqueue, fetch)
