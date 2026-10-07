"""Worker entrypoint: no RQ scheduler, bounded dequeue wait, stale-consumer
absorption before consuming (live evidence 2026-10-07, see omni_prod/worker.py).

Stdlib only: redis and rq are replaced by recording fakes, so this runs where
the real packages are not installable. The real-Redis reproduction (a frozen
blocked consumer steals the next job from a plain RQ worker; the entrypoint
absorbs it and the probe job is executed) is recorded in STATUS.md.
"""
import sys
import types
import unittest
from unittest import mock

from omni_prod import worker


class FakeList:
    """Redis list ops on one key; `stale` decoys get taken by a stale consumer."""

    def __init__(self, stale: int = 0):
        self.items, self.stale, self.calls = [], stale, []

    def lpush(self, key, value):
        self.calls.append(("lpush", key))
        self.items.insert(0, value)
        if self.stale:
            self.stale -= 1
            self.items.pop(0)            # a blocked stale consumer takes it at once

    def lpos(self, key, value):
        return self.items.index(value) if value in self.items else None

    def lrem(self, key, count, value):
        self.calls.append(("lrem", key))
        self.items.remove(value)


class WorkerTTLTests(unittest.TestCase):
    def test_default_bounds_the_dequeue_wait(self):
        self.assertEqual(worker.worker_ttl_from_env({}), 135)

    def test_env_override(self):
        self.assertEqual(worker.worker_ttl_from_env({"OMNI_WORKER_TTL_SECONDS": "75"}), 75)

    def test_invalid_values_fail_explicitly(self):
        for raw in ("abc", "10"):
            with self.assertRaises(RuntimeError):
                worker.worker_ttl_from_env({"OMNI_WORKER_TTL_SECONDS": raw})


class StaleConsumerTests(unittest.TestCase):
    def test_no_stale_consumer_leaves_the_queue_unchanged(self):
        conn = FakeList(stale=0)
        conn.items = ["real-job"]
        self.assertEqual(worker.absorb_stale_consumers(conn, "rq:queue:omni-builds", sleep=lambda s: None), 0)
        self.assertEqual(conn.items, ["real-job"])
        self.assertEqual(conn.calls, [("lpush", "rq:queue:omni-builds"), ("lrem", "rq:queue:omni-builds")])

    def test_one_stale_consumer_is_absorbed(self):
        conn = FakeList(stale=1)
        self.assertEqual(worker.absorb_stale_consumers(conn, "q", sleep=lambda s: None), 1)
        self.assertEqual(conn.items, [])

    def test_absorption_is_bounded(self):
        conn = FakeList(stale=10)
        self.assertEqual(worker.absorb_stale_consumers(conn, "q", max_rounds=3, sleep=lambda s: None), 3)

    def test_decoys_cannot_be_jobs(self):
        self.assertTrue(worker.DECOY_PREFIX.endswith(":"))
        self.assertNotIn("rq:job:", worker.DECOY_PREFIX)


class MainTests(unittest.TestCase):
    def test_scheduler_disabled_ttl_applied_and_absorption_runs_first(self):
        events = []

        class FakeRedis:
            @staticmethod
            def from_url(url):
                events.append(("connect", url))
                return FakeList()

        class FakeQueue:
            def __init__(self, name, connection):
                self.name, self.key = name, "rq:queue:" + name

        class FakeWorker:
            def __init__(self, queues, connection, worker_ttl):
                events.append(("worker", [q.name for q in queues], worker_ttl))
                self.dequeue_timeout = worker_ttl - 15

            def work(self, **kwargs):
                events.append(("work", kwargs))

        fake_redis = types.ModuleType("redis")
        fake_redis.Redis = FakeRedis
        fake_rq = types.ModuleType("rq")
        fake_rq.Queue, fake_rq.Worker = FakeQueue, FakeWorker

        def absorb(conn, key):
            events.append(("absorb", key))
            return 0

        with mock.patch.dict(sys.modules, {"redis": fake_redis, "rq": fake_rq}), \
                mock.patch.dict("os.environ", {"OMNI_REDIS_URL": "redis://example/0"}, clear=False), \
                mock.patch.object(worker, "absorb_stale_consumers", absorb), \
                mock.patch("builtins.print"):
            worker.main()

        self.assertEqual(events, [
            ("connect", "redis://example/0"),
            ("absorb", "rq:queue:omni-builds"),
            ("worker", ["omni-builds"], 135),
            ("work", {"with_scheduler": False}),
        ])


if __name__ == "__main__":
    unittest.main()
