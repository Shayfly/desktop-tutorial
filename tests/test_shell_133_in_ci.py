"""Warehouse 133's mutation table stays tested in CI (2026-11-23): tests/shell_133_browser.cjs plants the four rows no
other test plants, and this file keeps it in the browser job and keeps its faults."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8')
CHECK = (ROOT / 'tests' / 'shell_133_browser.cjs').read_text(encoding='utf-8')


class TheShellCheckRuns(unittest.TestCase):
    def test_the_browser_job_runs_it(self):
        self.assertIn('      - run: node tests/shell_133_browser.cjs\n', CI)
        self.assertIn('node --check tests/shell_133_browser.cjs', CI)

    def test_it_plants_the_four_rows_and_fails_on_a_miss(self):
        for fault in ('secondary_yellow', 'secondary_looks_disabled', 'status_colour_only', 'failure_empty', 'raw_id_in_row'):
            self.assertIn(f"id: '{fault}'", CHECK)
        self.assertIn('was NOT caught', CHECK)


if __name__ == '__main__':
    unittest.main()
