"""J3/T05: exactly one initial verification plus at most three repaired runs.

The fake executor verifies the policy with no Docker/model/billing side effects.
It does NOT qualify as a live worker/Preview E2E.
"""
import unittest

from omni_prod.autonomous_core import AutonomousProductEngine, ExecutionReport, AcceptanceFailure
from omni_prod.repository_patch import FilePatch


class Architect:
    def create_spec(self, prompt):
        return object()


class Generator:
    def generate(self, spec):
        return (FilePatch("app.py", "v0"),)


class Repairer:
    def __init__(self):
        self.calls = 0

    def repair(self, *, spec, repo_summary, failures):
        self.calls += 1
        return (FilePatch("app.py", "v" + str(self.calls)),)


class Verifier:
    def __init__(self, passing=()):
        self.passing = set(passing)
        self.runs = []

    def execute(self, *, repository, spec):
        content = repository["app.py"]
        self.runs.append(content)
        return ExecutionReport(content in self.passing, () if content in self.passing else (
            AcceptanceFailure("A1", "build failed", "Compiler error"),
        ))


class ThreeRepairRoundTests(unittest.TestCase):
    def make_engine(self, rounds=100, passing=()):
        repair, verify = Repairer(), Verifier(passing)
        engine = AutonomousProductEngine(architect=Architect(), generator=Generator(),
                                         repairer=repair, executor=verify, max_repair_rounds=rounds)
        engine._summary = lambda repo, failures=(): {"files": [
            {"path": path, "content": text} for path, text in repo.items()
        ]}
        return engine, repair, verify

    def test_configured_hundred_still_runs_only_three_repairs(self):
        engine, repair, verify = self.make_engine()
        result = engine.build("site")
        self.assertEqual(engine.max_repair_rounds, 3)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.stop_reason, "max_repair_rounds")
        self.assertEqual(result.repair_rounds, 3)
        self.assertEqual(repair.calls, 3)
        self.assertEqual(verify.runs, ["v0", "v1", "v2", "v3"])

    def test_third_repair_is_actually_verified_before_ready(self):
        engine, repair, verify = self.make_engine(passing={"v3"})
        result = engine.build("site")
        self.assertEqual((result.status, result.repair_rounds), ("ready", 3))
        self.assertEqual((repair.calls, verify.runs[-1]), (3, "v3"))
        self.assertTrue(result.report.passed)

    def test_initial_pass_does_not_call_repair_provider(self):
        engine, repair, verify = self.make_engine(passing={"v0"})
        result = engine.build("site")
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.repair_rounds, 0)
        self.assertEqual(repair.calls, 0)
        self.assertEqual(verify.runs, ["v0"])

    def test_invalid_policy_rejected(self):
        for value in (-1, True, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.make_engine(rounds=value)


if __name__ == "__main__":
    unittest.main()
