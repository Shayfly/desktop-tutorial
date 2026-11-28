"""S13.4 (the owner, 2026-11-27, answer 6): the render queue of long media jobs (a song, a clip, a sprite sheet).

Why a table and not only Redis. The build queue (omni_prod/queueing.py, RQ on Redis) ends a job at 1,200 s; a render
may take longer and must survive a worker that dies in the middle, and it must not pay a provider twice when it resumes.
So a render job is a ROW (infra/postgres/050_media_infra.sql) with a lease, a bounded number of attempts and a total
time budget; the build's worker claims it and gives it back. The RQ queue named MEDIA_QUEUE (queueing.py) only carries the
wake-up; the row is the truth. Nothing here calls a provider: a handler (registered per kind by the caller) does.

The life of a row, every step bounded:
  enqueue   one row per (account, idempotency_key); the same request again returns the same job, a different payload under
            the same key raises IdempotencyConflict (never a second paid job, never a silent overwrite)
  claim     takes the oldest queued job (FOR UPDATE SKIP LOCKED: two workers never get the same one), counts an attempt and
            leases it for lease_seconds, never beyond the job's total budget (counted from its FIRST start)
  heartbeat extends the lease, never beyond the budget; False when the lease is no longer this worker's
  complete  only the lease holder may; succeeded
  fail      only the lease holder may; retry=True returns it to the queue until max_attempts, then 'dead'; retry=False 'failed'
  reap      (inside every claim) a running job whose lease ran out is returned to the queue, ends 'dead' when it has used
            its attempts, and ends 'failed' (budget_exceeded) when its budget is spent. A killed worker therefore never
            leaves a job 'running' forever: the next claim finds it.
A job another account owns answers get() with None, as an unknown id.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from typing import Callable

MAX_ATTEMPTS = 5
MAX_BUDGET_SECONDS = 7200
MAX_LEASE_SECONDS = 1800
MIGRATION = '050_media_infra'
MISSING_TABLE = f'MISSING: migration {MIGRATION} (infra/postgres/{MIGRATION}.sql) is not applied to this database'
_COLS = ('job_id', 'account_id', 'project_id', 'build_id', 'kind', 'idempotency_key', 'payload', 'status', 'attempts',
         'max_attempts', 'budget_seconds', 'lease_owner', 'lease_expires_at', 'result', 'error_code', 'error_message')
_RETURNING = ', '.join(_COLS)
_KIND = re.compile(r'[a-z][a-z0-9_]{0,31}')
_KEY = re.compile(r'[A-Za-z0-9._:-]{8,120}')


class IdempotencyConflict(ValueError):
    pass


class MediaQueueError(RuntimeError):
    pass


@dataclass(frozen=True)
class MediaJob:
    job_id: str
    account_id: str
    project_id: str
    build_id: str
    kind: str
    idempotency_key: str
    payload: dict
    status: str
    attempts: int
    max_attempts: int
    budget_seconds: int
    lease_owner: str | None
    lease_expires_at: dt.datetime | None
    result: dict | None
    error_code: str | None
    error_message: str | None


def _job(row) -> MediaJob:
    return MediaJob(**dict(zip(_COLS, row)))


def _digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


# One statement per step. `now` is the database's clock unless a test passes one: every worker then agrees on it.
_NOW = 'COALESCE(%(now)s::timestamptz, clock_timestamp())'
_REAP = f"""
UPDATE media_render_jobs SET
    status = CASE WHEN started_at + budget_seconds * interval '1 second' <= {_NOW} THEN 'failed'
                  WHEN status = 'running' AND attempts >= max_attempts THEN 'dead' ELSE 'queued' END,
    error_code = CASE WHEN started_at + budget_seconds * interval '1 second' <= {_NOW} THEN 'budget_exceeded'
                      WHEN status = 'running' AND attempts >= max_attempts THEN 'lease_lost_attempts_used' ELSE NULL END,
    error_message = CASE WHEN started_at + budget_seconds * interval '1 second' <= {_NOW}
                         THEN 'the job used its whole time budget'
                         WHEN status = 'running' AND attempts >= max_attempts THEN 'the worker stopped answering on the last attempt'
                         ELSE NULL END,
    finished_at = CASE WHEN started_at + budget_seconds * interval '1 second' <= {_NOW}
                         OR (status = 'running' AND attempts >= max_attempts) THEN {_NOW} END,
    lease_owner = NULL, lease_expires_at = NULL
WHERE (status = 'running' AND lease_expires_at <= {_NOW})
   OR (status = 'queued' AND started_at IS NOT NULL AND started_at + budget_seconds * interval '1 second' <= {_NOW})
"""
_CLAIM = f"""
WITH next AS (
    SELECT job_id FROM media_render_jobs WHERE status = 'queued' ORDER BY created_at, job_id FOR UPDATE SKIP LOCKED LIMIT 1)
UPDATE media_render_jobs j SET
    status = 'running', attempts = j.attempts + 1, lease_owner = %(worker)s,
    started_at = COALESCE(j.started_at, {_NOW}),
    lease_expires_at = LEAST({_NOW} + %(lease)s * interval '1 second',
                             COALESCE(j.started_at, {_NOW}) + j.budget_seconds * interval '1 second')
FROM next WHERE j.job_id = next.job_id RETURNING {', '.join('j.' + c for c in _COLS)}
"""
_BEAT = f"""
UPDATE media_render_jobs SET lease_expires_at = LEAST({_NOW} + %(lease)s * interval '1 second',
                                                       started_at + budget_seconds * interval '1 second')
WHERE job_id = %(job)s AND status = 'running' AND lease_owner = %(worker)s AND lease_expires_at > {_NOW}
"""
_DONE = f"""
UPDATE media_render_jobs SET status = 'succeeded', result = %(result)s::jsonb, finished_at = {_NOW},
    lease_owner = NULL, lease_expires_at = NULL, error_code = NULL, error_message = NULL
WHERE job_id = %(job)s AND status = 'running' AND lease_owner = %(worker)s AND lease_expires_at > {_NOW}
"""
_FAIL = f"""
UPDATE media_render_jobs SET
    status = CASE WHEN %(retry)s AND attempts < max_attempts THEN 'queued' WHEN %(retry)s THEN 'dead' ELSE 'failed' END,
    error_code = %(code)s, error_message = %(message)s,
    finished_at = CASE WHEN %(retry)s AND attempts < max_attempts THEN NULL ELSE {_NOW} END,
    lease_owner = NULL, lease_expires_at = NULL
WHERE job_id = %(job)s AND status = 'running' AND lease_owner = %(worker)s AND lease_expires_at > {_NOW}
"""


class MediaJobQueue:
    """`pool` is omni_prod.db.DatabasePool (anything with .connection() giving a psycopg connection)."""

    def __init__(self, pool, *, now: Callable[[], dt.datetime] | None = None) -> None:
        self._pool, self._now = pool, now

    def _p(self, **kw) -> dict:
        return {'now': self._now() if self._now else None, **kw}

    def _run(self, fn):
        try:
            with self._pool.connection() as conn:
                with conn.transaction():
                    return fn(conn)
        except Exception as exc:
            if 'media_render_jobs' in str(exc) and 'does not exist' in str(exc):
                raise MediaQueueError(MISSING_TABLE) from exc
            raise

    def enqueue(self, *, account_id: str, project_id: str, build_id: str, kind: str, idempotency_key: str, payload: dict,
                budget_seconds: int, max_attempts: int = 3) -> tuple[MediaJob, bool]:
        """(the job, created). The same (account, key) with the same payload returns the first job, created=False."""
        if not _KIND.fullmatch(kind or ''):
            raise ValueError('kind is a lower-case word')
        if not _KEY.fullmatch(idempotency_key or ''):
            raise ValueError('idempotency_key is 8 to 120 characters of letters, digits and ._:-')
        if not isinstance(payload, dict):
            raise ValueError('payload is a JSON object')
        if not 1 <= budget_seconds <= MAX_BUDGET_SECONDS:
            raise ValueError(f'budget_seconds is 1 to {MAX_BUDGET_SECONDS}')
        if not 1 <= max_attempts <= MAX_ATTEMPTS:
            raise ValueError(f'max_attempts is 1 to {MAX_ATTEMPTS}')
        digest = _digest(payload)
        job_id = 'mrj_' + uuid.uuid4().hex

        def go(conn):
            cur = conn.execute(
                'INSERT INTO media_render_jobs (job_id, account_id, project_id, build_id, kind, idempotency_key, payload, '
                'payload_sha256, max_attempts, budget_seconds) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s) '
                f'ON CONFLICT (account_id, idempotency_key) DO NOTHING RETURNING {_RETURNING}',
                (job_id, account_id, project_id, build_id, kind, idempotency_key, json.dumps(payload), digest,
                 max_attempts, budget_seconds))
            row = cur.fetchone()
            if row:
                return _job(row), True
            row = conn.execute(f'SELECT {_RETURNING}, payload_sha256 FROM media_render_jobs '
                               'WHERE account_id = %s AND idempotency_key = %s', (account_id, idempotency_key)).fetchone()
            if row[-1] != digest or row[4] != kind or row[2] != project_id:
                raise IdempotencyConflict('this idempotency key was used for a different request')
            return _job(row[:-1]), False
        return self._run(go)

    def claim(self, worker_id: str, *, lease_seconds: int) -> MediaJob | None:
        if not (worker_id or '').strip():
            raise ValueError('worker_id is required')
        if not 1 <= lease_seconds <= MAX_LEASE_SECONDS:
            raise ValueError(f'lease_seconds is 1 to {MAX_LEASE_SECONDS}')

        def go(conn):
            conn.execute(_REAP, self._p())
            row = conn.execute(_CLAIM, self._p(worker=worker_id, lease=lease_seconds)).fetchone()
            return _job(row) if row else None
        return self._run(go)

    def heartbeat(self, job_id: str, worker_id: str, *, lease_seconds: int) -> bool:
        if not 1 <= lease_seconds <= MAX_LEASE_SECONDS:
            raise ValueError(f'lease_seconds is 1 to {MAX_LEASE_SECONDS}')
        return self._run(lambda c: c.execute(_BEAT, self._p(job=job_id, worker=worker_id, lease=lease_seconds)).rowcount == 1)

    def complete(self, job_id: str, worker_id: str, result: dict) -> bool:
        return self._run(lambda c: c.execute(_DONE, self._p(job=job_id, worker=worker_id, result=json.dumps(result))).rowcount == 1)

    def fail(self, job_id: str, worker_id: str, *, code: str, message: str, retry: bool) -> bool:
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', code or ''):
            raise ValueError('code is a lower-case identifier')
        return self._run(lambda c: c.execute(
            _FAIL, self._p(job=job_id, worker=worker_id, code=code, message=(message or '')[:500], retry=bool(retry))).rowcount == 1)

    def get(self, *, account_id: str, job_id: str) -> MediaJob | None:
        def go(conn):
            row = conn.execute(f'SELECT {_RETURNING} FROM media_render_jobs WHERE account_id = %s AND job_id = %s',
                               (account_id, job_id)).fetchone()
            return _job(row) if row else None
        return self._run(go)


def run_one(queue: MediaJobQueue, worker_id: str, handlers: dict[str, Callable[[MediaJob], dict]], *,
            lease_seconds: int = 120) -> str | None:
    """Claim one job and run its handler; the job id, or None when the queue is empty. A kind with no handler fails the job
    out loud (no_handler), it is never skipped. A handler's exception returns the job to the queue until its attempts are
    used; a handler that returns a dict completes it. The handler gets the job (job.attempts says which try it is: a
    handler that pays a provider must key its payment by job_id, so a second try cannot pay twice)."""
    job = queue.claim(worker_id, lease_seconds=lease_seconds)
    if job is None:
        return None
    handler = handlers.get(job.kind)
    if handler is None:
        queue.fail(job.job_id, worker_id, code='no_handler', message=f'no handler for kind {job.kind!r}', retry=False)
        return job.job_id
    try:
        result = handler(job)
    except Exception as exc:   # noqa: BLE001 -- every failure is recorded, never swallowed
        queue.fail(job.job_id, worker_id, code='handler_error', message=f'{type(exc).__name__}: {exc}', retry=True)
        return job.job_id
    if not isinstance(result, dict):
        queue.fail(job.job_id, worker_id, code='handler_result', message='a handler returns a dict', retry=False)
        return job.job_id
    if not queue.complete(job.job_id, worker_id, result):
        raise MediaQueueError(f'job {job.job_id} finished after its lease ran out; the queue has already taken it back')
    return job.job_id


def drain(queue: MediaJobQueue, worker_id: str, handlers, *, max_jobs: int, lease_seconds: int = 120) -> list[str]:
    """run_one until the queue is empty or max_jobs jobs ran: a bounded loop."""
    if max_jobs < 1:
        raise ValueError('max_jobs must be at least 1')
    done = []
    for _ in range(max_jobs):
        job_id = run_one(queue, worker_id, handlers, lease_seconds=lease_seconds)
        if job_id is None:
            break
        done.append(job_id)
    return done
