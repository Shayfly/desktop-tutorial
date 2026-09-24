"""Standalone real `rq.Worker` process for M4D.2b directive item 3
("EXECUTE THE ACTUAL RQ PRODUCTION JOB" -- "If possible, additionally
start a clean rq.Worker in a separate process that creates its own
database connections after process startup").

Run as: python3 tests/m4d2b_worker_process.py <burst-timeout-seconds>
(a genuinely separate OS process, via subprocess -- not a thread and not
the test process itself), with the environment variables below already
set by the caller. Exits 0 after `rq.Worker([queue]).work(burst=True)`
drains the queue (or immediately if it was already empty).

Why this avoids the fork-after-open-pool SSL-socket-corruption hazard
that forced M4D.2 (section G) to use `rq.SimpleWorker` in-process:
`rq.Worker`'s default `work()` forks a child ("work horse") per job via
`os.fork()` (rq/worker/worker_classes.py::Worker.fork_work_horse). The
hazard is forking a process that already holds a LIVE (already-connected)
psycopg SSL socket -- both parent and child end up sharing the
underlying file descriptor, and the next real query on either side gets
`SSL SYSCALL error: EOF detected`. That happened in M4D.2's tests because
the test PROCESS had already made real HTTP/DB calls (opening real pool
connections) before calling `.work()` in that same process.

This script imports `omni_prod.investor_app` in the PARENT, before
`.work()` is ever called, specifically to override `_v28.engine.workspace`
to a real `PostgresProjectWorkspace` (see below) -- but this stays safe
because `omni_prod.db.DatabasePool` never opens the underlying
`psycopg_pool.ConnectionPool` eagerly (`DatabasePool.open()` is only
called lazily, on first real `.connection()` use -- see
omni_prod/db.py). Neither importing `investor_app` (which only
*constructs* `DatabasePool(database_url)`) nor constructing
`PostgresProjectWorkspace(pool, artifact_store)` touches the network, so
there is still no live socket open in this parent process at fork time.
The actual first real connection open happens inside the FORKED CHILD,
the first time the job body calls `jobs.get_request(...)` --
i.e. `execute_modification_job`'s own dotted-import + first DB call, both
of which happen only after `os.fork()`, per
rq/worker/worker_classes.py::Worker.fork_work_horse ->
rq/worker/base.py::BaseWorker.main_work_horse -> perform_job ->
job.perform(). Each forked child therefore opens its OWN fresh
connection pool; nothing is inherited from the parent. This was verified
by empirically running this exact script against real jobs (see
PATCH_APPLICATION_REPORT.md's M4D.2b section) -- not merely reasoned
about.

Required environment variables (all set by the calling test before this
is launched via subprocess):
  OMNI_CREATOR_PERSISTENCE=postgres
  OMNI_DATABASE_URL
  OMNI_REDIS_URL
  OMNI_ENABLE_LIVE_BUILD=1
  OMNI_LOCAL_MODEL_URL      (points at the real local test model server)
  OMNI_SECRET_KEY
  OMNI_BILLING_ADMIN_KEY
  M4D2B_ARTIFACT_ROOT       (real directory; must match the directory the
                             API/test process used to seed the version's
                             repository content via the same
                             DiskArtifactStore interface)
  PYTHONPATH                (the exact-parity vendor directory)
"""
from __future__ import annotations

import sys


def main() -> int:
    import os

    burst_timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0

    import redis
    import rq

    # The one deliberate, disclosed override -- see module docstring for
    # why this is safe to do in the parent before .work() is called.
    import omni_prod.investor_app as iapp
    from omni_prod.workspace import PostgresProjectWorkspace
    from tests.test_m4d2_live_postgres import DiskArtifactStore

    assert iapp._v28_pool is not None, 'OMNI_CREATOR_PERSISTENCE=postgres must have wired a real DatabasePool'
    artifact_root = os.environ['M4D2B_ARTIFACT_ROOT']
    iapp._v28.engine.workspace = PostgresProjectWorkspace(iapp._v28_pool, DiskArtifactStore(artifact_root))

    from omni_prod.queueing import BUILD_QUEUE, redis_connection

    redis_url = os.environ['OMNI_REDIS_URL']
    conn = redis_connection(redis_url)
    queue = rq.Queue(BUILD_QUEUE, connection=conn)
    worker = rq.Worker([queue], connection=conn, name=f'm4d2b-separate-{os.getpid()}')
    # Real default Worker -- forks a child ("work horse") per job. burst=True:
    # process everything currently queued, then exit.
    ran = worker.work(burst=True, max_idle_time=burst_timeout)
    print(f'M4D2B_WORKER_PROCESS_DONE ran={ran} pid={os.getpid()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
