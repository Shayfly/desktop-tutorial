import unittest
from pathlib import Path

from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.capability_repository import (
    AttemptLeaseConflict, MemoryCapabilityRepository, PostgresCapabilityRepository,
)


def plan():
    return CapabilityPlan(
        requirements=(
            CapabilityRequirement("r-plan", "software.plan", "plan", True),
            CapabilityRequirement(
                "r-build", "software.build", "build", True,
                dependency_ids=("r-plan",),
            ),
        ),
        target_keys=("target.web",),
    )


class _Ctx:
    def __init__(self, value=None):
        self.value = value
    def __enter__(self):
        return self.value if self.value is not None else self
    def __exit__(self, *args):
        return False


class ScriptedCursor:
    def __init__(self, fetch=(), rowcounts=()):
        self.executed = []
        self._fetch = list(fetch)
        self._rowcounts = list(rowcounts)
        self.rowcount = 0
    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))
        self.rowcount = self._rowcounts.pop(0) if self._rowcounts else 1
    def fetchone(self):
        return self._fetch.pop(0) if self._fetch else None
    def fetchall(self):
        row = self._fetch.pop(0) if self._fetch else []
        return row if isinstance(row, list) else [row]
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
    def transaction(self):
        return _Ctx()
    def cursor(self):
        return self._cursor


class FakePool:
    def __init__(self, cursor):
        self._conn = FakeConn(cursor)
    def connection(self):
        return _Ctx(self._conn)


class CapabilityRepositoryMemoryTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryCapabilityRepository()
        self.repo.create_plan(build_id="b1", plan=plan())

    def test_create_plan_is_idempotent_for_identical_plan_and_rejects_drift(self):
        self.repo.create_plan(build_id="b1", plan=plan())
        drift = CapabilityPlan(
            requirements=(CapabilityRequirement("r-plan", "software.architecture", "changed", True),),
            target_keys=("target.web",),
        )
        with self.assertRaisesRegex(ValueError, "plan drift"):
            self.repo.create_plan(build_id="b1", plan=drift)

    def test_requirement_transition_is_compare_and_set(self):
        self.assertTrue(
            self.repo.transition(
                build_id="b1", requirement_id="r-plan",
                expected="PLANNED", target="QUOTED",
                selected_provider="p", pricing_version="v1",
            )
        )
        self.assertFalse(
            self.repo.transition(
                build_id="b1", requirement_id="r-plan",
                expected="PLANNED", target="FAILED",
            )
        )
        row = {r["requirement_id"]: r for r in self.repo.requirements(build_id="b1")}["r-plan"]
        self.assertEqual(row["status"], "QUOTED")
        self.assertEqual(row["selected_provider"], "p")

    def test_usage_event_is_idempotent_by_event_key(self):
        event = {
            "event_key": "b1:r-plan:p:collect:v1",
            "build_id": "b1",
            "account_id": "a1",
            "project_id": "p1",
            "requirement_id": "r-plan",
            "capability_key": "software.plan",
            "provider": "p",
            "provider_operation": "collect",
            "status": "SUCCEEDED",
            "actual_cost_usd": None,
        }
        first = self.repo.record_usage(event=event)
        second = self.repo.record_usage(event=dict(event))
        self.assertEqual(first, second)
        self.assertEqual(len(self.repo.usage_for_build(build_id="b1")), 1)

    def test_execution_attempt_identity_survives_retry(self):
        first = self.repo.ensure_execution_attempt(
            attempt_id="att-1", build_id="b1", requirement_id="r-plan",
            provider="p", pricing_version="v1", idempotency_key="idem-1",
        )
        second = self.repo.ensure_execution_attempt(
            attempt_id="att-2", build_id="b1", requirement_id="r-plan",
            provider="p", pricing_version="v1", idempotency_key="idem-1",
        )
        self.assertEqual(first["attempt_id"], "att-1")
        self.assertEqual(second["attempt_id"], "att-1")
        self.assertEqual(second["idempotency_key"], "idem-1")

    def test_execution_lease_prevents_parallel_workers_and_expires(self):
        self.repo.ensure_execution_attempt(
            attempt_id="att-1", build_id="b1", requirement_id="r-plan",
            provider="p", pricing_version="v1", idempotency_key="idem-1",
        )
        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w1", now=100, lease_seconds=30))
        self.assertFalse(self.repo.claim_execution_attempt("idem-1", worker_id="w2", now=120, lease_seconds=30))
        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w2", now=131, lease_seconds=30))

    def test_provider_task_id_is_persisted_once_and_resume_returns_same_handle(self):
        self.repo.ensure_execution_attempt(
            attempt_id="att-1", build_id="b1", requirement_id="r-plan",
            provider="p", pricing_version="v1", idempotency_key="idem-1",
        )
        self.assertTrue(self.repo.record_provider_handle("idem-1", provider_task_id="task-777"))
        self.assertTrue(self.repo.record_provider_handle("idem-1", provider_task_id="task-777"))
        with self.assertRaisesRegex(ValueError, "provider task identity conflict"):
            self.repo.record_provider_handle("idem-1", provider_task_id="task-other")
        resumed = self.repo.execution_attempt("idem-1")
        self.assertEqual(resumed["provider_task_id"], "task-777")
        self.assertEqual(resumed["status"], "SUBMITTED")

    def test_execution_status_transition_is_cas_and_terminal_attempt_cannot_be_reclaimed(self):
        self.repo.ensure_execution_attempt(
            attempt_id="att-1", build_id="b1", requirement_id="r-plan",
            provider="p", pricing_version="v1", idempotency_key="idem-1",
        )
        self.assertTrue(self.repo.transition_execution_attempt("idem-1", expected="SUBMITTING", target="FAILED"))
        self.assertFalse(self.repo.transition_execution_attempt("idem-1", expected="SUBMITTING", target="RUNNING"))
        self.assertFalse(self.repo.claim_execution_attempt("idem-1", worker_id="w", now=1000, lease_seconds=30))

    def test_stale_worker_cannot_mutate_after_lease_is_reclaimed(self):
        self.repo.ensure_execution_attempt(
            attempt_id="att-1", build_id="b1", requirement_id="r-plan",
            provider="p", pricing_version="v1", idempotency_key="idem-1",
        )
        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w1", now=100, lease_seconds=10))
        self.assertTrue(self.repo.claim_execution_attempt("idem-1", worker_id="w2", now=111, lease_seconds=10))
        with self.assertRaises(AttemptLeaseConflict):
            self.repo.record_provider_handle("idem-1", provider_task_id="provider-task", worker_id="w1")
        self.assertTrue(
            self.repo.record_provider_handle("idem-1", provider_task_id="provider-task", worker_id="w2")
        )


class MigrationContractTests(unittest.TestCase):
    def test_migration_has_durable_attempt_and_usage_idempotency_columns(self):
        text = Path("infra/postgres/017_capability_foundation.sql").read_text()
        normalized = " ".join(text.lower().split())
        self.assertIn("create table if not exists build_capability_requirements", normalized)
        self.assertIn("create table if not exists provider_execution_attempts", normalized)
        self.assertIn("provider_task_id text", normalized)
        self.assertIn("idempotency_key text not null unique", normalized)
        self.assertIn("pricing_version text not null", normalized)
        self.assertIn("lease_expires_at timestamptz", normalized)
        self.assertIn("'submitting'", normalized)
        self.assertNotIn("lease_owner text not null", normalized)
        self.assertIn("create table if not exists provider_usage_events", normalized)
        self.assertIn("event_key text not null unique", normalized)
        self.assertNotIn("api_key", normalized)
        self.assertNotIn("refresh_token", normalized)


class PostgresCapabilityRepositoryContractTests(unittest.TestCase):
    def test_ensure_attempt_persists_pricing_version_before_external_submit(self):
        cur = ScriptedCursor(fetch=[None])
        repo = PostgresCapabilityRepository(FakePool(cur))
        row = repo.ensure_execution_attempt(
            attempt_id="att-1", build_id="b1", requirement_id="r-plan", provider="p",
            pricing_version="price-2026-10", idempotency_key="idem-1",
        )
        self.assertEqual(row["status"], "SUBMITTING")
        insert_sql, params = cur.executed[-1]
        self.assertIn("pricing_version", insert_sql.lower())
        self.assertIn("SUBMITTING", params)
        self.assertIn("price-2026-10", params)

    def test_transition_attempt_requires_current_lease_owner(self):
        cur = ScriptedCursor(rowcounts=[1])
        repo = PostgresCapabilityRepository(FakePool(cur))
        self.assertTrue(repo.transition_execution_attempt(
            "idem-1", expected="SUBMITTED", target="RUNNING", worker_id="worker-1"
        ))
        sql, params = cur.executed[-1]
        lowered = sql.lower()
        self.assertIn("status=%s", lowered)
        self.assertIn("lease_owner=%s", lowered)
        self.assertIn("idempotency_key=%s", lowered)
        self.assertEqual(params[-1], "worker-1")


if __name__ == "__main__":
    unittest.main()
