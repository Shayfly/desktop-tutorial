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

    def test_shadow_mode_is_refused_on_staging_and_production(self):
        with patch.dict(os.environ, {'OMNI_RELEASE_POLICY': 'shadow', 'OMNI_ENV': 'staging'}):
            self.assertEqual(enforcement_mode(), 'enforce')
        with patch.dict(os.environ, {'OMNI_RELEASE_POLICY': 'shadow', 'OMNI_ENV': 'development'}):
            self.assertEqual(enforcement_mode(), 'shadow')


class WorkerPolicyTests(unittest.TestCase):
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
