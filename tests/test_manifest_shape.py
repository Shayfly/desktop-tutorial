"""The generated project manifest shape is stated to the model, and a bad
manifest is a repairable verification failure, not a build abort.

Golden E2E #1 on Preview (2026-10-07): with a valid spec the build failed with
"ValueError: at least one verification command required" and 0 repair rounds:
the generator prompt never named the manifest keys, and the parse error
aborted the build before the repair loop could run.
"""
import json
import re
import unittest

from omni_prod.autonomous_agents import _GENERATOR_SYSTEM, _REPAIR_SYSTEM
from omni_prod.product_spec import ProductSpec
from omni_prod.project_manifest import MANIFEST_SHAPE, ProjectManifest
from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor

SPEC = ProductSpec.from_dict({
    "title": "Team tasks", "summary": "Track team tasks", "stack": ["python", "sqlite"],
    "requirements": [{"id": "R1", "text": "Sign up and log in", "kind": "functional", "mandatory": True},
                     {"id": "R2", "text": "Create tasks", "kind": "functional", "mandatory": True}],
    "acceptance": [{"id": "A1", "requirement_id": "R1", "text": "A user can sign up and log in"},
                   {"id": "A2", "requirement_id": "R2", "text": "A user can create a task"}]})


def _executor(calls):
    def urlopen(req, timeout):
        calls.append(json.loads(req.data)["argv"])
        raise AssertionError("the sandbox must not run anything for an invalid manifest")
    return RemoteSandboxRepositoryExecutor(RemoteSandboxConfig("http://sandbox:8010", "s" * 64), urlopen=urlopen)


class PromptTests(unittest.TestCase):
    def test_generator_and_repair_state_the_exact_keys(self):
        for system in (_GENERATOR_SYSTEM, _REPAIR_SYSTEM):
            self.assertIn(MANIFEST_SHAPE, system)
        for key in ('"build"', '"verify"', '"name"', '"argv"', '"acceptance_ids"'):
            self.assertIn(key, MANIFEST_SHAPE)

    def test_the_stated_example_is_accepted_by_the_parser(self):
        example = re.search(r"(\{\"build\".*?\]\}\]\})", MANIFEST_SHAPE).group(1)
        manifest = ProjectManifest.from_repository({".omni/project.json": example})
        self.assertEqual(manifest.verify[0].acceptance_ids, ("A1", "A2"))
        self.assertEqual(manifest.verify[0].argv, ("python", "-m", "pytest", "-q"))


class InvalidManifestTests(unittest.TestCase):
    def _report(self, manifest_text):
        calls = []
        repo = {"app.py": "print(1)"}
        if manifest_text is not None:
            repo[".omni/project.json"] = manifest_text
        report = _executor(calls).execute(repository=repo, spec=SPEC)
        self.assertEqual(calls, [])
        return report

    def test_invented_keys_fail_every_criterion_with_the_parser_reason(self):
        report = self._report(json.dumps({"build_commands": [], "verification_commands": [{"cmd": "pytest"}]}))
        self.assertFalse(report.passed)
        self.assertEqual({f.acceptance_id for f in report.failures}, {"A1", "A2"})
        self.assertIn("at least one verification command required", report.failures[0].message)
        self.assertIn('"verify"', report.failures[0].evidence)       # the repairer is shown the shape

    def test_missing_and_malformed_manifests(self):
        self.assertIn("missing .omni/project.json", self._report(None).failures[0].message)
        self.assertIn("invalid .omni/project.json", self._report("{not json").failures[0].message)

    def test_unknown_acceptance_ids(self):
        report = self._report(json.dumps({"verify": [{"name": "t", "argv": ["python", "-m", "pytest"],
                                                      "acceptance_ids": ["A9"]}]}))
        self.assertIn("unknown acceptance id: A9", report.failures[0].message)


if __name__ == "__main__":
    unittest.main()
