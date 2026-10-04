import hashlib
import unittest
from decimal import Decimal

from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.capability_repository import MemoryCapabilityRepository
from omni_prod.provider_contracts import (
    ProviderArtifactPayload,
    ProviderCapability,
    ProviderExecutionResult,
    ProviderQuote,
    ProviderTaskHandle,
    ProviderTaskState,
)
from omni_prod.provider_registry import ProviderRegistry
from omni_prod.storage import StoredObject

try:
    from omni_prod.capability_executor import (
        CapabilityExecutionAssignment,
        CapabilityExecutionError,
        CapabilityExecutor,
    )
except ImportError:
    CapabilityExecutionAssignment = CapabilityExecutionError = CapabilityExecutor = None


PNG = b"\x89PNG\r\n\x1a\n" + b"artifact-bytes"


def requirement(rid="r-image", *, deps=()):
    return CapabilityRequirement(
        rid, "media.image.generate", "hero image", True,
        constraints={"prompt": "hero"}, dependency_ids=tuple(deps),
    )


def quote(provider="media", rid="r-image", maximum="0.20"):
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


class FakeProvider:
    name = "media"
    durable_idempotency = True
    paid_external = True

    def __init__(self, *, fail_first_poll=False, terminal="SUCCEEDED"):
        self.submit_calls = []
        self.poll_calls = []
        self.collect_calls = []
        self.fail_first_poll = fail_first_poll
        self.terminal = terminal
        self._handles = {}

    def capabilities(self):
        return (ProviderCapability("media.image.generate", ("image/png",), True),)
    def health(self):
        return "HEALTHY"
    def quote(self, requirement):
        return quote(self.name, requirement.id)
    def submit(self, req, *, idempotency_key):
        self.submit_calls.append((req.id, idempotency_key))
        handle = ProviderTaskHandle(self.name, f"task-{req.id}", req.id, idempotency_key)
        self._handles[handle.provider_task_id] = handle
        return handle
    def poll(self, handle):
        self.poll_calls.append(handle.provider_task_id)
        if self.fail_first_poll:
            self.fail_first_poll = False
            raise RuntimeError("simulated worker/process interruption after durable submit")
        return ProviderTaskState(self.terminal, 1.0 if self.terminal == "SUCCEEDED" else None)
    def collect(self, handle):
        self.collect_calls.append(handle.provider_task_id)
        return ProviderExecutionResult(
            artifacts=(), actual_cost_usd=None,
            usage={"images": 1}, evidence={"provider_request": handle.provider_task_id},
            payloads=(ProviderArtifactPayload("image/png", PNG, filename="hero.png"),),
        )
    def cancel(self, handle):
        return None


class CapabilityExecutorTests(unittest.TestCase):
    def make_executor(self, provider, repo=None, store=None):
        repo = repo or MemoryCapabilityRepository()
        store = store or MemoryStore()
        return CapabilityExecutor(
            providers=ProviderRegistry((provider,)), repository=repo,
            artifact_store=store, poll_interval_seconds=0,
        ), repo, store

    def test_budget_ceiling_blocks_before_attempt_or_provider_submit(self):
        provider = FakeProvider()
        executor, repo, _ = self.make_executor(provider)
        req = requirement()
        plan = CapabilityPlan((req,), ("target.web",))
        repo.create_plan(build_id="b1", plan=plan)
        assignment = CapabilityExecutionAssignment(req, "media", quote(maximum="0.20"))
        with self.assertRaisesRegex(CapabilityExecutionError, "authorized"):
            executor.execute(
                build_id="b1", project_id="p1", assignments=(assignment,),
                authorized_maximum_usd=Decimal("0.19"), worker_id="w1", now=100,
            )
        self.assertEqual(provider.submit_calls, [])
        self.assertEqual(repo.attempts, {})

    def test_restart_resumes_persisted_provider_task_without_duplicate_submit(self):
        provider = FakeProvider(fail_first_poll=True)
        repo = MemoryCapabilityRepository()
        store = MemoryStore()
        req = requirement()
        repo.create_plan(build_id="b1", plan=CapabilityPlan((req,), ("target.web",)))
        assignment = CapabilityExecutionAssignment(req, "media", quote())

        first = CapabilityExecutor(
            providers=ProviderRegistry((provider,)), repository=repo,
            artifact_store=store, poll_interval_seconds=0, lease_seconds=5,
        )
        with self.assertRaisesRegex(RuntimeError, "interruption"):
            first.execute(
                build_id="b1", project_id="p1", assignments=(assignment,),
                authorized_maximum_usd=Decimal("1"), worker_id="worker-a", now=100,
            )
        persisted = repo.execution_attempt("b1:r-image:media:price-v1")
        self.assertEqual(persisted["provider_task_id"], "task-r-image")
        self.assertEqual(persisted["status"], "SUBMITTED")
        self.assertEqual(len(provider.submit_calls), 1)

        restarted = CapabilityExecutor(
            providers=ProviderRegistry((provider,)), repository=repo,
            artifact_store=store, poll_interval_seconds=0, lease_seconds=5,
        )
        results = restarted.execute(
            build_id="b1", project_id="p1", assignments=(assignment,),
            authorized_maximum_usd=Decimal("1"), worker_id="worker-b", now=106,
        )
        self.assertEqual(len(provider.submit_calls), 1, "restart must reuse durable provider_task_id")
        self.assertEqual(results[0].status, "VERIFIED")
        self.assertEqual(len(store.objects), 1)
        self.assertEqual(repo.execution_attempt("b1:r-image:media:price-v1")["status"], "SUCCEEDED")

    def test_verified_artifact_and_usage_preserve_unknown_actual_cost(self):
        provider = FakeProvider()
        executor, repo, store = self.make_executor(provider)
        req = requirement()
        repo.create_plan(build_id="b1", plan=CapabilityPlan((req,), ("target.web",)))
        result = executor.execute(
            build_id="b1", project_id="tenant-project",
            assignments=(CapabilityExecutionAssignment(req, "media", quote()),),
            authorized_maximum_usd=Decimal("1"), worker_id="w1", now=100,
        )[0]
        self.assertEqual(result.status, "VERIFIED")
        self.assertEqual(result.artifacts[0].sha256, hashlib.sha256(PNG).hexdigest())
        self.assertIn("projects/tenant-project/", result.artifacts[0].artifact_key)
        usage = repo.usage_for_build(build_id="b1")
        self.assertEqual(len(usage), 1)
        self.assertIsNone(usage[0]["actual_cost_usd"])
        self.assertEqual(usage[0]["maximum_cost_usd"], Decimal("0.20"))
        self.assertEqual(store.objects[result.artifacts[0].artifact_key], PNG)

    def test_assignments_execute_in_dependency_order_not_input_order(self):
        provider = FakeProvider()
        executor, repo, _ = self.make_executor(provider)
        parent = requirement("parent")
        child = requirement("child", deps=("parent",))
        repo.create_plan(build_id="b1", plan=CapabilityPlan((parent, child), ("target.web",)))
        assignments = (
            CapabilityExecutionAssignment(child, "media", quote(rid="child")),
            CapabilityExecutionAssignment(parent, "media", quote(rid="parent")),
        )
        executor.execute(
            build_id="b1", project_id="p1", assignments=assignments,
            authorized_maximum_usd=Decimal("1"), worker_id="w1", now=100,
        )
        self.assertEqual([rid for rid, _ in provider.submit_calls], ["parent", "child"])

    def test_provider_terminal_failure_is_explicit_and_never_verified(self):
        provider = FakeProvider(terminal="FAILED")
        executor, repo, store = self.make_executor(provider)
        req = requirement()
        repo.create_plan(build_id="b1", plan=CapabilityPlan((req,), ("target.web",)))
        with self.assertRaisesRegex(CapabilityExecutionError, "FAILED"):
            executor.execute(
                build_id="b1", project_id="p1",
                assignments=(CapabilityExecutionAssignment(req, "media", quote()),),
                authorized_maximum_usd=Decimal("1"), worker_id="w1", now=100,
            )
        self.assertEqual(store.objects, {})
        self.assertEqual(repo.execution_attempt("b1:r-image:media:price-v1")["status"], "FAILED")
        status = {r["requirement_id"]: r["status"] for r in repo.requirements(build_id="b1")}
        self.assertEqual(status["r-image"], "FAILED")


if __name__ == "__main__":
    unittest.main()
