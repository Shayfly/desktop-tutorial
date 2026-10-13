from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    '148ai-intake-gates.yml',
    'intake-budget-pg.yml',
    'v11-overlay-ci.yml',
    'v24-ci.yml',
)


class WorkflowConcurrencyTests(unittest.TestCase):
    def test_push_and_pull_request_runs_have_separate_concurrency_groups(self):
        for name in WORKFLOWS:
            with self.subTest(workflow=name):
                workflow = yaml.safe_load((ROOT / '.github' / 'workflows' / name).read_text(encoding='utf-8'))
                events = workflow.get('on') or workflow.get(True)
                self.assertIn('push', events)
                self.assertIn('pull_request', events)
                self.assertIn('${{ github.event_name }}', workflow['concurrency']['group'])


if __name__ == '__main__':
    unittest.main()
