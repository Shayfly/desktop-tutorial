"""The platform stays usable by anyone who can read, and that check cannot be dropped quietly (the owner, 2026-11-22:
"מקטן שיודע לקרוא ועד למבוגר שלא מבין בכלל"; inbox 001 §6: zero technical terms to start and finish).
tests/platform_for_everyone_browser.cjs measures it in a real browser; this file keeps it in CI and keeps its teeth."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8')
CHECK = (ROOT / 'tests' / 'platform_for_everyone_browser.cjs').read_text(encoding='utf-8')
APP = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
PAGE = (ROOT / 'omni_prod' / 'assets' / 'index.html').read_text(encoding='utf-8')


class TheCheckRuns(unittest.TestCase):
    def test_the_browser_job_runs_it(self):
        self.assertIn('node tests/platform_for_everyone_browser.cjs', CI)
        self.assertIn('node --check tests/platform_for_everyone_browser.cjs', CI)

    def test_it_measures_the_five_things_and_proves_itself(self):
        for check in ('async first(', 'async words(', 'async text(', 'async targets(', 'async size(', 'async look('):
            self.assertIn(check, CHECK)
        self.assertIn('r.width < 43.5 || r.height < 43.5', CHECK)                 # 44px, not WCAG's 24px
        self.assertIn('(isSmall ? 14 : 16)', CHECK)                                # 16px reading text
        self.assertGreaterEqual(len(re.findall(r"\{ id: '[a-z_]+', check: '[a-z]+'", CHECK)), 7)
        self.assertIn('was NOT caught', CHECK)                                     # an uncaught fault fails


class NoNameBeforeTheFirstMessage(unittest.TestCase):
    def test_the_page_has_no_naming_step(self):
        for gone in ('id="firstProjectName"', 'id="newProjectDialog"', 'id="newProjectName"'):
            self.assertNotIn(gone, PAGE)

    def test_the_first_message_creates_and_names_the_project(self):
        self.assertIn('try { await createProject(titleFrom(text)); }', APP)


if __name__ == '__main__':
    unittest.main()
