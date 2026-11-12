"""C23: wrong secret lengths BLOCK the deploy (founder 2026-10-20; they were ::warning and the deploy went on).

The real infra/worker-host/write-env.sh runs (a copy in a temporary directory, with the catalog next to it) on a
synthetic WORKER_ENV that sets everything the script would otherwise fetch from the host or the network.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOST = Path(__file__).resolve().parents[1] / 'infra' / 'worker-host'
R2 = 'https://0123456789abcdef0123456789abcdef.r2.cloudflarestorage.com'


def worker_env(**over):
    v = {'OMNI_ENV': 'staging', 'OMNI_S3_ENDPOINT': R2, 'OMNI_S3_BUCKET': 'omni-artifacts',
         'OMNI_S3_ACCESS_KEY': 'a' * 32, 'OMNI_S3_SECRET_KEY': 'b' * 64, 'OMNI_SANDBOX_SHARED_SECRET': 's' * 40,
         'OMNI_MODEL_CATALOG_JSON': '[]', 'OMNI_PREVIEW_HOST_SUFFIX': '127-0-0-1.sslip.io',
         'OMNI_PREVIEW_RUNTIME_HOST': 'test-host', 'OMNI_INTAKE_MODEL': '0'}
    v.update(over)
    return '\n'.join(f'{k}={x}' for k, x in v.items() if x is not None)


def run(**over):
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(HOST / 'write-env.sh', d)
        shutil.copy(HOST / 'model-catalog.json', d)
        env = {'PATH': os.environ['PATH'], 'HOME': d, 'WORKER_ENV': worker_env(**over), 'GITHUB_SHA': 'test'}
        p = subprocess.run(['bash', os.path.join(d, 'write-env.sh')], env=env, capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout + p.stderr


class SecretLengthsBlock(unittest.TestCase):
    def test_correct_lengths_pass(self):
        code, out = run()
        self.assertEqual(code, 0, out)
        self.assertNotIn('::error', out)

    def test_an_r2_access_key_of_34_characters_fails_the_step(self):    # Golden E2E #1: a pasted key of 34
        code, out = run(OMNI_S3_ACCESS_KEY='a' * 34)
        self.assertEqual(code, 1, out)
        self.assertIn('::error title=WORKER_ENV::OMNI_S3_ACCESS_KEY has 34 characters', out)
        self.assertNotIn('a' * 34, out)                                    # never the value

    def test_an_r2_secret_key_of_63_characters_fails_the_step(self):
        code, out = run(OMNI_S3_SECRET_KEY='b' * 63)
        self.assertEqual(code, 1, out)
        self.assertIn('OMNI_S3_SECRET_KEY has 63 characters', out)

    def test_a_short_sandbox_secret_fails_the_step(self):
        code, out = run(OMNI_SANDBOX_SHARED_SECRET='s' * 31)
        self.assertEqual(code, 1, out)
        self.assertIn('OMNI_SANDBOX_SHARED_SECRET has 31 characters', out)

    def test_r2_lengths_are_not_applied_to_other_storage(self):
        code, out = run(OMNI_S3_ENDPOINT='https://s3.eu-central-1.amazonaws.com', OMNI_S3_ACCESS_KEY='A' * 20,
                        OMNI_S3_SECRET_KEY='B' * 40)
        self.assertEqual(code, 0, out)


if __name__ == '__main__':
    unittest.main()


class SecretKeyLengthIsDiscoveredNotEnforced(unittest.TestCase):
    def test_the_length_is_printed_and_never_blocks(self):
        for value, shown in (('k' * 50, 50), ('k' * 10, 10), (None, 0)):
            code, out = run(OMNI_SECRET_KEY=value)
            self.assertEqual(code, 0, out)
            self.assertIn(f'::notice title=secret-lengths::OMNI_SECRET_KEY={shown} characters', out)
            if value:
                self.assertNotIn(value, out)
