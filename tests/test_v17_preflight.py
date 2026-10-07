import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_prod.artifact_integrity import digest_bytes, verify_bytes
from omni_prod.migration_runner import apply_migrations
from omni_prod.migrations import discover_migrations
from omni_prod.preflight import run_preflight

class ArtifactIntegrityTests(unittest.TestCase):
    def test_integrity_accepts_exact_bytes(self):
        data = b"artifact"
        verify_bytes(data, digest_bytes(data))

    def test_integrity_rejects_tamper(self):
        expected = digest_bytes(b"artifact")
        with self.assertRaises(RuntimeError):
            verify_bytes(b"artifact!", expected)

class PreflightTests(unittest.TestCase):
    def base_env(self):
        return {
            "OMNI_SECRET_KEY": "x" * 64,
            "OMNI_DATABASE_URL": "postgresql://omni:pw@db/omni",
            "OMNI_REDIS_URL": "redis://redis:6379/0",
            "OMNI_ALLOWED_ORIGINS": "https://app.example.com",
            "OMNI_S3_ACCESS_KEY": "realaccessvalue123456",
            "OMNI_S3_SECRET_KEY": "realsecretvalue123456789",
        }

    def test_preflight_fails_closed_when_runtime_dependencies_missing(self):
        with patch("omni_prod.preflight._module_exists", return_value=False), \
             patch("omni_prod.preflight._binary_exists", return_value=False):
            report = run_preflight(self.base_env())
        self.assertFalse(report.ready)
        self.assertTrue(any(i.code.startswith("missing_") for i in report.issues))

    def test_preflight_accepts_complete_runtime(self):
        with patch("omni_prod.preflight._module_exists", return_value=True), \
             patch("omni_prod.preflight._binary_exists", return_value=True):
            report = run_preflight(self.base_env())
        self.assertTrue(report.ready, report.issues)

    def test_preflight_rejects_http_origin_and_placeholder_secret(self):
        env = self.base_env()
        env["OMNI_ALLOWED_ORIGINS"] = "http://localhost:8787"
        env["OMNI_S3_SECRET_KEY"] = "CHANGE_ME"
        with patch("omni_prod.preflight._module_exists", return_value=True), \
             patch("omni_prod.preflight._binary_exists", return_value=True):
            report = run_preflight(env)
        codes = {i.code for i in report.issues}
        self.assertIn("https_origins", codes)
        self.assertIn("omni_s3_secret_key", codes)
        self.assertFalse(report.ready)

class FakeCursor:
    def __init__(self, applied):
        self.applied = dict(applied)
        self.rows = []
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        normalized = " ".join(sql.split()).lower()
        if normalized.startswith("select to_regclass('schema_migrations')"):
            self.rows = [(True,)]   # this fake database already has the bookkeeping table
        elif normalized.startswith("select version, sha256"):
            self.rows = sorted(self.applied.items())
        elif normalized.startswith("insert into schema_migrations"):
            version, name, sha = params
            self.applied[version] = sha

    def fetchall(self):
        return list(self.rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None

class FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

class FakeConnection:
    def __init__(self, applied=None):
        self.cursor_obj = FakeCursor(applied or {})

    def transaction(self):
        return FakeTransaction()

    def cursor(self):
        return self.cursor_obj

class MigrationRunnerTests(unittest.TestCase):
    def test_applies_only_pending_migrations_under_lock(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root/"001_init.sql").write_text("CREATE TABLE a(x int);", encoding="utf-8")
            (root/"002_more.sql").write_text("CREATE TABLE b(x int);", encoding="utf-8")
            migrations = discover_migrations(root)
            conn = FakeConnection({1: migrations[0].sha256})
            result = apply_migrations(conn, migrations)
            self.assertEqual(result.applied_versions, (2,))
            executed_sql = [" ".join(x[0].split()).lower() for x in conn.cursor_obj.executed]
            self.assertTrue(any("pg_advisory_xact_lock" in x for x in executed_sql))
            self.assertTrue(any("create table b" in x for x in executed_sql))

if __name__ == "__main__":
    unittest.main()
