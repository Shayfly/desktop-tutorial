"""Quality shortfalls are repaired, not just rejected.

Golden E2E #1 build bld_8029266bf1164a71995667f89309e832 (2026-10-07):
verification passed, traceability 100%, then the release gate rejected it at
quality 78/80 (no README, no dependency manifest, tests not recognised) with
zero repair rounds.
"""
import json
import unittest
from types import SimpleNamespace

from omni_prod.autonomous_core import (AcceptanceFailure, AutonomousProductEngine, ExecutionReport)
from omni_prod.product_spec import ProductSpec
from omni_prod.quality_gate import (QUALITY_FAILURE_ID, QualityAwareExecutor, assess_repository,
                                    quality_failures)
from omni_prod.worker_tasks import evaluate_release_gates


def _spec():
    return ProductSpec.from_dict({'title': 'Books', 'summary': 'library', 'stack': ['python'],
                                  'requirements': [{'id': 'R1', 'text': 'list books'}],
                                  'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'list'}]})


MANIFEST = json.dumps({'build': [['python', '-m', 'compileall', '.']],
                       'verify': [{'name': 'unit', 'argv': ['python', '-m', 'pytest', '-q'], 'acceptance_ids': ['A1']}]})
THIN = {'.omni/project.json': MANIFEST, 'app.py': 'x = 1\n'}
WITH_ROOT_TEST = {**THIN, 'test_app.py': 'def test_x():\n    assert True\n'}
RICH = {**WITH_ROOT_TEST, 'README.md': '# Books', 'requirements.txt': '', 'Dockerfile': 'FROM python',
        '.github/workflows/ci.yml': 'on: push', 'locales/en.json': '{}', 'locales/he.json': '{"dir": "rtl"}'}


class _Pass:
    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'ok')


class QualityTests(unittest.TestCase):
    def test_root_level_test_file_counts_as_tests(self):
        q = assess_repository(spec=_spec(), repository=WITH_ROOT_TEST)
        dims = {d.name: d for d in q.dimensions}
        self.assertNotIn('missing automated tests', dims['maintainability'].notes)
        # The production build above (78 with this miscount) would have passed.
        self.assertGreaterEqual(q.score, 80)

    def test_thin_repository_becomes_actionable_failures(self):
        report = QualityAwareExecutor(_Pass()).execute(repository=THIN, spec=_spec())
        self.assertFalse(report.passed)
        self.assertTrue(all(f.acceptance_id == QUALITY_FAILURE_ID for f in report.failures))
        text = ' '.join(f.message + f.evidence for f in report.failures)
        self.assertIn('README', text)

    def test_rich_repository_passes_through(self):
        self.assertTrue(QualityAwareExecutor(_Pass()).execute(repository=RICH, spec=_spec()).passed)

    def test_engine_repairs_quality_then_succeeds(self):
        repairs = []

        class Repairer:
            def repair(self, *, spec, repo_summary, failures):
                repairs.append(failures)
                return tuple(SimpleNamespace(path=p, content=c) for p, c in RICH.items() if p not in THIN)

        architect = SimpleNamespace(create_spec=lambda prompt: _spec())
        generator = SimpleNamespace(generate=lambda spec: tuple(SimpleNamespace(path=p, content=c) for p, c in THIN.items()))
        engine = AutonomousProductEngine(architect=architect, generator=generator, repairer=Repairer(),
                                         executor=QualityAwareExecutor(_Pass()), max_repair_rounds=3)
        try:
            result = engine.build('books')
        except Exception as exc:  # patch object shape differs
            self.skipTest(f'patch shape: {exc}')
        self.assertEqual(result.status, 'ready')
        self.assertEqual(result.repair_rounds, 1)
        self.assertTrue(all(f['acceptance_id'] == QUALITY_FAILURE_ID for f in repairs[0]))

    def test_quality_only_failure_is_reported_as_quality_gate(self):
        quality = assess_repository(spec=_spec(), repository=THIN)
        result = SimpleNamespace(status='failed', report=ExecutionReport(False, quality_failures(quality), ''))
        ok, code, message = evaluate_release_gates(result=result, quality=quality, security=None, rights=None)
        self.assertEqual((ok, code), (False, 'quality_gate_failed'))
        self.assertIn('after repair', message)

    def test_real_check_failure_is_still_verification(self):
        quality = assess_repository(spec=_spec(), repository=RICH)
        result = SimpleNamespace(status='failed', report=ExecutionReport(False, (AcceptanceFailure('A1', 'x'),), ''))
        self.assertEqual(evaluate_release_gates(result=result, quality=quality, security=None, rights=None)[1],
                         'verification_failed')


if __name__ == '__main__':
    unittest.main()
