"""Attempt Ledger: immutable per-attempt execution evidence (migration 027).

Every provider call made through ``RoutedModelGateway`` and every verification
run of the build executor produces one record. Records carry the routing
decision (candidates, selected, reason), the versions that produced it
(policy, routing policy, prompt, price catalog) and the three cost layers kept
strictly apart: authorized, metered (usage x versioned catalog price) and
provider-reported. Reconciled cost is filled by a later reconciliation process.

Versions are content-addressed (short SHA-256 of the exact inputs), so two
attempts carry the same version id only if they ran under identical text and
configuration. Nothing here contains credentials.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from decimal import Decimal
import hashlib
import json
import logging
import time
import uuid
from typing import Any, Iterable

log = logging.getLogger(__name__)

VERIFICATION_CLASSES = ('PASS', 'REPAIRABLE_FAIL', 'RETRYABLE_FAIL', 'ESCALATABLE_FAIL', 'FATAL_FAIL')


def content_version(*parts: Any) -> str:
    """Short, stable id for exact content (prompt text, catalog, policy)."""
    h = hashlib.sha256()
    for part in parts:
        h.update(json.dumps(part, sort_keys=True, default=str, separators=(',', ':')).encode('utf-8'))
        h.update(b'\x1f')
    return h.hexdigest()[:12]


def metered_cost(option, input_tokens: int | None, output_tokens: int | None) -> Decimal | None:
    """usage x catalog price. Unknown when the provider did not report tokens."""
    if option is None or input_tokens is None or output_tokens is None:
        return None
    million = Decimal(1_000_000)
    return (Decimal(input_tokens) * option.input_per_million
            + Decimal(output_tokens) * option.output_per_million) / million


@dataclass
class AttemptRecord:
    task_type: str
    attempt_seq: int
    kind: str
    outcome: str
    provider: str | None = None
    model: str | None = None
    model_version: str | None = None
    provider_request_id: str | None = None
    trace_id: str | None = None
    policy_version: str | None = None
    routing_policy_version: str | None = None
    prompt_version: str | None = None
    price_catalog_version: str | None = None
    selection_reason: str | None = None
    selected_candidate: str | None = None
    candidate_set: list | None = None
    fallback_rank: int | None = None
    authorized_cost_usd: Decimal | None = None
    expected_cost_usd: Decimal | None = None
    metered_cost_usd: Decimal | None = None
    provider_reported_cost_usd: Decimal | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    latency_ms: int | None = None
    verification_class: str | None = None
    failure_reason: str | None = None
    # Build counters at the time of this attempt (migration 028), set by
    # AttemptRecorder.add(); see that method for exact definitions.
    retry_count: int | None = None
    repair_count: int | None = None
    regenerate_count: int | None = None
    escalation_count: int | None = None
    fallback_count: int | None = None
    # Not persisted: marks an attempt made by an escalation step. The current
    # pipeline has no escalation path, so this is never True yet.
    escalated: bool = False
    attempt_id: str = field(default_factory=lambda: f'att_{uuid.uuid4().hex}')

    def __post_init__(self) -> None:
        if self.kind not in ('provider_call', 'verification'):
            raise ValueError('invalid attempt kind')
        if self.outcome not in ('ok', 'error', 'unknown'):
            raise ValueError('invalid attempt outcome')
        if self.verification_class is not None and self.verification_class not in VERIFICATION_CLASSES:
            raise ValueError('invalid verification class')

    def to_dict(self) -> dict:
        out = asdict(self)
        for k, v in out.items():
            if isinstance(v, Decimal):
                out[k] = str(v)
        return out


class AttemptRecorder:
    """In-process collector for one build; persisted by the worker at the end."""

    def __init__(self, *, trace_id: str | None = None):
        self.trace_id = trace_id or f'trc_{uuid.uuid4().hex}'
        self.records: list[AttemptRecord] = []

    def next_seq(self) -> int:
        return len(self.records)

    def add(self, record: AttemptRecord) -> AttemptRecord:
        """Append a record and stamp the build counters (including this record).

        * retry_count: prior attempts of the same logical call. The routed
          gateway retries a call only by falling back to the next candidate,
          so this equals the record's fallback rank; verification runs are
          never retried automatically, so it is 0 for them.
        * repair_count: first attempts of `repair` calls so far.
        * regenerate_count: first attempts of `codegen` calls beyond the first.
        * escalation_count: attempts marked `escalated` so far.
        * fallback_count: attempts with fallback rank > 0 so far.
        """
        record.trace_id = record.trace_id or self.trace_id
        self.records.append(record)
        calls = [r for r in self.records if r.kind == 'provider_call']
        first = [r for r in calls if (r.fallback_rank or 0) == 0]
        record.retry_count = (record.fallback_rank or 0) if record.kind == 'provider_call' else 0
        record.repair_count = sum(1 for r in first if r.task_type == 'repair')
        record.regenerate_count = max(0, sum(1 for r in first if r.task_type == 'codegen') - 1)
        record.escalation_count = sum(1 for r in self.records if r.escalated)
        record.fallback_count = sum(1 for r in calls if (r.fallback_rank or 0) > 0)
        return record

    def summary(self) -> dict:
        by_task: dict[str, int] = {}
        for r in self.records:
            by_task[r.task_type] = by_task.get(r.task_type, 0) + 1
        last = self.records[-1] if self.records else None
        return {
            'attempts': len(self.records),
            'by_task_type': by_task,
            'fallbacks': sum(1 for r in self.records if (r.fallback_rank or 0) > 0),
            'unknown_outcomes': sum(1 for r in self.records if r.outcome == 'unknown'),
            'repairs': last.repair_count if last else 0,
            'regenerations': last.regenerate_count if last else 0,
            'escalations': last.escalation_count if last else 0,
        }


def classify_execution(report=None, error: BaseException | None = None) -> str:
    """Map an executor result to the verification taxonomy (Operating Contract 5.2).

    Only classes the current pipeline can actually distinguish are produced:
    PASS, REPAIRABLE_FAIL (acceptance/build failures the repair loop can act on),
    RETRYABLE_FAIL (sandbox infrastructure error, not the generated code).
    """
    if error is not None:
        return 'RETRYABLE_FAIL'
    if report is not None and getattr(report, 'passed', False):
        return 'PASS'
    return 'REPAIRABLE_FAIL'


class RecordingExecutor:
    """Wraps a repository executor; records each verification run."""

    def __init__(self, inner, recorder: AttemptRecorder, *, name: str = 'sandbox'):
        self._inner = inner
        self._recorder = recorder
        self._name = name

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        started = time.monotonic()
        try:
            report = self._inner.execute(repository=repository, spec=spec)
        except Exception as exc:
            self._recorder.add(AttemptRecord(
                task_type='verification', attempt_seq=self._recorder.next_seq(), kind='verification',
                outcome='error', provider=self._name, latency_ms=int((time.monotonic() - started) * 1000),
                verification_class=classify_execution(error=exc), failure_reason=f'{type(exc).__name__}: {exc}'[:500]))
            raise
        failures = getattr(report, 'failures', []) or []
        self._recorder.add(AttemptRecord(
            task_type='verification', attempt_seq=self._recorder.next_seq(), kind='verification',
            outcome='ok', provider=self._name, latency_ms=int((time.monotonic() - started) * 1000),
            verification_class=classify_execution(report=report),
            failure_reason=(None if getattr(report, 'passed', False)
                            else '; '.join(f'{getattr(f, "acceptance_id", "?")}: {getattr(f, "message", "")}'
                                           for f in failures)[:500] or 'verification failed')))
        return report


class TaskTaggedGateway:
    """Gives an agent a gateway whose calls carry a fixed task type."""

    def __init__(self, inner, task: str):
        self._inner = inner
        self.task = task

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def _supports_task(self) -> bool:
        return getattr(self._inner, 'accepts_task_tag', False)

    def complete(self, **kwargs):
        if self._supports_task():
            kwargs['task'] = self.task
        return self._inner.complete(**kwargs)

    def complete_json(self, **kwargs):
        if self._supports_task():
            kwargs['task'] = self.task
        return self._inner.complete_json(**kwargs)


_COLUMNS = ('attempt_id', 'build_id', 'tenant_id', 'project_id', 'task_id', 'task_type', 'attempt_seq', 'kind',
            'provider', 'model', 'model_version', 'provider_request_id', 'trace_id', 'policy_version',
            'routing_policy_version', 'prompt_version', 'price_catalog_version', 'selection_reason',
            'selected_candidate', 'candidate_set', 'fallback_rank', 'reservation_id', 'authorized_cost_usd',
            'expected_cost_usd', 'metered_cost_usd', 'provider_reported_cost_usd', 'input_tokens',
            'output_tokens', 'cached_tokens', 'latency_ms', 'outcome', 'verification_class',
            'failure_reason', 'final_outcome', 'retry_count', 'repair_count', 'regenerate_count',
            'escalation_count', 'fallback_count')


def ledger_rows(records: Iterable[AttemptRecord], *, build_id: str, tenant_id: str | None,
                project_id: str | None, reservation_id: str | None, final_outcome: str | None) -> list[tuple]:
    rows = []
    for r in records:
        d = r.to_dict()
        d.update(build_id=build_id, tenant_id=tenant_id, project_id=project_id,
                 task_id=f'{build_id}:{r.task_type}', reservation_id=reservation_id,
                 final_outcome=final_outcome,
                 candidate_set=None if r.candidate_set is None else json.dumps(r.candidate_set))
        rows.append(tuple(d.get(c) for c in _COLUMNS))
    return rows


def persist_attempts(pool, records: list[AttemptRecord], *, build_id: str, tenant_id: str | None = None,
                     project_id: str | None = None, reservation_id: str | None = None,
                     final_outcome: str | None = None) -> int:
    """Insert records idempotently (attempt_id primary key). Returns rows offered."""
    rows = ledger_rows(records, build_id=build_id, tenant_id=tenant_id, project_id=project_id,
                       reservation_id=reservation_id, final_outcome=final_outcome)
    if not rows:
        return 0
    placeholders = ','.join('%s::jsonb' if c == 'candidate_set' else '%s' for c in _COLUMNS)
    sql = (f"INSERT INTO task_attempts ({','.join(_COLUMNS)}) VALUES ({placeholders}) "
           "ON CONFLICT (attempt_id) DO UPDATE SET final_outcome = EXCLUDED.final_outcome")
    with pool.connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.executemany(sql, rows)
    return len(rows)
