"""Agent OS: the 52 agents of the autonomous completion directive (§7, §8) as
full AgentContracts. Implementation and evidence are named per agent; an
agent without real code is NOT_IMPLEMENTED (status computed by the audit).

Several agents share code (one generator call writes frontend and backend).
That is allowed and explicit: the contract names the shared code and the
agent's own responsibility; the audit never infers more than the evidence
asserted.
"""
from __future__ import annotations

from ..runtime_bindings import Evidence
from .contracts import AgentContract
from .evidence import BACKUP, CRASH, DEPLOY, FREE, PAID, REHEARSAL_ACCEPT

U = lambda path: Evidence('unit', path)  # noqa: E731

_POLICY = {
    'provider': 'COMMERCIAL_APPROVED providers only for paying customers; cheapest model meeting the task quality floor',
    'budget': 'spends only inside the build reservation; stops with model_budget_exhausted at the ceiling',
    'memory': 'no long-term memory beyond the project (contract, versions, events); never stores secrets',
    'state': 'durable task state in agent_tasks; resumes by re-running the task after a crash',
    'handoff': 'structured handoff record (from task, to agent, payload refs) before the next agent starts',
    'retry': 'bounded by the build repair rounds; transient provider errors retried by the router',
    'timeout': 'model call <= 300 s, sandbox run <= 180-200 s, whole build job <= 15 min',
    'escalation': 'unrecoverable failure -> build FAILED with the exact reason shown to the user',
    'approval': 'acts only on a server-bound approval of the brief, plan and price',
}

# key, name, category, purpose, responsibility, allowed skills, verifier, implementation, evidence, extra
_SPECS = [
    # ---- core product / software ------------------------------------------------
    ('executive_orchestrator', 'Executive Orchestrator', 'management', 'run the whole build as a task graph',
     'decides the order of agents and stops the run on failure or cancel',
     ('build_plan_generation', 'task_decomposition', 'agent_assignment', 'job_cancel'), 'quality_gate_agent',
     ('omni_prod.autonomous_core:AutonomousProductEngine', 'omni_prod.worker_tasks:_run_live_build_job', 'omni_prod.agent_os.runtime:AgentRuntime'),
     (PAID, CRASH), {}),
    ('discovery_agent', 'Discovery Agent', 'management', 'professional discovery conversation',
     'asks only what is missing, records delegated choices and contradictions',
     ('intent_classification', 'ambiguity_detection', 'smart_question_generation', 'safe_default_selection'),
     'requirements_traceability', ('omni_prod.discovery:start', 'omni_prod.discovery:answer'), (PAID,), {}),
    ('requirements_agent', 'Requirements Agent', 'management', 'turn the brief into binding requirements',
     'writes the requirements block and acceptance criteria the build is held to',
     ('requirement_extraction', 'functional_requirement_generation', 'acceptance_criteria_generation', 'scope_detection'),
     'requirements_traceability', ('omni_prod.discovery:requirements_text', 'omni_prod.product_architect:ProductArchitect'),
     (PAID, REHEARSAL_ACCEPT), {}),
    ('product_planner', 'Product Planner', 'management', 'plan and price the build',
     'compiles the build contract and the conservative quote', ('build_plan_generation', 'cost_estimation', 'capability_closure'),
     'cost_economics_agent', ('omni_prod.creator_plan:build_plan_preview', 'omni_prod.build_cost_plan:build_economics_quote'), (PAID,), {}),
    ('architecture_agent', 'Architecture Agent', 'software', 'design the product structure and tests',
     'writes the ProductSpec (modules, acceptance) the code must satisfy', ('stack_selection', 'data_model_design', 'api_contract_design'),
     'code_review_agent', ('omni_prod.autonomous_agents:ArchitectAgent',), (REHEARSAL_ACCEPT,), {}),
    ('ux_ui_design_agent', 'UX/UI Design Agent', 'software', 'screens, states and design system',
     'shapes the interface through design skills injected into generation and review',
     ('design_system_generation', 'form_design', 'empty_state_design', 'error_state_design', 'responsive_layout', 'rtl_design'),
     'browser_rehearsal_agent', ('omni_prod.skills_runtime:VISUAL_DESIGN', 'omni_prod.skills_runtime:UI_STATES'), (PAID,), {}),
    ('frontend_agent', 'Frontend Agent', 'software', 'the user interface code', 'pages, forms and API bindings',
     ('page_generation', 'form_generation', 'client_validation', 'api_binding'), 'browser_rehearsal_agent',
     ('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), {}),
    ('backend_agent', 'Backend Agent', 'software', 'the server code', 'endpoints, validation and business rules',
     ('api_endpoint_generation', 'request_validation', 'business_logic_generation'), 'behavioral_acceptance_agent',
     ('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), {}),
    ('database_agent', 'Database Agent', 'software', 'product data storage', 'schema, integrity and persistence of the product data',
     ('schema_generation', 'data_integrity_validation', 'persistence_verification', 'data_isolation'), 'qa_agent',
     ('omni_prod.autonomous_agents:GeneratorAgent', 'omni_prod.preview_runtime:project_data_dir'), (REHEARSAL_ACCEPT, FREE), {}),
    ('identity_auth_agent', 'Identity & Authentication Agent', 'software', 'sign-in for generated products',
     'adds sign-in only when approved; platform identity lives in the platform', ('signup', 'login', 'session_management'),
     'security_agent', (), (), {'gap': 'generated-app auth is not generated or verified; platform identity only'}),
    ('integration_agent', 'Integration Agent', 'software', 'external integrations of generated products',
     'connectors with secret references', ('api_connector_generation', 'oauth_connector'), 'security_agent', (), (),
     {'gap': 'no generated-app integration path'}),
    ('coding_agent', 'Coding Agent', 'software', 'write and change code', 'creates and modifies repository files',
     ('file_create', 'file_modify', 'repository_patch_application', 'dependency_add'), 'code_review_agent',
     ('omni_prod.autonomous_agents:GeneratorAgent', 'omni_prod.autonomous_agents:RepairAgent'), (REHEARSAL_ACCEPT,), {}),
    ('code_review_agent', 'Code Review Agent', 'quality', 'review generated code independently',
     'model review against the skills checklists; blocking findings go back to repair', ('xss_check',), 'qa_agent',
     ('omni_prod.product_review:ProductReviewExecutor',), (PAID, REHEARSAL_ACCEPT), {}),
    ('qa_agent', 'QA Agent', 'quality', 'run the product tests', 'executes tests in the isolated sandbox',
     ('unit_test_execution', 'persistence_test', 'negative_test'), 'quality_gate_agent',
     ('omni_prod.remote_sandbox:RemoteSandboxRepositoryExecutor', 'omni_prod.quality_gate:QualityAwareExecutor'),
     (REHEARSAL_ACCEPT, DEPLOY), {}),
    ('browser_rehearsal_agent', 'Browser Rehearsal Agent', 'quality', 'use the product in a real browser',
     'fills and submits forms, catches JS errors and vanishing feedback', ('browser_launch', 'form_test', 'javascript_error_detection'),
     'quality_gate_agent', ('omni_prod.browser_probe:BrowserFlowExecutor',), (PAID, DEPLOY, REHEARSAL_ACCEPT), {}),
    ('behavioral_acceptance_agent', 'Behavioral Acceptance Agent', 'quality', 'prove the promised behaviour over HTTP',
     'runs the acceptance plan on the started app; failures feed repair', ('behavioral_acceptance_test', 'api_test', 'requirement_traceability_test'),
     'quality_gate_agent', ('omni_prod.behavior_acceptance:BehaviorAcceptanceExecutor',), (REHEARSAL_ACCEPT,), {}),
    ('repair_agent', 'Repair Agent', 'quality', 'fix what failed', 'minimal patch from the failure evidence',
     ('failure_classification', 'minimal_patch_generation', 'repair_execution'), 'qa_agent',
     ('omni_prod.autonomous_agents:RepairAgent',), (REHEARSAL_ACCEPT,), {}),
    ('security_agent', 'Security Agent', 'quality', 'security gate', 'static hostile scan and preview access control',
     ('secret_detection', 'preview_access_check', 'security_release_gate'), 'quality_gate_agent',
     ('omni_prod.security_testing:hostile_repository_scan', 'omni_prod.preview_access:PreviewAccess'), (PAID, FREE), {}),
    ('compliance_ip_agent', 'Compliance & IP Agent', 'quality', 'rights and commercial terms',
     'rights assessment and provider commercial status', ('copyright_risk_detection', 'commercial_provider_validation'),
     'quality_gate_agent', ('omni_prod.rights_ip:RightsEngine', 'omni_prod.agent_os.providers:commercial_status'), (PAID,), {}),
    ('provider_router_agent', 'Provider Router Agent', 'platform', 'choose a model per call', 'price/quality routing with fallback',
     ('provider_selection', 'provider_fallback_selection', 'model_selection', 'provider_cost_compare'), 'compliance_ip_agent',
     ('omni_prod.routed_gateway:RoutedModelGateway',), (PAID, REHEARSAL_ACCEPT), {}),
    ('cost_economics_agent', 'Cost & Economics Agent', 'platform', 'quote, reserve, meter, settle',
     'never charges more than measured usage when usage is known', ('build_quote', 'credit_reservation', 'actual_cost_calculation', 'credit_settlement'),
     'quality_gate_agent', ('omni_prod.worker_tasks:resolve_m5_billing', 'omni_prod.worker_tasks:metered_llm_cost'), (CRASH, PAID), {}),
    ('infrastructure_agent', 'Infrastructure Agent', 'platform', 'workers, queue, storage health',
     'keeps the build infrastructure healthy and recovers stranded work', ('worker_health_check', 'queue_health_check', 'stale_job_recovery'),
     'sre_reliability_agent', ('omni_prod.maintenance:run_once', 'omni_prod.maintenance:recover_lost_running'), (CRASH, DEPLOY), {}),
    ('deployment_agent', 'Deployment Agent', 'platform', 'previews of generated products', 'private, persistent previews on the host',
     ('preview_deploy', 'preview_health_check', 'preview_access_protect'), 'release_agent',
     ('omni_prod.preview_runtime:DockerPreviewProvider', 'omni_prod.preview_router:make_handler'), (FREE,), {}),
    ('release_agent', 'Release Agent', 'platform', 'versions and release gates', 'commits a version only when gates pass',
     ('version_create', 'artifact_commit', 'release_gate'), 'quality_gate_agent',
     ('omni_prod.worker_tasks:evaluate_release_gates', 'omni_prod.workspace:PostgresProjectWorkspace.commit'), (PAID,),
     {'gap': 'no publishing to a live customer domain'}),
    ('observability_agent', 'Observability Agent', 'platform', 'traces and the live journal', 'every step is visible to the owner',
     ('execution_trace', 'provider_trace', 'cost_trace', 'agent_trace'), 'sre_reliability_agent',
     ('omni_prod.build_control:BuildControl', 'omni_prod.attempt_ledger:persist_attempts'), (FREE, PAID), {}),
    ('sre_reliability_agent', 'SRE / Reliability Agent', 'platform', 'no work lost', 'drain on deploy, crash recovery, lost-queue redispatch',
     ('job_resume', 'stale_job_recovery'), 'quality_gate_agent', ('path:.github/workflows/deploy-worker.yml', 'omni_prod.maintenance:recover_lost_running'),
     (CRASH, DEPLOY), {}),
    ('backup_recovery_agent', 'Backup & Recovery Agent', 'platform', 'backups proven by restore', 'daily backup + restore drill',
     ('database_backup', 'project_backup', 'restore_verification'), 'quality_gate_agent', ('omni_prod.backup:verify',), (BACKUP,), {}),
    ('migration_agent', 'Migration Agent', 'platform', 'platform schema changes', 'additive migrations with checksum ledger',
     ('migration_validation', 'migration_test'), 'backup_recovery_agent', ('omni_prod.migrate:main',), (DEPLOY,), {}),
    ('performance_agent', 'Performance Agent', 'quality', 'speed and load', 'measures latency/load of generated products', ('latency_analysis', 'load_test', 'frontend_performance_test'), 'quality_gate_agent', (), (), {'gap': 'not implemented'}),
    ('accessibility_agent', 'Accessibility Agent', 'quality', 'accessible products', 'labels, contrast, keyboard',
     ('label_test', 'contrast_test'), 'qa_agent', ('omni_prod.skills_runtime:FORM_VALIDATION',), (PAID,), {'gap': 'instructions + review only; no automated a11y test'}),
    ('localization_rtl_agent', 'Localization / RTL Agent', 'quality', 'Hebrew/RTL and locale formats', 'language, direction, dates',
     ('hebrew_localization', 'rtl_layout', 'locale_date'), 'qa_agent', ('omni_prod.skills_runtime:TEXT_LOCALE',), (PAID,), {}),
    ('seo_web_quality_agent', 'SEO / Web Quality Agent', 'quality', 'metadata and web quality', 'titles, descriptions, sitemaps', ('metadata_generation', 'sitemap_generation', 'seo_validation'), 'qa_agent', (), (), {'gap': 'not implemented'}),
    ('analytics_agent', 'Analytics Agent', 'platform', 'product analytics', 'event schema with consent', ('event_schema_generation', 'event_tracking', 'usage_metric'), 'privacy_reviewer', (), (), {'gap': 'not implemented'}),
    ('product_evolution_agent', 'Product Evolution Agent', 'software', 'change an existing product', 'classifies and applies a natural-language change, keeps the rest',
     ('file_modify',), 'qa_agent', ('omni_prod.modification_engine:CandidateModificationEngine', 'omni_prod.autonomous_agents:ChangeClassifierAgent'),
     (Evidence('live', 'mod_c14435dc9baa44bdac784d0c15ed9b85 -> v_0bc82ef7b33b4210', 'founder change accepted 2026-10-08', '3a4d822', 'workspace',
               ('change classified and applied', 'tests passed on the new version')),), {}),
    ('automation_agent', 'Automation Agent', 'automation', 'workflows and triggers', 'generates scheduled/webhook workflows', ('trigger_definition', 'schedule_definition', 'workflow_test'), 'qa_agent', (), (), {'gap': 'not implemented'}),
    # ---- media ---------------------------------------------------------------------
    ('media_orchestrator', 'Media Orchestrator', 'media', 'plan media assets', 'decides which assets a product needs',
     ('video_brief', 'brand_consistency'), 'compliance_ip_agent', ('omni_prod.media_pipeline:CreativeDirector',), (U('tests/test_m495_worker_capabilities.py'),), {}),
    ('image_agent', 'Image Agent', 'media', 'generate images', 'icons and visuals through a commercial provider',
     ('text_to_image', 'image_quality_check'), 'compliance_ip_agent', ('omni_prod.providers.image_provider:PredictionImageProvider',),
     (U('tests/test_replicate_image_test.py'),), {'config': ('OMNI_IMAGE_PROVIDER_BASE_URL', 'OMNI_IMAGE_PROVIDER_API_KEY_REF')}),
    ('video_agent', 'Video Agent', 'media', 'generate video', 'scripted video through a commercial provider', ('text_to_video', 'video_render', 'video_quality_check'), 'compliance_ip_agent', (), (),
     {'blocked_by': 'no commercial video provider contracted'}),
    ('voice_speech_agent', 'Voice & Speech Agent', 'media', 'speech in and out', 'TTS/STT through a commercial provider', ('text_to_speech', 'speech_to_text', 'speech_quality_check'), 'compliance_ip_agent', (), (),
     {'blocked_by': 'no commercial speech provider configured'}),
    ('audio_music_agent', 'Audio / Music Agent', 'media', 'music and sound', 'licensed music/SFX', ('music_generation', 'sound_effect_generation', 'music_license_check'), 'compliance_ip_agent', (), (),
     {'blocked_by': 'no commercially licensed music provider contracted'}),
    # ---- 2D games ----------------------------------------------------------------------
    ('game_designer_2d_agent', '2D Game Designer Agent', 'games', 'game concept and rules', 'genre, loop, win/lose', ('game_concept', 'game_loop_design', 'genre_rules'), 'game_qa_2d_agent', (), (), {'gap': 'not implemented'}),
    ('level_designer_2d_agent', '2D Level Designer Agent', 'games', 'levels', 'level layout and progression', ('level_system', 'progression_system', 'difficulty_system'), 'game_qa_2d_agent', (), (), {'gap': 'not implemented'}),
    ('game_engineering_2d_agent', '2D Game Engineering Agent', 'games', 'Phaser/Canvas game code', 'implements the playable game', ('player_movement', 'collision', 'score_system', 'restart'), 'game_qa_2d_agent', (), (),
     {'gap': 'no game pipeline; Phaser is not in the sandbox allowlist'}),
    ('game_qa_2d_agent', '2D Game QA Agent', 'games', 'play the game in a browser', 'controls, collision, scoring, restart', ('gameplay_test', 'level_completion_test', 'save_load_test'), 'quality_gate_agent', (), (), {'gap': 'not implemented'}),
    # ---- support ------------------------------------------------------------------------
    ('diagnostic_agent', 'Diagnostic Agent', 'platform', 'diagnose failures', 'collects logs/evidence for a failed run',
     ('failure_trace', 'execution_trace'), 'sre_reliability_agent', ('path:.github/workflows/worker-diagnostics.yml', 'path:.github/workflows/build-evidence.yml'), (DEPLOY,), {}),
    ('support_agent', 'Support Agent', 'platform', 'answer customers', 'explains failures and next steps', ('incident_creation',), 'customer_success', (), (), {'gap': 'not implemented'}),
    # ---- meta agents that verify 148AI itself (§8) ---------------------------------------
    ('platform_capability_auditor', 'Platform Capability Auditor', 'meta', 'claims vs reality',
     'computes every agent/skill status from code, configuration and fresh evidence; downgrades stale claims', ('regression_test',),
     'quality_gate_agent', ('omni_prod.agent_os.audit:audit',), (U('tests/test_agent_os.py'),), {}),
    ('regression_guardian', 'Regression Guardian', 'meta', 'protect what works',
     'compares every test result with the committed regression matrix; a new failure blocks progress', ('regression_test',),
     'quality_gate_agent', ('omni_prod.agent_os.meta:regression_guardian',), (U('tests/test_agent_os.py'),), {}),
    ('golden_path_verifier', 'Golden Path Verifier', 'meta', 'end-to-end journeys on the real system',
     'runs the golden journeys against the deployed platform and records the results', ('deployment_verification', 'cancellation_test', 'resume_test'),
     'quality_gate_agent', ('omni_prod.postdeploy_checks:main', 'path:.github/workflows/postdeploy-checks.yml'), (FREE, PAID, CRASH), {}),
    ('system_test_orchestrator', 'System Test Orchestrator', 'meta', 'which test layers a change needs',
     'maps changed files to the required layers; unit-only evidence never completes a feature', ('regression_test', 'requirement_traceability_test'), 'quality_gate_agent',
     ('omni_prod.agent_os.meta:required_layers',), (U('tests/test_agent_os.py'),), {}),
    ('failure_injection_agent', 'Failure Injection Agent', 'meta', 'prove graceful failure',
     'injects provider/DB/queue/worker/budget/token/artifact failures; real kill and drain on the host', ('provider_failure_test',),
     'quality_gate_agent', ('omni_prod.agent_os.meta:failure_injection',), (CRASH, U('tests/test_failure_injection.py')), {}),
    ('quality_gate_agent', 'Quality Gate Agent', 'meta', 'final platform gate',
     'a milestone is VERIFIED only with tests, no regressions, security, acceptance, cost, recovery and truthful registries',
     ('security_release_gate', 'release_gate'), '', ('omni_prod.agent_os.meta:quality_gate',), (U('tests/test_agent_os.py'),), {}),
]

# Roles referenced as verifiers that live in the older catalog (directive 2026-10-09 §8).
_EXTRA_VERIFIERS = {'requirements_traceability', 'privacy_reviewer', 'customer_success'}


def _contract(spec) -> AgentContract:
    key, name, category, purpose, responsibility, skills, verifier, impl, evidence, extra = spec
    return AgentContract(
        agent_key=key, name=name, version='1', category=category, identity=f'148AI {name}',
        purpose=purpose, unique_responsibility=responsibility,
        when_invoked=f'when the task graph reaches a {name} task',
        trigger_conditions=(f'a task assigned to {key} becomes READY',),
        required_inputs=('approved build contract', 'task input refs'), outputs=('task result', 'evidence'),
        allowed_skills=tuple(skills), forbidden_skills=(),
        allowed_tools=('sandbox runner', 'model router', 'platform database') if impl else ('none',),
        forbidden_actions=('approve its own output', 'spend outside the reservation', 'read or print secrets',
                           'publish without the release gate'),
        permissions=('read contract and project', 'write own task state and evidence'),
        provider_policy=_POLICY['provider'], budget_policy=_POLICY['budget'], memory_policy=_POLICY['memory'],
        state_policy=_POLICY['state'], handoff_policy=_POLICY['handoff'], retry_policy=_POLICY['retry'],
        timeout_policy=_POLICY['timeout'], escalation_policy=_POLICY['escalation'], approval_policy=_POLICY['approval'],
        success_criteria=(f'{responsibility}; accepted by {verifier or "the founder"}',),
        failure_criteria=('verification rejected', 'timeout', 'budget exhausted'),
        verifier=verifier, verification_tests=tuple(e.ref for e in evidence) or ('none',),
        observability_requirements=('task row with state transitions', 'journal line per step', 'cost per call'),
        security_requirements=('no secrets in evidence', 'owner/tenant scoping on every read'),
        commercial_constraints=('COMMERCIAL_APPROVED providers only for customer work',),
        implementation_location=tuple(impl), config=tuple(extra.get('config', ())), blocked_by=extra.get('blocked_by', ''),
        evidence=tuple(evidence),
    )


AGENTS: tuple[AgentContract, ...] = tuple(_contract(s) for s in _SPECS)
BY_KEY = {a.agent_key: a for a in AGENTS}
GAPS = {s[0]: s[9].get('gap', '') for s in _SPECS}

# Separation of duties (§13): producer -> required independent verifiers.
SEPARATION_OF_DUTIES = {
    'coding_agent': ('code_review_agent', 'qa_agent'),
    'deployment_agent': ('release_agent',),
    'migration_agent': ('qa_agent', 'backup_recovery_agent'),
    'provider_router_agent': ('compliance_ip_agent',),
    'game_engineering_2d_agent': ('game_qa_2d_agent',),
}
