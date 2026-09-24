import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from omni_prod.build_state import can_transition, assert_transition, terminal
from omni_prod.models import BuildStatus
from omni_prod.deployments import validate_environment, new_promotion
from omni_prod.usage import UsageEvent, UsageKind, Rate, cost
from omni_prod.provenance import build_manifest

class BuildStateTests(unittest.TestCase):
    def test_happy_path_transitions(self):
        self.assertTrue(can_transition(BuildStatus.QUEUED, BuildStatus.RUNNING))
        self.assertTrue(can_transition(BuildStatus.RUNNING, BuildStatus.READY))
        self.assertTrue(terminal(BuildStatus.READY))

    def test_illegal_transition_rejected(self):
        with self.assertRaises(ValueError):
            assert_transition(BuildStatus.READY, BuildStatus.RUNNING)

class DeploymentTests(unittest.TestCase):
    def test_environment_validation(self):
        self.assertEqual(validate_environment("production"), "production")
        with self.assertRaises(ValueError):
            validate_environment("../prod")

    def test_promotion_is_version_pinned(self):
        p = new_promotion(
            project_id="p1",
            version_id="v17",
            build_id="b9",
            environment="production",
            artifact_key="projects/p1/versions/v17/builds/b9/app.zip",
        )
        self.assertEqual(p.version_id, "v17")
        self.assertEqual(p.build_id, "b9")
        self.assertIn("v17", p.artifact_key)

class UsageTests(unittest.TestCase):
    def test_usage_cost(self):
        evt = UsageEvent(
            account_id="a1",
            project_id="p1",
            kind=UsageKind.BUILD_SECONDS,
            quantity=Decimal("12.5"),
        )
        rates = {
            UsageKind.BUILD_SECONDS: Rate(
                kind=UsageKind.BUILD_SECONDS,
                unit_price=Decimal("0.002"),
            )
        }
        self.assertEqual(cost(evt, rates), Decimal("0.025000"))

    def test_negative_usage_rejected(self):
        with self.assertRaises(ValueError):
            UsageEvent(
                account_id="a1",
                project_id="p1",
                kind=UsageKind.STORAGE_BYTES,
                quantity=Decimal("-1"),
            )

class ProvenanceTests(unittest.TestCase):
    def test_manifest_has_hash_and_ids(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "app.zip"
            p.write_bytes(b"hello")
            m = build_manifest(
                p,
                project_id="p1",
                version_id="v1",
                build_id="b1",
            )
            self.assertEqual(m["artifact"]["size"], 5)
            self.assertEqual(len(m["artifact"]["sha256"]), 64)
            self.assertEqual(m["version_id"], "v1")

if __name__ == "__main__":
    unittest.main()
