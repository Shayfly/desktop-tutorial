import tempfile
import unittest
from pathlib import Path

from omni_prod.backup_manifest import (
    write_backup_manifest, verify_backup_manifest
)
from omni_prod.metrics import MetricsRegistry
from omni_prod.recovery_drill import run_backup_restore_drill
from omni_prod.request_id import normalize_request_id
from omni_prod.slo import SLOTarget, evaluate_slo
from omni_prod.structured_event import make_event

class RequestIDTests(unittest.TestCase):
    def test_valid_request_id_preserved(self):
        self.assertEqual(
            normalize_request_id("req-12345678"),
            "req-12345678"
        )

    def test_invalid_request_id_replaced(self):
        value = normalize_request_id("../bad")
        self.assertNotEqual(value, "../bad")
        self.assertEqual(len(value), 32)

class MetricsTests(unittest.TestCase):
    def test_render(self):
        r = MetricsRegistry()
        r.inc("requests_total")
        r.observe("latency_ms", 10)
        text = r.render_prometheus()
        self.assertIn("requests_total 1.0", text)
        self.assertIn("latency_ms_count 1", text)

class SLOTests(unittest.TestCase):
    def test_slo_pass(self):
        target = SLOTarget(.02, 500, min_samples=100)
        result = evaluate_slo(
            target,
            latencies_ms=[100.0] * 100,
            errors=1,
        )
        self.assertEqual(result.status, "pass")

    def test_slo_fail(self):
        target = SLOTarget(.02, 500, min_samples=100)
        result = evaluate_slo(
            target,
            latencies_ms=[100.0] * 95 + [900.0] * 5,
            errors=3,
        )
        self.assertEqual(result.status, "fail")

class BackupTests(unittest.TestCase):
    def test_manifest_detects_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root/"db.dump").write_bytes(b"one")
            write_backup_manifest(root)
            ok, _ = verify_backup_manifest(root)
            self.assertTrue(ok)
            (root/"db.dump").write_bytes(b"two")
            ok, errors = verify_backup_manifest(root)
            self.assertFalse(ok)
            self.assertTrue(errors)

    def test_restore_drill(self):
        result = run_backup_restore_drill()
        self.assertTrue(result["manifest_verified"])
        self.assertTrue(result["database_restore_verified"])

class StructuredEventTests(unittest.TestCase):
    def test_secrets_redacted(self):
        event = make_event(
            event_type="provider.error",
            request_id="req-12345678",
            message="Authorization: Bearer abcdefghijklmnopqrstuvwxyz123",
            fields={"password": "password=hunter2"}
        )
        blob = str(event)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123", blob)
        self.assertNotIn("hunter2", blob)

if __name__ == "__main__":
    unittest.main()
