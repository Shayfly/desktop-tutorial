from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import uuid
from typing import Any, Mapping

from .capabilities import CapabilityPlan


class AttemptLeaseConflict(RuntimeError):
    pass


class InvalidAttemptTransition(RuntimeError):
    pass


@dataclass(frozen=True)
class CapabilityRequirementRecord:
    build_id: str
    requirement_id: str
    capability_key: str
    purpose: str
    required: bool
    quantity: int
    constraints: Mapping[str, Any]
    dependency_ids: tuple[str, ...]
    status: str = "PENDING"
    selected_provider: str | None = None
    artifact_key: str | None = None
    verification: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ProviderExecutionAttempt:
    id: str
    build_id: str
    requirement_id: str
    provider: str
    idempotency_key: str
    provider_task_id: str | None
    status: str
    lease_owner: str
    lease_expires_at: float
    last_error_code: str | None = None
    last_error_message: str | None = None


@dataclass(frozen=True)
class ProviderUsageEvent:
    event_key: str
    build_id: str
    requirement_id: str
    provider: str
    pricing_version: str
    estimated_cost_usd: Decimal
    maximum_cost_usd: Decimal
    actual_cost_usd: Decimal | None
    usage: Mapping[str, Any]
    evidence: Mapping[str, Any]


_ATTEMPT_TRANSITIONS: dict[str, frozenset[str]] = {
    "LEASED": frozenset({"SUBMITTED", "FAILED", "CANCELLED"}),
    "SUBMITTED": frozenset({"RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"}),
    "RUNNING": frozenset({"SUCCEEDED", "FAILED", "CANCELLED"}),
    "SUCCEEDED": frozenset(),
    "FAILED": frozenset(),
    "CANCELLED": frozenset(),
}


def _assert_transition(expected: str, target: str) -> None:
    if target not in _ATTEMPT_TRANSITIONS.get(expected, frozenset()):
        raise InvalidAttemptTransition(f"invalid provider attempt transition {expected}->{target}")


class MemoryCapabilityRepository:
    """Reference implementation of durable capability semantics.

    The public methods intentionally mirror the durable repository contract so
    crash/retry/idempotency behavior can be proven without a live Postgres
    dependency. No secret values are stored here or in the SQL schema.
    """

    TERMINAL_EXECUTION = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})

    def __init__(self) -> None:
        self._plans: dict[str, dict[str, Any]] = {}
        self._requirements: dict[tuple[str, str], dict[str, Any]] = {}
        self._attempts: dict[str, dict[str, Any]] = {}
        self._usage: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _plan_payload(plan: CapabilityPlan) -> dict[str, Any]:
        return plan.to_dict()

    def create_plan(self, *, build_id: str, plan: CapabilityPlan) -> None:
        payload = self._plan_payload(plan)
        existing = self._plans.get(build_id)
        if existing is not None:
            if existing != payload:
                raise ValueError(f"plan drift for build {build_id}")
            return
        self._plans[build_id] = payload
        for requirement in plan.requirements:
            self._requirements[(build_id, requirement.id)] = {
                "build_id": build_id,
                "requirement_id": requirement.id,
                "capability_key": requirement.key,
                "purpose": requirement.purpose,
                "required": requirement.required,
                "quantity": requirement.quantity,
                "constraints": dict(requirement.constraints),
                "dependency_ids": tuple(requirement.dependency_ids),
                "status": "PLANNED",
                "selected_provider": None,
                "pricing_version": None,
                "artifact_key": None,
                "verification": {},
            }

    # V2 canonical name. Keep save_plan as an adapter for executor code.
    def save_plan(self, build_id: str, plan: CapabilityPlan) -> None:
        self.create_plan(build_id=build_id, plan=plan)

    def requirements(self, *, build_id: str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for (bid, _), row in sorted(self._requirements.items())
            if bid == build_id
        ]

    def list_requirements(self, build_id: str) -> list[CapabilityRequirementRecord]:
        return [
            CapabilityRequirementRecord(
                build_id=row["build_id"], requirement_id=row["requirement_id"],
                capability_key=row["capability_key"], purpose=row["purpose"],
                required=row["required"], quantity=row["quantity"],
                constraints=dict(row["constraints"]), dependency_ids=tuple(row["dependency_ids"]),
                status=row["status"], selected_provider=row["selected_provider"],
                artifact_key=row["artifact_key"], verification=dict(row["verification"]),
            )
            for row in self.requirements(build_id=build_id)
        ]

    def transition(
        self, *, build_id: str, requirement_id: str, expected: str, target: str,
        selected_provider: str | None = None, pricing_version: str | None = None,
        artifact_key: str | None = None, verification: Mapping[str, Any] | None = None,
    ) -> bool:
        key = (build_id, requirement_id)
        row = self._requirements.get(key)
        if row is None:
            raise KeyError("capability requirement not found")
        if row["status"] != expected:
            return False
        row["status"] = target
        if selected_provider is not None:
            row["selected_provider"] = selected_provider
        if pricing_version is not None:
            row["pricing_version"] = pricing_version
        if artifact_key is not None:
            row["artifact_key"] = artifact_key
        if verification is not None:
            row["verification"] = dict(verification)
        return True

    def record_usage(self, *, event: Mapping[str, Any]) -> dict[str, Any]:
        event_key = str(event.get("event_key", "")).strip()
        if not event_key:
            raise ValueError("usage event_key must not be empty")
        existing = self._usage.get(event_key)
        payload = dict(event)
        if existing is not None:
            if existing != payload:
                raise ValueError("usage event idempotency conflict")
            return dict(existing)
        # Unknown actual cost stays None; never replace it with an estimate.
        if payload.get("actual_cost_usd") is not None and Decimal(str(payload["actual_cost_usd"])) < 0:
            raise ValueError("actual cost must be >= 0 when known")
        self._usage[event_key] = payload
        return dict(payload)

    def usage_for_build(self, *, build_id: str) -> list[dict[str, Any]]:
        return [dict(e) for e in self._usage.values() if e.get("build_id") == build_id]

    def ensure_execution_attempt(
        self, *, attempt_id: str, build_id: str, requirement_id: str,
        provider: str, pricing_version: str, idempotency_key: str,
    ) -> dict[str, Any]:
        existing = self._attempts.get(idempotency_key)
        if existing is not None:
            identity = (existing["build_id"], existing["requirement_id"], existing["provider"], existing["pricing_version"])
            requested = (build_id, requirement_id, provider, pricing_version)
            if identity != requested:
                raise ValueError("execution idempotency key identity conflict")
            return dict(existing)
        if (build_id, requirement_id) not in self._requirements:
            raise KeyError("capability requirement not found")
        row = {
            "attempt_id": attempt_id,
            "build_id": build_id,
            "requirement_id": requirement_id,
            "provider": provider,
            "pricing_version": pricing_version,
            "idempotency_key": idempotency_key,
            "provider_task_id": None,
            "status": "SUBMITTING",
            "lease_owner": None,
            "lease_expires_at": 0.0,
        }
        self._attempts[idempotency_key] = row
        return dict(row)

    def claim_execution_attempt(self, idempotency_key: str, *, worker_id: str, now: float, lease_seconds: int) -> bool:
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be >= 1")
        row = self._attempts.get(idempotency_key)
        if row is None:
            raise KeyError("provider execution attempt not found")
        if row["status"] in self.TERMINAL_EXECUTION:
            return False
        owner = row.get("lease_owner")
        expires = float(row.get("lease_expires_at") or 0)
        if owner not in {None, worker_id} and now < expires:
            return False
        row["lease_owner"] = worker_id
        row["lease_expires_at"] = now + lease_seconds
        return True

    def record_provider_handle(self, idempotency_key: str, *, provider_task_id: str) -> bool:
        row = self._attempts.get(idempotency_key)
        if row is None:
            raise KeyError("provider execution attempt not found")
        current = row.get("provider_task_id")
        if current is not None and current != provider_task_id:
            raise ValueError("provider task identity conflict")
        row["provider_task_id"] = provider_task_id
        if row["status"] == "SUBMITTING":
            row["status"] = "SUBMITTED"
        return True

    def execution_attempt(self, idempotency_key: str) -> dict[str, Any]:
        row = self._attempts.get(idempotency_key)
        if row is None:
            raise KeyError("provider execution attempt not found")
        return dict(row)

    def transition_execution_attempt(self, idempotency_key: str, *, expected: str, target: str) -> bool:
        row = self._attempts.get(idempotency_key)
        if row is None:
            raise KeyError("provider execution attempt not found")
        if row["status"] != expected:
            return False
        row["status"] = target
        return True

    # Compatibility helpers used by the executor implementation.
    @property
    def attempts(self) -> dict[str, ProviderExecutionAttempt]:
        return {
            row["attempt_id"]: ProviderExecutionAttempt(
                id=row["attempt_id"], build_id=row["build_id"], requirement_id=row["requirement_id"],
                provider=row["provider"], idempotency_key=row["idempotency_key"],
                provider_task_id=row["provider_task_id"], status=row["status"],
                lease_owner=row.get("lease_owner") or "", lease_expires_at=float(row.get("lease_expires_at") or 0),
            )
            for row in self._attempts.values()
        }

    @property
    def usage_events(self) -> dict[str, ProviderUsageEvent]:
        result = {}
        for key, row in self._usage.items():
            result[key] = ProviderUsageEvent(
                event_key=key, build_id=str(row.get("build_id", "")),
                requirement_id=str(row.get("requirement_id", "")), provider=str(row.get("provider", "")),
                pricing_version=str(row.get("pricing_version", "")),
                estimated_cost_usd=Decimal(str(row.get("estimated_cost_usd", 0))),
                maximum_cost_usd=Decimal(str(row.get("maximum_cost_usd", row.get("estimated_cost_usd", 0)))),
                actual_cost_usd=(None if row.get("actual_cost_usd") is None else Decimal(str(row["actual_cost_usd"]))),
                usage=dict(row.get("usage", {})), evidence=dict(row.get("evidence", {})),
            )
        return result


class PostgresCapabilityRepository:
    """PostgreSQL implementation of the M4.95 capability state machine."""

    def __init__(self, pool) -> None:
        self.pool = pool

    def save_plan(self, build_id: str, plan: CapabilityPlan) -> None:
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    for requirement in plan.requirements:
                        cur.execute(
                            """
                            INSERT INTO build_capability_requirements(
                                build_id, requirement_id, capability_key, purpose,
                                required, quantity, constraints_json, dependency_ids_json
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                            ON CONFLICT (build_id, requirement_id) DO NOTHING
                            """,
                            (
                                build_id, requirement.id, requirement.key, requirement.purpose,
                                requirement.required, requirement.quantity,
                                json.dumps(dict(requirement.constraints)),
                                json.dumps(list(requirement.dependency_ids)),
                            ),
                        )

    def list_requirements(self, build_id: str) -> list[CapabilityRequirementRecord]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT requirement_id, capability_key, purpose, required, quantity,
                           constraints_json, dependency_ids_json, status, selected_provider,
                           artifact_key, verification_json
                    FROM build_capability_requirements
                    WHERE build_id=%s ORDER BY requirement_id
                    """,
                    (build_id,),
                )
                rows = cur.fetchall()
        result = []
        for row in rows:
            constraints = json.loads(row[5]) if isinstance(row[5], str) else (row[5] or {})
            dependencies = json.loads(row[6]) if isinstance(row[6], str) else (row[6] or [])
            verification = json.loads(row[10]) if isinstance(row[10], str) else (row[10] or {})
            result.append(CapabilityRequirementRecord(
                build_id=build_id, requirement_id=row[0], capability_key=row[1], purpose=row[2],
                required=row[3], quantity=row[4], constraints=constraints,
                dependency_ids=tuple(dependencies), status=row[7], selected_provider=row[8],
                artifact_key=row[9], verification=verification,
            ))
        return result

    @staticmethod
    def _row_to_attempt(row) -> ProviderExecutionAttempt:
        expires = row[8]
        if hasattr(expires, "timestamp"):
            expires = expires.timestamp()
        return ProviderExecutionAttempt(
            id=row[0], build_id=row[1], requirement_id=row[2], provider=row[3],
            idempotency_key=row[4], provider_task_id=row[5], status=row[6],
            lease_owner=row[7], lease_expires_at=float(expires),
            last_error_code=row[9], last_error_message=row[10],
        )

    def acquire_attempt(
        self, *, build_id: str, requirement_id: str, provider: str,
        idempotency_key: str, lease_owner: str, now: float,
        lease_seconds: int,
    ) -> ProviderExecutionAttempt:
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be >= 1")
        now_dt = datetime.fromtimestamp(now, timezone.utc)
        expires = now_dt + timedelta(seconds=lease_seconds)
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, build_id, requirement_id, provider, idempotency_key,
                               provider_task_id, status, lease_owner, lease_expires_at,
                               last_error_code, last_error_message
                        FROM provider_execution_attempts
                        WHERE idempotency_key=%s FOR UPDATE
                        """,
                        (idempotency_key,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        attempt_id = f"pex_{uuid.uuid4().hex}"
                        cur.execute(
                            """
                            INSERT INTO provider_execution_attempts(
                                id, build_id, requirement_id, provider, idempotency_key,
                                status, lease_owner, lease_expires_at
                            ) VALUES (%s,%s,%s,%s,%s,'LEASED',%s,%s)
                            """,
                            (attempt_id, build_id, requirement_id, provider, idempotency_key, lease_owner, expires),
                        )
                        return ProviderExecutionAttempt(
                            attempt_id, build_id, requirement_id, provider, idempotency_key,
                            None, "LEASED", lease_owner, expires.timestamp(),
                        )
                    attempt = self._row_to_attempt(row)
                    if (attempt.build_id, attempt.requirement_id, attempt.provider) != (build_id, requirement_id, provider):
                        raise ValueError("idempotency key already belongs to a different execution")
                    if attempt.lease_owner != lease_owner and now < attempt.lease_expires_at:
                        raise AttemptLeaseConflict("provider execution attempt has an active lease")
                    cur.execute(
                        "UPDATE provider_execution_attempts SET lease_owner=%s, lease_expires_at=%s, updated_at=now() WHERE id=%s",
                        (lease_owner, expires, attempt.id),
                    )
                    return replace(attempt, lease_owner=lease_owner, lease_expires_at=expires.timestamp())

    def record_provider_task_id(self, attempt_id: str, provider_task_id: str, *, lease_owner: str) -> None:
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT provider_task_id, lease_owner FROM provider_execution_attempts WHERE id=%s FOR UPDATE",
                        (attempt_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise KeyError("provider execution attempt not found")
                    if row[1] != lease_owner:
                        raise AttemptLeaseConflict("lease owner mismatch")
                    if row[0] is not None and row[0] != provider_task_id:
                        raise ValueError("provider_task_id is immutable once recorded")
                    cur.execute(
                        "UPDATE provider_execution_attempts SET provider_task_id=%s, updated_at=now() WHERE id=%s",
                        (provider_task_id, attempt_id),
                    )

    def transition_attempt(self, attempt_id: str, *, expected: str, target: str, lease_owner: str) -> None:
        _assert_transition(expected, target)
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE provider_execution_attempts SET status=%s, updated_at=now()
                        WHERE id=%s AND status=%s AND lease_owner=%s
                        """,
                        (target, attempt_id, expected, lease_owner),
                    )
                    if cur.rowcount != 1:
                        raise InvalidAttemptTransition("provider attempt compare-and-swap failed")

    def record_usage_event(
        self, *, event_key: str, build_id: str, requirement_id: str, provider: str,
        pricing_version: str, estimated_cost_usd: Decimal, maximum_cost_usd: Decimal,
        actual_cost_usd: Decimal | None, usage: Mapping[str, Any],
        evidence: Mapping[str, Any] | None = None,
    ) -> bool:
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO provider_usage_events(
                            event_key, build_id, requirement_id, provider, pricing_version,
                            estimated_cost_usd, maximum_cost_usd, actual_cost_usd,
                            usage_json, evidence_json
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                        ON CONFLICT (event_key) DO NOTHING
                        """,
                        (
                            event_key, build_id, requirement_id, provider, pricing_version,
                            estimated_cost_usd, maximum_cost_usd, actual_cost_usd,
                            json.dumps(dict(usage)), json.dumps(dict(evidence or {})),
                        ),
                    )
                    return cur.rowcount == 1
