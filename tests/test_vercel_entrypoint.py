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

    def test_vercel_requirements_match_direct_production_pins(self):
        def dependency_lines(path):
            return [
                line.split('#', 1)[0].strip()
                for line in Path(path).read_text(encoding='utf-8').splitlines()
                if line.split('#', 1)[0].strip()
            ]

        requirements = dependency_lines('requirements.txt')
        production = dependency_lines('requirements-production.txt')
        self.assertTrue(requirements, 'Vercel dependencies must not be empty')
        self.assertEqual(requirements, production)
        for requirement in requirements:
            self.assertFalse(requirement.startswith('-'), 'Vercel requires direct dependency pins')
            self.assertIn('==', requirement, 'Production dependencies must be pinned')


if __name__ == '__main__':
    unittest.main()
