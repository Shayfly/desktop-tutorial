"""Skills OS: every skill of the autonomous completion directive §9 (427 keys
in 33 categories, `skills_taxonomy.json`), as a full SkillContract.

Implementation, evidence and gaps are declared per skill in IMPL below and
only there. A skill that has no entry has no code on a real path: it is
NOT_IMPLEMENTED, explicitly -- never a name with a status attached.
Category templates fill the descriptive fields (who runs it, who verifies
it, data and commercial policy); they do not make a skill exist.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..runtime_bindings import Evidence
from .contracts import SkillContract
from .evidence import BACKUP, CRASH, DEPLOY, FREE, PAID, REHEARSAL_ACCEPT

TAXONOMY: dict[str, list[str]] = json.loads((Path(__file__).with_name('skills_taxonomy.json')).read_text(encoding='utf-8'))

U = lambda path, note='': Evidence('unit', path, note)  # noqa: E731

# category -> (primary agent, verifier agent, targets, cost model, data policy, providers)
_CAT = {
    'Discovery / Requirements': ('discovery_agent', 'requirements_traceability', ('web',), 'deterministic ($0)', 'user request + answers; no secrets', ()),
    'Planning': ('product_planner', 'executive_orchestrator', ('web',), 'deterministic ($0)', 'contract data only', ()),
    'Architecture': ('architecture_agent', 'code_review_agent', ('web',), 'one model call within the build budget', 'contract data only', ('gemini',)),
    'UX/UI': ('ux_ui_design_agent', 'qa_agent', ('web',), 'instructions inside generation calls', 'no user data', ('gemini',)),
    'Frontend': ('frontend_agent', 'browser_rehearsal_agent', ('web',), 'part of code-generation calls', 'synthetic data in tests', ('gemini',)),
    'Backend': ('backend_agent', 'behavioral_acceptance_agent', ('web',), 'part of code-generation calls', 'synthetic data in tests', ('gemini',)),
    'Database': ('database_agent', 'qa_agent', ('web',), 'part of code generation; platform DB ops $0', 'tenant-isolated; backups encrypted at rest by the store', ()),
    'Authentication': ('identity_auth_agent', 'security_agent', ('web',), '$0 (platform identity)', 'password hashes, session hashes only', ()),
    'Integration': ('integration_agent', 'security_agent', ('web',), 'provider dependent', 'secret references only', ()),
    'Coding': ('coding_agent', 'code_review_agent', ('web',), 'model calls within the build budget', 'generated repository only', ('gemini',)),
    'QA': ('qa_agent', 'quality_gate_agent', ('web',), 'sandbox time ($0 marginal)', 'synthetic data, scratch storage', ()),
    'Browser': ('browser_rehearsal_agent', 'quality_gate_agent', ('web',), 'sandbox time ($0 marginal)', 'synthetic data', ()),
    'Repair': ('repair_agent', 'qa_agent', ('web',), 'model calls within the build budget', 'generated repository only', ('gemini',)),
    'Security': ('security_agent', 'quality_gate_agent', ('web',), '$0', 'findings only, never secret values', ()),
    'Compliance': ('compliance_ip_agent', 'quality_gate_agent', ('web',), '$0', 'rights evidence only', ()),
    'Provider Routing': ('provider_router_agent', 'compliance_ip_agent', ('web',), 'selection is $0; calls are metered', 'prompts sent to approved providers only', ('gemini', 'openai', 'anthropic')),
    'Economics': ('cost_economics_agent', 'quality_gate_agent', ('web',), '$0', 'amounts per build, no card data', ()),
    'Infrastructure': ('infrastructure_agent', 'sre_reliability_agent', ('web',), 'host time', 'no customer content', ()),
    'Deployment': ('deployment_agent', 'release_agent', ('web',), 'host time', 'preview data per project', ()),
    'Release': ('release_agent', 'quality_gate_agent', ('web',), '$0', 'versions + artifacts', ()),
    'Observability': ('observability_agent', 'sre_reliability_agent', ('web',), '$0', 'events in customer language, no prompts/secrets', ()),
    'Backup / Recovery': ('backup_recovery_agent', 'quality_gate_agent', ('web',), 'storage bytes', 'backups in the platform object store', ()),
    'Performance': ('performance_agent', 'quality_gate_agent', ('web',), 'sandbox time', 'synthetic data', ()),
    'Accessibility': ('accessibility_agent', 'qa_agent', ('web',), 'instructions + checks', 'no user data', ()),
    'Localization': ('localization_rtl_agent', 'qa_agent', ('web',), 'instructions + checks', 'no user data', ()),
    'SEO': ('seo_web_quality_agent', 'qa_agent', ('web',), 'instructions', 'no user data', ()),
    'Analytics': ('analytics_agent', 'privacy_reviewer', ('web',), 'n/a', 'consent required', ()),
    'Media — Image': ('image_agent', 'compliance_ip_agent', ('web', 'media'), 'per image (provider price)', 'prompts + outputs, rights recorded', ('replicate',)),
    'Media — Video': ('video_agent', 'compliance_ip_agent', ('media',), 'per second (provider price)', 'rights recorded', ()),
    'Voice': ('voice_speech_agent', 'compliance_ip_agent', ('media',), 'per character/second', 'voice consent required', ()),
    'Audio / Music': ('audio_music_agent', 'compliance_ip_agent', ('media',), 'per track', 'license recorded', ()),
    'Automation': ('automation_agent', 'qa_agent', ('automation',), 'per run', 'secret references only', ()),
    '2D Games': ('game_engineering_2d_agent', 'game_qa_2d_agent', ('game2d',), 'model calls + browser time', 'no user data', ('gemini',)),
}

# skill_key -> (implementation, evidence, gap)
IMPL: dict[str, tuple[tuple[str, ...], tuple, str]] = {
    # Discovery / Requirements
    'intent_classification': (('omni_prod.product_architect:ProductArchitect',), (PAID,), 'keyword families, no model'),
    'requirement_extraction': (('omni_prod.discovery:requirements_text', 'omni_prod.product_architect:ProductArchitect'), (PAID, REHEARSAL_ACCEPT), ''),
    'ambiguity_detection': (('omni_prod.discovery:next_group',), (PAID,), 'fixed question set'),
    'smart_question_generation': (('omni_prod.discovery:next_group',), (PAID,), 'deterministic questions, not generated'),
    'safe_default_selection': (('omni_prod.discovery:answer',), (PAID,), ''),
    'acceptance_criteria_generation': (('omni_prod.autonomous_agents:ArchitectAgent',), (REHEARSAL_ACCEPT,), ''),
    'acceptance_contract_generation': (('omni_prod.web_saas_acceptance:acceptance_scope',), (REHEARSAL_ACCEPT, U('tests/test_demand_driven_infrastructure.py')), ''),
    'functional_requirement_generation': (('omni_prod.product_architect:ProductArchitect',), (PAID,), ''),
    'scope_detection': (('omni_prod.discovery:detection_text', 'omni_prod.product_architect:ProductArchitect'), (U('tests/test_brief_capability_detection.py'),), ''),
    'constraint_extraction': (('omni_prod.product_architect:no_login_requested',), (PAID,), ''),
    'dependency_analysis': (('omni_prod.capability_planner:CapabilityPlanner',), (PAID,), ''),
    # Planning
    'build_plan_generation': (('omni_prod.creator_plan:build_plan_preview',), (PAID,), ''),
    'cost_estimation': (('omni_prod.build_cost_plan:build_economics_quote',), (PAID,), ''),
    'capability_closure': (('omni_prod.agent_os.resolver:resolve',), (U('tests/test_agent_os.py'),), 'web/SaaS families only'),
    'task_decomposition': (('omni_prod.agent_os.runtime:AgentRuntime',), (U('tests/test_agent_os.py'),), ''),
    'task_dependency_generation': (('omni_prod.agent_os.runtime:AgentRuntime',), (U('tests/test_agent_os.py'),), ''),
    'agent_assignment': (('omni_prod.agent_os.recorder:BuildAgentRecorder',), (U('tests/test_agent_os.py'),), ''),
    # Architecture
    'stack_selection': (('omni_prod.product_architect:ProductArchitect',), (PAID,), 'one self-contained web stack'),
    'data_model_design': (('omni_prod.autonomous_agents:ArchitectAgent',), (REHEARSAL_ACCEPT,), ''),
    'api_contract_design': (('omni_prod.autonomous_agents:ArchitectAgent',), (REHEARSAL_ACCEPT,), ''),
    'multi_tenant_architecture': (('omni_prod.preview_runtime:project_data_dir',), (FREE,), 'platform-level isolation of generated data'),
    # UX/UI
    'design_system_generation': (('omni_prod.skills_runtime:VISUAL_DESIGN',), (PAID,), 'instruction + CSS heuristic'),
    'design_token_generation': (('omni_prod.skills_runtime:VISUAL_DESIGN',), (PAID,), ''),
    'form_design': (('omni_prod.skills_runtime:FORM_VALIDATION',), (PAID,), ''),
    'empty_state_design': (('omni_prod.skills_runtime:UI_STATES',), (PAID,), ''),
    'error_state_design': (('omni_prod.skills_runtime:UI_STATES',), (PAID,), ''),
    'loading_state_design': (('omni_prod.skills_runtime:UI_STATES',), (PAID,), ''),
    'responsive_layout': (('omni_prod.skills_runtime:VISUAL_DESIGN',), (PAID,), ''),
    'rtl_design': (('omni_prod.skills_runtime:TEXT_LOCALE',), (PAID,), ''),
    # Frontend
    'page_generation': (('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), ''),
    'form_generation': (('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), ''),
    'client_validation': (('omni_prod.skills_runtime:FORM_VALIDATION',), (PAID,), ''),
    'api_binding': (('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), ''),
    'rtl_implementation': (('omni_prod.skills_runtime:TEXT_LOCALE',), (PAID,), ''),
    'table_generation': (('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), ''),
    # Backend
    'api_endpoint_generation': (('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), ''),
    'request_validation': (('omni_prod.skills_runtime:FORM_VALIDATION',), (REHEARSAL_ACCEPT,), ''),
    'business_logic_generation': (('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), ''),
    'server_error_handling': (('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), ''),
    # Database
    'schema_generation': (('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), 'SQLite in DATA_DIR'),
    'migration_validation': (('omni_prod.migrate:main', 'path:infra/staging/verify_neon_bootstrap.py'), (DEPLOY,), 'platform migrations only'),
    'data_integrity_validation': (('omni_prod.skills_runtime:DATA_INTEGRITY',), (PAID,), ''),
    'persistence_verification': (('omni_prod.preview_durability:selftest',), (DEPLOY, FREE), 'previews only'),
    'data_isolation': (('omni_prod.preview_runtime:project_data_dir',), (FREE, DEPLOY), ''),
    'scratch_database_generation': (('omni_prod.behavior_acceptance:BehaviorAcceptanceExecutor', 'omni_prod.preview_runtime:DockerPreviewProvider'), (REHEARSAL_ACCEPT, DEPLOY), ''),
    'backup_generation': (('omni_prod.backup:snapshot',), (BACKUP,), ''),
    'restore_validation': (('omni_prod.backup:verify',), (BACKUP,), ''),
    # Authentication (platform identity)
    'signup': (('omni_prod.creator_accounts:PostgresAccountService',), (FREE,), 'platform accounts, not generated apps'),
    'login': (('omni_prod.creator_accounts:PostgresAccountService',), (PAID,), 'platform accounts'),
    'logout': (('omni_prod.identity_lifecycle:IdentityService',), (U('tests/test_m5_identity_lifecycle.py'),), ''),
    'session_management': (('omni_prod.identity_lifecycle:IdentityService',), (U('tests/test_m5_identity_lifecycle.py'),), ''),
    'email_verification': (('omni_prod.identity_lifecycle:IdentityService',), (U('tests/test_m5_identity_lifecycle.py'),), 'no mail sender configured'),
    'password_reset': (('omni_prod.identity_lifecycle:IdentityService',), (U('tests/test_m5_identity_lifecycle.py'),), 'no mail sender configured'),
    'account_deletion': (('omni_prod.identity_lifecycle:IdentityService',), (U('tests/test_m5_identity_lifecycle.py'),), ''),
    'account_export': (('omni_prod.identity_lifecycle:IdentityService',), (U('tests/test_m5_identity_lifecycle.py'),), ''),
    # Integration
    'integration_health_check': (('omni_prod.model_probe:probe',), (Evidence('live', 'model-probe run 37814803770', '', 'ff6b4f6', 'worker-host', ('model provider availability',)),), 'model providers only'),
    'rate_limit_handling': (('omni_prod.routed_gateway:RoutedModelGateway',), (PAID,), 'model calls (429 released, route skipped)'),
    'provider_fallback': (('omni_prod.routed_gateway:RoutedModelGateway',), (U('tests/test_provider_quota_and_dialects.py'),), ''),
    'external_error_normalization': (('omni_prod.worker_tasks:failure_code',), (U('tests/test_m3_preview_logic.py'),), ''),
    # Coding
    'file_create': (('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), ''),
    'file_modify': (('omni_prod.autonomous_agents:RepairAgent',), (REHEARSAL_ACCEPT,), ''),
    'repository_patch_application': (('omni_prod.repository_patch:normalize_repo_path',), (REHEARSAL_ACCEPT,), ''),
    'dependency_add': (('omni_prod.dependency_policy:DependencyGateExecutor',), (REHEARSAL_ACCEPT,), 'pinned allowlist only'),
    # QA
    'unit_test_generation': (('omni_prod.autonomous_agents:GeneratorAgent',), (REHEARSAL_ACCEPT,), ''),
    'unit_test_execution': (('omni_prod.remote_sandbox:RemoteSandboxRepositoryExecutor',), (REHEARSAL_ACCEPT, DEPLOY), ''),
    'api_test': (('omni_prod.behavior_acceptance:BehaviorAcceptanceExecutor',), (REHEARSAL_ACCEPT,), ''),
    'behavioral_acceptance_test': (('omni_prod.behavior_acceptance:BehaviorAcceptanceExecutor', 'omni_prod.web_saas_acceptance:WebSaaSAcceptanceRunner'), (REHEARSAL_ACCEPT,), ''),
    'requirement_traceability_test': (('omni_prod.web_saas_acceptance:WebSaaSAcceptanceRunner',), (REHEARSAL_ACCEPT,), 'acceptance IDs -> steps'),
    'persistence_test': (('omni_prod.preview_durability:selftest',), (DEPLOY, FREE), ''),
    'restart_test': (('omni_prod.preview_durability:selftest',), (DEPLOY, FREE), ''),
    'resume_test': (('omni_prod.maintenance:recover_lost_running',), (CRASH,), 'build restarts from the beginning'),
    'cancellation_test': (('omni_prod.postdeploy_checks:stage_cancel_verify',), (FREE,), ''),
    'cost_test': (('omni_prod.worker_tasks:metered_llm_cost',), (CRASH, U('tests/test_actual_cost_settlement.py')), ''),
    'regression_test': (('omni_prod.agent_os.meta:regression_guardian',), (U('tests/test_agent_os.py'),), ''),
    'migration_test': (('path:infra/staging/verify_neon_bootstrap.py',), (DEPLOY,), ''),
    'provider_failure_test': (('omni_prod.agent_os.meta:failure_injection',), (U('tests/test_failure_injection.py'),), 'simulated providers'),
    'negative_test': (('omni_prod.web_saas_acceptance:WebSaaSAcceptanceRunner',), (REHEARSAL_ACCEPT,), ''),
    # Browser
    'browser_launch': (('omni_prod.browser_probe:BrowserFlowExecutor',), (PAID, DEPLOY), ''),
    'page_load_test': (('omni_prod.preview_smoke:PreviewReadyExecutor',), (PAID,), ''),
    'form_test': (('omni_prod.browser_probe:BrowserFlowExecutor',), (PAID, DEPLOY), 'fills forms by field type'),
    'click_test': (('omni_prod.browser_probe:BrowserFlowExecutor',), (PAID,), ''),
    'javascript_error_detection': (('omni_prod.browser_probe:BrowserFlowExecutor',), (DEPLOY,), ''),
    'network_error_detection': (('omni_prod.browser_probe:BrowserFlowExecutor',), (DEPLOY,), '5xx answers'),
    'browser_acceptance_test': (('omni_prod.browser_probe:BrowserFlowExecutor',), (PAID, REHEARSAL_ACCEPT), ''),
    # Repair
    'failure_classification': (('omni_prod.attempt_ledger:classify_execution',), (REHEARSAL_ACCEPT,), ''),
    'minimal_patch_generation': (('omni_prod.autonomous_agents:RepairAgent',), (REHEARSAL_ACCEPT,), ''),
    'repair_execution': (('omni_prod.autonomous_agents:RepairAgent',), (REHEARSAL_ACCEPT,), ''),
    'repair_verification': (('omni_prod.remote_sandbox:RemoteSandboxRepositoryExecutor', 'omni_prod.behavior_acceptance:BehaviorAcceptanceExecutor'), (REHEARSAL_ACCEPT,), ''),
    'retry_decision': (('omni_prod.autonomous_core:AutonomousProductEngine',), (REHEARSAL_ACCEPT,), 'bounded rounds'),
    # Security
    'secret_detection': (('omni_prod.security_testing:hostile_repository_scan',), (PAID,), 'static'),
    'xss_check': (('omni_prod.skills_runtime:TEXT_LOCALE', 'omni_prod.product_review:ProductReviewExecutor'), (REHEARSAL_ACCEPT,), 'review + instruction, no dynamic XSS probe'),
    'preview_access_check': (('omni_prod.preview_access:PreviewAccess',), (FREE,), ''),
    'security_release_gate': (('omni_prod.worker_tasks:evaluate_release_gates',), (PAID,), ''),
    'csrf_check': (('omni_prod.browser_session:extract_session_token',), (U('tests/test_v24_auth.py'),), 'platform API only'),
    # Compliance
    'commercial_provider_validation': (('omni_prod.agent_os.providers:commercial_status',), (U('tests/test_agent_os.py'),), ''),
    'copyright_risk_detection': (('omni_prod.rights_ip:RightsEngine',), (PAID,), ''),
    'ip_warning_generation': (('omni_prod.rights_ip:RightsEngine',), (PAID,), ''),
    'commercial_use_policy_check': (('omni_prod.agent_os.providers:commercial_status',), (U('tests/test_agent_os.py'),), ''),
    # Provider routing
    'capability_provider_match': (('omni_prod.routed_gateway:RoutedModelGateway',), (PAID,), ''),
    'provider_health_check': (('omni_prod.model_probe:probe',), (Evidence('live', 'model-probe run 37814803770', '', 'ff6b4f6', 'worker-host', ('model provider availability',)),), ''),
    'provider_cost_compare': (('omni_prod.routed_gateway:RoutedModelGateway',), (PAID,), ''),
    'provider_quality_compare': (('omni_prod.routed_gateway:RoutedModelGateway',), (PAID,), 'catalog quality scores'),
    'provider_selection': (('omni_prod.routed_gateway:RoutedModelGateway',), (PAID, REHEARSAL_ACCEPT), ''),
    'provider_fallback_selection': (('omni_prod.routed_gateway:RoutedModelGateway',), (U('tests/test_provider_quota_and_dialects.py'),), ''),
    'provider_retry': (('omni_prod.routed_gateway:RoutedModelGateway',), (U('tests/test_provider_quota_and_dialects.py'),), ''),
    'model_selection': (('omni_prod.routed_gateway:RoutedModelGateway',), (PAID,), ''),
    'commercial_permission_check': (('omni_prod.agent_os.providers:commercial_status',), (U('tests/test_agent_os.py'),), ''),
    # Economics
    'build_quote': (('omni_prod.build_cost_plan:build_economics_quote',), (PAID,), ''),
    'credit_reservation': (('omni_prod.subscription_store:PostgresSubscriptionService',), (PAID, FREE), ''),
    'usage_metering': (('omni_prod.attempt_ledger:metered_cost',), (CRASH,), ''),
    'provider_price_lookup': (('omni_prod.model_catalog:load_model_catalog',), (CRASH,), 'versioned catalog'),
    'actual_cost_calculation': (('omni_prod.worker_tasks:metered_llm_cost',), (CRASH,), ''),
    'credit_settlement': (('omni_prod.worker_tasks:resolve_m5_billing',), (CRASH,), ''),
    'unused_reservation_release': (('omni_prod.subscription_store:PostgresSubscriptionService',), (FREE, CRASH), ''),
    'budget_guard': (('omni_prod.model_policy:authorize_model_call',), (PAID,), 'ceiling bound to the reservation'),
    'reconciliation': (('omni_prod.qa_budget:qa_used_usd',), (U('tests/test_golden_mod_path_live_postgres.py'),), 'QA ledger'),
    'agent_budget_assignment': (('omni_prod.agent_os.runtime:AgentRuntime',), (U('tests/test_agent_os.py'),), ''),
    # Infrastructure
    'worker_health_check': (('omni_prod.postdeploy_checks:stage_free',), (FREE, DEPLOY), ''),
    'queue_health_check': (('path:.github/workflows/deploy-worker.yml',), (DEPLOY,), ''),
    'storage_health_check': (('path:.github/workflows/deploy-worker.yml',), (DEPLOY,), ''),
    'database_health_check': (('omni_prod.postdeploy_checks:stage_free',), (FREE,), ''),
    'queue_job_submit': (('omni_prod.queueing:enqueue_build',), (PAID, FREE), ''),
    'job_resume': (('omni_prod.maintenance:recover_lost_running',), (CRASH,), 'restart from the beginning, once'),
    'job_cancel': (('omni_prod.build_control:BuildControl', 'omni_prod.job_repository:PostgresBuildRepository.request_cancel'), (FREE,), ''),
    'job_timeout': (('omni_prod.sandbox:run_sandbox',), (U('tests/test_sandbox_cleanup.py'),), ''),
    'stale_job_recovery': (('omni_prod.maintenance:recover_lost_running', 'omni_prod.maintenance:redispatch_lost'), (CRASH,), ''),
    'environment_validation': (('path:infra/worker-host/write-env.sh',), (DEPLOY,), ''),
    # Deployment (previews)
    'preview_prepare': (('omni_prod.preview_runtime:DockerPreviewProvider',), (FREE,), ''),
    'preview_deploy': (('omni_prod.preview_runtime:DockerPreviewProvider',), (FREE, PAID), ''),
    'preview_health_check': (('omni_prod.preview_runtime:wait_until_healthy',), (FREE,), ''),
    'preview_access_protect': (('omni_prod.preview_access:PreviewAccess', 'omni_prod.preview_router:make_handler'), (FREE,), ''),
    'preview_token_issue': (('omni_prod.preview_access:PreviewAccess.issue',), (FREE,), ''),
    'preview_token_revoke': (('omni_prod.preview_access:PreviewAccess.set_mode',), (FREE,), ''),
    'deployment_verification': (('omni_prod.postdeploy_checks:main',), (FREE,), 'platform deploy'),
    'deployment_rollback': (('path:STATUS.md',), (), 'documented procedure, not automated'),
    # Release
    'version_create': (('omni_prod.workspace:PostgresProjectWorkspace.commit',), (PAID, FREE), ''),
    'artifact_commit': (('omni_prod.workspace:PostgresProjectWorkspace.commit',), (PAID,), ''),
    'release_evidence_generation': (('omni_prod.worker_tasks:_run_live_build_job',), (PAID,), ''),
    'release_gate': (('omni_prod.worker_tasks:evaluate_release_gates',), (PAID,), ''),
    'rollback_point_create': (('omni_prod.workspace:PostgresProjectWorkspace.restore',), (U('tests/test_golden_mod_path_live_postgres.py'),), ''),
    # Observability
    'execution_trace': (('omni_prod.build_control:BuildControl',), (FREE, PAID), ''),
    'agent_trace': (('omni_prod.agent_os.recorder:BuildAgentRecorder',), (U('tests/test_agent_os.py'),), ''),
    'provider_trace': (('omni_prod.attempt_ledger:persist_attempts',), (PAID,), ''),
    'cost_trace': (('omni_prod.attempt_ledger:AttemptRecorder',), (PAID, CRASH), ''),
    'failure_trace': (('omni_prod.behavior_acceptance:BehaviorAcceptanceExecutor',), (REHEARSAL_ACCEPT,), ''),
    'structured_logging': (('omni_prod.build_control:BuildControl',), (FREE,), ''),
    # Backup / Recovery
    'database_backup': (('omni_prod.backup:upload', 'path:.github/workflows/backup-restore.yml'), (BACKUP,), 'same object store as artifacts'),
    'artifact_backup': (('omni_prod.backup:snapshot',), (BACKUP,), 'content-addressed artifacts re-verified'),
    'project_backup': (('omni_prod.backup:snapshot',), (BACKUP,), ''),
    'backup_validation': (('omni_prod.backup:verify',), (BACKUP,), ''),
    'restore_database': (('path:.github/workflows/backup-restore.yml',), (BACKUP,), 'into a throw-away database'),
    'restore_project': (('omni_prod.backup:verify',), (BACKUP,), ''),
    'restore_artifact': (('omni_prod.backup:fetch',), (BACKUP,), ''),
    'restore_verification': (('omni_prod.backup:verify',), (BACKUP,), ''),
    'disaster_recovery_test': (('path:.github/workflows/backup-restore.yml',), (BACKUP,), 'restore drill only; no failover'),
    # Accessibility / Localization (instructions + review)
    'label_test': (('omni_prod.skills_runtime:FORM_VALIDATION',), (PAID,), 'instruction + review'),
    'contrast_test': (('omni_prod.skills_runtime:VISUAL_DESIGN',), (PAID,), 'instruction only'),
    'hebrew_localization': (('omni_prod.skills_runtime:TEXT_LOCALE',), (PAID,), ''),
    'rtl_layout': (('omni_prod.skills_runtime:TEXT_LOCALE',), (PAID,), ''),
    'locale_date': (('omni_prod.skills_runtime:TEXT_LOCALE',), (PAID,), ''),
    # Media — Image (provider configured on the API; no verified artifact yet)
    'text_to_image': (('omni_prod.providers.image_provider:PredictionImageProvider',), (U('tests/test_replicate_image_test.py'),), 'no verified real generation'),
    'image_quality_check': (('omni_prod.providers.image_provider:sniff_image',), (U('tests/test_replicate_image_test.py'),), 'format/size only'),
}

# Named blockers (external, not engineering).
BLOCKED_SKILLS = {
    'google_oauth': 'OAuth client registration (founder account) not provided',
    'apple_oauth': 'Apple developer account not provided',
    'text_to_video': 'no commercial video provider contracted',
    'image_to_video': 'no commercial video provider contracted',
    'video_to_video': 'no commercial video provider contracted',
    'lip_sync': 'no commercial video provider contracted',
    'voice_clone_where_licensed': 'no licensed voice provider contracted',
    'music_generation': 'no commercially licensed music provider contracted',
}
CONFIG_SKILLS = {  # implemented code that needs configuration not observed on the build worker
    'text_to_image': ('OMNI_IMAGE_PROVIDER_BASE_URL', 'OMNI_IMAGE_PROVIDER_API_KEY_REF', 'OMNI_IMAGE_PROVIDER_MODEL'),
}


def _name(key: str) -> str:
    return key.replace('_', ' ').capitalize()


def _contract(category: str, key: str) -> SkillContract:
    agent, verifier, targets, cost, data, providers = _CAT[category]
    impl, evidence, gap = IMPL.get(key, ((), (), 'not implemented'))
    return SkillContract(
        skill_key=key, name=_name(key), version='1', category=category,
        purpose=f'{_name(key)} for the {category} stage of a product build',
        unique_responsibility=f'only {_name(key).lower()}; composes with other {category} skills, never replaces them',
        when_used=f'when the approved contract needs {_name(key).lower()}',
        when_not_used='when the approved contract does not need it, or a cheaper skill already proved the result',
        trigger_conditions=(f'agent {agent} plans a task that requires {key}',),
        required_inputs=('approved build contract', 'task context'),
        optional_inputs=('previous attempt evidence',),
        outputs=(f'{key} result with evidence',),
        preconditions=('dependencies resolved AVAILABLE', 'budget reserved'),
        postconditions=('result recorded with evidence', 'verifier can re-check it'),
        dependencies=(),
        primary_agent=agent, secondary_agent='', verifier_agent=verifier,
        supported_targets=targets, providers=providers,
        cheap_provider=providers[0] if providers else '', standard_provider=providers[0] if providers else '',
        premium_provider=providers[-1] if providers else '', fallback_provider=providers[1] if len(providers) > 1 else '',
        estimated_cost_model=cost,
        permissions=('read approved contract', 'write task evidence'),
        security_constraints=('no secrets in prompts, logs or evidence', 'runs inside the isolated sandbox when executing code'),
        commercial_constraints=('COMMERCIAL_APPROVED providers only for paying customers',),
        data_policy=data, implementation_location=impl,
        verification_method='independent verifier agent + recorded evidence',
        quality_metrics=('pass/fail of its verification', 'cost', 'latency'),
        success_criteria=(f'{key} produced its output and the verifier accepted it',),
        failure_modes=('missing input', 'provider failure', 'verification rejected'),
        retry_policy='bounded by the build repair rounds and budget', fallback_policy='next approved provider or escalate',
        config=CONFIG_SKILLS.get(key, ()), blocked_by=BLOCKED_SKILLS.get(key, ''), evidence=evidence, gap=gap,
    )


SKILLS: tuple[SkillContract, ...] = tuple(_contract(cat, key) for cat, keys in TAXONOMY.items() for key in keys)
BY_KEY = {s.skill_key: s for s in SKILLS}
UNKNOWN_IMPL_KEYS = sorted(set(IMPL) - set(BY_KEY))
