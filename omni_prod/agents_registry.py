from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .capabilities import CapabilityStatus
from .capability_registry import CapabilityRegistry
from .skills_registry import MasterSkillsRegistry


@dataclass(frozen=True)
class AgentDefinition:
    key: str
    role: str
    responsibilities: tuple[str, ...]
    status: CapabilityStatus
    trigger_conditions: tuple[str, ...] = ()
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    allowed_skills: tuple[str, ...] = ()
    forbidden_skills: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    dependency_agents: tuple[str, ...] = ()
    escalation_rules: tuple[str, ...] = ()
    budget_limits: Mapping[str, Any] = field(default_factory=dict)
    state_requirements: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    verification_tests: tuple[str, ...] = ()
    observability: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("agent key must not be empty")
        if not self.role.strip():
            raise ValueError("agent role must not be empty")
        if not self.responsibilities:
            raise ValueError("agent responsibilities must not be empty")


class MasterAgentsRegistry:
    def __init__(
        self,
        definitions: Iterable[AgentDefinition],
        skills_registry: MasterSkillsRegistry,
        *,
        version: str = "m4.95-v2",
    ) -> None:
        self.version = version
        self._skills = skills_registry
        source = tuple(definitions)
        by_key: dict[str, AgentDefinition] = {}
        for definition in source:
            if definition.key in by_key:
                raise ValueError(f"duplicate agent key: {definition.key}")
            by_key[definition.key] = definition
        self._definitions = source
        self._by_key = by_key
        self._validate_skill_references()
        self._validate_agent_dependencies()

    def get(self, key: str) -> AgentDefinition:
        try:
            return self._by_key[key]
        except KeyError as exc:
            raise KeyError(f"unknown agent key: {key}") from exc

    def all(self) -> tuple[AgentDefinition, ...]:
        return self._definitions

    def contains(self, key: str) -> bool:
        return key in self._by_key

    def _validate_skill_references(self) -> None:
        for agent in self._definitions:
            overlap = set(agent.allowed_skills) & set(agent.forbidden_skills)
            if overlap:
                raise ValueError(
                    f"agent {agent.key} has skills both allowed and forbidden: {sorted(overlap)}"
                )
            for skill in agent.allowed_skills:
                if not self._skills.contains(skill):
                    raise ValueError(f"unknown allowed skill {skill} for {agent.key}")
            for skill in agent.forbidden_skills:
                if not self._skills.contains(skill):
                    raise ValueError(f"unknown forbidden skill {skill} for {agent.key}")

    def _validate_agent_dependencies(self) -> None:
        for agent in self._definitions:
            for dependency in agent.dependency_agents:
                if dependency not in self._by_key:
                    raise ValueError(
                        f"unknown agent dependency {dependency} for {agent.key}"
                    )
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(key: str) -> None:
            if key in visited:
                return
            if key in visiting:
                raise ValueError(f"agent dependency cycle at {key}")
            visiting.add(key)
            for dependency in self._by_key[key].dependency_agents:
                visit(dependency)
            visiting.remove(key)
            visited.add(key)

        for key in self._by_key:
            visit(key)


def _s(capability_key: str) -> str:
    return f"skill.{capability_key}"


def _agent(
    key: str,
    role: str,
    responsibilities: tuple[str, ...],
    status: CapabilityStatus,
    allowed: tuple[str, ...],
    *,
    dependencies: tuple[str, ...] = (),
    forbidden: tuple[str, ...] = (),
) -> AgentDefinition:
    resolved_dependencies = dependencies
    if not resolved_dependencies and key != "agent.chief_orchestrator":
        resolved_dependencies = ("agent.chief_orchestrator",)
    return AgentDefinition(
        key=key,
        role=role,
        responsibilities=responsibilities,
        status=status,
        trigger_conditions=("build contract or capability plan requires one of the allowed skills",),
        inputs=("build_contract", "project_context", "capability_plan", "correlation_id"),
        outputs=("structured_result", "evidence_or_explicit_failure"),
        allowed_skills=allowed,
        forbidden_skills=forbidden,
        forbidden_actions=(
            "invent_success_without_evidence",
            "exceed_authorized_budget",
            "expose_secret_values",
            "cross_tenant_boundary",
            "silently_drop_required_capability",
        ),
        dependency_agents=resolved_dependencies,
        escalation_rules=("escalate material ambiguity, blocked capability, policy or budget violation",),
        budget_limits={"policy": "inherit_build_contract", "hard_ceiling_required": True},
        state_requirements=("project-scoped durable context", "immutable build-contract revision",),
        success_criteria=("produce machine-verifiable evidence or explicit failure",),
        verification_tests=("tests/test_m495_skills_agents_registry.py::RegistryGovernanceMetadataTests::test_canonical_agent_governance_metadata_is_complete",),
        observability=("correlation_id", "structured_events", "cost_usage_evidence", "customer_safe_error_reference"),
    )


def build_canonical_agents_registry(
    skills: MasterSkillsRegistry,
) -> MasterAgentsRegistry:
    integration_skills = tuple(
        skill.key
        for skill in skills.all()
        if skill.key.startswith("skill.integration.")
    )
    three_d_skills = tuple(
        skill.key for skill in skills.all() if skill.key.startswith("skill.media.3d.")
    )
    audio_skills = tuple(
        skill.key for skill in skills.all() if skill.key.startswith("skill.media.audio.")
    )
    publish_skills = tuple(
        skill.key for skill in skills.all() if skill.key.startswith("skill.publish.")
    )

    agents = (
        _agent("agent.chief_orchestrator", "Chief Orchestrator", ("coordinate product-production agents and release evidence",), CapabilityStatus.PARTIAL, (
            "skill.internal.capability.plan", "skill.internal.cost.plan", "skill.internal.release.gate",
            _s("software.plan"), _s("software.architecture"), _s("software.code.generate"),
            _s("software.build"), _s("software.test"), _s("software.repair"), _s("software.preview"), _s("software.export"),
        )),
        _agent("agent.product_architect", "Product Architect", ("compile product intent into architecture and acceptance plan",), CapabilityStatus.PARTIAL, (
            "skill.internal.requirements.clarify", "skill.internal.capability.plan", _s("software.plan"), _s("software.architecture"),
        )),
        _agent("agent.clarification", "Clarification Agent", ("ask only material product questions",), CapabilityStatus.NOT_IMPLEMENTED, ("skill.internal.requirements.clarify",)),
        _agent("agent.capability_planner", "Capability Planner", ("produce deterministic capability dependency plans",), CapabilityStatus.PARTIAL, ("skill.internal.capability.plan",)),
        _agent("agent.cost_planner", "Cost Planner", ("construct conservative execution cost envelopes",), CapabilityStatus.PARTIAL, ("skill.internal.cost.plan", "skill.internal.cost_audit")),
        _agent("agent.design_director", "Design Director", ("govern coherent visual and interaction design",), CapabilityStatus.NOT_IMPLEMENTED, (
            "skill.internal.design.direct", _s("media.image.generate"), _s("media.vector.generate"), _s("media.texture.generate"),
        )),
        _agent("agent.code", "Code Agent", ("generate and modify production code",), CapabilityStatus.PARTIAL, (
            _s("software.code.generate"), _s("software.code.modify"), _s("software.dependencies.install"), _s("software.build"), _s("software.test"),
        )),
        _agent("agent.backend", "Backend Agent", ("produce backend, database and API product layers",), CapabilityStatus.PARTIAL, (
            _s("target.backend"), _s("target.database"), _s("software.code.generate"), _s("integration.database"), _s("integration.webhook"),
        )),
        _agent("agent.infrastructure", "Infrastructure Agent", ("plan and provision generated-product infrastructure",), CapabilityStatus.NOT_IMPLEMENTED, (
            "skill.internal.infrastructure.plan", _s("integration.storage"), _s("integration.database"), _s("integration.email"), _s("integration.webhook"),
        )),
        _agent("agent.integration", "Integration Agent", ("bind, validate and monitor external integrations",), CapabilityStatus.NOT_IMPLEMENTED, ("skill.internal.integration.bind",) + integration_skills),
        _agent("agent.asset_director", "Asset Director", ("orchestrate multimodal asset production and reuse",), CapabilityStatus.NOT_IMPLEMENTED, (
            "skill.internal.asset.orchestrate", _s("media.image.generate"), _s("media.audio.sfx"), _s("media.audio.music"), _s("media.3d.mesh.generate"), _s("media.video.generate"),
        )),
        _agent("agent.three_d", "3D Agent", ("produce and validate 3D assets",), CapabilityStatus.NOT_IMPLEMENTED, three_d_skills),
        _agent("agent.game_director", "Game Director", ("orchestrate gameplay systems and game-production acceptance",), CapabilityStatus.NOT_IMPLEMENTED, (
            "skill.internal.game.design", _s("target.game.2d"), _s("target.game.3d"),
        )),
        _agent("agent.world_builder", "World Builder", ("plan and construct worlds and levels",), CapabilityStatus.NOT_IMPLEMENTED, (
            "skill.internal.world.build", _s("media.3d.scene.compose"), _s("media.texture.generate"),
        )),
        _agent("agent.mission_designer", "Mission Designer", ("design mission and quest graphs with acceptance rules",), CapabilityStatus.NOT_IMPLEMENTED, ("skill.internal.mission.design",)),
        _agent("agent.animation", "Animation Agent", ("rig, animate and retarget 3D assets",), CapabilityStatus.NOT_IMPLEMENTED, (
            _s("media.3d.rig"), _s("media.3d.animate"), _s("media.3d.retarget"),
        )),
        _agent("agent.audio_director", "Audio Director", ("orchestrate voice, music and sound production",), CapabilityStatus.NOT_IMPLEMENTED, audio_skills),
        _agent("agent.qa", "QA Agent", ("run functional verification and aggregate release evidence",), CapabilityStatus.PARTIAL, (_s("software.test"), "skill.internal.release.gate")),
        _agent("agent.playtester", "Playtester Agent", ("execute gameplay flows and report objective failures",), CapabilityStatus.NOT_IMPLEMENTED, ("skill.internal.playtest", _s("target.game.2d"), _s("target.game.3d"))),
        _agent("agent.visual_qa", "Visual QA Agent", ("verify visual, responsive and presentation quality",), CapabilityStatus.NOT_IMPLEMENTED, ("skill.internal.visual_qa",)),
        _agent("agent.performance", "Performance Agent", ("measure latency, FPS, memory and resource budgets",), CapabilityStatus.NOT_IMPLEMENTED, ("skill.internal.performance_qa",)),
        _agent("agent.security", "Security Agent", ("apply security checks and release gates",), CapabilityStatus.PARTIAL, ("skill.internal.security_review",)),
        _agent("agent.compliance", "Compliance Agent", ("apply domain, rights and regulatory gates",), CapabilityStatus.NOT_IMPLEMENTED, ("skill.internal.compliance_review",)),
        _agent("agent.repair", "Repair Agent", ("repair verified product failures without hiding them",), CapabilityStatus.PARTIAL, (_s("software.repair"), _s("software.code.modify"), _s("software.test"))),
        _agent("agent.deployment", "Deployment Agent", ("publish verified releases and support rollback",), CapabilityStatus.NOT_IMPLEMENTED, (_s("software.deploy.web"),) + publish_skills),
        _agent("agent.cost_auditor", "Cost Auditor", ("reconcile provider/platform cost and gross contribution",), CapabilityStatus.PARTIAL, ("skill.internal.cost_audit",)),
    )
    return MasterAgentsRegistry(agents, skills)


def validate_master_registries(
    capabilities: CapabilityRegistry,
    skills: MasterSkillsRegistry,
    agents: MasterAgentsRegistry,
) -> dict[str, object]:
    uncovered = tuple(
        capability.key
        for capability in capabilities.all()
        if not skills.skills_for_capability(capability.key)
    )
    unknown_agent_skills = tuple(
        (agent.key, skill)
        for agent in agents.all()
        for skill in (*agent.allowed_skills, *agent.forbidden_skills)
        if not skills.contains(skill)
    )
    skill_governance_issues = tuple(
        (skill.key, field_name)
        for skill in skills.all()
        for field_name, present in (
            ("product_families", bool(skill.product_families)),
            ("supported_targets", bool(skill.supported_targets)),
            ("provider_keys", bool(skill.provider_keys)),
            ("cost_model", bool(skill.cost_model)),
            ("permissions", bool(skill.permissions)),
            ("security_constraints", bool(skill.security_constraints)),
            ("legal_constraints", bool(skill.legal_constraints)),
            ("implementation_location", bool(skill.implementation_location)),
            ("verification_tests", bool(skill.verification_tests)),
            ("quality_metrics", bool(skill.quality_metrics)),
            ("last_verified_version", bool(skill.last_verified_version)),
            ("last_verified_date", bool(skill.last_verified_date)),
        )
        if not present
    )
    agent_governance_issues = tuple(
        (agent.key, field_name)
        for agent in agents.all()
        for field_name, present in (
            ("trigger_conditions", bool(agent.trigger_conditions)),
            ("inputs", bool(agent.inputs)),
            ("outputs", bool(agent.outputs)),
            ("allowed_skills", bool(agent.allowed_skills)),
            ("forbidden_actions", bool(agent.forbidden_actions)),
            ("escalation_rules", bool(agent.escalation_rules)),
            ("budget_limits", bool(agent.budget_limits)),
            ("state_requirements", bool(agent.state_requirements)),
            ("success_criteria", bool(agent.success_criteria)),
            ("verification_tests", bool(agent.verification_tests)),
            ("observability", bool(agent.observability)),
            ("dependency_agents", bool(agent.dependency_agents) or agent.key == "agent.chief_orchestrator"),
        )
        if not present
    )
    return {
        "capability_count": len(capabilities.all()),
        "skill_count": len(skills.all()),
        "agent_count": len(agents.all()),
        "uncovered_capabilities": uncovered,
        "unknown_agent_skills": unknown_agent_skills,
        "skill_governance_issues": skill_governance_issues,
        "agent_governance_issues": agent_governance_issues,
    }
