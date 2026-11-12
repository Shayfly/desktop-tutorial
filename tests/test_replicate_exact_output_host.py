"""#324 fix (Michael 2026-11-12 16:36): Replicate returns its output from one Cloudflare R2 bucket. That host is
allowed EXACTLY -- an '=' entry -- so neither R2 as a whole nor any subdomain of the bucket host gets in. The
suffix entries (replicate.delivery) keep their meaning."""
import unittest

from omni_prod.providers.image_provider import build_image_provider
from omni_prod.safe_fetch import UnsafeURL, _host_allowed

R2 = 'ai-gateway-outputs.0d37909e38d3e99c29fa2cd343ac421a.r2.cloudflarestorage.com'
TOKEN = {'REPLICATE_API_TOKEN': 'r8_' + 'x' * 37, 'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1'}


def public(host, port, proto=None):
    return [(2, 1, 6, '', ('93.184.216.34', port))]


class Journal:
    def find(self, key):
        return None


def fetcher():
    f = build_image_provider(TOKEN, journal=Journal()).fetcher   # the allowlist the image test really uses
    f.resolver = public
    return f


class TheBucketHost(unittest.TestCase):
    def refused(self, url):
        with self.assertRaises(UnsafeURL) as cm:
            fetcher().validate(url)
        self.assertIn('not in the provider allowlist', str(cm.exception))

    def test_r2_on_its_own_is_refused(self):
        self.refused('https://r2.cloudflarestorage.com/out-0.png')

    def test_a_subdomain_of_the_bucket_host_is_refused(self):
        self.refused(f'https://x.{R2}/out-0.png')

    def test_the_full_host_is_accepted(self):
        fetcher().validate(f'https://{R2}')

    def test_a_path_and_parameters_on_that_host_are_accepted(self):
        fetcher().validate(f'https://{R2}/p/out-0.webp?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature=deadbeef')

    def test_other_buckets_and_accounts_are_refused(self):
        for host in ('other-bucket.0d37909e38d3e99c29fa2cd343ac421a.r2.cloudflarestorage.com',
                     'ai-gateway-outputs.ffffffffffffffffffffffffffffffff.r2.cloudflarestorage.com',
                     R2 + '.evil.com', 'evil' + R2):
            with self.subTest(host=host):
                self.refused(f'https://{host}/out-0.png')

    def test_replicate_suffix_entries_still_work(self):
        for host in ('replicate.delivery', 'pbxt.replicate.delivery', 'api.replicate.com'):
            with self.subTest(host=host):
                fetcher().validate(f'https://{host}/out-0.png')
        self.refused('https://evilreplicate.delivery/out-0.png')


class TheMechanism(unittest.TestCase):
    def test_exact_entry_matches_only_itself(self):
        self.assertTrue(_host_allowed('a.example', ['=a.example']))
        self.assertFalse(_host_allowed('b.a.example', ['=a.example']))
        self.assertFalse(_host_allowed('example', ['=a.example']))

    def test_suffix_entry_keeps_subdomains(self):
        self.assertTrue(_host_allowed('b.a.example', ['a.example']))
        self.assertTrue(_host_allowed('b.a.example', ['.a.example']))
        self.assertFalse(_host_allowed('ba.example', ['a.example']))

    def test_the_bucket_is_listed_exactly_never_as_a_suffix(self):
        hosts = fetcher().allowed_hosts
        self.assertIn('=' + R2, hosts)
        self.assertNotIn(R2, hosts)
        self.assertFalse(any(h.lstrip('=.').endswith('r2.cloudflarestorage.com') and not h.startswith('=')
                             for h in hosts))

    def test_no_entries_still_means_no_allowlist(self):
        self.assertTrue(_host_allowed('anything.example', []))


if __name__ == '__main__':
    unittest.main()


class MalformedEntriesNeverWiden(unittest.TestCase):
    """Michael 2026-11-12 16:49: '=' with no host, duplicates and blanks are dropped quietly -- and dropping never
    turns into an empty list that allows everything (the classic silent failure)."""

    def test_bare_equals_allows_nothing(self):
        self.assertFalse(_host_allowed('anything.example', ['=']))
        self.assertFalse(_host_allowed('', ['=']))

    def test_blanks_and_spaces_allow_nothing(self):
        for entries in ([''], ['   '], [' ', ''], ['= '], ['a b.example'], ['=a b.example'], ['*.example'],
                        ['=*.example'], ['.'], ['=.'], ['=.a.example'], ['a..example'], ['https://a.example']):
            with self.subTest(entries=entries):
                self.assertFalse(_host_allowed('a.example', entries))
                self.assertFalse(_host_allowed('evil.example', entries))

    def test_bad_entries_are_dropped_and_good_ones_kept(self):
        entries = ['=', '', '  =A.Example  ', '=a.example', 'replicate.delivery', 'replicate.delivery', '= ']
        self.assertTrue(_host_allowed('a.example', entries))
        self.assertFalse(_host_allowed('x.a.example', entries))
        self.assertTrue(_host_allowed('pbxt.replicate.delivery', entries))
        self.assertFalse(_host_allowed('evil.example', entries))

    def test_duplicates_are_kept_once(self):
        from omni_prod.safe_fetch import _allowlist
        self.assertEqual(_allowlist(['=a.example', ' =A.example', 'b.example', '.b.example'])[1],
                         (('exact', 'a.example'), ('suffix', 'b.example')))

    def test_a_set_but_blank_variable_never_means_no_allowlist(self):
        from omni_prod.providers.image_provider import ImageProviderConfig
        for value in (',', ' , ', '=', '= , ='):
            with self.subTest(value=value):
                env = {**TOKEN, 'OMNI_IMAGE_PROVIDER_OUTPUT_HOSTS': value}
                f = build_image_provider(env, journal=Journal()).fetcher
                f.resolver = public
                with self.assertRaises(UnsafeURL):
                    f.validate('https://evil.example/out.png')
                with self.assertRaises(UnsafeURL):
                    f.validate(f'https://{R2}/out.png')          # the configured value replaced the default
                self.assertTrue(ImageProviderConfig.from_env(env).output_hosts)

    def test_an_unset_variable_still_gets_the_default(self):
        fetcher().validate(f'https://{R2}/out.png')
