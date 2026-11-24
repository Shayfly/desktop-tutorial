"""Critical path freshness (2026-11-21): post-deploy verify-replay -- no model calls, a one-off container, the live
worker untouched -- runs by itself every day; every other stage of postdeploy-checks.yml stays manual. Above all the
paid stage (a real build with model spend) must never run on a schedule. The workflow is read as committed.
Mutations: tests/negative_controls/replay_daily.json."""
import re
import unittest
from pathlib import Path

import yaml

WF = Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'postdeploy-checks.yml'


class ReplayDaily(unittest.TestCase):
    def setUp(self):
        self.text = WF.read_text(encoding='utf-8')
        self.doc = yaml.safe_load(self.text)
        self.on = self.doc[True] if True in self.doc else self.doc['on']
        self.job = self.doc['jobs']['checks']

    def test_it_runs_every_day(self):
        self.assertRegex(self.on['schedule'][0]['cron'], r'^\d+ \d+ \* \* \*$')
        self.assertIn("github.event_name == 'schedule'", self.job['if'])

    def test_only_verify_replay_defaults_on_a_schedule(self):
        conds = [str(s.get('if', '')) for s in self.job['steps']]
        defaulted = [c for c in conds if "inputs.stage ||" in c]
        self.assertEqual(len(defaulted), 4)
        self.assertTrue(all("|| 'verify-replay') == 'verify-replay'" in c for c in defaulted))
        replay = next(s for s in self.job['steps'] if 'Re-verify stored versions' in s.get('name', ''))
        self.assertEqual(replay['env']['N'], "${{ inputs.versions || '10' }}")

    def test_the_paid_and_free_stages_never_run_by_themselves(self):
        for stage in ('free', 'paid', 'crash', 'cancel-build', 'economics', 'spend-audit'):
            step = [s for s in self.job['steps'] if str(s.get('if', '')) == f"inputs.stage == '{stage}'"]
            self.assertEqual(len(step), 1, stage)
        self.assertFalse(re.search(r"inputs\.stage \|\| '(free|paid|crash)'", self.text))


if __name__ == '__main__':
    unittest.main()
