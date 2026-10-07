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

Each step is independent and logged; one failing step never stops the loop.
"""
from __future__ import annotations

import os
import time

STALE_BUILD_MINUTES = int(os.getenv('OMNI_STALE_BUILD_MINUTES', '45'))
INTERVAL_SECONDS = int(os.getenv('OMNI_MAINTENANCE_INTERVAL_SECONDS', '60'))


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
        error_message=f'the build stopped responding for more than {minutes} minutes and was released; '
                      'no credits were charged',
        evidence_json={'billing': 'released', 'reaped_by': 'maintenance', 'stale_minutes': minutes})
    if moved:
        subscriptions.release(build_id=build_id)
    return bool(moved)


def run_once(*, pool, preview_repo, jobs, subscriptions, stop_preview, runtime_host: str) -> dict:
    out = {'expired': 0, 'cleaned': 0, 'reaped': 0, 'errors': []}
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
    return out


def main():
    from .investor_app import _v28, _v28_pool
    from .job_repository import PostgresBuildRepository
    from .preview_repository import PostgresPreviewRepository
    from .worker_tasks import preview_runtime_host, stop_preview_task
    if _v28_pool is None:
        raise RuntimeError('maintenance requires OMNI_CREATOR_PERSISTENCE=postgres')
    host = preview_runtime_host()
    deps = dict(pool=_v28_pool, preview_repo=PostgresPreviewRepository(_v28_pool),
                jobs=PostgresBuildRepository(_v28_pool), subscriptions=_v28.subscriptions,
                stop_preview=stop_preview_task, runtime_host=host)
    _say(f'maintenance started: host {host}, every {INTERVAL_SECONDS}s, stale builds after {STALE_BUILD_MINUTES} min')
    while True:
        result = run_once(**deps)
        if result['expired'] or result['cleaned'] or result['reaped'] or result['errors']:
            _say(f"expired={result['expired']} cleaned={result['cleaned']} reaped={result['reaped']} "
                 f"errors={result['errors'][:3]}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
