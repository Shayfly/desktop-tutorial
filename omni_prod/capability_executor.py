from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import hashlib
from typing import Mapping

from .artifact_keys import build_capability_artifact_key
from .capabilities import CapabilityPlan, CapabilityRequirement
from .capability_verification import (
    ArtifactVerificationError, verify_capability_artifact, verify_capability_artifact_stream,
)
from .provider_contracts import CapabilityArtifact, ProviderQuote, ProviderTaskHandle


class CapabilityExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class CapabilityExecutionAssignment:
    provider: str
    quote: ProviderQuote


@dataclass(frozen=True)
class CapabilityExecutionSummary:
    build_id: str
    status: str
    artifacts: tuple[CapabilityArtifact, ...]
    failed_requirements: tuple[str, ...]


def _topological_requirements(plan: CapabilityPlan) -> tuple[CapabilityRequirement, ...]:
    by_id = {r.id: r for r in plan.requirements}
    indegree = {r.id: 0 for r in plan.requirements}
    children: dict[str, list[str]] = {r.id: [] for r in plan.requirements}
    for requirement in plan.requirements:
        for dependency_id in requirement.dependency_ids:
            if dependency_id not in by_id:
                raise CapabilityExecutionError(
                    f"requirement {requirement.id} depends on missing {dependency_id}"
                )
            indegree[requirement.id] += 1
            children[dependency_id].append(requirement.id)
    ready = sorted(key for key, value in indegree.items() if value == 0)
    ordered: list[CapabilityRequirement] = []
    while ready:
        current = ready.pop(0)
        ordered.append(by_id[current])
        for child in sorted(children[current]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(ordered) != len(plan.requirements):
        raise CapabilityExecutionError("capability plan contains a dependency cycle")
    return tuple(ordered)


class CapabilityExecutor:
    def __init__(
        self,
        *,
        provider_registry,
        repository,
        artifact_store,
        worker_id: str,
        lease_seconds: int = 60,
        max_polls: int = 60,
        max_artifact_bytes: int = 512 * 1024 * 1024,
    ) -> None:
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        if lease_seconds < 1 or max_polls < 1 or max_artifact_bytes < 1:
            raise ValueError("lease_seconds, max_polls and max_artifact_bytes must be >= 1")
        self.provider_registry = provider_registry
        self.repository = repository
        self.artifact_store = artifact_store
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.max_polls = max_polls
        self.max_artifact_bytes = max_artifact_bytes

    @staticmethod
    def _idempotency_key(build_id: str, requirement: CapabilityRequirement, assignment: CapabilityExecutionAssignment) -> str:
        source = f"{build_id}\0{requirement.id}\0{assignment.provider}\0{assignment.quote.pricing_version}"
        return "cap_" + hashlib.sha256(source.encode("utf-8")).hexdigest()

    def _requirement_row(self, build_id: str, requirement_id: str) -> dict:
        rows = self.repository.requirements(build_id=build_id)
        for row in rows:
            if row["requirement_id"] == requirement_id:
                return row
        raise KeyError(f"capability requirement not found: {requirement_id}")

    def _transition_requirement(
        self,
        *,
        build_id: str,
        requirement_id: str,
        expected: str,
        target: str,
        **kwargs,
    ) -> bool:
        return self.repository.transition(
            build_id=build_id,
            requirement_id=requirement_id,
            expected=expected,
            target=target,
            **kwargs,
        )

    def _persist_payload(
        self,
        *,
        build_id: str,
        project_id: str,
        requirement: CapabilityRequirement,
        provider_name: str,
        payload,
    ) -> tuple[CapabilityArtifact, dict]:
        key = build_capability_artifact_key(
            project_id=project_id,
            build_id=build_id,
            requirement_id=requirement.id,
            filename=payload.filename,
        )
        digest = hashlib.sha256(payload.data).hexdigest()
        expected = CapabilityArtifact(
            artifact_key=key,
            mime_type=payload.mime_type,
            sha256=digest,
            size_bytes=len(payload.data),
            provider=provider_name,
            capability_key=requirement.key,
            metadata=dict(payload.metadata),
            provenance=dict(payload.provenance),
        )
        verification = verify_capability_artifact(
            expected,
            payload.data,
            max_size_bytes=self.max_artifact_bytes,
        )
        try:
            stored = self.artifact_store.put_bytes(key, payload.data)
            if getattr(stored, "sha256", digest) != digest or getattr(stored, "size", len(payload.data)) != len(payload.data):
                raise CapabilityExecutionError(f"artifact store integrity mismatch: {key}")
        except KeyError:
            # Retry after a crash may encounter an immutable object written by
            # the previous worker. Reuse only if the stored bytes verify.
            existing = self.artifact_store.get_bytes(key)
            if bytes(existing) != bytes(payload.data):
                raise CapabilityExecutionError(f"artifact key collision with different bytes: {key}")
        return expected, {
            "verified": verification.verified,
            "checks": list(verification.checks),
            "sha256": verification.sha256,
            "size_bytes": verification.size_bytes,
        }

    def _execute_one(
        self,
        *,
        build_id: str,
        project_id: str,
        requirement: CapabilityRequirement,
        assignment: CapabilityExecutionAssignment,
        now: float,
    ) -> tuple[CapabilityArtifact, ...]:
        if assignment.provider != assignment.quote.provider:
            raise CapabilityExecutionError("assignment provider/quote provider mismatch")
        if assignment.quote.capability_key != requirement.key:
            raise CapabilityExecutionError("assignment quote capability mismatch")

        provider = self.provider_registry.get(assignment.provider)
        idempotency_key = self._idempotency_key(build_id, requirement, assignment)
        attempt = self.repository.ensure_execution_attempt(
            attempt_id="att_" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:24],
            build_id=build_id,
            requirement_id=requirement.id,
            provider=assignment.provider,
            pricing_version=assignment.quote.pricing_version,
            idempotency_key=idempotency_key,
        )
        if attempt["status"] == "SUCCEEDED":
            return ()
        if attempt["status"] in {"FAILED", "CANCELLED"}:
            raise CapabilityExecutionError(
                f"provider attempt is terminal: {attempt['status']} for {requirement.id}"
            )
        if not self.repository.claim_execution_attempt(
            idempotency_key,
            worker_id=self.worker_id,
            now=now,
            lease_seconds=self.lease_seconds,
        ):
            raise CapabilityExecutionError(f"provider execution lease unavailable: {requirement.id}")

        attempt = self.repository.execution_attempt(idempotency_key)
        provider_task_id = attempt.get("provider_task_id")
        if provider_task_id is None:
            # The external submit MUST receive the same durable idempotency key
            # on every retry. A process death after this line but before the
            # handle write is therefore recoverable without duplicate spend for
            # providers truthfully marked durable-idempotent.
            if getattr(provider, "paid_external", False) and not getattr(provider, "durable_idempotency", False):
                raise CapabilityExecutionError("paid provider lacks durable idempotency")
            handle = provider.submit(requirement, idempotency_key=idempotency_key)
            if handle.idempotency_key != idempotency_key or handle.provider != assignment.provider:
                raise CapabilityExecutionError("provider returned inconsistent durable handle")
            self.repository.record_provider_handle(
                idempotency_key,
                provider_task_id=handle.provider_task_id,
                worker_id=self.worker_id,
            )
        else:
            handle = ProviderTaskHandle(
                provider=assignment.provider,
                provider_task_id=provider_task_id,
                capability_requirement_id=requirement.id,
                idempotency_key=idempotency_key,
            )

        current_status = self.repository.execution_attempt(idempotency_key)["status"]
        state = None
        for _ in range(self.max_polls):
            state = provider.poll(handle)
            if state.terminal:
                break
            if current_status == "SUBMITTED":
                self.repository.transition_execution_attempt(
                    idempotency_key,
                    expected="SUBMITTED",
                    target="RUNNING",
                    worker_id=self.worker_id,
                )
                current_status = "RUNNING"
        if state is None or not state.terminal:
            raise CapabilityExecutionError(f"provider task did not finish within poll budget: {requirement.id}")
        if state.status != "SUCCEEDED":
            current_status = self.repository.execution_attempt(idempotency_key)["status"]
            self.repository.transition_execution_attempt(
                idempotency_key,
                expected=current_status,
                target="FAILED" if state.status == "FAILED" else "CANCELLED",
                worker_id=self.worker_id,
            )
            raise CapabilityExecutionError(
                f"{state.error_code or state.status}: {state.error_message or 'provider execution failed'}"
            )

        result = provider.collect(handle)
        artifacts: list[CapabilityArtifact] = []
        verification_items: list[dict] = []
        try:
            # A provider-supplied CapabilityArtifact is evidence, not trust.
            # Verify the declared bytes from platform-owned storage before it
            # can contribute to a VERIFIED requirement.
            for artifact in result.artifacts:
                if artifact.provider != assignment.provider or artifact.capability_key != requirement.key:
                    raise CapabilityExecutionError("provider artifact identity mismatch")
                if hasattr(self.artifact_store, "iter_bytes"):
                    verification = verify_capability_artifact_stream(
                        artifact, self.artifact_store.iter_bytes(artifact.artifact_key),
                        max_size_bytes=self.max_artifact_bytes,
                    )
                else:
                    verification = verify_capability_artifact(
                        artifact, self.artifact_store.get_bytes(artifact.artifact_key),
                        max_size_bytes=self.max_artifact_bytes,
                    )
                artifacts.append(artifact)
                verification_items.append({
                    "verified": verification.verified, "checks": list(verification.checks),
                    "sha256": verification.sha256, "size_bytes": verification.size_bytes,
                })

            for payload in result.payloads:
                artifact, verification = self._persist_payload(
                    build_id=build_id, project_id=project_id, requirement=requirement,
                    provider_name=assignment.provider, payload=payload,
                )
                artifacts.append(artifact)
                verification_items.append(verification)
        except CapabilityExecutionError:
            raise
        except (ArtifactVerificationError, KeyError, OSError, ValueError) as exc:
            raise CapabilityExecutionError(f"artifact verification/storage failed: {exc}") from exc

        event = {
            "event_key": f"{build_id}:{requirement.id}:{assignment.provider}:collect:{assignment.quote.pricing_version}",
            "build_id": build_id, "requirement_id": requirement.id,
            "capability_key": requirement.key, "provider": assignment.provider,
            "provider_operation": "collect", "pricing_version": assignment.quote.pricing_version,
            "status": "SUCCEEDED",
            "estimated_cost_usd": assignment.quote.estimated_cost_usd,
            "maximum_cost_usd": assignment.quote.maximum_cost_usd,
            "actual_cost_usd": result.actual_cost_usd,
            "usage": dict(result.usage), "evidence": dict(result.evidence),
        }
        artifact_key = artifacts[0].artifact_key if artifacts else None
        verification_evidence = {
            "artifacts": verification_items,
            "provider_evidence": dict(result.evidence),
        }
        # The repository owns the atomic truth transition. In Postgres this
        # commits usage + requirement VERIFIED + attempt SUCCEEDED in one
        # transaction, eliminating the crash window between those writes.
        if not self.repository.finalize_execution_success(
            idempotency_key=idempotency_key, worker_id=self.worker_id,
            build_id=build_id, requirement_id=requirement.id, event=event,
            artifact_key=artifact_key, verification=verification_evidence,
            selected_provider=assignment.provider,
            pricing_version=assignment.quote.pricing_version,
        ):
            raise CapabilityExecutionError("atomic capability finalization failed")
        return tuple(artifacts)

    def execute_plan(
        self,
        *,
        build_id: str,
        project_id: str,
        plan: CapabilityPlan,
        assignments: Mapping[str, CapabilityExecutionAssignment],
        now: float,
    ) -> CapabilityExecutionSummary:
        artifacts: list[CapabilityArtifact] = []
        failed: list[str] = []

        for requirement in _topological_requirements(plan):
            row = self._requirement_row(build_id, requirement.id)
            if row["status"] == "VERIFIED":
                continue

            dependency_rows = {
                dep_id: self._requirement_row(build_id, dep_id)
                for dep_id in requirement.dependency_ids
            }
            broken_dependency = next(
                (dep_id for dep_id, dep in dependency_rows.items() if dep["status"] != "VERIFIED"),
                None,
            )
            if broken_dependency is not None:
                current = row["status"]
                self._transition_requirement(
                    build_id=build_id,
                    requirement_id=requirement.id,
                    expected=current,
                    target="BLOCKED",
                )
                failed.append(requirement.id)
                if requirement.required:
                    raise CapabilityExecutionError(
                        f"required dependency {broken_dependency} is not verified for {requirement.id}"
                    )
                continue

            assignment = assignments.get(requirement.id)
            if assignment is None:
                current = row["status"]
                self._transition_requirement(
                    build_id=build_id,
                    requirement_id=requirement.id,
                    expected=current,
                    target="BLOCKED" if requirement.required else "SKIPPED",
                )
                failed.append(requirement.id)
                if requirement.required:
                    raise CapabilityExecutionError(f"no provider assignment for required capability {requirement.key}")
                continue

            if row["status"] == "PLANNED":
                if not self._transition_requirement(
                    build_id=build_id,
                    requirement_id=requirement.id,
                    expected="PLANNED",
                    target="QUOTED",
                    selected_provider=assignment.provider,
                    pricing_version=assignment.quote.pricing_version,
                ):
                    raise CapabilityExecutionError("requirement quote CAS failed")
                row = self._requirement_row(build_id, requirement.id)
            if row["status"] == "QUOTED":
                if not self._transition_requirement(
                    build_id=build_id,
                    requirement_id=requirement.id,
                    expected="QUOTED",
                    target="RUNNING",
                    selected_provider=assignment.provider,
                    pricing_version=assignment.quote.pricing_version,
                ):
                    raise CapabilityExecutionError("requirement start CAS failed")
                row = self._requirement_row(build_id, requirement.id)
            if row["status"] not in {"RUNNING", "VERIFIED"}:
                raise CapabilityExecutionError(
                    f"requirement {requirement.id} cannot execute from {row['status']}"
                )

            try:
                artifacts.extend(self._execute_one(
                    build_id=build_id,
                    project_id=project_id,
                    requirement=requirement,
                    assignment=assignment,
                    now=now,
                ))
            except CapabilityExecutionError:
                row = self._requirement_row(build_id, requirement.id)
                if row["status"] == "RUNNING":
                    self._transition_requirement(
                        build_id=build_id,
                        requirement_id=requirement.id,
                        expected="RUNNING",
                        target="FAILED",
                    )
                failed.append(requirement.id)
                if requirement.required:
                    raise

        required_ids = {r.id for r in plan.requirements if r.required}
        rows = {r["requirement_id"]: r for r in self.repository.requirements(build_id=build_id)}
        if any(rows[rid]["status"] != "VERIFIED" for rid in required_ids):
            status = "FAILED"
        elif failed:
            status = "PARTIAL"
        else:
            status = "VERIFIED"
        return CapabilityExecutionSummary(build_id, status, tuple(artifacts), tuple(failed))
