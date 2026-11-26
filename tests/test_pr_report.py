"""Every pull request carries the plan's 18-field delivery report (the owner's plan v3, S1.7, 2026-11-25).

scripts/check_pr_report.py reads the title and body; the "PR report" workflow runs it on every pull request, also when
the body alone is edited. Checked here on the real script and the real template and workflow files."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_pr_report as R  # noqa: E402

TEMPLATE = (ROOT / '.github' / 'pull_request_template.md').read_text(encoding='utf-8')
WORKFLOW = yaml.safe_load((ROOT / '.github' / 'workflows' / 'pr-report.yml').read_text(encoding='utf-8'))
TITLE = 'S1.7 A pull request template with the 18 fields'


def filled(**override) -> str:
    """The real template with every section filled; `override` replaces a section's text, None drops the section."""
    values = {f: f'{f} text.' for f in R.FIELDS}
    values.update({'Task ID': 'S1.7', 'Status': 'HOLD (waiting for the review)'})
    values.update(override)
    out = []
    for f in R.FIELDS:
        if values[f] is not None:
            out.append(f'## {f}\n<!-- guidance -->\n{values[f]}\n')
    return '\n'.join(out)


class TheTemplate(unittest.TestCase):
    def test_it_has_the_18_fields_of_section_17_in_order(self):
        self.assertEqual(len(R.FIELDS), 18)
        self.assertEqual(re.findall(r'^## (.+)$', TEMPLATE, re.M), list(R.FIELDS))

    def test_an_unfilled_template_does_not_pass(self):
        found = R.problems(TITLE, TEMPLATE)
        self.assertEqual(len(found), 18)                       # every section is still only guidance
        self.assertTrue(all('is empty' in p for p in found))


class TheCheck(unittest.TestCase):
    def test_a_filled_report_passes(self):
        self.assertEqual(R.problems(TITLE, filled()), [])
        for status in R.STATUSES:
            self.assertEqual(R.problems(TITLE, filled(Status=f'**{status}**: reason')), [], status)

    def test_a_missing_or_empty_field_fails(self):
        self.assertEqual(R.problems(TITLE, filled(Rollback=None)), ['the section "## Rollback" is missing'])
        self.assertEqual(R.problems(TITLE, filled(Cost='<!-- only guidance -->')), ['the section "## Cost" is empty'])

    def test_a_status_outside_the_three_fails(self):
        for bad in ('DONE', 'passed', 'ready to merge'):
            with self.subTest(status=bad):
                self.assertEqual(len(R.problems(TITLE, filled(Status=bad))), 1)

    def test_the_task_id_is_a_plan_id_and_is_in_the_title(self):
        self.assertIn('names no plan task id', R.problems(TITLE, filled(**{'Task ID': 'the template'}))[0])
        self.assertIn('the title names none', R.problems('A template', filled())[0])
        self.assertEqual(R.problems('S1.8 OWNERS', filled(**{'Task ID': 'S1.7, S1.8'})), [])

    def test_headings_are_matched_without_regard_to_case(self):
        self.assertEqual(R.problems(TITLE, filled().replace('## Status', '## status')), [])

    def test_the_command_line_fails_loudly(self):
        env = {k: v for k, v in os.environ.items() if k not in ('PR_TITLE', 'PR_BODY')}
        run = lambda extra: subprocess.run([sys.executable, str(ROOT / 'scripts' / 'check_pr_report.py')],
                                           env={**env, **extra}, capture_output=True, text=True)
        unread = run({})
        self.assertEqual(unread.returncode, 1)
        self.assertIn('could not be read', unread.stdout)               # no body is an error, never a pass
        bad = run({'PR_TITLE': TITLE, 'PR_BODY': filled(Status='DONE')})
        self.assertEqual(bad.returncode, 1)
        good = run({'PR_TITLE': TITLE, 'PR_BODY': filled()})
        self.assertEqual(good.returncode, 0, good.stdout)
        self.assertIn('::notice title=PR report::all 18 fields present; status HOLD', good.stdout)


class TheWorkflow(unittest.TestCase):
    def test_it_runs_on_every_pull_request_and_on_an_edited_body(self):
        on = WORKFLOW.get('on') or WORKFLOW.get(True)
        self.assertEqual(set(on), {'pull_request'})
        self.assertIn('edited', on['pull_request']['types'])
        self.assertIn('synchronize', on['pull_request']['types'])
        self.assertNotIn('paths', on['pull_request'])                  # never skipped for some files

    def test_the_body_reaches_the_script_through_the_environment_only(self):
        step = WORKFLOW['jobs']['report']['steps'][-1]
        self.assertEqual(step['run'], 'python3 scripts/check_pr_report.py')
        self.assertNotIn('${{', step['run'])                           # no injection of the body into the shell
        self.assertEqual(step['env']['PR_BODY'], '${{ github.event.pull_request.body }}')
        self.assertNotIn('continue-on-error', step)
        self.assertNotIn('continue-on-error', WORKFLOW['jobs']['report'])


if __name__ == '__main__':
    unittest.main()
