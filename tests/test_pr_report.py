"""Every pull request carries the plan's 18-field delivery report (the owner's plan v3, S1.7, 2026-11-25).

scripts/check_pr_report.py reads the title and body; the "PR report" workflow runs it on every pull request, also when
the body alone is edited. Checked here on the real script and the real template and workflow files. The cases come
from the review of #532 (2026-11-25): each one passed or failed wrongly before."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_pr_report as R  # noqa: E402

TEMPLATE = (ROOT / '.github' / 'pull_request_template.md').read_text(encoding='utf-8')
WORKFLOW_TEXT = (ROOT / '.github' / 'workflows' / 'pr-report.yml').read_text(encoding='utf-8')
WORKFLOW = yaml.safe_load(WORKFLOW_TEXT)
TITLE = 'S1.7 A pull request template with the 18 fields'
SCRIPT = str(ROOT / 'scripts' / 'check_pr_report.py')


def filled(**override) -> str:
    """The real template with every section filled; `override` replaces a section's text, None drops the section."""
    values = {f: f'{f} text.' for f in R.FIELDS}
    values.update({'Task ID': 'S1.7', 'Status': 'HOLD (waiting for the review)'})
    values.update(override)
    out = []
    for f in R.FIELDS:
        if values[f] is not None:
            out.append(f'## {f}\n<!-- guidance\nover two lines -->\n{values[f]}\n')
    return '\n'.join(out)


def plain(**override) -> str:
    """The 18 sections with text and no guidance comment."""
    values = {f: f'{f} text.' for f in R.FIELDS}
    values.update({'Task ID': 'S1.7', 'Status': 'PASS'})
    values.update(override)
    return '\n'.join(f'## {f}\n{values[f]}\n' for f in R.FIELDS)


def run(*args, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k not in ('PR_TITLE', 'PR_BODY', 'PR_AUTHOR')}
    return subprocess.run([sys.executable, SCRIPT, *args], env={**env, **(env_extra or {})}, capture_output=True,
                          text=True)


def event_file(directory: str, title, body, login='someone') -> str:
    path = os.path.join(directory, 'event.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump({'action': 'edited', 'pull_request': {'title': title, 'body': body, 'user': {'login': login}}}, fh)
    return path


class TheTemplate(unittest.TestCase):
    def test_it_has_the_18_fields_of_section_17_in_order(self):
        self.assertEqual(len(R.FIELDS), 18)
        self.assertEqual(re.findall(r'^## (.+)$', TEMPLATE, re.M), list(R.FIELDS))

    def test_an_unfilled_template_does_not_pass(self):
        found = R.problems(TITLE, TEMPLATE)
        self.assertEqual(len(found), 18)                       # every section is still only guidance
        self.assertTrue(all('is empty' in p for p in found))

    def test_the_guidance_with_its_marks_removed_does_not_pass(self):
        # an author who deletes "<!--" and "-->" instead of replacing the guidance
        bare = TEMPLATE.replace('<!--', '').replace('-->', '')
        found = R.problems(TITLE, bare)
        self.assertEqual(found, ['"## Status" must begin with PASS, FAIL or HOLD as a whole word, not '
                                 "'One of the three words first, then the r'"])

    def test_the_reviewer_guidance_follows_the_owner_rule(self):
        reviewer = TEMPLATE.split('## Reviewer', 1)[1].split('## Blockers', 1)[0]
        self.assertIn('no independent reviewer', reviewer)
        self.assertIn('OWNERS.md rule 1', reviewer)
        self.assertIn("the author's own check", reviewer)
        self.assertNotIn('ChatGPT', reviewer)
        self.assertNotIn('"pending" until', reviewer)


class TheSections(unittest.TestCase):
    def test_a_filled_report_passes(self):
        self.assertEqual(R.problems(TITLE, filled()), [])
        for status in R.STATUSES:
            self.assertEqual(R.problems(TITLE, filled(Status=f'**{status}**: reason')), [], status)
            self.assertEqual(R.problems(TITLE, filled(Status=f'`{status}` (reason)')), [], status)
            self.assertEqual(R.problems(TITLE, filled(Status=status)), [], status)
            for after in (' reason', ': reason', '. Reason', ' - reason', '-reason', ' — reason'):
                self.assertEqual(R.problems(TITLE, filled(Status=status + after)), [], status + after)

    def test_a_missing_or_empty_field_fails(self):
        self.assertEqual(R.problems(TITLE, filled(Rollback=None)), ['the section "## Rollback" is missing'])
        for empty in ('<!-- only guidance -->', '<!-- one\nand two -->', '   ', '### Details', '# x', '```\n```',
                      '~~~\n\n~~~', '---', '***', '<br>', '&nbsp;', '​', ' ', '<!-->', '<!--->', '-', '>'):
            with self.subTest(content=empty):
                self.assertEqual(R.problems(TITLE, filled(Cost=empty)), ['the section "## Cost" is empty'])

    def test_a_fenced_block_with_text_is_content(self):
        self.assertEqual(R.problems(TITLE, filled(Cost='```\nnone: nothing was spent\n```')), [])

    def test_comments_are_removed_from_the_whole_body_before_the_split(self):
        self.assertEqual(R.problems(TITLE, plain()), [])
        whole = '<!--\n' + plain() + '\n-->'                      # GitHub shows an empty description
        self.assertEqual(len(R.problems(TITLE, whole)), 18)
        self.assertTrue(all('is missing' in p for p in R.problems(TITLE, whole)))
        across = filled().replace('## Performance\n', '<!--\n## Performance\n').replace('## Deployment', '-->\n## Deployment')
        found = R.problems(TITLE, across)
        self.assertIn('the section "## Performance" is missing', found)
        self.assertNotIn('the section "## Cost" is empty', found)  # Cost keeps its own text
        # an unclosed comment ends at the next "-->" (here the next section's guidance), as on GitHub: the heading
        # "## Performance" is hidden and its text shows under Cost
        found = R.problems(TITLE, filled(Cost='<!-- todo'))
        self.assertEqual(found, ['the section "## Performance" is missing'])
        found = R.problems(TITLE, plain(Cost='<!-- todo'))
        self.assertIn('the section "## Cost" is empty', found)
        self.assertIn('the section "## Status" is missing', found)
        self.assertEqual(len(found), 7)                         # Cost, and the six sections after it

    def test_a_duplicate_section_fails(self):
        body = filled() + '\n## Status\r\nFAIL: the suite is red on this SHA\r\n'
        self.assertIn('the section "## Status" appears 2 times; write it once', R.problems(TITLE, body))
        other_case = filled().replace('## Status', '## status\nFAIL: red\n\n## Status')
        self.assertIn('the section "## Status" appears 2 times; write it once', R.problems(TITLE, other_case))

    def test_a_heading_inside_a_code_fence_is_text(self):
        evidence = 'the log:\n```\n## Status\nDONE\n```'
        self.assertEqual(R.problems(TITLE, filled(Evidence=evidence)), [])
        tilde = 'the log:\n~~~~\n## Rollback\n```\nstill inside\n~~~~'
        self.assertEqual(R.problems(TITLE, filled(Evidence=tilde)), [])

    def test_a_crlf_body_passes(self):
        crlf = filled().replace('\n', '\r\n')
        self.assertEqual(R.problems(TITLE, crlf), [])
        self.assertEqual(R.status_word(crlf), 'HOLD')
        self.assertEqual(R.problems(TITLE, filled().replace('\n', '\r')), [])

    def test_headings_are_matched_without_regard_to_case(self):
        self.assertEqual(R.problems(TITLE, filled().replace('## Status', '## status')), [])


class TheStatus(unittest.TestCase):
    def test_a_status_outside_the_three_fails(self):
        for bad in ('DONE', 'passed', 'ready to merge', 'PASSED', 'PASSING', 'HOLDING', 'FAILED', 'PASS/FAIL',
                    'PASS/FAIL/HOLD', 'PASS_WITH_WARNINGS', 'PASS_PENDING', 'PASS2', 'PASS, FAIL or HOLD',
                    'PASS, FAIL or HOLD, as the first word.', 'not PASS', 'will FAIL', '**PASS', 'pass'):
            with self.subTest(status=bad):
                found = R.problems(TITLE, filled(Status=bad))
                self.assertEqual(len(found), 1, found)
                self.assertIn('"## Status" must begin with', found[0])


class TheTaskId(unittest.TestCase):
    def test_the_task_id_is_a_plan_id_and_is_in_the_title(self):
        self.assertIn('names no plan task id', R.problems(TITLE, filled(**{'Task ID': 'the template'}))[0])
        self.assertIn('names no plan task id', R.problems('S1 x', filled(**{'Task ID': 'S1'}))[0])
        self.assertIn('the title names none', R.problems('A template', filled())[0])
        self.assertEqual(R.problems('S1.8 OWNERS', filled(**{'Task ID': 'S1.7, S1.8'})), [])
        self.assertEqual(R.problems('S1.5–S1.8: four tasks', filled(**{'Task ID': 'S1.5, S1.6, S1.7, S1.8'})), [])

    def test_the_title_names_a_whole_id(self):
        for title in ('S1.75 another task', 'XS1.7 another', 'S1.7.1 a sub-step', 'S11.7 other'):
            with self.subTest(title=title):
                self.assertIn('the title names none', R.problems(title, filled())[0])
        self.assertEqual(R.problems('(S1.7) the template', filled()), [])

    def test_none_with_a_reason_needs_no_task_id(self):
        for none in ('none: an urgent fix outside the plan', 'None — the owner ordered it', 'none, a warehouse item',
                     'none\nthe owner ordered it on 2026-11-25'):
            with self.subTest(task=none):
                self.assertEqual(R.problems('Fix the worker crash on an empty brief',
                                            filled(**{'Task ID': none})), [])

    def test_none_without_a_reason_fails(self):
        for none in ('none', 'none:', 'None.', 'none -'):
            with self.subTest(task=none):
                found = R.problems('Fix the worker crash', filled(**{'Task ID': none}))
                self.assertEqual(len(found), 1, found)
                self.assertIn('says none without the reason', found[0])
        self.assertIn('names no plan task id', R.problems('x', filled(**{'Task ID': 'nonexistent task'}))[0])


class TheExceptions(unittest.TestCase):
    def test_a_github_revert_passes_with_its_generated_body(self):
        title = 'Revert "S1.7 A pull request template with the 18 fields"'
        for body in ('Reverts Shayfly/desktop-tutorial#532', 'Reverts Shayfly/desktop-tutorial#532\r\n\r\nWhy: red'):
            with self.subTest(body=body):
                self.assertIsNotNone(R.accepted_without_report(title, body, 'someone'))
                with tempfile.TemporaryDirectory() as d:
                    done = run('--event', event_file(d, title, body))
                self.assertEqual(done.returncode, 0, done.stdout)
                self.assertIn('no delivery report needed: a GitHub revert', done.stdout)

    def test_a_revert_title_alone_is_not_enough(self):
        self.assertIsNone(R.accepted_without_report('Revert "S1.7 x"', 'I undo it', 'someone'))
        self.assertIsNone(R.accepted_without_report('S1.7 x', 'Reverts Shayfly/desktop-tutorial#532', 'someone'))
        with tempfile.TemporaryDirectory() as d:
            done = run('--event', event_file(d, 'Revert "S1.7 x"', 'I undo it'))
        self.assertEqual(done.returncode, 1)

    def test_dependabot_passes_and_another_login_does_not(self):
        self.assertEqual(R.BOTS, ('dependabot[bot]',))
        with tempfile.TemporaryDirectory() as d:
            bot = run('--event', event_file(d, 'Bump yaml from 6.0 to 6.1', 'Bumps yaml.', 'dependabot[bot]'))
            person = run('--event', event_file(d, 'Bump yaml from 6.0 to 6.1', 'Bumps yaml.', 'dependabot'))
        self.assertEqual(bot.returncode, 0, bot.stdout)
        self.assertIn('opened by dependabot[bot]', bot.stdout)
        self.assertEqual(person.returncode, 1)


class TheCommandLine(unittest.TestCase):
    def test_the_command_line_fails_loudly(self):
        unread = run()
        self.assertEqual(unread.returncode, 1)
        self.assertIn('could not be read', unread.stdout)               # no body is an error, never a pass
        no_body = run(env_extra={'PR_TITLE': TITLE})
        self.assertEqual(no_body.returncode, 1)
        self.assertIn('the body could not be read', no_body.stdout)
        bad = run(env_extra={'PR_TITLE': TITLE, 'PR_BODY': filled(Status='DONE')})
        self.assertEqual(bad.returncode, 1)
        good = run(env_extra={'PR_TITLE': TITLE, 'PR_BODY': filled()})
        self.assertEqual(good.returncode, 0, good.stdout)
        self.assertIn('::notice title=PR report::all 18 fields present; status HOLD', good.stdout)

    def test_a_null_or_empty_body_fails_loudly(self):
        with tempfile.TemporaryDirectory() as d:
            null = run('--event', event_file(d, TITLE, None))
            empty = run('--event', event_file(d, TITLE, ''))
            spaces = run('--event', event_file(d, TITLE, ' \r\n '))
            good = run('--event', event_file(d, TITLE, filled().replace('\n', '\r\n')))
            with open(os.path.join(d, 'push.json'), 'w', encoding='utf-8') as fh:
                json.dump({'ref': 'refs/heads/main'}, fh)
            not_a_pr = run('--event', os.path.join(d, 'push.json'))
        self.assertEqual(null.returncode, 1)
        self.assertIn('the body is null', null.stdout)
        self.assertEqual(empty.returncode, 1)
        self.assertIn('the body is empty', empty.stdout)
        self.assertEqual(spaces.returncode, 1)
        self.assertEqual(good.returncode, 0, good.stdout)
        self.assertIn('status HOLD', good.stdout)
        self.assertEqual(not_a_pr.returncode, 1)
        self.assertIn('holds no pull_request', not_a_pr.stdout)


class TheWorkflow(unittest.TestCase):
    """The whole workflow is read: every trigger, every step, every key that could skip it or widen it."""

    def test_it_runs_on_every_pull_request_and_on_an_edited_body(self):
        self.assertEqual(set(WORKFLOW), {'name', True, 'permissions', 'jobs'})       # yaml reads `on` as True
        on = WORKFLOW[True]
        self.assertEqual(set(on), {'pull_request'})
        self.assertEqual(set(on['pull_request']), {'types'})       # no paths, paths-ignore or branches filter
        self.assertEqual(set(on['pull_request']['types']),
                         {'opened', 'edited', 'synchronize', 'reopened', 'ready_for_review'})

    def test_nothing_skips_it_or_widens_it(self):
        self.assertEqual(WORKFLOW['permissions'], {'contents': 'read'})
        self.assertEqual(set(WORKFLOW['jobs']), {'report'})
        job = WORKFLOW['jobs']['report']
        self.assertEqual(set(job), {'runs-on', 'timeout-minutes', 'steps'})   # no if, continue-on-error, permissions
        for step in job['steps']:
            self.assertFalse({'if', 'continue-on-error'} & set(step), step)
        self.assertNotIn('if:', WORKFLOW_TEXT)
        self.assertNotIn('continue-on-error', WORKFLOW_TEXT)

    def test_the_body_reaches_the_script_as_data_only(self):
        steps = WORKFLOW['jobs']['report']['steps']
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0], {'uses': 'actions/checkout@v5', 'with': {'persist-credentials': False}})
        self.assertEqual(steps[1]['run'], 'python3 scripts/check_pr_report.py --event "$GITHUB_EVENT_PATH"')
        self.assertNotIn('env', steps[1])
        self.assertNotIn('${{', WORKFLOW_TEXT)              # no expression anywhere: no title or body in a shell line


if __name__ == '__main__':
    unittest.main()
