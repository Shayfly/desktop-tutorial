"""inspect-round-artifacts.yml: read-only ENFORCED, failures FAIL, the zips are uploaded (founder 2026-10-20; Matt's
HOLD on #88: (a) a bad checksum or failed download only printed a note, (b) read-only was declared, not enforced,
(c) the truncated annotations do not replace the zip)."""
import hashlib
import importlib.util
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


def steps():
    return workflow()['jobs']['inspect']['steps']


def reader_run():
    return steps()[0]['run']


def embedded(run: str) -> str:
    return run.split("<<'PY'\n", 1)[1].split('\nPY', 1)[0]


def make_zip(repo):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for k, v in repo.items():
            zf.writestr(k, v)
    return buf.getvalue()


class Fakes:
    """A database that records every statement and a store whose client has botocore-like events."""

    def __init__(self, snaps, objects, status='failed', build_exists=True):
        self.statements, self.registered = [], []
        fakes = self

        class Conn:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def transaction(self): return self
            def execute(self, q, p=()):
                fakes.statements.append(q.strip())
                return types.SimpleNamespace(fetchone=lambda: (status, snaps) if build_exists else None)

        class Client:
            meta = types.SimpleNamespace(events=types.SimpleNamespace(
                register=lambda event, fn: fakes.registered.append((event, fn))))

            def get_object(self, Bucket, Key):
                if Key not in objects:
                    raise KeyError(f'NoSuchKey {Key}')
                data, meta = objects[Key]
                return {'Body': io.BytesIO(data), 'Metadata': meta}
        self.pool = types.SimpleNamespace(connection=lambda: Conn())
        self.store = types.SimpleNamespace(client=Client(), bucket='b')


def run_reader(fakes, rounds='all', files='front'):
    src = embedded(reader_run())
    with tempfile.TemporaryDirectory() as out:
        os.makedirs(os.path.join(out, 'zips'))
        code = 0
        with mock.patch.dict(os.environ, {'BID': 'bld_x', 'ROUNDS': rounds, 'FILES': files}), \
                mock.patch('omni_prod.investor_app._v28_pool', fakes.pool, create=True), \
                mock.patch('omni_prod.evidence_export._default_store', lambda env: fakes.store):
            try:
                exec(compile(src.replace('/out/', out + '/'), 'reader', 'exec'), {})
            except SystemExit as exc:
                code = exc.code
        notes = [json.loads(l) for f in sorted(os.listdir(out)) if f.endswith('.jsonl')
                 for l in open(os.path.join(out, f), encoding='utf-8')]
        zips = sorted(os.listdir(os.path.join(out, 'zips')))
    return code, notes, zips


REPO = {'app.py': 'KEY = "AIza' + 'x' * 30 + '"\n' + 'print(1)\n' * 500, 'index.html': '<html>' + 'a' * 4000 + '</html>',
        '.omni/project.json': '{}', 'static/s.css': 'a{b:c}'}


def good():
    from omni_prod.workspace import _checksum
    data, sha = make_zip(REPO), _checksum(REPO)
    key = f'build-rounds/bld_x/00-{sha[:12]}.zip'
    snaps = [{'round': 0, 'decision': 'initial', 'failing': ['PREVIEW'], 'key': key, 'sha256': sha}]
    return snaps, {key: (data, {'sha256': hashlib.sha256(data).hexdigest()})}, key


class Contract(unittest.TestCase):
    def test_no_write_or_container_control_anywhere(self):
        text = WF.read_text(encoding='utf-8')
        for forbidden in ('put_object', 'delete_object', 'put_bytes', 'sql_write', 'INSERT ', 'UPDATE ', 'DELETE FROM',
                          'docker compose stop', 'docker compose start', 'docker exec', 'docker compose run',
                          'docker compose restart', 'subprocess', 'continue-on-error'):
            self.assertNotIn(forbidden, text, forbidden)

    def test_read_only_is_enforced_on_the_container(self):
        run = reader_run()
        for flag in ('--read-only', '--tmpfs /tmp', '--cap-drop ALL', '--security-opt no-new-privileges'):
            self.assertIn(flag, run)

    def test_inputs_are_validated_before_use(self):
        run = reader_run()
        for check in (r'^bld_[0-9a-f]{32}$', r'^(all|[0-9]{1,2}(,[0-9]{1,2})*)$', r'^(front|all)$'):
            self.assertIn(check, run)
        self.assertLess(run.index('[[ "$BID" =~'), run.index('docker run'))

    def test_prints_run_even_when_the_reader_failed_and_the_zips_are_uploaded_once(self):
        job = workflow()['jobs']['inspect']
        prints = [s for s in job['steps'] if s['name'].startswith('Print part')]
        self.assertEqual(len(prints), 5)
        self.assertTrue(all(s.get('if') == 'always()' for s in prints))
        upload = next(s for s in job['steps'] if s['name'] == 'Upload the round zips')
        self.assertEqual(upload['uses'], 'actions/upload-artifact@v4')
        self.assertEqual(upload['if'], 'always() && matrix.slice == 0')
        self.assertIn('/rounds/zips/', upload['with']['path'])
        names = [s['name'] for s in job['steps']]
        self.assertLess(names.index('Upload the round zips'), names.index('Clean up'))
        self.assertEqual(job['strategy']['max-parallel'], 1)


class ReaderAgainstFakes(unittest.TestCase):
    def test_clean_read_prints_verifies_redacts_and_saves_the_zip(self):
        snaps, objects, key = good()
        f = Fakes(snaps, objects)
        code, notes, zips = run_reader(f)
        self.assertEqual(code, 0)
        self.assertEqual(f.statements[0], 'SET TRANSACTION READ ONLY')          # before the SELECT
        self.assertTrue(f.statements[1].startswith('SELECT'))
        self.assertEqual([e for e, _ in f.registered], ['before-call.s3'])
        manifest = json.loads(dict(notes)['round 0 manifest'])
        self.assertTrue(manifest['metadata_sha256_matches'])
        self.assertEqual(manifest['repository_sha256_recomputed'], manifest['repository_sha256_recorded'])
        self.assertIn('round 0 index.html [1/2]', dict(notes))
        self.assertNotIn('round 0 .omni/project.json [1/1]', dict(notes))
        self.assertFalse(any(re.search(r'AIza[0-9A-Za-z_-]{16,}', m) for _, m in notes))
        self.assertEqual(zips, [f'00-{key.rsplit("/", 1)[-1]}'])

    def test_a_key_shaped_filename_is_redacted_in_the_title_too(self):
        # T7c (Matt on #88): note(title, msg) redacted only msg; a chosen filename went into the annotation title.
        from omni_prod.workspace import _checksum
        leaky = 'sk-' + 'x' * 20 + '.js'
        repo = {**REPO, leaky: 'console.log(1)'}
        data, sha = make_zip(repo), _checksum(repo)
        key = f'build-rounds/bld_x/00-{sha[:12]}.zip'
        snaps = [{'round': 0, 'decision': 'initial', 'failing': [], 'key': key, 'sha256': sha}]
        code, notes, _ = run_reader(Fakes(snaps, {key: (data, {'sha256': hashlib.sha256(data).hexdigest()})}))
        self.assertEqual(code, 0)
        self.assertFalse([t for t, _ in notes if 'sk-' + 'x' * 20 in t], [t for t, _ in notes])
        self.assertIn('round 0 [redacted].js [1/1]', [t for t, _ in notes])          # the file is still shown, by name
        self.assertFalse([m for _, m in notes if 'sk-' + 'x' * 20 in m])             # and the manifest's file list

    def test_a_wrong_metadata_checksum_fails_the_job(self):
        snaps, objects, key = good()
        objects[key] = (objects[key][0], {'sha256': '0' * 64})
        code, notes, _ = run_reader(Fakes(snaps, objects))
        self.assertEqual(code, 1)
        self.assertTrue(notes[0][0].startswith('FAIL round 0'), notes[0])       # errors are printed first

    def test_a_repository_that_is_not_the_recorded_one_fails_the_job(self):
        snaps, objects, _ = good()
        snaps[0]['sha256'] = 'f' * 64
        code, notes, _ = run_reader(Fakes(snaps, objects))
        self.assertEqual(code, 1)
        self.assertIn('repository checksum', notes[0][1])

    def test_a_failed_download_fails_the_job(self):
        snaps, _, _ = good()
        code, notes, zips = run_reader(Fakes(snaps, {}))
        self.assertEqual(code, 1)
        self.assertIn('NoSuchKey', notes[0][1])
        self.assertEqual(zips, [])

    def test_a_missing_build_a_missing_key_or_a_requested_absent_round_fails(self):
        self.assertEqual(run_reader(Fakes([], {}, build_exists=False))[0], 1)
        self.assertEqual(run_reader(Fakes([{'round': 0, 'key': None}], {}))[0], 1)
        snaps, objects, _ = good()
        code, notes, _ = run_reader(Fakes(snaps, objects), rounds='0,2')
        self.assertEqual(code, 1)
        self.assertIn('round 2', notes[0][0])


# Skippable ONLY outside CI: both CI jobs install requirements-production.txt (boto3==1.43.94), and a skip there would
# leave the S3 write guard untested without anyone noticing (founder 2026-10-20 22:07). In GitHub Actions a missing
# boto3 is an error, not a skip.
@unittest.skipIf(importlib.util.find_spec('boto3') is None and not os.environ.get('GITHUB_ACTIONS'),
                 'boto3 not installed here (local only; never skipped in CI)')
class TheS3GuardRefusesWritesOnARealClient(unittest.TestCase):
    def test_put_and_delete_are_refused_before_any_request(self):
        import boto3
        src = embedded(reader_run())
        guard_src = src[src.index('def only_get_object'):src.index('with _v28_pool')]
        ns = {}
        exec(guard_src, ns)
        client = boto3.client('s3', endpoint_url='http://127.0.0.1:9', aws_access_key_id='x',
                              aws_secret_access_key='y', region_name='us-east-1')
        client.meta.events.register('before-call.s3', ns['only_get_object'])
        for call in (lambda: client.put_object(Bucket='b', Key='k', Body=b'x'),
                     lambda: client.delete_object(Bucket='b', Key='k')):
            with self.assertRaises(PermissionError):
                call()
        if os.environ.get('GITHUB_ACTIONS') == 'true':   # T7c: the named outcome, readable as an annotation (O14)
            print(f'::notice title=T7c S3 guard on a real boto3 {boto3.__version__} client::'
                  'PASS test_put_and_delete_are_refused_before_any_request (PutObject and DeleteObject refused '
                  'before any request)', flush=True)


if __name__ == '__main__':
    unittest.main()
