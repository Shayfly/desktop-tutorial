"""The Python checks that need a real Chromium run in CI (2026-11-21, the review of the content-document route): v24-ci
installs no Python playwright, so the section library's visual check and the content route's real-chain engine tests
skipped there, and the library's browser-only negative controls ran nowhere. browser-python runs them with a
bounded, retried Chromium install, fails on any skipped test, and runs the browser-only controls."""
import json
import pathlib
import re
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
BROWSER_ONLY = ('test_every_variant_in_every_direction_passes_every_gate_and_never_scrolls_sideways',
                'test_nothing_scrolls_sideways_in_any_direction_or_shape',
                'test_nothing_scrolls_sideways_on_a_phone_or_a_wide_screen',
                'test_round_two_holds_on_every_palette_at_phone_and_desktop_width',
                'test_the_production_visual_check_finds_nothing_it_enforces_on_a_phone_or_a_desktop',
                'test_the_purged_page_is_pixel_identical_to_the_full_stylesheet',
                'test_the_render_check_sees_every_element_settled_after_300ms')


class TheBrowserJob(unittest.TestCase):
    def setUp(self):
        wf = yaml.safe_load((ROOT / '.github/workflows/browser-python.yml').read_text(encoding='utf-8'))
        self.events = wf.get('on') or wf.get(True)
        self.job = wf['jobs']['browser-python']
        self.steps = self.job['steps']

    def run_of(self, name):
        return next(s for s in self.steps if s.get('name') == name)

    def test_it_runs_on_every_pull_request_within_the_ci_cost_limit(self):
        self.assertIn('pull_request', self.events)
        self.assertLessEqual(self.job['timeout-minutes'], 27)     # 20 until the library's 24 controls (2026-11-21)
        install = self.run_of('Install Chromium (bounded attempts, retried)')
        per_try = int(re.search(r'timeout (\d+) python -m playwright install --with-deps chromium', install['run']).group(1))
        self.assertLessEqual(per_try * 3 + 30, install['timeout-minutes'] * 60)
        wait = int(re.search(r'DPkg::Lock::Timeout "(\d+)"', install['run']).group(1))
        self.assertLess(wait, per_try)
        self.assertLess(install['run'].index('DPkg::Lock::Timeout'), install['run'].index('for attempt in 1 2 3'))
        self.assertTrue(install['run'].rstrip().endswith('exit 1'))
        self.assertLessEqual(sum(s.get('timeout-minutes', 0) for s in self.steps) + 1, self.job['timeout-minutes'])

    def test_the_browser_tests_run_and_none_may_be_skipped(self):
        tests = self.run_of('Browser tests')['run']
        self.assertIn('tests/test_section_library.py', tests)
        self.assertIn('tests/test_site_content_engine.py', tests)
        self.assertIn('tests/test_library_cookie_banner.py', tests)        # DECISIONS 14 b
        self.assertIn('--junitxml=browser.xml', tests)
        guard = self.run_of('No test may be skipped')
        self.assertEqual(guard['if'], 'always()')
        self.assertIn("sys.exit(1 if skipped or failed or not cases else 0)", guard['run'])

    def test_the_browser_only_controls_run_here(self):
        step = self.run_of('Negative controls (browser)')
        self.assertEqual(step['env']['NC_ENV'], 'browser')
        self.assertIn('run_negative_controls.py section_library', step['run'])
        # #541: visual_qa's viewport and widening tests need Chromium, which v24-ci's shards lack
        self.assertIn('run_negative_controls.py repair_converge_offscreen', step['run'])
        # its controls share test_visual_qa's fixed ports, so they run one at a time (run 45860673027)
        self.assertIn('NC_JOBS=1 NC_SCOPE=declared python scripts/run_negative_controls.py repair_converge_offscreen', step['run'])
        self.assertIn('run_negative_controls.py library_cookie_banner', step['run'])
        self.assertIn('exit $(( a | b ))', step['run'])                     # one failing spec fails the step
        # bundle 2 (warehouse 126): the typography spec's 4 browser controls run here too, and fail the step
        self.assertIn('NC_SCOPE=declared python scripts/run_negative_controls.py typography_126_129; c=$?', step['run'])
        self.assertIn('b=$(( b | c ))', step['run'])
        spec = json.loads((ROOT / 'tests/negative_controls/section_library.json').read_text(encoding='utf-8'))
        for control in spec['controls']:
            needs_browser = set(control['expect_failed']) <= set(BROWSER_ONLY)
            with self.subTest(control=control['id']):
                # a control that only a browser test can catch runs only where the browser is
                self.assertEqual(control.get('envs') == ['browser'], needs_browser)


if __name__ == '__main__':
    unittest.main()
