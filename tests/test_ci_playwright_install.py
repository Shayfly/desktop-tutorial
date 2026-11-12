"""browser-tests must not be skipped because the Chromium install hung (2026-10-27, runs 40538006896 and
40556234795): the browser cache is keyed by the pinned Playwright version, each attempt is bounded and retried,
and repeated failure fails the job."""
import pathlib
import re
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PlaywrightInstallTests(unittest.TestCase):
    def setUp(self):
        wf = yaml.safe_load((ROOT / '.github/workflows/v24-ci.yml').read_text())
        self.job = wf['jobs']['browser-tests']
        self.steps = self.job['steps']

    def step(self, pred):
        return next(s for s in self.steps if pred(s))

    def test_browser_cache_is_keyed_by_the_pinned_playwright_version(self):
        npm = self.step(lambda s: 'npm install' in s.get('run', ''))
        version = re.search(r'playwright@([\d.]+)', npm['run']).group(1)
        cache = self.step(lambda s: str(s.get('uses', '')).startswith('actions/cache@'))
        self.assertEqual(cache['with']['path'], '~/.cache/ms-playwright')
        self.assertIn(version, cache['with']['key'])
        self.assertLess(self.steps.index(cache), self.steps.index(self.step(lambda s: 'playwright install' in s.get('run', ''))))

    def test_install_is_bounded_retried_and_fails_loudly(self):
        inst = self.step(lambda s: 'playwright install' in s.get('run', ''))
        run = inst['run']
        self.assertRegex(run, r'for attempt in 1 2 3')
        per_try = int(re.search(r'timeout (\d+) npx playwright install --with-deps chromium', run).group(1))
        self.assertLessEqual(per_try * 3 + 30, inst['timeout-minutes'] * 60)       # all attempts fit the step
        self.assertLessEqual(inst['timeout-minutes'] + 6, self.job['timeout-minutes'])   # and the tests fit the job
        self.assertTrue(run.rstrip().endswith('exit 1'))
        self.assertNotIn('continue-on-error', inst)

    def test_browser_tests_still_run_after_install(self):
        runs = [s.get('run', '') for s in self.steps]
        self.assertIn('node tests/customer_flow_browser.cjs', runs)


if __name__ == '__main__':
    unittest.main()
