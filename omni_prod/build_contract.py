from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping

from .capabilities import CapabilityPlan, CapabilityRequirement
from .product_spec import AcceptanceCriterion, ProductSpec


def _canonical_json(data: Mapping[str, Any] | dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_fingerprint(data: Mapping[str, Any] | dict[str, Any]) -> str:
    return "sha256:" + sha256(_canonical_json(data).encode("utf-8")).hexdigest()


class BuildContractStatus(str, Enum):
    READY = "READY"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ClarificationQuestion:
    id: str
    question: str
    reason: str
    material: bool = True
    answer_options: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.question.strip() or not self.reason.strip():
            raise ValueError("clarification id/question/reason are required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "reason": self.reason,
            "material": self.material,
            "answer_options": list(self.answer_options),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ClarificationQuestion":
        return cls(
            id=str(data["id"]),
            question=str(data["question"]),
            reason=str(data["reason"]),
            material=bool(data.get("material", True)),
            answer_options=tuple(str(x) for x in data.get("answer_options", ())),
        )


@dataclass(frozen=True)
class InfrastructureRequirement:
    kind: str
    purpose: str
    required: bool = True
    connection_mode: str = "PLATFORM_MANAGED"
    environment_scope: str = "preview_and_production"
    secret_reference_only: bool = True

    def __post_init__(self) -> None:
        if not self.kind.strip() or not self.purpose.strip():
            raise ValueError("infrastructure kind/purpose are required")
        # SELF_CONTAINED (decision 2026-10-07 #27): embedded in the generated app,
        # never provisioned; verified only by the app's tests and preview acceptance.
        if self.connection_mode not in {"PLATFORM_MANAGED", "CUSTOMER_CONNECTED", "BYOK", "SELF_CONTAINED"}:
            raise ValueError(f"unsupported infrastructure connection mode: {self.connection_mode}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "purpose": self.purpose,
            "required": self.required,
            "connection_mode": self.connection_mode,
            "environment_scope": self.environment_scope,
            "secret_reference_only": self.secret_reference_only,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InfrastructureRequirement":
        return cls(
            kind=str(data["kind"]),
            purpose=str(data["purpose"]),
            required=bool(data.get("required", True)),
            connection_mode=str(data.get("connection_mode", "PLATFORM_MANAGED")),
            environment_scope=str(data.get("environment_scope", "preview_and_production")),
            secret_reference_only=bool(data.get("secret_reference_only", True)),
        )


@dataclass(frozen=True)
class CostEnvelopeReference:
    pricing_catalog_version: str
    quote_basis: str = "CONSERVATIVE_MAXIMUM"
    reservation_required: bool = True
    authorization_policy: str = "M5-T10"
    actual_cost_policy: str = "PROVIDER_REPORTED_OR_UNKNOWN"

    def __post_init__(self) -> None:
        if not self.pricing_catalog_version.strip():
            raise ValueError("pricing catalog version is required")
        if self.quote_basis != "CONSERVATIVE_MAXIMUM":
            raise ValueError("M5 build contracts require conservative maximum quote basis")

    def to_dict(self) -> dict[str, Any]:
        return {
            "pricing_catalog_version": self.pricing_catalog_version,
            "quote_basis": self.quote_basis,
            "reservation_required": self.reservation_required,
            "authorization_policy": self.authorization_policy,
            "actual_cost_policy": self.actual_cost_policy,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CostEnvelopeReference":
        return cls(
            pricing_catalog_version=str(data["pricing_catalog_version"]),
            quote_basis=str(data.get("quote_basis", "CONSERVATIVE_MAXIMUM")),
            reservation_required=bool(data.get("reservation_required", True)),
            authorization_policy=str(data.get("authorization_policy", "M5-T10")),
            actual_cost_policy=str(data.get("actual_cost_policy", "PROVIDER_REPORTED_OR_UNKNOWN")),
        )


@dataclass(frozen=True)
class BuildContract:
    id: str
    project_id: str
    contract_version: int
    status: BuildContractStatus
    prompt: str
    product_family: str
    target: str
    release_target: str
    product_spec: ProductSpec
    user_roles: tuple[str, ...]
    data_requirements: tuple[str, ...]
    required_integrations: tuple[str, ...]
    infrastructure: tuple[InfrastructureRequirement, ...]
    capability_plan: CapabilityPlan
    capability_plan_fingerprint: str
    acceptance: tuple[AcceptanceCriterion, ...]
    security: tuple[str, ...]
    cost_envelope: CostEnvelopeReference
    unresolved_questions: tuple[ClarificationQuestion, ...]
    defaults_applied: tuple[str, ...]
    required_skill_keys: tuple[str, ...]
    required_agent_keys: tuple[str, ...]
    skills_registry_version: str
    agents_registry_version: str
    created_at: str
    contract_fingerprint: str

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.project_id.strip():
            raise ValueError("contract id and project id are required")
        if self.contract_version < 1:
            raise ValueError("contract_version must be >= 1")
        if not self.prompt.strip():
            raise ValueError("prompt is required")
        if not self.product_family.strip() or not self.target.strip() or not self.release_target.strip():
            raise ValueError("product family, target and release target are required")
        if not self.acceptance:
            raise ValueError("build contract must contain acceptance criteria")
        if not self.security:
            raise ValueError("build contract must contain security requirements")
        expected_plan = sha256_fingerprint(self.capability_plan.to_dict())
        if self.capability_plan_fingerprint != expected_plan:
            raise ValueError("capability plan fingerprint mismatch")
        if self.status == BuildContractStatus.READY and any(q.material for q in self.unresolved_questions):
            raise ValueError("READY contract cannot contain unresolved material questions")

    def _fingerprint_payload(self) -> dict[str, Any]:
        payload = self.to_dict(include_fingerprint=False)
        payload.pop("id", None)
        payload.pop("created_at", None)
        return payload

    def verify_fingerprint(self) -> bool:
        return self.contract_fingerprint == sha256_fingerprint(self._fingerprint_payload())

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "project_id": self.project_id,
            "contract_version": self.contract_version,
            "status": self.status.value,
            "prompt": self.prompt,
            "product_family": self.product_family,
            "target": self.target,
            "release_target": self.release_target,
            "product_spec": self.product_spec.to_dict(),
            "user_roles": list(self.user_roles),
            "data_requirements": list(self.data_requirements),
            "required_integrations": list(self.required_integrations),
            "infrastructure": [item.to_dict() for item in self.infrastructure],
            "capability_plan": self.capability_plan.to_dict(),
            "capability_plan_fingerprint": self.capability_plan_fingerprint,
            "acceptance": [
                {"id": item.id, "requirement_id": item.requirement_id, "text": item.text}
                for item in self.acceptance
            ],
            "security": list(self.security),
            "cost_envelope": self.cost_envelope.to_dict(),
            "unresolved_questions": [q.to_dict() for q in self.unresolved_questions],
            "defaults_applied": list(self.defaults_applied),
            "required_skill_keys": list(self.required_skill_keys),
            "required_agent_keys": list(self.required_agent_keys),
            "skills_registry_version": self.skills_registry_version,
            "agents_registry_version": self.agents_registry_version,
            "created_at": self.created_at,
        }
        if include_fingerprint:
            data["contract_fingerprint"] = self.contract_fingerprint
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BuildContract":
        capability_data = data["capability_plan"]
        requirements = tuple(
            CapabilityRequirement(
                id=str(item["id"]),
                key=str(item["key"]),
                purpose=str(item["purpose"]),
                required=bool(item["required"]),
                quantity=int(item.get("quantity", 1)),
                constraints=dict(item.get("constraints", {})),
                dependency_ids=tuple(str(x) for x in item.get("dependency_ids", ())),
            )
            for item in capability_data.get("requirements", ())
        )
        plan = CapabilityPlan(
            requirements=requirements,
            target_keys=tuple(str(x) for x in capability_data.get("target_keys", ())),
            notes=tuple(str(x) for x in capability_data.get("notes", ())),
        )
        acceptance = tuple(
            AcceptanceCriterion(str(item["id"]), str(item["requirement_id"]), str(item["text"]))
            for item in data.get("acceptance", ())
        )
        contract = cls(
            id=str(data["id"]),
            project_id=str(data["project_id"]),
            contract_version=int(data["contract_version"]),
            status=BuildContractStatus(str(data["status"])),
            prompt=str(data["prompt"]),
            product_family=str(data["product_family"]),
            target=str(data["target"]),
            release_target=str(data["release_target"]),
            product_spec=ProductSpec.from_dict(dict(data["product_spec"])),
            user_roles=tuple(str(x) for x in data.get("user_roles", ())),
            data_requirements=tuple(str(x) for x in data.get("data_requirements", ())),
            required_integrations=tuple(str(x) for x in data.get("required_integrations", ())),
            infrastructure=tuple(InfrastructureRequirement.from_dict(item) for item in data.get("infrastructure", ())),
            capability_plan=plan,
            capability_plan_fingerprint=str(data["capability_plan_fingerprint"]),
            acceptance=acceptance,
            security=tuple(str(x) for x in data.get("security", ())),
            cost_envelope=CostEnvelopeReference.from_dict(data["cost_envelope"]),
            unresolved_questions=tuple(ClarificationQuestion.from_dict(item) for item in data.get("unresolved_questions", ())),
            defaults_applied=tuple(str(x) for x in data.get("defaults_applied", ())),
            required_skill_keys=tuple(str(x) for x in data.get("required_skill_keys", ())),
            required_agent_keys=tuple(str(x) for x in data.get("required_agent_keys", ())),
            skills_registry_version=str(data["skills_registry_version"]),
            agents_registry_version=str(data["agents_registry_version"]),
            created_at=str(data["created_at"]),
            contract_fingerprint=str(data["contract_fingerprint"]),
        )
        if not contract.verify_fingerprint():
            raise ValueError("build contract fingerprint mismatch")
        return contract
