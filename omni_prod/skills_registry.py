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
    supported_targets: tuple[str, ...] = ()
    provider_keys: tuple[str, ...] = ()
    cost_model: str = "UNKNOWN"
    permissions: tuple[str, ...] = ()
    security_constraints: tuple[str, ...] = ()
    legal_constraints: tuple[str, ...] = ()
    implementation_location: str = ""
    verification_tests: tuple[str, ...] = ()
    quality_metrics: tuple[str, ...] = ()
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


def _supported_targets_for(capability_key: str) -> tuple[str, ...]:
    if capability_key.startswith("target."):
        parts = capability_key.split(".")
        target = parts[1]
        return ("mobile" if target in {"android", "ios"} else target,)
    if capability_key.startswith("media."):
        return ("web", "saas", "mobile", "desktop", "game", "media")
    if capability_key.startswith("integration."):
        return ("web", "saas", "mobile", "desktop", "agent", "automation")
    if capability_key.startswith("publish."):
        return ("web", "mobile", "asset")
    if capability_key.startswith(("ecosystem.", "game.")):
        return ("web", "saas", "game")
    return ("web", "saas", "backend", "mobile", "desktop", "agent", "automation", "game", "media")


def _provider_keys_for(capability_key: str, *, provider_backed: bool) -> tuple[str, ...]:
    if provider_backed:
        return ("runtime.provider_registry",)
    if capability_key.startswith("integration."):
        return ("runtime.integration_registry",)
    return ("platform.internal",)


def _implementation_location_for(capability_key: str) -> str:
    if capability_key.startswith("media."):
        return "omni_prod/media_pipeline.py"
    if capability_key.startswith("integration."):
        return "omni_prod/integrations.py"
    if capability_key.startswith("target.game") or capability_key.startswith("game."):
        return "omni_prod/game_pipeline.py"
    if capability_key.startswith("target.android") or capability_key.startswith("target.ios"):
        return "omni_prod/mobile_pipeline.py"
    if capability_key.startswith("publish.") or capability_key == "software.deploy.web":
        return "omni_prod/deployment.py"
    if capability_key.startswith("software."):
        return "omni_prod/worker_tasks.py"
    return "omni_prod/capability_executor.py"


def _quality_metrics_for(capability_key: str) -> tuple[str, ...]:
    base = ("truthful_status", "explicit_failure", "dependency_closure")
    if capability_key.startswith("media."):
        return base + ("artifact_integrity", "format_validation")
    if capability_key.startswith("software."):
        return base + ("build_test_evidence",)
    if capability_key.startswith("integration."):
        return base + ("secret_safety", "idempotency")
    return base


def _internal_skill(key: str, description: str, status: CapabilityStatus, location: str) -> SkillDefinition:
    return SkillDefinition(
        key=key,
        description=description,
        status=status,
        product_families=("platform",),
        supported_targets=("all",),
        provider_keys=("platform.internal",),
        cost_model="PLATFORM_COMPUTE",
        permissions=("tenant_project_scope",),
        security_constraints=("tenant_isolation", "no_secret_exposure", "evidence_required_before_success"),
        legal_constraints=("inherit_product_rights_policy",),
        implementation_location=location,
        verification_tests=("tests/test_m495_skills_agents_registry.py::RegistryGovernanceMetadataTests::test_canonical_skill_governance_metadata_is_complete",),
        quality_metrics=("truthful_status", "machine_verifiable_evidence", "explicit_failure"),
        last_verified_version="registry-governance-v1",
        last_verified_date="2026-10-04",
    )


_INTERNAL_SKILLS: tuple[SkillDefinition, ...] = (
    _internal_skill("skill.internal.requirements.clarify", "Clarify only material product uncertainties", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/product_architect.py"),
    _internal_skill("skill.internal.capability.plan", "Compile intent into a capability dependency DAG", CapabilityStatus.PARTIAL, "omni_prod/capability_planner.py"),
    _internal_skill("skill.internal.cost.plan", "Construct conservative pre-execution cost envelope", CapabilityStatus.PARTIAL, "omni_prod/provider_pricing.py"),
    _internal_skill("skill.internal.design.direct", "Choose and govern a coherent product visual system", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/media_pipeline.py"),
    _internal_skill("skill.internal.infrastructure.plan", "Plan durable generated-product infrastructure", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/capability_planner.py"),
    _internal_skill("skill.internal.integration.bind", "Bind and validate customer/platform integrations", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/integration_center.py"),
    _internal_skill("skill.internal.asset.orchestrate", "Orchestrate asset DAG generation, reuse and regeneration", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/media_pipeline.py"),
    _internal_skill("skill.internal.game.design", "Create game production and mechanics plan", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/game_pipeline.py"),
    _internal_skill("skill.internal.world.build", "Plan/build large game worlds and levels", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/game_pipeline.py"),
    _internal_skill("skill.internal.mission.design", "Plan mission/quest graphs and acceptance rules", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/game_pipeline.py"),
    _internal_skill("skill.internal.playtest", "Execute gameplay flows and collect pass/fail evidence", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/game_pipeline.py"),
    _internal_skill("skill.internal.visual_qa", "Perform visual and responsive quality review", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/acceptance.py"),
    _internal_skill("skill.internal.performance_qa", "Measure runtime performance and resource budgets", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/observability.py"),
    _internal_skill("skill.internal.security_review", "Perform security review and release gating", CapabilityStatus.PARTIAL, "omni_prod/security_testing.py"),
    _internal_skill("skill.internal.compliance_review", "Apply domain/legal/compliance release gates", CapabilityStatus.NOT_IMPLEMENTED, "omni_prod/rights_engine.py"),
    _internal_skill("skill.internal.cost_audit", "Reconcile provider usage, platform cost and margin", CapabilityStatus.PARTIAL, "omni_prod/provider_pricing.py"),
    _internal_skill("skill.internal.release.gate", "Aggregate release evidence and block false readiness", CapabilityStatus.PARTIAL, "omni_prod/release_gate.py"),
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
                supported_targets=_supported_targets_for(capability.key),
                provider_keys=_provider_keys_for(capability.key, provider_backed=capability.provider_backed),
                cost_model=_cost_model_for(capability.key),
                permissions=("tenant_project_scope",),
                security_constraints=("tenant_isolation", "no_secret_exposure", "evidence_required_before_success"),
                legal_constraints=("commercial_use_rights", "provider_terms_and_ip_policy")
                if capability.commercial_use_required
                else ("provider_terms_and_ip_policy",),
                implementation_location=_implementation_location_for(capability.key),
                verification_tests=("tests/test_m495_skills_agents_registry.py::RegistryGovernanceMetadataTests::test_canonical_skill_governance_metadata_is_complete",),
                quality_metrics=_quality_metrics_for(capability.key),
                last_verified_version="registry-governance-v1",
                last_verified_date="2026-10-04",
            )
        )
    return MasterSkillsRegistry(
        tuple(capability_skills) + _INTERNAL_SKILLS,
        capabilities,
    )
