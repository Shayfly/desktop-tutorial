from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    '148ai-intake-gates.yml',
    'intake-budget-pg.yml',
    'v11-overlay-ci.yml',
    'v24-ci.yml',
    'neon-bootstrap-ci.yml',
)


class WorkflowConcurrencyTests(unittest.TestCase):
    def test_full_ci_has_disjoint_feature_push_and_pr_triggers(self):
        for name in WORKFLOWS:
            with self.subTest(workflow=name):
                workflow = yaml.safe_load((ROOT / '.github' / 'workflows' / name).read_text(encoding='utf-8'))
                events = workflow.get('on') or workflow.get(True)
                self.assertIn('push', events)
                self.assertIn('pull_request', events)
                self.assertIsInstance(events, dict)
                self.assertEqual(events['push']['branches'], ['main', 'milestone/pre-staging-2026-10-05'])
                self.assertIn('workflow_dispatch', events)
                group = workflow['concurrency']['group']
                self.assertIn('github.workflow', group)
                self.assertIn('github.event.pull_request.number', group)
                self.assertNotIn('head.sha', group)
                self.assertTrue(workflow['concurrency']['cancel-in-progress'])

    def test_heavy_jobs_are_gated_but_security_suite_is_always_present(self):
        def read(name):
            return yaml.safe_load((ROOT / '.github/workflows' / name).read_text(encoding='utf-8'))
        jobs = read('v24-ci.yml')['jobs']
        self.assertNotIn('if', jobs['test'])
        self.assertIn("needs.changes.outputs.heavy == 'true'", jobs['browser-tests']['if'])
        pg_jobs = read('intake-budget-pg.yml')['jobs']
        pg = pg_jobs['pg-tests']
        self.assertIn("needs.changes.outputs.heavy == 'true'", pg['if'])
        commands = '\n'.join(s.get('run', '') for s in jobs['test']['steps'])
        for gate in ('python -m pytest -q', 'meta regression', 'agent_os.audit', 'run_hostile_static_suite.py', 'run_international_gate.py'):
            self.assertIn(gate, commands)
        self.assertTrue(any(s.get('name') == 'No test may be skipped' for s in pg['steps']))
        for gate, heavy_job in ((jobs['customer-ui'], 'browser-tests'), (pg_jobs['pg'], 'pg-tests')):
            self.assertEqual(gate['if'], 'always()')
            self.assertEqual(gate['needs'], ['changes', heavy_job])
            step = gate['steps'][-1]
            self.assertEqual(step['run'], 'python scripts/ci_scope.py --verify-gate')
            self.assertEqual(step['env']['SCOPE_RESULT'], '${{ needs.changes.result }}')
            self.assertEqual(step['env']['TEST_RESULT'], '${{ needs.' + heavy_job + '.result }}')

    def test_changed_jobs_have_time_limits(self):
        for name in WORKFLOWS:
            d = yaml.safe_load((ROOT / '.github/workflows' / name).read_text(encoding='utf-8'))
            for job in d['jobs'].values():
                with self.subTest(workflow=name):
                    self.assertGreater(job.get('timeout-minutes', 0), 0)
                    self.assertLessEqual(job['timeout-minutes'], 20)

    def test_fast_push_checks_cover_feature_branches(self):
        d = yaml.safe_load((ROOT / '.github/workflows/ci-fast.yml').read_text(encoding='utf-8'))
        events = d.get('on', d.get(True))
        self.assertEqual(events['push']['branches-ignore'], ['main', 'milestone/pre-staging-2026-10-05'])
        self.assertNotIn('pull_request', events)

    def test_merge_gate_cancels_stale_commit_pair(self):
        d = yaml.safe_load((ROOT / '.github/workflows/148ai-merge-candidate-review.yml').read_text(encoding='utf-8'))
        group = d['concurrency']['group']
        self.assertIn('pull_request.number', group)
        self.assertNotIn('head.sha', group)
        self.assertNotIn('base.sha', group)

    def test_stateful_operations_remain_non_cancellable(self):
        for name in ('deploy-worker.yml', 'backup-restore.yml', 'postdeploy-checks.yml', 'golden-rehearsal.yml', '148ai-registry-refresh.yml', 'registry-snapshot-review.yml'):
            d = yaml.safe_load((ROOT / '.github/workflows' / name).read_text(encoding='utf-8'))
            self.assertFalse(d['concurrency']['cancel-in-progress'], name)


if __name__ == '__main__':
    unittest.main()
