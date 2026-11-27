"""WH-100: the site answered slowly. Two request-path costs fixed in code.

1. live_core PostgresStore opened a new Neon connection (TCP + TLS + auth) on every store call; it now keeps one pool.
2. The page's own assets are versioned (?v=<hash>) but were served `no-cache`, so every page load invoked the Python
   function for each asset; a request with the current hash is now immutable.
"""
from __future__ import annotations

import unittest
from contextlib import contextmanager
from unittest import mock

from live_core import postgres_store as PS


class _FakePool:
    created = 0

    def __init__(self, conninfo, **kwargs):
        type(self).created += 1
        self.conninfo, self.kwargs = conninfo, kwargs

    @contextmanager
    def connection(self):
        yield object()

    check_connection = staticmethod(lambda conn: None)


class StoreConnectionReuseTests(unittest.TestCase):
    def setUp(self):
        _FakePool.created = 0

    def test_many_store_calls_open_one_pool_and_never_a_raw_connection(self):
        store = PS.PostgresStore("postgresql://u:p@host/db")
        store._schema_ready = True
        with mock.patch("psycopg_pool.ConnectionPool", _FakePool), \
                mock.patch.object(PS.psycopg, "connect", side_effect=AssertionError("raw connect per call")):
            for _ in range(5):
                with store._connection():
                    pass
        self.assertEqual(_FakePool.created, 1)

    def test_pool_is_lazy_and_checks_connections_on_checkout(self):
        store = PS.PostgresStore("postgresql://u:p@host/db")
        with mock.patch("psycopg_pool.ConnectionPool", _FakePool):
            self.assertEqual(_FakePool.created, 0)          # constructing the store opens nothing
            pool = store._get_pool()
        self.assertTrue(pool.kwargs["kwargs"]["autocommit"])
        self.assertIn("check", pool.kwargs)


class AssetCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from omni_prod import investor_app
        cls.mod = investor_app
        cls.client = TestClient(investor_app.app)

    def test_current_version_is_immutable(self):
        for name in ("app.js", "app.css", "visual-edit.js"):
            r = self.client.get(f"/assets/{name}?v={self.mod._ASSET_VERSION}")
            self.assertEqual(r.status_code, 200, name)
            self.assertIn("immutable", r.headers["cache-control"], name)

    def test_unversioned_or_stale_hash_still_revalidates(self):
        for url in ("/assets/app.js", "/assets/app.js?v=deadbeef0000"):
            r = self.client.get(url)
            self.assertEqual(r.headers["cache-control"], "no-cache", url)

    def test_index_references_the_hash_the_server_treats_as_immutable(self):
        self.assertIn(f"/assets/app.js?v={self.mod._ASSET_VERSION}", self.mod._HTML)


if __name__ == "__main__":
    unittest.main()
