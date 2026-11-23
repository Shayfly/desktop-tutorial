"""Warehouse 134's browser checks stay where a skip fails (2026-11-23): tests/test_game_kit.py plays the games and
plants game_probe's faults only with a browser, and v24-ci has none. browser-python runs it and its browser controls."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / '.github' / 'workflows' / 'browser-python.yml').read_text(encoding='utf-8')


class TheGamesArePlayedInCI(unittest.TestCase):
    def test_the_browser_job_runs_the_game_tests(self):
        line = next(l for l in CI.splitlines() if 'pytest' in l and '--junitxml=browser.xml' in l)
        self.assertIn('tests/test_game_kit.py', line.split())

    def test_the_browser_controls_run_there(self):
        self.assertIn('python scripts/run_negative_controls.py game_kit; c=$?', CI)
        self.assertIn('exit $(( a | b | c ))', CI)


if __name__ == '__main__':
    unittest.main()
