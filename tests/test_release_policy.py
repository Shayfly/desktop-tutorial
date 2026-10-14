"""Release policy (Production Assurance v2 §4/§5; issue #6 P1): a check that did
not run is not a pass, and nothing averages over a mandatory failure.
Cases come from the 2026-10-10 audit of skip paths in the verification chain."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.release_policy import FAIL, NOT_RUN, PASS, build_report, enforcement_mode
from tests.policy_fixtures import ACCEPTED_SPEC, verified_chain
from tests.test_m3_preview_logic import BuildHarness

OK = SimpleNamespace(passed=True, score=90, minimum_score=80)
RIGHTS = SimpleNamespace(publish_allowed=True)


def _evidence(**over):
    ev = {'consistency_gate': {'last': {'passed': True, 'blocking': [], 'advisories': []}},
          'preview_smoke': {'status': 'PASS'},
          'behavior_acceptance': {'last': {'status': 'PASS', 'summary': 'ok'}},
          'browser_check': {'status': 'passed'},
          'product_review': [{'round': 1, 'model': 'reviewer', 'blocking': 0}]}
    ev.update(over)
    return ev


def _report(evidence, *, spec=ACCEPTED_SPEC, passed=True, failures=(), authors=('author',)):
    result = SimpleNamespace(status='ready' if passed else 'failed', spec=spec,
                             report=ExecutionReport(passed, failures, ''))
    return build_report(build_id='b', artifact_sha256='sha', result=result, evidence=evidence, quality=OK,
                        security=OK, rights=RIGHTS, author_models=set(authors))


def _status(report, check):
    return next(c.status for c in report.checks if c.check == check)


class PolicyTests(unittest.TestCase):
    def test_enforced_visual_failure_blocks_even_with_missing_visual_evidence(self):
        for visual in ({'status': 'FINDINGS'}, None, {'status': 'PASS'}):
            with self.subTest(visual=visual):
                r = _report(_evidence(visual_qa=visual), passed=False,
                            failures=(AcceptanceFailure('VISUAL', 'enforced layout failure'),))
                self.assertEqual(r.decision, 'FAILED')
                self.assertEqual(_status(r, 'visual_layout_desktop_mobile'), FAIL)

    def test_advisory_visual_findings_do_not_block(self):
        r = _report(_evidence(visual_qa={'status': 'FINDINGS'}))
        self.assertEqual(r.decision, 'READY')

    def test_everything_ran_and_passed_is_ready(self):
        r = _report(_evidence())
        self.assertEqual(r.decision, 'READY', r.to_dict()['blocking'])
        self.assertEqual(r.to_dict()['schema'], 'quality-report/1')

    def test_browser_unavailable_is_not_a_pass(self):
        r = _report(_evidence(browser_check={'status': 'unavailable', 'reason': 'no browser profile'}))
        self.assertEqual(_status(r, 'browser_flow'), NOT_RUN)
        self.assertEqual(r.decision, 'FAILED')

    def test_behaviour_not_run_blocks(self):
        r = _report(_evidence(behavior_acceptance={'last': None}))
        self.assertEqual(_status(r, 'behavioural_acceptance'), NOT_RUN)
        self.assertEqual(r.decision, 'FAILED')

    def test_preview_smoke_without_runner_blocks(self):
        self.assertEqual(_report(_evidence(preview_smoke={'status': 'NOT_RUN'})).decision, 'FAILED')
        self.assertEqual(_report(_evidence(preview_smoke=None)).decision, 'FAILED')

    def test_disabled_consistency_gate_blocks(self):
        r = _report(_evidence(consistency_gate=None))
        self.assertEqual(_status(r, 'cross_file_consistency'), NOT_RUN)
        self.assertEqual(r.decision, 'FAILED')

    def test_review_findings_left_after_the_enforced_rounds_fail(self):
        r = _report(_evidence(product_review=[{'round': 1, 'model': 'reviewer', 'blocking': 2},
                                              {'round': 2, 'model': 'reviewer', 'blocking': 1}]))
        self.assertEqual(_status(r, 'qa_review_blocking_findings'), FAIL)
        self.assertEqual(r.decision, 'FAILED')

    def test_spec_without_acceptance_criteria_is_not_ready(self):
        r = _report(_evidence(), spec=SimpleNamespace(acceptance=()))
        self.assertEqual(_status(r, 'acceptance_criteria_defined'), FAIL)
        self.assertEqual(r.decision, 'FAILED')

    def test_reviewer_who_wrote_the_code_is_flagged_but_advisory(self):
        r = _report(_evidence(), authors=('reviewer',))
        self.assertEqual(_status(r, 'reviewer_independent_of_author'), NOT_RUN)
        self.assertEqual(r.decision, 'READY')     # advisory: deterministic platform checks carry the decision

    def test_tests_status_reflects_chain_order(self):
        r = _report(_evidence(), passed=False, failures=(AcceptanceFailure('BEHAVIOR', 'x'),))
        self.assertEqual(_status(r, 'sandbox_build_and_tests'), PASS)     # tests ran before behaviour
        r = _report(_evidence(), passed=False, failures=(AcceptanceFailure('A1', 'unit tests'),))
        self.assertEqual(_status(r, 'sandbox_build_and_tests'), FAIL)
        r = _report(_evidence(), passed=False, failures=(AcceptanceFailure('CONSISTENCY', 'x'),))
        self.assertEqual(_status(r, 'sandbox_build_and_tests'), NOT_RUN)
        r = _report(_evidence(), passed=False, failures=(AcceptanceFailure('BEHAVIOR', 'x'),))
        self.assertEqual(_status(r, 'dependency_allowlist'), PASS)        # replay 38080024444 showed UNKNOWN
        r = _report(_evidence(), passed=False, failures=(AcceptanceFailure('UNSUPPORTED_DEPENDENCY', 'x'),))
        self.assertEqual(_status(r, 'dependency_allowlist'), FAIL)

    def test_shadow_mode_is_refused_on_staging_and_production(self):
        with patch.dict(os.environ, {'OMNI_RELEASE_POLICY': 'shadow', 'OMNI_ENV': 'staging'}):
            self.assertEqual(enforcement_mode(), 'enforce')
        with patch.dict(os.environ, {'OMNI_RELEASE_POLICY': 'shadow', 'OMNI_ENV': 'development'}):
            self.assertEqual(enforcement_mode(), 'shadow')


class WorkerPolicyTests(unittest.TestCase):
    def test_report_generation_error_blocks_ready_and_preserves_billing(self):
        from decimal import Decimal
        for environment in ('staging', 'production'):
            for calls in (0, 2):
                with self.subTest(environment=environment, calls=calls):
                    h = BuildHarness(calls=calls)
                    with patch.dict(os.environ, {'OMNI_ENV': environment, 'OMNI_RELEASE_POLICY': 'shadow'}), \
                         patch('omni_prod.release_policy.build_report', side_effect=ValueError('broken report')), \
                         self.assertLogs('omni_prod.worker_tasks', level='ERROR'):
                        self.assertEqual(h.run(), 'failed')
                    self.assertEqual(h.final['error_code'], 'release_policy_unavailable')
                    h.workspace.commit.assert_not_called()
                    self.assertIsNone(h.final['result_version_id'])
                    self.assertFalse(h.final['evidence_json']['release_ready'])
                    if calls:
                        h.subs.settle.assert_called_once_with(
                            build_id='bld_1', actual_provider_cost_usd=Decimal('0.50'))
                        h.subs.release.assert_not_called()
                    else:
                        h.subs.release.assert_called_once_with(build_id='bld_1')
                        h.subs.settle.assert_not_called()

    def test_missing_report_remains_advisory_in_explicit_development_shadow(self):
        h = BuildHarness()
        with patch.dict(os.environ, {'OMNI_ENV': 'development', 'OMNI_RELEASE_POLICY': 'shadow'}), \
             patch('omni_prod.worker_tasks.release_quality_report', return_value=None):
            self.assertEqual(h.run(), 'ready')

    def test_build_with_an_unavailable_browser_check_is_not_ready(self):
        h = BuildHarness()
        h.engine.executor = verified_chain(overrides={'browser': {'status': 'unavailable', 'reason': 'no chromium'}})
        self.assertEqual(h.run(), 'failed')
        self.assertEqual(h.final['error_code'], 'release_policy_failed')
        self.assertIn('visual/browser_flow NOT_RUN', h.final['error_message'])
        report = h.final['evidence_json']['quality_report']
        self.assertEqual(report['decision'], 'FAILED')
        self.assertEqual(report['artifact_sha256'], __import__('omni_prod.workspace', fromlist=['_checksum'])._checksum(h.result.repository))

    def test_policy_report_is_stored_on_a_ready_build(self):
        h = BuildHarness()
        self.assertEqual(h.run(), 'ready')
        self.assertEqual(h.final['evidence_json']['quality_report']['decision'], 'READY')


if __name__ == '__main__':
    unittest.main()


class FakeVerificationTests(unittest.TestCase):
    def test_noop_commands_are_fake_and_real_tests_are_not(self):
        from omni_prod.sandbox_executor import _is_fake_verification as fake
        for argv in (('true',), (':',), ('echo', 'ok'), ('python', '-c', 'pass'), ('python3', '-c', 'print(1)'),
                     ('sh', '-c', 'exit 0'), ('bash', '-c', 'true'), ('exit', '0')):
            self.assertTrue(fake(argv), argv)
        for argv in (('python', '-m', 'pytest', '-q'), ('python', '-m', 'unittest'),
                     ('python', '-c', 'import app; assert app.ok()'), ('node', 'test.js')):
            self.assertFalse(fake(argv), argv)

    def test_remote_runner_refuses_a_noop_verify_command(self):
        import json
        from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor
        ex = RemoteSandboxRepositoryExecutor(RemoteSandboxConfig('http://127.0.0.1:9', 's' * 32))
        ran = []
        ex._run = lambda repo, argv, tag, **k: ran.append(argv) or {'returncode': 0, 'stdout': '', 'stderr': ''}
        spec = SimpleNamespace(acceptance=(SimpleNamespace(id='A1', text='x'),))
        repo = {'.omni/project.json': json.dumps({'verify': [{'name': 'unit', 'argv': ['python', '-c', 'pass'],
                                                              'acceptance_ids': ['A1']}]})}
        report = ex.execute(repository=repo, spec=spec)
        self.assertFalse(report.passed)
        self.assertIn('Fake verification', report.failures[0].evidence)
        self.assertEqual(ran, [])


DATABASE_URL = os.environ.get('M4D2_DATABASE_URL')


@unittest.skipUnless(DATABASE_URL, 'live PostgreSQL not configured')
class StageEvidenceLivePostgresTests(unittest.TestCase):
    """Migration 035: immutable, idempotent stage rows bound to the artifact digest."""

    def setUp(self):
        from pathlib import Path
        from omni_prod.db import DatabasePool
        self.pool = DatabasePool(DATABASE_URL)
        sql = (Path(__file__).resolve().parents[1] / 'infra/postgres/035_build_stage_results.sql').read_text()
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute(sql)

    def _rows(self, build_id):
        with self.pool.connection() as conn:
            return conn.execute('SELECT check_key, status, artifact_sha256, decision, source_commit FROM build_stage_results '
                                'WHERE build_id = %s ORDER BY check_key', (build_id,)).fetchall()

    def test_rows_are_written_once_and_bound_to_the_artifact(self):
        import uuid
        from omni_prod.release_policy import persist
        bid = f'bld_{uuid.uuid4().hex[:10]}'
        report = _report(_evidence(browser_check={'status': 'unavailable'}))
        report.build_id = bid
        with patch.dict(os.environ, {'OMNI_SOURCE_COMMIT': 'abc123', 'OMNI_ENV': 'staging'}):
            n = persist(self.pool, report, tenant_key='tenant-x')
            persist(self.pool, report, tenant_key='tenant-x')            # duplicate delivery: no new rows
        rows = self._rows(bid)
        self.assertEqual(len(rows), n)
        self.assertTrue(all(r[2] == 'sha' and r[3] == 'FAILED' and r[4] == 'abc123' for r in rows))
        self.assertIn(('browser_flow', 'NOT_RUN'), [(r[0], r[1]) for r in rows])
        report2 = _report(_evidence())
        report2.build_id, report2.artifact_sha256 = bid, 'sha-2'                # a new repository state
        persist(self.pool, report2)
        self.assertEqual(len(self._rows(bid)), 2 * n)                         # evidence does not transfer
