"""Direct regression of the EXISTING RepairAgent with feature flag on/off.

No provider request is made. Preserve legacy gateway and approval contracts.
"""
import json
import os
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from omni_prod.autonomous_agents import RepairAgent
from omni_prod.repair_contracts import repository_fingerprint
from omni_prod.repository_patch import FilePatch, PatchValidationError


class FakeGateway:
    def __init__(self, result):
        self.result, self.calls = result, []

    def complete_json(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class FakeSpec:
    acceptance = (SimpleNamespace(id="A1"),)

    def to_dict(self):
        return {"acceptance": [{"id": "A1"}]}


def summary(candidates=True):
    return {"files": [{"path": "src/site.py", "content": "broken", "chars": 6}],
            "file_count": 1, "total_chars": 6,
            "base_repository_fingerprint": repository_fingerprint({"src/site.py": "broken"}),
            "candidate_files": ([{"path": "src/site.py", "reason": "compiler traceback", "confidence": "HIGH"}]
                                if candidates else [])}


def structured_reply(changes):
    return {"schema_version": 1, "reason_code": "FIX_COMPILE_ERROR",
            "base_repository_fingerprint": summary()["base_repository_fingerprint"],
            "changes": changes, "repaired_acceptance_ids": ["A1"],
            "summary": "targeted repair", "requires_dependency_change": False}


class RealAgentRepairIntegrationTests(unittest.TestCase):
    def test_default_is_still_legacy_gateway(self):
        gw = FakeGateway({"files": [{"path": "src/site.py", "content": "fixed"}]})
        with patch.dict(os.environ, {"OMNI_REPAIR_STRUCTURED_V1": "0"}):
            result = RepairAgent(gw).repair(spec=FakeSpec(), repo_summary=summary(), failures=[])
        self.assertEqual(result, (FilePatch("src/site.py", "fixed"),))
        self.assertEqual(gw.calls[0]["max_tokens"], 20000)

    def test_structured_repair_uses_same_gateway(self):
        gw = FakeGateway(structured_reply([
            {"path": "src/site.py", "operation": "UPSERT", "content": "fixed"}]))
        with patch.dict(os.environ, {"OMNI_REPAIR_STRUCTURED_V1": "1"}):
            result = RepairAgent(gw).repair(spec=FakeSpec(), repo_summary=summary(),
                                            failures=[{"acceptance_id": "A1",
                                                       "message": "SyntaxError src/site.py:1"}])
        self.assertEqual(result, (FilePatch("src/site.py", "fixed"),))
        self.assertEqual(gw.calls[0]["max_tokens"], 12000)
        self.assertIn("base_repository_fingerprint", json.loads(gw.calls[0]["user"])["repository"])

    def test_unattributed_failure_refuses_expensive_model_call(self):
        gw = FakeGateway({})
        with patch.dict(os.environ, {"OMNI_REPAIR_STRUCTURED_V1": "1"}):
            with self.assertRaises(PatchValidationError):
                RepairAgent(gw).repair(spec=FakeSpec(), repo_summary=summary(False), failures=[])
        self.assertEqual(gw.calls, [])

    def test_model_cannot_add_unrelated_file_in_multifile_patch(self):
        gw = FakeGateway(structured_reply([
            {"path": "src/site.py", "operation": "UPSERT", "content": "fixed"},
            {"path": "src/hidden.py", "operation": "UPSERT", "content": "malicious"},
        ]))
        with patch.dict(os.environ, {"OMNI_REPAIR_STRUCTURED_V1": "1"}):
            with self.assertRaises(PatchValidationError):
                RepairAgent(gw).repair(spec=FakeSpec(), repo_summary=summary(), failures=[])
        self.assertEqual(len(gw.calls), 1)

    def test_untrusted_failure_secret_redacted_before_model_prompt(self):
        gw = FakeGateway(structured_reply([
            {"path": "src/site.py", "operation": "UPSERT", "content": "fixed"}]))
        with patch.dict(os.environ, {"OMNI_REPAIR_STRUCTURED_V1": "1"}):
            RepairAgent(gw).repair(spec=FakeSpec(), repo_summary=summary(),
                                   failures=[{"acceptance_id": "A1",
                                              "message": "postgres://admin:privatepass@db/project"}])
        self.assertNotIn("privatepass", gw.calls[0]["user"])
        self.assertIn("[REDACTED]", gw.calls[0]["user"])


if __name__ == "__main__":
    unittest.main()
