"""Dependency allowlist for generated code (founder decision 2026-10-07 #25)."""
import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod.attempt_ledger import AttemptRecorder, RecordingExecutor
from omni_prod.dependency_policy import (
    GENERATION_CONSTRAINTS, RUNTIME_PACKAGES, TEST_ONLY_PACKAGES, UNSUPPORTED_DEPENDENCY,
    DependencyGateExecutor, scan)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.dumps({"build": [], "verify": [{"name": "t", "argv": ["python", "-m", "pytest", "-q"],
                                                "acceptance_ids": ["A1"]}]})
APP = "import json, sqlite3\nfrom http.server import BaseHTTPRequestHandler\nfrom store import save\n"
GOOD = {
    "app.py": APP,
    "store.py": "import sqlite3\ndef save(x):\n    return x\n",
    "src/pkg/__init__.py": "",
    "src/pkg/core.py": "from pkg import helpers\n",
    "tests/test_app.py": "import pytest\nimport app\nfrom pkg.core import helpers\n",
    "conftest.py": "import pytest\n",
    "requirements-dev.txt": "pytest==8.3.5\n# comment\n\n",
    ".omni/project.json": MANIFEST,
}


def names(findings):
    return sorted((f.name, f.source) for f in findings)


class ScanTests(unittest.TestCase):
    def test_stdlib_app_with_pytest_tests_is_supported(self):
        self.assertEqual(scan(GOOD), ())

    def test_third_party_import_in_app_is_unsupported(self):
        f = scan({**GOOD, "app.py": APP + "import fastapi\nfrom requests import get\n"})
        self.assertEqual(names(f), [("fastapi", "app.py"), ("requests", "app.py")])

    def test_pytest_in_application_code_is_unsupported(self):
        (f,) = scan({**GOOD, "app.py": APP + "import pytest\n"})
        self.assertIn("test-only", f.reason)

    def test_guarded_optional_import_is_allowed(self):
        code = APP + "try:\n    import orjson as fastjson\nexcept ImportError:\n    fastjson = None\n"
        self.assertEqual(scan({**GOOD, "app.py": code}), ())

    def test_relative_imports_and_syntax_errors_do_not_trip_the_gate(self):
        self.assertEqual(scan({**GOOD, "src/pkg/a.py": "from . import core\n", "broken.py": "def (:\n"}), ())

    def test_requirements(self):
        cases = {
            "pytest>=7,<9\n": None,
            "pytest==8.3.*\n": None,
            "pytest==7.4.0\n": "provides 8.3.5",
            "requests==2.32.3\n": "not in the allowlist",
            "-r base.txt\n": "install options",
            "git+https://example.com/x.git\n": "install options",
            "pytest @ https://example.com/p.whl\n": "direct references",
            "pytest>=8.dev0\n": "cannot be verified",
        }
        for text, reason in cases.items():
            found = scan({**GOOD, "requirements-dev.txt": text})
            if reason is None:
                self.assertEqual(found, (), text)
            else:
                self.assertEqual(len(found), 1, text)
                self.assertIn(reason, found[0].reason, text)

    def test_pytest_as_a_runtime_requirement_is_unsupported(self):
        (f,) = scan({**GOOD, "requirements.txt": "pytest==8.3.5\n"})
        self.assertIn("test-only", f.reason)

    def test_pyproject(self):
        toml = ('[project]\nname="x"\ndependencies=["flask>=3"]\n'
                '[project.optional-dependencies]\ntest=["pytest==8.3.5"]\n')
        (f,) = scan({**GOOD, "pyproject.toml": toml})
        self.assertEqual((f.name, f.source), ("flask", "pyproject.toml"))

    def test_install_steps_are_unsupported(self):
        for argv in (["pip", "install", "-r", "requirements.txt"], ["python3", "-m", "pip", "install", "x"],
                     ["/usr/bin/npm", "ci"]):
            manifest = json.dumps({"build": [argv], "verify": json.loads(MANIFEST)["verify"]})
            (f,) = scan({**GOOD, ".omni/project.json": manifest})
            self.assertIn("install steps", f.reason, argv)

    def test_install_in_preview_start_is_unsupported(self):
        manifest = json.dumps({**json.loads(MANIFEST), "start": ["sh", "-c", "x"]})
        self.assertEqual(scan({**GOOD, ".omni/project.json": manifest}), ())
        manifest = json.dumps({**json.loads(MANIFEST), "start": ["pip", "install", "flask"]})
        self.assertEqual(len(scan({**GOOD, ".omni/project.json": manifest})), 1)

    def test_node_toolchain_is_unsupported(self):
        (f,) = scan({**GOOD, "package.json": json.dumps({"dependencies": {"express": "^4"}})})
        self.assertIn("no Node toolchain", f.reason)
        manifest = json.dumps({**json.loads(MANIFEST), "runtime": "node:20-slim"})
        self.assertEqual([x.name for x in scan({**GOOD, ".omni/project.json": manifest})], ["node"])


class GateTests(unittest.TestCase):
    class Inner:
        def __init__(self):
            self.calls = 0

        def execute(self, *, repository, spec):
            self.calls += 1
            return SimpleNamespace(passed=True, failures=[])

    def test_unsupported_fails_explicitly_without_starting_the_sandbox(self):
        inner = self.Inner()
        report = DependencyGateExecutor(inner).execute(repository={**GOOD, "app.py": "import django\n"}, spec=None)
        self.assertEqual(inner.calls, 0)
        self.assertFalse(report.passed)
        (failure,) = report.failures
        self.assertEqual(failure.acceptance_id, UNSUPPORTED_DEPENDENCY)
        self.assertIn("django", failure.message)
        evidence = json.loads(failure.evidence)
        self.assertRegex(evidence["policy_version"], r"^[0-9a-f]{12}$")
        self.assertIn("sandbox not started", report.build_log)

    def test_supported_repository_reaches_the_sandbox(self):
        inner = self.Inner()
        self.assertTrue(DependencyGateExecutor(inner).execute(repository=GOOD, spec=None).passed)
        self.assertEqual(inner.calls, 1)

    def test_recorded_as_repairable_verification_attempt(self):
        rec = AttemptRecorder()
        RecordingExecutor(DependencyGateExecutor(self.Inner()), rec).execute(repository={"a.py": "import yaml\n"}, spec=None)
        (r,) = rec.records
        self.assertEqual(r.verification_class, "REPAIRABLE_FAIL")
        self.assertIn(UNSUPPORTED_DEPENDENCY, r.failure_reason)

    def test_release_gate_reports_unsupported_dependency(self):
        from omni_prod.worker_tasks import evaluate_release_gates
        report = DependencyGateExecutor(self.Inner()).execute(repository={"a.py": "import yaml\n"}, spec=None)
        ok, code, message = evaluate_release_gates(result=SimpleNamespace(status="failed", report=report),
                                                   quality=None, security=None, rights=None)
        self.assertEqual((ok, code), (False, "unsupported_dependency"))
        self.assertIn("yaml", message)


class DriftTests(unittest.TestCase):
    def test_sandbox_image_installs_exactly_the_allowlist(self):
        dockerfile = (ROOT / "infra/sandbox/Dockerfile").read_text()
        pinned = dict(re.findall(r"^\s+([A-Za-z0-9_.-]+)==([0-9][^\s\\]*)", dockerfile, re.M))
        self.assertEqual(pinned, {**TEST_ONLY_PACKAGES, **RUNTIME_PACKAGES})

    def test_generation_and_repair_prompts_carry_the_policy(self):
        from omni_prod.autonomous_agents import _GENERATOR_SYSTEM, _REPAIR_SYSTEM
        self.assertIn(GENERATION_CONSTRAINTS, _GENERATOR_SYSTEM)
        self.assertIn(GENERATION_CONSTRAINTS, _REPAIR_SYSTEM)


if __name__ == "__main__":
    unittest.main()
