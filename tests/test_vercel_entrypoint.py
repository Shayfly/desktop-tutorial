from __future__ import annotations

import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class VercelEntrypointTests(unittest.TestCase):
    def test_asgi_entrypoint_imports_and_serves_status(self):
        from app import app

        response = TestClient(app).get('/api/status')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload, dict)

    def test_vercel_config_targets_app_function_without_secrets(self):
        config = json.loads(Path('vercel.json').read_text(encoding='utf-8'))
        self.assertIn('app.py', config.get('functions', {}))
        serialized = json.dumps(config).lower()
        for forbidden in ('secret_key', 'api_key', 'password', 'token'):
            self.assertNotIn(forbidden, serialized)

    def test_vercel_requirements_delegate_to_production_requirements(self):
        requirements = Path('requirements.txt').read_text(encoding='utf-8').strip()
        self.assertEqual(requirements, '-r requirements-production.txt')


if __name__ == '__main__':
    unittest.main()
