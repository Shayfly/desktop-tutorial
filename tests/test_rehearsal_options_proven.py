"""A requested rehearsal option that the worker did not apply is a red run, never a silent pass (run 46005664127).

That run printed `image=customer_photo`, ended READY and never printed the `customer photo` line: the worker image was
built before the option existed and its rehearsal ignored REHEARSAL_IMAGE without a word. The workflow's step "Prove the
requested options were applied" now reads the report the container printed. The test runs the step's own Python (taken
from the workflow file) on rehearsal outputs: the one that run printed (no `options_applied`), and the ones a current
worker prints."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omni_prod import rehearsal as R
from omni_prod import rehearsal_photo as P

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = (ROOT / '.github' / 'workflows' / 'golden-rehearsal.yml').read_text(encoding='utf-8')
STEP = WORKFLOW.split('- name: Prove the requested options were applied', 1)[1].split('- uses: actions/upload-artifact@v6', 1)[0]
SCRIPT = '\n'.join(l[10:] if l.startswith(' ' * 10) else l for l in STEP.split("<<'PY'\n", 1)[1].split('\n          PY', 1)[0].split('\n'))

# what run 46005664127's container printed: a finished READY report with no trace of the options
OLD_WORKER = {'outcome': 'ready', 'quality': {'passed': True}, 'release_policy': {'decision': 'READY'}, 'build_id': 'rehearsal-46005664127'}
PHOTO_OK = {'as_file': True, 'hero_kept': True, 'ok': True, 'inline_data_uri_in': [], 'images': []}
CURRENT = {**OLD_WORKER, 'options_applied': {'image': 'customer_photo', 'account': '', 'time_budget': []}, 'photo': PHOTO_OK}


def check(report, *, image='', account='', budget='', raw=None):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / 'rehearsal.out'
        out.write_text(raw if raw is not None else ('noise\nREHEARSAL ' + json.dumps(report) + '\n::notice x::y\n'),
                       encoding='utf-8')
        env = {**os.environ, 'IMAGE': image, 'ACCOUNT': account, 'TIME_BUDGET': budget}
        done = subprocess.run([sys.executable, '-I', '-c', SCRIPT, str(out)], env=env, capture_output=True, text=True)
    return done.returncode, done.stdout


class TheStepProvesTheOptions(unittest.TestCase):
    def test_the_script_was_found(self):
        self.assertIn('options_applied', SCRIPT)
        self.assertTrue(SCRIPT.lstrip().startswith('import json'))

    def test_nothing_requested_nothing_to_prove(self):
        rc, out = check(OLD_WORKER)
        self.assertEqual(rc, 0)
        self.assertIn('none requested', out)

    def test_an_image_the_worker_ignored_is_red_and_says_why(self):
        rc, out = check(OLD_WORKER, image='customer_photo')            # run 46005664127
        self.assertEqual(rc, 1)
        self.assertIn('::error title=rehearsal options::', out)
        self.assertIn('does not know these options', out)

    def test_no_report_at_all_is_red(self):
        rc, out = check(None, image='customer_photo', raw='no report here\n')
        self.assertEqual(rc, 1)
        self.assertIn('printed no REHEARSAL report', out)

    def test_an_applied_image_with_a_good_photo_prints_the_notice(self):
        rc, out = check(CURRENT, image='customer_photo')
        self.assertEqual(rc, 0)
        self.assertIn('::notice title=customer photo::photo_as_file=True hero_kept=True', out)

    def test_a_photo_that_is_not_ok_is_red(self):
        rc, out = check({**CURRENT, 'photo': {**PHOTO_OK, 'hero_kept': False, 'ok': False}}, image='customer_photo')
        self.assertEqual(rc, 1)
        self.assertIn('::error title=customer photo::photo_as_file=True hero_kept=False', out)

    def test_an_applied_image_without_a_photo_section_is_red(self):
        report = {k: v for k, v in CURRENT.items() if k != 'photo'}
        rc, out = check(report, image='customer_photo')
        self.assertEqual(rc, 1)
        self.assertIn('has no photo section', out)

    def test_another_image_than_the_one_requested_is_red(self):
        rc, out = check({**CURRENT, 'options_applied': {'image': '', 'account': '', 'time_budget': []}}, image='customer_photo')
        self.assertEqual(rc, 1)
        self.assertIn('not applied', out)

    def test_the_account_and_the_time_budget_are_proven_too(self):
        applied = {'image': '', 'account': 'non_founder', 'time_budget': [120, 600]}
        good = {**OLD_WORKER, 'options_applied': applied, 'account': {'founder': False}, 'time_budget': {'ended_by': 'x'}}
        self.assertEqual(check(good, account='non_founder', budget='120, 600')[0], 0)
        self.assertEqual(check({**good, 'options_applied': {**applied, 'time_budget': []}}, budget='120,600')[0], 1)
        self.assertEqual(check({**good, 'options_applied': {**applied, 'account': ''}}, account='non_founder')[0], 1)
        self.assertEqual(check({k: v for k, v in good.items() if k != 'account'}, account='non_founder')[0], 1)
        self.assertEqual(check({k: v for k, v in good.items() if k != 'time_budget'}, budget='120,600')[0], 1)

    def test_the_step_runs_after_the_rehearsal_even_when_it_failed(self):
        self.assertIn('if: always()', STEP.split('run: |', 1)[0])
        self.assertLess(WORKFLOW.index('- name: Rehearse one build'), WORKFLOW.index('- name: Prove the requested options'))
        for name in ('IMAGE', 'ACCOUNT', 'TIME_BUDGET'):
            self.assertIn(f'{name}: ${{{{ inputs.{name.lower()} }}}}', STEP)


class TheCodeSaysWhatItApplied(unittest.TestCase):
    def run_it(self, options):
        token = R._OPTIONS.set(options)
        self.addCleanup(R._OPTIONS.reset, token)
        engine = SimpleNamespace(executor=SimpleNamespace(), architect=None, build=mock.Mock(side_effect=RuntimeError('stop')))
        with mock.patch('omni_prod.investor_app._live_components', return_value=(engine, SimpleNamespace())):
            return R.run('x')

    def test_nothing_asked_nothing_applied(self):
        self.assertEqual(self.run_it(R.Options())['options_applied'], {'image': '', 'account': '', 'time_budget': []})

    def test_what_was_asked_is_what_the_report_says(self):
        report = self.run_it(R.Options(photo=P.load('customer_photo'), account_id=P.NON_FOUNDER_ID, time_budget=(60, 300)))
        self.assertEqual(report['options_applied'], {'image': 'customer_photo', 'account': 'non_founder', 'time_budget': [60, 300]})
        self.assertIn('photo', report)                      # a requested image always has its report, even with no build


if __name__ == '__main__':
    unittest.main()
