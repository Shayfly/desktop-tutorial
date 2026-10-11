"""Read-only gate: is any customer job RUNNING right now? (founder directive 2026-10-11, safe deployment)

    python -m omni_prod.active_jobs [--wait-minutes N] [--poll-seconds S]

Exit 0 = nothing is running, a deploy may drain; exit 3 = running work remained after the wait. Only SELECTs and
Redis reads; no model call, no write. QUEUED work is only reported: it waits in the queue and the new worker takes it,
so it is not interrupted. A RUNNING build whose heartbeat is older than STALE_SECONDS is listed separately as `stale`
(a crashed worker) and does not block, because waiting for it would never end; the drain then reports its fate.
"""
from __future__ import annotations

import json
import os
import sys
import time

STALE_SECONDS = 900


def snapshot(conn, redis=None) -> dict:
    builds = conn.execute(
        "SELECT id, status, phase, EXTRACT(EPOCH FROM (now() - COALESCE(heartbeat_at, started_at, created_at)))::int "
        "FROM build_jobs WHERE status IN ('queued', 'running') ORDER BY created_at").fetchall()
    mods = conn.execute("SELECT id, status FROM modification_requests WHERE status IN ('QUEUED', 'RUNNING')").fetchall()
    running = [b for b in builds if b[1] == 'running' and b[3] <= STALE_SECONDS]
    stale = [b for b in builds if b[1] == 'running' and b[3] > STALE_SECONDS]
    out = {'running_builds': [b[0] for b in running], 'stale_running_builds': [b[0] for b in stale],
           'queued_builds': [b[0] for b in builds if b[1] == 'queued'],
           'running_modifications': [m[0] for m in mods if m[1] == 'RUNNING'],
           'queued_modifications': [m[0] for m in mods if m[1] == 'QUEUED'], 'rq': None}
    if redis is not None:
        try:
            from rq.registry import StartedJobRegistry
            from rq import Queue
            rq = {}
            for name in ('omni-builds', 'omni-previews'):
                q = Queue(name, connection=redis)
                rq[name] = {'started': len(StartedJobRegistry(queue=q).get_job_ids()), 'queued': q.count}
            out['rq'] = rq
        except Exception as exc:  # reported, never hidden
            out['rq'] = f'unavailable: {type(exc).__name__}'
    out['busy'] = bool(out['running_builds'] or out['running_modifications']
                       or (isinstance(out['rq'], dict) and any(v['started'] for v in out['rq'].values())))
    return out


def main(argv: list[str]) -> int:
    import psycopg
    wait = float(argv[argv.index('--wait-minutes') + 1]) if '--wait-minutes' in argv else 0.0
    poll = float(argv[argv.index('--poll-seconds') + 1]) if '--poll-seconds' in argv else 30.0
    redis = None
    if os.getenv('OMNI_REDIS_URL'):
        from redis import Redis
        redis = Redis.from_url(os.environ['OMNI_REDIS_URL'])
    deadline = time.monotonic() + wait * 60
    while True:
        with psycopg.connect(os.environ['OMNI_DATABASE_URL'], connect_timeout=10) as conn:
            conn.read_only = True            # the whole session is read-only
            snap = snapshot(conn, redis)
        brief = {k: (v[:10] + [f'... +{len(v) - 10} more'] if isinstance(v, list) and len(v) > 10 else v) for k, v in snap.items()}
        print(json.dumps(brief, ensure_ascii=False))
        if not snap['busy']:
            print('::notice title=active-jobs::no running job; draining is safe'
                  + (f" (queued builds: {len(snap['queued_builds'])} will wait for the new worker)" if snap['queued_builds'] else ''))
            return 0
        if time.monotonic() >= deadline:
            print(f"::error title=active-jobs::NOT draining: running work remains after {wait:g} min "
                  f"(builds={snap['running_builds']} modifications={snap['running_modifications']} rq={snap['rq']})")
            return 3
        time.sleep(poll)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
