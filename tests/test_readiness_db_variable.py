"""2026-11-15 (Michael: check which variable readiness reads before the old 148ai-db integration vars are removed).

readiness.postgres_config read OMNI_DATABASE_URL or, failing that, DATABASE_URL. The app connects only with
OMNI_DATABASE_URL (investor_app, migrate, entitlements, active_jobs, build_outbox_relay, reservation_worker). The real
key sets of Vercel project 148aiv28 (names and targets only, no values) are in
tests/fixtures/vercel_env_keys_148aiv28_2026_11_15.json: production has OMNI_DATABASE_URL; preview has only the
10-05 integration's DATABASE_URL -- so on preview the gate said 'PostgreSQL configured' while the app had none."""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod.readiness import collect_readiness

KEYS = json.loads((Path(__file__).resolve().parent / 'fixtures' / 'vercel_env_keys_148aiv28_2026_11_15.json').read_text())


def postgres_gate(target):
    env = {k: 'set' for k in KEYS[target]}           # presence only; the gate never reads a value
    with mock.patch.dict(os.environ, env, clear=True):
        return next(g for g in collect_readiness() if g.name == 'postgres_config')


class ReadinessReadsTheAppsVariable(unittest.TestCase):
    def test_the_fixture_is_the_case(self):
        self.assertIn('OMNI_DATABASE_URL', KEYS['production'])
        self.assertNotIn('OMNI_DATABASE_URL', KEYS['preview'])
        self.assertIn('DATABASE_URL', KEYS['preview'])

    def test_production_is_configured(self):
        g = postgres_gate('production')
        self.assertTrue(g.passed)
        self.assertIn('OMNI_DATABASE_URL', g.detail)

    def test_preview_with_only_the_old_integration_variable_is_not_configured(self):
        g = postgres_gate('preview')
        self.assertFalse(g.passed, g.detail)
        self.assertEqual(g.detail, 'PostgreSQL not configured: OMNI_DATABASE_URL is not set')

    def test_no_reader_of_database_url_is_left_in_the_app(self):
        root = Path(__file__).resolve().parents[1] / 'omni_prod'
        readers = [str(p.relative_to(root)) for p in root.rglob('*.py')
                   if any(s in p.read_text(encoding='utf-8', errors='replace')
                          for s in ("getenv('DATABASE_URL'", 'getenv("DATABASE_URL"', "'OMNI_DATABASE_URL','DATABASE_URL'"))]
        self.assertEqual(readers, [])


if __name__ == '__main__':
    unittest.main()
