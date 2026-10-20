"""inspect-round-artifacts.yml stays read-only and prints what it read (founder 2026-10-20 21:24)."""
import hashlib
import io
import json
import os
import re
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github' / 'workflows' / 'inspect-round-artifacts.yml'


def workflow():
    return yaml.safe_load(WF.read_text(encoding='utf-8'))


def embedded(run: str) -> str:
    return run.split("<<'PY'\n", 1)[1].split('\nPY', 1)[0]


class ReadOnlyContract(unittest.TestCase):
    def test_nothing_writes_stops_or_executes_product_code(self):
        text = WF.read_text(encoding='utf-8')
        for forbidden in ('put_object', 'delete_object', 'put_bytes', 'sql_write', 'INSERT ', 'UPDATE ', 'DELETE FROM',
                          'docker compose stop', 'docker compose start', 'docker exec', 'docker compose run',
                          'docker compose restart', 'subprocess', 'continue-on-error'):
            self.assertNotIn(forbidden, text, forbidden)

    def test_inputs_are_validated_before_use(self):
        run = workflow()['jobs']['inspect']['steps'][0]['run']
        for check in (r'^bld_[0-9a-f]{32}$', r'^(all|[0-9]{1,2}(,[0-9]{1,2})*)$', r'^(front|all)$'):
            self.assertIn(check, run)
        self.assertLess(run.index('[[ "$BID" =~'), run.index('docker run'))

    def test_annotation_budget_per_job(self):
        job = workflow()['jobs']['inspect']
        prints = [s for s in job['steps'] if s['name'].startswith('Print part')]
        self.assertEqual(len(prints), 5)                       # 5 x 10 notices per matrix slice
        self.assertEqual(job['strategy']['max-parallel'], 1)
        self.assertEqual(job['strategy']['matrix']['slice'], [0, 1, 2, 3])


class EmbeddedReaderRunsAgainstFakes(unittest.TestCase):
    def test_reads_verifies_redacts_and_groups(self):
        from omni_prod.workspace import _checksum
        repo = {'app.py': 'KEY = "AIza' + 'x' * 30 + '"\n' + 'print(1)\n' * 500, 'index.html': '<html>' + 'a' * 4000 + '</html>',
                '.omni/project.json': '{}', 'static/s.css': 'a{b:c}'}
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            for k, v in repo.items():
                zf.writestr(k, v)
        data = buf.getvalue()
        sha = _checksum(repo)
        key = f'build-rounds/bld_x/00-{sha[:12]}.zip'

        class Conn:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, q, p):
                assert q.lstrip().upper().startswith('SELECT'), q
                return types.SimpleNamespace(fetchone=lambda: ('failed', [
                    {'round': 0, 'decision': 'initial', 'failing': ['PREVIEW'], 'key': key, 'sha256': sha},
                    {'round': 1, 'key': None}]))

        class Client:
            def get_object(self, Bucket, Key):
                return {'Body': io.BytesIO(data), 'Metadata': {'sha256': hashlib.sha256(data).hexdigest()}}
        store = types.SimpleNamespace(client=Client(), bucket='b')
        src = embedded(workflow()['jobs']['inspect']['steps'][0]['run'])
        with tempfile.TemporaryDirectory() as out, \
                mock.patch.dict(os.environ, {'BID': 'bld_x', 'ROUNDS': 'all', 'FILES': 'front'}), \
                mock.patch('omni_prod.investor_app._v28_pool', types.SimpleNamespace(connection=lambda: Conn()), create=True), \
                mock.patch('omni_prod.evidence_export._default_store', lambda env: store):
            exec(compile(src.replace('/out/', out + '/'), 'reader', 'exec'), {})
            notes = [json.loads(l) for f in sorted(os.listdir(out)) for l in open(os.path.join(out, f), encoding='utf-8')]
        titles = [t for t, _ in notes]
        manifest = json.loads(dict(notes)['round 0 manifest'])
        self.assertTrue(manifest['metadata_sha256_matches'])
        self.assertEqual(manifest['repository_sha256_recomputed'], manifest['repository_sha256_recorded'])
        self.assertIn('round 0 index.html [1/2]', titles)
        self.assertIn('round 0 static/s.css [1/1]', titles)
        self.assertNotIn('round 0 .omni/project.json [1/1]', titles)          # 'front' prints only the UI + app.py
        self.assertFalse(any(re.search(r'AIza[0-9A-Za-z_-]{16,}', m) for _, m in notes))
        self.assertIn('[redacted]', dict(notes)['round 0 app.py [1/2]'])
        self.assertIn('no key stored', dict(notes)['round 1'])


if __name__ == '__main__':
    unittest.main()
