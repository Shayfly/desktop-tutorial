"""infra/worker-host/provider_probe.py without network: a configured key on an account with no money is FAIL, a
missing key is FAIL, only HTTP 200 is PASS, and no key ever appears in the output."""
import importlib.util
import io
import json
import pathlib
import shutil
import tempfile
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
KEYS = {'GEMINI_API_KEY': 'AIza-test-gemini-secret', 'OPENAI_API_KEY': 'sk-test-openai-secret',
        'ANTHROPIC_API_KEY': 'sk-ant-test-secret', 'VENICE_API_KEY1': 'VENICE_INFERENCE_KEY_test_secret'}


class FakeResp(io.BytesIO):
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): return False


def fake_urlopen(req, timeout=None):
    url, auth = req.full_url, req.headers.get('Authorization', '') + req.headers.get('X-api-key', '')
    def http_error(code, payload):
        return urllib.error.HTTPError(url, code, 'x', {}, io.BytesIO(json.dumps(payload).encode()))
    if 'openai.com' in url:
        raise http_error(429, {'error': {'code': 'insufficient_quota', 'message': 'no credit for ' + auth}})
    if 'anthropic.com' in url:
        raise http_error(400, {'error': {'type': 'invalid_request_error', 'message': 'credit balance too low'}})
    if url.endswith('/models?type=text'):
        return FakeResp(json.dumps({'data': [{'id': 'cheap-private', 'model_spec': {'privacy': 'private',
                        'pricing': {'input': {'usd': 0.05}, 'output': {'usd': 0.13}}}}]}).encode())
    return FakeResp(b'{"choices": []}')


class ProviderProbe(unittest.TestCase):
    def run_probe(self, keys):
        d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        shutil.copy(ROOT / 'infra/worker-host/provider_probe.py', d)
        shutil.copy(ROOT / 'infra/worker-host/model-catalog.json', d)
        (d / '.env').write_text(''.join(f'{k}={v}\n' for k, v in keys.items()))
        spec = importlib.util.spec_from_file_location('probe', d / 'provider_probe.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out = io.StringIO()
        with mock.patch('urllib.request.urlopen', fake_urlopen), redirect_stdout(out):
            rc = mod.main()
        return rc, out.getvalue()

    def test_no_money_is_fail_and_keys_never_printed(self):
        rc, out = self.run_probe(KEYS)
        self.assertEqual(rc, 1)
        # a valid key with no money: auth PASS, billing FAIL, verdict FAIL
        self.assertIn('provider-probe openai/gpt-6-luna::FAIL auth=PASS billing=FAIL http=429 code=insufficient_quota', out)
        self.assertIn('provider-probe anthropic/claude-sonnet-5-5::FAIL auth=PASS billing=FAIL http=400', out)
        self.assertIn('provider-probe gemini/gemini-3.5-flash-lite::PASS auth=PASS billing=VERIFIED http=200', out)
        self.assertIn('provider-probe venice/cheap-private::PASS auth=PASS billing=VERIFIED http=200', out)
        self.assertIn('provider-probe replicate::FAIL auth=NOT_SET billing=NOT_REACHED', out)
        for secret in KEYS.values():
            self.assertNotIn(secret, out)
        self.assertNotIn('credit balance too low', out)                 # provider messages are not printed

    def test_replicate_token_valid_is_partial_never_pass(self):
        rc, out = self.run_probe({**KEYS, 'REPLICATE_API_TOKEN': 'r8_test_secret'})
        self.assertIn('provider-probe replicate/account::PARTIAL auth=PASS billing=NOT_COVERED http=200', out)
        self.assertIn('billing NOT covered', out)
        self.assertNotIn('r8_test_secret', out)

    def test_rejected_key_is_auth_fail(self):
        def reject(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 401, 'x', {}, io.BytesIO(b'{"error": {"code": "invalid_api_key"}}'))
        d = None
        with mock.patch.object(sys.modules[__name__], 'fake_urlopen', reject):
            rc, out = self.run_probe(KEYS)
        self.assertIn('auth=FAIL billing=NOT_REACHED http=401', out)

    def test_missing_key_is_fail(self):
        rc, out = self.run_probe({})
        self.assertEqual(rc, 1)
        self.assertIn('GEMINI_API_KEY not set on the worker', out)
        self.assertIn('VENICE_API_KEY1 not set on the worker', out)
        self.assertNotIn('::PASS', out)


if __name__ == '__main__':
    unittest.main()
