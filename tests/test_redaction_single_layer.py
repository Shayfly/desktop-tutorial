"""C27: one redaction layer, and it knows Google keys (founder 2026-10-20).

C30: four separate redactors; omni_prod.secret_redaction (used by structured events, the acceptance pipeline and
training data) did not match AIza... keys, and no logging filter existed, so a Gemini key in a log line was printed.
"""
import io
import logging
import unittest

from omni_prod import secret_redaction
from omni_prod.secret_redaction import redact


def install_log_redaction():
    fn = getattr(secret_redaction, 'install_log_redaction', None)
    assert callable(fn), 'no install_log_redaction: there is no logging layer'
    fn()

GOOGLE = 'AIza' + 'SyD3m0x9Q7aB-cdEfGh_ijKLmnopQRstuv1'          # synthetic, the shape of a Google API key
SECRETS = {
    'google': f'request failed for key={GOOGLE[:4]}... full {GOOGLE} in url ?key={GOOGLE}',
    'github': 'push with ghp_' + 'a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8',
    'github_pat': 'token github_pat_' + '11ABCDEFG0abcdefghijklmnopqrstuvwxyz',
    'replicate': 'auth r8_' + 'AbCdEfGhIjKlMnOpQrStUvWxYz012345',
    'anthropic': 'x-api-key: sk-ant-api03-' + 'abcdefghijklmnopqrstuvwx',
    'redis_url': 'connect rediss://default:' + 'S3cretPassw0rd' + '@eu1.upstash.io:6379',
}
LEAKS = {'google': GOOGLE, 'github': 'a1B2c3D4e5F6g7H8i9J0', 'github_pat': 'abcdefghijklmnopqrstuvwxyz',
         'replicate': 'AbCdEfGhIjKlMnOpQrSt', 'anthropic': 'abcdefghijklmnopqrstuvwx', 'redis_url': 'S3cretPassw0rd'}


class TheLayerKnowsTheProviders(unittest.TestCase):
    def test_every_provider_secret_shape_is_removed(self):
        for name, text in SECRETS.items():
            self.assertNotIn(LEAKS[name], redact(text), name)

    def test_what_is_not_a_secret_survives(self):
        sha = 'f6152ea8c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8'
        text = f'deploy {sha} build bld_4f3b3514edd34776b096bf20fd66cc58 https://example.com/a?b=1'
        self.assertEqual(redact(text), text)


class EveryLoggerGoesThroughIt(unittest.TestCase):
    def setUp(self):
        self.factory = logging.getLogRecordFactory()
        self.addCleanup(logging.setLogRecordFactory, self.factory)

    def capture(self, name):
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        log = logging.getLogger(name)
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        log.propagate = False
        self.addCleanup(log.removeHandler, handler)
        return log, buf

    def test_a_key_passed_as_an_argument_to_any_logger_is_redacted(self):
        install_log_redaction()
        install_log_redaction()                                         # idempotent
        log, buf = self.capture('omni_prod.some.module.created.later')
        log.warning('model call failed for %s with %s', 'gemini', GOOGLE)
        log.info(SECRETS['redis_url'])
        out = buf.getvalue()
        self.assertNotIn(GOOGLE, out)
        self.assertNotIn('S3cretPassw0rd', out)
        self.assertIn('model call failed for gemini with [REDACTED]', out)

    def test_the_worker_and_the_api_install_it(self):
        import inspect
        from omni_prod import worker
        self.assertIn('install_log_redaction()', inspect.getsource(worker.main))
        src = open(secret_redaction.__file__.replace('secret_redaction.py', 'investor_app.py'), encoding='utf-8').read()
        self.assertIn('install_log_redaction()', src)

    def test_evidence_export_parity_with_the_layer(self):
        # evidence_export runs as a single file (no package import), so it keeps its own redactor: it must remove every
        # secret shape the layer removes.
        from omni_prod.evidence_export import redact as export_redact
        for name, text in SECRETS.items():
            self.assertNotIn(LEAKS[name], export_redact(text), name)
            self.assertNotIn(LEAKS[name], redact(text), name)


if __name__ == '__main__':
    unittest.main()
