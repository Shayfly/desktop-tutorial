"""The platform UI's WCAG 2.2 AA check runs on every pull request and cannot be dropped quietly (the owner, 2026-11-22:
the platform UI moves to Claude Code; "נגישה לכל אדם"). tests/platform_a11y_browser.cjs needs axe-core, and the
browser job installs the pinned version next to Playwright."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8')
CHECK = (ROOT / 'tests' / 'platform_a11y_browser.cjs').read_text(encoding='utf-8')


class TheCheckRuns(unittest.TestCase):
    def test_the_browser_job_runs_it_and_installs_its_engine(self):
        self.assertIn('node tests/platform_a11y_browser.cjs', CI)
        self.assertIn('node --check tests/platform_a11y_browser.cjs', CI)
        self.assertRegex(CI, r'npm install [^\n]*axe-core@\d+\.\d+\.\d+')      # an exact version, never a range

    def test_it_judges_wcag_22_aa_at_three_widths_and_proves_itself(self):
        self.assertIn("'wcag22aa'", CHECK)
        self.assertIn('[320, 390, 1440]', CHECK)
        self.assertGreaterEqual(len(re.findall(r"\{ id: '[a-z_]+',", CHECK)), 7)      # the deliberate faults
        self.assertIn('was NOT caught', CHECK)                                          # an uncaught fault fails

    def test_the_design_review_fixes_run_too(self):
        self.assertIn('node tests/workspace_review_fixes_browser.cjs', CI)
        fixes = (ROOT / 'tests' / 'workspace_review_fixes_browser.cjs').read_text(encoding='utf-8')
        for fix in ('F1', 'F2', 'F3', 'F5'):
            self.assertIn(f'  async {fix}(browser, fix)', fixes)
        self.assertIn('also passes with its fix taken out', fixes)                    # each proves itself

    def test_every_platform_language_is_checked_whole(self):
        self.assertIn('node tests/ui_languages_browser.cjs', CI)
        self.assertIn("const LANGS = ['he', 'en', 'ar'];", CHECK)                          # accessibility in every language
        langs = (ROOT / 'tests' / 'ui_languages_browser.cjs').read_text(encoding='utf-8')
        self.assertIn("['he', 'en', 'ar']", langs)
        self.assertIn('was NOT caught', langs)


if __name__ == '__main__':
    unittest.main()
