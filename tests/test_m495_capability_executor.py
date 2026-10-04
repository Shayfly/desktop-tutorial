import hashlib
import unittest
from decimal import Decimal

from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.capability_executor import (
    CapabilityExecutionAssignment,
    CapabilityExecutionError,
    CapabilityExecutor,
)
from omni_prod.capability_repository import MemoryCapabilityRepository
from omni_prod.provider_contracts import (
    CapabilityArtifact,
    ProviderArtifactPayload,
    ProviderCapability,
    ProviderExecutionResult,
    ProviderQuote,
    ProviderTaskHandle,
    ProviderTaskState,
)
from omni_prod.provider_registry import ProviderRegistry
from omni_prod.storage import StoredObject


PNG = b"\x89PNG\r\n\x1a\n" + b"artifact-bytes"


def requirement(rid="r-image", *, deps=()):
    return CapabilityRequirement(
        rid, "media.image.generate", "hero image", True,
        constraints={"prompt": "hero"}, dependency_ids=tuple(deps),
    )


def quote(provider="media", maximum="0.20"):
    return ProviderQuote(
        provider, "media.image.generate", Decimal("0.10"), Decimal(maximum),
        "price-v1", "image", Decimal("1"),
    )


class MemoryStore:
    def __init__(self):
        self.objects = {}
    def put_bytes(self, key, data):
        data = bytes(data)
        self.objects[key] = data
        return StoredObject(key=key, sha256=hashlib.sha256(data).hexdigest(), size=len(data))
    def get_bytes(self, key, *, verify=True):
        return self.objects[key]
    def iter_bytes(self, key, **kwargs):
        yield self.objects[key]


class FakeProvider:
    name = "media"
    durable_idempotency = True
    paid_external = True

    def __init__(self, *, fail_first_poll=False, terminal="SUCCEEDED", result_factory=None):
        self.submit_calls = []
        self.poll_calls = []
        self.collect_calls = []
        self.fail_first_poll = fail_first_poll
        self.terminal = terminal
        self.result_factory = result_factory

    def capabilities(self):
        return (ProviderCapability("media.image.generate", ("image/png",), True),)
    def health(self):
        return "HEALTHY"
    def quote(self, requirement):
        return quote(self.name)
    def submit(self, req, *, idempotency_key):
        self.submit_calls.append((req.id, idempotency_key))
        return ProviderTaskHandle(self.name, f"task-{req.id}", req.id, idempotency_key)
    def poll(self, handle):
        self.poll_calls.append(handle.provider_task_id)
        if self.fail_first_poll:
            self.fail_first_poll = False
            raise RuntimeError("simulated worker/process interruption after durable submit")
        return ProviderTaskState(self.terminal, 1.0 if self.terminal == "SUCCEEDED" else None)
    def collect(self, handle):
        self.collect_calls.append(handle.provider_task_id)
        if self.result_factory:
            return self.result_factory(handle)
        return ProviderExecutionResult(
            artifacts=(), actual_cost_usd=None,
            usage={"images": 1}, evidence={"provider_request": handle.provider_task_id},
            payloads=(ProviderArtifactPayload("image/png", PNG, filename="hero.png"),),
        )
    def cancel(self, handle):
        return None


class CrashBeforeAtomicFinalizeRepository(MemoryCapabilityRepository):
    def __init__(self):
        super().__init__()
        self.crash_once = True
    def finalize_execution_success(self, **kwargs):
        if self.crash_once:
            self.crash_once = False
            raise RuntimeError("simulated crash before atomic finalization commit")
        return super().finalize_execution_success(**kwargs)
    def record_usage(self, *, event):
        raise AssertionError("executor must not split usage from atomic finalization")


class CapabilityExecutorTests(unittest.TestCase):
    def make_executor(self, provider, repo=None, store=None, *, worker_id="w1", lease_seconds=5):
        repo = repo or MemoryCapabilityRepository()
        store = store or MemoryStore()
        return CapabilityExecutor(
            provider_registry=ProviderRegistry((provider,)), repository=repo,
            artifact_store=store, worker_id=worker_id, lease_seconds=lease_seconds,
            max_polls=5,
        ), repo, store

    def run_one(self, executor, repo, req, *, now=100, project_id="p1"):
        plan = CapabilityPlan((req,), ("target.web",))
        if not repo.requirements(build_id="b1"):
            repo.create_plan(build_id="b1", plan=plan)
        return executor.execute_plan(
            build_id="b1", project_id=project_id, plan=plan,
            assignments={req.id: CapabilityExecutionAssignment("media", quote())}, now=now,
        )

    def test_restart_resumes_persisted_provider_task_without_duplicate_submit(self):
        provider = FakeProvider(fail_first_poll=True)
        repo = MemoryCapabilityRepository()
        store = MemoryStore()
        req = requirement()
        first, _, _ = self.make_executor(provider, repo, store, worker_id="worker-a")
        with self.assertRaisesRegex(RuntimeError, "interruption"):
            self.run_one(first, repo, req, now=100)
        attempt = next(iter(repo.attempts.values()))
        self.assertEqual(attempt.provider_task_id, "task-r-image")
        self.assertEqual(attempt.status, "SUBMITTED")
        self.assertEqual(len(provider.submit_calls), 1)

        restarted, _, _ = self.make_executor(provider, repo, store, worker_id="worker-b")
        summary = self.run_one(restarted, repo, req, now=106)
        self.assertEqual(len(provider.submit_calls), 1, "restart must reuse durable provider_task_id")
        self.assertEqual(summary.status, "VERIFIED")
        self.assertEqual(repo.requirements(build_id="b1")[0]["status"], "VERIFIED")
        self.assertEqual(next(iter(repo.attempts.values())).status, "SUCCEEDED")

    def test_crash_before_atomic_finalize_is_recoverable_without_split_truth(self):
        provider = FakeProvider()
        repo = CrashBeforeAtomicFinalizeRepository()
        store = MemoryStore()
        req = requirement()
        first, _, _ = self.make_executor(provider, repo, store, worker_id="worker-a")
        with self.assertRaisesRegex(RuntimeError, "before atomic finalization"):
            self.run_one(first, repo, req, now=100)
        # No partial truth may survive a failed finalization transaction.
        self.assertNotEqual(next(iter(repo.attempts.values())).status, "SUCCEEDED")
        self.assertEqual(repo.requirements(build_id="b1")[0]["status"], "RUNNING")
        self.assertEqual(repo.usage_for_build(build_id="b1"), [])

        restarted, _, _ = self.make_executor(provider, repo, store, worker_id="worker-b")
        summary = self.run_one(restarted, repo, req, now=106)
        self.assertEqual(summary.status, "VERIFIED")
        self.assertEqual(len(provider.submit_calls), 1)
        self.assertEqual(len(repo.usage_for_build(build_id="b1")), 1, "usage event must remain idempotent")

    def test_verified_payload_is_stored_and_unknown_actual_cost_stays_null(self):
        provider = FakeProvider()
        executor, repo, store = self.make_executor(provider)
        req = requirement()
        summary = self.run_one(executor, repo, req, project_id="tenant-project")
        self.assertEqual(summary.status, "VERIFIED")
        self.assertEqual(summary.artifacts[0].sha256, hashlib.sha256(PNG).hexdigest())
        self.assertIn("projects/tenant-project/", summary.artifacts[0].artifact_key)
        usage = repo.usage_for_build(build_id="b1")
        self.assertEqual(len(usage), 1)
        self.assertIsNone(usage[0]["actual_cost_usd"])
        self.assertEqual(usage[0]["maximum_cost_usd"], Decimal("0.20"))
        self.assertEqual(store.objects[summary.artifacts[0].artifact_key], PNG)

    def test_pre_materialized_artifact_is_not_trusted_without_storage_verification(self):
        store = MemoryStore()
        forged_key = "projects/p1/capabilities/b1/r-image/forged.png"
        store.objects[forged_key] = b"not-the-declared-bytes"
        declared = CapabilityArtifact(
            artifact_key=forged_key, mime_type="image/png",
            sha256=hashlib.sha256(PNG).hexdigest(), size_bytes=len(PNG),
            provider="media", capability_key="media.image.generate",
        )
        provider = FakeProvider(result_factory=lambda handle: ProviderExecutionResult(
            artifacts=(declared,), actual_cost_usd=Decimal("0.10"), usage={}, evidence={}, payloads=(),
        ))
        executor, repo, _ = self.make_executor(provider, store=store)
        req = requirement()
        with self.assertRaises(Exception):
            self.run_one(executor, repo, req)
        self.assertNotEqual(repo.requirements(build_id="b1")[0]["status"], "VERIFIED")

    def test_requirements_execute_in_dependency_order(self):
        provider = FakeProvider()
        executor, repo, _ = self.make_executor(provider)
        parent = requirement("parent")
        child = requirement("child", deps=("parent",))
        plan = CapabilityPlan((child, parent), ("target.web",))
        repo.create_plan(build_id="b1", plan=plan)
        summary = executor.execute_plan(
            build_id="b1", project_id="p1", plan=plan,
            assignments={
                "child": CapabilityExecutionAssignment("media", quote()),
                "parent": CapabilityExecutionAssignment("media", quote()),
            }, now=100,
        )
        self.assertEqual(summary.status, "VERIFIED")
        self.assertEqual([rid for rid, _ in provider.submit_calls], ["parent", "child"])

    def test_provider_terminal_failure_is_explicit_and_never_verified(self):
        provider = FakeProvider(terminal="FAILED")
        executor, repo, store = self.make_executor(provider)
        req = requirement()
        with self.assertRaisesRegex(CapabilityExecutionError, "FAILED"):
            self.run_one(executor, repo, req)
        self.assertEqual(store.objects, {})
        self.assertEqual(next(iter(repo.attempts.values())).status, "FAILED")
        self.assertEqual(repo.requirements(build_id="b1")[0]["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
