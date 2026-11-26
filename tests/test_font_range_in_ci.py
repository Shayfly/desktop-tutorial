"""The font range's live checks stay where a skip fails (the owner, 2026-11-25, the font question): the licences and
weights Google Fonts states for the allowed list, and every Hebrew pair on the section library's page, run only with
a browser and the network (tests/test_font_pair_range_live.py), and v24-ci has no browser. browser-python's
`font-range` job runs them, fails on a skip, and runs the font range's browser-only controls; its steps fit inside its
own cap, and every browser-only control of the spec is one of the job's tests."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / '.github' / 'workflows' / 'browser-python.yml').read_text(encoding='utf-8'))
JOB = WORKFLOW['jobs']['font-range']
STEPS = {s.get('name'): s for s in JOB['steps']}
SPEC = json.loads((ROOT / 'tests' / 'negative_controls' / 'font_range.json').read_text(encoding='utf-8'))


class TheFontRangeIsCheckedInCI(unittest.TestCase):
    def test_the_job_runs_the_live_tests_on_every_pull_request_and_a_skip_fails_it(self):
        self.assertIn('pull_request', WORKFLOW.get('on') or WORKFLOW.get(True))
        self.assertIn('tests/test_font_pair_range_live.py', STEPS['Font range tests']['run'].split())
        guard = STEPS['No test may be skipped']
        self.assertEqual(guard['if'], 'always()')
        self.assertIn("ET.parse('fonts.xml')", guard['run'])
        self.assertIn('sys.exit(1 if skipped or failed or not cases else 0)', guard['run'])

    def test_the_browser_controls_run_there(self):
        step = STEPS['Negative controls (browser)']
        self.assertEqual(step['env']['NC_ENV'], 'browser')
        self.assertEqual(step['run'].strip(), 'NC_SCOPE=declared python scripts/run_negative_controls.py font_range')
        browser = [c for c in SPEC['controls'] if c.get('envs') == ['browser']]
        self.assertEqual(len(browser), 5)
        for c in browser:
            self.assertEqual(c['targets'], ['tests/test_font_pair_range_live.py'], c['id'])

    def test_the_steps_fit_inside_the_job(self):
        self.assertLessEqual(sum(s.get('timeout-minutes', 0) for s in JOB['steps']) + 1, JOB['timeout-minutes'])


if __name__ == '__main__':
    unittest.main()
