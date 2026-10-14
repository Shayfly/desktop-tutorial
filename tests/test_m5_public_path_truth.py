import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from omni_prod import investor_app


class M5PublicPathTruthTests(unittest.TestCase):
    def test_durable_mode_rejects_legacy_sync_build(self):
        with patch.object(investor_app, '_async_build_mode', return_value=True):
            with self.assertRaises(HTTPException) as ctx:
                investor_app._reject_legacy_sync_build()
        self.assertEqual(ctx.exception.status_code, 410)
        self.assertIn('/builds', str(ctx.exception.detail))

    def test_durable_mode_refuses_every_deterministic_build_and_in_memory_publish(self):
        """Directive 2026-10-09 gap map #11: no shadow build, no fake publish."""
        from fastapi.testclient import TestClient
        client = TestClient(investor_app.app)
        with patch.object(investor_app, '_async_build_mode', return_value=True):
            for path, body in (('/api/demo/build', {'prompt': 'xyz'}), ('/api/v25/build', {'prompt': 'xyz'}),
                               ('/api/v26/projects/p/build', {'prompt': 'xyz'}),
                               ('/api/v27/projects/p/build', {'prompt': 'xyz'})):
                self.assertEqual(client.post(path, json=body).status_code, 410, path)
            for path in ('/api/v25/projects/p/promote', '/api/v26/projects/p/promote',
                         '/api/v27/projects/p/promote', '/api/v28/projects/p/promote'):
                r = client.post(path)
                self.assertEqual(r.status_code, 501, path)
                self.assertEqual(r.json()['detail']['error'], 'publish_not_available')

    def test_memory_mode_is_never_m5_staging_ready(self):
        with patch.dict(os.environ, {'OMNI_CREATOR_PERSISTENCE': 'memory'}, clear=False):
            payload = investor_app._m5_status_payload()
        self.assertEqual(payload['status'], 'M5_PARTIAL')
        self.assertFalse(payload['staging_ready'])
        self.assertEqual(payload['persistence'], 'memory')

    def test_m5_truth_starts_partial_until_release_gate_proves_candidate(self):
        payload = investor_app._m5_status_payload()
        self.assertEqual(payload['status'], 'M5_PARTIAL')
        self.assertFalse(payload['production_ready'])
        self.assertIn('external_proof_required', payload['blockers'])


if __name__ == '__main__':
    unittest.main()
