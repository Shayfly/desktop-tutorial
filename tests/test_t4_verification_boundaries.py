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
        self.assertEqual(len(nc), 5)
        self.assertEqual(set(nc.values()), {'NO_CHECKS'})

    def test_every_positive_control_passes_with_a_real_check(self):
        pos = [e for e in self.out['t4_extra'] if e['case'].startswith('positive_') and e['expected'] == 'PASS']
        self.assertEqual(len(pos), 5)
        self.assertEqual([e['case'] for e in pos if e['observed'].get('verdict') != 'PASS'], [])

    def test_matts_three_blockers(self):
        got = {e['case']: e['observed'].get('verdict') for e in self.out['t4_extra']}
        self.assertEqual(got['positive_content_site_page_observed_no_forms'], 'PASS')   # a content site is judged
        self.assertEqual(got['content_site_with_a_javascript_error'], 'FAIL')         # ... and can fail
        self.assertEqual(got['behavior_no_acceptance_and_no_plan'], 'NO_CHECKS')      # no longer the input report
        self.assertEqual(got['behavior_non_python_runtime'], 'FAIL')
        self.assertEqual(got['preview_non_python_runtime'], 'FAIL')

    def test_the_group_reraises_control_exceptions(self):
        g = [e for e in self.out['t4_extra'] if e['case'].startswith('group_propagates_')]
        self.assertEqual(len(g), 3)
        self.assertEqual([e['case'] for e in g if e['boundary_violated']], [])

    def test_the_committed_evidence_artifact_is_this_code_and_this_result(self):
        # Matt reads evidence, he does not run it: smoke/t4-verification-boundaries.{json,md} must describe exactly
        # the code in this commit (source SHA-256) and exactly what the probe observes now (per case).
        import hashlib
        art = json.loads((ROOT / 'smoke' / 't4-verification-boundaries.json').read_text(encoding='utf-8'))
        for path, digest in art['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest, path)
        # The MD table must carry the JSON's hash for every key (2026-11-03: the MD kept behavior_acceptance.py at
        # 32454280 after bbe8586 moved the JSON to 31a069ae, and nothing noticed because only the JSON was read).
        md = (ROOT / 'smoke' / 't4-verification-boundaries.md').read_text(encoding='utf-8')
        import re
        table = {p: (h, line) for p, h, line in re.findall(r'^\| `([^`]+)` \| `([0-9a-f]{64})` \| ([^|]*) \|$', md, re.M)}
        for path, digest in art['source_sha256'].items():
            self.assertEqual(table.get(path, (None,))[0], digest, f'smoke/t4-verification-boundaries.md row for {path}')
        # The line a finding points at is part of the lock too (founder 2026-11-03 10:07): every key of source_sha256
        # is in source_lines; a number must match the MD; null means the MD claims no line for that file anywhere.
        lines = art['source_lines']
        self.assertEqual(sorted(lines), sorted(art['source_sha256']))
        for path, line in lines.items():
            cell = table[path][1].strip()
            if line is None:
                self.assertFalse(re.search(r'\d', cell), f'MD claims line {cell!r} for {path}; the JSON says null')
                self.assertNotRegex(md, re.escape(path) + r':\d+', f'MD cites a line of {path}; the JSON says null')
            else:
                self.assertEqual(cell, str(line), f'MD line for {path}')
        now = {f['case']: ('MET' if not f['boundary_violated'] else 'VIOLATED') for f in self.out['findings']}
        now.update({e['case']: ('MET' if not e['boundary_violated'] else 'VIOLATED') for e in self.out['t4_extra']})
        self.assertEqual({r['id']: r['result'] for r in art['cases'] + art['t4_cases']}, now)
        self.assertEqual(len(art['cases']), 26)

    def test_exit_code_0(self):
        self.assertEqual(self.exit, 0)


if __name__ == '__main__':
    unittest.main()
