"""What actually runs, per agent role: code, configuration and evidence.

Only roles with real code on a real path appear here. Each binding names the
code that implements the role ('module:Symbol', or 'path:<file>' for
non-Python code such as a workflow; checked by the auditor), the configuration
it needs (environment variable NAMES and where their presence was observed --
never values), the evidence that it worked, and the observed cost.

Evidence (master directive 2026-10-09 §6):
  kind     'live' = a real run on the deployed system with an id a reader can
           look up; 'unit' = tests only
  ref      run/build/version id or test path
  commit   the code that ran (worker deploy SHA at the time; CI head SHA).
           The auditor marks live evidence STALE when the binding's
           implementation files changed after this commit.
  env      worker-host | workspace (founder, deployed) | ci | local
  asserts  what the run actually checked -- the VERIFIED scope. One run backs
           several roles only through what it asserted for each.
A role missing from this file is DEFINED and nothing more.

Edit rules: never add 'live' evidence without an id from a real run and its
commit; never widen `verified_scope` beyond what `asserts` checked; never mark
a gap closed without evidence; keep `gaps` honest.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Evidence:
    kind: str  # 'live' | 'unit'
    ref: str   # build/run/version id, STATUS section or test path
    note: str = ''
    commit: str = ''
    env: str = ''
    asserts: tuple[str, ...] = ()


@dataclass(frozen=True)
class Requirement:
    names: tuple[str, ...]  # environment variable names, or a service name
    observed: str = ''      # where presence was observed (deploy notice, probe run); '' = not observed


@dataclass(frozen=True)
class Binding:
    role: str                       # agent_catalog key
    implementation: tuple[str, ...]  # 'module:Symbol' or 'path:<repo file>'
    scope: str                      # product family/path this binding covers
    config: tuple[Requirement, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    cost: str = ''
    gaps: tuple[str, ...] = field(default_factory=tuple)
    blocked_by: str = ''            # set when a named credential/service is missing
    verified_scope: tuple[str, ...] = ()  # the narrow claims the live evidence supports


_MODEL = Requirement(('GEMINI_API_KEY', 'OMNI_MODEL_CATALOG_JSON'),
                     'deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok')
_SANDBOX = Requirement(('OMNI_SANDBOX_RUNNER_URL', 'OMNI_SANDBOX_SHARED_SECRET'), 'deploy-worker sandbox probe PASS (every deploy)')
_DB = Requirement(('OMNI_DATABASE_URL',), 'deploy-worker migrations + queue probe PASS')
_S3 = Requirement(('OMNI_S3_ENDPOINT', 'OMNI_S3_BUCKET', 'OMNI_S3_ACCESS_KEY', 'OMNI_S3_SECRET_KEY'), 'deploy-worker storage probe PASS')
_REDIS = Requirement(('OMNI_REDIS_URL',), 'deploy-worker queue probe PASS')

# Commits: the worker deploy that was live when the run happened (deploy-worker
# run list, 2026-10-08/09), or the run's own head for CI/deploy runs.
_FOUNDER_BUILD = Evidence('live', 'bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39',
                          'founder build from the workspace, 2026-10-08 21:30-21:35, quality 84', 'beb67b4', 'workspace',
                          ('prompt -> build contract (task list)', 'model-generated code', 'sandbox tests passed',
                           'version committed to R2', 'preview served a real UI'))
_FOUNDER_CHANGE = Evidence('live', 'mod_c14435dc9baa44bdac784d0c15ed9b85 -> v_0bc82ef7b33b4210',
                           'natural-language change accepted 2026-10-08 22:55; spec A1-A6', '3a4d822', 'workspace',
                           ('change classified and applied', 'tests passed on the new version', 'version promoted on accept'))
_REHEARSAL = Evidence('live', 'golden-rehearsal run 37820429767', 'task-list prompt: ready, quality 86, 2 min', '782dafd',
                      'worker-host', ('prompt -> ready build (task list)', 'quality gate >= 80'))
_E2E = Evidence('live', 'STATUS.md "Golden E2E #1: full chain from the founder\'s workspace" (2026-10-08 23:05)', '', '3a4d822',
                'workspace', ('login -> plan -> build -> preview -> change -> accept -> ZIP',))
_LIBRARY = Evidence('live', 'bld_8263a2a1905346399747f4fe8b92e919 -> v_f65e904334b04776',
                    'founder library build 2026-10-09 02:30; HTTP behaviour probes passed', 'b0a0cfa', 'workspace',
                    ('prompt -> ready build (library, business rules)', 'HTTP acceptance: create/read/conflict/return/delete'))

WEB = 'web/self_contained_v1'

BINDINGS: tuple[Binding, ...] = (
    Binding('request_interpreter',
            ('omni_prod.product_architect:ProductArchitect', 'omni_prod.autonomous_agents:ArchitectAgent'),
            WEB, (_MODEL,), (_FOUNDER_BUILD, _REHEARSAL, _LIBRARY), 'one model call per build (~$0.005)',
            ('no discovery conversation: at most one heuristic question (see discovery_lead)',
             'planner adds login/roles although the request says "no login"'),
            verified_scope=('a Hebrew prompt becomes a build contract for a single-page web app',)),
    Binding('product_analyst', ('omni_prod.autonomous_agents:ArchitectAgent',), WEB, (_MODEL,),
            (_FOUNDER_BUILD, _FOUNDER_CHANGE), 'shared with request_interpreter',
            ('acceptance criteria only; no user stories or edge-case analysis',),
            verified_scope=('acceptance criteria A1..An derived for the requested product',)),
    Binding('capability_resolver', ('omni_prod.capability_planner:CapabilityPlanner', 'omni_prod.build_contract:BuildContract'),
            WEB, (_DB,), (_FOUNDER_BUILD,), '$0 (deterministic)',
            ('keyword-based game detection misclassifies "משחק" (football match)',),
            verified_scope=('web/self_contained_v1 capabilities resolved and bound into the contract',)),
    Binding('solution_architect', ('omni_prod.autonomous_agents:ArchitectAgent', 'omni_prod.dependency_policy:GENERATION_CONSTRAINTS'),
            WEB, (_MODEL,), (_FOUNDER_BUILD,), 'shared with request_interpreter',
            ('one fixed stack (Python stdlib + SQLite in /tmp); no durable data or API-contract design',),
            verified_scope=('the fixed stdlib stack is planned consistently',)),
    Binding('project_orchestrator',
            ('omni_prod.worker_tasks:_run_live_build_job', 'omni_prod.autonomous_core:AutonomousProductEngine', 'omni_prod.worker:main'),
            WEB, (_REDIS, _DB), (_FOUNDER_BUILD, _E2E), '$0 (deterministic)',
            ('fixed 4-step pipeline, not a task graph', 'no cancel', 'no resume of a half-finished build (janitor fails it)'),
            verified_scope=('the fixed build pipeline runs to ready',)),
    Binding('cost_controller',
            ('omni_prod.routed_gateway:RoutedModelGateway', 'omni_prod.subscription_store:PostgresSubscriptionService',
             'omni_prod.qa_budget:qa_used_usd'),
            WEB, (_DB,), (Evidence('live', 'build-evidence run 37864934013', 'QA counted all-time $3.31', 'd8a01fa', 'worker-host',
                                   ('QA spend counted from recorded spend, reservation at most once per build',)),
                          Evidence('unit', 'tests/test_provider_quota_and_dialects.py'),
                          Evidence('unit', 'tests/test_qa_budget.py', 'a start date needs free-tier evidence')),
            '$0 (deterministic)', ('no per-step cost shown to the user', 'no provider invoice reconciliation',
                                   'spend ledger is tokens x catalog price, not a supplier-confirmed cost'),
            verified_scope=('QA budget cap enforced before a build is admitted',)),
    Binding('frontend_developer', ('omni_prod.autonomous_agents:GeneratorAgent',), WEB, (_MODEL,),
            (_FOUNDER_BUILD, _FOUNDER_CHANGE, _LIBRARY), 'part of ~$0.07 per build',
            ('generated library hid every message after the first (found by the browser check, 2026-10-09)',
             'UI quality gaps found by the founder: alert() errors, ISO dates, hidden filter state'),
            verified_scope=('single-page HTML/JS UI wired to JSON endpoints',)),
    Binding('backend_developer', ('omni_prod.autonomous_agents:GeneratorAgent',), WEB, (_MODEL,),
            (_FOUNDER_BUILD, _FOUNDER_CHANGE, _LIBRARY), 'shared with frontend_developer',
            ('input validation only when the user asks for it', 'data in /tmp (not durable)'),
            verified_scope=('stdlib HTTP JSON API with SQLite in /tmp',)),
    Binding('repository_maintainer',
            ('omni_prod.workspace:PostgresProjectWorkspace', 'omni_prod.storage:S3ArtifactStore',
             'omni_prod.spec_repository:restore_version_with_spec'),
            WEB, (_DB, _S3), (_FOUNDER_CHANGE, Evidence('live', 'ZIP of v_0bc82ef7b33b4210 opened by the founder 2026-10-08 22:59',
                                                        '', '3a4d822', 'workspace', ('export ZIP of a promoted version',))),
            '$0', (), verified_scope=('versions committed, promoted and exported as ZIP',)),
    Binding('qa_verifier',
            ('omni_prod.remote_sandbox:RemoteSandboxRepositoryExecutor', 'omni_prod.preview_smoke:PreviewReadyExecutor',
             'omni_prod.quality_gate:QualityAwareExecutor', 'omni_prod.product_review:ProductReviewExecutor',
             'omni_prod.browser_probe:BrowserFlowExecutor', 'omni_prod.web_saas_acceptance:WebSaaSAcceptanceRunner'),
            WEB, (_SANDBOX, _MODEL), (_FOUNDER_BUILD, _REHEARSAL, _LIBRARY,
                                      Evidence('live', 'golden-rehearsal run 37841459920',
                                               'skills on: QA review round 1 by gemini-3.8-flash, 0 blocking; ready, quality 86',
                                               'dbd1232', 'worker-host', ('model review of the code against skill checklists',)),
                                      Evidence('live', 'deploy-worker run 37864475043', 'browser-probe PASS both ways on the host',
                                               'd8a01fa', 'worker-host',
                                               ('real browser: working fixture passes, vanishing-message fixture caught',))),
            'one review call per round (~$0.01); browser check $0',
            ('same model vendor writes and reviews (allowed by directive §17; separate run)',
             'browser check not yet exercised inside a founder build',
             'no screenshots or visual inspection yet'),
            verified_scope=('sandbox unit tests', 'HTTP behaviour probes', 'preview start', 'quality score',
                            'browser flow on fixtures')),
    Binding('security_reviewer', ('omni_prod.security_testing:hostile_repository_scan', 'omni_prod.worker_tasks:evaluate_release_gates'),
            WEB, (), (_FOUNDER_BUILD,), '$0', ('static scan only; no authorization testing of the generated app',),
            verified_scope=('static hostile-pattern scan gates release',)),
    Binding('repair_agent', ('omni_prod.autonomous_agents:RepairAgent',), WEB, (_MODEL, _SANDBOX),
            (_FOUNDER_BUILD, Evidence('live', 'golden-rehearsal run 37814985551', '5 repair rounds converged', 'ff6b4f6', 'worker-host',
                                      ('failed checks repaired until tests pass',))),
            'part of ~$0.07 per build', ('repairs the whole repository rather than a minimal patch',),
            verified_scope=('failing sandbox tests repaired within the round limit',)),
    Binding('preview_operator',
            ('omni_prod.preview_runtime:DockerPreviewProvider', 'omni_prod.preview_router:make_handler',
             'omni_prod.preview_repository:PostgresPreviewRepository'),
            WEB, (Requirement(('PREVIEW_DOMAIN_TEMPLATE', 'OMNI_PREVIEW_HOST_SUFFIX'), 'deploy-worker "Preview edge is up" PASS'),),
            (Evidence('live', 'https://prv-1760dedc67864c0186aa0cdf945bab0d.151-145-89-132.sslip.io',
                      'v_246bae81234e4c39 shown in the workspace', 'beb67b4', 'workspace', ('preview served and routed',)),
             Evidence('unit', 'tests/test_golden_mod_path_live_postgres.py::test_preview_acceptance_report_is_recorded_on_real_postgres',
                      'acceptance recording fixed 2026-10-09 (library preview was torn down)')),
            '$0 (worker host)', ('data in /tmp is lost when the preview stops', 'temporary sslip.io address, open to anyone with the link',
                                 'acceptance recording fix not yet seen on a founder preview'),
            verified_scope=('preview container started and routed over HTTPS',)),
    Binding('operations_agent', ('omni_prod.maintenance:run_once',), 'platform', (_DB,),
            (Evidence('unit', 'tests/test_maintenance_live_postgres.py'), Evidence('live', 'deploy-worker "janitor started"', '',
                                                                                   'd8a01fa', 'worker-host', ('janitor process running',))),
            '$0', ('no alerting', 'no health monitoring of generated products'),
            verified_scope=('janitor runs',)),
    Binding('release_change_coordinator',
            ('path:.github/workflows/deploy-worker.yml', 'omni_prod.job_repository:PostgresBuildRepository.claim_contract_build'),
            'platform', (),
            (Evidence('live', 'deploy-worker run 37862903906', 'drained 213 s for a running job, exit 0', '51bb631', 'worker-host',
                      ('a deploy waits for the running job before replacing anything',)),
             Evidence('live', 'deploy-worker run 37864475043 + build bld_e204320872c8',
                      'founder build finished ready while the deploy drained 65 s', 'd8a01fa', 'worker-host',
                      ('a real build survives a deploy',)),
             Evidence('unit', 'tests/test_golden_mod_path_live_postgres.py::test_two_parallel_approvals_of_one_plan_create_one_build')),
            '$0', ('branch ownership is a written rule, not enforced by a tool', 'no rollback step in the workflow'),
            verified_scope=('no worker replacement mid-job',)),
    Binding('discovery_lead', ('omni_prod.discovery:next_group', 'omni_prod.discovery:answer',
                               'omni_prod.brief_repository:PostgresBriefRepository'), WEB, (_DB,),
            (Evidence('unit', 'tests/test_discovery_and_approval.py', 'engine + live-Postgres revisions and approvals'),),
            '$0 (deterministic)', ('not yet used by the founder in the workspace', 'a fixed question bank; no model phrasing',
                                   'domains: web apps/business systems only'),),
    Binding('visual_creator', ('omni_prod.providers.image_provider:PredictionImageProvider',), 'assets',
            (Requirement(('REPLICATE_API_TOKEN',), 'Replicate authentication live-verified on Preview (STATUS 2026-10-06)'),),
            (Evidence('unit', 'tests/test_replicate_image_test.py'),), 'about $0.003 per image (FLUX Schnell list price)',
            ('no image has been generated live yet', 'not on the build path')),
    Binding('registry_auditor', ('omni_prod.registry_audit:audit',), 'platform', (),
            (Evidence('unit', 'tests/test_registry_audit.py'),), '$0', ()),
    Binding('provider_evaluator', ('omni_prod.model_probe:probe', 'omni_prod.rehearsal:cost_projection'), 'platform', (_MODEL,),
            (Evidence('live', 'model-probe run 37814803770', '3 Gemini models ok; OpenAI/Anthropic refused: no credit', 'ff6b4f6',
                      'worker-host', ('availability of each catalog model',)),),
            '< $0.001 per probe', ('no quality benchmark across providers yet',),
            verified_scope=('model availability probe',)),
)

BY_ROLE = {b.role: b for b in BINDINGS}


@dataclass(frozen=True)
class SkillBinding:
    key: str                         # omni_prod.skills_runtime skill key
    evidence: tuple[Evidence, ...] = ()
    gaps: tuple[str, ...] = ()


_SKILLS_REHEARSAL = Evidence('live', 'golden-rehearsal run 37841459920',
                             'skills_applied recorded in the build; QA review against their checklists, 0 blocking',
                             'dbd1232', 'worker-host', ('guidance injected', 'model review found no blocking issue'))

SKILL_BINDINGS: tuple[SkillBinding, ...] = (
    SkillBinding('skill.request_fidelity', (_SKILLS_REHEARSAL,),
                 ('the plan view still lists "login and sessions" from ProductArchitect for a "no login" request',)),
    SkillBinding('skill.form_validation', (_SKILLS_REHEARSAL,), ('no HTTP probe sends invalid input to the running app yet',)),
    SkillBinding('skill.ui_states', (_SKILLS_REHEARSAL,), ('checked by code review and the browser flow check; no screenshots',)),
    SkillBinding('skill.text_locale', (_SKILLS_REHEARSAL,), ()),
    SkillBinding('skill.data_integrity', (_SKILLS_REHEARSAL,), ('no conflict/404 probe against the running app yet',)),
    SkillBinding('skill.visual_design', (Evidence('live', 'golden-rehearsal run 37858017258',
                                                  'library prompt: ready, quality 86, design static check passed, review 0 blocking',
                                                  '727af63', 'worker-host', ('CSS heuristic passed', 'model review 0 blocking')),),
                 ('checked by a CSS heuristic and code review, not by looking at a screenshot (directive §11: not a design approval)',
                  'not yet seen by the founder in a preview')),
)
SKILL_BY_KEY = {b.key: b for b in SKILL_BINDINGS}
assert len(BY_ROLE) == len(BINDINGS), 'one binding per role'
