"""The words of an image failure stay tested in CI (2026-11-23): tests/image_failure_words_browser.cjs is the only
test that tells a never-checked image (NOT_RUN) from a real mismatch, in Hebrew, English and Arabic, and plants the
two faults that prove it. This file keeps it in the browser job with its faults."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8')
CHECK = (ROOT / 'tests' / 'image_failure_words_browser.cjs').read_text(encoding='utf-8')


class TheImageFailureWordsAreChecked(unittest.TestCase):
    def test_the_browser_job_runs_it(self):
        self.assertIn('      - run: node tests/image_failure_words_browser.cjs\n', CI)
        self.assertIn('node --check tests/image_failure_words_browser.cjs', CI)

    def test_it_plants_its_faults_and_fails_on_a_miss(self):
        for fault in ('never_checked_reads_as_a_mismatch', 'a_real_mismatch_loses_what_was_seen'):
            self.assertIn(f"id: '{fault}'", CHECK)
        self.assertIn('was NOT caught', CHECK)

    def test_the_words_exist_in_every_platform_language(self):
        app = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
        self.assertEqual(app.count('image_not_described'), 4)   # he, en, ar and the branch that chooses it
