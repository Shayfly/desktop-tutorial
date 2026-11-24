"""Critical path freshness (2026-11-21): the rehearsal's publish-taxonomy job pushed straight to main, which main's
protection (C16, live since 2026-10-20) rejects -- so every rehearsal ended red and the freshness check counted the
path BROKEN although the rehearsal step passed; smoke/rehearsal-builds.jsonl still holds one build, of 2026-10-19.
The job now only reads and reports in the run summary and an artifact. The workflow is read as committed.
Mutations: tests/negative_controls/rehearsal_publish.json."""
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'golden-rehearsal.yml'


class PublishTaxonomy(unittest.TestCase):
    def setUp(self):
        self.job = yaml.safe_load(WORKFLOW.read_text(encoding='utf-8'))['jobs']['publish-taxonomy']
        self.run = '\n'.join(str(s.get('run', '')) for s in self.job['steps'])

    def test_it_only_reads_and_keeps_no_credentials(self):
        self.assertEqual(self.job['permissions'], {'contents': 'read'})
        checkout = next(s for s in self.job['steps'] if str(s.get('uses', '')).startswith('actions/checkout'))
        self.assertIs(checkout['with']['persist-credentials'], False)

    def test_it_never_pushes_to_main(self):
        for forbidden in ('git push', 'git commit', 'HEAD:main', '>> smoke/'):
            self.assertNotIn(forbidden, self.run, forbidden)

    def test_it_reports_in_the_summary_and_as_an_artifact(self):
        self.assertIn("os.environ['GITHUB_STEP_SUMMARY']", self.run)
        upload = [s for s in self.job['steps'] if str(s.get('uses', '')).startswith('actions/upload-artifact')]
        self.assertEqual([u['with']['name'] for u in upload], ['rehearsal-taxonomy-report'])


if __name__ == '__main__':
    unittest.main()
