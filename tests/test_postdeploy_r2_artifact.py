"""paid-verify reads the built version back from R2 and compares SHA-256 with the build's record (2026-10-20)."""
import hashlib
import io
import unittest
import zipfile

from omni_prod.postdeploy_checks import r2_artifact_check
from omni_prod.workspace import _checksum

REPO = {'app.py': 'print("hi")\n', '.omni/project.json': '{}'}
SHA = _checksum(REPO)
KEY = f'repositories/{SHA}.zip'


def zipped(repo):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for k, v in repo.items():
            zf.writestr(k, v)
    return buf.getvalue()


class Store:
    bucket = 'b'

    def __init__(self, objects):
        self.objects = objects
        store = self

        class Client:
            def get_object(self, *, Bucket, Key):
                if Key not in store.objects:
                    raise KeyError(f'NoSuchKey {Key}')
                data, meta = store.objects[Key]
                return {'Body': io.BytesIO(data), 'Metadata': meta}
        self.client = Client()


def good_store(repo=REPO):
    data = zipped(repo)
    return Store({KEY: (data, {'sha256': hashlib.sha256(data).hexdigest()})})


class R2ArtifactCheckTests(unittest.TestCase):
    def check(self, store, recorded=SHA, key=KEY, stage=(SHA,)):
        return r2_artifact_check('bld', 'v1', store=store, rows=((recorded, key), list(stage)))

    def test_matching_artifact_passes_and_reports_every_value(self):
        ok, out = self.check(good_store())
        self.assertTrue(ok, out)
        self.assertEqual(out['recomputed_repository_sha256'], SHA)
        self.assertEqual(out['object_sha256'], out['object_metadata_sha256'])

    def test_different_content_in_r2_fails(self):
        ok, out = self.check(good_store({**REPO, 'app.py': 'print("tampered")\n'}))
        self.assertFalse(ok)
        self.assertNotEqual(out['recomputed_repository_sha256'], SHA)

    def test_missing_object_fails_with_the_error(self):
        ok, out = self.check(Store({}))
        self.assertFalse(ok)
        self.assertIn('NoSuchKey', out['error'])

    def test_metadata_mismatch_fails(self):
        data = zipped(REPO)
        ok, out = self.check(Store({KEY: (data, {'sha256': '0' * 64})}))
        self.assertFalse(ok)

    def test_no_store_or_no_record_is_not_a_pass(self):
        self.assertFalse(self.check(good_store(), recorded=None)[0])
        self.assertFalse(self.check(good_store(), key=None)[0])

    def test_stage_results_with_another_sha_fail(self):
        self.assertFalse(self.check(good_store(), stage=('f' * 64,))[0])
        self.assertFalse(self.check(good_store(), stage=())[0])


if __name__ == '__main__':
    unittest.main()
