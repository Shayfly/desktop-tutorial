"""Warehouse 100 (the owner, 2026-11-20: "תעשה את כל מה שיש לנו במחסן"): the 148ai site was slow because its
functions ran in Vercel's default region, iad1 (Washington, D.C.), while everything they talk to on a request is in
Frankfurt: Neon (aws-eu-central-1, project 148ai-db-v2), Upstash/QStash (eu-central-1), R2 and the worker host
(infra/worker-host/README_HE.md: "Germany Central (Frankfurt), close to Neon, Upstash and R2").

Measured before the change (Vercel observability, production, p50, 2026-11-17..20): a static file 8 ms; every route
that reads the database 1.4-2.5 s -- /api/v28/auth/login 2,466 ms, a build's status/events/plan 1,950-2,040 ms,
/api/v28/deployment 1,423 ms. Each query crossed the Atlantic. The functions now run in fra1 (Frankfurt), next to the
data; a model call (US providers) crosses once per call instead, which is small against its generation time.
Vercel documents `regions` as the project default ("defaults to iad1 ... Hobby plans can select any single region")."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TheFunctionsRunNextToTheirData(unittest.TestCase):
    def test_the_functions_run_in_frankfurt_with_the_database_queue_storage_and_worker(self):
        config = json.loads((ROOT / 'vercel.json').read_text(encoding='utf-8'))
        self.assertEqual(config.get('regions'), ['fra1'])

    def test_no_function_overrides_the_region_back_to_another_continent(self):
        config = json.loads((ROOT / 'vercel.json').read_text(encoding='utf-8'))
        overrides = {name: f['regions'] for name, f in config.get('functions', {}).items() if 'regions' in f}
        self.assertEqual(overrides, {})

    def test_the_worker_host_is_documented_in_the_same_region(self):
        readme = (ROOT / 'infra' / 'worker-host' / 'README_HE.md').read_text(encoding='utf-8')
        self.assertIn('Frankfurt', readme)


if __name__ == '__main__':
    unittest.main()
