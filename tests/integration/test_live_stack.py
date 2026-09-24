import os
import unittest

RUN = os.getenv("OMNI_RUN_LIVE_INTEGRATION") == "1"

@unittest.skipUnless(RUN, "set OMNI_RUN_LIVE_INTEGRATION=1 to run real service tests")
class LiveProductionStackTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.config import Settings
        from omni_prod.production_adapters import build_production_adapters
        self.settings = Settings.from_env()
        self.adapters = build_production_adapters(self.settings)

    def tearDown(self):
        self.adapters.close()

    def test_postgres_pool_real_connection(self):
        self.adapters.db_pool.wait_until_ready(attempts=3)

    def test_redis_real_connection(self):
        self.assertTrue(self.adapters.redis.ping())

    def test_s3_real_bucket_roundtrip(self):
        key = "integration/healthcheck.txt"
        stored = self.adapters.artifacts.put_bytes(key, b"omni-integration")
        self.assertEqual(stored.size, 16)
        self.assertEqual(
            self.adapters.artifacts.get_bytes(key),
            b"omni-integration",
        )
