"""#95 FAILED_BUILD_REPORTED_FIRST_PASS: a failed build is never a first pass.

Matt's case: ExecutionReport(passed=False, failures=()) -> status failed, yet first_pass=True in the engine AND in the
worker's terminal evidence (the old rule read "no failures listed" as "passed"). Through the engine and through the real
worker function (ContractBuildHarness), with synthetic executors only.
"""
import unittest

from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.repository_patch import FilePatch
from omni_prod.worker_tasks import taxonomy_evidence
from tests.m5_worker_harness import ContractBuildHarness
from tests.policy_fixtures import ACCEPTED_SPEC


class Architect:
    def create_spec(self, prompt):
        return ACCEPTED_SPEC


class Generator:
    def generate(self, spec):
        return (FilePatch('app.py', 'print(1)\n'),)


class Fixed:
    def __init__(self, report):
        self.report = report

    def execute(self, **kw):
        return self.report


def engine(report):
    return AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=None,
                                   executor=Fixed(report), max_repair_rounds=0)


SILENT_FAIL = ExecutionReport(False, (), 'threshold failed without diagnostic')
PASSED = ExecutionReport(True, (), 'ok')


class FirstPassRequiresAPassedBuild(unittest.TestCase):
    def test_a_failed_round_with_no_failures_listed_is_not_a_first_pass(self):
        e = engine(SILENT_FAIL)
        r = e.build('synthetic')
        self.assertEqual(r.status, 'failed')
        self.assertIs(e.first_pass, False)
        self.assertIs(taxonomy_evidence(e)['first_pass'], False)

    def test_it_still_leaves_a_taxonomy_row(self):
        e = engine(SILENT_FAIL)
        e.build('synthetic')
        self.assertEqual([(t['round_index'], t['layer'], t['failure_type']) for t in e.failure_taxonomy],
                         [(0, 'sandbox', 'check_failed_unspecified')])

    def test_the_worker_terminal_evidence_says_false_too(self):
        h = ContractBuildHarness()
        h.engine = engine(SILENT_FAIL)
        h.run()
        self.assertEqual(h.final['target'].value, 'failed')
        self.assertIs(h.final['evidence_json']['first_pass'], False)

    def test_a_build_that_passes_round_0_is_a_first_pass(self):
        e = engine(PASSED)
        r = e.build('synthetic')
        self.assertEqual(r.status, 'ready')
        self.assertIs(e.first_pass, True)
        self.assertEqual(e.failure_taxonomy, [])

    def test_the_worker_never_reports_first_pass_unless_ready(self):
        class Says:
            failure_taxonomy, first_pass = [], True        # an engine that claims first pass
        self.assertIs(taxonomy_evidence(Says(), ready=True)['first_pass'], True)
        self.assertIs(taxonomy_evidence(Says())['first_pass'], False)
        self.assertIs(taxonomy_evidence(Says(), ready=False)['first_pass'], False)

    def test_a_round_0_pass_followed_by_a_raise_is_not_a_first_pass(self):
        e = engine(PASSED)
        e._snapshot = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('store down'))
        with self.assertRaises(RuntimeError):
            e.build('synthetic')
        self.assertIs(e.first_pass, False)

    def test_a_silent_round_0_failure_repaired_to_ready_is_not_a_first_pass(self):
        class Seq:
            def __init__(self):
                self.reports = [SILENT_FAIL, PASSED]

            def execute(self, **kw):
                return self.reports.pop(0)

        class Repairer:
            def repair(self, *, spec, repo_summary, failures):
                return (FilePatch('app.py', 'print(2)\n'),)
        e = AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=Repairer(),
                                    executor=Seq(), max_repair_rounds=1)
        r = e.build('synthetic')
        self.assertEqual((r.status, r.repair_rounds), ('ready', 1))
        self.assertIs(e.first_pass, False)                 # it needed a repair

    def test_named_failures_are_unchanged(self):
        e = engine(ExecutionReport(False, (AcceptanceFailure('BEHAVIOR', 'button does nothing: x'),)))
        e.build('synthetic')
        self.assertIs(e.first_pass, False)
        self.assertNotIn('check_failed_unspecified', {t['failure_type'] for t in e.failure_taxonomy})
        self.assertEqual([t['layer'] for t in e.failure_taxonomy], ['behaviour'])


if __name__ == '__main__':
    unittest.main()
