"""#236: live_core DDL moved into migration 042, with a hand-run rollback.

Unit tests (always run) pin the migration to the fallback DDL, the rollback to the
exact objects the migration creates, and the fallback switch-off. The PostgreSQL
class (needs M4D2_DATABASE_URL, run by intake-budget-pg) applies every repository
migration to a throw-away database, then 042 on top of the existing schema, then
the rollback, and requires the schema to match the pre-042 fingerprint exactly.
"""
from __future__ import annotations

import os
import re
import unittest
import uuid
from pathlib import Path

from live_core import postgres_store as PS
from omni_prod.migrations import discover_migrations

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "infra" / "postgres"
UP = MIGRATIONS / "042_live_core_tables.sql"
DOWN = MIGRATIONS / "rollback" / "042_live_core_tables.down.sql"
DATABASE_URL = os.getenv("M4D2_DATABASE_URL", "").strip()

TABLES = ["live_users", "live_sessions", "live_projects", "live_artifacts",
          "live_versions", "live_builds", "live_build_events"]
INDEXES = ["idx_live_projects_owner", "idx_live_versions_project", "idx_live_versions_owner_project",
           "idx_live_builds_owner_project", "idx_live_build_events_build", "idx_live_artifacts_owner_project"]


def _statements(sql: str) -> list[str]:
    body = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    return [re.sub(r"\s+", " ", s).strip() for s in body.split(";") if s.strip()]


class MigrationFileTests(unittest.TestCase):
    def test_042_is_discovered_and_is_the_newest(self):
        found = discover_migrations(MIGRATIONS)
        self.assertEqual(found[-1].version, 42)
        self.assertEqual(found[-1].name, "live_core_tables")

    def test_042_is_exactly_the_fallback_ddl(self):
        # One source of truth in two places: they must never drift.
        self.assertEqual(_statements(UP.read_text()), _statements(PS.SCHEMA))

    def test_042_creates_seven_tables_and_six_indexes_idempotently(self):
        stmts = _statements(UP.read_text())
        created_tables = [re.search(r"CREATE TABLE IF NOT EXISTS (\w+)", s).group(1)
                          for s in stmts if s.startswith("CREATE TABLE")]
        created_indexes = [re.search(r"CREATE INDEX IF NOT EXISTS (\w+)", s).group(1)
                           for s in stmts if s.startswith("CREATE INDEX")]
        self.assertEqual(created_tables, TABLES)
        self.assertEqual(sorted(created_indexes), sorted(INDEXES))
        self.assertTrue(all("IF NOT EXISTS" in s for s in stmts))

    def test_042_touches_only_live_objects(self):
        text = UP.read_text()
        # Only CREATE statements: nothing is dropped, altered or rewritten.
        self.assertTrue(all(s.startswith("CREATE ") for s in _statements(text)))
        referenced = set(re.findall(r"REFERENCES (\w+)", text))
        self.assertTrue(referenced <= set(TABLES), referenced)

    def test_rollback_is_not_run_by_the_migration_runner(self):
        # The runner reads infra/postgres/*.sql only; the rollback lives in a subdirectory.
        names = {m.path.name for m in discover_migrations(MIGRATIONS)}
        self.assertNotIn(DOWN.name, names)
        self.assertTrue(DOWN.exists())

    def test_rollback_removes_exactly_what_042_creates(self):
        stmts = _statements(DOWN.read_text())
        dropped_tables = [re.search(r"DROP TABLE IF EXISTS (\w+)", s).group(1) for s in stmts if "DROP TABLE" in s]
        dropped_indexes = [re.search(r"DROP INDEX IF EXISTS (\w+)", s).group(1) for s in stmts if "DROP INDEX" in s]
        self.assertEqual(dropped_tables, list(reversed(TABLES)))
        self.assertEqual(sorted(dropped_indexes), sorted(INDEXES))
        self.assertIn("DELETE FROM schema_migrations WHERE version = 42", stmts)
        self.assertEqual(stmts[0], "BEGIN")
        self.assertEqual(stmts[-1], "COMMIT")
        self.assertNotRegex(DOWN.read_text(), r"(?i)\bcascade\b")


class _Conn:
    """Records executed SQL; answers the two migration_applied probes."""

    def __init__(self, table_present: bool, applied: bool):
        self.table_present, self.applied, self.executed = table_present, applied, []

    def execute(self, sql, args=()):
        self.executed.append(sql)
        conn = self

        class _Cur:
            def fetchone(self_inner):
                if "to_regclass" in sql:
                    return {"present": conn.table_present}
                if "schema_migrations WHERE version" in sql:
                    return {"applied": conn.applied}
                return None
        return _Cur()


class FallbackTests(unittest.TestCase):
    def _store(self):
        return PS.PostgresStore("postgresql://unused.invalid/db")

    def test_fallback_ddl_does_not_run_once_042_is_recorded(self):
        conn = _Conn(table_present=True, applied=True)
        self._store()._ensure_schema(conn)
        self.assertNotIn(PS.SCHEMA, conn.executed)

    def test_fallback_ddl_runs_when_042_is_not_recorded(self):
        conn = _Conn(table_present=True, applied=False)
        self._store()._ensure_schema(conn)
        self.assertIn(PS.SCHEMA, conn.executed)

    def test_fallback_ddl_runs_on_a_database_without_schema_migrations(self):
        conn = _Conn(table_present=False, applied=False)
        self._store()._ensure_schema(conn)
        self.assertIn(PS.SCHEMA, conn.executed)
        self.assertFalse(any("WHERE version" in s for s in conn.executed))


_FINGERPRINT = """
SELECT
  (SELECT count(*) FROM pg_tables WHERE schemaname = 'public') AS tables,
  (SELECT count(*) FROM pg_indexes WHERE schemaname = 'public') AS indexes,
  (SELECT max(version) FROM schema_migrations) AS max_migration,
  (SELECT md5(string_agg(table_name||'.'||column_name||':'||data_type||':'||is_nullable, ','
               ORDER BY table_name, ordinal_position))
     FROM information_schema.columns WHERE table_schema = 'public') AS columns_md5,
  (SELECT md5(string_agg(indexdef, ',' ORDER BY indexname)) FROM pg_indexes WHERE schemaname = 'public') AS indexes_md5,
  (SELECT md5(string_agg(conname||':'||pg_get_constraintdef(oid), ',' ORDER BY conname))
     FROM pg_constraint WHERE connamespace = 'public'::regnamespace) AS constraints_md5
"""


class RealPostgresMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest("BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured")
        try:
            import psycopg
            cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        except Exception as exc:
            raise unittest.SkipTest(f"BLOCKED: PostgreSQL unreachable ({type(exc).__name__})")
        cls.dbname = f"m042_{uuid.uuid4().hex[:10]}"
        cls.admin.execute(f"CREATE DATABASE {cls.dbname}")
        cls.url = DATABASE_URL.rsplit("/", 1)[0] + "/" + cls.dbname

    @classmethod
    def tearDownClass(cls):
        cls.admin.execute(f"DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)")
        cls.admin.close()

    def test_042_on_an_existing_schema_then_rollback_restores_it_exactly(self):
        import psycopg
        from omni_prod.migration_runner import apply_migrations

        everything = discover_migrations(MIGRATIONS)
        before_042 = [m for m in everything if m.version < 42]
        with psycopg.connect(self.url) as conn:
            apply_migrations(conn, before_042)                      # the existing schema (001-041)
            conn.commit()
            baseline = conn.execute(_FINGERPRINT).fetchone()
            self.assertEqual(baseline[2], 41)

            run = apply_migrations(conn, everything)                 # 042 on top of it, via the real runner
            conn.commit()
            self.assertEqual(run.applied_versions, (42,))
            live_tables = conn.execute(
                "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'live\\_%'").fetchone()[0]
            live_indexes = conn.execute(
                "SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'idx\\_live\\_%'").fetchone()[0]
            self.assertEqual((live_tables, live_indexes), (7, 6))
            self.assertTrue(PS.migration_applied(conn))

            conn.execute(DOWN.read_text())                            # the hand-run rollback
            conn.commit()
            self.assertEqual(conn.execute(_FINGERPRINT).fetchone(), baseline)
            self.assertFalse(PS.migration_applied(conn))

            again = apply_migrations(conn, everything)               # and 042 applies cleanly again
            conn.commit()
            self.assertEqual(again.applied_versions, (42,))

    def test_042_is_clean_where_the_fallback_ddl_already_ran(self):
        import psycopg
        from omni_prod.migration_runner import apply_migrations

        dbname = f"m042f_{uuid.uuid4().hex[:10]}"
        self.admin.execute(f"CREATE DATABASE {dbname}")
        try:
            url = DATABASE_URL.rsplit("/", 1)[0] + "/" + dbname
            everything = discover_migrations(MIGRATIONS)
            with psycopg.connect(url) as conn:
                apply_migrations(conn, [m for m in everything if m.version < 42])
                conn.execute(PS.SCHEMA)                               # what an earlier first request did
                conn.commit()
                run = apply_migrations(conn, everything)
                conn.commit()
                self.assertEqual(run.applied_versions, (42,))
        finally:
            self.admin.execute(f"DROP DATABASE IF EXISTS {dbname} WITH (FORCE)")
