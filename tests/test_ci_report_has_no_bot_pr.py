"""#146 (open since 2026-10-26): the main CI report is published in the run summary and as an artifact, never as a
force-pushed branch with an auto-merging PR. Such a PR could never pass the additive-only check (every report rewrites
the file) and auto-merge stands against CLAUDE.md section 2.5. The workflow is read as committed.
Mutations: tests/negative_controls/ci_report.json."""
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'v24-ci.yml'


class TheReportJob(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding='utf-8')
        self.job = yaml.safe_load(self.text)['jobs']['publish-report']
        self.run = '\n'.join(str(s.get('run', '')) for s in self.job['steps'])

    def test_it_only_reads(self):
        self.assertEqual(self.job['permissions'], {'contents': 'read'})
        checkout = next(s for s in self.job['steps'] if str(s.get('uses', '')).startswith('actions/checkout'))
        self.assertIs(checkout['with']['persist-credentials'], False)

    def test_it_pushes_nothing_and_opens_no_pr(self):
        for forbidden in ('git push', 'gh pr create', 'gh pr merge', '--auto', 'gh workflow run', 'ci/v24-report'):
            self.assertNotIn(forbidden, self.run, forbidden)

    def test_it_publishes_the_report_in_the_run_summary_and_as_an_artifact(self):
        self.assertIn("os.environ['GITHUB_STEP_SUMMARY']", self.run)
        upload = [s for s in self.job['steps'] if str(s.get('uses', '')).startswith('actions/upload-artifact')]
        self.assertEqual(len(upload), 1)
        self.assertEqual(upload[0]['with']['name'], 'ci-last-run')
        self.assertEqual(upload[0]['with']['path'], 'report/ci-last-run.md')

    def test_the_stale_copy_is_not_kept_in_the_repository(self):
        self.assertFalse((ROOT / 'smoke' / 'ci-last-run.md').exists())


if __name__ == '__main__':
    unittest.main()
