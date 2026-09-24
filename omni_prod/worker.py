from __future__ import annotations
import os

def main():
    from redis import Redis
    from rq import Worker
    url = os.environ["OMNI_REDIS_URL"]
    conn = Redis.from_url(url)
    worker = Worker(["omni-builds"], connection=conn)
    worker.work(with_scheduler=True)

if __name__ == "__main__":
    main()
