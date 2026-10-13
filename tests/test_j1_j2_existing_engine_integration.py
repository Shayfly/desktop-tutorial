"""J1/J2 regression gates for additive existing-agent and Docker sandbox integration.

Tests are offline; a green test does not claim Oracle/E2E verified.
"""
import os
import unittest
from unittest.mock import patch

from omni_prod.repair_contracts import (
    RepairPatchV1, validated_file_patches, repository_fingerprint,
    attributed_files, sanitized_tail, ExecutionEvidenceV1,
)
from omni_prod.repository_patch import PatchValidationError
from omni_prod.sandbox_request_policy import (
    validate_snapshot, validate_command, SandboxRequestRejected,
)


REPO = {"src/server.py": "print('hello')", "src/util.py": "VALUE=2"}
BASE = repository_fingerprint(REPO)
PATCH = {
    "schema_version": 1,
    "reason_code": "FIX_COMPILE_ERROR",
    "base_repository_fingerprint": BASE,
    "changes": [{"path": "src/server.py", "operation": "UPSERT",
                 "content": "print('repaired')"}],
    "repaired_acceptance_ids": ["A1"],
    "summary": "fix server syntax",
    "requires_dependency_change": False,
}


class ContractAndSandboxTests(unittest.TestCase):
    def test_valid_patch_reuses_existing_filepatch_contract(self):
        files = validated_file_patches(PATCH, base_fingerprint=BASE, approved_acceptance_ids={"A1"})
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].path, "src/server.py")

    def test_wrong_fingerprint_is_rejected(self):
        with self.assertRaises(PatchValidationError):
            validated_file_patches(PATCH, base_fingerprint="sha256:" + "0"*64,
                                   approved_acceptance_ids={"A1"})

    def test_malicious_target_outside_repository_rejected(self):
        payload = {**PATCH, "changes": [{"path": "../.env", "operation": "UPSERT", "content": "SECRET=BAD"}]}
        with self.assertRaises(PatchValidationError):
            validated_file_patches(payload, base_fingerprint=BASE, approved_acceptance_ids={"A1"})

    def test_patch_cannot_mutate_acceptance_tests(self):
        payload = {**PATCH, "changes": [{"path": "tests/test_smoke.py", "operation": "UPSERT", "content": "pass"}]}
        with self.assertRaises(PatchValidationError):
            validated_file_patches(payload, base_fingerprint=BASE, approved_acceptance_ids={"A1"})

    def test_patch_cannot_mutate_dependency_lock(self):
        payload = {**PATCH, "changes": [{"path": "package.json", "operation": "UPSERT", "content": "{}"}]}
        with self.assertRaises(PatchValidationError):
            validated_file_patches(payload, base_fingerprint=BASE, approved_acceptance_ids={"A1"})

    def test_unknown_source_file_remains_unknown(self):
        self.assertEqual(attributed_files(REPO, stderr="generic syntax error"), [])

    def test_compiler_path_attribution_with_no_last_file_guess(self):
        self.assertEqual([x["path"] for x in attributed_files(REPO, stderr="SyntaxError at src/server.py:1")],
                         ["src/server.py"])

    def test_log_secrets_redacted_before_truncation(self):
        redacted = sanitized_tail("postgres://admin:password@host/db" + "z"*200, limit=220)
        self.assertNotIn("password@host", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_sandbox_rejects_path_traversal(self):
        with self.assertRaises(SandboxRequestRejected):
            validate_snapshot({"../outside.py": "print('x')"})

    def test_sandbox_rejects_secret_file(self):
        with self.assertRaises(SandboxRequestRejected):
            validate_snapshot({".env": "TOKEN=SECRET"})

    def test_sandbox_rejects_file_directory_collision(self):
        with self.assertRaises(SandboxRequestRejected):
            validate_snapshot({"src": "text", "src/server.py": "print(1)"})

    def test_sandbox_rejects_shell_command_controls(self):
        with self.assertRaises(SandboxRequestRejected):
            validate_command(["python", "-c", "print(1)\nprint(2)"], build_id="build1")

    def test_sandbox_strict_mode_denies_unlisted_command(self):
        with self.assertRaises(SandboxRequestRejected):
            validate_command(["curl", "https://invalid.test"], build_id="build1",
                             repository=REPO, strict=True)

    def test_bare_command_policy_preserves_legacy_non_shell_argv(self):
        validate_command(["python", "-m", "pytest"], build_id="build1", repository=REPO)

    def test_invalid_schema_version_does_not_accept_bool(self):
        with self.assertRaises(Exception):
            RepairPatchV1.model_validate({**PATCH, "schema_version": True})

    def test_execution_evidence_pass_requires_real_exit_code(self):
        from omni_prod.repair_contracts import EvidenceCheck
        with self.assertRaises(Exception):
            EvidenceCheck(name="unit", status="PASS", exit_code=None)


if __name__ == "__main__":
    unittest.main()
