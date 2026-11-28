from __future__ import annotations

BUILD_QUEUE = "omni-builds"
# Preview launches need a worker with Docker access (infra/worker-host:
# preview-worker); the build worker has none, so they get their own queue.
PREVIEW_QUEUE = "omni-previews"

def redis_connection(
    redis_url: str,
    *,
    socket_timeout_seconds: float = 5.0,
    connect_timeout_seconds: float = 5.0,
):
    from redis import Redis
    return Redis.from_url(
        redis_url,
        socket_timeout=socket_timeout_seconds,
        socket_connect_timeout=connect_timeout_seconds,
        health_check_interval=30,
        retry_on_timeout=True,
        decode_responses=False,
    )

# S13.4: long media renders. The row in media_render_jobs (omni_prod/media_queue.py) is the truth; this RQ queue only
# carries the wake-up, in its own worker process, one job at a time, so a render never takes the build queue's worker.
MEDIA_QUEUE = "omni-media"

PREVIEW_HOST_QUEUE_PREFIX = "omni-preview-host-"

def preview_host_queue(runtime_host: str) -> str:
    """M3 Rev2: per-host queue for preview stop/cleanup tasks.

    A preview container and its bind-mounted source directory live on the
    worker host that launched it. A stop task picked up by any other worker
    would talk to the wrong Docker daemon and the wrong filesystem. Every
    worker that launches previews must therefore also consume its own host
    queue:  rq worker omni-builds omni-preview-host-$OMNI_PREVIEW_RUNTIME_HOST
    """
    safe = ''.join(c if (c.isalnum() or c in '-_.') else '-' for c in runtime_host.strip())
    if not safe:
        raise ValueError('runtime_host is required for a host-scoped queue')
    return PREVIEW_HOST_QUEUE_PREFIX + safe[:120]

# The time a build may take, in one place (the owner, 2026-11-16: "the worker dies in the middle of a build").
# Production, 2026-11-16: bld_426addd3 and bld_0e142230 were both killed 15 minutes after they started -- the queue's
# 900-second job timeout -- in repair round 5-6, with no terminal state written: the customer watched a build that
# "stopped responding" until the 45-minute janitor failed it as worker_lost. A build now ends ITSELF, in order:
#   BUILD_REPAIR_UNTIL_SECONDS   no new repair round starts after this; the best version so far is judged as usual
#   BUILD_STOP_AT_SECONDS        the next step boundary raises BuildDeadline: FAILED build_timeout, settled, said
#   BUILD_JOB_TIMEOUT_SECONDS    the queue's own limit, the last resort; it must never be the one that ends a build
# The longest accepted build of 2026-11-13..15 took 8:57 (3 repair rounds); the repair budget leaves 4 minutes more.
BUILD_REPAIR_UNTIL_SECONDS = 780
BUILD_STOP_AT_SECONDS = 1020
BUILD_JOB_TIMEOUT_SECONDS = 1200
if not 0 < BUILD_REPAIR_UNTIL_SECONDS < BUILD_STOP_AT_SECONDS < BUILD_JOB_TIMEOUT_SECONDS - 120:
    raise RuntimeError('build time budget out of order: repair < stop < job timeout - 120 s')


def queue(redis_url: str, queue_name: str = BUILD_QUEUE, **redis_kwargs):
    from rq import Queue
    return Queue(
        queue_name,
        connection=redis_connection(redis_url, **redis_kwargs),
        default_timeout=BUILD_JOB_TIMEOUT_SECONDS,
    )

def enqueue_build(
    redis_url: str,
    func_path: str,
    *args,
    timeout: int = BUILD_JOB_TIMEOUT_SECONDS,
    job_id: str | None = None,
    queue_name: str = BUILD_QUEUE,
    **redis_kwargs,
):
    # M3: widened from a single `payload` positional to `*args` so this one
    # queue/helper can dispatch to jobs that take more than one plain
    # argument (execute_preview_launch(preview_id, project_id, version_id)),
    # not just the single-value payload M1's execute_live_build_job(build_id)
    # needed. Backward compatible: enqueue_build(url, path, build_id,
    # job_id=...) still enqueues exactly one arg, same as before.
    # M3 Rev2: optional queue_name (default unchanged) for host-scoped
    # preview cleanup -- see preview_host_queue().
    q = queue(redis_url, queue_name, **redis_kwargs)
    return q.enqueue(
        func_path,
        *args,
        job_timeout=timeout,
        job_id=job_id,
        result_ttl=86400,
        failure_ttl=604800,
    )

def ping(redis_url: str, **redis_kwargs) -> bool:
    try:
        return bool(redis_connection(redis_url, **redis_kwargs).ping())
    except Exception:
        return False
