"""#569 (warehouse 129): the Arabic page's browser tests run in a job that has a browser, and the controls that need one say so.

Found by negative-controls (2) (job 141029594446): script_layer_129 NC3, NC6, NC7 and NC9 expect tests of
tests/test_script_layer_129.py::InABrowser, which skip where there is no Chromium (v24-ci's shards), so they were
"DID NOT RUN: expected tests were skipped". Root causes: (1) those four controls had no `envs: ["browser"]`; (2) the
deeper gap: no CI job with a browser ran tests/test_script_layer_129.py at all, so InABrowser skipped everywhere and the
computed-direction / letter-spacing checks were never executed. browser-python runs the file now (a skip fails the job)
and runs the browser-only controls."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = yaml.safe_load((ROOT / '.github' / 'workflows' / 'browser-python.yml').read_text(encoding='utf-8'))
STEPS = {s.get('name'): s for s in WORKFLOW['jobs']['browser-python']['steps']}
SPEC = json.loads((ROOT / 'tests' / 'negative_controls' / 'script_layer_129.json').read_text(encoding='utf-8'))
TEST_SRC = (ROOT / 'tests' / 'test_script_layer_129.py').read_text(encoding='utf-8')


def browser_tests() -> set[str]:
    """The test methods of the classes that skip without Chromium (a skipUnless(chromium(), ...) decorator)."""
    out: set[str] = set()
    for m in re.finditer(r"@unittest\.skipUnless\(chromium\(\)[^\n]*\)\nclass \w+\([^\n]*\):\n(.*?)(?=\n(?:class |@unittest|def |if __name__)|\Z)",
                         TEST_SRC, re.S):
        out |= set(re.findall(r'\n    def (test_\w+)\(', m.group(1)))
    return out


class TheBrowserTestsRunWhereThereIsABrowser(unittest.TestCase):
    def test_the_browser_job_runs_the_file_on_every_pull_request_and_a_skip_fails_it(self):
        self.assertIn('pull_request', WORKFLOW.get('on') or WORKFLOW.get(True))
        self.assertIn('tests/test_script_layer_129.py', STEPS['Browser tests']['run'].split())
        guard = STEPS['No test may be skipped']
        self.assertEqual(guard['if'], 'always()')
        self.assertIn('sys.exit(1 if skipped or failed or not cases else 0)', guard['run'])

    def test_the_spec_runs_in_the_browser_job_and_a_failing_spec_fails_the_step(self):
        step = STEPS['Negative controls (browser)']
        self.assertEqual(step['env']['NC_ENV'], 'browser')
        self.assertIn('NC_SCOPE=declared python scripts/run_negative_controls.py script_layer_129; e=$?', step['run'])
        self.assertRegex(step['run'], r'c=\$\(\( c \| d \| e \)\)')

    def test_the_steps_fit_inside_the_job(self):
        job = WORKFLOW['jobs']['browser-python']
        self.assertLessEqual(sum(s.get('timeout-minutes', 0) for s in job['steps']) + 1, job['timeout-minutes'])


class TheControlsThatNeedAChromium(unittest.TestCase):
    def test_the_file_has_browser_tests_to_find(self):
        self.assertGreaterEqual(len(browser_tests()), 3, browser_tests())

    def test_a_control_expecting_a_browser_test_is_declared_browser_and_only_that_one(self):
        needs = browser_tests()
        wrong = [c['id'] for c in SPEC['controls'] if bool(set(c['expect_failed']) & needs) != (c.get('envs') == ['browser'])]
        self.assertEqual(wrong, [])
        self.assertEqual([c['id'] for c in SPEC['controls'] if c.get('envs') == ['browser']], ['NC3', 'NC6', 'NC7', 'NC9'])


if __name__ == '__main__':
    unittest.main()
