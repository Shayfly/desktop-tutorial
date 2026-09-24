from __future__ import annotations

BUILD_QUEUE = "omni-builds"

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

def queue(redis_url: str, **redis_kwargs):
    from rq import Queue
    return Queue(
        BUILD_QUEUE,
        connection=redis_connection(redis_url, **redis_kwargs),
        default_timeout=900,
    )

def enqueue_build(
    redis_url: str,
    func_path: str,
    payload: dict,
    *,
    timeout: int = 900,
    job_id: str | None = None,
    **redis_kwargs,
):
    q = queue(redis_url, **redis_kwargs)
    return q.enqueue(
        func_path,
        payload,
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
