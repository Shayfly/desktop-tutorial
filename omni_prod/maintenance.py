"""Host maintenance loop (runs as the `janitor` service on the worker host).

Two gaps found during Golden E2E #1 (2026-10-07/08):

1. Previews: `mark_expired()` existed but nothing called it, and an expired
   preview's container kept running until someone sent a DELETE. Every pass
   marks expired previews and removes the containers of EXPIRED/STOPPED
   previews on this host (the same `stop_preview_task` a DELETE uses).
2. Builds: a build whose worker died stayed RUNNING forever with its credits
   reserved (bld_2f248e2339cb4ad9848a7ebb5c0c4ed6). Builds RUNNING longer than
   the stale limit (default 45 minutes; the job timeout is 15) are moved to
   FAILED with error `worker_lost`, and their reservation is released.

3. Lost queue entries (post-deploy check 2026-10-09): a job pushed while the
   build worker was stopped (deploy drain) can be taken by the stopped
   worker's still-open blocking read on the serverless Redis and is then
   gone; the build stayed QUEUED with its credits reserved
   (bld_a99ca1119c8f445aa4f6243c330d6a46). A build or change that is still
   QUEUED after a few minutes and whose id is no longer in its queue is
   dispatched again. Safe: the worker's QUEUED -> RUNNING claim is
   conditional, so a duplicate delivery is a no-op.

4. Crash recovery (autonomous completion §5): a RUNNING build or change whose
   worker heartbeat (written at every step boundary) is older than
   OMNI_LOST_RUNNING_MINUTES and which no live worker reports as its current
   job lost its worker. A stop request ends it CANCELLED; otherwise it is put
   back in the queue once (recovery_attempts) and failed with `worker_lost`
   after that. Reservations are released for anything that ends.

Each step is independent and logged; one failing step never stops the loop.
"""
from __future__ import annotations

import os
import time

STALE_BUILD_MINUTES = int(os.getenv('OMNI_STALE_BUILD_MINUTES', '45'))
INTERVAL_SECONDS = int(os.getenv('OMNI_MAINTENANCE_INTERVAL_SECONDS', '60'))
LOST_QUEUED_MINUTES = int(os.getenv('OMNI_LOST_QUEUED_MINUTES', '3'))
LOST_RUNNING_MINUTES = int(os.getenv('OMNI_LOST_RUNNING_MINUTES', '15'))
MAX_RECOVERY = 1

BUILD_JOB = 'omni_prod.worker_tasks.execute_live_build_job'
MODIFICATION_JOB = 'omni_prod.worker_tasks.execute_modification_job'


def _say(msg: str) -> None:
    print(time.strftime('%H:%M:%S ') + msg, flush=True)


def previews_to_clean(pool, runtime_host: str) -> list[str]:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM project_previews WHERE status IN ('EXPIRED', 'STOPPED') "
                        "AND cleaned_at IS NULL AND runtime_host = %s ORDER BY id LIMIT 50", (runtime_host,))
            return [r[0] for r in cur.fetchall()]


def stale_builds(pool, minutes: int) -> list[str]:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM build_jobs WHERE status = 'running' "
                        "AND COALESCE(started_at, created_at) < now() - make_interval(mins => %s) ORDER BY id LIMIT 50",
                        (int(minutes),))
            return [r[0] for r in cur.fetchall()]


def reap_build(jobs, subscriptions, build_id: str, minutes: int) -> bool:
    from .models import BuildStatus
    moved = jobs.transition(
        build_id=build_id, expected=BuildStatus.RUNNING, target=BuildStatus.FAILED, error_code='worker_lost',
        error_message=f'the build stopped responding for more than {minutes} minutes; '
                      'provider exposure must be reconciled before funds can be released',
        evidence_json={'billing': 'exposure_checked_release', 'reaped_by': 'maintenance', 'stale_minutes': minutes})
    if moved:
        subscriptions.release(build_id=build_id)
    return bool(moved)


def queued_too_long(pool, minutes: int) -> list[tuple[str, str]]:
    """(job function, id) of builds and changes still QUEUED after `minutes`."""
    with pool.connection() as conn:
        with conn.cursor() as cur:
            # Only recent work: a row queued for hours is not "lost in a deploy"
            # and must not be re-sent every minute forever.
            cur.execute("SELECT id FROM build_jobs WHERE status = 'queued' AND cancel_requested_at IS NULL "
                        "AND created_at < now() - make_interval(mins => %s) AND created_at > now() - interval '6 hours' "
                        "ORDER BY created_at LIMIT 20", (int(minutes),))
            builds = [(BUILD_JOB, r[0]) for r in cur.fetchall()]
            cur.execute("SELECT id FROM modification_requests WHERE status = 'QUEUED' "
                        "AND created_at < now() - make_interval(mins => %s) AND created_at > now() - interval '6 hours' "
                        "ORDER BY created_at LIMIT 20", (int(minutes),))
            changes = [(MODIFICATION_JOB, r[0]) for r in cur.fetchall()]
    return builds + changes


_REDISPATCHED: dict[str, int] = {}
MAX_REDISPATCH = 3


def redispatch_lost(pool, *, queued_ids, enqueue, minutes: int = LOST_QUEUED_MINUTES,
                    attempts: dict | None = None) -> list[str]:
    """Re-enqueue QUEUED work whose id is no longer waiting in the queue.
    `queued_ids()` returns the ids currently in the build queue (and being
    worked on); `enqueue(func, id)` dispatches with job_id=id. Each id is sent
    again at most MAX_REDISPATCH times by this process."""
    attempts = _REDISPATCHED if attempts is None else attempts
    waiting = set(queued_ids())
    sent = []
    for func, item in queued_too_long(pool, minutes):
        if item in waiting or attempts.get(item, 0) >= MAX_REDISPATCH:
            continue  # still in line behind another job, or given up on
        enqueue(func, item)
        attempts[item] = attempts.get(item, 0) + 1
        sent.append(item)
    return sent


_LOST = {
    'build': ("SELECT id, cancel_requested_at IS NOT NULL, recovery_attempts FROM build_jobs WHERE status = 'running' "
              "AND heartbeat_at IS NOT NULL AND heartbeat_at < now() - make_interval(mins => %s) LIMIT 20"),
    'modification': ("SELECT id, cancel_requested_at IS NOT NULL, recovery_attempts FROM modification_requests "
                     "WHERE status = 'RUNNING' AND heartbeat_at IS NOT NULL "
                     "AND heartbeat_at < now() - make_interval(mins => %s) LIMIT 20"),
}
_END = {
    'build': ("UPDATE build_jobs SET status = %s, phase = UPPER(%s), finished_at = now(), error_code = %s, "
              "error_message = %s WHERE id = %s AND status = 'running'"),
    'modification': ("UPDATE modification_requests SET status = UPPER(%s), completed_at = now(), error_code = %s, "
                     "error_message = %s WHERE id = %s AND status = 'RUNNING'"),
}
_REQUEUE = {
    'build': ("UPDATE build_jobs SET status = 'queued', phase = 'RECOVERING', heartbeat_at = NULL, "
              "recovery_attempts = recovery_attempts + 1 WHERE id = %s AND status = 'running' "
              "AND heartbeat_at < now() - make_interval(mins => %s)"),
    'modification': ("UPDATE modification_requests SET status = 'QUEUED', heartbeat_at = NULL, "
                     "recovery_attempts = recovery_attempts + 1 WHERE id = %s AND status = 'RUNNING' "
                     "AND heartbeat_at < now() - make_interval(mins => %s)"),
}


def recover_lost_running(pool, *, subscriptions, enqueue, busy_ids=lambda: (), minutes: int = LOST_RUNNING_MINUTES,
                         max_recovery: int = MAX_RECOVERY) -> dict:
    """Crash recovery for builds and changes whose worker disappeared."""
    out = {'recovered': [], 'cancelled': [], 'failed': []}
    busy = set(busy_ids())
    for kind in ('build', 'modification'):
        with pool.connection() as conn:
            rows = conn.execute(_LOST[kind], (int(minutes),)).fetchall()
        for item, stop, attempts in rows:
            if item in busy:
                continue  # a live worker still has it: slow, not lost
            with pool.connection() as conn:
                with conn.transaction():
                    # Serialize against the mandatory pre-provider journal.
                    table = 'build_jobs' if kind == 'build' else 'modification_requests'
                    active_state = 'running' if kind == 'build' else 'RUNNING'
                    current = conn.execute(f'SELECT cancel_requested_at IS NOT NULL, recovery_attempts FROM {table} '
                                           'WHERE id=%s AND status=%s AND heartbeat_at IS NOT NULL '
                                           'AND heartbeat_at < now() - make_interval(mins => %s) FOR UPDATE',
                                           (item, active_state, int(minutes))).fetchone()
                    if current is None:
                        continue
                    stop, attempts = current
                    from .subscription_store import provider_exposure
                    with conn.cursor() as cur:
                        exposed = provider_exposure(cur, item)
                    if exposed:
                        done = _end(conn, kind, item, 'failed', 'provider_liability_unknown',
                                    'worker lost after provider activity; reservation held for reconciliation')
                        bucket, message = 'failed', 'העבודה נעצרה. חשיפת הספק נשמרת עד בירור החיוב.'
                    elif stop:
                        done = _end(conn, kind, item, 'cancelled', 'cancelled_by_user',
                                    'stopped on request; its worker had stopped responding')
                        bucket, message = 'cancelled', 'הבנייה נעצרה לבקשתך.'
                    elif attempts < max_recovery:
                        done = conn.execute(_REQUEUE[kind], (item, int(minutes))).rowcount == 1
                        bucket, message = 'recovered', 'השרת שעבד על זה הפסיק להגיב. מתחיל מחדש מהתחלה.'
                    else:
                        done = _end(conn, kind, item, 'failed', 'worker_lost',
                                    f'the worker stopped responding for more than {minutes} minutes twice; '
                                    'the reservation was released')
                        bucket, message = 'failed', 'השרת הפסיק להגיב פעמיים. העבודה נעצרה והקרדיטים שוחררו.'
                    if done:
                        conn.execute("INSERT INTO build_events(build_id, kind, message, job_kind) VALUES (%s, 'info', %s, %s)",
                                     (item, message, kind))
            if not done:
                continue
            out[bucket].append(item)
            if bucket == 'recovered':
                enqueue(BUILD_JOB if kind == 'build' else MODIFICATION_JOB, item)
            else:
                subscriptions.release(build_id=item)
    return out


def _end(conn, kind, item, status, code, message) -> bool:
    if kind == 'build':
        return conn.execute(_END['build'], (status, status, code, message, item)).rowcount == 1
    return conn.execute(_END['modification'], (status, code, message, item)).rowcount == 1


def run_once(*, pool, preview_repo, jobs, subscriptions, stop_preview, runtime_host: str,
             queued_ids=None, enqueue=None, busy_ids=None) -> dict:
    out = {'expired': 0, 'cleaned': 0, 'reaped': 0, 'redispatched': [], 'recovery': None, 'errors': []}
    try:
        out['expired'] = preview_repo.mark_expired()
    except Exception as exc:
        out['errors'].append(f'mark_expired: {type(exc).__name__}: {exc}')
    try:
        for pid in previews_to_clean(pool, runtime_host):
            try:
                stop_preview(pid); out['cleaned'] += 1
            except Exception as exc:
                out['errors'].append(f'clean {pid}: {type(exc).__name__}: {exc}')
    except Exception as exc:
        out['errors'].append(f'previews_to_clean: {type(exc).__name__}: {exc}')
    try:
        for bid in stale_builds(pool, STALE_BUILD_MINUTES):
            try:
                out['reaped'] += reap_build(jobs, subscriptions, bid, STALE_BUILD_MINUTES)
            except Exception as exc:
                out['errors'].append(f'reap {bid}: {type(exc).__name__}: {exc}')
    except Exception as exc:
        out['errors'].append(f'stale_builds: {type(exc).__name__}: {exc}')
    if queued_ids is not None and enqueue is not None:
        try:
            out['redispatched'] = redispatch_lost(pool, queued_ids=queued_ids, enqueue=enqueue)
        except Exception as exc:
            out['errors'].append(f'redispatch: {type(exc).__name__}: {exc}')
        try:
            rec = recover_lost_running(pool, subscriptions=subscriptions, enqueue=enqueue,
                                       busy_ids=busy_ids or (lambda: ()))
            out['recovery'] = rec if any(rec.values()) else None
        except Exception as exc:
            out['errors'].append(f'recovery: {type(exc).__name__}: {exc}')
    return out


def recover_now(minutes: int) -> dict:
    """One recovery pass with a custom staleness limit (crash-recovery test)."""
    from .investor_app import _v28, _v28_pool
    from .queueing import BUILD_QUEUE, enqueue_build, queue, redis_connection
    from rq import Worker
    redis_url = os.environ['OMNI_REDIS_URL']

    def busy():
        return [w.get_current_job_id() for w in Worker.all(connection=redis_connection(redis_url))
                if w.get_current_job_id()]
    return recover_lost_running(_v28_pool, subscriptions=_v28.subscriptions,
                                enqueue=lambda f, i: enqueue_build(redis_url, f, i, job_id=i),
                                busy_ids=busy, minutes=minutes)


def main():
    from .investor_app import _v28, _v28_pool
    from .job_repository import PostgresBuildRepository
    from .preview_repository import PostgresPreviewRepository
    from .worker_tasks import preview_runtime_host, stop_preview_task
    if _v28_pool is None:
        raise RuntimeError('maintenance requires OMNI_CREATOR_PERSISTENCE=postgres')
    host = preview_runtime_host()
    from .queueing import BUILD_QUEUE, enqueue_build, queue
    redis_url = os.getenv('OMNI_REDIS_URL', '')

    def queued_ids():
        from rq.registry import StartedJobRegistry
        q = queue(redis_url, BUILD_QUEUE)
        return list(q.job_ids) + list(StartedJobRegistry(queue=q).get_job_ids())

    def enqueue(func, item):
        enqueue_build(redis_url, func, item, job_id=item)

    def busy_ids():
        from rq import Worker
        from .queueing import redis_connection
        ids = []
        for w in Worker.all(connection=redis_connection(redis_url)):
            try:
                jid = w.get_current_job_id()
            except Exception:
                jid = None
            if jid:
                ids.append(jid)
        return ids

    deps = dict(pool=_v28_pool, preview_repo=PostgresPreviewRepository(_v28_pool),
                jobs=PostgresBuildRepository(_v28_pool), subscriptions=_v28.subscriptions,
                stop_preview=stop_preview_task, runtime_host=host,
                queued_ids=queued_ids if redis_url else None, enqueue=enqueue if redis_url else None,
                busy_ids=busy_ids if redis_url else None)
    _say(f'maintenance started: host {host}, every {INTERVAL_SECONDS}s, stale builds after {STALE_BUILD_MINUTES} min')
    while True:
        result = run_once(**deps)
        if (result['expired'] or result['cleaned'] or result['reaped'] or result['redispatched']
                or result['recovery'] or result['errors']):
            _say(f"expired={result['expired']} cleaned={result['cleaned']} reaped={result['reaped']} "
                 f"redispatched={result['redispatched']} recovery={result['recovery']} errors={result['errors'][:3]}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
