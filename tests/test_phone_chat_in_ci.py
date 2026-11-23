"""The owner's phone fixes stay tested in CI (2026-11-23): tests/phone_chat_browser.cjs plants the four faults no other
test plants (Enter sends on a phone, the page left pushed up, the height not measured, the card cut inside the chat),
and this file keeps it in the browser job with its faults."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8')
CHECK = (ROOT / 'tests' / 'phone_chat_browser.cjs').read_text(encoding='utf-8')


class ThePhoneCheckRuns(unittest.TestCase):
    def test_the_browser_job_runs_it(self):
        self.assertIn('      - run: node tests/phone_chat_browser.cjs\n', CI)
        self.assertIn('node --check tests/phone_chat_browser.cjs', CI)

    def test_it_plants_its_faults_and_fails_on_a_miss(self):
        for fault in ('enter_sends_on_phone', 'page_left_pushed_up', 'height_not_measured', 'card_cut_inside_chat'):
            self.assertIn(f"id: '{fault}'", CHECK)
        self.assertIn('was NOT caught', CHECK)


if __name__ == '__main__':
    unittest.main()
