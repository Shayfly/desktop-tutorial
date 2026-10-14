import unittest
from pathlib import Path

from omni_prod.capability_registry import CapabilityRegistry
from omni_prod.capabilities import CapabilityStatus
from omni_prod.skills_registry import (
    SkillDefinition,
    MasterSkillsRegistry,
    build_canonical_skills_registry,
)
from omni_prod.agents_registry import (
    AgentDefinition,
    MasterAgentsRegistry,
    build_canonical_agents_registry,
    validate_master_registries,
)


class MasterSkillsRegistryTests(unittest.TestCase):
    def test_every_canonical_capability_has_at_least_one_skill(self):
        capabilities = CapabilityRegistry()
        skills = build_canonical_skills_registry(capabilities)
        for capability in capabilities.all():
            self.assertTrue(
                skills.skills_for_capability(capability.key),
                f"missing skill coverage for {capability.key}",
            )

    def test_skill_keys_are_unique_and_dependencies_must_exist(self):
        one = SkillDefinition(
            key="skill.one",
            description="one",
            capability_keys=("software.plan",),
            status=CapabilityStatus.PARTIAL,
        )
        with self.assertRaisesRegex(ValueError, "duplicate skill key"):
            MasterSkillsRegistry((one, one), CapabilityRegistry())
        broken = SkillDefinition(
            key="skill.broken",
            description="broken",
            dependency_keys=("skill.nope",),
            status=CapabilityStatus.NOT_IMPLEMENTED,
        )
        with self.assertRaisesRegex(ValueError, "unknown skill dependency"):
            MasterSkillsRegistry((broken,), CapabilityRegistry())

    def test_skill_dependency_cycles_are_rejected(self):
        a = SkillDefinition(
            key="skill.a", description="a", dependency_keys=("skill.b",),
            status=CapabilityStatus.NOT_IMPLEMENTED,
        )
        b = SkillDefinition(
            key="skill.b", description="b", dependency_keys=("skill.a",),
            status=CapabilityStatus.NOT_IMPLEMENTED,
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            MasterSkillsRegistry((a, b), CapabilityRegistry())

    def test_skill_capability_references_must_be_canonical(self):
        bad = SkillDefinition(
            key="skill.bad", description="bad", capability_keys=("missing.cap",),
            status=CapabilityStatus.NOT_IMPLEMENTED,
        )
        with self.assertRaisesRegex(ValueError, "unknown capability"):
            MasterSkillsRegistry((bad,), CapabilityRegistry())

    def test_internal_skills_can_exist_without_user_capability_mapping(self):
        skill = SkillDefinition(
            key="skill.internal.review", description="review",
            capability_keys=(), status=CapabilityStatus.NOT_IMPLEMENTED,
        )
        registry = MasterSkillsRegistry((skill,), CapabilityRegistry())
        self.assertEqual(registry.get("skill.internal.review"), skill)


class MasterAgentsRegistryTests(unittest.TestCase):
    def setUp(self):
        self.capabilities = CapabilityRegistry()
        self.skills = build_canonical_skills_registry(self.capabilities)

    def test_canonical_agent_roles_exist(self):
        agents = build_canonical_agents_registry(self.skills)
        required = {
            "agent.chief_orchestrator", "agent.product_architect",
            "agent.clarification", "agent.capability_planner", "agent.cost_planner",
            "agent.design_director", "agent.code", "agent.backend",
            "agent.infrastructure", "agent.integration", "agent.asset_director",
            "agent.three_d", "agent.game_director", "agent.world_builder",
            "agent.mission_designer", "agent.animation", "agent.audio_director",
            "agent.qa", "agent.playtester", "agent.visual_qa", "agent.performance",
            "agent.security", "agent.compliance", "agent.repair",
            "agent.deployment", "agent.cost_auditor",
        }
        self.assertTrue(required.issubset({agent.key for agent in agents.all()}))

    def test_agents_cannot_reference_unknown_skills(self):
        bad = AgentDefinition(
            key="agent.bad", role="bad", responsibilities=("x",),
            allowed_skills=("skill.nope",), status=CapabilityStatus.NOT_IMPLEMENTED,
        )
        with self.assertRaisesRegex(ValueError, "unknown allowed skill"):
            MasterAgentsRegistry((bad,), self.skills)

    def test_allowed_and_forbidden_skills_cannot_overlap(self):
        skill_key = self.skills.all()[0].key
        bad = AgentDefinition(
            key="agent.bad", role="bad", responsibilities=("x",),
            allowed_skills=(skill_key,), forbidden_skills=(skill_key,),
            status=CapabilityStatus.NOT_IMPLEMENTED,
        )
        with self.assertRaisesRegex(ValueError, "both allowed and forbidden"):
            MasterAgentsRegistry((bad,), self.skills)

    def test_agent_dependencies_must_exist_and_be_acyclic(self):
        a = AgentDefinition(
            key="agent.a", role="a", responsibilities=("a",),
            dependency_agents=("agent.b",), status=CapabilityStatus.NOT_IMPLEMENTED,
        )
        b = AgentDefinition(
            key="agent.b", role="b", responsibilities=("b",),
            dependency_agents=("agent.a",), status=CapabilityStatus.NOT_IMPLEMENTED,
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            MasterAgentsRegistry((a, b), self.skills)

    def test_cross_registry_truth_validation_passes_for_canonical_sets(self):
        agents = build_canonical_agents_registry(self.skills)
        report = validate_master_registries(self.capabilities, self.skills, agents)
        self.assertEqual(report["uncovered_capabilities"], ())
        self.assertEqual(report["unknown_agent_skills"], ())
        self.assertGreater(report["skill_count"], 80)
        self.assertGreaterEqual(report["agent_count"], 26)

    def test_no_canonical_agent_is_claimed_live_in_m495_foundation(self):
        agents = build_canonical_agents_registry(self.skills)
        self.assertNotIn(CapabilityStatus.LIVE, {agent.status for agent in agents.all()})


class RegistryGovernanceMetadataTests(unittest.TestCase):
    def test_canonical_skill_governance_metadata_is_complete(self):
        capabilities = CapabilityRegistry()
        skills = build_canonical_skills_registry(capabilities)
        for skill in skills.all():
            self.assertTrue(skill.product_families, skill.key)
            self.assertTrue(skill.supported_targets, skill.key)
            self.assertTrue(skill.provider_keys, skill.key)
            self.assertTrue(skill.cost_model, skill.key)
            self.assertTrue(skill.permissions, skill.key)
            self.assertTrue(skill.security_constraints, skill.key)
            self.assertTrue(skill.legal_constraints, skill.key)
            self.assertTrue(skill.implementation_location, skill.key)
            self.assertTrue(skill.verification_tests, skill.key)
            self.assertTrue(skill.quality_metrics, skill.key)
            self.assertTrue(skill.last_verified_version, skill.key)
            self.assertTrue(skill.last_verified_date, skill.key)
            if skill.status in {CapabilityStatus.PARTIAL, CapabilityStatus.LIVE}:
                self.assertTrue(
                    (Path(__file__).resolve().parents[1] / skill.implementation_location).exists(),
                    f"{skill.key}: missing implementation location {skill.implementation_location}",
                )

    def test_canonical_agent_governance_metadata_is_complete(self):
        capabilities = CapabilityRegistry()
        skills = build_canonical_skills_registry(capabilities)
        agents = build_canonical_agents_registry(skills)
        for agent in agents.all():
            self.assertTrue(agent.trigger_conditions, agent.key)
            self.assertTrue(agent.inputs, agent.key)
            self.assertTrue(agent.outputs, agent.key)
            self.assertTrue(agent.allowed_skills, agent.key)
            self.assertTrue(agent.forbidden_actions, agent.key)
            self.assertTrue(agent.escalation_rules, agent.key)
            self.assertTrue(agent.budget_limits, agent.key)
            self.assertTrue(agent.state_requirements, agent.key)
            self.assertTrue(agent.success_criteria, agent.key)
            self.assertTrue(agent.verification_tests, agent.key)
            self.assertTrue(agent.observability, agent.key)
            if agent.key != "agent.chief_orchestrator":
                self.assertTrue(agent.dependency_agents, agent.key)

    def test_cross_registry_report_has_no_governance_metadata_gaps(self):
        capabilities = CapabilityRegistry()
        skills = build_canonical_skills_registry(capabilities)
        agents = build_canonical_agents_registry(skills)
        report = validate_master_registries(capabilities, skills, agents)
        self.assertEqual(report["skill_governance_issues"], ())
        self.assertEqual(report["agent_governance_issues"], ())


if __name__ == "__main__":
    unittest.main()
