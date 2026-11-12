"""#324: when the image-test result cannot be retrieved, the log names the stage and the exception type -- and
nothing else (no URL, no provider text, no secret). Replicate deletes a result after one hour, so a retry without
this log teaches nothing."""
import logging
import unittest
from types import SimpleNamespace

from omni_prod.providers import replicate_image_test as R

SECRET_URL = 'https://replicate.delivery/secret-path/out-0.png?token=abc'


class Journal:
    def find(self, key):
        return SimpleNamespace(provider='replicate', provider_task_id='p1', idempotency_key=key)


class Store:
    def __init__(self, get_exc=KeyError('none'), put_exc=None):
        self.get_exc, self.put_exc = get_exc, put_exc

    def get_bytes(self, key):
        raise self.get_exc

    def put_bytes(self, key, data):
        if self.put_exc:
            raise self.put_exc


class UnsafeFetch(Exception):
    pass


def svc(store, poll=None, collect=None):
    t = R.ReplicateImageTest.__new__(R.ReplicateImageTest)
    t.journal, t.store, t.env = Journal(), store, {}
    t.provider = SimpleNamespace(
        poll=poll or (lambda h: SimpleNamespace(status='SUCCEEDED')),
        collect=collect or (lambda h: SimpleNamespace(payloads=[SimpleNamespace(data=b'png')], actual_cost_usd=None)))
    return t


class StageIsLogged(unittest.TestCase):
    def check(self, service, stage, exc_type):
        with self.assertLogs('omni_prod.providers.replicate_image_test', level='WARNING') as logs:
            with self.assertRaises(Exception):
                service.status('acct')
        line = logs.output[0]
        self.assertIn(f'stage={stage}', line)
        self.assertIn(f'type={exc_type}', line)
        self.assertNotIn('replicate.delivery', line)
        self.assertNotIn('token', line)

    def test_storage_read(self):
        err = RuntimeError(SECRET_URL)
        err.response = {'Error': {'Code': 'AccessDenied'}}
        self.check(svc(Store(get_exc=err)), 'read_stored_image', 'RuntimeError')

    def test_poll(self):
        def boom(h):
            raise ConnectionError(SECRET_URL)
        self.check(svc(Store(), poll=boom), 'poll', 'ConnectionError')

    def test_download(self):
        def boom(h):
            raise UnsafeFetch(SECRET_URL)
        self.check(svc(Store(), collect=boom), 'collect_and_download', 'UnsafeFetch')

    def test_the_reason_is_a_fixed_word_never_the_host(self):
        # the exact messages image_provider/_download and sniff_image raise (2026-11-12 run: collect_and_download/ValueError)
        cases = {'provider output URL rejected: host replicate.delivery is not in the provider allowlist': 'url_host_not_allowed',
                 'provider output URL rejected: host x.example does not resolve': 'url_host_unresolved',
                 'provider output is not a PNG, JPEG or WebP image': 'not_an_image',
                 'something new ' + SECRET_URL: 'other'}
        for message, reason in cases.items():
            def boom(h, m=message):
                raise ValueError(m)
            with self.subTest(reason=reason), \
                    self.assertLogs('omni_prod.providers.replicate_image_test', level='WARNING') as logs:
                with self.assertRaises(ValueError):
                    svc(Store(), collect=boom).status('acct')
            self.assertIn(f'reason={reason}', logs.output[0])
            self.assertNotIn('replicate.delivery', logs.output[0])
            self.assertNotIn('example', logs.output[0])

    def test_store_write(self):
        self.check(svc(Store(put_exc=OSError(SECRET_URL))), 'store_image', 'OSError')

    def test_success_logs_nothing(self):
        with self.assertNoLogs('omni_prod.providers.replicate_image_test', level='WARNING'):
            self.assertTrue(svc(Store()).status('acct')['generation_verified'])


if __name__ == '__main__':
    unittest.main()
