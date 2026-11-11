import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CIScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('ci_scope', ROOT / 'scripts/ci_scope.py')
        cls.scope = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.scope)

    def test_documentation_only_skips_heavy_checks(self):
        self.assertFalse(self.scope.needs_heavy(['README.md', 'STATUS.md', 'docs/guide.md']))

    def test_code_dependency_infrastructure_security_and_workflow_changes_run_heavy(self):
        for path in ('omni_prod/auth.py', 'omni_prod/assets/app.css', 'tests/test_auth.py', 'requirements-production.txt', 'requirements-test.txt', 'Dockerfile', 'infra/postgres/001.sql', '.github/workflows/v24-ci.yml', 'AGENT_OS_REGISTRY.json', 'docs/tool.py', '.github/README.md'):
            with self.subTest(path=path):
                self.assertTrue(self.scope.needs_heavy(['README.md', path]))

    def test_empty_unknown_and_unsafe_paths_fail_closed(self):
        for paths in ([], ['new-file'], ['../README.md'], ['docs/../omni_prod/auth.md'], ['docs\\guide.md']):
            self.assertTrue(self.scope.needs_heavy(paths), paths)

    def test_renames_include_old_code_path(self):
        self.assertTrue(self.scope.needs_heavy(['omni_prod/auth.py', 'docs/auth.md']))

    def test_deleted_code_still_runs_heavy(self):
        self.assertTrue(self.scope.needs_heavy(['omni_prod/deleted.py']))

    def test_gate_accepts_only_completed_tests_or_explicit_documentation_skip(self):
        self.assertTrue(self.scope.gate_passes('success', 'true', 'success'))
        self.assertTrue(self.scope.gate_passes('success', 'false', 'skipped'))

    def test_gate_rejects_classifier_failure_missing_output_and_test_failure(self):
        for scope, heavy, result in (
            ('failure', 'true', 'skipped'), ('cancelled', 'false', 'skipped'),
            ('skipped', 'false', 'skipped'), ('success', '', 'skipped'),
            ('success', None, 'skipped'), ('success', 'true', 'failure'),
            ('success', 'true', 'cancelled'), ('success', 'true', 'skipped'),
            ('success', 'false', 'failure'), ('success', 'false', 'success'),
        ):
            with self.subTest(scope=scope, heavy=heavy, result=result):
                self.assertFalse(self.scope.gate_passes(scope, heavy, result))
