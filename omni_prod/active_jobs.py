"""Read-only, FAIL-CLOSED gate: may the worker consumers be stopped right now? (founder directive 2026-10-11)

    python -m omni_prod.active_jobs [--wait-minutes N] [--poll-seconds S] [--acknowledge-stale ID[,ID...]]
                                    [--tolerate-unverified]

Exit codes
  0  verified quiet: no consumer is executing anything; draining is safe
  3  running work remains (after the optional wait)
  2  the state CANNOT BE VERIFIED (no/failed DB or Redis connection, a query or table missing, bad arguments).
     Missing information is never "quiet": it blocks the deploy exactly like running work.

What counts as running (every one blocks)
  * build_jobs.status = 'running' -- whatever its heartbeat. An old heartbeat is NOT proof that the work ended: the
    worker may be stalled or partitioned and still hold the job. Only an operator who has looked at a specific job can
    release the gate for it, with --acknowledge-stale <exact id>; the deploy workflow never passes that flag.
  * modification_requests.status = 'RUNNING'
  * intake_reservations.state IN ('CLAIMED', 'EXECUTING') (the intake consumer, even with an expired lease)
  * project_previews.status = 'STARTING' (the preview consumer is mid-launch)
  * RQ: any job in a StartedJobRegistry of omni-builds, omni-previews, omni-intake, any omni-preview-host-* queue or any
    other queue registered in Redis, and any RQ worker whose state is 'busy'.
QUEUED work (build_jobs, modifications, undelivered intake outbox rows, RQ queue length) only waits for the new worker;
it is reported, not blocking.

--tolerate-unverified (explicit; the default stays fail-closed): when, at the deadline, NOTHING blocking was seen and
EVERY error is a real connection failure, classified by exception type (OperationalError, ConnectionError,
TimeoutError, PoolTimeout, redis ConnectionError/TimeoutError -- e.g. the database is down for an hour), print a
::warning with the exact errors and exit 0. Running work still exits 3. A missing environment variable (config), a
missing table or failed query, a gate error, any other exception (TypeError, RuntimeError, KeyError ...) or bad
arguments still exit 2. Deploy build worker #127 died on exactly this: a DB outage, not running work.

Only SELECTs and Redis reads (the DB session is read-only); no model call, no write.
"""
from __future__ import annotations

import json
import os
import sys
import time

KNOWN_QUEUES = ('omni-builds', 'omni-previews', 'omni-intake')
EXIT_QUIET, EXIT_UNVERIFIED, EXIT_BUSY = 0, 2, 3
# Why a fact could not be read. Only CONNECTION may be tolerated (--tolerate-unverified); a missing environment
# variable is CONFIG, a failed/missing query is QUERY and anything else (TypeError, RuntimeError, KeyError ...) is
# LOGIC: those mean the gate itself is wrong or misconfigured, and are never "we just could not reach it".
CONNECTION, CONFIG, QUERY, LOGIC = 'connection', 'config', 'query', 'logic'


def _connection_types() -> tuple[type[BaseException], ...]:
    types: list = [ConnectionError, TimeoutError]
    for mod, names in (('psycopg', ('OperationalError',)), ('psycopg_pool', ('PoolTimeout',)),
                       ('redis.exceptions', ('ConnectionError', 'TimeoutError'))):
        try:
            m = __import__(mod, fromlist=list(names))
        except Exception:
            continue
        types += [getattr(m, n) for n in names if isinstance(getattr(m, n, None), type)]
    return tuple(types)


def classify(exc: BaseException, otherwise: str = LOGIC) -> str:
    return CONNECTION if isinstance(exc, _connection_types()) else otherwise


def only_connection_failures(snap: dict) -> bool:
    """Every error is a real connection failure (by exception type), not configuration, a query or a bug."""
    kinds = snap.get('error_kinds') or []
    return bool(kinds) and len(kinds) == len(snap.get('errors') or []) and all(k == CONNECTION for k in kinds)


def _rows(conn, sql: str, errors: list, what: str, kinds: list):
    try:
        return conn.execute(sql).fetchall()
    except Exception as exc:                                    # a failed query is missing information, never "quiet"
        errors.append(f'{what}: {type(exc).__name__}')
        kinds.append(classify(exc, QUERY))                      # a dropped connection mid-query is still CONNECTION
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def _db_part(conn, out: dict, ack: set, errors: list, kinds: list) -> None:
    builds = _rows(conn,
                   "SELECT id, status, EXTRACT(EPOCH FROM (now() - COALESCE(heartbeat_at, started_at, created_at)))::int "
                   "FROM build_jobs WHERE status IN ('queued', 'running') ORDER BY created_at", errors, 'build_jobs', kinds)
    mods = _rows(conn, "SELECT id, status FROM modification_requests WHERE status IN ('QUEUED', 'RUNNING')",
                 errors, 'modification_requests', kinds)
    intake = _rows(conn, "SELECT id, state FROM intake_reservations WHERE state IN ('RESERVED', 'CLAIMED', 'EXECUTING')",
                   errors, 'intake_reservations', kinds)
    pending = _rows(conn, 'SELECT reservation_id FROM intake_outbox WHERE enqueued_at IS NULL', errors, 'intake_outbox', kinds)
    prev = _rows(conn, "SELECT id FROM project_previews WHERE status = 'STARTING'", errors, 'project_previews', kinds)
    if builds is not None:
        running = [b for b in builds if b[1] == 'running']
        out['running_builds'] = [b[0] for b in running if b[0] not in ack]
        out['acknowledged_stale_builds'] = [b[0] for b in running if b[0] in ack]
        # informational only: which running rows also have an old heartbeat (they still block)
        out['running_builds_with_old_heartbeat'] = [b[0] for b in running if b[2] > 900 and b[0] not in ack]
        out['queued_builds'] = [b[0] for b in builds if b[1] == 'queued']
    if mods is not None:
        out['running_modifications'] = [m[0] for m in mods if m[1] == 'RUNNING']
        out['queued_modifications'] = [m[0] for m in mods if m[1] == 'QUEUED']
    if intake is not None:
        out['running_intake'] = [i[0] for i in intake if i[1] in ('CLAIMED', 'EXECUTING')]
        out['queued_intake'] = [i[0] for i in intake if i[1] == 'RESERVED']
    if pending is not None:
        out['undelivered_intake_outbox'] = [p[0] for p in pending]
    if prev is not None:
        out['starting_previews'] = [p[0] for p in prev]


def _redis_part(redis, out: dict, errors: list, kinds: list) -> None:
    if redis is None:
        errors.append('redis: OMNI_REDIS_URL is not set, RQ state cannot be read')
        kinds.append(CONFIG)
        return
    try:
        redis.ping()                                            # reachability first: its failure is CONNECTION
        from rq import Queue, Worker
        from rq.registry import StartedJobRegistry
        names = list(KNOWN_QUEUES)
        host = os.getenv('OMNI_PREVIEW_RUNTIME_HOST', '').strip()
        if host:
            from .queueing import preview_host_queue
            names.append(preview_host_queue(host))
        names += [q.name for q in Queue.all(connection=redis)]
        # A host-scoped queue is not in rq's queue set until something was enqueued on it, and this process may not
        # know OMNI_PREVIEW_RUNTIME_HOST: also discover every started-job registry by its Redis key.
        for pattern, prefix in (('rq:wip:*', 'rq:wip:'), ('rq:started:*', 'rq:started:')):
            for key in redis.scan_iter(match=pattern, count=500):
                key = key.decode() if isinstance(key, bytes) else key
                names.append(key[len(prefix):])
        rq, started = {}, []
        for name in dict.fromkeys(names):
            q = Queue(name, connection=redis)
            ids = StartedJobRegistry(queue=q).get_job_ids()
            rq[name] = {'started': len(ids), 'queued': q.count}
            started += [f'{name}:{i}' for i in ids]
        busy_workers = [w.name for w in Worker.all(connection=redis) if w.get_state() == 'busy']
        out['rq'] = rq
        out['rq_started_jobs'] = started
        out['rq_busy_workers'] = busy_workers
    except Exception as exc:
        errors.append(f'redis: {type(exc).__name__}')
        kinds.append(classify(exc))                             # RuntimeError / TypeError / KeyError ... -> LOGIC


def snapshot(conn, redis=None, acknowledge_stale=(), db_error: tuple[str, str] | None = None) -> dict:
    """`db_error` = (message, kind) when the connection could not be made (see _connect)."""
    errors: list = []
    kinds: list = []
    out: dict = {'rq': None}
    ack = set(acknowledge_stale)
    if conn is None:
        message, kind = db_error or ('db: no connection', LOGIC)
        errors.append(message)
        kinds.append(kind)
    else:
        _db_part(conn, out, ack, errors, kinds)
    _redis_part(redis, out, errors, kinds)
    blocking = []
    for key in ('running_builds', 'running_modifications', 'running_intake', 'starting_previews',
                'rq_started_jobs', 'rq_busy_workers'):
        blocking += [f'{key}:{v}' for v in out.get(key, [])]
    out['errors'] = errors
    out['error_kinds'] = kinds
    out['blocking'] = blocking
    out['busy'] = bool(blocking)
    out['unverified'] = bool(errors)
    out['safe_to_drain'] = not blocking and not errors
    return out


def _brief(snap: dict) -> dict:
    return {k: (v[:10] + [f'... +{len(v) - 10} more'] if isinstance(v, list) and len(v) > 10 else v) for k, v in snap.items()}


def _connect():
    import psycopg
    url = os.environ.get('OMNI_DATABASE_URL')
    if not url:
        return None, ('db: OMNI_DATABASE_URL is not set', CONFIG)            # configuration, not a connection failure
    try:
        conn = psycopg.connect(url, connect_timeout=10)
        conn.read_only = True                       # the whole session is read-only
        return conn, None
    except Exception as exc:
        return None, (f'db: connection failed ({type(exc).__name__})', classify(exc))


def _redis():
    url = os.environ.get('OMNI_REDIS_URL')
    if not url:
        return None
    from redis import Redis
    return Redis.from_url(url, socket_connect_timeout=10, socket_timeout=10)


def check_once(acknowledge_stale=()) -> dict:
    conn, err = _connect()
    try:
        snap = snapshot(conn, _redis(), acknowledge_stale, db_error=err)
    finally:
        if conn is not None:
            conn.close()
    return snap


def main(argv: list[str]) -> int:
    def arg(name, default):
        return argv[argv.index(name) + 1] if name in argv else default
    try:
        wait, poll = float(arg('--wait-minutes', 0.0)), float(arg('--poll-seconds', 30.0))
    except (ValueError, IndexError):
        print('::error title=active-jobs::bad arguments; NOT draining')
        return EXIT_UNVERIFIED
    ack = [x for x in str(arg('--acknowledge-stale', '')).split(',') if x]
    tolerate = '--tolerate-unverified' in argv
    deadline = time.monotonic() + wait * 60
    while True:
        try:
            snap = check_once(ack)
        except Exception as exc:                        # anything unexpected is also "cannot verify"
            snap = {'errors': [f'gate: {type(exc).__name__}'], 'error_kinds': [LOGIC], 'blocking': [], 'busy': False,
                    'unverified': True, 'safe_to_drain': False}
        print(json.dumps(_brief(snap), ensure_ascii=False))
        if snap['safe_to_drain']:
            q = len(snap.get('queued_builds', [])) + len(snap.get('queued_intake', []))
            print('::notice title=active-jobs::verified quiet; draining is safe'
                  + (f' ({q} queued items wait for the new worker)' if q else ''))
            return EXIT_QUIET
        if time.monotonic() >= deadline:
            if snap['unverified'] and tolerate and not snap['blocking'] and only_connection_failures(snap):
                print("::warning title=active-jobs::draining WITHOUT verification (--tolerate-unverified). The relief "
                      "covers ONLY not being able to know: every error is a connection failure, so the state could not "
                      "be read; it does NOT say nothing is running. No running work was seen; running work that is seen "
                      f"still refuses. Unread: {snap['errors']}")
                return EXIT_QUIET
            if snap['unverified'] and tolerate and snap['blocking']:
                print(f"::error title=active-jobs::NOT draining: running work seen while the state is only partly "
                      f"verified: {snap['blocking'][:10]}; errors: {snap['errors']}")
                return EXIT_BUSY
            if snap['unverified']:
                print(f"::error title=active-jobs::NOT draining: the state could not be verified: {snap['errors']}")
                return EXIT_UNVERIFIED
            print(f"::error title=active-jobs::NOT draining: running work remains after {wait:g} min: {snap['blocking'][:10]}")
            return EXIT_BUSY
        time.sleep(poll)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
