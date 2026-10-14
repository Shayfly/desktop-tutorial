from __future__ import annotations

"""Relay for build_outbox rows whose Redis enqueue never happened.

Run it on a schedule (cron / systemd timer / a sidecar loop) next to the
workers:

    python -m omni_prod.build_outbox_relay            # one pass
    python -m omni_prod.build_outbox_relay --loop 15  # every 15 seconds

Needs OMNI_DATABASE_URL and OMNI_REDIS_URL. Nothing in this repository
schedules it -- that is deployment configuration (see
PATCH_APPLICATION_REPORT.md, M3 Revision 2).
"""

import argparse
import os
import sys
import time

BUILD_JOB_PATH = "omni_prod.worker_tasks.execute_live_build_job"


def relay_once(pool, redis_url: str, *, older_than_seconds: int = 30, limit: int = 100, enqueue=None) -> list[str]:
    from .job_repository import PostgresBuildRepository
    if enqueue is None:
        from .queueing import enqueue_build

        def enqueue(build_id: str) -> None:
            enqueue_build(redis_url, BUILD_JOB_PATH, build_id, job_id=build_id)

    return PostgresBuildRepository(pool).dispatch_pending_outbox(
        enqueue, older_than_seconds=older_than_seconds, limit=limit)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loop', type=float, default=0.0, help='seconds between passes (0 = single pass)')
    parser.add_argument('--older-than', type=int, default=30)
    parser.add_argument('--limit', type=int, default=100)
    args = parser.parse_args(argv)

    database_url = os.getenv('OMNI_DATABASE_URL', '').strip()
    redis_url = os.getenv('OMNI_REDIS_URL', '').strip()
    if not database_url or not redis_url:
        print('OMNI_DATABASE_URL and OMNI_REDIS_URL are required', file=sys.stderr)
        return 2

    from .db import DatabasePool
    pool = DatabasePool(database_url)
    try:
        while True:
            try:
                sent = relay_once(pool, redis_url, older_than_seconds=args.older_than, limit=args.limit)
                print(f'build_outbox_relay: dispatched {len(sent)} build(s)', flush=True)
            except Exception as exc:  # keep looping; report honestly
                print(f'build_outbox_relay: pass failed: {type(exc).__name__}: {exc}', file=sys.stderr, flush=True)
                if not args.loop:
                    return 1
            if not args.loop:
                return 0
            time.sleep(args.loop)
    finally:
        pool.close()


if __name__ == '__main__':
    raise SystemExit(main())
