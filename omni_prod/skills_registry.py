from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .capabilities import CapabilityStatus
from .capability_registry import CapabilityRegistry


@dataclass(frozen=True)
class SkillDefinition:
    key: str
    description: str
    status: CapabilityStatus
    capability_keys: tuple[str, ...] = ()
    dependency_keys: tuple[str, ...] = ()
    product_families: tuple[str, ...] = ()
    provider_keys: tuple[str, ...] = ()
    cost_model: str = "UNKNOWN"
    permissions: tuple[str, ...] = ()
    legal_constraints: tuple[str, ...] = ()
    verification_tests: tuple[str, ...] = ()
    last_verified_version: str | None = None
    last_verified_date: str | None = None

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("skill key must not be empty")
        if not self.description.strip():
            raise ValueError("skill description must not be empty")


class MasterSkillsRegistry:
    def __init__(
        self,
        definitions: Iterable[SkillDefinition],
        capability_registry: CapabilityRegistry,
        *,
        version: str = "m4.95-v2",
    ) -> None:
        self.version = version
        self._capabilities = capability_registry
        source = tuple(definitions)
        by_key: dict[str, SkillDefinition] = {}
        for definition in source:
            if definition.key in by_key:
                raise ValueError(f"duplicate skill key: {definition.key}")
            for capability_key in definition.capability_keys:
                if not capability_registry.contains(capability_key):
                    raise ValueError(
                        f"unknown capability {capability_key} referenced by {definition.key}"
                    )
            by_key[definition.key] = definition
        self._definitions = source
        self._by_key = by_key
        self._validate_dependencies()

    def get(self, key: str) -> SkillDefinition:
        try:
            return self._by_key[key]
        except KeyError as exc:
            raise KeyError(f"unknown skill key: {key}") from exc

    def contains(self, key: str) -> bool:
        return key in self._by_key

    def all(self) -> tuple[SkillDefinition, ...]:
        return self._definitions

    def skills_for_capability(self, capability_key: str) -> tuple[SkillDefinition, ...]:
        if not self._capabilities.contains(capability_key):
            raise KeyError(f"unknown capability key: {capability_key}")
        return tuple(
            skill for skill in self._definitions if capability_key in skill.capability_keys
        )

    def dependency_closure(self, keys: tuple[str, ...]) -> tuple[str, ...]:
        result: list[str] = []
        emitted: set[str] = set()
        visiting: set[str] = set()

        def visit(key: str) -> None:
            if key in emitted:
                return
            if key in visiting:
                raise ValueError(f"skill dependency cycle at {key}")
            skill = self.get(key)
            visiting.add(key)
            for dependency in skill.dependency_keys:
                visit(dependency)
            visiting.remove(key)
            emitted.add(key)
            result.append(key)

        for key in keys:
            visit(key)
        return tuple(result)

    def _validate_dependencies(self) -> None:
        for skill in self._definitions:
            for dependency in skill.dependency_keys:
                if dependency not in self._by_key:
                    raise ValueError(
                        f"unknown skill dependency {dependency} referenced by {skill.key}"
                    )
        self.dependency_closure(tuple(self._by_key))


def _skill_key(capability_key: str) -> str:
    return f"skill.{capability_key}"


def _status_for_capability(key: str) -> CapabilityStatus:
    if key.startswith("software."):
        return (
            CapabilityStatus.NOT_IMPLEMENTED
            if key == "software.deploy.web"
            else CapabilityStatus.PARTIAL
        )
    if key in {"target.web", "target.saas", "target.backend", "target.database"}:
        return CapabilityStatus.PARTIAL
    if key in {
        "target.android.source", "target.android.build", "target.ios.source",
        "target.ios.build", "target.game.2d", "target.game.3d",
    }:
        return CapabilityStatus.PARTIAL
    if key.startswith("media."):
        return CapabilityStatus.PARTIAL
    if key.startswith("integration.") and key in {
        "integration.payment", "integration.email", "integration.maps",
        "integration.storage", "integration.database", "integration.source_control",
        "integration.oauth", "integration.analytics", "integration.webhook",
    }:
        return CapabilityStatus.PARTIAL
    return CapabilityStatus.NOT_IMPLEMENTED


def _cost_model_for(capability_key: str) -> str:
    if capability_key.startswith(("media.", "ai.")) or capability_key in {
        "software.plan", "software.architecture", "software.code.generate",
        "software.code.modify", "software.repair",
    }:
        return "PROVIDER_METERED"
    if capability_key.startswith(("software.", "target.", "publish.")):
        return "PLATFORM_COMPUTE"
    return "UNKNOWN"


_INTERNAL_SKILLS: tuple[SkillDefinition, ...] = (
    SkillDefinition("skill.internal.requirements.clarify", "Clarify only material product uncertainties", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.capability.plan", "Compile intent into a capability dependency DAG", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.cost.plan", "Construct conservative pre-execution cost envelope", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.design.direct", "Choose and govern a coherent product visual system", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.infrastructure.plan", "Plan durable generated-product infrastructure", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.integration.bind", "Bind and validate customer/platform integrations", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.asset.orchestrate", "Orchestrate asset DAG generation, reuse and regeneration", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.game.design", "Create game production and mechanics plan", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.world.build", "Plan/build large game worlds and levels", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.mission.design", "Plan mission/quest graphs and acceptance rules", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.playtest", "Execute gameplay flows and collect pass/fail evidence", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.visual_qa", "Perform visual and responsive quality review", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.performance_qa", "Measure runtime performance and resource budgets", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.security_review", "Perform security review and release gating", CapabilityStatus.PARTIAL),
    SkillDefinition("skill.internal.compliance_review", "Apply domain/legal/compliance release gates", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.cost_audit", "Reconcile provider usage, platform cost and margin", CapabilityStatus.NOT_IMPLEMENTED),
    SkillDefinition("skill.internal.release.gate", "Aggregate release evidence and block false readiness", CapabilityStatus.PARTIAL),
)


def build_canonical_skills_registry(
    capability_registry: CapabilityRegistry | None = None,
) -> MasterSkillsRegistry:
    capabilities = capability_registry or CapabilityRegistry()
    capability_skills: list[SkillDefinition] = []
    for capability in capabilities.all():
        capability_skills.append(
            SkillDefinition(
                key=_skill_key(capability.key),
                description=f"Execute capability {capability.key}",
                status=_status_for_capability(capability.key),
                capability_keys=(capability.key,),
                dependency_keys=tuple(_skill_key(dep) for dep in capability.dependency_keys),
                product_families=(capability.family,),
                cost_model=_cost_model_for(capability.key),
                permissions=("tenant_project_scope",),
                legal_constraints=("commercial_use_rights",)
                if capability.commercial_use_required
                else (),
            )
        )
    return MasterSkillsRegistry(
        tuple(capability_skills) + _INTERNAL_SKILLS,
        capabilities,
    )
