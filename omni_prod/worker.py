"""RQ build worker entrypoint (runs on the worker host, see infra/worker-host).

Three choices here come from live evidence on the staging worker host
(STATUS.md, 2026-10-07):

* No RQ scheduler. Nothing in 148AI uses enqueue_at / enqueue_in or interval
  retries, and RQ's scheduler polls Redis every second (about 4 commands per
  second, ~10M per month). On a metered Redis such as Upstash (free tier:
  500K commands per month) that alone exhausts the quota in days.

* A bounded dequeue wait. RQ blocks in BLMOVE for worker_ttl - 15 seconds
  (405 s by default). A shorter wait bounds how long a stale blocked request
  can hold the queue and keeps idle traffic predictable: about 4 commands per
  wait cycle (heartbeat + BLMOVE), ~86K per month at the default 120 s.

* Stale-consumer absorption at start-up. After a deploy replaced the worker
  container, a probe job enqueued seconds later was moved out of the queue
  but never executed, while the same probe against the running worker passed.
  The likely cause is the previous container's blocked BLMOVE still being
  registered on the server after the container was torn down, which then
  takes the next pushed job. Before consuming, the worker pushes a decoy id
  (no job behind it) to the front of the queue; if something else takes it
  within a short window, a stale consumer existed and has been satisfied. RQ
  skips ids without a job and its intermediate-queue cleanup removes them.
  Decoys that nobody takes are removed again.
"""
from __future__ import annotations

import os
import time
import uuid

QUEUE_NAME = "omni-builds"
DEFAULT_WORKER_TTL_SECONDS = 135          # BLMOVE wait = ttl - 15 = 120 s
MIN_WORKER_TTL_SECONDS = 30
DECOY_PREFIX = "omni-stale-consumer-absorber:"


def _say(message: str) -> None:
    # Plain stdout in RQ's own log format; logging.basicConfig would duplicate
    # every RQ log line through the root logger.
    print(time.strftime("%H:%M:%S") + " " + message, flush=True)


def worker_ttl_from_env(env=os.environ) -> int:
    raw = str(env.get("OMNI_WORKER_TTL_SECONDS", "")).strip()
    if not raw:
        return DEFAULT_WORKER_TTL_SECONDS
    try:
        value = int(raw)
    except ValueError:
        raise RuntimeError("OMNI_WORKER_TTL_SECONDS must be an integer number of seconds") from None
    if value < MIN_WORKER_TTL_SECONDS:
        raise RuntimeError(f"OMNI_WORKER_TTL_SECONDS must be at least {MIN_WORKER_TTL_SECONDS}")
    return value


def absorb_stale_consumers(conn, queue_key: str, *, wait_seconds: float = 2.0, max_rounds: int = 3,
                           sleep=time.sleep) -> int:
    """Satisfy blocked consumers left behind by a previous worker.

    Returns how many stale consumers took a decoy. Must run before this
    worker starts consuming, otherwise the worker itself would take a decoy.
    """
    absorbed = 0
    for _ in range(max_rounds):
        decoy = DECOY_PREFIX + uuid.uuid4().hex
        conn.lpush(queue_key, decoy)
        sleep(wait_seconds)
        if conn.lpos(queue_key, decoy) is not None:
            conn.lrem(queue_key, 1, decoy)
            break
        absorbed += 1
    return absorbed


def main():
    from redis import Redis
    from rq import Queue, Worker

    conn = Redis.from_url(os.environ["OMNI_REDIS_URL"])
    ttl = worker_ttl_from_env()
    queue = Queue(QUEUE_NAME, connection=conn)
    absorbed = absorb_stale_consumers(conn, queue.key)
    _say(f"stale consumers absorbed before start: {absorbed}")
    worker = Worker([queue], connection=conn, worker_ttl=ttl)
    _say(f"worker ttl {ttl}s, dequeue wait {worker.dequeue_timeout}s, scheduler disabled")
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
