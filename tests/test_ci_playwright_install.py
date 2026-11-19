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
        self.assertIn('node tests/approval_one_truth_browser.cjs', runs)     # chat and panel: one approval state


class AStalledAttemptDoesNotLockOutTheRetries(unittest.TestCase):
    """#449 (run 44259745208): attempt 1 hit its 160 s bound on a slow apt mirror; its apt-get child lived on and
    held /var/lib/dpkg/lock-frontend, so attempts 2 and 3 failed in 0 s on "Could not get lock" and the A2 browser
    tests were skipped. Every bounded, retried Chromium install makes apt wait for the dpkg lock, for less than one
    attempt, before its first attempt."""

    INSTALLS = (('.github/workflows/a2-offline.yml', 'a2-offline'), ('.github/workflows/v24-ci.yml', 'browser-tests'))

    def install_step(self, path, job):
        steps = yaml.safe_load((ROOT / path).read_text(encoding='utf-8'))['jobs'][job]['steps']
        return next(s['run'] for s in steps if 'playwright install --with-deps' in s.get('run', ''))

    def test_apt_waits_for_the_dpkg_lock_before_the_first_attempt(self):
        for path, job in self.INSTALLS:
            with self.subTest(path=path):
                run = self.install_step(path, job)
                m = re.search(r"""echo 'DPkg::Lock::Timeout "(\d+)";' \| sudo tee /etc/apt/apt\.conf\.d/[\w.-]+""", run)
                self.assertIsNotNone(m, f'{path}: no dpkg lock wait; a stalled attempt locks out every retry')
                self.assertLess(m.start(), run.index('for attempt in 1 2 3'), f'{path}: the lock wait is set after the loop')

    def test_the_lock_wait_ends_inside_one_attempt(self):
        for path, job in self.INSTALLS:
            with self.subTest(path=path):
                run = self.install_step(path, job)
                wait = int(re.search(r'DPkg::Lock::Timeout "(\d+)"', run).group(1))
                per_try = int(re.search(r'timeout (\d+) (?:npx|python -m) playwright install --with-deps chromium', run).group(1))
                self.assertGreater(wait, 0)
                self.assertLess(wait, per_try, f'{path}: apt must report the lock itself, not be killed by the attempt bound')


if __name__ == '__main__':
    unittest.main()
