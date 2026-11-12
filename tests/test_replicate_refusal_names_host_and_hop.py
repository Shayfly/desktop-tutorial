"""#324 step 2 (Michael 2026-11-12 14:37): an allowlist refusal of the Replicate output is logged with the bare HOST
name and the HOP (the URL Replicate gave us, or a redirect target) -- never a path, a '?', a parameter or a token.
Also the allowlist itself: Replicate's own hosts pass, any other host is refused (the list is not opened wide)."""
import logging
import unittest
from types import SimpleNamespace
from urllib import request

from omni_prod.providers import replicate_image_test as R
from omni_prod.providers.image_provider import build_image_provider
from omni_prod.safe_fetch import SafeFetcher, UnsafeURL

OPEN = {'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1'}
TOKEN = {'REPLICATE_API_TOKEN': 'r8_' + 'x' * 37, **OPEN}
SIGNED = '/xezq/secret-path/out-0.png?token=abc&X-Amz-Signature=deadbeef'


def public(host, port, proto=None):
    return [(2, 1, 6, '', ('93.184.216.34', port))]


class Journal:
    def find(self, key):
        return SimpleNamespace(provider='replicate', provider_task_id='p1', idempotency_key=key)


def provider():
    p = build_image_provider(TOKEN, journal=Journal())
    p.fetcher.resolver = public   # no DNS in tests; the allowlist is checked before resolving anyway
    return p


class TheAllowlistInForce(unittest.TestCase):
    """What the Replicate image test actually allows (the Vercel variable is not set; the code default applies)."""

    def test_replicate_hosts_pass_the_allowlist(self):
        f = provider().fetcher
        for host in ('replicate.delivery', 'pbxt.replicate.delivery', 'api.replicate.com'):
            with self.subTest(host=host):
                f.validate(f'https://{host}{SIGNED}')        # no exception

    def test_any_other_host_is_refused(self):
        f = provider().fetcher
        for host in ('example.com', 'replicate.delivery.evil.com', 'evilreplicate.delivery', 'replicate.com',
                     'storage.googleapis.com'):
            with self.subTest(host=host), self.assertRaises(UnsafeURL) as cm:
                f.validate(f'https://{host}{SIGNED}')
            self.assertEqual(cm.exception.host, host)


class TheRefusalCarriesHostAndHop(unittest.TestCase):
    def test_the_url_replicate_returned(self):
        with self.assertRaises(ValueError) as cm:
            provider()._download('https://cdn.example.net' + SIGNED)
        self.assertEqual((cm.exception.url_host, cm.exception.url_hop), ('cdn.example.net', 'output'))

    def test_a_redirect_target(self):
        f = SafeFetcher(allowed_hosts=('replicate.delivery',), resolver=public)
        req = request.Request('https://replicate.delivery' + SIGNED)
        with self.assertRaises(UnsafeURL) as cm:
            f.redirect_handler().redirect_request(req, None, 302, 'Found', {}, 'https://bucket.example.org' + SIGNED)
        self.assertEqual((cm.exception.host, cm.exception.hop), ('bucket.example.org', 'redirect'))


def status_line(exc):
    t = R.ReplicateImageTest.__new__(R.ReplicateImageTest)
    t.journal, t.env = Journal(), {}
    t.store = SimpleNamespace(get_bytes=lambda key: (_ for _ in ()).throw(KeyError('none')))

    def boom(h):
        raise exc
    t.provider = SimpleNamespace(poll=lambda h: SimpleNamespace(status='SUCCEEDED'), collect=boom)
    with unittest.TestCase().assertLogs('omni_prod.providers.replicate_image_test', level='WARNING') as logs:
        try:
            t.status('acct')
        except Exception:
            pass
    return logs.output[0]


class TheLogLine(unittest.TestCase):
    def refusal(self, url, hop_fetcher=None):
        try:
            provider()._download(url)
        except ValueError as exc:
            return exc
        self.fail('not refused')

    def assert_clean(self, line):
        for bad in ('/', '?', '&', '=deadbeef', 'token', 'xezq', 'secret', 'Signature', 'https'):
            self.assertNotIn(bad, line.split('replicate_image_test_status_failed', 1)[1])

    def test_host_and_hop_are_logged_and_nothing_else(self):
        line = status_line(self.refusal('https://cdn.example.net' + SIGNED))
        self.assertIn('stage=collect_and_download type=ValueError reason=url_host_not_allowed '
                      'host=cdn.example.net hop=output', line)
        self.assert_clean(line)

    def test_a_redirect_is_named_as_one(self):
        exc = ValueError('provider output URL rejected: host bucket.example.org is not in the provider allowlist')
        exc.url_host, exc.url_hop = 'bucket.example.org', 'redirect'
        line = status_line(exc)
        self.assertIn('reason=url_host_not_allowed host=bucket.example.org hop=redirect', line)
        self.assert_clean(line)

    def test_the_host_is_never_parsed_from_the_message(self):
        line = status_line(ValueError('provider output URL rejected: host leak.example is not in the provider allowlist'))
        self.assertIn('host=unknown hop=unknown', line)
        self.assertNotIn('leak.example', line)

    def test_a_field_that_is_not_a_bare_host_is_unknown(self):
        exc = ValueError('host x is not in the provider allowlist')
        exc.url_host, exc.url_hop = 'cdn.example.net/out.png?token=abc', 'output'
        line = status_line(exc)
        self.assertIn('host=unknown hop=output', line)
        self.assert_clean(line)

    def test_other_reasons_add_nothing(self):
        exc = ValueError('provider output is not a PNG, JPEG or WebP image')
        exc.url_host, exc.url_hop = 'cdn.example.net', 'output'
        line = status_line(exc)
        self.assertIn('reason=not_an_image', line)
        self.assertNotIn('host=', line)
        self.assertNotIn('hop=', line)


if __name__ == '__main__':
    unittest.main()
