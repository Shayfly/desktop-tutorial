import json
import tempfile
import unittest
from pathlib import Path

from omni_prod.audit import GENESIS, create_event, verify_chain
from omni_prod.canary import CanaryObservation, CanaryPolicy
from omni_prod.canary_controller import CanaryState, next_canary_state
from omni_prod.migrations import discover_migrations, verify_applied, pending_migrations
from omni_prod.release_manifest import write_release_manifest, verify_release_manifest
from omni_prod.secret_scan import scan_text
from omni_prod.staging_simulation import run_staging_simulation

class MigrationTests(unittest.TestCase):
    def test_migration_discovery_and_checksum_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "001_init.sql").write_text("SELECT 1;\n", encoding="utf-8")
            (root / "002_more.sql").write_text("SELECT 2;\n", encoding="utf-8")
            migrations = discover_migrations(root)
            self.assertEqual([m.version for m in migrations], [1, 2])
            applied = {1: migrations[0].sha256}
            self.assertEqual([m.version for m in pending_migrations(migrations, applied)], [2])
            (root / "001_init.sql").write_text("SELECT 9;\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                verify_applied(discover_migrations(root), applied)

class AuditTests(unittest.TestCase):
    def test_hash_chain_detects_tamper(self):
        e1 = create_event(
            sequence=1, event_type="build.created", actor_id="u1",
            resource_id="b1", payload={"status": "queued"}, previous_hash=GENESIS,
            timestamp="2026-09-20T00:00:00+00:00"
        )
        e2 = create_event(
            sequence=2, event_type="build.ready", actor_id="worker1",
            resource_id="b1", payload={"status": "ready"}, previous_hash=e1.event_hash,
            timestamp="2026-09-20T00:01:00+00:00"
        )
        self.assertTrue(verify_chain([e1, e2]))
        bad = type(e2)(
            sequence=e2.sequence, event_type=e2.event_type, actor_id=e2.actor_id,
            resource_id=e2.resource_id, timestamp=e2.timestamp,
            payload={"status": "failed"}, previous_hash=e2.previous_hash,
            event_hash=e2.event_hash
        )
        self.assertFalse(verify_chain([e1, bad]))

class SecretScanTests(unittest.TestCase):
    def test_detects_real_looking_secrets(self):
        findings = scan_text(
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456\n"
            "api_key=abcdefghijklmnopqrstuvwx123456\n"
        )
        self.assertGreaterEqual(len(findings), 2)

    def test_ignores_placeholders(self):
        self.assertEqual(scan_text("secret=CHANGE_ME_WITH_64_RANDOM_CHARS"), [])

class ManifestTests(unittest.TestCase):
    def test_manifest_detects_file_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("one", encoding="utf-8")
            write_release_manifest(root, version="V16", test_count=1)
            ok, errors = verify_release_manifest(root)
            self.assertTrue(ok, errors)
            (root / "a.txt").write_text("two", encoding="utf-8")
            ok, errors = verify_release_manifest(root)
            self.assertFalse(ok)
            self.assertTrue(any("mismatch" in e for e in errors))

class CanaryControllerTests(unittest.TestCase):
    def test_canary_progresses_to_complete(self):
        policy = CanaryPolicy(
            initial_percent=5, step_percent=50,
            error_rate_threshold=.02, min_requests=100
        )
        state = CanaryState(5, "running")
        state = next_canary_state(policy, state, CanaryObservation(200, 1))
        self.assertEqual(state.percent, 55)
        state = next_canary_state(policy, state, CanaryObservation(200, 1))
        self.assertEqual(state.status, "complete")
        self.assertEqual(state.percent, 100)

    def test_canary_rolls_back_on_regression(self):
        policy = CanaryPolicy(min_requests=100, error_rate_threshold=.02)
        state = next_canary_state(
            policy, CanaryState(5, "running"), CanaryObservation(1000, 30)
        )
        self.assertEqual((state.status, state.percent), ("rolled_back", 0))

class StagingSimulationTests(unittest.TestCase):
    def test_full_staging_simulation(self):
        result = run_staging_simulation()
        self.assertEqual(result.build_status, "ready")
        self.assertEqual(result.final_canary_status, "complete")
        self.assertEqual(result.final_canary_percent, 100)
        self.assertEqual(result.deployments, 1)
        self.assertEqual(result.artifacts, 1)

if __name__ == "__main__":
    unittest.main()
