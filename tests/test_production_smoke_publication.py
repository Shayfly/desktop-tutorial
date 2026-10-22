"""Production smoke evidence survives protected main without committing a result."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/production-smoke.yml'


class SmokePublication(unittest.TestCase):
    def test_publication_preserves_redacted_report_without_git_writes(self):
        workflow = yaml.safe_load(WORKFLOW.read_text())
        step = next(s for s in workflow['jobs']['smoke']['steps'] if s.get('name') == 'publish results')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / 'input.txt'
            report.write_text('API passed\n::add-mask::fixture\neyJhbGciOiSynthetic.fixture.signature\n')
            git = root / 'git'
            git.write_text('#!/bin/sh\necho "unexpected git operation" >&2\nexit 42\n')
            git.chmod(0o755)
            script = step['run'].replace('/tmp/report.clean.txt', str(root / 'clean.txt')).replace('/tmp/report.txt', str(report))
            result = subprocess.run(['bash', '-eo', 'pipefail', '-c', script], cwd=root,
                                    env={**os.environ, 'PATH': str(root) + ':' + os.environ['PATH'],
                                         'GITHUB_RUN_ID': 'fixture-run'}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            saved = (root / 'smoke/last-run.md').read_text()
            self.assertIn('API passed', saved)
            self.assertIn('fixture-run', saved)
            self.assertNotIn('eyJhbGciOi', saved)
            self.assertNotIn('::add-mask::', saved)

    def test_artifact_is_uploaded_even_when_the_probe_fails(self):
        job = yaml.safe_load(WORKFLOW.read_text())['jobs']['smoke']
        uploads = [s for s in job['steps'] if s.get('uses', '').startswith('actions/upload-artifact@')]
        self.assertEqual(len(uploads), 1)
        upload = uploads[0]
        self.assertIn('always()', upload['if'])
        self.assertEqual(upload['with']['retention-days'], 90)
        self.assertEqual(upload['id'], 'smoke_artifact')
        self.assertEqual(upload['with']['path'], 'smoke/last-run.md')
        self.assertEqual(upload['with']['if-no-files-found'], 'error')
        self.assertEqual(job.get('permissions', {}).get('contents', 'read'), 'read')


    def test_summary_links_the_uploaded_artifact(self):
        steps = yaml.safe_load(WORKFLOW.read_text())['jobs']['smoke']['steps']
        step = next(s for s in steps if s.get('name') == 'Link smoke evidence')
        self.assertIn('steps.smoke_artifact.outputs.artifact-url', step['env']['ARTIFACT_URL'])
        with tempfile.TemporaryDirectory() as temp:
            summary = Path(temp) / 'summary.md'
            url = 'https://github.invalid/artifacts/123'
            result = subprocess.run(['bash', '-eo', 'pipefail', '-c', step['run']],
                                    env={**os.environ, 'ARTIFACT_URL': url,
                                         'GITHUB_STEP_SUMMARY': str(summary)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('](' + url + ')', summary.read_text())


if __name__ == '__main__':
    unittest.main()
