"""A2 1.1-1.3, offline (docs/spec/gemini-a2.md): search, verify and capture against sites served from this machine.

The browser tests run in a real Chromium. Where Chromium or Playwright is missing they are skipped -- except when
A2_REQUIRE_BROWSER=1 (the a2-offline CI job), where a missing browser FAILS: a skipped check is never a pass.
"""
import hashlib
import importlib.util
import os
import unittest

from omni_prod.a2 import search
from omni_prod.a2.capture import VIEWPORTS, capture, png_size
from omni_prod.a2.contract import A2ContractError, candidate_id, checked
from omni_prod.memory_adapters import MemoryArtifactStore
from tests.a2_offline_sites import HEAVY_BYTES, SLOW_SECONDS, Sites, url


def _search(n_good=34, extra=()):
    entries = [(url(f'good-{i}'), 1 + i % 3) for i in range(n_good)] + list(extra)
    return search.from_library(vertical='butcher', category='retail', audience='public', style='warm',
                               entries=entries, description='האטליז של סבא שמעון, טלפון 0504000162')


class Search(unittest.TestCase):
    def test_enough_candidates_in_all_three_tiers_is_ok(self):
        doc = _search()
        self.assertEqual(doc['coverage'], {'tier1': 12, 'tier2': 11, 'tier3': 11, 'status': 'ok'})
        self.assertEqual([q['tier'] for q in doc['queries']], [1, 2, 3])
        self.assertEqual(doc['candidates'][0]['candidate_id'], candidate_id(url('good-0')))

    def test_fewer_than_thirty_is_insufficient(self):
        self.assertEqual(_search(20)['coverage']['status'], 'insufficient')

    def test_a_tier_that_returned_nothing_is_said_and_is_not_ok(self):
        doc = search.from_library(vertical='butcher', category='retail', audience='public', style='warm',
                                  entries=[(url(f'good-{i}'), 1 + i % 2) for i in range(40)])
        self.assertEqual(doc['queries'][2], {'tier': 3, 'language': 'en', 'returned': 0})
        self.assertEqual(doc['coverage']['status'], 'insufficient')

    def test_more_than_sixty_is_cut_and_counted(self):
        doc = _search(70)
        self.assertEqual((len(doc['candidates']), doc['truncated']), (60, 10))

    def test_the_customers_words_never_reach_the_library(self):
        doc = _search()
        self.assertNotIn('שמעון', str(doc))
        self.assertNotIn('0504000162', str(doc))
        self.assertEqual(len(doc['inputs']['description_sha256']), 64)

    def test_live_search_is_not_wired(self):
        with self.assertRaises(search.LiveSearchNotEnabled):
            search.live(vertical='butcher')

    def test_a_document_outside_the_schema_stops_the_run(self):
        doc = _search()
        doc['candidates'][0]['url'] = 'http://insecure.example/'
        with self.assertRaises(A2ContractError):
            checked(doc)


def _browser_ready():
    if not importlib.util.find_spec('playwright'):
        return False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


REQUIRED = os.environ.get('A2_REQUIRE_BROWSER') == '1'
READY = _browser_ready()


class BrowserIsThereWhenRequired(unittest.TestCase):
    def test_the_ci_job_never_skips_the_browser(self):
        if REQUIRED:
            self.assertTrue(READY, 'A2_REQUIRE_BROWSER=1 but Chromium/Playwright cannot start')


@unittest.skipUnless(READY, 'needs Chromium and Playwright (the a2-offline CI job requires them)')
class Offline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from omni_prod.a2 import browser
        cls.sites = Sites()
        cls._cm = browser.session(offline_origin=cls.sites.origin)
        cls.session = cls._cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls._cm.__exit__(None, None, None)
        cls.sites.close()

    def _cand(self, name):
        u = url(name)
        return {'candidate_id': candidate_id(u), 'url': u, 'tier': 1, 'source': 'library'}

    def _verify(self, name):
        from omni_prod.a2.verify import verify
        return verify(self.session, self._cand(name))

    # ---------------------------------------------------------------- 1.2 verify
    def test_a_good_page_passes_with_its_measurements(self):
        v = self._verify('good-0')
        self.assertEqual((v['outcome'], v['http_status'], v['direction'], v['robots_allowed']), ('pass', 200, 'rtl', True))
        self.assertLess(v['load_ms_390'], 4000)
        self.assertGreater(v['transfer_bytes'], 500)

    def test_a_dead_site_is_rejected(self):
        v = self._verify('dead')
        self.assertEqual((v['outcome'], v['rejection']['reason_code'], v['rejection']['measured']),
                         ('reject', 'not_live', 404))

    def test_a_slow_site_is_rejected(self):
        v = self._verify('slow')
        self.assertEqual(v['rejection']['reason_code'], 'too_slow')
        self.assertGreaterEqual(v['rejection']['measured'], int(SLOW_SECONDS * 1000) - 200)

    def test_a_heavy_site_is_rejected(self):
        v = self._verify('heavy')
        self.assertEqual(v['rejection']['reason_code'], 'too_heavy')
        self.assertGreaterEqual(v['transfer_bytes'], HEAVY_BYTES)

    def test_robots_disallow_is_respected_and_the_page_is_never_requested(self):
        v = self._verify('blocked')
        self.assertEqual(v['rejection']['reason_code'], 'robots_disallowed')
        self.assertNotIn(('blocked.a2.test', '/'), self.sites.requests)
        self.assertIn(('blocked.a2.test', '/robots.txt'), self.sites.requests)

    def test_an_ltr_page_is_neutral_not_rtl(self):
        self.assertEqual(self._verify('ltr')['direction'], 'neutral')

    def test_nothing_leaves_this_machine(self):
        before = len(self.session.blocked)
        v = self._verify('external')
        self.assertEqual(v['outcome'], 'pass')
        self.assertEqual(sorted(set(self.session.blocked[before:])), ['cdn.example.com', 'images.example.org'])
        from omni_prod.a2.verify import verify
        real = verify(self.session, {'candidate_id': candidate_id('https://example.com/'), 'url': 'https://example.com/',
                                     'tier': 1, 'source': 'library'})
        self.assertEqual((real['rejection']['reason_code'], real['rejection']['measured']),
                         ('not_live', 'blocked_offline'))                     # never reached, not even robots.txt
        self.assertEqual(self.session.blocked[-1], 'example.com')

    # ---------------------------------------------------------------- 1.3 capture
    def test_two_full_page_screenshots_stored_by_their_digest(self):
        store = MemoryArtifactStore()
        c = capture(self.session, self._cand('good-1'), store)
        self.assertEqual(c['outcome'], 'pass')
        self.assertEqual([s['viewport_px'] for s in c['screenshots']], [w for w, _ in VIEWPORTS])
        for shot in c['screenshots']:
            key = next(k for k in store.objects if k.endswith(f"/{shot['viewport_px']}-{shot['sha256']}.png"))
            data = store.objects[key]
            self.assertEqual(hashlib.sha256(data).hexdigest(), shot['sha256'])
            self.assertEqual(png_size(data), (shot['viewport_px'], shot['height_px']))

    def test_a_missing_screenshot_is_never_a_pass(self):
        def fails_at_1440(page, width):
            if width == 1440:
                raise RuntimeError('browser crashed')
            return page.screenshot(full_page=True, type='png')
        c = capture(self.session, self._cand('good-2'), MemoryArtifactStore(), shoot=fails_at_1440)
        self.assertEqual((c['outcome'], c['rejection']['reason_code']), ('reject', 'capture_missing'))
        self.assertEqual(len(c['screenshots']), 1)

    def test_a_page_above_twenty_thousand_pixels_is_not_captured(self):
        c = capture(self.session, self._cand('tall'), MemoryArtifactStore())
        self.assertEqual(c['rejection']['reason_code'], 'capture_missing')

    # ---------------------------------------------------------------- the run
    def test_one_run_counts_every_rejection_by_its_reason(self):
        from omni_prod.a2 import collect
        extra = [(url(n), 2) for n in ('dead', 'slow', 'heavy', 'blocked', 'tall')]
        out = collect.run(self.session, _search(30, extra), MemoryArtifactStore())
        # #393 a2-offline NC6 failed twice in CI on this test and never locally: one assertion first that names every
        # rejection with what it measured, so a recurrence shows the site and the number, not only the test name
        why = [(d.get('url') or d.get('candidate_id'), d['rejection']['reason_code'], d['rejection'].get('measured'))
               for d in out['verified'] + out['captured'] if d['outcome'] != 'pass']
        self.assertEqual((out['funnel']['candidates'], out['funnel']['verified'], out['funnel']['captured'],
                          out['funnel']['rejected']),
                         (35, 31, 30, {'not_live': 1, 'too_slow': 1, 'too_heavy': 1, 'robots_disallowed': 1,
                                       'capture_missing': 1}),
                         f"rejected={why} blocked={out['blocked_hosts']}")
        self.assertEqual(out['funnel']['candidates'], 35)
        self.assertEqual(out['funnel']['verified'], 31)       # 30 good + tall (tall fails only at capture)
        self.assertEqual(out['funnel']['captured'], 30)
        self.assertEqual(out['funnel']['rejected'], {'not_live': 1, 'too_slow': 1, 'too_heavy': 1,
                                                     'robots_disallowed': 1, 'capture_missing': 1})

    def test_an_insufficient_search_opens_no_page(self):
        from omni_prod.a2 import collect
        seen = len(self.sites.requests)
        out = collect.run(self.session, _search(10), MemoryArtifactStore())
        self.assertEqual((out['stopped'], out['funnel']['verified'], len(self.sites.requests)),
                         ('search_insufficient', 0, seen))


if __name__ == '__main__':
    unittest.main()
