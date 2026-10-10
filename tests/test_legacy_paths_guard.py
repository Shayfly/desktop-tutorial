"""Audit 2026-10-10: legacy in-process paths are refused on staging/production."""
import os
import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    from omni_prod import investor_app
except Exception:  # pragma: no cover - fastapi absent in some local environments
    TestClient = None


@unittest.skipIf(TestClient is None, 'fastapi not installed')
class LegacyGuardTests(unittest.TestCase):
    def test_legacy_paths_are_410_on_staging(self):
        client = TestClient(investor_app.app)
        with patch.dict(os.environ, {'OMNI_ENV': 'staging'}):
            for method, path in (('get', '/hosted/v25/x'), ('post', '/runtime/v27/x/login'),
                                 ('get', '/api/source/mobile/android'), ('get', '/api/v25/source/omni-android'),
                                 ('post', '/api/v28/projects/p/patch')):
                r = client.request(method.upper(), path, json={})
                self.assertEqual(r.status_code, 410, (path, r.status_code))
                self.assertEqual(r.json()['error'], 'legacy_path_disabled')

    def test_template_build_and_promote_refused_on_staging_without_durable_backend(self):
        with patch.dict(os.environ, {'OMNI_ENV': 'staging'}), patch.object(investor_app, '_async_build_mode', return_value=False):
            self.assertTrue(investor_app._legacy_refused())
            with self.assertRaises(Exception) as ctx:
                investor_app._reject_legacy_sync_build()
            self.assertEqual(getattr(ctx.exception, 'status_code', None), 410)

    def test_local_development_keeps_them(self):
        with patch.dict(os.environ, {'OMNI_ENV': 'development'}), patch.object(investor_app, '_async_build_mode', return_value=False):
            self.assertFalse(investor_app._legacy_refused())


if __name__ == '__main__':
    unittest.main()
