"""Directive 2026-10-10 P0.8: no READY while a mandatory acceptance check fails."""
import unittest
from types import SimpleNamespace

from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.repository_patch import parse_patch
from omni_prod.worker_tasks import evaluate_release_gates

OK = SimpleNamespace(passed=True, score=90, minimum_score=80, findings=(), blockers=())
RIGHTS = SimpleNamespace(publish_allowed=True, status='CLEAR')


class _Arch:
    def create_spec(self, prompt):
        return 'spec'


class _Gen:
    def generate(self, spec):
        return parse_patch({'files': [{'path': 'app.py', 'content': 'v0'}]})


class _Rep:
    n = 0

    def repair(self, **kw):
        self.n += 1
        return parse_patch({'files': [{'path': 'app.py', 'content': f'v{self.n}'}]})


class _AlwaysBehaviourFails:
    def execute(self, *, repository, spec):
        return ExecutionReport(False, (AcceptanceFailure('BEHAVIOR', 'behavioural acceptance failed: 1 failed check'),))


class ReleaseGateTests(unittest.TestCase):
    def test_failed_behaviour_acceptance_never_becomes_ready(self):
        engine = AutonomousProductEngine(architect=_Arch(), generator=_Gen(), repairer=_Rep(),
                                         executor=_AlwaysBehaviourFails(), max_repair_rounds=3)
        result = engine.build('p')
        self.assertEqual(result.status, 'failed')
        ready, code, message = evaluate_release_gates(result=result, quality=OK, security=OK, rights=RIGHTS)
        self.assertFalse(ready)
        self.assertEqual(code, 'verification_failed')
        self.assertIn('BEHAVIOR: behavioural acceptance failed', message)   # says what failed

    def test_ready_status_with_a_failed_report_is_still_refused(self):
        result = SimpleNamespace(status='ready', repair_rounds=0,
                                 report=ExecutionReport(False, (AcceptanceFailure('REVIEW', 'blocking finding'),)))
        self.assertFalse(evaluate_release_gates(result=result, quality=OK, security=OK, rights=RIGHTS)[0])


if __name__ == '__main__':
    unittest.main()
