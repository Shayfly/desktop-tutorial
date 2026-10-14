"""Uncovered acceptance criteria are failures the repair loop can fix.

Golden E2E #1 build bld_a8b2ceec26734c7e8d2859575686f9f2 (2026-10-07): sandbox
verification passed with 4 of 7 criteria referenced, then the quality gate
rejected it (traceability 57%) with no repair round.
"""
import json
import unittest

from omni_prod.product_spec import ProductSpec
from omni_prod.project_manifest import ProjectManifest, uncovered_acceptance_failures
from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor


def _spec():
    return ProductSpec.from_dict({
        'title': 'League', 'summary': 'league table', 'stack': ['python'],
        'requirements': [{'id': 'R1', 'text': 'teams'}],
        'acceptance': [{'id': f'A{i}', 'requirement_id': 'R1', 'text': f'criterion {i}'} for i in (1, 2, 3)],
    })


def _repo(ids):
    manifest = {'build': [['python', '-m', 'compileall', '.']],
                'verify': [{'name': 'unit', 'argv': ['python', '-m', 'pytest', '-q'], 'acceptance_ids': ids}]}
    return {'.omni/project.json': json.dumps(manifest), 'app.py': 'x = 1\n'}


class _OkSandbox(RemoteSandboxRepositoryExecutor):
    def __init__(self):
        super().__init__(RemoteSandboxConfig('http://sandbox.invalid', 's' * 32))

    def _run(self, repository, argv, build_id):
        return {'returncode': 0, 'stdout': 'ok', 'stderr': ''}


class CoverageTests(unittest.TestCase):
    def test_helper_lists_only_uncovered_ids_with_actionable_instruction(self):
        spec = _spec()
        manifest = ProjectManifest.from_repository(_repo(['A1']))
        failures = uncovered_acceptance_failures(manifest, spec)
        self.assertEqual([f.acceptance_id for f in failures], ['A2', 'A3'])
        self.assertIn('criterion 2', failures[0].evidence)
        self.assertIn('acceptance_ids', failures[0].evidence)

    def test_remote_executor_fails_when_a_criterion_has_no_check(self):
        report = _OkSandbox().execute(repository=_repo(['A1', 'A2']), spec=_spec())
        self.assertFalse(report.passed)
        self.assertEqual([f.acceptance_id for f in report.failures], ['A3'])

    def test_remote_executor_passes_with_full_coverage(self):
        report = _OkSandbox().execute(repository=_repo(['A1', 'A2', 'A3']), spec=_spec())
        self.assertTrue(report.passed)
        self.assertEqual(report.failures, ())


if __name__ == '__main__':
    unittest.main()
