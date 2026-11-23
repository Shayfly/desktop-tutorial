"""Warehouse 134's browser checks stay where a skip fails (2026-11-23): tests/test_game_kit.py plays the games and
plants game_probe's faults only with a browser, and v24-ci has none. browser-python's `game-kit` job runs the tests,
fails on a skip, and runs the game kit's browser-only controls; its steps fit inside its own cap."""
from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
JOB = yaml.safe_load((ROOT / '.github' / 'workflows' / 'browser-python.yml').read_text(encoding='utf-8'))['jobs']['game-kit']
STEPS = {s.get('name'): s for s in JOB['steps']}


class TheGamesArePlayedInCI(unittest.TestCase):
    def test_the_job_runs_the_game_tests_and_a_skip_fails_it(self):
        self.assertIn('tests/test_game_kit.py', STEPS['Game tests']['run'].split())
        guard = STEPS['No test may be skipped']
        self.assertEqual(guard['if'], 'always()')
        self.assertIn("ET.parse('games.xml')", guard['run'])
        self.assertIn('sys.exit(1 if skipped or failed or not cases else 0)', guard['run'])

    def test_the_browser_controls_run_there(self):
        step = STEPS['Negative controls (browser)']
        self.assertEqual(step['env']['NC_ENV'], 'browser')
        self.assertEqual(step['run'].strip(), 'python scripts/run_negative_controls.py game_kit')

    def test_the_steps_fit_inside_the_job(self):
        self.assertLessEqual(sum(s.get('timeout-minutes', 0) for s in JOB['steps']) + 1, JOB['timeout-minutes'])


if __name__ == '__main__':
    unittest.main()
