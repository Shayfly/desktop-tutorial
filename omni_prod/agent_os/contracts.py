"""Agent and Skill contracts (autonomous completion directive §6, §10).

A contract says what an agent or skill IS: responsibility, when it runs,
inputs/outputs, what it may and may not do, who verifies it, its policies and
where its code lives. It never says whether it works -- status is computed by
`omni_prod.agent_os.audit` from the implementation (does the code import),
configuration (was it observed) and evidence (real runs, fresh for the code
that ran). A record with only a name and a description is NOT implemented.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields

# Status vocabulary (Production Assurance v2 §3, 2026-10-10), weakest to strongest:
#   NOT_IMPLEMENTED       no implementation, or it does not import
#   IMPLEMENTED           code exists, no test evidence
#   UNIT_TESTED           unit tests only
#   INTEGRATION_TESTED    tests against real dependencies (e.g. live PostgreSQL)
#   REAL_SERVER_VERIFIED  a fresh run on the deployed pre-staging system
#   LIVE                  a fresh run in PRODUCTION (no production exists yet)
#   BLOCKED               a named external blocker (credential, contract, configuration)
NOT_IMPLEMENTED, IMPLEMENTED, UNIT_TESTED, INTEGRATION_TESTED = 'NOT_IMPLEMENTED', 'IMPLEMENTED', 'UNIT_TESTED', 'INTEGRATION_TESTED'
REAL_SERVER_VERIFIED, LIVE, BLOCKED = 'REAL_SERVER_VERIFIED', 'LIVE', 'BLOCKED'
STATUSES = (NOT_IMPLEMENTED, IMPLEMENTED, UNIT_TESTED, INTEGRATION_TESTED, REAL_SERVER_VERIFIED, LIVE, BLOCKED)
VERIFIED_STATUSES = (REAL_SERVER_VERIFIED, LIVE)
PRODUCTION_ENVS = ('production',)


@dataclass(frozen=True)
class AgentContract:
    agent_key: str
    name: str
    version: str
    category: str
    identity: str
    purpose: str
    unique_responsibility: str
    when_invoked: str
    trigger_conditions: tuple[str, ...]
    required_inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    allowed_skills: tuple[str, ...]
    forbidden_skills: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    permissions: tuple[str, ...]
    provider_policy: str
    budget_policy: str
    memory_policy: str
    state_policy: str
    handoff_policy: str
    retry_policy: str
    timeout_policy: str
    escalation_policy: str
    approval_policy: str
    success_criteria: tuple[str, ...]
    failure_criteria: tuple[str, ...]
    verifier: str                       # agent_key of the independent verifier ('' = founder)
    verification_tests: tuple[str, ...]  # test paths / check names
    observability_requirements: tuple[str, ...]
    security_requirements: tuple[str, ...]
    commercial_constraints: tuple[str, ...]
    implementation_location: tuple[str, ...]  # 'module:Symbol' / 'path:file'; () = none
    config: tuple[str, ...] = ()        # environment names the implementation needs
    blocked_by: str = ''
    evidence: tuple = ()                # runtime_bindings.Evidence
    # status / last_verified_at / last_verified_commit are computed by the audit

    def missing_fields(self) -> list[str]:
        optional = {'config', 'blocked_by', 'evidence', 'implementation_location', 'forbidden_skills', 'verifier'}
        return [f.name for f in fields(self) if f.name not in optional and not getattr(self, f.name)]


@dataclass(frozen=True)
class SkillContract:
    skill_key: str
    name: str
    version: str
    category: str
    purpose: str
    unique_responsibility: str
    when_used: str
    when_not_used: str
    trigger_conditions: tuple[str, ...]
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    preconditions: tuple[str, ...]
    postconditions: tuple[str, ...]
    dependencies: tuple[str, ...]
    primary_agent: str
    secondary_agent: str
    verifier_agent: str
    supported_targets: tuple[str, ...]
    providers: tuple[str, ...]
    cheap_provider: str
    standard_provider: str
    premium_provider: str
    fallback_provider: str
    estimated_cost_model: str
    permissions: tuple[str, ...]
    security_constraints: tuple[str, ...]
    commercial_constraints: tuple[str, ...]
    data_policy: str
    implementation_location: tuple[str, ...]
    verification_method: str
    quality_metrics: tuple[str, ...]
    success_criteria: tuple[str, ...]
    failure_modes: tuple[str, ...]
    retry_policy: str
    fallback_policy: str
    config: tuple[str, ...] = ()
    blocked_by: str = ''
    evidence: tuple = ()
    gap: str = ''

    def missing_fields(self) -> list[str]:
        optional = {'config', 'blocked_by', 'evidence', 'gap', 'implementation_location', 'optional_inputs',
                    'dependencies', 'secondary_agent', 'providers', 'cheap_provider', 'standard_provider',
                    'premium_provider', 'fallback_provider'}
        return [f.name for f in fields(self) if f.name not in optional and not getattr(self, f.name)]
