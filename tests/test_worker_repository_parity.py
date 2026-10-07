"""Postgres repositories used by the worker implement what the worker calls.

Golden E2E #1 on Preview (2026-10-07): the first real build failed with
"'PostgresCapabilityRepository' object has no attribute 'create_plan'" because
every worker test used MemoryCapabilityRepository. These tests pin the
interface and the semantics of the Postgres twin (the real-Postgres run of the
capability stage is recorded in STATUS.md). Also covers the migration runner
on an empty database (schema_migrations is created by migration 005, after
001-004 already need it).
"""
import ast
import json
import re
import unittest
from pathlib import Path

from omni_prod.capabilities import CapabilityPlan
from omni_prod.capability_repository import MemoryCapabilityRepository, PostgresCapabilityRepository
from omni_prod.migration_runner import _load_applied, apply_migrations
from omni_prod.product_architect import ProductArchitect

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ("Build a team task tracker web app: users sign up and log in, create projects, add tasks with title, "
          "due date and status, assign tasks to teammates, and see a dashboard of overdue tasks.")


def _called_repository_methods() -> set[str]:
    names = set()
    for path in (ROOT / "omni_prod").rglob("*.py"):
        names |= set(re.findall(r"repository\.(\w+)\(", path.read_text()))
    return names


class InterfaceParityTests(unittest.TestCase):
    def test_every_called_method_exists_on_the_postgres_twin(self):
        memory = {n for n in dir(MemoryCapabilityRepository) if not n.startswith("_")}
        called = _called_repository_methods() & memory
        self.assertIn("create_plan", called)
        self.assertIn("transition", called)
        missing = sorted(n for n in called if not hasattr(PostgresCapabilityRepository, n))
        self.assertEqual(missing, [])


class _Cur:
    """Scripted cursor: each execute() pops the next queued result set."""

    def __init__(self, results):
        self.results, self.sql, self.current = list(results), [], []

    def execute(self, sql, params=None):
        self.sql.append((" ".join(sql.split()), params))
        self.current = self.results.pop(0) if self.results else []

    def fetchone(self):
        return self.current[0] if self.current else None

    def fetchall(self):
        return list(self.current)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Pool:
    def __init__(self, cur):
        self.cur = cur

    def connection(self):
        pool = self

        class Conn:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def transaction(self): return self
            def cursor(self): return pool.cur
        return Conn()


def _plan():
    return ProductArchitect().compile(PROMPT, project_id="prj_golden", contract_version=1).capability_plan


def _stored_rows(plan):
    return [(r.id, r.key, r.purpose, r.required, r.quantity, json.dumps(dict(r.constraints)),
             json.dumps(list(r.dependency_ids))) for r in plan.requirements]


class CreatePlanTests(unittest.TestCase):
    def test_inserts_every_requirement_idempotently(self):
        plan = _plan()
        cur = _Cur([[]] * len(plan.requirements) + [_stored_rows(plan)])
        PostgresCapabilityRepository(_Pool(cur)).create_plan(build_id="bld_1", plan=plan)
        inserts = [s for s, _ in cur.sql if s.startswith("INSERT INTO build_capability_requirements")]
        self.assertEqual(len(inserts), len(plan.requirements))
        self.assertTrue(all("ON CONFLICT (build_id, requirement_id) DO NOTHING" in s for s in inserts))

    def test_different_plan_for_the_same_build_is_drift(self):
        plan = _plan()
        smaller = CapabilityPlan(requirements=plan.requirements[:-1], target_keys=plan.target_keys, notes=plan.notes)
        cur = _Cur([[]] * len(smaller.requirements) + [_stored_rows(plan)])
        with self.assertRaises(ValueError):
            PostgresCapabilityRepository(_Pool(cur)).create_plan(build_id="bld_1", plan=smaller)

    def test_save_plan_is_the_same_operation(self):
        plan = _plan()
        cur = _Cur([[]] * len(plan.requirements) + [_stored_rows(plan)])
        PostgresCapabilityRepository(_Pool(cur)).save_plan("bld_1", plan)
        self.assertTrue(cur.sql[-1][0].startswith("SELECT requirement_id"))


class TransitionTests(unittest.TestCase):
    def _transition(self, results, **kw):
        cur = _Cur(results)
        args = dict(build_id="bld_1", requirement_id="req_1", expected="PLANNED", target="VERIFIED")
        args.update(kw)
        return PostgresCapabilityRepository(_Pool(cur)).transition(**args), cur

    def test_compare_and_set_success(self):
        ok, cur = self._transition([[("req_1",)]], verification={"core_ready": True})
        self.assertTrue(ok)
        sql, params = cur.sql[0]
        self.assertIn("WHERE build_id=%s AND requirement_id=%s AND status=%s", sql)
        self.assertEqual(params[0], "VERIFIED")
        self.assertEqual(json.loads(params[4]), {"core_ready": True})
        self.assertEqual(params[-3:], ("bld_1", "req_1", "PLANNED"))

    def test_status_mismatch_returns_false(self):
        ok, _ = self._transition([[], [(1,)]])
        self.assertFalse(ok)

    def test_missing_requirement_raises_like_the_memory_twin(self):
        with self.assertRaises(KeyError):
            self._transition([[], []])
        with self.assertRaises(KeyError):
            MemoryCapabilityRepository().transition(build_id="b", requirement_id="r", expected="PLANNED", target="FAILED")


class EmptyDatabaseMigrationTests(unittest.TestCase):
    def test_load_applied_on_an_empty_database(self):
        self.assertEqual(_load_applied(_Cur([[(False,)]])), {})

    def test_bookkeeping_table_exists_before_the_first_migration(self):
        cur = _Cur([[], [], [(False,)]])

        class Conn:
            def transaction(self): return cur
            def cursor(self): return cur
        run = apply_migrations(Conn(), [])
        self.assertEqual(run.applied_versions, ())
        statements = [s for s, _ in cur.sql]
        self.assertTrue(statements[0].startswith("SELECT pg_advisory_xact_lock"))
        self.assertTrue(statements[1].startswith("CREATE TABLE IF NOT EXISTS schema_migrations"))


class FailedBuildStepsTests(unittest.TestCase):
    def test_steps_after_the_failure_are_never_shown_as_done(self):
        js = (ROOT / "omni_prod/assets/app.js").read_text()
        self.assertIn("const FAIL_STEP =", js)
        self.assertNotIn("reached > idx || reached === -1 ? 'done'", js)


if __name__ == "__main__":
    unittest.main()
