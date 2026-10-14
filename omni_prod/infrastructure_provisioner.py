"""M5 Task 6: provisioning orchestration and the READY gate for build workers.

``InfrastructureProvisioningService`` turns a BuildContract's infrastructure
requirements into owned, durable bindings through an
``InfrastructureProvisioner`` adapter, then evaluates the READY gate.

* Idempotent: a LIVE binding with the same idempotency key is reused, never
  re-provisioned. NOT_CONFIGURED / BLOCKED / REVOKED records are retried with
  the *same* key, so a later configuration change heals without duplicates.
* Ownership: a binding belongs to one tenant/project/environment; another
  tenant can never adopt it.
* Fail closed: an adapter that cannot provision returns NOT_CONFIGURED or
  BLOCKED, and the gate reports the product as not ready.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from .build_contract import InfrastructureRequirement
from .infrastructure_contracts import (
    BindingStatus,
    InfrastructureBinding,
    InfrastructureEnvironment,
    InfrastructureGateResult,
    InfrastructureKind,
    InfrastructureQuote,
    deterministic_resource_name,
    evaluate_infrastructure_readiness,
    provisioning_idempotency_key,
)
from .infrastructure_registry import InfrastructureProfileRegistry, profile_for_contract


class InfrastructureStageBlocked(RuntimeError):
    """Raised when required generated-app infrastructure is not LIVE."""

    def __init__(self, message: str, *, evidence: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.evidence = dict(evidence or {})


class MemoryInfrastructureBindingRepository:
    """In-process binding store (tests / reviewer memory mode only; not durable)."""

    durable = False

    def __init__(self) -> None:
        self._by_key: dict[str, InfrastructureBinding] = {}

    def get_by_idempotency_key(self, idempotency_key: str) -> InfrastructureBinding | None:
        return self._by_key.get(idempotency_key)

    def get(self, binding_id: str) -> InfrastructureBinding:
        for binding in self._by_key.values():
            if binding.binding_id == binding_id:
                return binding
        raise KeyError(binding_id)

    def save(self, binding: InfrastructureBinding) -> InfrastructureBinding:
        existing = self._by_key.get(binding.idempotency_key)
        if existing is not None and existing.tenant_id != binding.tenant_id:
            raise PermissionError("infrastructure binding is owned by another tenant")
        self._by_key[binding.idempotency_key] = binding
        return binding

    def list_for(self, *, project_id: str, environment) -> tuple[InfrastructureBinding, ...]:
        env = InfrastructureEnvironment(environment) if not isinstance(environment, InfrastructureEnvironment) else environment
        return tuple(sorted(
            (b for b in self._by_key.values() if b.project_id == project_id and b.environment == env),
            key=lambda b: b.kind.value,
        ))


class PostgresInfrastructureBindingRepository:
    """Durable binding store (migration 021). Stores references, never secret values."""

    durable = True
    _COLUMNS = ("binding_id, idempotency_key, profile_key, tenant_id, project_id, environment, kind, status, "
                "resource_name, provisioner, secret_references, public_config, evidence, status_reason, "
                "created_at, revoked_at")

    def __init__(self, pool) -> None:
        self._pool = pool

    @staticmethod
    def _row_to_binding(row) -> InfrastructureBinding:
        (binding_id, idempotency_key, profile_key, tenant_id, project_id, environment, kind, status,
         resource_name, provisioner, secret_references, public_config, evidence, status_reason,
         created_at, revoked_at) = row

        def _json(value):
            if isinstance(value, (bytes, str)):
                import json as _j
                return _j.loads(value)
            return dict(value or {})

        def _iso(value):
            if value is None:
                return None
            return value.isoformat().replace("+00:00", "Z") if hasattr(value, "isoformat") else str(value)

        return InfrastructureBinding.from_record({
            "binding_id": binding_id, "idempotency_key": idempotency_key, "profile_key": profile_key,
            "tenant_id": tenant_id, "project_id": project_id, "environment": environment, "kind": kind,
            "status": status, "resource_name": resource_name, "provisioner": provisioner,
            "secret_references": _json(secret_references), "public_config": _json(public_config),
            "evidence": _json(evidence), "status_reason": status_reason,
            "created_at": _iso(created_at), "revoked_at": _iso(revoked_at),
        })

    def get_by_idempotency_key(self, idempotency_key: str) -> InfrastructureBinding | None:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT {self._COLUMNS} FROM generated_app_bindings WHERE idempotency_key=%s",
                            (idempotency_key,))
                row = cur.fetchone()
        return None if row is None else self._row_to_binding(row)

    def get(self, binding_id: str) -> InfrastructureBinding:
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT {self._COLUMNS} FROM generated_app_bindings WHERE binding_id=%s", (binding_id,))
                row = cur.fetchone()
        if row is None:
            raise KeyError(binding_id)
        return self._row_to_binding(row)

    def save(self, binding: InfrastructureBinding) -> InfrastructureBinding:
        import json as _j
        record = binding.to_record()
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT tenant_id FROM generated_app_bindings WHERE idempotency_key=%s FOR UPDATE",
                        (binding.idempotency_key,),
                    )
                    row = cur.fetchone()
                    if row is not None and row[0] != binding.tenant_id:
                        raise PermissionError("infrastructure binding is owned by another tenant")
                    cur.execute(
                        "INSERT INTO generated_app_bindings(binding_id, idempotency_key, profile_key, tenant_id, "
                        "project_id, environment, kind, status, resource_name, provisioner, secret_references, "
                        "public_config, evidence, status_reason, revoked_at) "
                        "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s) "
                        "ON CONFLICT (idempotency_key) DO UPDATE SET status=EXCLUDED.status, "
                        "resource_name=EXCLUDED.resource_name, provisioner=EXCLUDED.provisioner, "
                        "secret_references=EXCLUDED.secret_references, public_config=EXCLUDED.public_config, "
                        "evidence=EXCLUDED.evidence, status_reason=EXCLUDED.status_reason, "
                        "revoked_at=EXCLUDED.revoked_at",
                        (record["binding_id"], record["idempotency_key"], record["profile_key"],
                         record["tenant_id"], record["project_id"], record["environment"], record["kind"],
                         record["status"], record["resource_name"], record["provisioner"],
                         _j.dumps(record["secret_references"], sort_keys=True),
                         _j.dumps(record["public_config"], sort_keys=True, default=str),
                         _j.dumps(record["evidence"], sort_keys=True, default=str),
                         record["status_reason"], record["revoked_at"]),
                    )
        return binding

    def list_for(self, *, project_id: str, environment) -> tuple[InfrastructureBinding, ...]:
        env = environment.value if isinstance(environment, InfrastructureEnvironment) else str(environment)
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT {self._COLUMNS} FROM generated_app_bindings "
                    "WHERE project_id=%s AND environment=%s ORDER BY kind",
                    (project_id, env),
                )
                rows = cur.fetchall()
        return tuple(self._row_to_binding(row) for row in rows)


class UnconfiguredInfrastructureProvisioner:
    """Explicit NOT_CONFIGURED adapter used when no generated-app infrastructure exists.

    It never pretends a resource exists. Every provision() returns a
    NOT_CONFIGURED binding carrying the precise reason.
    """

    name = "unconfigured"
    profile_key = "managed_web_saas_v1"
    supported_kinds: tuple[InfrastructureKind, ...] = tuple(InfrastructureKind)

    def __init__(self, *, reason: str, status: BindingStatus = BindingStatus.NOT_CONFIGURED) -> None:
        if status not in {BindingStatus.NOT_CONFIGURED, BindingStatus.BLOCKED}:
            raise ValueError("unconfigured provisioner may only report NOT_CONFIGURED or BLOCKED")
        self.reason = reason
        self._status = status

    def quote(self, requirement, *, project_id, environment) -> InfrastructureQuote:
        return InfrastructureQuote(
            profile_key=self.profile_key, kind=requirement.kind, environment=environment,
            estimated_monthly_usd=None, maximum_monthly_usd=None, basis=f"{self._status.value}: {self.reason}",
        )

    def provision(self, requirement, *, tenant_id, project_id, environment, idempotency_key) -> InfrastructureBinding:
        kind = InfrastructureKind(requirement.kind)
        return InfrastructureBinding(
            binding_id="ib_" + idempotency_key[:24], profile_key=self.profile_key, tenant_id=tenant_id,
            project_id=project_id, environment=environment, kind=kind, status=self._status,
            resource_name=deterministic_resource_name(project_id=project_id, environment=environment, kind=kind),
            idempotency_key=idempotency_key, provisioner=self.name, status_reason=self.reason,
            evidence={"provisioned": False, "reason": self.reason},
        )

    def status(self, binding: InfrastructureBinding) -> InfrastructureBinding:
        return binding

    def revoke(self, binding: InfrastructureBinding) -> InfrastructureBinding:
        return binding.revoked(reason="revoked (nothing was provisioned)")

    def readiness(self) -> dict[str, str]:
        return {kind.value: self._status.value for kind in self.supported_kinds}


class InfrastructureProvisioningService:
    def __init__(self, *, provisioner, repository, registry: InfrastructureProfileRegistry | None = None) -> None:
        self.provisioner = provisioner
        self.repository = repository
        self.registry = registry

    # -- planning ---------------------------------------------------------
    def requirements_for(self, contract) -> tuple[str, tuple[InfrastructureRequirement, ...]]:
        """Requirements a provisioner must make LIVE. SELF_CONTAINED kinds
        (decision 2026-10-07 #27) are embedded in the generated app and are
        never provisioned, quoted or reported LIVE; see self_contained_evidence()."""
        profile = profile_for_contract(contract, self.registry)
        by_kind = {r.kind: r for r in contract.infrastructure}
        closure = profile.dependency_closure(tuple(by_kind))
        merged = []
        for kind in closure:
            if kind.value in by_kind:
                merged.append(by_kind[kind.value])
            else:
                # A dependency pulled in by the profile DAG inherits requiredness
                # from the profile, never silently becomes optional.
                merged.append(profile.requirement_for(kind))
        return profile.key, tuple(r for r in merged if getattr(r, "connection_mode", "") != "SELF_CONTAINED")

    def self_contained_evidence(self, contract) -> dict[str, Any] | None:
        """Truthful status of embedded and not-required kinds, or None when the
        contract requires every kind as platform-managed."""
        from .infrastructure_registry import INFRASTRUCTURE_KINDS
        embedded = [r.kind for r in contract.infrastructure
                    if getattr(r, "connection_mode", "") == "SELF_CONTAINED"]
        present = {r.kind for r in contract.infrastructure}
        not_required = [k for k in INFRASTRUCTURE_KINDS if k not in present]
        if not embedded and not not_required:
            return None
        return {
            "embedded": {k: "SELF_CONTAINED: not provisioned; verified only by the app's tests and preview acceptance"
                         for k in embedded},
            "not_required": {k: "NOT_REQUIRED" for k in not_required},
        }

    def quote(self, contract, *, project_id: str, environment) -> list[dict[str, Any]]:
        _, requirements = self.requirements_for(contract)
        return [self.provisioner.quote(r, project_id=project_id, environment=environment).to_dict()
                for r in requirements]

    def cost_quotes(self, contract, *, tenant_id: str, project_id: str, environment) -> list[InfrastructureQuote]:
        """Per-build provisioning quotes. A kind that already has an owned LIVE
        binding is reused and costs nothing to provision again."""
        env = InfrastructureEnvironment(environment) if not isinstance(environment, InfrastructureEnvironment) else environment
        profile_key, requirements = self.requirements_for(contract)
        quotes = []
        for requirement in requirements:
            kind = InfrastructureKind(requirement.kind)
            key = provisioning_idempotency_key(profile_key=profile_key, project_id=project_id, environment=env, kind=kind)
            existing = self.repository.get_by_idempotency_key(key)
            if existing is not None and existing.live and existing.tenant_id == tenant_id:
                quotes.append(InfrastructureQuote(
                    profile_key=profile_key, kind=kind, environment=env, estimated_monthly_usd=None,
                    maximum_monthly_usd=None, basis="reuse existing LIVE binding",
                    provisioning_estimated_usd=Decimal("0"), provisioning_maximum_usd=Decimal("0")))
            else:
                quotes.append(self.provisioner.quote(requirement, project_id=project_id, environment=env))
        return quotes

    # -- provisioning -----------------------------------------------------
    def _provision_one(self, requirement, *, profile_key, tenant_id, project_id, environment) -> InfrastructureBinding:
        kind = InfrastructureKind(requirement.kind)
        key = provisioning_idempotency_key(
            profile_key=profile_key, project_id=project_id, environment=environment, kind=kind)
        existing = self.repository.get_by_idempotency_key(key)
        if existing is not None and existing.tenant_id != tenant_id:
            raise PermissionError("infrastructure binding is owned by another tenant")
        if existing is not None and existing.live:
            return existing
        if kind not in tuple(self.provisioner.supported_kinds):
            binding = UnconfiguredInfrastructureProvisioner(
                reason=f"provisioner {self.provisioner.name} does not support {kind.value}",
            ).provision(requirement, tenant_id=tenant_id, project_id=project_id,
                        environment=environment, idempotency_key=key)
        else:
            binding = self.provisioner.provision(
                requirement, tenant_id=tenant_id, project_id=project_id,
                environment=environment, idempotency_key=key)
        if (binding.idempotency_key != key or binding.project_id != project_id
                or binding.tenant_id != tenant_id or binding.kind != kind
                or binding.environment.value != InfrastructureEnvironment(environment).value):
            raise RuntimeError("provisioner returned a binding with inconsistent identity")
        return self.repository.save(binding)

    def ensure(self, contract, *, tenant_id: str, project_id: str, environment) -> InfrastructureGateResult:
        env = InfrastructureEnvironment(environment) if not isinstance(environment, InfrastructureEnvironment) else environment
        profile_key, requirements = self.requirements_for(contract)
        for requirement in requirements:
            self._provision_one(requirement, profile_key=profile_key, tenant_id=tenant_id,
                                project_id=project_id, environment=env)
        return evaluate_infrastructure_readiness(
            requirements, self.repository.list_for(project_id=project_id, environment=env),
            project_id=project_id, environment=env, profile_key=profile_key, tenant_id=tenant_id,
        )

    def require_ready(self, contract, *, tenant_id: str, project_id: str, environment) -> dict[str, Any]:
        result = self.ensure(contract, tenant_id=tenant_id, project_id=project_id, environment=environment)
        evidence = result.to_dict()
        self_contained = self.self_contained_evidence(contract)
        if self_contained is not None:
            evidence["self_contained"] = self_contained
        if not result.ready:
            parts = []
            if result.missing_kinds:
                parts.append("missing " + ", ".join(k.value for k in result.missing_kinds))
            if result.not_live:
                parts.append(", ".join(f"{k.value}={v}" for k, v in result.not_live.items()))
            if result.ownership_violations:
                parts.append(f"{len(result.ownership_violations)} ownership violation(s)")
            raise InfrastructureStageBlocked(
                "required generated-app infrastructure is not LIVE: " + "; ".join(parts), evidence=evidence)
        return evidence

    def revoke_all(self, *, project_id: str, environment) -> tuple[InfrastructureBinding, ...]:
        revoked = []
        for binding in self.repository.list_for(project_id=project_id, environment=environment):
            if binding.status == BindingStatus.REVOKED:
                continue
            updated = self.provisioner.revoke(binding)
            if updated.status != BindingStatus.REVOKED:
                raise RuntimeError(f"provisioner did not revoke {binding.binding_id}")
            revoked.append(self.repository.save(updated))
        return tuple(revoked)

    def readiness(self) -> dict[str, str]:
        return dict(self.provisioner.readiness())


def bindings_by_kind(bindings: Iterable[InfrastructureBinding]) -> dict[str, dict[str, Any]]:
    return {b.kind.value: b.to_public_dict() for b in bindings}
