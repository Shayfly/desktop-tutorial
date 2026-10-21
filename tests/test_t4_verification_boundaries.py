"""T4 (Matt's design, founder 2026-10-21): 0 false successes, and the positive controls pass with a REAL check.

Runs the red-team boundary probe (tools/redteam_verification_boundaries.py, from #74, sharpened for case 23) as a
process, exactly as an auditor would, and requires:
  * the 26 original cases: every one meets its expected verdict (FAIL, or the control exception propagates);
  * NO_CHECKS is its own verdict (browser zero forms, behaviour PASS with zero checks, visual nothing inspected) and is
    never PASS; a group with one NO_CHECKS stage is not PASS either;
  * every positive control holds at least one real passing check and PASSES (a system that fails everything is not a
    fix);
  * the group re-raises control exceptions.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class T4VerificationBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = subprocess.run([sys.executable, str(ROOT / 'tools' / 'redteam_verification_boundaries.py')],
                           capture_output=True, text=True, timeout=300, cwd=ROOT)
        cls.exit, cls.out = p.returncode, json.loads(p.stdout)

    def test_the_26_cases_meet_their_expected_verdict(self):
        self.assertEqual(self.out['cases'], 26)
        self.assertEqual([f['case'] for f in self.out['findings'] if f['boundary_violated']], [])

    def test_zero_false_successes(self):
        false = [f['case'] for f in self.out['findings'] if f['observed'].get('passed') is True]
        self.assertEqual(false, [])

    def test_no_checks_is_its_own_verdict_and_never_pass(self):
        nc = {e['case']: e['observed'].get('verdict') for e in self.out['t4_extra'] if e['expected'] == 'NO_CHECKS'}
        self.assertEqual(len(nc), 4)
        self.assertEqual(set(nc.values()), {'NO_CHECKS'})

    def test_every_positive_control_passes_with_a_real_check(self):
        pos = [e for e in self.out['t4_extra'] if e['case'].startswith('positive_') and e['expected'] == 'PASS']
        self.assertEqual(len(pos), 4)
        self.assertEqual([e['case'] for e in pos if e['observed'].get('verdict') != 'PASS'], [])

    def test_the_group_reraises_control_exceptions(self):
        g = [e for e in self.out['t4_extra'] if e['case'].startswith('group_propagates_')]
        self.assertEqual(len(g), 3)
        self.assertEqual([e['case'] for e in g if e['boundary_violated']], [])

    def test_exit_code_0(self):
        self.assertEqual(self.exit, 0)


if __name__ == '__main__':
    unittest.main()
