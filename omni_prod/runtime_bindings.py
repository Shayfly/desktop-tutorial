"""What actually runs, per agent role: code, configuration and evidence.

Only roles with real code on a real path appear here. Each binding names the
importable symbols that implement the role (checked by the auditor), the
configuration it needs (environment variable NAMES and where their presence
was observed -- never values), the evidence that it worked, and the observed
cost. Evidence of kind 'live' means a real run on the deployed system with an
id a reader can look up (build, run, version, STATUS entry); 'unit' means tests
only. A role missing from this file is DEFINED and nothing more.

Edit rules: never add 'live' evidence without an id from a real run; never
mark a gap closed without evidence; keep `gaps` honest.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Evidence:
    kind: str  # 'live' | 'unit'
    ref: str   # build/run/version id, STATUS section or test path
    note: str = ''


@dataclass(frozen=True)
class Requirement:
    names: tuple[str, ...]  # environment variable names, or a service name
    observed: str = ''      # where presence was observed (deploy notice, probe run); '' = not observed


@dataclass(frozen=True)
class Binding:
    role: str                       # agent_catalog key
    implementation: tuple[str, ...]  # 'module:Symbol'
    scope: str                      # product family/path this binding covers
    config: tuple[Requirement, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    cost: str = ''
    gaps: tuple[str, ...] = field(default_factory=tuple)
    blocked_by: str = ''            # set when a named credential/service is missing


_MODEL = Requirement(('GEMINI_API_KEY', 'OMNI_MODEL_CATALOG_JSON'),
                     'deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok')
_SANDBOX = Requirement(('OMNI_SANDBOX_RUNNER_URL', 'OMNI_SANDBOX_SHARED_SECRET'), 'deploy-worker sandbox probe PASS (every deploy)')
_DB = Requirement(('OMNI_DATABASE_URL',), 'deploy-worker migrations + queue probe PASS')
_S3 = Requirement(('OMNI_S3_ENDPOINT', 'OMNI_S3_BUCKET', 'OMNI_S3_ACCESS_KEY', 'OMNI_S3_SECRET_KEY'), 'deploy-worker storage probe PASS')
_REDIS = Requirement(('OMNI_REDIS_URL',), 'deploy-worker queue probe PASS')

_FOUNDER_BUILD = Evidence('live', 'bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39',
                          'founder build from the workspace, 2026-10-08 21:30-21:35, quality 84')
_FOUNDER_CHANGE = Evidence('live', 'mod_c14435dc9baa44bdac784d0c15ed9b85 -> v_0bc82ef7b33b4210',
                           'natural-language change accepted 2026-10-08 22:55; spec A1-A6')
_REHEARSAL = Evidence('live', 'golden-rehearsal run 37820429767', 'task-list prompt: ready, quality 86, 2 min')
_E2E = Evidence('live', 'STATUS.md "Golden E2E #1: full chain from the founder\'s workspace" (2026-10-08 23:05)')

WEB = 'web/self_contained_v1'

BINDINGS: tuple[Binding, ...] = (
    Binding('request_interpreter',
            ('omni_prod.product_architect:ProductArchitect', 'omni_prod.autonomous_agents:ArchitectAgent'),
            WEB, (_MODEL,), (_FOUNDER_BUILD, _REHEARSAL), 'one model call per build (~$0.005)',
            ('no clarification questions are asked', 'planner adds login/roles although the request says "no login"')),
    Binding('product_analyst', ('omni_prod.autonomous_agents:ArchitectAgent',), WEB, (_MODEL,),
            (_FOUNDER_BUILD, _FOUNDER_CHANGE), 'shared with request_interpreter',
            ('acceptance criteria only; no user stories or edge-case analysis',)),
    Binding('capability_resolver', ('omni_prod.capability_planner:CapabilityPlanner', 'omni_prod.build_contract:BuildContract'),
            WEB, (_DB,), (_FOUNDER_BUILD,), '$0 (deterministic)',
            ('keyword-based game detection misclassifies "משחק" (football match)',)),
    Binding('solution_architect', ('omni_prod.autonomous_agents:ArchitectAgent', 'omni_prod.dependency_policy:GENERATION_CONSTRAINTS'),
            WEB, (_MODEL,), (_FOUNDER_BUILD,), 'shared with request_interpreter',
            ('one fixed stack (Python stdlib + SQLite in /tmp); no durable data or API-contract design',)),
    Binding('project_orchestrator',
            ('omni_prod.worker_tasks:_run_live_build_job', 'omni_prod.autonomous_core:AutonomousProductEngine', 'omni_prod.worker:main'),
            WEB, (_REDIS, _DB), (_FOUNDER_BUILD, _E2E), '$0 (deterministic)',
            ('fixed 4-step pipeline, not a task graph', 'no cancel', 'no resume of a half-finished build (janitor fails it)')),
    Binding('cost_controller',
            ('omni_prod.routed_gateway:RoutedModelGateway', 'omni_prod.subscription_store:PostgresSubscriptionService',
             'omni_prod.qa_budget:qa_used_usd'),
            WEB, (_DB,), (Evidence('live', 'build-evidence run 37832677078', 'QA real spend since paid tier $0.35'),
                          Evidence('unit', 'tests/test_provider_quota_and_dialects.py')),
            '$0 (deterministic)', ('no per-step cost shown to the user', 'no provider invoice reconciliation')),
    Binding('frontend_developer', ('omni_prod.autonomous_agents:GeneratorAgent',), WEB, (_MODEL,),
            (_FOUNDER_BUILD, _FOUNDER_CHANGE), 'part of ~$0.07 per build',
            ('no browser check of flows', 'UI quality gaps found by the founder: alert() errors, ISO dates, hidden filter state')),
    Binding('backend_developer', ('omni_prod.autonomous_agents:GeneratorAgent',), WEB, (_MODEL,),
            (_FOUNDER_BUILD, _FOUNDER_CHANGE), 'shared with frontend_developer',
            ('input validation only when the user asks for it',)),
    Binding('repository_maintainer',
            ('omni_prod.workspace:PostgresProjectWorkspace', 'omni_prod.storage:S3ArtifactStore',
             'omni_prod.spec_repository:restore_version_with_spec'),
            WEB, (_DB, _S3), (_FOUNDER_CHANGE, Evidence('live', 'ZIP of v_0bc82ef7b33b4210 opened by the founder 2026-10-08 22:59')),
            '$0', ()),
    Binding('qa_verifier',
            ('omni_prod.remote_sandbox:RemoteSandboxRepositoryExecutor', 'omni_prod.preview_smoke:PreviewReadyExecutor',
             'omni_prod.quality_gate:QualityAwareExecutor', 'omni_prod.product_review:ProductReviewExecutor'),
            WEB, (_SANDBOX, _MODEL), (_FOUNDER_BUILD, _REHEARSAL,
                                      Evidence('live', 'golden-rehearsal run 37841459920',
                                               'skills on: QA review round 1 by gemini-3.8-flash, 0 blocking; ready, quality 86')),
            'one review call per round (~$0.01)',
            ('the reviewer is a Gemini model like the author: OpenAI/Anthropic have no credit, so no independent vendor',
             'reviews the code, not the running product: no HTTP behaviour probes or browser yet',
             'not yet exercised on a founder build')),
    Binding('security_reviewer', ('omni_prod.security_testing:hostile_repository_scan', 'omni_prod.worker_tasks:evaluate_release_gates'),
            WEB, (), (_FOUNDER_BUILD,), '$0', ('static scan only; no authorization testing of the generated app',)),
    Binding('repair_agent', ('omni_prod.autonomous_agents:RepairAgent',), WEB, (_MODEL, _SANDBOX),
            (_FOUNDER_BUILD, Evidence('live', 'golden-rehearsal run 37814985551', '5 repair rounds converged')),
            'part of ~$0.07 per build', ('repairs the whole repository rather than a minimal patch',)),
    Binding('preview_operator',
            ('omni_prod.preview_runtime:DockerPreviewProvider', 'omni_prod.preview_router:make_handler'),
            WEB, (Requirement(('PREVIEW_DOMAIN_TEMPLATE', 'OMNI_PREVIEW_HOST_SUFFIX'), 'deploy-worker "Preview edge is up" PASS'),),
            (Evidence('live', 'https://prv-1760dedc67864c0186aa0cdf945bab0d.151-145-89-132.sslip.io', 'v_246bae81234e4c39 shown in the workspace'),),
            '$0 (worker host)', ('data in /tmp is lost when the preview stops', 'temporary sslip.io address, open to anyone with the link')),
    Binding('operations_agent', ('omni_prod.maintenance:run_once',), 'platform', (_DB,),
            (Evidence('unit', 'tests/test_maintenance_live_postgres.py'), Evidence('live', 'deploy-worker "janitor started"')),
            '$0', ('no alerting', 'no health monitoring of generated products')),
    Binding('visual_creator', ('omni_prod.providers.image_provider:PredictionImageProvider',), 'assets',
            (Requirement(('REPLICATE_API_TOKEN',), 'Replicate authentication live-verified on Preview (STATUS 2026-10-06)'),),
            (Evidence('unit', 'tests/test_replicate_image_test.py'),), 'about $0.003 per image (FLUX Schnell list price)',
            ('no image has been generated live yet', 'not on the build path')),
    Binding('registry_auditor', ('omni_prod.registry_audit:audit',), 'platform', (),
            (Evidence('unit', 'tests/test_registry_audit.py'),), '$0', ()),
    Binding('provider_evaluator', ('omni_prod.model_probe:probe', 'omni_prod.rehearsal:cost_projection'), 'platform', (_MODEL,),
            (Evidence('live', 'model-probe run 37814803770', '3 Gemini models ok; OpenAI/Anthropic refused: no credit'),),
            '< $0.001 per probe', ('no quality benchmark across providers yet',)),
)

BY_ROLE = {b.role: b for b in BINDINGS}


@dataclass(frozen=True)
class SkillBinding:
    key: str                         # omni_prod.skills_runtime skill key
    evidence: tuple[Evidence, ...] = ()
    gaps: tuple[str, ...] = ()


_SKILLS_REHEARSAL = Evidence('live', 'golden-rehearsal run 37841459920',
                             'skills_applied recorded in the build; QA review against their checklists, 0 blocking')

SKILL_BINDINGS: tuple[SkillBinding, ...] = (
    SkillBinding('skill.request_fidelity', (_SKILLS_REHEARSAL,),
                 ('the plan view still lists "login and sessions" from ProductArchitect for a "no login" request',)),
    SkillBinding('skill.form_validation', (_SKILLS_REHEARSAL,), ('no HTTP probe sends invalid input to the running app yet',)),
    SkillBinding('skill.ui_states', (_SKILLS_REHEARSAL,), ('checked by code review only, not in a browser',)),
    SkillBinding('skill.text_locale', (_SKILLS_REHEARSAL,), ()),
    SkillBinding('skill.data_integrity', (_SKILLS_REHEARSAL,), ('no conflict/404 probe against the running app yet',)),
    SkillBinding('skill.visual_design', (Evidence('live', 'golden-rehearsal run 37858017258',
                                                  'library prompt: ready, quality 86, design static check passed, review 0 blocking'),),
                 ('checked by a CSS heuristic and code review, not by looking at a screenshot',
                  'not yet seen by the founder in a preview')),
)
SKILL_BY_KEY = {b.key: b for b in SKILL_BINDINGS}
assert len(BY_ROLE) == len(BINDINGS), 'one binding per role'
