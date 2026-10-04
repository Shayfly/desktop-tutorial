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
        return profile.key, tuple(merged)

    def quote(self, contract, *, project_id: str, environment) -> list[dict[str, Any]]:
        _, requirements = self.requirements_for(contract)
        return [self.provisioner.quote(r, project_id=project_id, environment=environment).to_dict()
                for r in requirements]

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
