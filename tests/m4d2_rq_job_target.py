"""Real job bodies for M4D.2's live Redis/RQ worker tests
(tests/test_m4d2_live_fastapi_redis.py::LiveRedisRQTests). Kept in their
own importable module (rather than nested inside the test file) because
`rq.Worker` resolves a job's `func_path` by dotted import in the WORKER
process, which for `rq.Worker.work(burst=True)` is this same process but
must still be able to `import tests.m4d2_rq_job_target` fresh -- a
function defined inline in the test file or a closure is not importable
by dotted path and would fail with a real (and correct) rq error, not a
fake pass.

Each function opens its OWN short-lived psycopg connection rather than
reusing any pool object from the enqueuing process, because a real queued
job's function only ever receives the plain arguments it was enqueued
with (see omni_prod.queueing.enqueue_build) -- exactly like the real
production job `omni_prod.worker_tasks.execute_modification_job`, which
also opens its own connection via lazy imports rather than receiving one
from the API process.
"""
from __future__ import annotations

import os

DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')


def mark_done(marker: str) -> str:
    import psycopg
    conn = psycopg.connect(DATABASE_URL)
    try:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO m4d2_rq_markers(marker) VALUES (%s) ON CONFLICT (marker) DO NOTHING", (marker,))
    finally:
        conn.close()
    return f'marked {marker}'


def always_fails(_arg: str) -> None:
    raise RuntimeError('M4D.2 intentional worker-failure-recovery test job')
