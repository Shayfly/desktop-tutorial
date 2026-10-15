

## META

```
commit: a7afd99d353462410bfc400b0417a0e98209b540
date:   2026-10-15T19:06:17Z
branch: audit/cto-pack
files:  879
```


## INVENTORY — כל קובץ py לפי שורות

```
      0 tests/integration/__init__.py
      1 omni_prod/intake/__init__.py
      1 omni_prod/planning/__init__.py
      1 omni_prod/providers/__init__.py
      2 omni_prod/agent_os/__init__.py
      5 omni_prod/__init__.py
      9 tests/integration/test_live_model.py
     10 app.py
     10 omni_prod/request_id.py
     10 tools/ui_visual_edit/serve_api.py
     12 tests/fixtures/visual/good_app.py
     13 omni_prod/intelligence/__init__.py
     13 tests/integration/test_live_sandbox_security.py
     13 tests/integration/test_mobile_signing_readiness.py
     14 omni_prod/health.py
     15 omni_prod/worker_health.py
     16 omni_prod/human_evaluation.py
     16 omni_prod/secret_redaction.py
     16 tests/fixtures/visual/bad_app.py
     17 omni_prod/artifact_keys.py
     17 omni_prod/cors_policy.py
     17 scripts/run_http_load.py
     17 scripts/run_live_sandbox_hostile.py
     18 omni_prod/artifact_integrity.py
     18 omni_prod/repair_loop.py
     18 tests/test_architect_website_no_crud.py
     18 tests/test_intake_product_family_regression.py
     19 omni_prod/attestation.py
     19 tests/test_customer_font_security.py
     20 tools/ui_visual_edit/fixture/app.py
     21 omni_prod/dead_letter.py
     21 omni_prod/retry.py
     21 scripts/run_hostile_static_suite.py
     21 tests/test_intake_explicit_intent_regression.py
     22 omni_prod/sbom.py
     23 omni_prod/brand_native_clients.py
     23 omni_prod/worker_lease.py
     23 scripts/run_live_benchmark.py
     24 omni_prod/training_data.py
     25 omni_prod/build_budget.py
     25 omni_prod/i18n.py
     25 omni_prod/mobile_pipeline.py
     25 omni_prod/recovery_drill.py
     26 scripts/run_v26_release_gate.py
     26 tests/test_r2_storage_signing.py
     27 omni_prod/deployment_runtime.py
     27 omni_prod/game_pipeline.py
     27 omni_prod/international_engine.py
     28 omni_prod/teams.py
     28 tests/test_ci_workflow_concurrency.py
     28 tests/test_r2_config_diagnostic.py
     28 tests/test_rehearsal.py
     29 omni_prod/limits.py
     29 omni_prod/rate_limit.py
     29 omni_prod/structured_event.py
     29 tests/test_v18_supplychain_security.py
     29 tests/test_website_requirements_regression.py
     30 omni_prod/canary_controller.py
     30 omni_prod/design_system.py
     30 omni_prod/rollback.py
     30 scripts/run_v28_offline_benchmark.py
     30 tests/integration/test_live_stack.py
     30 tests/test_intake_palette_regression.py
     30 tests/test_v24_auth.py
     32 omni_prod/memory_adapters.py
     32 omni_prod/observability.py
     32 scripts/run_quality_gate.py
     32 tests/policy_fixtures.py
     32 tools/ui_visual_edit/common.py
     33 omni_prod/canary.py
     33 tests/test_history_without_artifact_download.py
     34 omni_prod/change_policy.py
     34 omni_prod/dependency_inventory.py
     34 omni_prod/diagnostics_app.py
     34 omni_prod/launch_readiness_v28.py
     34 omni_prod/models.py
     34 omni_prod/specialist_agents.py
     35 omni_prod/api_routes.py
     35 omni_prod/error_taxonomy.py
     35 scripts/run_v25_release_gate.py
     36 scripts/run_v25_offline_benchmark.py
     36 tests/test_repair_sees_main_file.py
     36 tests/test_v7_content_only_provenance.py
     37 omni_prod/schema_manifest.py
     37 omni_prod/web_security.py
     37 tests/integration/test_qstash_scheduler_live.py
     38 omni_prod/product_analytics.py
     38 omni_prod/readiness.py
     38 scripts/run_v27_release_gate.py
     38 tests/test_legacy_paths_guard.py
     39 omni_prod/usage.py
     39 scripts/run_international_gate.py
     40 omni_prod/agent_os/providers.py
     40 omni_prod/metrics.py
     40 omni_prod/release_gate.py
     40 tests/m4d2_rq_job_target.py
     40 tests/test_backup_restore.py
     41 omni_prod/recovery_simulation.py
     41 omni_prod/security_testing.py
     41 omni_prod/ui_translations.py
     41 tests/test_intake_palette_preservation.py
     41 tests/test_v7_visitor_no_login_boundary.py
     42 omni_prod/provenance.py
     43 tests/test_m5_migration_numbering.py
     44 tests/test_vercel_entrypoint.py
     45 omni_prod/build_state.py
     45 omni_prod/orchestrator.py
     45 omni_prod/planning/router.py
     45 tests/test_database_pool_health.py
     45 tests/test_secret_scan_ci_exemption.py
     46 omni_prod/media_gateway.py
     46 omni_prod/model_policy.py
     46 omni_prod/provider_registry.py
     47 infra/staging/verify_neon_bootstrap.py
     47 tests/test_intake_family_intent.py
     47 tests/test_m5_public_path_truth.py
     48 omni_prod/auth.py
     48 omni_prod/modification_admission.py
     48 tests/test_model_gateway_idempotency.py
     48 tests/test_spec_language.py
     48 tests/test_v7_semantic_marker_provenance.py
     49 tests/test_m495_subscription_settlement.py
     50 omni_prod/evidence_json.py
     50 omni_prod/international_readiness.py
     51 omni_prod/slo.py
     51 tests/test_financial_journal_guard.py
     52 tests/integration/test_m5_live_llm_usage.py
     53 omni_prod/agent_team.py
     54 tests/test_isolation_check.py
     54 tests/test_release_blocks_on_failed_acceptance.py
     55 omni_prod/backup_manifest.py
     55 omni_prod/project_memory.py
     55 tests/test_conversation_ux.py
     56 tests/integration/test_v28_creator_persistence.py
     56 tests/test_asset_requirements.py
     56 tests/test_m495_asset_evidence.py
     57 omni_prod/integrations.py
     58 omni_prod/browser_fixtures.py
     58 tests/test_acceptance_coverage.py
     59 omni_prod/production_adapters.py
     60 omni_prod/circuit_breaker.py
     60 tests/test_brief_capability_detection.py
     60 tests/test_failure_replay.py
     61 omni_prod/customer_views.py
     61 tests/test_architect_spec_shape.py
     62 omni_prod/model_runtime_config.py
     63 omni_prod/acceptance_pipeline.py
     63 omni_prod/brand_clearance.py
     63 omni_prod/intake/benchmark.py
     63 tests/test_v13_core.py
     63 tests/test_v22_sandbox_executor.py
     64 tests/integration/test_m5_live_media_provider.py
     64 tests/test_architect_assignment_gate.py
     64 tests/test_company_loss.py
     64 tests/test_live_build_stores_spec.py
     64 tests/test_v14_core.py
     65 omni_prod/capabilities.py
     65 omni_prod/creator_accounts.py
     65 omni_prod/intelligence/governance.py
     65 omni_prod/model_router.py
     65 omni_prod/planning/registry_view.py
     65 omni_prod/repository_patch.py
     65 tools/golden_e2e_quote_probe.py
     66 omni_prod/agent_os/resolver.py
     66 tools/ui_visual_edit/preview_host.py
     67 omni_prod/credential_binding.py
     67 omni_prod/intake/lanes.py
     67 omni_prod/model_probe.py
     68 omni_prod/build_outbox_relay.py
     69 tests/test_overlay.py
     70 tests/test_sandbox_cleanup.py
     70 tests/test_v15_acceptance.py
     71 omni_prod/agent_os/evidence.py
     71 tests/test_v24_native_remote.py
     72 omni_prod/idempotency.py
     72 tests/test_modification_context.py
     73 omni_prod/config.py
     73 omni_prod/intent_terms.py
     73 omni_prod/migrate.py
     74 omni_prod/migrations.py
     75 omni_prod/intake/families.py
     75 omni_prod/native_source.py
     75 tests/test_manifest_shape.py
     75 tests/test_preview_router.py
     76 omni_prod/intelligence/task_policy.py
     77 omni_prod/release_manifest.py
     78 omni_prod/product_spec.py
     78 tests/test_v19_reliability.py
     79 omni_prod/audit.py
     79 omni_prod/migration_runner.py
     79 omni_prod/outbox.py
     79 omni_prod/queueing.py
     79 tests/test_entitlements.py
     79 tests/test_requirement_ledger.py
     79 tests/test_worker_budget_binding.py
     80 omni_prod/integration_center.py
     80 tests/test_m5_browser_session.py
     80 tests/test_task_quality_routing.py
     80 tools/generate_neon_bootstrap.py
     81 omni_prod/providers/llm_provider.py
     81 omni_prod/uploaded_assets.py
     81 tests/integration/test_financial_fault_experiment.py
     81 tests/test_v12_core.py
     82 tests/test_build_state_machine.py
     82 tests/test_janitor_redispatch.py
     83 omni_prod/company_loss.py
     83 omni_prod/staging_simulation.py
     83 omni_prod/v26_platform.py
     83 tests/test_economics_report.py
     83 tests/test_universal_family_skill_resolution.py
     84 omni_prod/conversation/memory.py
     84 tests/integration/test_r2_generated_storage_live.py
     84 tests/test_customer_flow_rejects.py
     85 tests/test_v20_observability_recovery.py
     86 tests/test_m5_planner_target_detection.py
     87 omni_prod/providers/r2_credentials.py
     87 omni_prod/sandbox_service.py
     87 tests/test_j3_three_repair_round_policy.py
     88 omni_prod/browser_session.py
     88 omni_prod/universal_brain.py
     88 tests/test_model_json_parsing.py
     89 omni_prod/billing.py
     89 omni_prod/product_evolution.py
     89 omni_prod/remote_sandbox.py
     90 omni_prod/deployments.py
     90 tests/test_m495_truth_lock.py
     91 scripts/run_v28_http_acceptance.py
     91 tests/test_db_fingerprint.py
     91 tests/test_maintenance_live_postgres.py
     91 tests/test_quality_repairable.py
     93 omni_prod/account_tenant.py
     93 omni_prod/media_branding.py
     93 tests/test_m5_project_lifecycle.py
     95 tests/test_j1_real_agent_feature_flag.py
     96 omni_prod/redis_circuit_breaker.py
     97 tests/m4d2b_worker_process.py
     97 tests/test_m495_provider_pricing_economics.py
     98 omni_prod/providers/replicate_connection.py
     98 omni_prod/sandbox_request_policy.py
     98 tests/test_uploaded_logo.py
     99 omni_prod/preflight.py
     99 omni_prod/project_manifest.py
     99 tests/test_m495_capability_planner.py
     99 tests/test_sandbox_runner_health.py
    100 omni_prod/benchmark_suite.py
    101 omni_prod/product_review.py
    101 tests/test_m495_provider_contracts.py
    102 omni_prod/db.py
    102 omni_prod/v28_platform.py
    103 omni_prod/spec_repository.py
    104 tests/test_evidence_json.py
    105 omni_prod/worker.py
    106 tests/test_j1_j2_existing_engine_integration.py
    107 omni_prod/intelligence/states.py
    107 omni_prod/planning/feasibility.py
    107 tests/test_failure_injection.py
    109 omni_prod/intelligence/lifecycle.py
    109 tests/m5_worker_harness.py
    109 tests/test_profit_protection.py
    109 tests/test_v16_release_gate.py
    111 tests/test_m2_native_logic.py
    112 scripts/run_v28_release_gate.py
    113 omni_prod/secret_scan.py
    113 tests/test_public_pricing_economics.py
    114 omni_prod/intake/mode.py
    114 tests/test_spec_repository.py
    114 tests/test_v7_readiness_regression.py
    115 omni_prod/providers/http_media_provider.py
    115 tests/test_browser_probe.py
    115 tests/test_intake_worker_route.py
    116 omni_prod/entitlements.py
    116 tests/test_visual_qa.py
    117 tests/test_product_evolution.py
    118 omni_prod/failure_replay.py
    118 tests/test_v17_preflight.py
    119 tests/test_worker_entrypoint.py
    119 tools/ui_conversation_walkthrough.py
    120 tests/test_replicate_image_test.py
    121 omni_prod/agent_os/contracts.py
    121 omni_prod/intake/worker_route.py
    122 tests/test_discovery_endpoints.py
    127 tests/test_v26_universal_pro.py
    128 omni_prod/capability_verification.py
    129 omni_prod/media_pipeline.py
    129 omni_prod/preview_durability.py
    129 tests/integration/test_m5_managed_web_saas_live.py
    130 tests/integration/test_profit_billing_events_pg.py
    131 omni_prod/isolation_check.py
    132 omni_prod/demo_project.py
    133 tests/test_crash_recovery_and_change_parity.py
    133 tests/test_preview_access.py
    134 tests/test_model_transient_retry.py
    134 tests/test_modification_diff.py
    134 tests/test_qa_plan_parity.py
    135 omni_prod/infrastructure_registry.py
    135 omni_prod/providers/replicate_image_test.py
    135 tests/test_preview_smoke.py
    137 tests/test_behavior_acceptance_in_build.py
    137 tests/test_r2_generated_credentials.py
    137 tests/test_replicate_connection.py
    138 tests/test_m495_truth_readiness_api.py
    138 tests/test_v23_investor_grade.py
    139 omni_prod/rehearsal.py
    139 tools/m49_ready_invariant_check.py
    140 omni_prod/semantic_capabilities.py
    140 tests/test_consistency_gate.py
    141 tests/test_m5_identity_lifecycle.py
    141 tests/test_migration_rollback_tolerance.py
    142 omni_prod/intake/agent.py
    144 omni_prod/branding.py
    145 omni_prod/creator_plan.py
    145 omni_prod/preview_smoke.py
    147 tests/test_registry_audit.py
    149 omni_prod/modification_diff.py
    149 tests/test_v21_gemini_remediation.py
    150 omni_prod/capability_worker.py
    150 tests/test_m495_capability_verification.py
    153 omni_prod/preview_access.py
    156 omni_prod/intake/complexity.py
    156 tests/test_dependency_policy.py
    157 tests/test_v7_semantic_intake_architect.py
    158 omni_prod/build_contract_repository.py
    160 tests/test_m495_capability_registry.py
    161 tests/test_m5_product_architect.py
    162 tests/integration/test_live_preview_runtime.py
    163 omni_prod/brief_repository.py
    164 tests/test_m495_worker_capabilities.py
    166 omni_prod/build_cost_plan.py
    166 tests/test_m495_provider_adapters_credentials.py
    166 tests/test_m5_generated_app_storage_isolation.py
    166 tests/test_worker_repository_parity.py
    167 omni_prod/intelligence/prices.py
    167 tests/integration/test_m495_provider_adapter.py
    168 omni_prod/conversation/store.py
    168 omni_prod/sandbox_executor.py
    168 tests/test_m5_ssrf_guard.py
    169 tests/m4d2b_local_model_server.py
    171 omni_prod/model_catalog.py
    174 tests/test_skills_runtime_and_review.py
    176 omni_prod/build_control.py
    176 tests/test_intake_requirements_preservation.py
    176 tests/test_v25_unified_v10_parity.py
    177 omni_prod/safe_fetch.py
    177 omni_prod/stripe_billing.py
    177 tests/test_v22_autonomous_core.py
    177 tests/test_v24_international.py
    178 omni_prod/quality_gate.py
    178 tests/test_customer_economics_views.py
    178 tests/test_m495_golden_acceptance.py
    181 omni_prod/sandbox.py
    181 omni_prod/v27_platform.py
    182 omni_prod/storage.py
    183 omni_prod/behavior_acceptance.py
    184 omni_prod/qa_budget.py
    186 tests/test_repair_stop_loss.py
    187 omni_prod/agent_os/audit.py
    187 tests/test_m5_creator_workspace.py
    188 omni_prod/intake/reservation_worker.py
    190 tests/test_intake_complexity.py
    191 omni_prod/requirement_ledger.py
    191 tests/test_m495_skills_agents_registry.py
    192 tests/test_model_catalog_routing.py
    193 tests/test_infisical_secret_store.py
    194 omni_prod/provider_contracts.py
    198 omni_prod/agent_catalog.py
    198 tests/test_qa_budget.py
    199 omni_prod/providers/qstash_scheduler.py
    202 omni_prod/active_jobs.py
    203 omni_prod/browser_probe.py
    203 tests/test_build_cancel_and_log.py
    204 tests/test_m49_lifecycle.py
    206 omni_prod/modification_engine.py
    206 tests/test_v27_rights_company_os.py
    208 omni_prod/autonomous_core.py
    208 omni_prod/economics_report.py
    208 tests/test_actual_cost_settlement.py
    208 tests/test_modifier_engine.py
    209 omni_prod/agent_os/truth_matrix.py
    214 omni_prod/capability_planner.py
    218 tests/test_preview_data_durability.py
    221 omni_prod/gate_replay.py
    222 omni_prod/planning/graph.py
    222 omni_prod/preview_router.py
    222 tests/test_release_policy.py
    223 omni_prod/agent_os/departments.py
    225 omni_prod/backup.py
    225 tests/test_discovery_and_approval.py
    227 omni_prod/intake/contract.py
    227 omni_prod/modifier_engine.py
    227 omni_prod/provider_usage.py
    227 tests/test_evidence_export.py
    227 tests/test_intake_assistant_he.py
    227 tests/test_m495_provider_router.py
    231 omni_prod/intelligence/inventory.py
    231 tests/test_content_only_site.py
    232 omni_prod/runtime_bindings.py
    233 omni_prod/planning/architect.py
    233 omni_prod/visual_edit.py
    236 omni_prod/agent_os/meta.py
    237 omni_prod/agent_os/agents.py
    237 omni_prod/intelligence/health.py
    240 tests/test_qstash_scheduler.py
    241 tests/integration/test_m5_build_economics_postgres.py
    244 omni_prod/skill_catalog.py
    244 tests/test_attempt_ledger.py
    245 omni_prod/verification_contract.py
    247 tests/test_m495_capability_repository.py
    248 omni_prod/preview_inspector.py
    248 tests/test_m5_economics_reconciliation.py
    249 omni_prod/provider_router.py
    249 tests/test_m5_build_contract_binding.py
    252 omni_prod/visual_qa.py
    253 omni_prod/autonomous_agents.py
    253 tests/test_v28_148ai_launch.py
    254 omni_prod/workspace.py
    257 omni_prod/repair_contracts.py
    258 omni_prod/company_os.py
    263 omni_prod/release_policy.py
    265 omni_prod/agent_os/runtime.py
    265 omni_prod/capability_registry.py
    266 omni_prod/attachments.py
    268 omni_prod/evidence_export.py
    271 tests/test_m495_capability_executor.py
    272 omni_prod/skills_registry.py
    274 tests/test_m5_llm_usage_evidence.py
    275 omni_prod/secrets_manager.py
    276 omni_prod/intelligence/matrix.py
    277 omni_prod/skills_runtime.py
    278 omni_prod/build_contract.py
    278 tools/ui_visual_edit/walkthrough.py
    282 tests/financial_fault_harness.py
    283 tests/test_workspace_version_conflict.py
    285 tests/test_agent_os.py
    287 tests/test_demand_driven_infrastructure.py
    288 omni_prod/attempt_ledger.py
    289 omni_prod/agents_registry.py
    293 tests/test_golden_mod_path_live_postgres.py
    294 tests/test_m49_sandbox_security.py
    299 omni_prod/rights_ip.py
    300 omni_prod/provider_pricing.py
    303 omni_prod/maintenance.py
    303 omni_prod/model_gateway.py
    310 tests/test_m4_worker.py
    315 omni_prod/preview_repository.py
    317 omni_prod/agent_os/skills.py
    325 omni_prod/project_lifecycle.py
    327 omni_prod/pricing.py
    330 tests/test_visual_edit.py
    333 tests/test_intelligence_plane.py
    333 tests/test_m49_clean_room.py
    333 tests/test_provider_quota_and_dialects.py
    335 omni_prod/truth_lock.py
    346 omni_prod/intake/interpreter.py
    350 omni_prod/unified_engine.py
    352 omni_prod/infrastructure_provisioner.py
    356 tests/test_m4_modification_engine.py
    356 tests/test_m5_infrastructure_contracts.py
    356 tests/test_real_docker_drain_recovery.py
    357 omni_prod/dependency_policy.py
    378 omni_prod/registry_audit.py
    384 tests/test_m4d2b_parity_and_worker.py
    421 omni_prod/subscription_store.py
    424 tests/test_m5_web_saas_acceptance.py
    425 omni_prod/consistency_gate.py
    433 omni_prod/job_repository.py
    433 tests/test_m5_managed_web_saas_profile.py
    434 tests/test_m5_media_provider_adapters.py
    438 omni_prod/web_saas_acceptance.py
    468 tests/test_plan_driven_execution.py
    475 tests/test_m4d2_live_fastapi_redis.py
    476 tools/deployment_verify.py
    483 tests/test_worker_deploy_recovery.py
    495 omni_prod/infrastructure_contracts.py
    498 omni_prod/capability_executor.py
    499 omni_prod/routed_gateway.py
    504 omni_prod/agent_os/recorder.py
    507 omni_prod/modification_repository.py
    526 omni_prod/preview_runtime.py
    529 omni_prod/intake/budget.py
    535 tests/test_conversation_os.py
    545 tests/test_m5_build_economics.py
    565 omni_prod/product_architect.py
    575 omni_prod/discovery.py
    578 omni_prod/conversation/supervisor.py
    583 omni_prod/identity_lifecycle.py
    590 omni_prod/providers/image_provider.py
    639 tests/test_modification_repository.py
    647 tests/test_intake_budget_pg.py
    653 tests/test_m4d1_atomic_accept.py
    654 omni_prod/postdeploy_checks.py
    679 tests/test_m4_acceptance.py
    750 omni_prod/providers/managed_web_saas.py
    773 tests/test_deployment_verification.py
    835 omni_prod/capability_repository.py
    853 tests/test_m4d2_live_postgres.py
   1082 tests/test_m3_preview_logic.py
   1574 omni_prod/worker_tasks.py
   3351 omni_prod/investor_app.py
  80494 total
```


## PATHS — נתיבים קשיחים

```
./omni_prod/autonomous_agents.py:74:    'the filesystem is read-only except /tmp, it runs as an unprivileged user, and it must listen on 0.0.0.0 '
./omni_prod/behavior_acceptance.py:12:only, data under /tmp), using the same `WebSaaSAcceptanceRunner` code the
./omni_prod/behavior_acceptance.py:53:data_dir = tempfile.mkdtemp(prefix="behavior-", dir="/tmp")  # fresh, scratch data for every run
./omni_prod/behavior_acceptance.py:54:env = dict(os.environ, PORT=str(port), HOME="/tmp", DATA_DIR=data_dir, PYTHONDONTWRITEBYTECODE="1")
./omni_prod/browser_probe.py:41:env = dict(os.environ, PORT=str(port), HOME="/tmp", DATA_DIR="/tmp", PYTHONDONTWRITEBYTECODE="1")
./omni_prod/dependency_policy.py:61:    'write files only under os.environ.get("DATA_DIR", "/tmp") (for example a SQLite database at '
./omni_prod/dependency_policy.py:62:    'os.path.join(os.environ.get("DATA_DIR", "/tmp"), "app.db")), never next to the code, and create that path at '
./omni_prod/postdeploy_checks.py:52:DATA = pathlib.Path(os.environ.get("DATA_DIR", "/tmp")) / "count.txt"
./omni_prod/preview_durability.py:27:DATA = pathlib.Path(os.environ.get("DATA_DIR", "/tmp")) / "count.txt"
./omni_prod/preview_runtime.py:11:source mount, a small `/tmp` tmpfs, a non-root user, and a host port that
./omni_prod/preview_runtime.py:47:# non-root user. `--tmpfs /tmp` gives the app writable scratch space while the
./omni_prod/preview_runtime.py:58:    # PermissionError on the first write to /tmp).
./omni_prod/preview_runtime.py:59:    '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777',
./omni_prod/preview_runtime.py:228:        '-e', 'HOME=/tmp',
./omni_prod/preview_runtime.py:230:        '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', f'DATA_DIR={"/data" if data_dir else "/tmp"}',
./omni_prod/preview_runtime.py:420:        # with this worker). Unset -> previews keep data only in /tmp.
./omni_prod/preview_smoke.py:26:    'use only the Python standard library (no install step runs), write only under /tmp (the rest is '
./omni_prod/preview_smoke.py:37:env = dict(os.environ, PORT=str(port), HOME="/tmp", DATA_DIR="/tmp", PYTHONDONTWRITEBYTECODE="1")
./omni_prod/runtime_bindings.py:102:            ('one fixed stack (Python stdlib + SQLite in /tmp); no durable data or API-contract design',),
./omni_prod/runtime_bindings.py:126:            ('input validation only when the user asks for it', 'data in /tmp (not durable)'),
./omni_prod/runtime_bindings.py:127:            verified_scope=('stdlib HTTP JSON API with SQLite in /tmp',)),
./omni_prod/runtime_bindings.py:167:            '$0 (worker host)', ('data in /tmp is lost when the preview stops', 'temporary sslip.io address, open to anyone with the link',
./omni_prod/sandbox.py:57:        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=256m",
./omni_prod/sandbox.py:62:        "--env", "HOME=/tmp",
./omni_prod/sandbox.py:68:        "--env", "DATA_DIR=/tmp",
./omni_prod/sandbox.py:69:        "--env", "PYTHONPYCACHEPREFIX=/tmp/pycache",
./omni_prod/visual_qa.py:51:env = dict(os.environ, PORT=str(port), HOME="/tmp", DATA_DIR="/tmp", PYTHONDONTWRITEBYTECODE="1")
./tests/integration/test_live_preview_runtime.py:116:            self.assertIn('/tmp', hc['Tmpfs'])
./tests/integration/test_live_preview_runtime.py:127:            self.assertEqual(sh("open('/tmp/x','w').write('ok')").returncode, 0)  # tmpfs scratch
./tests/test_behavior_acceptance_in_build.py:17:DATA = os.path.join(os.environ.get("DATA_DIR", "/tmp"), "items.json")
./tests/test_behavior_acceptance_in_build.py:69:    repository as the working directory, a writable /tmp."""
./tests/test_m3_preview_logic.py:172:        self.argv = build_run_argv(preview_id='prv_abc', contract=self.c, workdir='/tmp/omni-preview-prv_abc-x')
./tests/test_m3_preview_logic.py:181:        self.assertTrue(self.argv[i + 1].startswith('/tmp:'))
./tests/test_m3_preview_logic.py:202:        self.assertEqual(mount, 'type=bind,src=/tmp/omni-preview-prv_abc-x,dst=/workspace,readonly')
./tests/test_m3_preview_logic.py:299:        # 65534 gets PermissionError on /tmp.
./tests/test_m3_preview_logic.py:519:        return StartedPreview('cid1', 45678, '/tmp/omni-preview-prv_1-abc', contract(health_path='/healthz'))
./tests/test_m3_preview_logic.py:570:                                        'workdir': '/tmp/omni-preview-prv_1-abc', 'data_storage': 'temporary'})
./tests/test_m3_preview_logic.py:581:        self.assertEqual(provider.events, ['start', 'stop:cid1', 'rmdir:/tmp/omni-preview-prv_1-abc'])
./tests/test_m3_preview_logic.py:594:        crashed = StartedPreview('cid1', None, '/tmp/omni-preview-prv_1-abc', contract())
./tests/test_m3_preview_logic.py:600:        self.assertEqual(provider.events, ['start', 'stop:cid1', 'rmdir:/tmp/omni-preview-prv_1-abc'])
./tests/test_m3_preview_logic.py:631:        self.assertEqual(provider.events, ['start', 'stop:cid1', 'rmdir:/tmp/omni-preview-prv_1-abc'])
./tests/test_m3_preview_logic.py:643:        r.runtime = {'container_id': 'cid1', 'runtime_host': host, 'workdir': '/tmp/omni-preview-prv_1-abc'}
./tests/test_m3_preview_logic.py:651:        self.assertEqual(provider.events, ['stop:cid1', 'rmdir:/tmp/omni-preview-prv_1-abc'])
./tests/test_m3_preview_logic.py:811:                                   'worker-a', 45678, '/tmp/omni-preview-a', None, None)])
./tests/test_m495_provider_contracts.py:64:            "video/mp4", None, filename="clip.mp4", file_path="/tmp/clip.mp4"
./tests/test_m495_provider_contracts.py:66:        self.assertEqual(file_backed.file_path, "/tmp/clip.mp4")
./tests/test_m495_provider_contracts.py:71:                "image/png", b"bytes", filename="x.png", file_path="/tmp/x.png"
./tests/test_m49_clean_room.py:46:  PYTHONPATH=/tmp/m4d2b_vendor:/tmp/m49_pytest_vendor \\
./tests/test_m49_clean_room.py:323:        with open('/tmp/m49_clean_room_ids.json', 'w') as f:
./tests/test_m49_lifecycle.py:19:/tmp/m49_clean_room_ids.json, written by that test) rather than manually
./tests/test_m49_lifecycle.py:25:  PYTHONPATH=/tmp/m4d2b_vendor:/tmp/m49_pytest_vendor \\
./tests/test_m49_lifecycle.py:42:    if not os.path.exists('/tmp/m49_clean_room_ids.json'):
./tests/test_m49_lifecycle.py:43:        return ('/tmp/m49_clean_room_ids.json not found -- run tests/test_m49_clean_room.py '
./tests/test_m49_lifecycle.py:45:    with open('/tmp/m49_clean_room_ids.json') as f:
./tests/test_m49_lifecycle.py:61:    with open('/tmp/m49_clean_room_ids.json') as f:
./tests/test_m49_sandbox_security.py:35:    /tmp (tmpfs) and /output (rw bind mount) proven writable as a
./tests/test_m49_sandbox_security.py:128:ok, detail = try_write("/tmp/m49_write_test")
./tests/test_m4d2b_parity_and_worker.py:7:`/tmp/m4d2b_vendor` -- fastapi/psycopg/redis-py/rq/starlette checked out
./tests/test_m4d2_live_postgres.py:26:PYTHONPATH vendor directory (`/tmp/m4d2_vendor`), instead of a normal `pip
./tests/test_m5_web_saas_acceptance.py:205:        return SimpleNamespace(container_id='cid', host_port=43210, workdir='/tmp/w',
./tests/test_preview_data_durability.py:32:        self.assertIn('DATA_DIR=/tmp', argv)
./tests/test_preview_data_durability.py:77:            self.assertIn('DATA_DIR=/tmp', calls[0])
./tests/test_preview_data_durability.py:127:        return StartedPreview(f'cid-{preview_id}', port, f'/tmp/omni-preview-{preview_id}', CONTRACT,
./tests/test_preview_data_durability.py:197:                    return StartedPreview(f'c{port}', port, '/tmp/x', CONTRACT)
./tests/test_sandbox_runner_health.py:53:        self.assertIn("PYTHONPYCACHEPREFIX=/tmp/pycache", pairs)
./tools/m49_ready_invariant_check.py:4:/tmp/m49_clean_room_ids.json for identifiers (real, from the final
./tools/m49_ready_invariant_check.py:9:sys.path.insert(0, "/tmp/m4d2b_vendor")
./tools/m49_ready_invariant_check.py:12:with open("/tmp/m49_clean_room_ids.json") as f:
---- windows ----
```


## ENV VARS — שמות בלבד

```
environ.get("DATA_DIR"
environ.get("DOCKER_CERT_PATH"
environ.get("DOCKER_HOST"
environ.get("DOCKER_TLS_VERIFY"
environ.get("M5_DATABASE_URL"
environ.get("M5_GENAPP_LIVE"
environ.get("M5_LIVE_IMAGE"
environ.get("M5_LIVE_LLM_EXPECT_COST"
environ.get("M5_QSTASH_LIVE"
environ.get("M5_R2_LIVE"
environ.get("OMNI_ALLOWED_ORIGINS"
environ.get("OMNI_CHROMIUM"
environ.get("OMNI_GENAPP_SECRET_STORE_TOKEN_ENV"
environ.get("OMNI_S3_ACCESS_KEY"
environ.get("OMNI_S3_BUCKET"
environ.get("PORT"
environ.get("PYTHONPATH"
environ.get("QSTASH_TEST_DESTINATION"
environ.get("QSTASH_TOKEN"
environ.get("QSTASH_URL"
getenv("OMNI_ANDROID_KEYSTORE"
getenv("OMNI_ANDROID_KEY_ALIAS"
getenv("OMNI_ANDROID_KEY_PASSWORD"
getenv("OMNI_ANDROID_STORE_PASSWORD"
getenv("OMNI_ENV"
getenv("OMNI_PREVIEW_INSPECTOR"
getenv("OMNI_RUN_LIVE_INTEGRATION"
getenv("OMNI_SANDBOX_CPUS"
getenv("OMNI_SANDBOX_IMAGE"
getenv("OMNI_SANDBOX_MEMORY"
getenv("ONE48AI_ANDROID_KEYSTORE"
getenv("ONE48AI_ANDROID_KEY_ALIAS"
getenv("ONE48AI_ANDROID_KEY_PASSWORD"
getenv("ONE48AI_ANDROID_STORE_PASSWORD"
```


## ROUTES

```
./omni_prod/api_routes.py:13:    @router.get("/health/live")
./omni_prod/api_routes.py:17:    @router.get("/health/ready")
./omni_prod/diagnostics_app.py:24:@app.get("/_omni/preflight")
./omni_prod/investor_app.py:569:@app.get('/',response_class=HTMLResponse)
./omni_prod/investor_app.py:572:@app.get('/api/status')
./omni_prod/investor_app.py:587:@app.get('/api/international/readiness')
./omni_prod/investor_app.py:590:@app.get('/api/integrations')
./omni_prod/investor_app.py:593:@app.get('/api/benchmark/catalog')
./omni_prod/investor_app.py:598:@app.get('/api/targets/mobile/{platform}')
./omni_prod/investor_app.py:603:@app.get('/api/targets/game/{engine}')
./omni_prod/investor_app.py:608:@app.get('/api/source/mobile/{platform}')
./omni_prod/investor_app.py:615:@app.get('/api/source/game/{engine}')
./omni_prod/investor_app.py:621:@app.get('/api/agent-team')
./omni_prod/investor_app.py:625:@app.post('/api/billing/classify')
./omni_prod/investor_app.py:630:@app.post('/api/demo/build')
./omni_prod/investor_app.py:651:@app.get('/api/projects/{project_id}/history')
./omni_prod/investor_app.py:655:@app.get('/api/projects/{project_id}/versions/{version_id}/download')
./omni_prod/investor_app.py:666:@app.get('/api/projects/{project_id}/memory')
./omni_prod/investor_app.py:766:@app.post('/api/live/build')
./omni_prod/investor_app.py:814:@app.post('/api/v26/auth/register')
./omni_prod/investor_app.py:819:@app.post('/api/v26/auth/login')
./omni_prod/investor_app.py:824:@app.get('/api/v26/me')
./omni_prod/investor_app.py:830:@app.post('/api/v26/projects')
./omni_prod/investor_app.py:836:@app.get('/api/v26/projects')
./omni_prod/investor_app.py:841:@app.post('/api/v26/projects/{project_id}/build')
./omni_prod/investor_app.py:848:@app.get('/api/v26/projects/{project_id}/history')
./omni_prod/investor_app.py:853:@app.post('/api/v26/projects/{project_id}/patch')
./omni_prod/investor_app.py:859:@app.post('/api/v26/projects/{project_id}/restore')
./omni_prod/investor_app.py:865:@app.get('/api/v26/projects/{project_id}/export')
./omni_prod/investor_app.py:872:@app.post('/api/v26/projects/{project_id}/promote')
./omni_prod/investor_app.py:879:@app.post('/api/v26/brain/plan')
./omni_prod/investor_app.py:886:@app.post('/api/v26/projects/{project_id}/live-build')
./omni_prod/investor_app.py:906:@app.get('/api/v26/capabilities')
./omni_prod/investor_app.py:914:@app.get('/hosted/v26/{deployment_id}',response_class=HTMLResponse)
./omni_prod/investor_app.py:921:@app.post('/runtime/v26/{deployment_id}/register')
./omni_prod/investor_app.py:928:@app.post('/runtime/v26/{deployment_id}/login')
./omni_prod/investor_app.py:935:@app.get('/runtime/v26/{deployment_id}/data/{collection}')
./omni_prod/investor_app.py:942:@app.post('/runtime/v26/{deployment_id}/data/{collection}')
./omni_prod/investor_app.py:961:@app.get('/api/v25/parity')
./omni_prod/investor_app.py:971:@app.post('/api/v25/build')
./omni_prod/investor_app.py:977:@app.get('/api/v25/projects/{project_id}/export')
./omni_prod/investor_app.py:983:@app.post('/api/v25/projects/{project_id}/patch')
./omni_prod/investor_app.py:990:@app.post('/api/v25/projects/{project_id}/promote')
./omni_prod/investor_app.py:997:@app.get('/api/v25/source/omni-android')
./omni_prod/investor_app.py:1002:@app.get('/hosted/v25/{deployment_id}',response_class=HTMLResponse)
./omni_prod/investor_app.py:1016:@app.post('/runtime/v25/{deployment_id}/register')
./omni_prod/investor_app.py:1023:@app.post('/runtime/v25/{deployment_id}/login')
./omni_prod/investor_app.py:1030:@app.get('/runtime/v25/{deployment_id}/data/{collection}')
./omni_prod/investor_app.py:1038:@app.post('/runtime/v25/{deployment_id}/data/{collection}')
./omni_prod/investor_app.py:1062:@app.get('/assets/app.css')
./omni_prod/investor_app.py:1065:@app.get('/assets/app.js')
./omni_prod/investor_app.py:1068:@app.get('/assets/visual-edit.js')
./omni_prod/investor_app.py:1071:@app.get('/manifest.webmanifest')
./omni_prod/investor_app.py:1074:@app.get('/sw.js')
./omni_prod/investor_app.py:1081:@app.post('/api/v27/auth/register')
./omni_prod/investor_app.py:1086:@app.post('/api/v27/auth/login')
./omni_prod/investor_app.py:1091:@app.get('/api/v27/me')
./omni_prod/investor_app.py:1097:@app.post('/api/v27/projects')
./omni_prod/investor_app.py:1103:@app.get('/api/v27/projects')
./omni_prod/investor_app.py:1108:@app.post('/api/v27/projects/{project_id}/build')
./omni_prod/investor_app.py:1115:@app.get('/api/v27/projects/{project_id}/history')
./omni_prod/investor_app.py:1120:@app.post('/api/v27/projects/{project_id}/patch')
./omni_prod/investor_app.py:1126:@app.post('/api/v27/projects/{project_id}/restore')
./omni_prod/investor_app.py:1132:@app.get('/api/v27/projects/{project_id}/export')
./omni_prod/investor_app.py:1139:@app.get('/api/v27/projects/{project_id}/rights')
./omni_prod/investor_app.py:1144:@app.post('/api/v27/projects/{project_id}/rights/evidence')
./omni_prod/investor_app.py:1155:@app.post('/api/v27/projects/{project_id}/rights/review')
./omni_prod/investor_app.py:1165:@app.post('/api/v27/projects/{project_id}/rights/original-alternative')
./omni_prod/investor_app.py:1171:@app.post('/api/v27/projects/{project_id}/promote')
./omni_prod/investor_app.py:1178:@app.post('/api/v27/brain/plan')
./omni_prod/investor_app.py:1184:@app.get('/api/v27/rights/jurisdictions')
./omni_prod/investor_app.py:1188:@app.get('/api/v27/company-os')
./omni_prod/investor_app.py:1192:@app.get('/api/v27/company-os/departments/{department_id}')
./omni_prod/investor_app.py:1197:@app.post('/api/v27/company-os/triage')
./omni_prod/investor_app.py:1201:@app.post('/api/v27/company-os/ceo-brief')
./omni_prod/investor_app.py:1205:@app.post('/api/v27/company-os/release-council/evaluate')
./omni_prod/investor_app.py:1209:@app.post('/api/v27/projects/{project_id}/live-build')
./omni_prod/investor_app.py:1237:@app.get('/hosted/v27/{deployment_id}',response_class=HTMLResponse)
./omni_prod/investor_app.py:1244:@app.post('/runtime/v27/{deployment_id}/register')
./omni_prod/investor_app.py:1251:@app.post('/runtime/v27/{deployment_id}/login')
./omni_prod/investor_app.py:1258:@app.get('/runtime/v27/{deployment_id}/data/{collection}')
./omni_prod/investor_app.py:1265:@app.post('/runtime/v27/{deployment_id}/data/{collection}')
./omni_prod/investor_app.py:1284:@app.get('/api/v28/brand/readiness')
./omni_prod/investor_app.py:1288:@app.get('/api/v28/launch/readiness')
./omni_prod/investor_app.py:1292:@app.get('/api/v28/source/client/{platform}')
./omni_prod/investor_app.py:1300:@app.get('/api/v28/ui/translations')
./omni_prod/investor_app.py:1313:@app.get('/api/v28/pricing')
./omni_prod/investor_app.py:1317:@app.post('/api/v28/billing/checkout')
./omni_prod/investor_app.py:1330:@app.post('/api/v28/billing/stripe/webhook')
./omni_prod/investor_app.py:1341:@app.post('/api/v28/auth/register')
./omni_prod/investor_app.py:1350:@app.post('/api/v28/auth/login')
./omni_prod/investor_app.py:1360:@app.post('/api/v28/auth/logout')
./omni_prod/investor_app.py:1376:@app.get('/api/v28/auth/sessions')
./omni_prod/investor_app.py:1385:@app.post('/api/v28/auth/sessions/{session_id}/revoke')
./omni_prod/investor_app.py:1395:@app.post('/api/v28/auth/email-verification/request', status_code=202)
./omni_prod/investor_app.py:1407:@app.post('/api/v28/auth/verify-email')
./omni_prod/investor_app.py:1415:@app.post('/api/v28/auth/password-reset/request', status_code=202)
./omni_prod/investor_app.py:1422:@app.post('/api/v28/auth/password-reset/confirm')
./omni_prod/investor_app.py:1430:@app.post('/api/v28/auth/consents')
./omni_prod/investor_app.py:1440:@app.post('/api/v28/auth/data-export', status_code=202)
./omni_prod/investor_app.py:1450:@app.post('/api/v28/auth/account-deletion', status_code=202)
./omni_prod/investor_app.py:1460:@app.get('/api/v28/me')
./omni_prod/investor_app.py:1473:@app.get('/api/v28/me/subscription')
./omni_prod/investor_app.py:1480:@app.post('/api/v28/admin/subscription')
./omni_prod/investor_app.py:1491:@app.post('/api/v28/projects')
./omni_prod/investor_app.py:1503:@app.get('/api/v28/projects')
./omni_prod/investor_app.py:1510:@app.get('/api/v28/projects/search')
./omni_prod/investor_app.py:1522:@app.patch('/api/v28/projects/{project_id}')
./omni_prod/investor_app.py:1536:@app.post('/api/v28/projects/{project_id}/archive')
./omni_prod/investor_app.py:1550:@app.post('/api/v28/projects/{project_id}/unarchive')
./omni_prod/investor_app.py:1564:@app.delete('/api/v28/projects/{project_id}', status_code=202)
./omni_prod/investor_app.py:1576:@app.get('/api/v28/projects/{project_id}/state')
./omni_prod/investor_app.py:1588:@app.post('/api/v28/projects/{project_id}/build')
./omni_prod/investor_app.py:1598:@app.get('/api/v28/projects/{project_id}/history')
./omni_prod/investor_app.py:1618:@app.post('/api/v28/projects/{project_id}/patch')
./omni_prod/investor_app.py:1627:@app.post('/api/v28/projects/{project_id}/restore')
./omni_prod/investor_app.py:1641:@app.get('/api/v28/projects/{project_id}/export')
./omni_prod/investor_app.py:1651:@app.get('/api/v28/projects/{project_id}/rights')
./omni_prod/investor_app.py:1658:@app.post('/api/v28/projects/{project_id}/rights/original-alternative')
./omni_prod/investor_app.py:1667:@app.post('/api/v28/projects/{project_id}/branding')
./omni_prod/investor_app.py:1674:@app.post('/api/v28/projects/{project_id}/usage/quote')
./omni_prod/investor_app.py:1683:@app.post('/api/v28/projects/{project_id}/promote')
./omni_prod/investor_app.py:1799:@app.post('/api/v28/projects/{project_id}/discovery')
./omni_prod/investor_app.py:1817:@app.get('/api/v28/projects/{project_id}/discovery')
./omni_prod/investor_app.py:1827:@app.post('/api/v28/projects/{project_id}/discovery/answers')
./omni_prod/investor_app.py:1976:@app.post('/api/v28/projects/{project_id}/conversation')
./omni_prod/investor_app.py:2016:@app.get('/api/v28/projects/{project_id}/conversation')
./omni_prod/investor_app.py:2022:@app.get('/api/v28/projects/{project_id}/memory')
./omni_prod/investor_app.py:2071:@app.get('/api/v28/projects/{project_id}/builds/{build_id}/plan')
./omni_prod/investor_app.py:2133:@app.post('/api/v28/projects/{project_id}/approvals')
./omni_prod/investor_app.py:2165:@app.post('/api/v28/projects/{project_id}/build-contracts')
./omni_prod/investor_app.py:2228:@app.post('/api/v28/projects/{project_id}/builds')
./omni_prod/investor_app.py:2425:@app.get('/api/v28/projects/{project_id}/builds/latest')
./omni_prod/investor_app.py:2441:@app.get('/api/v28/projects/{project_id}/builds/{build_id}')
./omni_prod/investor_app.py:2471:@app.post('/api/v28/projects/{project_id}/builds/{build_id}/cancel')
./omni_prod/investor_app.py:2495:@app.get('/api/v28/projects/{project_id}/builds/{build_id}/events')
./omni_prod/investor_app.py:2552:@app.post('/api/v28/projects/{project_id}/versions/{version_id}/previews')
./omni_prod/investor_app.py:2588:@app.get('/api/v28/projects/{project_id}/previews/{preview_id}')
./omni_prod/investor_app.py:2618:@app.post('/api/v28/projects/{project_id}/previews/{preview_id}/access')
./omni_prod/investor_app.py:2632:@app.post('/api/v28/projects/{project_id}/previews/{preview_id}/sharing')
./omni_prod/investor_app.py:2647:@app.delete('/api/v28/projects/{project_id}/previews/{preview_id}')
./omni_prod/investor_app.py:2708:@app.post('/api/v28/projects/{project_id}/versions/{version_id}/modifications')
./omni_prod/investor_app.py:2772:@app.get('/api/v28/projects/{project_id}/modifications/latest')
./omni_prod/investor_app.py:2789:@app.post('/api/v28/projects/{project_id}/modifications/{modification_id}/cancel')
./omni_prod/investor_app.py:2804:@app.get('/api/v28/projects/{project_id}/modifications/{modification_id}/events')
./omni_prod/investor_app.py:2815:@app.get('/api/v28/projects/{project_id}/modifications/{modification_id}')
./omni_prod/investor_app.py:2833:@app.get('/api/v28/projects/{project_id}/modifications/{modification_id}/candidate')
./omni_prod/investor_app.py:2849:@app.post('/api/v28/projects/{project_id}/modifications/{modification_id}/accept')
./omni_prod/investor_app.py:2869:@app.post('/api/v28/projects/{project_id}/modifications/{modification_id}/reject')
./omni_prod/investor_app.py:2907:@app.post('/api/v28/projects/{project_id}/attachments')
./omni_prod/investor_app.py:2920:@app.get('/api/v28/projects/{project_id}/attachments')
./omni_prod/investor_app.py:2927:@app.get('/api/v28/projects/{project_id}/attachments/{attachment_id}')
./omni_prod/investor_app.py:2945:@app.delete('/api/v28/projects/{project_id}/attachments/{attachment_id}')
./omni_prod/investor_app.py:2964:@app.post('/api/v28/projects/{project_id}/versions/{version_id}/visual-edit/locate')
./omni_prod/investor_app.py:3004:@app.post('/api/v28/projects/{project_id}/rollback')
./omni_prod/investor_app.py:3020:@app.get('/api/v28/capabilities')
./omni_prod/investor_app.py:3032:@app.get('/api/v28/providers/status')
./omni_prod/investor_app.py:3045:@app.post('/api/v28/providers/replicate/check')
./omni_prod/investor_app.py:3046:@app.get('/api/v28/providers/replicate/check')
./omni_prod/investor_app.py:3075:@app.get('/r2-diagnostics', response_class=HTMLResponse)
./omni_prod/investor_app.py:3087:@app.post('/api/v28/providers/replicate/image-test')
./omni_prod/investor_app.py:3107:@app.get('/api/v28/providers/replicate/image-test')
./omni_prod/investor_app.py:3116:@app.get('/api/v28/providers/replicate/image-test/image')
./omni_prod/investor_app.py:3126:@app.get('/replicate-test', response_class=HTMLResponse)
./omni_prod/investor_app.py:3132:@app.get('/assets/replicate-test.js')
./omni_prod/investor_app.py:3137:@app.get('/api/v28/projects/{project_id}/builds/{build_id}/capabilities')
./omni_prod/investor_app.py:3172:@app.get('/api/v28/m5/status')
./omni_prod/investor_app.py:3202:@app.get('/api/v28/deployment')
./omni_prod/investor_app.py:3212:@app.get('/api/v28/integrations')
./omni_prod/investor_app.py:3221:@app.get('/api/v28/company-os')
./omni_prod/investor_app.py:3234:@app.post('/api/v28/projects/{project_id}/live-build')
./omni_prod/investor_app.py:3283:@app.get('/hosted/v28/{deployment_id}', response_class=HTMLResponse)
./omni_prod/investor_app.py:3291:@app.post('/runtime/v28/{deployment_id}/register')
./omni_prod/investor_app.py:3301:@app.post('/runtime/v28/{deployment_id}/login')
./omni_prod/investor_app.py:3311:@app.get('/runtime/v28/{deployment_id}/data/{collection}')
./omni_prod/investor_app.py:3321:@app.post('/runtime/v28/{deployment_id}/data/{collection}')
./omni_prod/investor_app.py:3346:@app.get('/brand/{asset_name}')
./omni_prod/observability.py:27:    @app.get("/_omni/metrics")
./omni_prod/sandbox_service.py:42:@app.get('/health')
./omni_prod/sandbox_service.py:49:@app.post('/run')
./omni_prod/unified_engine.py:103:    return f'''from fastapi import APIRouter\nrouter=APIRouter(prefix="/{module}", tags=["{module}"])\n@router.get("")\ndef list_{module}(): return {{"items": [], "module": "{module}"}}\n@router.post("")\ndef create_{singular}(payload: dict): return {{"id": "generated", **payload}}\n'''
./omni_prod/unified_engine.py:123:        repo['backend/app.py'] = '''from fastapi import FastAPI\napp=FastAPI(title="Omni Generated App")\n@app.get("/health")\ndef health(): return {"ok": True}\n'''
./tests/test_customer_font_security.py:10:    @app.get('/')
./tests/test_v7_readiness_regression.py:100:        create = source.split("def v28_create_project(", 1)[1].split("@app.get('/api/v28/projects')", 1)[0]
```


## AUTH

```
./infra/staging/verify_neon_bootstrap.py:34:    "creator_accounts", "creator_sessions", "creator_projects",
./omni_prod/active_jobs.py:23:Only SELECTs and Redis reads (the DB session is read-only); no model call, no write.
./omni_prod/active_jobs.py:143:        conn.read_only = True                       # the whole session is read-only
./omni_prod/agent_catalog.py:70:       ('signup', 'login', 'sessions', 'authorization', 'tenant isolation'),
./omni_prod/agent_catalog.py:146:       ('synchronization', 'sessions', 'reconnect', 'authority checks'), 'tested with at least two real participants or separate clients'),
./omni_prod/agent_os/agents.py:81:     'adds sign-in only when approved; platform identity lives in the platform', ('signup', 'login', 'session_management'),
./omni_prod/agent_os/resolver.py:18:SIGN_IN = ('signup', 'login', 'session_management', 'auth_test')
./omni_prod/agent_os/skills.py:34:    'Authentication': ('identity_auth_agent', 'security_agent', ('web',), '$0 (platform identity)', 'password hashes, session hashes only', ()),
./omni_prod/agent_os/skills.py:123:    'session_management': ((), (), 'generated-app session management not implemented; platform accounts are tracked separately'),
./omni_prod/agent_os/skills.py:173:    'csrf_check': (('omni_prod.browser_session:extract_session_token',), (U('tests/test_v24_auth.py'),), 'platform API only'),
./omni_prod/auth.py:18:    session_id: str | None = None
./omni_prod/auth.py:22:def issue_token(*, secret:str,user_id:str,org_id:str,role:str,ttl_seconds:int=3600,now:int|None=None,session_id:str|None=None)->str:
./omni_prod/auth.py:29:    if session_id is not None:
./omni_prod/auth.py:30:        if not session_id.strip(): raise ValueError('session_id must not be blank')
./omni_prod/auth.py:31:        claims['sid']=session_id
./omni_prod/autonomous_agents.py:89:    'Each persona has an id/role and HTTP steps. Every step has id, kind, acceptance_ids referencing only acceptance IDs from the approved ProductSpec, method, path and expect_status; optional headers/json/expect_json_contains/expect_text_contains/capture may be used. Use ${name} variables captured from earlier JSON responses so login/session and CRUD can be exercised end-to-end. Do not hard-code a showcase domain: derive paths and payloads from the generated product. '
./omni_prod/browser_session.py:1:"""Browser session transport: HttpOnly cookie for the web workspace, Bearer for API clients.
./omni_prod/browser_session.py:6:* login/register set ``148ai_session`` as HttpOnly, SameSite=Strict, path=/,
./omni_prod/browser_session.py:8:  for plain-http local development). No max_age: a browser-session cookie;
./omni_prod/browser_session.py:10:* ``Authorization: Bearer`` keeps working and takes precedence, so existing
./omni_prod/browser_session.py:12:* A request authenticated by the cookie that changes state (anything but
./omni_prod/browser_session.py:23:__all__ = ["COOKIE_NAME", "SessionTokenError", "browser_session_readiness", "cookie_settings",
./omni_prod/browser_session.py:24:           "extract_session_token"]
./omni_prod/browser_session.py:26:COOKIE_NAME = "148ai_session"
./omni_prod/browser_session.py:56:def extract_session_token(request, *, allowed_origins: Iterable[str]) -> tuple[str, str]:
./omni_prod/browser_session.py:58:    if raw.startswith("Bearer ") and raw[7:].strip():
./omni_prod/browser_session.py:59:        return raw[7:].strip(), "bearer"
./omni_prod/browser_session.py:62:    cookie = (getattr(request, "cookies", {}) or {}).get(COOKIE_NAME)
./omni_prod/browser_session.py:63:    if not cookie:
./omni_prod/browser_session.py:66:        raise SessionTokenError(403, "cross-site request refused for cookie session")
./omni_prod/browser_session.py:67:    return cookie, "cookie"
./omni_prod/browser_session.py:76:def cookie_settings(*, production: bool, env: Mapping[str, str] | None = None) -> dict:
./omni_prod/browser_session.py:81:def browser_session_readiness(*, production: bool, env: Mapping[str, str] | None = None) -> dict:
./omni_prod/browser_session.py:85:                "reason": "session cookie is not Secure (OMNI_SESSION_COOKIE_SECURE=0); acceptable only for local http development"}
./omni_prod/browser_session.py:87:            "reason": ("HttpOnly + Secure + SameSite=Strict cookie with same-origin check on writes; "
./omni_prod/credential_binding.py:39:        if any(token in self.secret_reference.lower() for token in ("bearer ", "sk-live-", "sk-proj-")):
./omni_prod/discovery.py:469:    lines.append('Sign-in: ' + {'none': 'NONE. Do not add login, sessions, users or roles.',
./omni_prod/identity_lifecycle.py:55:    session_id: str
./omni_prod/identity_lifecycle.py:66:    session_id: str
./omni_prod/identity_lifecycle.py:74:            "session_id": self.session_id,
./omni_prod/identity_lifecycle.py:117:    def update_password_and_revoke_sessions(self, user_id: str, password_hash: str, salt_b64: str, revoked_at: str) -> None: ...
./omni_prod/identity_lifecycle.py:119:    def create_session(self, session: SessionRecord) -> None: ...
./omni_prod/identity_lifecycle.py:120:    def session_by_id(self, session_id: str) -> SessionRecord | None: ...
./omni_prod/identity_lifecycle.py:121:    def touch_session(self, session_id: str, seen_at: str) -> None: ...
./omni_prod/identity_lifecycle.py:122:    def revoke_session(self, user_id: str, session_id: str, revoked_at: str) -> bool: ...
./omni_prod/identity_lifecycle.py:123:    def revoke_all_sessions(self, user_id: str, revoked_at: str) -> None: ...
./omni_prod/identity_lifecycle.py:124:    def list_sessions(self, user_id: str) -> tuple[SessionRecord, ...]: ...
./omni_prod/identity_lifecycle.py:137:        self._sessions: dict[str, SessionRecord] = {}
./omni_prod/identity_lifecycle.py:161:    def update_password_and_revoke_sessions(self, user_id: str, password_hash: str, salt_b64: str, revoked_at: str) -> None:
./omni_prod/identity_lifecycle.py:164:        self.revoke_all_sessions(user_id, revoked_at)
./omni_prod/identity_lifecycle.py:170:    def create_session(self, session: SessionRecord) -> None:
./omni_prod/identity_lifecycle.py:171:        self._sessions[session.session_id] = session
./omni_prod/identity_lifecycle.py:173:    def session_by_id(self, session_id: str) -> SessionRecord | None:
./omni_prod/identity_lifecycle.py:174:        return self._sessions.get(session_id)
./omni_prod/identity_lifecycle.py:176:    def touch_session(self, session_id: str, seen_at: str) -> None:
./omni_prod/identity_lifecycle.py:177:        session = self._sessions.get(session_id)
./omni_prod/identity_lifecycle.py:178:        if session:
./omni_prod/identity_lifecycle.py:179:            self._sessions[session_id] = replace(session, last_seen_at=seen_at)
./omni_prod/identity_lifecycle.py:181:    def revoke_session(self, user_id: str, session_id: str, revoked_at: str) -> bool:
./omni_prod/identity_lifecycle.py:182:        session = self._sessions.get(session_id)
./omni_prod/identity_lifecycle.py:183:        if not session or session.user_id != user_id:
./omni_prod/identity_lifecycle.py:185:        if session.revoked_at is None:
./omni_prod/identity_lifecycle.py:186:            self._sessions[session_id] = replace(session, revoked_at=revoked_at)
./omni_prod/identity_lifecycle.py:189:    def revoke_all_sessions(self, user_id: str, revoked_at: str) -> None:
./omni_prod/identity_lifecycle.py:190:        for session_id, session in tuple(self._sessions.items()):
./omni_prod/identity_lifecycle.py:191:            if session.user_id == user_id and session.revoked_at is None:
./omni_prod/identity_lifecycle.py:192:                self._sessions[session_id] = replace(session, revoked_at=revoked_at)
./omni_prod/identity_lifecycle.py:194:    def list_sessions(self, user_id: str) -> tuple[SessionRecord, ...]:
./omni_prod/identity_lifecycle.py:195:        return tuple(sorted((s for s in self._sessions.values() if s.user_id == user_id), key=lambda s: s.created_at, reverse=True))
./omni_prod/identity_lifecycle.py:239:    def _session(row) -> SessionRecord | None:
./omni_prod/identity_lifecycle.py:243:            session_id=str(row[0]), user_id=str(row[1]), token_hash=str(row[2]),
./omni_prod/identity_lifecycle.py:293:    def update_password_and_revoke_sessions(self, user_id: str, password_hash: str, salt_b64: str, revoked_at: str) -> None:
./omni_prod/identity_lifecycle.py:298:                    cur.execute("UPDATE creator_sessions SET revoked_at=COALESCE(revoked_at,%s) WHERE user_id=%s AND revoked_at IS NULL", (revoked_at, user_id))
./omni_prod/identity_lifecycle.py:306:    def create_session(self, session: SessionRecord) -> None:
./omni_prod/identity_lifecycle.py:311:                        "INSERT INTO creator_sessions(session_id,user_id,token_hash,created_at,expires_at,revoked_at,last_seen_at) VALUES(%s,%s,%s,%s,%s,%s,%s)",
./omni_prod/identity_lifecycle.py:312:                        (session.session_id, session.user_id, session.token_hash, session.created_at, session.expires_at, session.revoked_at, session.last_seen_at),
./omni_prod/identity_lifecycle.py:315:    def session_by_id(self, session_id: str) -> SessionRecord | None:
./omni_prod/identity_lifecycle.py:318:                cur.execute("SELECT session_id,user_id,token_hash,created_at,expires_at,revoked_at,last_seen_at FROM creator_sessions WHERE session_id=%s", (session_id,))
./omni_prod/identity_lifecycle.py:319:                return self._session(cur.fetchone())
./omni_prod/identity_lifecycle.py:321:    def touch_session(self, session_id: str, seen_at: str) -> None:
./omni_prod/identity_lifecycle.py:325:                    cur.execute("UPDATE creator_sessions SET last_seen_at=%s WHERE session_id=%s AND revoked_at IS NULL", (seen_at, session_id))
./omni_prod/identity_lifecycle.py:327:    def revoke_session(self, user_id: str, session_id: str, revoked_at: str) -> bool:
./omni_prod/identity_lifecycle.py:331:                    cur.execute("UPDATE creator_sessions SET revoked_at=COALESCE(revoked_at,%s) WHERE session_id=%s AND user_id=%s RETURNING session_id", (revoked_at, session_id, user_id))
./omni_prod/identity_lifecycle.py:334:    def revoke_all_sessions(self, user_id: str, revoked_at: str) -> None:
./omni_prod/identity_lifecycle.py:338:                    cur.execute("UPDATE creator_sessions SET revoked_at=COALESCE(revoked_at,%s) WHERE user_id=%s AND revoked_at IS NULL", (revoked_at, user_id))
./omni_prod/identity_lifecycle.py:340:    def list_sessions(self, user_id: str) -> tuple[SessionRecord, ...]:
./omni_prod/identity_lifecycle.py:343:                cur.execute("SELECT session_id,user_id,token_hash,created_at,expires_at,revoked_at,last_seen_at FROM creator_sessions WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
./omni_prod/identity_lifecycle.py:344:                return tuple(self._session(row) for row in cur.fetchall())  # type: ignore[misc]
./omni_prod/identity_lifecycle.py:406:    def _issue_session(self, user_id: str) -> str:
./omni_prod/identity_lifecycle.py:408:        session_id = "ses_" + secrets.token_urlsafe(18)
./omni_prod/identity_lifecycle.py:417:            session_id=session_id,
./omni_prod/identity_lifecycle.py:419:        self._repo.create_session(SessionRecord(
./omni_prod/identity_lifecycle.py:420:            session_id=session_id,
./omni_prod/identity_lifecycle.py:445:        return account.as_account(), self._issue_session(account.id)
./omni_prod/identity_lifecycle.py:454:        return account.as_account(), self._issue_session(account.id)
./omni_prod/identity_lifecycle.py:462:        if not claims.session_id:
./omni_prod/identity_lifecycle.py:463:            raise PermissionError("durable session required")
./omni_prod/identity_lifecycle.py:464:        session = self._repo.session_by_id(claims.session_id)
./omni_prod/identity_lifecycle.py:465:        if not session or session.user_id != claims.user_id:
./omni_prod/identity_lifecycle.py:466:            raise PermissionError("session revoked or unavailable")
./omni_prod/identity_lifecycle.py:467:        if session.revoked_at is not None:
./omni_prod/identity_lifecycle.py:468:            raise PermissionError("session revoked")
./omni_prod/identity_lifecycle.py:469:        if _as_datetime(session.expires_at) <= now:
./omni_prod/identity_lifecycle.py:470:            raise PermissionError("session expired")
./omni_prod/identity_lifecycle.py:471:        if not hmac.compare_digest(session.token_hash, _token_hash(token)):
./omni_prod/identity_lifecycle.py:476:        self._repo.touch_session(session.session_id, now.isoformat())
./omni_prod/identity_lifecycle.py:485:        if not claims.session_id or not self._repo.revoke_session(claims.user_id, claims.session_id, now.isoformat()):
./omni_prod/identity_lifecycle.py:486:            raise PermissionError("session not found")
./omni_prod/identity_lifecycle.py:488:    def revoke_session(self, user_id: str, session_id: str) -> None:
./omni_prod/identity_lifecycle.py:489:        if not self._repo.revoke_session(user_id, session_id, self._now().isoformat()):
./omni_prod/identity_lifecycle.py:490:            raise PermissionError("session not found or access denied")
./omni_prod/identity_lifecycle.py:492:    def list_sessions(self, user_id: str) -> tuple[SessionView, ...]:
./omni_prod/identity_lifecycle.py:493:        return tuple(SessionView(s.session_id, s.created_at, s.expires_at, s.revoked_at, s.last_seen_at) for s in self._repo.list_sessions(user_id))
./omni_prod/identity_lifecycle.py:549:        self._repo.update_password_and_revoke_sessions(
./omni_prod/identity_lifecycle.py:570:        self._repo.revoke_all_sessions(user_id, now)
./omni_prod/infrastructure_contracts.py:4:relational database, application auth/session secrets, object storage,
./omni_prod/infrastructure_contracts.py:59:    AUTH_SESSION = "auth_session"
./omni_prod/infrastructure_contracts.py:78:_INLINE_SECRET_MARKERS = ("bearer ", "sk-live-", "sk-proj-", "sk-ant-", "-----begin")
./omni_prod/infrastructure_registry.py:28:        "database, application auth/session secret, S3-compatible object storage, scheduled HTTP "
./omni_prod/infrastructure_registry.py:34:        InfrastructureRequirement("auth_session", "application-scoped durable authentication and sessions"),
./omni_prod/infrastructure_registry.py:49:# in-app sessions in its own runtime. Nothing is provisioned, so nothing here
./omni_prod/infrastructure_registry.py:58:        "authentication/sessions inside the app runtime. No platform-provisioned resources. "
./omni_prod/infrastructure_registry.py:64:        InfrastructureRequirement("auth_session", "in-app authentication and sessions stored in the embedded database",
./omni_prod/investor_app.py:67:from .browser_session import SessionTokenError, browser_session_readiness, cookie_settings, extract_session_token
./omni_prod/investor_app.py:96:@app.middleware('http')
./omni_prod/investor_app.py:100:        if not raw.startswith('Bearer '):
./omni_prod/investor_app.py:122:@app.middleware('http')
./omni_prod/investor_app.py:383:        'browser_session': browser_session_readiness(production=_PRODUCTION),
./omni_prod/investor_app.py:797:def _v26_bearer(request:Request)->str:
./omni_prod/investor_app.py:798:    # Bearer header (API clients) or the HttpOnly browser session cookie, with a
./omni_prod/investor_app.py:799:    # same-origin requirement for cookie-authenticated writes (CSRF guard).
./omni_prod/investor_app.py:801:        token, _transport = extract_session_token(request, allowed_origins=_ALLOWED_ORIGINS)
./omni_prod/investor_app.py:806:def _set_session_cookie(response: Response, token: str) -> None:
./omni_prod/investor_app.py:807:    response.set_cookie(value=token, **cookie_settings(production=_PRODUCTION))
./omni_prod/investor_app.py:809:def _clear_session_cookie(response: Response) -> None:
./omni_prod/investor_app.py:810:    settings = cookie_settings(production=_PRODUCTION)
./omni_prod/investor_app.py:811:    response.delete_cookie(settings['key'], path=settings['path'], secure=settings['secure'],
./omni_prod/investor_app.py:826:    try: a=_v26.account(_v26_bearer(request))
./omni_prod/investor_app.py:832:    try:return _v26.create_project(token=_v26_bearer(request),title=req.title)
./omni_prod/investor_app.py:838:    try:return {'projects':_v26.list_projects(token=_v26_bearer(request))}
./omni_prod/investor_app.py:844:    try:return _v26.build(token=_v26_bearer(request),project_id=project_id,prompt=req.prompt)
./omni_prod/investor_app.py:850:    try:return {'project_id':project_id,'versions':_v26.history(token=_v26_bearer(request),project_id=project_id)}
./omni_prod/investor_app.py:855:    try:return _v26.patch(token=_v26_bearer(request),project_id=project_id,payload={'files':req.files},message=req.message)
./omni_prod/investor_app.py:861:    try:return _v26.restore(token=_v26_bearer(request),project_id=project_id,version_id=req.version_id)
./omni_prod/investor_app.py:867:    try:payload=_v26.export(token=_v26_bearer(request),project_id=project_id,version_id=version_id)
./omni_prod/investor_app.py:875:    try:return _v26.promote(token=_v26_bearer(request),project_id=project_id,version_id=version_id)
./omni_prod/investor_app.py:881:    try:_v26.account(_v26_bearer(request))
./omni_prod/investor_app.py:889:    token=_v26_bearer(request)
./omni_prod/investor_app.py:908:    return {'release':'V26 Universal Pro','creator_security':['signup/login','PBKDF2 password hashing','signed session tokens','owner-scoped project IDs','cross-user denial'],
./omni_prod/investor_app.py:937:    token=_runtime_bearer(request)
./omni_prod/investor_app.py:944:    token=_runtime_bearer(request)
./omni_prod/investor_app.py:1011:def _runtime_bearer(request:Request)->str:
./omni_prod/investor_app.py:1013:    if not raw.startswith('Bearer '): raise HTTPException(401,'authentication required')
./omni_prod/investor_app.py:1032:    token=_runtime_bearer(request)
./omni_prod/investor_app.py:1040:    token=_runtime_bearer(request)
./omni_prod/investor_app.py:1078:def _v27_bearer(request:Request)->str:
./omni_prod/investor_app.py:1079:    return _v26_bearer(request)
./omni_prod/investor_app.py:1093:    try: a=_v27.account(_v27_bearer(request))
./omni_prod/investor_app.py:1099:    try:return _v27.create_project(token=_v27_bearer(request),title=req.title)
./omni_prod/investor_app.py:1105:    try:return {'projects':_v27.list_projects(token=_v27_bearer(request))}
./omni_prod/investor_app.py:1111:    try:return _v27.build(token=_v27_bearer(request),project_id=project_id,prompt=req.prompt,target_markets=tuple(req.target_markets))
./omni_prod/investor_app.py:1117:    try:return {'project_id':project_id,'versions':_v27.history(token=_v27_bearer(request),project_id=project_id)}
./omni_prod/investor_app.py:1122:    try:return _v27.patch(token=_v27_bearer(request),project_id=project_id,payload={'files':req.files},message=req.message)
./omni_prod/investor_app.py:1128:    try:return _v27.restore(token=_v27_bearer(request),project_id=project_id,version_id=req.version_id)
./omni_prod/investor_app.py:1134:    try:payload=_v27.export(token=_v27_bearer(request),project_id=project_id,version_id=version_id)
./omni_prod/investor_app.py:1141:    try:return _v27.rights_status(token=_v27_bearer(request),project_id=project_id)
./omni_prod/investor_app.py:1148:            token=_v27_bearer(request),project_id=project_id,right_kind=req.right_kind,
./omni_prod/investor_app.py:1161:    try:return _v27.verify_rights_evidence(token=_v27_bearer(request),project_id=project_id,evidence_id=req.evidence_id)
./omni_prod/investor_app.py:1167:    try:return _v27.original_alternative(token=_v27_bearer(request),project_id=project_id,prompt=req.prompt)
./omni_prod/investor_app.py:1174:    try:return _v27.promote(token=_v27_bearer(request),project_id=project_id,version_id=version_id)
./omni_prod/investor_app.py:1180:    try:_v27.account(_v27_bearer(request))
./omni_prod/investor_app.py:1212:    token=_v27_bearer(request)
./omni_prod/investor_app.py:1260:    token=_runtime_bearer(request)
./omni_prod/investor_app.py:1267:    token=_runtime_bearer(request)
./omni_prod/investor_app.py:1304:def _v28_bearer(request: Request) -> str:
./omni_prod/investor_app.py:1305:    return _v26_bearer(request)
./omni_prod/investor_app.py:1320:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1322:        session = StripeCheckoutClient().create_subscription(user_id=account.id, email=account.email, plan=req.plan)
./omni_prod/investor_app.py:1323:        return {'checkout_session_id': session.id, 'url': session.url, 'plan': session.plan, 'provider': 'stripe'}
./omni_prod/investor_app.py:1347:    _set_session_cookie(response, payload['token'])
./omni_prod/investor_app.py:1357:    _set_session_cookie(response, payload['token'])
./omni_prod/investor_app.py:1362:    # The browser cookie is always cleared, even if server-side revocation is
./omni_prod/investor_app.py:1363:    # unavailable (memory mode) or the session already expired.
./omni_prod/investor_app.py:1366:    # truthfully whether the server-side session was revoked.
./omni_prod/investor_app.py:1367:    _clear_session_cookie(response)
./omni_prod/investor_app.py:1369:        _m5_identity_service().logout(_v28_bearer(request))
./omni_prod/investor_app.py:1370:        return {'logged_out': True, 'server_session_revoked': True}
./omni_prod/investor_app.py:1372:        return {'logged_out': True, 'server_session_revoked': False, 'reason': str(exc.detail)}
./omni_prod/investor_app.py:1374:        return {'logged_out': True, 'server_session_revoked': False, 'reason': str(exc)}
./omni_prod/investor_app.py:1376:@app.get('/api/v28/auth/sessions')
./omni_prod/investor_app.py:1377:def v28_sessions(request: Request) -> dict:
./omni_prod/investor_app.py:1379:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1381:        return {'sessions': [x.to_dict() for x in _m5_identity_service().list_sessions(account.id)]}
./omni_prod/investor_app.py:1385:@app.post('/api/v28/auth/sessions/{session_id}/revoke')
./omni_prod/investor_app.py:1386:def v28_revoke_session(session_id: str, request: Request) -> dict:
./omni_prod/investor_app.py:1388:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1390:        _m5_identity_service().revoke_session(account.id, session_id)
./omni_prod/investor_app.py:1391:        return {'revoked': True, 'session_id': session_id}
./omni_prod/investor_app.py:1398:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1433:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1443:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1453:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1463:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1476:        return _v28.subscription(token=_v28_bearer(request))
./omni_prod/investor_app.py:1494:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1506:        return {'projects': _v28.list_projects(token=_v28_bearer(request))}
./omni_prod/investor_app.py:1513:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1525:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1539:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1553:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1567:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1579:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1592:        return _v28.build(token=_v28_bearer(request), project_id=project_id, prompt=req.prompt, target_markets=tuple(req.target_markets))
./omni_prod/investor_app.py:1601:        token = _v28_bearer(request)
./omni_prod/investor_app.py:1621:        return _v28.patch(token=_v28_bearer(request), project_id=project_id, payload={'files': req.files}, message=req.message)
./omni_prod/investor_app.py:1632:            _, key = _v28.resolve_project_key(token=_v28_bearer(request), project_id=project_id)
./omni_prod/investor_app.py:1635:        return _v28.restore(token=_v28_bearer(request), project_id=project_id, version_id=req.version_id)
./omni_prod/investor_app.py:1644:        payload = _v28.export(token=_v28_bearer(request), project_id=project_id, version_id=version_id)
./omni_prod/investor_app.py:1654:        return _v28.rights_status(token=_v28_bearer(request), project_id=project_id)
./omni_prod/investor_app.py:1661:        return _v28.original_alternative(token=_v28_bearer(request), project_id=project_id, prompt=req.prompt)
./omni_prod/investor_app.py:1670:        return _v28.set_project_branding(token=_v28_bearer(request), project_id=project_id, visible=req.visible, white_label_name=req.white_label_name)
./omni_prod/investor_app.py:1677:        d = _v28.authorize_live_usage(token=_v28_bearer(request), project_id=project_id, cost_class=req.cost_class, credits=req.credits,
./omni_prod/investor_app.py:1687:        return _v28.promote(token=_v28_bearer(request), project_id=project_id, version_id=version_id)
./omni_prod/investor_app.py:1791:    token = _v28_bearer(request)
./omni_prod/investor_app.py:1982:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2025:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2074:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2171:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2239:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2430:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2443:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2477:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2498:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2545:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2621:    preview (the router exchanges it for an HttpOnly cookie)."""
./omni_prod/investor_app.py:2626:    account = _v28.account(_v28_bearer(request))
./omni_prod/investor_app.py:2641:        account = _v28.account(_v28_bearer(request))
./omni_prod/investor_app.py:2701:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2711:    token = _v28_bearer(request)
./omni_prod/investor_app.py:2794:    account = _v28.account(_v28_bearer(request))
./omni_prod/investor_app.py:2900:    token = _v28_bearer(request)
./omni_prod/investor_app.py:3023:        _v28.account(_v28_bearer(request))
./omni_prod/investor_app.py:3035:        _v28.account(_v28_bearer(request))
./omni_prod/investor_app.py:3049:        _v28.account(_v28_bearer(request))
./omni_prod/investor_app.py:3061:        account = _v28.account(_v28_bearer(request))
./omni_prod/investor_app.py:3139:    token = _v28_bearer(request)
./omni_prod/investor_app.py:3215:        _v28.account(_v28_bearer(request))
./omni_prod/investor_app.py:3224:        _v28.account(_v28_bearer(request))
./omni_prod/investor_app.py:3237:    token = _v28_bearer(request)
./omni_prod/investor_app.py:3313:    token = _runtime_bearer(request)
./omni_prod/investor_app.py:3323:    token = _runtime_bearer(request)
./omni_prod/media_gateway.py:37:        if self.endpoint.api_key: headers['authorization']='Bearer '+self.endpoint.api_key
./omni_prod/model_gateway.py:186:                headers['Authorization'] = f'Bearer {self.endpoint.api_key}'
./omni_prod/modification_diff.py:26:    'admin', '.env', 'cors', 'session', 'credential', 'webhook',
./omni_prod/observability.py:8:    @app.middleware("http")
./omni_prod/postdeploy_checks.py:108:        headers['Authorization'] = f'Bearer {token}'
./omni_prod/postdeploy_checks.py:449:                             headers={'Authorization': f'Bearer {token}'})
./omni_prod/preview_access.py:13:The router accepts a token as `?__148ai_access=` (sets an HttpOnly cookie and
./omni_prod/preview_access.py:14:redirects to the clean URL), as the `omni_prv` cookie, or as the
./omni_prod/preview_access.py:16:reaches the generated app (cookie and header are stripped before proxying).
./omni_prod/preview_inspector.py:19:path, the box) back to that origin only. It never reads cookies, storage,
./omni_prod/preview_router.py:25:from http.cookies import SimpleCookie
./omni_prod/preview_router.py:104:def _strip_cookie(raw: str | None) -> str | None:
./omni_prod/preview_router.py:161:                    # Exchange the link token for an HttpOnly cookie and drop it from the address bar.
./omni_prod/preview_router.py:176:                       if k.lower() not in _HOP_BY_HOP and k.lower() not in (HEADER.lower(), 'cookie')}
./omni_prod/preview_router.py:177:            cookie = _strip_cookie(self.headers.get('Cookie'))
./omni_prod/preview_router.py:178:            if cookie:
./omni_prod/preview_router.py:179:                headers['Cookie'] = cookie
./omni_prod/product_architect.py:132:    Persistence and sessions are always needed (every contract has data and the
./omni_prod/product_architect.py:142:        # Directive 2026-10-09 §17 "no-login fidelity": sessions are not added
./omni_prod/product_architect.py:144:        "auth_session": not (no_login_requested(prompt) if no_login is None else no_login),
./omni_prod/product_architect.py:216:        # Fully content-only sites need neither user nor admin sessions.
./omni_prod/product_architect.py:254:            # "No sign-in" is honoured: one kind of user, no roles or sessions.
./omni_prod/product_architect.py:266:            "secure_session_lifecycle",
./omni_prod/product_architect.py:270:        ) if not (content_only and s in ("least_privilege_rbac", "secure_session_lifecycle")))
./omni_prod/product_architect.py:343:            Requirement("platform-auth", "Users authenticate through durable application sessions", "security"),
./omni_prod/product_architect.py:358:            # without adding application visitor sessions.
./omni_prod/product_architect.py:362:                "148AI platform-authenticated operator access; no generated-product visitor sign-in or sessions"
./omni_prod/providers/image_provider.py:352:        headers = {"Authorization": f"Bearer {self.resolve_reference(self.config.api_key_ref)}",
./omni_prod/providers/managed_web_saas.py:9:* auth_session    -> a per-app session signing secret
./omni_prod/providers/managed_web_saas.py:204:                                                "set OMNI_GENAPP_S3_ROLE_ARN (STS AssumeRole with a prefix-scoped session policy)")
./omni_prod/providers/managed_web_saas.py:266:    req = request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
./omni_prod/providers/managed_web_saas.py:318:    """Least-privilege session policy: object CRUD and listing under one prefix only."""
./omni_prod/providers/managed_web_saas.py:351:    other S3-compatible stores that implement AssumeRole with session policies)."""
./omni_prod/providers/managed_web_saas.py:357:    def issue(self, *, operator_access_key, operator_secret_key, role_arn, policy, session_name, ttl_seconds) -> dict:
./omni_prod/providers/managed_web_saas.py:362:        out = client.assume_role(RoleArn=role_arn, RoleSessionName=session_name[:64], Policy=policy,
./omni_prod/providers/managed_web_saas.py:366:                "session_token": out["SessionToken"],
./omni_prod/providers/managed_web_saas.py:374:    def _client(endpoint, region, access_key, secret_key, session_token):
./omni_prod/providers/managed_web_saas.py:378:                            aws_session_token=session_token)
./omni_prod/providers/managed_web_saas.py:380:    def verify(self, *, endpoint, bucket, prefix, region, access_key, secret_key, session_token=None) -> dict:
./omni_prod/providers/managed_web_saas.py:383:            client = self._client(endpoint, region, access_key, secret_key, session_token)
./omni_prod/providers/managed_web_saas.py:390:    def verify_denied(self, *, endpoint, bucket, key, region, access_key, secret_key, session_token=None) -> bool:
./omni_prod/providers/managed_web_saas.py:393:            self._client(endpoint, region, access_key, secret_key, session_token).get_object(Bucket=bucket, Key=key)
./omni_prod/providers/managed_web_saas.py:488:            InfrastructureKind.AUTH_SESSION: self._provision_auth_session,
./omni_prod/providers/managed_web_saas.py:539:    def _provision_auth_session(self, requirement, *, tenant_id, project_id, environment, idempotency_key):
./omni_prod/providers/managed_web_saas.py:541:        ref = self._generated_ref(project_id, environment, InfrastructureKind.AUTH_SESSION, "session_signing_secret")
./omni_prod/providers/managed_web_saas.py:544:        return self._binding(requirement, status=BindingStatus.LIVE, refs={"session_signing_secret": ref},
./omni_prod/providers/managed_web_saas.py:575:            policy=policy, session_name=name, ttl_seconds=self.config.s3_credential_ttl_seconds)
./omni_prod/providers/managed_web_saas.py:577:        for field in ("access_key_id", "secret_access_key", "session_token"):
./omni_prod/providers/managed_web_saas.py:588:                      session_token=creds.get("session_token"))
./omni_prod/providers/managed_web_saas.py:679:                    session_token=self.secret_store.resolve(binding.secret_references["session_token"]))
./omni_prod/providers/qstash_scheduler.py:63:                              headers={"Authorization": "Bearer " + self._token,
./omni_prod/providers/r2_credentials.py:60:              session_name, ttl_seconds) -> dict:
./omni_prod/providers/r2_credentials.py:85:            "session_token": base64.b64encode(("jwt/" + jwt).encode("ascii")).decode("ascii"),
./omni_prod/providers/replicate_connection.py:60:                          headers={'Authorization': 'Bearer ' + token,
./omni_prod/providers/replicate_image_test.py:41:            'session_token_present': bool(creds.token)},
./omni_prod/repair_contracts.py:43:    re.compile(r'(?i)\b(?:authorization\s*:\s*bearer)\s+\S+'),
./omni_prod/runtime_bindings.py:220:                 ('the plan view still lists "login and sessions" from ProductArchitect for a "no login" request',)),
./omni_prod/secrets_manager.py:48:# Generated apps get their own credentials (database role password, session
./omni_prod/secrets_manager.py:147:        # Universal Auth credentials and bearer tokens must never follow redirects.
./omni_prod/secrets_manager.py:194:            headers['Authorization'] = 'Bearer ' + token
./omni_prod/secret_redaction.py:4:_BEARER = re.compile(r'(?i)(authorization:\s*bearer\s+)([^\s]+)')
./omni_prod/secret_scan.py:23:    ("bearer_token", re.compile(r"Authorization\s*:\s*Bearer\s+([A-Za-z0-9._~+/=-]{16,})", re.I)),
./omni_prod/skills_runtime.py:149:        'there is no login / no users ("בלי התחברות"), do not add sign-up, login, sessions, roles or permissions anywhere '
./omni_prod/stripe_billing.py:39:    endpoint = 'https://api.stripe.com/v1/checkout/sessions'
./omni_prod/stripe_billing.py:64:            'success_url': self.base_url + '/?billing=success&session_id={CHECKOUT_SESSION_ID}',
./omni_prod/stripe_billing.py:72:            'Authorization': 'Bearer ' + self.secret_key,
./omni_prod/stripe_billing.py:80:        session_id = str(body.get('id', ''))
./omni_prod/stripe_billing.py:82:        if not session_id or not url.startswith('https://'):
./omni_prod/stripe_billing.py:84:        return CheckoutSession(session_id, url, code.value)
./omni_prod/stripe_billing.py:123:    SUPPORTED = {'checkout.session.completed', 'checkout.session.async_payment_succeeded',
./omni_prod/stripe_billing.py:141:            if event_type.startswith('checkout.session.'):
./omni_prod/stripe_billing.py:170:            source = obj.get('subscription') if event_type.startswith('checkout.session.') else obj.get('id')
./omni_prod/unified_engine.py:128:        repo['frontend/src/auth.js'] = "export const authHeader=t=>({Authorization:`Bearer ${t}`});\n"
./omni_prod/verification_contract.py:51:    'deployment_endpoint', 'commit_sha', 'schema_compatible', 'register_synthetic_user', 'session_identity',
./omni_prod/web_saas_acceptance.py:13:import http.cookiejar
./omni_prod/web_saas_acceptance.py:108:    """Stateful stdlib HTTP client: preserves cookies across persona steps."""
./omni_prod/web_saas_acceptance.py:111:        jar = http.cookiejar.CookieJar()
./omni_prod/web_saas_acceptance.py:146:    # back, truncated. Synthetic test data only; never headers or cookies.
./omni_prod/web_security.py:2:from fastapi.middleware.cors import CORSMiddleware
./omni_prod/web_security.py:9:    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,
./omni_prod/web_security.py:13:    @app.middleware('http')
./scripts/run_v28_http_acceptance.py:58:    u1=register('owner@148ai.test'); u2=register('intruder@148ai.test'); h1={'Authorization':'Bearer '+u1['token']}; h2={'Authorization':'Bearer '+u2['token']}
./scripts/run_v28_http_acceptance.py:85:        rh={'Authorization':'Bearer '+rr['token']}; out['generated_app_auth_create_status']=req(base,f'/runtime/v28/{dep}/data/items','POST',{'payload':{'name':'record'}},rh)[0]
./tests/integration/test_m5_managed_web_saas_live.py:12:  (STS AssumeRole with session policies; optional OMNI_GENAPP_S3_STS_ENDPOINT)
./tests/integration/test_profit_billing_events_pg.py:89:    return BillingEntitlementEvent(eid, 'u', plan, 'checkout.session.completed', source, created)
./tests/integration/test_r2_generated_storage_live.py:52:                policy=scoped_object_policy(cfg.s3_bucket, prefix), session_name=app, ttl_seconds=900)
./tests/integration/test_r2_generated_storage_live.py:56:                                  aws_session_token=creds["session_token"])
./tests/integration/test_v28_creator_persistence.py:18:    def test_session_revocation_survives_service_instance_change(self):
./tests/integration/test_v28_creator_persistence.py:19:        email=f'session-{uuid.uuid4().hex}@example.com'
./tests/integration/test_v28_creator_persistence.py:24:        sessions=b.identity.list_sessions(acct.id)
./tests/integration/test_v28_creator_persistence.py:25:        self.assertEqual(len(sessions),1)
./tests/integration/test_v28_creator_persistence.py:26:        b.identity.revoke_session(acct.id,sessions[0].session_id)
./tests/integration/test_v28_creator_persistence.py:30:                cur.execute('SELECT token_hash FROM creator_sessions WHERE session_id=%s',(sessions[0].session_id,))
./tests/test_customer_economics_views.py:167:        h = {"Authorization": "Bearer " + reg["token"]}
./tests/test_demand_driven_infrastructure.py:59:        self.assertEqual(_modes(c), {"database": "SELF_CONTAINED", "auth_session": "SELF_CONTAINED"})
./tests/test_demand_driven_infrastructure.py:80:        self.assertEqual(_modes(c), {"database": "PLATFORM_MANAGED", "auth_session": "PLATFORM_MANAGED"})
./tests/test_demand_driven_infrastructure.py:83:        self.assertTrue(all("database" in u or "auth_session" in u for u in ctx.exception.unknown))
./tests/test_demand_driven_infrastructure.py:91:        self.assertEqual(_modes(c), {"database": "SELF_CONTAINED", "auth_session": "SELF_CONTAINED",
./tests/test_demand_driven_infrastructure.py:109:        self.assertEqual(_modes(c), {"database": "SELF_CONTAINED", "auth_session": "SELF_CONTAINED",
./tests/test_demand_driven_infrastructure.py:131:                         ["database", "auth_session", "object_storage", "scheduled_http", "outbound"])
./tests/test_deployment_verification.py:314:                  'set_cookie': False, 'sleep_on': None, 'drop_on': None, 'huge_on': None, 'html_on': None,
./tests/test_deployment_verification.py:337:                return stub.tokens.get((self.headers.get('Authorization') or '').removeprefix('Bearer '))
./tests/test_deployment_verification.py:343:                                  'cookie': self.headers.get('Cookie')})
./tests/test_deployment_verification.py:361:                cookie = [('Set-Cookie', 'track=1; Path=/')] if stub.f['set_cookie'] else []
./tests/test_deployment_verification.py:367:                                                       'note': 'free text <script> must not be copied'}}, extra=cookie)
./tests/test_deployment_verification.py:371:                    return self._send(200, {} if stub.f['no_token'] else {'token': tok}, extra=cookie)
./tests/test_deployment_verification.py:501:    def test_pr9_contracts_session_identity_and_conversation_shape(self):
./tests/test_deployment_verification.py:502:        r = self.run_stub(me_wrong_user=True)                       # session resolves to someone else
./tests/test_deployment_verification.py:503:        self.assertEqual((r['verdict'], self.status(r, 'session_identity')), (vc.FAILED, vc.FAIL))
./tests/test_deployment_verification.py:516:        r = self.run_stub(no_token=True)                       # register answers without a session token
./tests/test_deployment_verification.py:584:    # --- attacks: redirects, cookies, injection, token leakage --------------
./tests/test_deployment_verification.py:595:    def test_redirect_after_login_does_not_forward_the_bearer_token(self):
./tests/test_deployment_verification.py:614:    def test_cookies_are_never_stored_or_sent(self):
./tests/test_deployment_verification.py:615:        stub = _Stub(set_cookie=True)
./tests/test_deployment_verification.py:618:        self.assertTrue(all(s['cookie'] is None for s in stub.seen))
./tests/test_deployment_verification.py:625:        self.assertNotIn('sess-', text)                                       # session tokens
./tests/test_deployment_verification.py:626:        self.assertNotIn('Bearer', text)                                      # echoed Authorization header
./tests/test_discovery_and_approval.py:72:        self.assertNotIn('auth_session', {i.kind for i in c.infrastructure})
./tests/test_discovery_endpoints.py:45:        self.patches = [patch.object(investor_app, '_v28', v28), patch.object(investor_app, '_v28_bearer', return_value='tok'),
./tests/test_evidence_json.py:27:    'at': datetime(2026, 10, 7, 14, 36, tzinfo=timezone.utc), 'kinds': {'database', 'auth_session'},
./tests/test_evidence_json.py:43:        self.assertEqual(data['kinds'], ['auth_session', 'database'])
./tests/test_infisical_secret_store.py:15:REF = "vault:secret/data/148ai/generated-apps/project/preview/auth_session/signing"
./tests/test_infisical_secret_store.py:47:        assert req.get_header("Authorization") == "Bearer access-token-test"
./tests/test_intelligence_plane.py:166:        for pattern in ('sk-', 'AIza', 'r8_', 'Bearer '):
./tests/test_m495_truth_readiness_api.py:67:            headers={"Authorization": f"Bearer {token}"},
./tests/test_m495_truth_readiness_api.py:80:            headers={"Authorization": f"Bearer {token}"},
./tests/test_m495_truth_readiness_api.py:97:                headers={"Authorization": f"Bearer {token}"},
./tests/test_m495_truth_readiness_api.py:118:                headers={"Authorization": f"Bearer {owner_token}"},
./tests/test_m495_truth_readiness_api.py:132:                headers={"Authorization": f"Bearer {other_token}"},
./tests/test_m49_clean_room.py:201:        h = {'Authorization': 'Bearer ' + reg['token']}
./tests/test_m49_lifecycle.py:91:        cls.h = {'Authorization': 'Bearer ' + _IDS['token']}
./tests/test_m4d2b_parity_and_worker.py:161:        h = {'Authorization': 'Bearer ' + reg['token']}
./tests/test_m4d2b_parity_and_worker.py:199:        h = {'Authorization': 'Bearer ' + reg['token']}
./tests/test_m4d2b_parity_and_worker.py:285:        h = {'Authorization': 'Bearer ' + reg['token']}
./tests/test_m4d2b_parity_and_worker.py:352:        h = {'Authorization': 'Bearer ' + reg['token']}
./tests/test_m4d2_live_fastapi_redis.py:127:        h = {'Authorization': 'Bearer ' + reg['token']}
./tests/test_m4d2_live_fastapi_redis.py:148:        h = {'Authorization': 'Bearer ' + reg['token']}
./tests/test_m4d2_live_fastapi_redis.py:212:        h = {'Authorization': 'Bearer ' + reg['token']}
./tests/test_m4d2_live_fastapi_redis.py:256:        h = {'Authorization': 'Bearer ' + reg['token']}
./tests/test_m4d2_live_fastapi_redis.py:290:        h = {'Authorization': 'Bearer ' + reg['token']}
./tests/test_m4d2_live_fastapi_redis.py:325:        h1 = {'Authorization': 'Bearer ' + reg1['token']}
./tests/test_m4d2_live_fastapi_redis.py:326:        h2 = {'Authorization': 'Bearer ' + reg2['token']}
./tests/test_m4d2_live_fastapi_redis.py:375:        h = {'Authorization': 'Bearer ' + reg['token']}
./tests/test_m4d2_live_postgres.py:465:    modification_repository.py and workspace.py as of this session):
./tests/test_m5_browser_session.py:1:"""M5 remediation: browser sessions use an HttpOnly cookie; Bearer stays for API clients."""
./tests/test_m5_browser_session.py:7:from omni_prod.browser_session import (
./tests/test_m5_browser_session.py:8:    COOKIE_NAME, SessionTokenError, cookie_settings, extract_session_token, browser_session_readiness)
./tests/test_m5_browser_session.py:14:    def __init__(self, method="GET", headers=None, cookies=None, host="app.148ai.example", scheme="https"):
./tests/test_m5_browser_session.py:17:        self.cookies = cookies or {}
./tests/test_m5_browser_session.py:22:    def test_bearer_header_still_works_and_wins(self):
./tests/test_m5_browser_session.py:23:        req = _Req("POST", headers={"Authorization": "Bearer api-token"}, cookies={COOKIE_NAME: "cookie-token"})
./tests/test_m5_browser_session.py:24:        self.assertEqual(extract_session_token(req, allowed_origins=()), ("api-token", "bearer"))
./tests/test_m5_browser_session.py:26:    def test_cookie_authenticates_safe_requests(self):
./tests/test_m5_browser_session.py:27:        self.assertEqual(extract_session_token(_Req("GET", cookies={COOKIE_NAME: "c"}), allowed_origins=()),
./tests/test_m5_browser_session.py:28:                         ("c", "cookie"))
./tests/test_m5_browser_session.py:30:    def test_cookie_write_requires_same_origin(self):
./tests/test_m5_browser_session.py:31:        ok = _Req("POST", headers={"Origin": "https://app.148ai.example"}, cookies={COOKIE_NAME: "c"})
./tests/test_m5_browser_session.py:32:        self.assertEqual(extract_session_token(ok, allowed_origins=())[0], "c")
./tests/test_m5_browser_session.py:33:        fetch_site = _Req("DELETE", headers={"Sec-Fetch-Site": "same-origin"}, cookies={COOKIE_NAME: "c"})
./tests/test_m5_browser_session.py:34:        self.assertEqual(extract_session_token(fetch_site, allowed_origins=())[0], "c")
./tests/test_m5_browser_session.py:35:        allowed = _Req("PATCH", headers={"Origin": "https://studio.148ai.example"}, cookies={COOKIE_NAME: "c"})
./tests/test_m5_browser_session.py:36:        self.assertEqual(extract_session_token(allowed, allowed_origins=("https://studio.148ai.example",))[0], "c")
./tests/test_m5_browser_session.py:40:                extract_session_token(_Req("POST", headers=headers, cookies={COOKIE_NAME: "c"}), allowed_origins=())
./tests/test_m5_browser_session.py:45:            extract_session_token(_Req("GET"), allowed_origins=())
./tests/test_m5_browser_session.py:48:            extract_session_token(_Req("GET", headers={"Authorization": "Basic abc"}), allowed_origins=())
./tests/test_m5_browser_session.py:52:    def test_production_cookie_is_httponly_secure_strict(self):
./tests/test_m5_browser_session.py:53:        s = cookie_settings(production=True, env={})
./tests/test_m5_browser_session.py:56:        self.assertNotIn("max_age", s)  # browser-session cookie; token expiry stays server-side
./tests/test_m5_browser_session.py:59:        self.assertFalse(cookie_settings(production=False, env={"OMNI_SESSION_COOKIE_SECURE": "0"})["secure"])
./tests/test_m5_browser_session.py:60:        self.assertTrue(cookie_settings(production=True, env={"OMNI_SESSION_COOKIE_SECURE": "0"})["secure"])
./tests/test_m5_browser_session.py:61:        self.assertTrue(cookie_settings(production=False, env={})["secure"])
./tests/test_m5_browser_session.py:63:    def test_readiness_never_calls_insecure_cookie_hardened(self):
./tests/test_m5_browser_session.py:64:        self.assertEqual(browser_session_readiness(production=True, env={})["status"], "PARTIAL")
./tests/test_m5_browser_session.py:65:        dev = browser_session_readiness(production=False, env={"OMNI_SESSION_COOKIE_SECURE": "0"})
./tests/test_m5_browser_session.py:74:        self.assertIn("localStorage.removeItem('148ai_token')", js)  # migrates old sessions away
./tests/test_m5_build_economics.py:427:             patch.object(investor_app, '_v28_bearer', return_value='tok'), \
./tests/test_m5_creator_workspace.py:45:                                                         ("database", "auth_session", "object_storage", "scheduled_http", "outbound")}},
./tests/test_m5_creator_workspace.py:57:                         {"database", "auth_session", "object_storage", "scheduled_http", "outbound"})
./tests/test_m5_generated_app_storage_isolation.py:4:The fake object store below ENFORCES the session policy attached to issued
./tests/test_m5_generated_app_storage_isolation.py:30:    """Fake S3: every request is evaluated against the credential's session policy."""
./tests/test_m5_generated_app_storage_isolation.py:37:    def issue(self, *, operator_access_key, operator_secret_key, role_arn, policy, session_name, ttl_seconds):
./tests/test_m5_generated_app_storage_isolation.py:39:        key = f"ASIA{len(self.credentials):04d}{session_name[-8:]}"
./tests/test_m5_generated_app_storage_isolation.py:42:                "session_token": "scoped-token-" + key, "expires_at": "2026-10-04T23:00:00Z"}
./tests/test_m5_generated_app_storage_isolation.py:49:    def verify(self, *, endpoint, bucket, prefix, region, access_key, secret_key, session_token=None):
./tests/test_m5_generated_app_storage_isolation.py:53:    def verify_denied(self, *, endpoint, bucket, key, region, access_key, secret_key, session_token=None):
./tests/test_m5_generated_app_storage_isolation.py:97:            self.assertEqual(set(b.secret_references), {"access_key_id", "secret_access_key", "session_token"})
./tests/test_m5_identity_lifecycle.py:37:    def test_register_is_unverified_and_session_token_is_only_hashed_at_rest(self):
./tests/test_m5_identity_lifecycle.py:46:        self.assertTrue(claims.session_id)
./tests/test_m5_identity_lifecycle.py:47:        session = self.repo.session_by_id(claims.session_id)
./tests/test_m5_identity_lifecycle.py:48:        self.assertEqual(session.token_hash, hashlib.sha256(token.encode()).hexdigest())
./tests/test_m5_identity_lifecycle.py:49:        self.assertNotEqual(session.token_hash, token)
./tests/test_m5_identity_lifecycle.py:62:    def test_password_reset_token_is_hashed_expires_and_success_revokes_sessions(self):
./tests/test_m5_identity_lifecycle.py:63:        account, session_token = self.identity.register(email="reset@example.com", password="StrongPass123!")
./tests/test_m5_identity_lifecycle.py:74:        with self.assertRaisesRegex(PermissionError, "session revoked"):
./tests/test_m5_identity_lifecycle.py:75:            self.identity.authenticate(session_token)
./tests/test_m5_identity_lifecycle.py:80:        account, token = self.identity.register(email="sessions@example.com", password="StrongPass123!")
./tests/test_m5_identity_lifecycle.py:83:        session_id = verify_token(token, secret=SECRET, now=int(self.clock.now().timestamp())).session_id
./tests/test_m5_identity_lifecycle.py:84:        second.revoke_session(account.id, session_id)
./tests/test_m5_identity_lifecycle.py:85:        with self.assertRaisesRegex(PermissionError, "session revoked"):
./tests/test_m5_identity_lifecycle.py:103:    def test_list_sessions_never_exposes_token_hash(self):
./tests/test_m5_identity_lifecycle.py:105:        payload = self.identity.list_sessions(account.id)
./tests/test_m5_identity_lifecycle.py:113:    def test_migration_has_durable_sessions_hashed_one_time_tokens_consent_and_privacy_requests(self):
./tests/test_m5_identity_lifecycle.py:115:        for table in ("creator_sessions", "creator_identity_tokens", "creator_consents", "creator_privacy_requests"):
./tests/test_m5_infrastructure_contracts.py:103:        self.assertEqual(required, {"database", "auth_session", "object_storage", "scheduled_http", "outbound"})
./tests/test_m5_infrastructure_contracts.py:107:        closure_a = MANAGED_WEB_SAAS_V1.dependency_closure(("auth_session", "scheduled_http"))
./tests/test_m5_infrastructure_contracts.py:108:        closure_b = MANAGED_WEB_SAAS_V1.dependency_closure(("scheduled_http", "auth_session"))
./tests/test_m5_infrastructure_contracts.py:113:        self.assertEqual(closure_a, MANAGED_WEB_SAAS_V1.dependency_closure(("auth_session", "scheduled_http")))
./tests/test_m5_infrastructure_contracts.py:165:            self._binding(public_config={"note": "Bearer abc.def"})
./tests/test_m5_managed_web_saas_profile.py:109:    def issue(self, *, operator_access_key, operator_secret_key, role_arn, policy, session_name, ttl_seconds):
./tests/test_m5_managed_web_saas_profile.py:111:        self.issued.append(session_name)
./tests/test_m5_managed_web_saas_profile.py:113:        return {"access_key_id": f"ASIA-{n}-{session_name}", "secret_access_key": f"scoped-secret-{n}",
./tests/test_m5_managed_web_saas_profile.py:114:                "session_token": f"scoped-token-{n}", "expires_at": "2099-01-01T00:00:00Z"}
./tests/test_m5_managed_web_saas_profile.py:116:    def verify(self, *, endpoint, bucket, prefix, region, access_key, secret_key, session_token=None):
./tests/test_m5_managed_web_saas_profile.py:121:    def verify_denied(self, *, endpoint, bucket, key, region, access_key, secret_key, session_token=None):
./tests/test_m5_media_provider_adapters.py:207:        self.assertTrue(all(h == "Bearer img-secret-key" for h in api.auth_headers[:1]))
./tests/test_m5_product_architect.py:57:        self.assertTrue({"database", "auth_session", "object_storage", "scheduled_http", "outbound"}.issubset(infra))
./tests/test_m5_ssrf_guard.py:82:        req = request.Request("https://cdn.provider.example/x.png", headers={"Authorization": "Bearer k"})
./tests/test_m5_web_saas_acceptance.py:65:             'path': '/api/me', 'headers': {'Authorization': 'Bearer ${token}'},
./tests/test_m5_web_saas_acceptance.py:68:             'path': '/api/items', 'headers': {'Authorization': 'Bearer ${token}'},
./tests/test_m5_web_saas_acceptance.py:71:             'path': '/api/items/${item_id}', 'headers': {'Authorization': 'Bearer ${token}'},
./tests/test_m5_web_saas_acceptance.py:74:             'path': '/api/items/${item_id}', 'headers': {'Authorization': 'Bearer ${token}'},
./tests/test_m5_web_saas_acceptance.py:77:             'path': '/api/items/${item_id}', 'headers': {'Authorization': 'Bearer ${token}'},
./tests/test_m5_web_saas_acceptance.py:80:             'path': '/api/jobs', 'headers': {'Authorization': 'Bearer ${token}'},
./tests/test_m5_web_saas_acceptance.py:127:        self.assertEqual(transport.calls[1]['headers']['Authorization'], 'Bearer tok-1')
./tests/test_m5_web_saas_acceptance.py:322:    def test_real_http_session_executes_full_behavioral_flow(self):
./tests/test_m5_web_saas_acceptance.py:348:                return self.headers.get('authorization') == 'Bearer tok-1'
./tests/test_preview_access.py:91:    def test_owner_link_becomes_a_cookie_and_the_token_never_reaches_the_app(self):
./tests/test_preview_access.py:99:        path, cookie, header = _App.seen[-1]
./tests/test_preview_access.py:101:        self.assertEqual(cookie, 'other=1')
./tests/test_profit_protection.py:14: StripeSubscriptionWebhookProcessor(service).process(event('unpaid','checkout.session.completed',payment_status='unpaid',mode='subscription'))
./tests/test_profit_protection.py:19: processor.process(event('created','checkout.session.completed',payment_status='paid',mode='subscription'))
./tests/test_profit_protection.py:41: paid=event('paid','checkout.session.completed',payment_status='paid',mode='subscription')
./tests/test_profit_protection.py:50: out=StripeSubscriptionWebhookProcessor(service).process(event('paid','checkout.session.completed',created=100,payment_status='paid',mode='subscription'))
./tests/test_profit_protection.py:57:  events=[event('paid','checkout.session.completed',payment_status='paid',mode='subscription'),event('cancelled','customer.subscription.deleted')]
./tests/test_profit_protection.py:65: StripeSubscriptionWebhookProcessor(service).process(event('paid','checkout.session.completed',payment_status='paid',mode='subscription'))
./tests/test_profit_protection.py:83: StripeSubscriptionWebhookProcessor(service).process(event('paid1','checkout.session.completed',created=100,payment_status='paid',mode='subscription'))
./tests/test_profit_protection.py:84: StripeSubscriptionWebhookProcessor(service).process(event('paid2','checkout.session.completed',created=200,payment_status='paid',mode='subscription',subscription='sub_new'))
./tests/test_profit_protection.py:97: StripeSubscriptionWebhookProcessor(service).process(event('basic-paid','checkout.session.completed',created=100,payment_status='paid',mode='subscription'))
./tests/test_profit_protection.py:99: paid_upgrade=event('pro-paid','checkout.session.completed',created=200,payment_status='paid',mode='subscription',metadata={'user_id':'audit-user','plan_code':'pro'})
./tests/test_profit_protection.py:105: StripeSubscriptionWebhookProcessor(service).process(event('basic-paid','checkout.session.completed',created=100,payment_status='paid',mode='subscription'))
./tests/test_profit_protection.py:107: out=StripeSubscriptionWebhookProcessor(service).process(event('new-paid','checkout.session.completed',created=200,payment_status='paid',mode='subscription',subscription='sub_new',metadata={'user_id':'audit-user','plan_code':'pro'}))
./tests/test_provider_quota_and_dialects.py:198:        self.assertEqual(seen['headers']['authorization'], 'Bearer secret')
./tests/test_qstash_scheduler.py:73:        self.assertEqual(headers["authorization"], "Bearer " + TOKEN)
./tests/test_r2_generated_credentials.py:27:    raw = base64.b64decode(creds["session_token"]).decode()
./tests/test_r2_generated_credentials.py:37:                      role_arn="", policy=POLICY, session_name="app", ttl_seconds=900)
./tests/test_r2_generated_credentials.py:64:        self.assertNotEqual(self.issue()["session_token"], self.issue()["session_token"])
./tests/test_r2_generated_credentials.py:128:        self.assertEqual(set(binding.secret_references), {"access_key_id", "secret_access_key", "session_token"})
./tests/test_replicate_connection.py:59:        assert req.get_header('Authorization') == 'Bearer test-only-token'
./tests/test_replicate_connection.py:86:def test_check_route_requires_session_before_provider_call(monkeypatch):
./tests/test_replicate_connection.py:111:        headers={'Authorization': 'Bearer ' + signup.json()['token']})
./tests/test_replicate_connection.py:116:        headers={'Authorization': 'Bearer ' + signup.json()['token']}).json()['status'] == 'NOT_CONFIGURED'
./tests/test_v15_acceptance.py:63:        text='Authorization: Bearer supersecret api_key=abc123 password=hunter2 postgresql://u:pw@db/x'
./tests/test_v16_release_gate.py:52:            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456\n"
./tests/test_v20_observability_recovery.py:77:            message="Authorization: Bearer abcdefghijklmnopqrstuvwxyz123",
./tests/test_v24_auth.py:29:            c=TestClient(app); r=c.post('/api/demo/build',headers={'Authorization':'Bearer '+t},json={'prompt':'Build CRM','project_id':'auth-p'})
./tests/test_v25_unified_v10_parity.py:146:        auth=self.c.post(f'/runtime/v25/{dep}/data/rides',headers={'Authorization':f'Bearer {token}'},json={'payload':{'from':'A','to':'B'}})
./tests/test_v25_unified_v10_parity.py:148:        listed=self.c.get(f'/runtime/v25/{dep}/data/rides',headers={'Authorization':f'Bearer {token}'}).json()['items']
./tests/test_v25_unified_v10_parity.py:169:        self.c.post(f'/runtime/v25/{dep}/data/rides',headers={'Authorization':f'Bearer {token}'},json={'payload':{'ride':'kept'}})
./tests/test_v25_unified_v10_parity.py:172:        items=self.c.get(f'/runtime/v25/{dep}/data/rides',headers={'Authorization':f'Bearer {token}'}).json()['items']
./tests/test_v26_universal_pro.py:49:    def _auth(self,t): return {'Authorization':'Bearer '+t}
./tests/test_v26_universal_pro.py:94:        t=r.json()['token']; h={'Authorization':'Bearer '+t}
./tests/test_v27_rights_company_os.py:96:    def _auth(self,t): return {'Authorization':'Bearer '+t}
./tests/test_v28_148ai_launch.py:118:        self.assertEqual(reg.status_code,200,reg.text); tok=reg.json()['token']; h={'Authorization':'Bearer '+tok}
./tests/test_v28_148ai_launch.py:128:        email=self._email(); reg=self.c.post('/api/v28/auth/register',json={'email':email,'password':'StrongPass123!'}).json(); h={'Authorization':'Bearer '+reg['token']}
./tests/test_v28_148ai_launch.py:134:        email=self._email(); reg=self.c.post('/api/v28/auth/register',json={'email':email,'password':'StrongPass123!'}).json(); h={'Authorization':'Bearer '+reg['token']}
./tests/test_v28_148ai_launch.py:201:        payload=json.dumps({'id':'evt_148ai_1','created':now,'type':'checkout.session.completed','data':{'object':{'id':'cs_test_retention','subscription':'sub_test_retention','payment_status':'paid','mode':'subscription','metadata':{'user_id':'u-stripe','plan_code':'pro'}}}},separators=(',',':')).encode()
./tests/test_v28_148ai_launch.py:222:        reg=self._register(); h={'Authorization':'Bearer '+reg['token']}
./tests/test_v28_148ai_launch.py:231:        reg=self._register(); h={'Authorization':'Bearer '+reg['token']}
./tests/test_v28_148ai_launch.py:232:        event={'id':'evt_'+uuid.uuid4().hex,'type':'checkout.session.completed','data':{'object':{'client_reference_id':reg['user']['id'],'metadata':{'plan_code':'pro'}}}}
./tests/test_v28_148ai_launch.py:246:        event={'id':'evt_'+uuid.uuid4().hex,'created':int(time.time()),'type':'checkout.session.completed','data':{'object':{'id':'cs_test_paid','subscription':'sub_test_paid','payment_status':'paid','mode':'subscription','client_reference_id':uid,'metadata':{'user_id':uid,'plan_code':'pro'}}}}
./tests/test_v28_148ai_launch.py:252:        snap=c.get('/api/v28/me/subscription',headers={'Authorization':'Bearer '+token})
./tests/test_v7_content_only_provenance.py:24:        self.assertIn("auth_session", {x.kind for x in contract.infrastructure})
./tests/test_v7_readiness_regression.py:30:                "auth_session": {"status": "PARTIAL", "reason": "configured"},
./tests/test_v7_semantic_intake_architect.py:95:        self.assertIn("auth_session", kinds)
./tests/test_v7_visitor_no_login_boundary.py:11:    def test_explicit_no_login_plain_task_app_has_no_sessions_or_roles(self):
./tests/test_v7_visitor_no_login_boundary.py:15:        self.assertNotIn("auth_session", infrastructure)
./tests/test_v7_visitor_no_login_boundary.py:17:        # though no product visitor accounts or sessions are created.
./tests/test_v7_visitor_no_login_boundary.py:21:        self.assertIn("no generated-product visitor sign-in or sessions", auth)
./tests/test_v7_visitor_no_login_boundary.py:29:        self.assertIn("auth_session", infrastructure)
./tests/test_v7_visitor_no_login_boundary.py:37:        self.assertNotIn("auth_session", {x.kind for x in contract.infrastructure})
./tests/test_visual_edit.py:296:        def get(srv, path, dest=None, cookie='owner'):
./tests/test_visual_edit.py:298:            headers = {'Host': f'{label}.prv.test', 'X-148AI-Preview-Token': cookie}
./tests/test_visual_edit.py:322:            self.assertEqual(get(on, PI.INSPECTOR_PATH, cookie='stranger')[0], 404)
./tests/test_visual_edit.py:323:            self.assertEqual(get(on, '/', 'iframe', cookie='stranger')[0], 401)   # access control unchanged
./tools/deployment_verify.py:12:  session_identity, create_project, conversation_turn, conversation_persists, project_memory,
./tools/deployment_verify.py:26:  * redirects are never followed (same-origin included), so the bearer token
./tools/deployment_verify.py:28:  * no cookie jar, no environment proxies, TLS verification on, bounded
./tools/deployment_verify.py:64:            'session_identity': 'auth_bypass',
./tools/deployment_verify.py:186:            headers['Authorization'] = f'Bearer {self.token}'
./tools/deployment_verify.py:381:    # PR #9 (PDV-001) contract: the session must resolve to exactly the synthetic identity
./tools/deployment_verify.py:384:    check('session_identity', o.status == 200 and {'id', 'email', 'created_at', 'subscription'} <= set(me)
./tools/ui_visual_edit/walkthrough.py:36:    """fetch() from the page itself (same-origin session cookie)."""
```


## TRANSACTIONS

```
./omni_prod/active_jobs.py:42:            conn.rollback()
./omni_prod/agent_os/runtime.py:73:            with conn.transaction():
./omni_prod/agent_os/runtime.py:82:            with conn.transaction():
./omni_prod/agent_os/runtime.py:95:            with conn.transaction():
./omni_prod/agent_os/runtime.py:105:            with conn.transaction():
./omni_prod/agent_os/runtime.py:126:            with conn.transaction():
./omni_prod/agent_os/runtime.py:159:            with conn.transaction():
./omni_prod/agent_os/runtime.py:214:            with conn.transaction():
./omni_prod/agent_os/runtime.py:224:            with conn.transaction():
./omni_prod/agent_os/runtime.py:229:            with conn.transaction():
./omni_prod/agent_os/runtime.py:240:            with conn.transaction():
./omni_prod/agent_os/runtime.py:248:            with conn.transaction():
./omni_prod/attachments.py:213:                with conn.transaction():
./omni_prod/attachments.py:263:            with conn.transaction():
./omni_prod/attempt_ledger.py:275:        with conn.transaction():
./omni_prod/brief_repository.py:82:                with conn.transaction():
./omni_prod/brief_repository.py:114:            with conn.transaction():
./omni_prod/build_contract_repository.py:74:                with conn.transaction():
./omni_prod/build_control.py:135:            with conn.transaction():
./omni_prod/build_control.py:141:            with conn.transaction():
./omni_prod/build_control.py:148:            with conn.transaction():
./omni_prod/capability_repository.py:358:            with conn.transaction():
./omni_prod/capability_repository.py:408:            with conn.transaction():
./omni_prod/capability_repository.py:557:            with conn.transaction():
./omni_prod/capability_repository.py:602:            with conn.transaction():
./omni_prod/capability_repository.py:620:            with conn.transaction():
./omni_prod/capability_repository.py:669:            with conn.transaction():
./omni_prod/capability_repository.py:745:            with conn.transaction():
./omni_prod/capability_repository.py:818:            with conn.transaction():
./omni_prod/conversation/store.py:109:            with conn.transaction():
./omni_prod/conversation/store.py:152:            with conn.transaction():
./omni_prod/db.py:82:            with conn.transaction():
./omni_prod/db.py:88:        with conn.transaction():
./omni_prod/entitlements.py:100:            with conn.transaction():
./omni_prod/identity_lifecycle.py:252:                with conn.transaction():
./omni_prod/identity_lifecycle.py:282:            with conn.transaction():
./omni_prod/identity_lifecycle.py:295:            with conn.transaction():
./omni_prod/identity_lifecycle.py:302:            with conn.transaction():
./omni_prod/identity_lifecycle.py:308:            with conn.transaction():
./omni_prod/identity_lifecycle.py:323:            with conn.transaction():
./omni_prod/identity_lifecycle.py:329:            with conn.transaction():
./omni_prod/identity_lifecycle.py:336:            with conn.transaction():
./omni_prod/identity_lifecycle.py:348:            with conn.transaction():
./omni_prod/identity_lifecycle.py:357:            with conn.transaction():
./omni_prod/identity_lifecycle.py:371:            with conn.transaction():
./omni_prod/identity_lifecycle.py:381:            with conn.transaction():
./omni_prod/infrastructure_provisioner.py:133:            with conn.transaction():
./omni_prod/intake/budget.py:278:            with conn.transaction(), conn.cursor() as cur:
./omni_prod/intake/budget.py:283:            with conn.transaction(), conn.cursor() as cur:
./omni_prod/intake/budget.py:323:            with conn.transaction(), conn.cursor() as cur:
./omni_prod/intake/budget.py:342:            with conn.transaction(), conn.cursor() as cur:
./omni_prod/intake/budget.py:385:            with conn.transaction(), conn.cursor() as cur:
./omni_prod/intake/budget.py:418:            with conn.transaction(), conn.cursor() as cur:
./omni_prod/intake/budget.py:444:                    with conn.transaction(), conn.cursor() as cur:
./omni_prod/intake/budget.py:467:            with conn.transaction(), conn.cursor() as cur:
./omni_prod/intake/budget.py:492:            with conn.transaction(), conn.cursor() as cur:
./omni_prod/intake/budget.py:503:                with conn.transaction(), conn.cursor() as cur:
./omni_prod/intelligence/health.py:117:            with conn.transaction():
./omni_prod/investor_app.py:2315:                with conn.transaction():
./omni_prod/investor_app.py:2739:        with conn.transaction():
./omni_prod/investor_app.py:2863:    # detects a stale source atomically, inside workspace.commit()'s own
./omni_prod/job_repository.py:41:        # `.db.transaction()` already handles both. The M1-added methods below
./omni_prod/job_repository.py:128:    # `with pool.connection() as conn: with conn.transaction(): with
./omni_prod/job_repository.py:290:            with conn.transaction():
./omni_prod/job_repository.py:310:                with conn.transaction():
./omni_prod/job_repository.py:337:            with conn.transaction():
./omni_prod/job_repository.py:353:            with conn.transaction():
./omni_prod/job_repository.py:376:            with conn.transaction():
./omni_prod/job_repository.py:413:            with conn.transaction():
./omni_prod/maintenance.py:154:                with conn.transaction():
./omni_prod/migration_runner.py:52:        conn.commit()
./omni_prod/migration_runner.py:58:    with conn.transaction():
./omni_prod/modification_repository.py:43:    successful `workspace.commit()` (force=False/True respectively) -- this
./omni_prod/modification_repository.py:127:            with conn.transaction():
./omni_prod/modification_repository.py:142:                with conn.transaction():
./omni_prod/modification_repository.py:198:            with conn.transaction():
./omni_prod/modification_repository.py:231:            with conn.transaction():
./omni_prod/modification_repository.py:327:            with conn.transaction():
./omni_prod/modification_repository.py:355:        `workspace.commit()`'s own atomic compare (see workspace.py's
./omni_prod/modification_repository.py:359:        afterward. The original design called `workspace.commit()`
./omni_prod/modification_repository.py:370:        `force=True` passes `SKIP_VERSION_CHECK` to `workspace.commit()`
./omni_prod/modification_repository.py:382:                with conn.transaction():
./omni_prod/modification_repository.py:432:            # Postgres: conn.transaction()'s __exit__ rolls back on
./omni_prod/modification_repository.py:451:            with conn.transaction():
./omni_prod/modification_repository.py:491:            with conn.transaction():
./omni_prod/postdeploy_checks.py:155:        with conn.transaction():
./omni_prod/postdeploy_checks.py:172:        with conn.transaction():
./omni_prod/preview_access.py:58:            with conn.transaction():
./omni_prod/preview_access.py:69:            with conn.transaction():
./omni_prod/preview_access.py:82:            with conn.transaction():
./omni_prod/preview_access.py:120:                with conn.transaction():
./omni_prod/preview_access.py:149:                    with conn.transaction():
./omni_prod/preview_repository.py:37:            with conn.transaction():
./omni_prod/preview_repository.py:51:            with conn.transaction():
./omni_prod/preview_repository.py:101:            with conn.transaction():
./omni_prod/preview_repository.py:180:            with conn.transaction():
./omni_prod/preview_repository.py:225:            with conn.transaction():
./omni_prod/preview_repository.py:306:            with conn.transaction():
./omni_prod/project_lifecycle.py:163:                with conn.transaction():
./omni_prod/project_lifecycle.py:185:            with conn.transaction():
./omni_prod/providers/image_provider.py:214:            with conn.transaction():
./omni_prod/providers/image_provider.py:240:            with conn.transaction():
./omni_prod/providers/image_provider.py:252:            with conn.transaction():
./omni_prod/qa_budget.py:160:        with conn.transaction():
./omni_prod/release_policy.py:260:        with conn.transaction():
./omni_prod/spec_repository.py:45:            with conn.transaction():
./omni_prod/spec_repository.py:72:        with conn.transaction():
./omni_prod/subscription_store.py:32:            with conn.transaction():
./omni_prod/subscription_store.py:99:            with conn.transaction():
./omni_prod/subscription_store.py:106:            with conn.transaction():
./omni_prod/subscription_store.py:117:            with conn.transaction():
./omni_prod/subscription_store.py:131:            with conn.transaction():
./omni_prod/subscription_store.py:152:            with conn.transaction():
./omni_prod/subscription_store.py:314:            with conn.transaction():
./omni_prod/subscription_store.py:404:            with conn.transaction():
./omni_prod/worker_tasks.py:742:                with conn.transaction():
./omni_prod/workspace.py:218:                with conn.transaction():
./tests/financial_fault_harness.py:162:        with pool.connection() as conn, conn.transaction(), conn.cursor() as cur:
./tests/financial_fault_harness.py:209:            with pool.connection() as conn, conn.transaction():
./tests/integration/test_m5_build_economics_postgres.py:51:        with conn.transaction():
./tests/integration/test_m5_build_economics_postgres.py:65:        with conn.transaction():
./tests/integration/test_m5_build_economics_postgres.py:89:                    with conn.transaction():
./tests/integration/test_m5_build_economics_postgres.py:131:                    with conn.transaction():
./tests/integration/test_m5_build_economics_postgres.py:197:            with conn.transaction():
./tests/m4d2_rq_job_target.py:30:        with conn.transaction():
./tests/test_actual_cost_settlement.py:162:            with conn.transaction():
./tests/test_build_cancel_and_log.py:150:            with conn.transaction():
./tests/test_build_state_machine.py:46:            with conn.transaction():
./tests/test_conversation_os.py:422:            with conn.transaction():
./tests/test_conversation_os.py:429:            conn.commit()
./tests/test_conversation_os.py:529:                with conn.transaction():
./tests/test_crash_recovery_and_change_parity.py:37:            with c.transaction():
./tests/test_crash_recovery_and_change_parity.py:60:            with c.transaction():
./tests/test_crash_recovery_and_change_parity.py:91:                with c.transaction():
./tests/test_crash_recovery_and_change_parity.py:100:            with c.transaction():
./tests/test_crash_recovery_and_change_parity.py:123:            with c.transaction():
./tests/test_discovery_and_approval.py:117:            conn.commit()
./tests/test_discovery_and_approval.py:135:            with conn.transaction():
./tests/test_evidence_export.py:79:                conn.rollback()
./tests/test_evidence_export.py:110:                conn.rollback()
./tests/test_evidence_export.py:118:                conn.rollback()
./tests/test_evidence_export.py:121:                conn.rollback()
./tests/test_evidence_export.py:127:                conn.rollback()
./tests/test_evidence_export.py:139:                conn.rollback()
./tests/test_evidence_export.py:200:                conn.rollback()
./tests/test_evidence_export.py:210:                conn.rollback()
./tests/test_golden_mod_path_live_postgres.py:62:            with conn.transaction():
./tests/test_golden_mod_path_live_postgres.py:111:            with conn.transaction():
./tests/test_golden_mod_path_live_postgres.py:162:            with conn.transaction():
./tests/test_golden_mod_path_live_postgres.py:188:                with conn.transaction():
./tests/test_golden_mod_path_live_postgres.py:200:            conn.commit()
./tests/test_golden_mod_path_live_postgres.py:223:            conn.commit()
./tests/test_golden_mod_path_live_postgres.py:236:                with conn.transaction():
./tests/test_golden_mod_path_live_postgres.py:264:            conn.commit()
./tests/test_golden_mod_path_live_postgres.py:278:            conn.commit()
./tests/test_intake_budget_pg.py:69:            with conn.transaction():
./tests/test_intake_budget_pg.py:292:                    with conn.transaction():
./tests/test_intelligence_plane.py:318:            with conn.transaction():
./tests/test_janitor_redispatch.py:62:            with c.transaction():
./tests/test_janitor_redispatch.py:67:            with c.transaction():  # earlier test runs leave queued rows behind; age them out of the window
./tests/test_janitor_redispatch.py:75:            with c.transaction():
./tests/test_m4d1_atomic_accept.py:5:`accept()` design production-blocking. It called `workspace.commit()`
./tests/test_m4d1_atomic_accept.py:189:        both dispatched into workspace.commit() at the SAME instant (forced
./tests/test_m4d1_atomic_accept.py:284:        SELECT) raises -- workspace.commit() is never even reached."""
./tests/test_m4d1_atomic_accept.py:297:        """spec_repo.save() raises after workspace.commit() already
./tests/test_m4d1_atomic_accept.py:299:        connection, conn.transaction() rolls the WHOLE transaction back on
./tests/test_m4d1_atomic_accept.py:519:        """Temporarily replaces MemoryProjectWorkspace.commit() with a
./tests/test_m4d1_atomic_accept.py:610:                    with conn.transaction():
./tests/test_m4d2_live_fastapi_redis.py:122:        methods (`workspace.commit()`, `PostgresSpecRepository.save()`)
./tests/test_m4d2_live_fastapi_redis.py:427:            with conn.transaction():
./tests/test_m4d2_live_postgres.py:15:ROLLBACK (via `conn.transaction()`'s real `__exit__`) to undo it -- the
./tests/test_m4d2_live_postgres.py:145:        with conn.transaction():
./tests/test_m4d2_live_postgres.py:161:    """The exact same formula PostgresProjectWorkspace.commit() uses, so
./tests/test_m4d2_live_postgres.py:322:        """C.6: hold the exact advisory lock id PostgresProjectWorkspace.commit()
./tests/test_m4d2_live_postgres.py:369:        holder.rollback()  # releases the advisory lock (xact-scoped)
./tests/test_m4d2_live_postgres.py:393:    `conn.transaction()`'s real `__exit__`, which issues a real ROLLBACK --
./tests/test_m4d2_live_postgres.py:429:        return self._conn.transaction()
./tests/test_m4d2_live_postgres.py:447:    `workspace.commit()` and `spec_repo.save()` -- goes through this same
./tests/test_m4d2_live_postgres.py:767:        workspace.commit()/spec_repo.save()/the final ModificationRequest
./tests/test_m4d2_live_postgres.py:807:                return self._conn.transaction()
./tests/test_m4d2_live_postgres.py:848:                          f'workspace.commit(), spec_repo.save() and the final status UPDATE must all run '
./tests/test_m4_acceptance.py:124:        # cursor they gave workspace.commit(), merging everything into one
./tests/test_m4_acceptance.py:422:        (asserts exactly one `conn.transaction()`) for the executed proof.
./tests/test_maintenance_live_postgres.py:52:            with conn.transaction():
./tests/test_maintenance_live_postgres.py:63:            conn.commit()
./tests/test_maintenance_live_postgres.py:81:            conn.commit()
./tests/test_migration_rollback_tolerance.py:80:        self.conn.commit()
./tests/test_migration_rollback_tolerance.py:94:        self.conn.rollback()
./tests/test_migration_rollback_tolerance.py:103:        self.conn.commit()
./tests/test_migration_rollback_tolerance.py:133:        self.conn.commit()
./tests/test_modification_repository.py:116:        # workspace.commit(), to merge everything into one transaction) but
./tests/test_modification_repository.py:135:    MemoryProjectWorkspace.commit() now does its expected-version compare
./tests/test_modification_repository.py:447:        # `conn.transaction()`, not the pre-M4D.1 two (pre-check + a later,
./tests/test_modification_repository.py:517:        workspace.commit() itself, before any row for THIS modification is
./tests/test_preview_access.py:51:            with c.transaction():
./tests/test_preview_access.py:123:            with c.transaction():
./tests/test_real_docker_drain_recovery.py:240:        self.conn.commit()
./tests/test_real_docker_drain_recovery.py:326:        self.conn.commit()
./tests/test_release_policy.py:198:            with conn.transaction():
./tests/test_visual_edit.py:112:            with conn.transaction():
./tests/test_visual_edit.py:165:                with conn.transaction():
./tests/test_worker_deploy_recovery.py:369:                conn.rollback()
./tests/test_worker_deploy_recovery.py:400:                conn.rollback()
./tests/test_worker_deploy_recovery.py:426:                conn.rollback()
./tests/test_workspace_version_conflict.py:24:  - `cur`, when given, lets PostgresProjectWorkspace.commit() participate in
./tools/ui_visual_edit/walkthrough.py:93:        with conn.transaction():
```


## IN-MEMORY STATE — מודול-גלובלי

```
```


## BROAD EXCEPTS

```
./omni_prod/active_jobs.py:39:    except Exception as exc:                                    # a failed query is missing information, never "quiet"
./omni_prod/active_jobs.py:43:        except Exception:
./omni_prod/active_jobs.py:107:    except Exception as exc:
./omni_prod/active_jobs.py:145:    except Exception as exc:
./omni_prod/active_jobs.py:183:        except Exception as exc:                        # anything unexpected is also "cannot verify"
./omni_prod/agent_os/recorder.py:44:        except Exception as exc:  # recording must never fail the build
./omni_prod/agent_os/recorder.py:312:        except Exception:
./omni_prod/agent_os/recorder.py:487:        except Exception:
./omni_prod/attachments.py:219:        except Exception:
./omni_prod/attachments.py:222:            except Exception:
./omni_prod/attempt_ledger.py:187:        except Exception as exc:
./omni_prod/auth.py:48:    except Exception as exc: raise AuthError('invalid token') from exc
./omni_prod/autonomous_core.py:83:        except Exception:  # a snapshot must never change the build
./omni_prod/backup.py:157:        except Exception as exc:
./omni_prod/backup.py:216:    except Exception as exc:
./omni_prod/behavior_acceptance.py:62:    except Exception:
./omni_prod/behavior_acceptance.py:74:except Exception:
./omni_prod/behavior_acceptance.py:160:        except Exception as exc:
./omni_prod/benchmark_suite.py:79:            except Exception as exc:
./omni_prod/browser_probe.py:50:    except Exception:
./omni_prod/browser_probe.py:184:        except Exception as exc:
./omni_prod/build_contract_repository.py:111:        except Exception as exc:
./omni_prod/build_control.py:50:        except Exception:
./omni_prod/build_control.py:60:        except Exception:  # pragma: no cover - logging must never fail a build
./omni_prod/build_control.py:69:        except Exception:
./omni_prod/build_outbox_relay.py:56:            except Exception as exc:  # keep looping; report honestly
./omni_prod/conversation/memory.py:32:    except Exception as exc:  # a missing table on an older database: say so, never fail the page
./omni_prod/conversation/supervisor.py:467:        except Exception:
./omni_prod/conversation/supervisor.py:475:        except Exception:
./omni_prod/db.py:68:            except Exception as exc:
./omni_prod/db.py:100:    except Exception:
./omni_prod/demo_project.py:122:        except Exception as exc:
./omni_prod/demo_project.py:130:        except Exception as exc:
./omni_prod/evidence_export.py:102:        except Exception:
./omni_prod/evidence_export.py:142:    except Exception:  # pragma: no cover - stdin use on an older image
./omni_prod/evidence_export.py:243:            except Exception as exc:
./omni_prod/gate_replay.py:67:        except Exception as exc:
./omni_prod/gate_replay.py:139:        except Exception as exc:
./omni_prod/gate_replay.py:200:    except Exception as exc:
./omni_prod/identity_lifecycle.py:258:        except Exception as exc:
./omni_prod/intake/interpreter.py:326:        except Exception as exc:  # provider down / budget: the conversation continues deterministically
./omni_prod/intake/mode.py:111:    except Exception as exc:  # spend unknown -> never risk an uncapped call
./omni_prod/intake/reservation_worker.py:106:    except Exception as exc:
./omni_prod/intake/reservation_worker.py:116:    except Exception as exc:
./omni_prod/intake/reservation_worker.py:176:            except Exception as exc:
./omni_prod/intake/worker_route.py:75:        except Exception as exc:   # BudgetError, ValueError, schema/DB errors: fail closed, no paid call
./omni_prod/intake/worker_route.py:82:            except Exception as exc:    # queue down: nothing was sent, so give the money back now
./omni_prod/intelligence/health.py:144:        except Exception:
./omni_prod/intelligence/health.py:190:        except Exception:
./omni_prod/intelligence/health.py:200:        except Exception:
./omni_prod/investor_app.py:774:    except Exception as exc: raise HTTPException(status_code=503,detail=str(exc)[:1000]) from exc
./omni_prod/investor_app.py:781:        except Exception as exc:
./omni_prod/investor_app.py:900:    except Exception as exc: raise HTTPException(503,str(exc)[:1000]) from exc
./omni_prod/investor_app.py:952:    except Exception:
./omni_prod/investor_app.py:1048:    except Exception:
./omni_prod/investor_app.py:1229:    except Exception as exc: raise HTTPException(503,str(exc)[:1000]) from exc
./omni_prod/investor_app.py:1275:    except Exception:
./omni_prod/investor_app.py:1404:    except Exception as exc:
./omni_prod/investor_app.py:1412:    except Exception as exc:
./omni_prod/investor_app.py:1614:        except Exception:
./omni_prod/investor_app.py:1727:    except Exception as exc:
./omni_prod/investor_app.py:1911:        except Exception:
./omni_prod/investor_app.py:2409:        except Exception:
./omni_prod/investor_app.py:2582:    except Exception as exc:
./omni_prod/investor_app.py:2668:        except Exception as exc:
./omni_prod/investor_app.py:2763:    except Exception:
./omni_prod/investor_app.py:3103:    except Exception:
./omni_prod/investor_app.py:3112:    except Exception:
./omni_prod/investor_app.py:3122:    except Exception:
./omni_prod/investor_app.py:3182:    except Exception:
./omni_prod/investor_app.py:3197:    except Exception as exc:
./omni_prod/investor_app.py:3272:    except Exception as exc:
./omni_prod/investor_app.py:3335:    except Exception:
./omni_prod/maintenance.py:208:    except Exception as exc:
./omni_prod/maintenance.py:214:            except Exception as exc:
./omni_prod/maintenance.py:216:    except Exception as exc:
./omni_prod/maintenance.py:222:            except Exception as exc:
./omni_prod/maintenance.py:224:    except Exception as exc:
./omni_prod/maintenance.py:229:        except Exception as exc:
./omni_prod/maintenance.py:235:        except Exception as exc:
./omni_prod/maintenance.py:281:            except Exception:
./omni_prod/media_gateway.py:41:        except Exception as exc: raise MediaGatewayError(f'{self.endpoint.name} media generation failed: {exc}') from exc
./omni_prod/media_gateway.py:44:        except Exception as exc: raise MediaGatewayError('invalid media provider response') from exc
./omni_prod/migration_runner.py:76:                except Exception as exc:
./omni_prod/model_gateway.py:38:    except Exception:
./omni_prod/model_probe.py:42:        except Exception as exc:
./omni_prod/postdeploy_checks.py:135:        except Exception:
./omni_prod/postdeploy_checks.py:324:    except Exception as exc:  # the check outcome is already printed; storage is best effort
./omni_prod/postdeploy_checks.py:367:        except Exception as exc:
./omni_prod/postdeploy_checks.py:640:    except Exception as exc:
./omni_prod/preview_access.py:152:            except Exception:
./omni_prod/preview_durability.py:64:        except Exception:
./omni_prod/preview_durability.py:106:    except Exception as exc:
./omni_prod/preview_durability.py:112:            except Exception:
./omni_prod/preview_inspector.py:195:            except Exception:
./omni_prod/preview_router.py:93:        except Exception:
./omni_prod/preview_router.py:147:                except Exception:
./omni_prod/preview_runtime.py:342:        except Exception as exc:  # connection refused/reset/timeouts while booting
./omni_prod/preview_runtime.py:471:        except Exception:
./omni_prod/preview_runtime.py:491:        except Exception:
./omni_prod/preview_smoke.py:51:    except Exception:
./omni_prod/preview_smoke.py:70:            except Exception:
./omni_prod/preview_smoke.py:81:    except Exception as e:
./omni_prod/preview_smoke.py:87:except Exception:
./omni_prod/preview_smoke.py:125:        except Exception as exc:  # sandbox unavailable: the build cannot be verified
./omni_prod/product_review.py:71:        except Exception as exc:  # outage: say so, never invent a review
./omni_prod/project_lifecycle.py:169:        except Exception as exc:
./omni_prod/providers/image_provider.py:81:    except Exception:
./omni_prod/providers/managed_web_saas.py:244:    except Exception:
./omni_prod/providers/managed_web_saas.py:270:    except Exception as exc:  # status codes from HTTPError, otherwise unreachable
./omni_prod/providers/managed_web_saas.py:386:        except Exception as exc:
./omni_prod/providers/managed_web_saas.py:394:        except Exception as exc:
./omni_prod/providers/managed_web_saas.py:450:        except Exception:
./omni_prod/providers/managed_web_saas.py:459:        except Exception:
./omni_prod/providers/managed_web_saas.py:495:        except Exception as exc:
./omni_prod/providers/managed_web_saas.py:684:        except Exception as exc:
./omni_prod/providers/managed_web_saas.py:699:                except Exception as exc:
./omni_prod/providers/qstash_scheduler.py:82:        except Exception:
./omni_prod/providers/qstash_scheduler.py:190:        except Exception:
./omni_prod/providers/qstash_scheduler.py:195:        except Exception:
./omni_prod/providers/replicate_connection.py:71:    except Exception:
./omni_prod/providers/replicate_connection.py:96:    except Exception:
./omni_prod/providers/replicate_image_test.py:74:        except Exception as exc:
./omni_prod/providers/replicate_image_test.py:110:            except Exception as exc:
./omni_prod/quality_gate.py:55:    except Exception as exc:
./omni_prod/queueing.py:78:    except Exception:
./omni_prod/registry_audit.py:74:    except Exception:
./omni_prod/registry_audit.py:247:    except Exception:
./omni_prod/registry_audit.py:257:    except Exception as exc:
./omni_prod/rehearsal.py:36:    except Exception as exc:
./omni_prod/rehearsal.py:40:    except Exception as exc:
./omni_prod/release_gate.py:25:    except Exception as exc:
./omni_prod/routed_gateway.py:191:            except Exception as exc:
./omni_prod/routed_gateway.py:204:        except Exception as exc:
./omni_prod/routed_gateway.py:421:                except Exception as exc:
./omni_prod/routed_gateway.py:440:                                except Exception as fitted_exc:
./omni_prod/sandbox.py:142:    except Exception:
./omni_prod/sandbox_service.py:64:    except Exception as exc: raise HTTPException(400,'invalid request') from exc
./omni_prod/secrets_manager.py:40:        except Exception as exc: raise SecretResolutionError('vault resolution failed') from exc
./omni_prod/secrets_manager.py:101:        except Exception as exc:
./omni_prod/secrets_manager.py:207:        except Exception:
./omni_prod/security_testing.py:39:    except Exception as exc:
./omni_prod/storage.py:65:        except Exception:
./omni_prod/storage.py:180:        except Exception:
./omni_prod/stripe_billing.py:78:        except Exception as exc:
./omni_prod/stripe_billing.py:99:    except Exception as exc:
./omni_prod/stripe_billing.py:110:    except Exception as exc:
./omni_prod/stripe_billing.py:159:                except Exception as exc:
./omni_prod/visual_qa.py:57:    except Exception:
./omni_prod/visual_qa.py:213:            except Exception as exc:
./omni_prod/visual_qa.py:229:                except Exception as exc:  # evidence storage must not change the outcome
./omni_prod/web_saas_acceptance.py:254:                except Exception as exc:
./omni_prod/web_saas_acceptance.py:262:                    except Exception:
./omni_prod/worker_tasks.py:213:    except Exception:
./omni_prod/worker_tasks.py:236:    except Exception:
./omni_prod/worker_tasks.py:266:    except Exception:  # evidence must never fail a build
./omni_prod/worker_tasks.py:302:    except Exception:
./omni_prod/worker_tasks.py:433:    except Exception:
./omni_prod/worker_tasks.py:582:        except Exception:
./omni_prod/worker_tasks.py:861:    except Exception as exc:
./omni_prod/worker_tasks.py:956:            except Exception:
./omni_prod/worker_tasks.py:965:    except Exception:
./omni_prod/worker_tasks.py:985:        except Exception:
./omni_prod/worker_tasks.py:991:    except Exception as exc:
./omni_prod/worker_tasks.py:1168:    except Exception as exc:
./omni_prod/worker_tasks.py:1261:    except Exception as exc:
./omni_prod/worker_tasks.py:1265:    except Exception as exc:
./omni_prod/worker_tasks.py:1270:        except Exception as exc:
./omni_prod/worker_tasks.py:1301:    except Exception as exc:
./omni_prod/worker_tasks.py:1327:            except Exception as exc:
./omni_prod/worker_tasks.py:1378:                except Exception as exc:
./omni_prod/worker_tasks.py:1388:                    except Exception as exc:
./omni_prod/worker_tasks.py:1393:                    except Exception:
./omni_prod/worker_tasks.py:1398:                        except Exception as exc:
./omni_prod/worker_tasks.py:1422:                        except Exception:
./omni_prod/worker_tasks.py:1426:    except Exception as exc:
./omni_prod/worker_tasks.py:1476:    except Exception:
./omni_prod/workspace.py:191:        except Exception:
./scripts/run_http_load.py:11:    except Exception as exc: return 0,int((time.perf_counter()-t)*1000),str(exc)[:200]
./scripts/run_v25_offline_benchmark.py:25:    except Exception as exc:
./scripts/run_v28_http_acceptance.py:26:        except Exception: payload=raw.decode('utf-8','ignore')
./scripts/run_v28_http_acceptance.py:44:        except Exception: pass
./scripts/run_v28_offline_benchmark.py:25:    except Exception as exc:
./tests/integration/test_m5_build_economics_postgres.py:31:    except Exception as exc:
./tests/integration/test_m5_build_economics_postgres.py:98:            except Exception as exc:
./tests/integration/test_m5_build_economics_postgres.py:164:            except Exception as exc:
./tests/m4d2b_local_model_server.py:129:        except Exception as exc:  # pragma: no cover - defensive, surfaces as a real HTTP 500
./tests/test_agent_os.py:153:    except Exception as exc:
./tests/test_behavior_acceptance_in_build.py:21:    except Exception:
./tests/test_build_cancel_and_log.py:130:    except Exception as exc:
./tests/test_conversation_os.py:408:    except Exception as exc:
./tests/test_crash_recovery_and_change_parity.py:21:    except Exception as exc:
./tests/test_discovery_and_approval.py:92:    except Exception as exc:
./tests/test_golden_mod_path_live_postgres.py:30:    except Exception as exc:
./tests/test_golden_mod_path_live_postgres.py:230:            except Exception as exc:  # surfaced in the assertion message
./tests/test_intake_budget_pg.py:48:        except Exception as exc:
./tests/test_intake_budget_pg.py:102:            except Exception as exc:            # collected and asserted by the caller
./tests/test_intake_budget_pg.py:296:            except Exception as exc:
./tests/test_janitor_redispatch.py:50:    except Exception as exc:
./tests/test_legacy_paths_guard.py:9:except Exception:  # pragma: no cover - fastapi absent in some local environments
./tests/test_m49_clean_room.py:74:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m49_clean_room.py:78:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m49_lifecycle.py:50:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m49_sandbox_security.py:78:except Exception as e:
./tests/test_m49_sandbox_security.py:87:except Exception as e:
./tests/test_m49_sandbox_security.py:94:except Exception as e:
./tests/test_m49_sandbox_security.py:102:except Exception as e:
./tests/test_m49_sandbox_security.py:108:except Exception as e:
./tests/test_m4d1_atomic_accept.py:588:            except Exception:
./tests/test_m4d2b_parity_and_worker.py:67:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m4d2b_parity_and_worker.py:71:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m4d2_live_fastapi_redis.py:58:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m4d2_live_fastapi_redis.py:62:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_m4d2_live_postgres.py:70:    except Exception as exc:  # pragma: no cover - environment probe
./tests/test_maintenance_live_postgres.py:20:    except Exception as exc:
./tests/test_plan_driven_execution.py:248:            except Exception:
./tests/test_preview_access.py:21:    except Exception as exc:
./tests/test_quality_repairable.py:70:        except Exception as exc:  # patch object shape differs
./tests/test_real_docker_drain_recovery.py:66:    except Exception:
./tests/test_visual_edit.py:100:    except Exception as exc:
./tools/ui_visual_edit/preview_host.py:52:                except Exception:
./tools/ui_visual_edit/walkthrough.py:50:        except Exception:
```


## MARKERS

```
./omni_prod/agent_os/agents.py:137:    ('performance_agent', 'Performance Agent', 'quality', 'speed and load', 'measures latency/load of generated products', ('latency_analysis', 'load_test', 'frontend_performance_test'), 'quality_gate_agent', (), (), {'gap': 'not implemented'}),
./omni_prod/agent_os/agents.py:142:    ('seo_web_quality_agent', 'SEO / Web Quality Agent', 'quality', 'metadata and web quality', 'titles, descriptions, sitemaps', ('metadata_generation', 'sitemap_generation', 'seo_validation'), 'qa_agent', (), (), {'gap': 'not implemented'}),
./omni_prod/agent_os/agents.py:143:    ('analytics_agent', 'Analytics Agent', 'platform', 'product analytics', 'event schema with consent', ('event_schema_generation', 'event_tracking', 'usage_metric'), 'privacy_reviewer', (), (), {'gap': 'not implemented'}),
./omni_prod/agent_os/agents.py:148:    ('automation_agent', 'Automation Agent', 'automation', 'workflows and triggers', 'generates scheduled/webhook workflows', ('trigger_definition', 'schedule_definition', 'workflow_test'), 'qa_agent', (), (), {'gap': 'not implemented'}),
./omni_prod/agent_os/agents.py:162:    ('game_designer_2d_agent', '2D Game Designer Agent', 'games', 'game concept and rules', 'genre, loop, win/lose', ('game_concept', 'game_loop_design', 'genre_rules'), 'game_qa_2d_agent', (), (), {'gap': 'not implemented'}),
./omni_prod/agent_os/agents.py:163:    ('level_designer_2d_agent', '2D Level Designer Agent', 'games', 'levels', 'level layout and progression', ('level_system', 'progression_system', 'difficulty_system'), 'game_qa_2d_agent', (), (), {'gap': 'not implemented'}),
./omni_prod/agent_os/agents.py:166:    ('game_qa_2d_agent', '2D Game QA Agent', 'games', 'play the game in a browser', 'controls, collision, scoring, restart', ('gameplay_test', 'level_completion_test', 'save_load_test'), 'quality_gate_agent', (), (), {'gap': 'not implemented'}),
./omni_prod/agent_os/agents.py:170:    ('support_agent', 'Support Agent', 'platform', 'answer customers', 'explains failures and next steps', ('incident_creation',), 'customer_success', (), (), {'gap': 'not implemented'}),
./omni_prod/agent_os/contracts.py:8:that ran). A record with only a name and a description is NOT implemented.
./omni_prod/agent_os/departments.py:97:               ('D12',), 'games (not yet)', 'gameplay tests (not implemented)', 'not priced'),
./omni_prod/agent_os/departments.py:106:               'workflow tests (not implemented)', 'not priced'),
./omni_prod/agent_os/meta.py:135:    ('invalid OAuth', '', 'not applicable: generated-app OAuth not implemented'),
./omni_prod/agent_os/meta.py:150:    ('Golden 2 — SaaS with authentication', (), 'NOT_RUN', 'generated-app sign-in is not implemented (Identity & Auth agent NOT_IMPLEMENTED)'),
./omni_prod/agent_os/skills.py:120:    'signup': ((), (), 'generated-app sign-up not implemented; platform accounts are tracked separately'),
./omni_prod/agent_os/skills.py:121:    'login': ((), (), 'generated-app login not implemented; platform accounts are tracked separately'),
./omni_prod/agent_os/skills.py:122:    'logout': ((), (), 'generated-app logout not implemented; platform accounts are tracked separately'),
./omni_prod/agent_os/skills.py:123:    'session_management': ((), (), 'generated-app session management not implemented; platform accounts are tracked separately'),
./omni_prod/agent_os/skills.py:124:    'email_verification': ((), (), 'generated-app email verification not implemented; platform accounts are tracked separately'),
./omni_prod/agent_os/skills.py:125:    'password_reset': ((), (), 'generated-app password reset not implemented; platform accounts are tracked separately'),
./omni_prod/agent_os/skills.py:126:    'account_deletion': ((), (), 'generated-app account deletion not implemented; platform accounts are tracked separately'),
./omni_prod/agent_os/skills.py:127:    'account_export': ((), (), 'generated-app account export not implemented; platform accounts are tracked separately'),
./omni_prod/agent_os/skills.py:130:    'integration_health_check': ((), (), 'generated-app integrations not implemented; model-provider probe is platform routing'),
./omni_prod/agent_os/skills.py:131:    'rate_limit_handling': ((), (), 'generated-app integrations not implemented; model 429 handling is platform routing'),
./omni_prod/agent_os/skills.py:132:    'provider_fallback': ((), (), 'generated-app integrations not implemented; model fallback is platform routing'),
./omni_prod/agent_os/skills.py:133:    'external_error_normalization': ((), (), 'generated-app integrations not implemented'),
./omni_prod/agent_os/skills.py:283:    impl, evidence, gap = IMPL.get(key, ((), (), 'not implemented'))
./omni_prod/autonomous_agents.py:78:    'app; a health string or placeholder at / is rejected. Automated tests must exercise the HTTP endpoints and '
./omni_prod/browser_probe.py:72:    const key = ((el.name || '') + ' ' + (el.id || '') + ' ' + (el.placeholder || '')).toLowerCase();
./omni_prod/discovery.py:364:    todo = pending(brief)
./omni_prod/discovery.py:365:    urgent = [q for q in todo if q.id == 'access_scope']
./omni_prod/discovery.py:369:        qs = [q for q in todo if q.group == g]
./omni_prod/investor_app.py:2358:                        # is never the literal placeholder 'UNKNOWN'.
./omni_prod/modifier_engine.py:38:    Scope of this stub, deliberately:
./omni_prod/planning/architect.py:98:           outputs=('running preview of the candidate',), accept=('"/" serves the product (not a stub)',),
./omni_prod/preflight.py:24:        "change_me", "changeme", "example", "placeholder", "your_"
./omni_prod/preflight.py:41:            "OMNI_SECRET_KEY must be >=48 chars and not a placeholder."
./omni_prod/preflight.py:71:                f"{key} must be configured with a non-placeholder value."
./omni_prod/preview_inspector.py:58:    var attrs = {}, keys = ['name','type','href','src','placeholder','aria-label','data-testid','role','title','alt','for'];
./omni_prod/preview_inspector.py:60:    if (attrs.type === 'password') delete attrs.placeholder;
./omni_prod/preview_smoke.py:29:    'buttons, tables) wired to the app\'s JSON endpoints -- never a placeholder or a health string.'
./omni_prod/preview_smoke.py:79:            verdict = ("GET / returned a placeholder page, not the product's user interface "
./omni_prod/registry_audit.py:208:        row = Row(role, DEFINED, '—', '—', 'not verified', '—', '—', 'not implemented')
./omni_prod/secret_scan.py:15:    "your_key", "your_secret", "test", "dummy", "placeholder"
./omni_prod/skill_catalog.py:57:_NI = 'not implemented'
./omni_prod/truth_lock.py:140:        "- `NOT_IMPLEMENTED`: canonical product scope exists but execution is not implemented.",
./omni_prod/visual_edit.py:12:id, name/aria-label/placeholder, visible text, class list).
./omni_prod/visual_edit.py:19:ATTR_KEYS = ('name', 'type', 'href', 'src', 'placeholder', 'aria-label', 'data-testid', 'role', 'title', 'alt', 'for')
./omni_prod/visual_edit.py:104:    for key in ('data-testid', 'name', 'aria-label', 'placeholder', 'for', 'title', 'alt'):
./omni_prod/visual_edit.py:199:    for k in ('name', 'aria-label', 'placeholder', 'type'):
./omni_prod/visual_qa.py:84:      if (!labelled) add('unlabelled_field', el, el.getAttribute('placeholder') ? 'placeholder only' : '');
./tests/m5_worker_harness.py:41:    def __init__(self, contract=None, *, verified=True, gateway=None, engine_exc=None, prompt='Build a todo app'):
./tests/test_deployment_verification.py:4:deployment smoke red -> release stays blocked) run against a local HTTP stub
./tests/test_deployment_verification.py:298:        stub = _Stub()
./tests/test_deployment_verification.py:300:            r = dv.verify(stub.url, expect_sha=SHA)
./tests/test_deployment_verification.py:302:            stub.close()
./tests/test_deployment_verification.py:318:        stub = self
./tests/test_deployment_verification.py:335:                if stub.f['reject_tokens']:
./tests/test_deployment_verification.py:337:                return stub.tokens.get((self.headers.get('Authorization') or '').removeprefix('Bearer '))
./tests/test_deployment_verification.py:341:                stub.seen.append({'path': path, 'auth': self.headers.get('Authorization'),
./tests/test_deployment_verification.py:345:                if stub.f['drop_on'] == tag:
./tests/test_deployment_verification.py:348:                if stub.f['sleep_on'] == tag:
./tests/test_deployment_verification.py:350:                if stub.f['redirect_to'] and path == stub.f.get('redirect_path', '/api/v28/deployment'):
./tests/test_deployment_verification.py:351:                    return self._send(302, b'', extra=[('Location', stub.f['redirect_to'] + path)])
./tests/test_deployment_verification.py:352:                if stub.f['protected'] and self.headers.get('x-vercel-protection-bypass') != stub.f['bypass_ok']:
./tests/test_deployment_verification.py:354:                if stub.f['huge_on'] == tag:
./tests/test_deployment_verification.py:356:                if stub.f['html_on'] == tag:
./tests/test_deployment_verification.py:361:                cookie = [('Set-Cookie', 'track=1; Path=/')] if stub.f['set_cookie'] else []
./tests/test_deployment_verification.py:363:                    return self._send(200, {'source_commit': stub.f['sha'], 'environment': stub.f['env'], 'branch': 'b',
./tests/test_deployment_verification.py:364:                                            'schema': {'required': 36, 'compatible': stub.f['compatible'],
./tests/test_deployment_verification.py:365:                                                       'status': 'COMPATIBLE' if stub.f['compatible'] else 'MIGRATIONS_PENDING',
./tests/test_deployment_verification.py:366:                                                       'missing': [] if stub.f['compatible'] else [36],
./tests/test_deployment_verification.py:370:                    stub.tokens[tok] = body['email']
./tests/test_deployment_verification.py:371:                    return self._send(200, {} if stub.f['no_token'] else {'token': tok}, extra=cookie)
./tests/test_deployment_verification.py:376:                    if stub.f['me_wrong_user']:
./tests/test_deployment_verification.py:382:                    pid = stub.f['project_id'] or f'p{len(stub.owner)}'
./tests/test_deployment_verification.py:383:                    stub.owner[pid] = user
./tests/test_deployment_verification.py:386:                if not user and not stub.f['anon_ok']:
./tests/test_deployment_verification.py:388:                if user and stub.owner.get(pid) != user and not stub.f['leak']:
./tests/test_deployment_verification.py:391:                    if stub.f['conversation_status'] == 503:
./tests/test_deployment_verification.py:395:                    if stub.f['conversation_status'] != 200:
./tests/test_deployment_verification.py:396:                        echoed = self.headers.get('Authorization') if stub.f['echo_auth'] else 'Internal Server Error'
./tests/test_deployment_verification.py:397:                        return self._send(stub.f['conversation_status'], {'detail': echoed})
./tests/test_deployment_verification.py:399:                        stub.messages.setdefault(pid, []).extend(['u', 'a'])
./tests/test_deployment_verification.py:401:                    body = {'messages': stub.messages.get(pid, []), 'discovery': None, 'plan': None, 'plan_id': None,
./tests/test_deployment_verification.py:403:                    if stub.f['bad_contract']:
./tests/test_deployment_verification.py:426:    def run_stub(self, expect_sha=SHA, bypass=None, stub=None, **kw):
./tests/test_deployment_verification.py:429:        stub = stub or _Stub(**faults)
./tests/test_deployment_verification.py:431:            return dv.verify(stub.url, expect_sha=expect_sha, bypass=bypass, **opts)
./tests/test_deployment_verification.py:433:            stub.close()
./tests/test_deployment_verification.py:599:            r = self.run_stub(stub=victim, bypass='synthetic-bypass')
./tests/test_deployment_verification.py:607:        stub = _Stub()
./tests/test_deployment_verification.py:608:        stub.f['redirect_to'] = stub.url
./tests/test_deployment_verification.py:609:        stub.f['redirect_path'] = '/api/v28/deployment'
./tests/test_deployment_verification.py:610:        r = self.run_stub(stub=stub)
./tests/test_deployment_verification.py:612:        self.assertEqual(len([s for s in stub.seen if s['path'] == '/api/v28/deployment']), 1)
./tests/test_deployment_verification.py:615:        stub = _Stub(set_cookie=True)
./tests/test_deployment_verification.py:616:        r = self.run_stub(stub=stub)
./tests/test_deployment_verification.py:618:        self.assertTrue(all(s['cookie'] is None for s in stub.seen))
./tests/test_deployment_verification.py:621:        stub = _Stub(protected=True, conversation_status=500, echo_auth=True)
./tests/test_deployment_verification.py:622:        r = self.run_stub(stub=stub, bypass='synthetic-bypass')
./tests/test_deployment_verification.py:627:        self.assertTrue(all(s['bypass'] == 'synthetic-bypass' for s in stub.seen))
./tests/test_deployment_verification.py:628:        anon = [s for s in stub.seen if s['auth'] is None and '/projects/' in s['path']]
./tests/test_deployment_verification.py:635:        stub = _Stub(project_id='../../admin')
./tests/test_deployment_verification.py:636:        r = self.run_stub(stub=stub)
./tests/test_deployment_verification.py:638:        self.assertFalse(any('admin' in s['path'] for s in stub.seen))
./tests/test_deployment_verification.py:674:        stub = _Stub()
./tests/test_deployment_verification.py:679:                self.assertEqual(dv.main([stub.url, '--expect-sha', SHA, '--out', out]), 0)
./tests/test_deployment_verification.py:681:                self.assertEqual(dv.main([stub.url, '--out', out]), 2)                       # no SHA -> BLOCKED
./tests/test_deployment_verification.py:682:                stub.f['conversation_status'] = 500
./tests/test_deployment_verification.py:683:                self.assertEqual(dv.main([stub.url, '--expect-sha', SHA]), 1)               # FAILED
./tests/test_deployment_verification.py:687:                self.assertEqual(dv.main([stub.url, '--bypass-token-env', 'X;rm -rf /']), 3)
./tests/test_deployment_verification.py:700:            stub.close()
./tests/test_m3_preview_logic.py:880:            'user_id': 'u1', 'internal_project_id': 'tenant_abc', 'prompt': 'Build a todo app',
./tests/test_m49_clean_room.py:150:    '<body><h1 aria-label="Todo List">Todo List</h1><ul><li>Buy milk</li></ul></body></html>'
./tests/test_m49_clean_room.py:152:_SEED_README = '# Todo App\n\nMinimal todo list app used for the M4.9 clean-room verification run.\n'
./tests/test_m49_clean_room.py:158:    '    assert "Todo List" in html\n'
./tests/test_m49_clean_room.py:202:        pr = self.client.post('/api/v28/projects', headers=h, json={'title': 'M4.9 clean-room todo'})
./tests/test_m49_clean_room.py:210:            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_m49_clean_room.py:212:            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
./tests/test_m49_clean_room.py:251:                              'todo list must keep passing after this fix'})
./tests/test_m49_clean_room.py:302:        self.assertEqual(cand['spec']['title'], 'Todo')
./tests/test_m49_clean_room.py:314:        self.assertEqual(db_candidate['spec'].title, 'Todo')
./tests/test_m4d1_atomic_accept.py:47:    'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_m4d1_atomic_accept.py:49:    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
./tests/test_m4d1_atomic_accept.py:448:        self.assertEqual(spec_repo._store[result['version_id']].title, 'Todo')
./tests/test_m4d1_atomic_accept.py:479:            self.assertEqual(spec_repo._store[vid].title, 'Todo')
./tests/test_m4d2b_parity_and_worker.py:170:            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_m4d2b_parity_and_worker.py:172:            'acceptance': [{'id': acceptance_id, 'requirement_id': 'R1', 'text': 'home shows todo list'}],
./tests/test_m4d2b_parity_and_worker.py:290:            json={'followup': 'fix the todo list -- M4D2B_CLASSIFY:system_bug M4D2B_IDS:A1 per acceptance A1'})
./tests/test_m4d2_live_fastapi_redis.py:136:            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_m4d2_live_fastapi_redis.py:138:            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
./tests/test_m4d2_live_fastapi_redis.py:153:            json={'followup': 'Add a delete button to each todo item.'})
./tests/test_m4d2_live_fastapi_redis.py:177:            'title': 'Todo', 'summary': 'Todo app with delete', 'stack': ['python'],
./tests/test_m4d2_live_fastapi_redis.py:179:                              {'id': 'R2', 'text': 'delete a todo', 'kind': 'functional', 'mandatory': True}],
./tests/test_m4d2_live_fastapi_redis.py:180:            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
./tests/test_m4d2_live_fastapi_redis.py:220:            'title': 'Todo', 'summary': 'Todo', 'stack': ['python'],
./tests/test_m4d2_live_fastapi_redis.py:268:            'title': 'Todo', 'summary': 'Todo', 'stack': ['python'],
./tests/test_m4d2_live_fastapi_redis.py:302:            'title': 'Todo', 'summary': 'Todo', 'stack': ['python'],
./tests/test_m4d2_live_postgres.py:86:    'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_m4d2_live_postgres.py:88:    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
./tests/test_m4d2_live_postgres.py:97:# omni_prod.storage.S3ArtifactStore, not a stub that pretends to work.
./tests/test_m4_acceptance.py:41:    'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_m4_acceptance.py:43:    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
./tests/test_m4_acceptance.py:86:        new_spec = ProductSpec.from_dict({**SPEC, 'title': 'Todo Plus'})
./tests/test_m4_acceptance.py:291:        self.assertEqual(spec.title, 'Todo')  # F: the spec tied to v1, never "latest"
./tests/test_m4_acceptance.py:341:        self.assertEqual(outcome.candidate_spec.title, 'Todo Plus')  # a real, new spec
./tests/test_m4_acceptance.py:487:            'title': 'Todo', 'summary': 'x', 'stack': ['python'],
./tests/test_m4_modification_engine.py:11:    'title': 'Todo',
./tests/test_m4_modification_engine.py:12:    'summary': 'Todo app',
./tests/test_m4_modification_engine.py:18:        {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
./tests/test_m4_modification_engine.py:23:    'title': 'Todo',
./tests/test_m4_modification_engine.py:24:    'summary': 'Todo app',
./tests/test_m4_modification_engine.py:31:        {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
./tests/test_m4_modification_engine.py:313:        self.assertEqual(outcome.candidate_spec.title, 'Todo')
./tests/test_m4_worker.py:36:    'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_m4_worker.py:38:    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
./tests/test_m4_worker.py:41:EVOLVED_SPEC = {**SPEC, 'title': 'Todo Plus'}
./tests/test_m4_worker.py:228:        self.assertEqual(f['candidate_spec'].title, 'Todo')  # unchanged spec, free-repair path
./tests/test_m4_worker.py:244:        self.assertEqual(f['candidate_spec'].title, 'Todo Plus')  # evolved spec carried through
./tests/test_modification_diff.py:7:    'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_modification_diff.py:9:    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
./tests/test_modification_diff.py:79:            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_modification_diff.py:85:                {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
./tests/test_modification_diff.py:110:        new_dict['title'] = 'Super Todo'
./tests/test_modification_repository.py:35:    'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_modification_repository.py:37:    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
./tests/test_modification_repository.py:39:SPEC_V2 = {**SPEC, 'title': 'Todo v2'}
./tests/test_modification_repository.py:358:        self.assertEqual(json.loads(insert_params[3])['title'], 'Todo')
./tests/test_modification_repository.py:397:        self.assertEqual(out['spec'].title, 'Todo')
./tests/test_modification_repository.py:461:        self.assertEqual(spec_repo._store[new_id].title, 'Todo')
./tests/test_modification_repository.py:613:        self.assertEqual(spec_repo._store[result['version_id']].title, 'Todo')
./tests/test_modifier_engine.py:10:    'title': 'Todo',
./tests/test_modifier_engine.py:11:    'summary': 'Todo app',
./tests/test_modifier_engine.py:17:        {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
./tests/test_modifier_engine.py:141:            spec=_spec(), repository={'app.py': 'BROKEN'}, followup='the todo list never shows anything',
./tests/test_preview_smoke.py:21:        "<h1>טבלת ליגה</h1><form id='add'><input name='team' placeholder='שם קבוצה'><button>הוספה</button></form>"
./tests/test_preview_smoke.py:134:        self.assertIn('placeholder page', line)
./tests/test_product_evolution.py:8:    'title': 'Todo',
./tests/test_product_evolution.py:9:    'summary': 'Todo app',
./tests/test_product_evolution.py:15:        {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
./tests/test_product_evolution.py:41:            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_product_evolution.py:47:                {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
./tests/test_product_evolution.py:68:        self.assertEqual(sent['spec']['title'], 'Todo')
./tests/test_product_evolution.py:85:            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_product_evolution.py:88:                {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
./tests/test_product_evolution.py:89:                {'id': 'A1b', 'requirement_id': 'R1', 'text': 'todo list updates live'},
./tests/test_product_evolution.py:94:            {'id': 'A1b', 'requirement_id': 'R1', 'text': 'todo list updates live'},
./tests/test_repair_stop_loss.py:176:        prev = ExecutionReport(False, (AcceptanceFailure('PREVIEW', 'placeholder page'),))
./tests/test_skills_runtime_and_review.py:65:        rtl = [f for f in static_findings(repo, {'request': 'a todo site'}) if 'rtl' in f.problem.lower()]
./tests/test_spec_repository.py:7:    'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
./tests/test_spec_repository.py:9:    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
./tests/test_spec_repository.py:75:        self.assertEqual(json.loads(params[2])['title'], 'Todo')
./tests/test_spec_repository.py:95:        self.assertEqual(spec.title, 'Todo')
./tests/test_spec_repository.py:104:        self.assertEqual(spec.title, 'Todo')
./tests/test_v22_autonomous_core.py:18:    'title': 'Todo',
./tests/test_v22_autonomous_core.py:19:    'summary': 'Todo app',
./tests/test_v22_autonomous_core.py:25:        {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}
./tests/test_v22_autonomous_core.py:77:        ).build('todo')
./tests/test_visual_edit.py:177:                            '<input name="borrower" placeholder="Who borrows?">\n</body></html>\n',
./tests/test_visual_edit.py:192:        r = V.locate(REPO, {'tag': 'input', 'attrs': {'name': 'borrower', 'placeholder': 'Who borrows?'}})
./tests/test_worker_deploy_recovery.py:268:    stub = d / 'gate.sh'
./tests/test_worker_deploy_recovery.py:269:    stub.write_text('#!/usr/bin/env bash\nn=$(cat "%s/n"); read -ra c < "%s/codes"\n'
./tests/test_worker_deploy_recovery.py:272:    return f'bash {stub}', d
```


## SECRETS

```
omni_prod/acceptance_pipeline.py:10:from .secret_redaction import redact
omni_prod/account_tenant.py:5:import base64, hmac, re, secrets, threading
omni_prod/account_tenant.py:6:from .auth import issue_token, verify_token, AuthError
omni_prod/account_tenant.py:10:def _hash_password(password:str,salt:bytes)->str:
omni_prod/account_tenant.py:11:    return base64.urlsafe_b64encode(pbkdf2_hmac('sha256',password.encode(),salt,250_000)).decode()
omni_prod/account_tenant.py:17:    password_hash:str
omni_prod/account_tenant.py:36:    def __init__(self,*,token_secret:str):
omni_prod/account_tenant.py:37:        if len(token_secret)<32: raise ValueError('token_secret must be at least 32 chars')
omni_prod/account_tenant.py:38:        self._secret=token_secret
omni_prod/account_tenant.py:44:    def register(self,*,email:str,password:str)->tuple[Account,str]:
omni_prod/account_tenant.py:47:        if len(password)<10: raise ValueError('password must be at least 10 characters')
omni_prod/account_tenant.py:50:            salt=secrets.token_bytes(16)
omni_prod/account_tenant.py:51:            aid='usr_'+secrets.token_urlsafe(12)
omni_prod/account_tenant.py:52:            acct=Account(aid,email,_hash_password(password,salt),base64.urlsafe_b64encode(salt).decode(),datetime.now(timezone.utc).isoformat())
omni_prod/account_tenant.py:54:            return acct,issue_token(user_id=aid,org_id='omni-control',role='creator',secret=self._secret,ttl_seconds=7*24*3600)
omni_prod/account_tenant.py:56:    def login(self,*,email:str,password:str)->tuple[Account,str]:
omni_prod/account_tenant.py:60:            if not aid: raise PermissionError('invalid credentials')
omni_prod/account_tenant.py:63:            if not hmac.compare_digest(acct.password_hash,_hash_password(password,salt)): raise PermissionError('invalid credentials')
omni_prod/account_tenant.py:64:            return acct,issue_token(user_id=aid,org_id='omni-control',role='creator',secret=self._secret,ttl_seconds=7*24*3600)
omni_prod/account_tenant.py:66:    def authenticate(self,token:str)->Account:
omni_prod/account_tenant.py:67:        try: claims=verify_token(token,secret=self._secret)
omni_prod/account_tenant.py:77:            pid='prj_'+secrets.token_urlsafe(10)
omni_prod/agents_registry.py:142:            "expose_secret_values",
omni_prod/agent_catalog.py:82:    _r('security_reviewer', QUALITY, 'Security Reviewer', 'check access boundaries and secrets',
omni_prod/agent_catalog.py:83:       ('authorization checks', 'secret detection', 'dependency review'),
omni_prod/agent_catalog.py:176:       ('palette.propose', 'typography.select', 'design.tokens', 'references'), 'approved choices are used consistently'),
omni_prod/agent_catalog.py:179:    _r('integration_secret_steward', PLATFORM, 'Integration & Secret Steward', 'ownership of commercial connections',
omni_prod/agent_catalog.py:180:       ('scopes', 'vault refs', 'revoke', 'managed/customer/BYOK'), 'no secret in any product, log or export'),
omni_prod/agent_os/agents.py:21:    'memory': 'no long-term memory beyond the project (contract, versions, events); never stores secrets',
omni_prod/agent_os/agents.py:84:     'connectors with secret references', ('api_connector_generation', 'oauth_connector'), 'security_agent', (), (),
omni_prod/agent_os/agents.py:106:     ('secret_detection', 'preview_access_check', 'security_release_gate'), 'quality_gate_agent',
omni_prod/agent_os/agents.py:154:     (U('tests/test_replicate_image_test.py'),), {'config': ('OMNI_IMAGE_PROVIDER_BASE_URL', 'OMNI_IMAGE_PROVIDER_API_KEY_REF')}),
omni_prod/agent_os/agents.py:185:     'injects provider/DB/queue/worker/budget/token/artifact failures; real kill and drain on the host', ('provider_failure_test',),
omni_prod/agent_os/agents.py:206:        forbidden_actions=('approve its own output', 'spend outside the reservation', 'read or print secrets',
omni_prod/agent_os/agents.py:216:        security_requirements=('no secrets in evidence', 'owner/tenant scoping on every read'),
omni_prod/agent_os/audit.py:41:    'GEMINI_API_KEY', 'OMNI_MODEL_CATALOG_JSON', 'OMNI_SANDBOX_RUNNER_URL', 'OMNI_DATABASE_URL', 'OMNI_REDIS_URL',
omni_prod/agent_os/contracts.py:21:#   BLOCKED               a named external blocker (credential, contract, configuration)
omni_prod/agent_os/departments.py:62:               ('ux_ui_design_agent', 'localization_rtl_agent'), (), (), (), 'never hard-codes colours outside the design tokens',
omni_prod/agent_os/departments.py:63:               ('D06',), 'design tokens from the brief', 'visual QA layout rules desktop + mobile', 'inside the codegen call'),
omni_prod/agent_os/departments.py:75:               ('payments adapter', 'email/SMS adapter', 'OAuth connector'), 'never stores raw secrets; references only',
omni_prod/agent_os/departments.py:76:               ('D07',), 'connectors', 'contract tests + live credential checks', 'per-integration quote (none connected)'),
omni_prod/agent_os/departments.py:81:    Department('D11', 'Security, Privacy & Compliance', 'threats, permissions, secrets, IP',
omni_prod/agent_os/departments.py:93:               'provider matrix validation, circuit-breaker tests', 'cost per verified success, not token price'),
omni_prod/agent_os/evidence.py:13:                 'preview private by default (anonymous 401)', 'owner token access', 'share link only while shared',
omni_prod/agent_os/evidence.py:19:                'settled $0.105302 at metered usage incl. thinking tokens', '039574f', 'worker-host',
omni_prod/agent_os/meta.py:133:    ('expired preview token', 'tests/test_preview_access.py::test_public_needs_no_token_and_expired_tokens_fail', '401 private page'),
omni_prod/agent_os/recorder.py:109:            final.append(('security_agent', ('secret_detection', 'security_release_gate'), bool(gates['security'].get('passed')), 'static scan'))
omni_prod/agent_os/resolver.py:15:            'unit_test_execution', 'browser_launch', 'behavioral_acceptance_test', 'repair_execution', 'secret_detection',
omni_prod/agent_os/skills.py:27:    'Discovery / Requirements': ('discovery_agent', 'requirements_traceability', ('web',), 'deterministic ($0)', 'user request + answers; no secrets', ()),
omni_prod/agent_os/skills.py:34:    'Authentication': ('identity_auth_agent', 'security_agent', ('web',), '$0 (platform identity)', 'password hashes, session hashes only', ()),
omni_prod/agent_os/skills.py:35:    'Integration': ('integration_agent', 'security_agent', ('web',), 'provider dependent', 'secret references only', ()),
omni_prod/agent_os/skills.py:40:    'Security': ('security_agent', 'quality_gate_agent', ('web',), '$0', 'findings only, never secret values', ()),
omni_prod/agent_os/skills.py:47:    'Observability': ('observability_agent', 'sre_reliability_agent', ('web',), '$0', 'events in customer language, no prompts/secrets', ()),
omni_prod/agent_os/skills.py:58:    'Automation': ('automation_agent', 'qa_agent', ('automation',), 'per run', 'secret references only', ()),
omni_prod/agent_os/skills.py:90:    'design_token_generation': (('omni_prod.skills_runtime:VISUAL_DESIGN',), (PAID,), ''),
omni_prod/agent_os/skills.py:125:    'password_reset': ((), (), 'generated-app password reset not implemented; platform accounts are tracked separately'),
omni_prod/agent_os/skills.py:169:    'secret_detection': (('omni_prod.security_testing:hostile_repository_scan',), (VERIFY_REPLAY, PAID, U('tests/test_m49_clean_room.py')), 'static'),
omni_prod/agent_os/skills.py:173:    'csrf_check': (('omni_prod.browser_session:extract_session_token',), (U('tests/test_v24_auth.py'),), 'platform API only'),
omni_prod/agent_os/skills.py:218:    'preview_token_issue': (('omni_prod.preview_access:PreviewAccess.issue',), (FREE,), ''),
omni_prod/agent_os/skills.py:219:    'preview_token_revoke': (('omni_prod.preview_access:PreviewAccess.set_mode',), (FREE,), ''),
omni_prod/agent_os/skills.py:273:    'text_to_image': ('OMNI_IMAGE_PROVIDER_BASE_URL', 'OMNI_IMAGE_PROVIDER_API_KEY_REF', 'OMNI_IMAGE_PROVIDER_MODEL'),
omni_prod/agent_os/skills.py:303:        security_constraints=('no secrets in prompts, logs or evidence', 'runs inside the isolated sandbox when executing code'),
omni_prod/agent_os/truth_matrix.py:121:    Row('No secrets or unsafe code in the product', 'security scan', 'security_agent',
omni_prod/agent_os/truth_matrix.py:122:        ('secret_detection', 'security_release_gate')),
omni_prod/agent_os/truth_matrix.py:126:        ('preview_access_protect', 'preview_token_revoke'), shown_to_customer=True),
omni_prod/attempt_ledger.py:12:configuration. Nothing here contains credentials.
omni_prod/attempt_ledger.py:43:def metered_cost(option, input_tokens: int | None, output_tokens: int | None) -> Decimal | None:
omni_prod/attempt_ledger.py:44:    """usage x catalog price. Unknown when the provider did not report tokens."""
omni_prod/attempt_ledger.py:45:    if option is None or input_tokens is None or output_tokens is None:
omni_prod/attempt_ledger.py:48:    return (Decimal(input_tokens) * option.input_per_million
omni_prod/attempt_ledger.py:49:            + Decimal(output_tokens) * option.output_per_million) / million
omni_prod/attempt_ledger.py:75:    input_tokens: int | None = None
omni_prod/attempt_ledger.py:76:    output_tokens: int | None = None
omni_prod/attempt_ledger.py:77:    cached_tokens: int | None = None
omni_prod/attempt_ledger.py:232:            'expected_cost_usd', 'metered_cost_usd', 'provider_reported_cost_usd', 'input_tokens',
omni_prod/attempt_ledger.py:233:            'output_tokens', 'cached_tokens', 'latency_ms', 'outcome', 'verification_class',
omni_prod/attempt_ledger.py:238:_COMPLETABLE = ('model_version', 'provider_request_id', 'metered_cost_usd', 'provider_reported_cost_usd', 'input_tokens',
omni_prod/attempt_ledger.py:239:                'output_tokens', 'cached_tokens', 'latency_ms', 'verification_class', 'failure_reason')
omni_prod/auth.py:22:def issue_token(*, secret:str,user_id:str,org_id:str,role:str,ttl_seconds:int=3600,now:int|None=None,session_id:str|None=None)->str:
omni_prod/auth.py:23:    if len(secret)<32: raise ValueError('auth secret must be at least 32 chars')
omni_prod/auth.py:33:    msg=f'{header}.{payload}'.encode(); sig=_b64(hmac.new(secret.encode(),msg,hashlib.sha256).digest())
omni_prod/auth.py:36:def verify_token(token:str,*,secret:str,now:int|None=None)->AuthClaims:
omni_prod/auth.py:37:    if len(secret)<32: raise AuthError('auth secret unavailable')
omni_prod/auth.py:39:        header,payload,sig=token.split('.')
omni_prod/auth.py:40:        msg=f'{header}.{payload}'.encode(); expected=_b64(hmac.new(secret.encode(),msg,hashlib.sha256).digest())
omni_prod/auth.py:43:        if h.get('alg')!='HS256' or h.get('typ')!='OMNI': raise AuthError('invalid token header')
omni_prod/auth.py:45:        if exp<=ts: raise AuthError('token expired')
omni_prod/auth.py:48:    except Exception as exc: raise AuthError('invalid token') from exc
omni_prod/autonomous_agents.py:56:    "Design for international use, accessibility, responsive behavior, safe secrets, observability and testability rather than a toy demo."
omni_prod/autonomous_agents.py:90:    'Never write outside the repository and never include secrets. Generate automated tests, README/setup, accessible responsive UI when relevant, i18n scaffolding, safe integration adapters, CI/deployment metadata, and production-grade error handling. Avoid generic AI-template styling; create a coherent design system appropriate to the product. '
omni_prod/autonomous_agents.py:162:        data = self.gateway.complete_json(system=_ARCHITECT_SYSTEM, user=user, max_tokens=6000)
omni_prod/autonomous_agents.py:175:            data = self.gateway.complete_json(system=_ARCHITECT_SYSTEM, user=correction, max_tokens=6000)
omni_prod/autonomous_agents.py:190:            # and 12k output tokens truncated the JSON on every model.
omni_prod/autonomous_agents.py:191:            max_tokens=24000,
omni_prod/autonomous_agents.py:206:    'Never change tests, acceptance policy, secrets, manifests or lockfiles; '
omni_prod/autonomous_agents.py:219:                system=_REPAIR_SYSTEM, user=json.dumps(payload, ensure_ascii=False), max_tokens=20000)
omni_prod/autonomous_agents.py:235:            system=_REPAIR_SYSTEM_V1, user=json.dumps(payload, ensure_ascii=False), max_tokens=12000)
omni_prod/autonomous_agents.py:251:            max_tokens=2000,
omni_prod/backup.py:4:deployed worker image, with the real environment. Never prints secrets.
omni_prod/benchmark_suite.py:30:    'automation': 'workflow automation system with triggers, actions, retries, idempotency, secrets and run history',
omni_prod/benchmark_suite.py:43:    ('06','advanced','Add integrations through secret references only; never hard-code credentials.'),
omni_prod/brand_native_clients.py:9:        'app/build.gradle.kts':f'''plugins {{ id("com.android.application") }}\nandroid {{ namespace="{app_id}"; compileSdk=35\n defaultConfig {{ applicationId="{app_id}"; minSdk=26; targetSdk=35; versionCode=1; versionName="1.0" }}\n signingConfigs {{ create("release") {{ val ks=System.getenv("ONE48AI_ANDROID_KEYSTORE"); if (ks != null) storeFile=file(ks); storePassword=System.getenv("ONE48AI_ANDROID_STORE_PASSWORD"); keyAlias=System.getenv("ONE48AI_ANDROID_KEY_ALIAS"); keyPassword=System.getenv("ONE48AI_ANDROID_KEY_PASSWORD") }} }}\n buildTypes {{ release {{ signingConfig=signingConfigs.getByName("release"); isMinifyEnabled=false }} }} }}\n''',
omni_prod/brand_native_clients.py:12:        '.github/workflows/android-aab.yml':'name: 148ai-android-aab\non: [workflow_dispatch]\njobs:\n  aab:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-java@v4\n        with: {distribution: temurin, java-version: "17"}\n      - uses: gradle/actions/setup-gradle@v4\n        with: {gradle-version: "8.9"}\n      - run: gradle bundleRelease\n        env:\n          ONE48AI_ANDROID_KEYSTORE: ${{ secrets.ONE48AI_ANDROID_KEYSTORE }}\n          ONE48AI_ANDROID_STORE_PASSWORD: ${{ secrets.ONE48AI_ANDROID_STORE_PASSWORD }}\n          ONE48AI_ANDROID_KEY_ALIAS: ${{ secrets.ONE48AI_ANDROID_KEY_ALIAS }}\n          ONE48AI_ANDROID_KEY_PASSWORD: ${{ secrets.ONE48AI_ANDROID_KEY_PASSWORD }}\n',
omni_prod/brand_native_clients.py:13:        'README.md':'# 148AI Android client\nBranded source wrapper for the 148AI web platform. A signed AAB requires external Android signing credentials.\n',
omni_prod/brand_native_clients.py:22:        'README.md':'# 148AI iOS client\nBranded SwiftUI/WKWebView client source. Signed IPA/TestFlight requires Apple Developer credentials and macOS/Xcode.\n',
omni_prod/browser_probe.py:85:    else if (el.type === 'password') v = 'Passw0rd-' + round;
omni_prod/browser_session.py:3:The token itself is unchanged (same identity service, same server-side
omni_prod/browser_session.py:23:__all__ = ["COOKIE_NAME", "SessionTokenError", "browser_session_readiness", "cookie_settings",
omni_prod/browser_session.py:24:           "extract_session_token"]
omni_prod/browser_session.py:30:class SessionTokenError(Exception):
omni_prod/browser_session.py:56:def extract_session_token(request, *, allowed_origins: Iterable[str]) -> tuple[str, str]:
omni_prod/browser_session.py:61:        raise SessionTokenError(401, "authentication required")
omni_prod/browser_session.py:64:        raise SessionTokenError(401, "authentication required")
omni_prod/browser_session.py:66:        raise SessionTokenError(403, "cross-site request refused for cookie session")
omni_prod/build_contract.py:66:    secret_reference_only: bool = True
omni_prod/build_contract.py:83:            "secret_reference_only": self.secret_reference_only,
omni_prod/build_contract.py:94:            secret_reference_only=bool(data.get("secret_reference_only", True)),
omni_prod/build_control.py:11:secrets). Writing it is best effort: a log failure never changes a build.
omni_prod/capability_planner.py:209:        # Token-aware: "api" must not match "rapid", "db" must not match "feedback".
omni_prod/capability_repository.py:89:    dependency. No secret values are stored here or in the SQL schema.
omni_prod/company_os.py:44:               ('creative director', 'design tokens', 'anti-template checks', 'media gateway'),
omni_prod/company_os.py:52:    Department('security', 'Security / Privacy', 'Protect tenants, secrets, generated code and infrastructure.',
omni_prod/company_os.py:53:               ('threat modeling', 'secret scanning', 'tenant tests', 'abuse controls', 'incident response'),
omni_prod/company_os.py:54:               ('sandbox', 'secret scanner', 'RBAC tests', 'audit chain', 'rate limits'),
omni_prod/config.py:22:    secret_key: str
omni_prod/config.py:28:    s3_secret_key: str
omni_prod/config.py:44:        secret = _required("OMNI_SECRET_KEY")
omni_prod/config.py:45:        if env == "production" and len(secret) < 48:
omni_prod/config.py:46:            raise RuntimeError("OMNI_SECRET_KEY must be at least 48 chars in production")
omni_prod/config.py:55:            secret_key=secret,
omni_prod/config.py:61:            s3_secret_key=_required("OMNI_S3_SECRET_KEY"),
omni_prod/creator_accounts.py:4:import base64, hmac, re, secrets
omni_prod/creator_accounts.py:5:from .account_tenant import Account, ProjectRecord, _hash_password, _EMAIL_RE, AccountService
omni_prod/creator_accounts.py:6:from .auth import issue_token, verify_token, AuthError
omni_prod/creator_accounts.py:18:    def __init__(self, *, token_secret: str, pool: DatabasePool):
omni_prod/creator_accounts.py:19:        if len(token_secret) < 32:
omni_prod/creator_accounts.py:20:            raise ValueError('token_secret must be at least 32 chars')
omni_prod/creator_accounts.py:21:        self._secret = token_secret
omni_prod/creator_accounts.py:24:            token_secret=token_secret,
omni_prod/creator_accounts.py:29:    def register(self, *, email: str, password: str) -> tuple[Account, str]:
omni_prod/creator_accounts.py:30:        return self.identity.register(email=email, password=password)
omni_prod/creator_accounts.py:32:    def login(self, *, email: str, password: str) -> tuple[Account, str]:
omni_prod/creator_accounts.py:33:        return self.identity.login(email=email, password=password)
omni_prod/creator_accounts.py:35:    def authenticate(self, token: str) -> Account:
omni_prod/creator_accounts.py:36:        return self.identity.authenticate(token)
omni_prod/credential_binding.py:7:from .secrets_manager import SecretResolver
omni_prod/credential_binding.py:10:class CredentialMode(str, Enum):
omni_prod/credential_binding.py:16:class CredentialStatus(str, Enum):
omni_prod/credential_binding.py:23:class CredentialBinding:
omni_prod/credential_binding.py:26:    mode: CredentialMode
omni_prod/credential_binding.py:27:    status: CredentialStatus
omni_prod/credential_binding.py:29:    secret_reference: str
omni_prod/credential_binding.py:34:        if self.mode in {CredentialMode.CUSTOMER_CONNECTED, CredentialMode.BYOK} and not self.tenant_id:
omni_prod/credential_binding.py:35:            raise ValueError("tenant_id is required for customer credential modes")
omni_prod/credential_binding.py:36:        scheme, sep, remainder = self.secret_reference.partition(":")
omni_prod/credential_binding.py:38:            raise ValueError("secret reference must use an approved env: or vault: reference")
omni_prod/credential_binding.py:39:        if any(token in self.secret_reference.lower() for token in ("bearer ", "sk-live-", "sk-proj-")):
omni_prod/credential_binding.py:40:            raise ValueError("secret reference must not contain inline credential material")
omni_prod/credential_binding.py:49:            "configured": self.status == CredentialStatus.CONFIGURED,
omni_prod/credential_binding.py:53:class CredentialBindingBroker:
omni_prod/credential_binding.py:54:    def __init__(self, *, resolvers: Mapping[str, SecretResolver]) -> None:
omni_prod/credential_binding.py:57:    def resolve(self, binding: CredentialBinding, *, tenant_id: str) -> str:
omni_prod/credential_binding.py:58:        if binding.status != CredentialStatus.CONFIGURED:
omni_prod/credential_binding.py:59:            raise RuntimeError(f"credential binding is not configured: {binding.status.value}")
omni_prod/credential_binding.py:60:        if binding.mode in {CredentialMode.CUSTOMER_CONNECTED, CredentialMode.BYOK}:
omni_prod/credential_binding.py:62:                raise PermissionError("tenant is not authorized for this credential binding")
omni_prod/credential_binding.py:63:        scheme = binding.secret_reference.split(":", 1)[0]
omni_prod/credential_binding.py:66:            raise RuntimeError(f"no secret resolver configured for {scheme}")
omni_prod/credential_binding.py:67:        return resolver.resolve(binding.secret_reference)
omni_prod/design_system.py:6:class DesignTokens:
omni_prod/design_system.py:18:def derive_tokens(project_seed: str) -> DesignTokens:
omni_prod/design_system.py:27:    return DesignTokens(radius,spacing,type,density,motion,personality)
omni_prod/design_system.py:29:def anti_template_fingerprint(tokens: DesignTokens) -> str:
omni_prod/design_system.py:30:    return sha256(repr(tokens).encode()).hexdigest()[:16]
omni_prod/discovery.py:220:    assets: dict[str, dict] = field(default_factory=dict)  # owner-checked attachment id + digest, never bytes/secrets
omni_prod/discovery.py:400:    """Ordered, bounded tokens from stated colour words or hex colours."""
omni_prod/discovery.py:403:    tokens = []
omni_prod/discovery.py:406:        token = match.group(1).lower() if match.group(1) else _COLOUR_ALIASES[match.group(2).lower()]
omni_prod/discovery.py:407:        if token not in tokens:
omni_prod/discovery.py:408:            tokens.append(token)
omni_prod/discovery.py:410:    return (words_seen if preserve_words else tokens)[:6]
omni_prod/discovery.py:414:    return [_COLOR_HEX.get(token, token) for token in colour_palette(text)]
omni_prod/discovery.py:492:    tokens = palette_css(color)
omni_prod/discovery.py:493:    colours = (f'primary colour {tokens[0]}; palette {", ".join(tokens)}' if tokens else
omni_prod/discovery.py:495:    if tokens:
omni_prod/economics_report.py:9:  * metered = provider tokens x versioned catalog price (incl. thinking tokens
omni_prod/evidence_export.py:10:It opens a READ ONLY transaction, writes nothing, calls no model and prints no secret (known secret shapes are
omni_prod/evidence_export.py:11:redacted; flags come from an allow-list of non-secret names). It reports the approved brief revision/fingerprint and
omni_prod/evidence_export.py:17:reproduction (keep that directory private: generated code is not configuration but could contain secret-like text).
omni_prod/evidence_export.py:33:NON_SECRET_FLAGS = (
omni_prod/evidence_export.py:43:    text = re.sub(r'(?i)(key|token|secret|password|authorization)(["\' :=]+)[^\s"\',]+', r'\1\2[redacted]', text)
omni_prod/evidence_export.py:64:            'flags': {k: env.get(k) for k in NON_SECRET_FLAGS if k != 'OMNI_SOURCE_COMMIT'},
omni_prod/evidence_export.py:65:            'flags_unset': [k for k in NON_SECRET_FLAGS if not env.get(k)]}
omni_prod/evidence_export.py:131:    keys = ('OMNI_S3_ENDPOINT', 'OMNI_S3_BUCKET', 'OMNI_S3_ACCESS_KEY', 'OMNI_S3_SECRET_KEY')
omni_prod/evidence_export.py:136:                           access_key=env['OMNI_S3_ACCESS_KEY'], secret_key=env['OMNI_S3_SECRET_KEY'])
omni_prod/evidence_export.py:237:            out['generated_files'] = ('MISSING: OMNI_S3_ENDPOINT/BUCKET/ACCESS_KEY/SECRET_KEY are not set where this runs; run it '
omni_prod/evidence_json.py:12:carry credentials, e.g. an endpoint with its API key); they fail encoding and
omni_prod/identity_lifecycle.py:9:import secrets
omni_prod/identity_lifecycle.py:11:from .account_tenant import Account, _EMAIL_RE, _hash_password
omni_prod/identity_lifecycle.py:12:from .auth import AuthError, issue_token, verify_token
```


## MIGRATIONS

```
./omni_prod/migrations.py
./omni_prod/migration_runner.py
./omni_prod/__pycache__/migrations.cpython-313.pyc
./omni_prod/__pycache__/migration_runner.cpython-313.pyc
./tests/integration/m5_migration_021_psql_check.sql
./tests/test_m5_migration_numbering.py
./tests/test_migration_rollback_tolerance.py
./tests/__pycache__/test_m5_migration_numbering.cpython-313-pytest-9.0.2.pyc
./tests/__pycache__/test_migration_rollback_tolerance.cpython-313-pytest-9.0.2.pyc
```


## TESTS

```
    282 tests/financial_fault_harness.py
     16 tests/fixtures/visual/bad_app.py
     12 tests/fixtures/visual/good_app.py
      0 tests/integration/__init__.py
     81 tests/integration/test_financial_fault_experiment.py
      9 tests/integration/test_live_model.py
    162 tests/integration/test_live_preview_runtime.py
     13 tests/integration/test_live_sandbox_security.py
     30 tests/integration/test_live_stack.py
    167 tests/integration/test_m495_provider_adapter.py
    241 tests/integration/test_m5_build_economics_postgres.py
     52 tests/integration/test_m5_live_llm_usage.py
     64 tests/integration/test_m5_live_media_provider.py
    129 tests/integration/test_m5_managed_web_saas_live.py
     13 tests/integration/test_mobile_signing_readiness.py
    130 tests/integration/test_profit_billing_events_pg.py
     37 tests/integration/test_qstash_scheduler_live.py
     84 tests/integration/test_r2_generated_storage_live.py
     56 tests/integration/test_v28_creator_persistence.py
     40 tests/m4d2_rq_job_target.py
    169 tests/m4d2b_local_model_server.py
     97 tests/m4d2b_worker_process.py
    109 tests/m5_worker_harness.py
     32 tests/policy_fixtures.py
     58 tests/test_acceptance_coverage.py
    208 tests/test_actual_cost_settlement.py
    285 tests/test_agent_os.py
     64 tests/test_architect_assignment_gate.py
     61 tests/test_architect_spec_shape.py
     18 tests/test_architect_website_no_crud.py
     56 tests/test_asset_requirements.py
    244 tests/test_attempt_ledger.py
     40 tests/test_backup_restore.py
    137 tests/test_behavior_acceptance_in_build.py
     60 tests/test_brief_capability_detection.py
    115 tests/test_browser_probe.py
    203 tests/test_build_cancel_and_log.py
     82 tests/test_build_state_machine.py
     28 tests/test_ci_workflow_concurrency.py
     64 tests/test_company_loss.py
    140 tests/test_consistency_gate.py
    231 tests/test_content_only_site.py
    535 tests/test_conversation_os.py
     55 tests/test_conversation_ux.py
    133 tests/test_crash_recovery_and_change_parity.py
    178 tests/test_customer_economics_views.py
     84 tests/test_customer_flow_rejects.py
     19 tests/test_customer_font_security.py
     45 tests/test_database_pool_health.py
     91 tests/test_db_fingerprint.py
    287 tests/test_demand_driven_infrastructure.py
    156 tests/test_dependency_policy.py
    773 tests/test_deployment_verification.py
    225 tests/test_discovery_and_approval.py
    122 tests/test_discovery_endpoints.py
     83 tests/test_economics_report.py
     79 tests/test_entitlements.py
    227 tests/test_evidence_export.py
    104 tests/test_evidence_json.py
    107 tests/test_failure_injection.py
     60 tests/test_failure_replay.py
     51 tests/test_financial_journal_guard.py
    293 tests/test_golden_mod_path_live_postgres.py
     33 tests/test_history_without_artifact_download.py
    193 tests/test_infisical_secret_store.py
    227 tests/test_intake_assistant_he.py
    647 tests/test_intake_budget_pg.py
    190 tests/test_intake_complexity.py
     21 tests/test_intake_explicit_intent_regression.py
     47 tests/test_intake_family_intent.py
     41 tests/test_intake_palette_preservation.py
     30 tests/test_intake_palette_regression.py
     18 tests/test_intake_product_family_regression.py
    176 tests/test_intake_requirements_preservation.py
    115 tests/test_intake_worker_route.py
    333 tests/test_intelligence_plane.py
     54 tests/test_isolation_check.py
    106 tests/test_j1_j2_existing_engine_integration.py
     95 tests/test_j1_real_agent_feature_flag.py
     87 tests/test_j3_three_repair_round_policy.py
     82 tests/test_janitor_redispatch.py
     38 tests/test_legacy_paths_guard.py
     64 tests/test_live_build_stores_spec.py
    111 tests/test_m2_native_logic.py
   1082 tests/test_m3_preview_logic.py
     56 tests/test_m495_asset_evidence.py
    271 tests/test_m495_capability_executor.py
     99 tests/test_m495_capability_planner.py
    160 tests/test_m495_capability_registry.py
    247 tests/test_m495_capability_repository.py
    150 tests/test_m495_capability_verification.py
    178 tests/test_m495_golden_acceptance.py
    166 tests/test_m495_provider_adapters_credentials.py
    101 tests/test_m495_provider_contracts.py
     97 tests/test_m495_provider_pricing_economics.py
    227 tests/test_m495_provider_router.py
    191 tests/test_m495_skills_agents_registry.py
     49 tests/test_m495_subscription_settlement.py
     90 tests/test_m495_truth_lock.py
    138 tests/test_m495_truth_readiness_api.py
    164 tests/test_m495_worker_capabilities.py
    333 tests/test_m49_clean_room.py
    204 tests/test_m49_lifecycle.py
    294 tests/test_m49_sandbox_security.py
    679 tests/test_m4_acceptance.py
    356 tests/test_m4_modification_engine.py
    310 tests/test_m4_worker.py
    653 tests/test_m4d1_atomic_accept.py
    475 tests/test_m4d2_live_fastapi_redis.py
    853 tests/test_m4d2_live_postgres.py
    384 tests/test_m4d2b_parity_and_worker.py
     80 tests/test_m5_browser_session.py
    249 tests/test_m5_build_contract_binding.py
    545 tests/test_m5_build_economics.py
    187 tests/test_m5_creator_workspace.py
    248 tests/test_m5_economics_reconciliation.py
    166 tests/test_m5_generated_app_storage_isolation.py
    141 tests/test_m5_identity_lifecycle.py
    356 tests/test_m5_infrastructure_contracts.py
    274 tests/test_m5_llm_usage_evidence.py
    433 tests/test_m5_managed_web_saas_profile.py
    434 tests/test_m5_media_provider_adapters.py
     43 tests/test_m5_migration_numbering.py
     86 tests/test_m5_planner_target_detection.py
    161 tests/test_m5_product_architect.py
     93 tests/test_m5_project_lifecycle.py
     47 tests/test_m5_public_path_truth.py
    168 tests/test_m5_ssrf_guard.py
    424 tests/test_m5_web_saas_acceptance.py
     91 tests/test_maintenance_live_postgres.py
     75 tests/test_manifest_shape.py
    141 tests/test_migration_rollback_tolerance.py
    192 tests/test_model_catalog_routing.py
     48 tests/test_model_gateway_idempotency.py
     88 tests/test_model_json_parsing.py
    134 tests/test_model_transient_retry.py
     72 tests/test_modification_context.py
    134 tests/test_modification_diff.py
    639 tests/test_modification_repository.py
    208 tests/test_modifier_engine.py
     69 tests/test_overlay.py
    468 tests/test_plan_driven_execution.py
    133 tests/test_preview_access.py
    218 tests/test_preview_data_durability.py
     75 tests/test_preview_router.py
    135 tests/test_preview_smoke.py
    117 tests/test_product_evolution.py
    109 tests/test_profit_protection.py
    333 tests/test_provider_quota_and_dialects.py
    113 tests/test_public_pricing_economics.py
    198 tests/test_qa_budget.py
    134 tests/test_qa_plan_parity.py
    240 tests/test_qstash_scheduler.py
     91 tests/test_quality_repairable.py
     28 tests/test_r2_config_diagnostic.py
    137 tests/test_r2_generated_credentials.py
     26 tests/test_r2_storage_signing.py
    356 tests/test_real_docker_drain_recovery.py
    147 tests/test_registry_audit.py
     28 tests/test_rehearsal.py
     54 tests/test_release_blocks_on_failed_acceptance.py
    222 tests/test_release_policy.py
     36 tests/test_repair_sees_main_file.py
    186 tests/test_repair_stop_loss.py
    137 tests/test_replicate_connection.py
    120 tests/test_replicate_image_test.py
     79 tests/test_requirement_ledger.py
     70 tests/test_sandbox_cleanup.py
     99 tests/test_sandbox_runner_health.py
     45 tests/test_secret_scan_ci_exemption.py
    174 tests/test_skills_runtime_and_review.py
     48 tests/test_spec_language.py
    114 tests/test_spec_repository.py
     80 tests/test_task_quality_routing.py
     83 tests/test_universal_family_skill_resolution.py
     98 tests/test_uploaded_logo.py
     81 tests/test_v12_core.py
     63 tests/test_v13_core.py
     64 tests/test_v14_core.py
     70 tests/test_v15_acceptance.py
    109 tests/test_v16_release_gate.py
    118 tests/test_v17_preflight.py
     29 tests/test_v18_supplychain_security.py
     78 tests/test_v19_reliability.py
     85 tests/test_v20_observability_recovery.py
    149 tests/test_v21_gemini_remediation.py
    177 tests/test_v22_autonomous_core.py
     63 tests/test_v22_sandbox_executor.py
    138 tests/test_v23_investor_grade.py
     30 tests/test_v24_auth.py
    177 tests/test_v24_international.py
     71 tests/test_v24_native_remote.py
    176 tests/test_v25_unified_v10_parity.py
    127 tests/test_v26_universal_pro.py
    206 tests/test_v27_rights_company_os.py
    253 tests/test_v28_148ai_launch.py
     36 tests/test_v7_content_only_provenance.py
    114 tests/test_v7_readiness_regression.py
    157 tests/test_v7_semantic_intake_architect.py
     48 tests/test_v7_semantic_marker_provenance.py
     41 tests/test_v7_visitor_no_login_boundary.py
     44 tests/test_vercel_entrypoint.py
    330 tests/test_visual_edit.py
    116 tests/test_visual_qa.py
     29 tests/test_website_requirements_regression.py
     79 tests/test_worker_budget_binding.py
    483 tests/test_worker_deploy_recovery.py
    119 tests/test_worker_entrypoint.py
    166 tests/test_worker_repository_parity.py
    283 tests/test_workspace_version_conflict.py
  33607 total
```


## CI

```
.github/workflows/148ai-final-regression-smoke.yml
.github/workflows/148ai-image-rollback-readiness.yml
.github/workflows/148ai-intake-gates.yml
.github/workflows/148ai-intake-runtime-readiness.yml
.github/workflows/148ai-merge-candidate-review.yml
.github/workflows/148ai-prototype-intake-enable.yml
.github/workflows/148ai-rebuild-safe-rollback-images.yml
.github/workflows/148ai-registry-refresh.yml
.github/workflows/148ai-v7-registry-audit-evidence.yml
.github/workflows/148ai-v7-registry-sync.yml
.github/workflows/backup-restore.yml
.github/workflows/build-evidence.yml
.github/workflows/deploy-worker.yml
.github/workflows/deployment-verify.yml
.github/workflows/evidence-export.yml
.github/workflows/financial-fault-experiment.yml
.github/workflows/golden-rehearsal.yml
.github/workflows/intake-budget-pg.yml
.github/workflows/internal-entitlement.yml
.github/workflows/migrate-target.yml
.github/workflows/model-probe.yml
.github/workflows/neon-bootstrap-ci.yml
.github/workflows/postdeploy-checks.yml
.github/workflows/registry-snapshot-review.yml
.github/workflows/t01-private-prototype-contract-audit.yml
.github/workflows/t01-registry-repair.yml
.github/workflows/v11-overlay-ci.yml
.github/workflows/v24-ci.yml
.github/workflows/verify.yml
.github/workflows/worker-diagnostics.yml
---- ci content ----
name: Founder prototype regression smoke (self-hosted, no AI spend)
# One-time read-only source validation on OCI, isolated from docker compose.
# Network disabled; no provider API calls, deploys or database writes.
on:
  push:
    branches: [codex/148ai-verified-intake-2026-10-12]
    paths: [.github/workflows/148ai-final-regression-smoke.yml]
permissions:
  contents: read
jobs:
  focused-regression:
    runs-on: [self-hosted, omni-worker]
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
        with:
          path: regression-source
          persist-credentials: false
      - name: Test source in existing image, network disabled
        shell: bash
        run: |
          set -euo pipefail
          img=$(docker inspect -f '{{.Config.Image}}' omni-worker-worker-1)
          docker run --rm --network none --read-only --tmpfs /tmp:rw \
            -e PYTHONPATH=/workspace -e PYTHONDONTWRITEBYTECODE=1 \
            -v "$GITHUB_WORKSPACE/regression-source:/workspace:ro" -w /workspace \
            "$img" python -m unittest -q \
              tests.test_provider_quota_and_dialects \
              tests.test_qa_budget \
              tests.test_qa_plan_parity \
              tests.test_agent_os \
              tests.test_m5_browser_session \
              tests.test_model_transient_retry
          echo "::notice title=Regression::Real source tests passed in existing image; no external AI or network used"
name: One-time rollback image availability diagnosis

# Read-only Docker metadata: DO NOT drain or restart anything.
on:
  push:
    branches: [codex/148ai-verified-intake-2026-10-12]
    paths: [.github/workflows/148ai-image-rollback-readiness.yml]

permissions:
  contents: read
jobs:
  inspect:
    runs-on: [self-hosted, omni-worker]
    timeout-minutes: 5
    steps:
      - name: Check whether images backing running containers still exist
        shell: bash
        run: |
          set -uo pipefail
          for s in worker intake-worker intake-maintain preview-worker; do
            cid=$(docker ps -aq -f "name=^/omni-worker-${s}-1$" | head -1)
            if [ -z "$cid" ]; then
              echo "::warning title=image $s::no container found"
              continue
            fi
            img=$(docker inspect -f '{{.Image}}' "$cid" 2>/dev/null || true)
            [ -n "$img" ] || { echo "::warning title=image $s::no image ID"; continue; }
            if docker image inspect "$img" >/dev/null 2>&1; then
              echo "::notice title=image $s::existing container image ID available"
            else
              echo "::error title=image $s::container runs from an image ID no longer present in Docker image store; cannot tag old image for rollback"
            fi
            echo "s=$s running=$(docker inspect -f '{{.State.Running}}' "$cid") ref=$(docker inspect -f '{{.Config.Image}}' "$cid")"
          done
          docker system df --format '{{json .}}' | head -c 1400 || true
          echo
          echo "::notice title=diagnosis::read-only; no service or image was changed"
name: 148AI intake and architecture regression gates

on:
  pull_request:
  push:
    branches: [codex/148ai-verified-intake-2026-10-12]

concurrency:
  group: ci-${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.head.ref || github.ref_name }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  deterministic-regressions:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Record environment and revision
        run: |
          mkdir -p evidence
          git rev-parse HEAD > evidence/revision.txt
          python --version > evidence/python.txt
      - name: Product intent and capability closure (no provider calls)
        run: |
          set -o pipefail
          python -m unittest -v tests.test_intake_palette_preservation tests.test_intake_palette_regression tests.test_customer_flow_rejects.CustomerFlowTests.test_free_colour_combination_is_preserved_in_binding tests.test_customer_flow_rejects.CustomerFlowTests.test_multi_colour_message_keeps_the_full_palette tests.test_intake_family_intent tests.test_architect_assignment_gate tests.test_architect_website_no_crud tests.test_intake_complexity 2>&1 | tee evidence/unit.txt
      - name: Hostile static cases (does not prove sandbox isolation)
        run: python scripts/run_hostile_static_suite.py > evidence/hostile-static.json
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: deterministic-regression-evidence
          path: evidence/
name: One-time 148AI intake runtime readiness

# Read-only. Uses EXISTING self-hosted worker and running containers.
# No checkout, registry pull, provider request, migration, restart, or build.
on:
  push:
    branches: [codex/148ai-verified-intake-2026-10-12]
    paths: [.github/workflows/148ai-intake-runtime-readiness.yml]

permissions:
  contents: read

jobs:
  readiness:
    runs-on: [self-hosted, omni-worker]
    timeout-minutes: 6
    steps:
      - name: Existing worker and intake container states (read-only)
        run: |
          set -euo pipefail
          docker ps --format '{{.Names}}: {{.Status}}' | grep -E 'omni-worker-(worker|intake-worker|intake-maintain|sandbox-runner|preview-worker)-1' || true
          docker exec -i omni-worker-intake-worker-1 python - <<'PY'
          import os
          from omni_prod.intake.budget import allowed_models
          from omni_prod.intake import mode
          print('intake_worker_model_enabled=' + str(os.getenv('OMNI_INTAKE_MODEL') == '1'))
          print('intake_worker_queues=' + str(os.getenv('OMNI_WORKER_QUEUES', '')))
          print('intake_worker_has_database=' + str(bool(os.getenv('OMNI_DATABASE_URL'))))
          print('intake_worker_has_redis=' + str(bool(os.getenv('OMNI_REDIS_URL'))))
          print('intake_worker_allowlisted_model_ids=' + ','.join(allowed_models()))
          print('intake_worker_provider_keys_present=' + ','.join(
              x.replace('_API_KEY', '') for x in ('GEMINI_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GROQ_API_KEY')
              if os.getenv(x)))
          print('intake_worker_source_commit=' + str(os.getenv('OMNI_SOURCE_COMMIT','unknown'))[:12])
          for key in ('OMNI_INTAKE_MODEL_BUDGET_USD', 'OMNI_INTAKE_DAILY_BUDGET_USD',
                      'OMNI_INTAKE_CALL_BUDGET_USD'):
              print(key + '_is_set=' + str(bool(os.getenv(key))))
          try:
              from omni_prod.intake.budget import quote
              q=quote(system='You are an assistant.', user='Create a simple website', max_tokens=700)
              print('intake_quote_usd=' + str(q.amount_usd))
          except Exception as exc:
              print('intake_quote_unavailable=' + type(exc).__name__ + ': ' + str(exc)[:140])
          PY
          docker exec -i omni-worker-intake-maintain-1 python - <<'PY'
          import os
          print('intake_maintain_enabled=' + str(os.getenv('OMNI_INTAKE_MODEL')=='1'))
          PY
          echo "::notice title=READ-ONLY::No request to an AI provider or database write was performed"
name: 148AI merge candidate compatibility (read-only)
'on':
  pull_request:
    branches:
      - milestone/pre-staging-2026-10-05
    paths:
      - '.github/workflows/148ai-merge-candidate-review.yml'
      - '.github/workflows/worker-diagnostics.yml'
      - '.github/workflows/build-evidence.yml'
      - 'omni_prod/**'
      - 'tests/**'
      - 'AGENT_OS_REGISTRY.json'
      - 'docs/AGENT_SKILL_STATUS.md'
      - 'omni_prod/registry_evidence_lock.json'
      - '.github/workflows/v24-ci.yml'
      - '.github/workflows/v11-overlay-ci.yml'

permissions:
  contents: read

concurrency:
  group: merge-candidate-${{ github.event.pull_request.number }}-${{ github.event.pull_request.head.sha }}-${{ github.event.pull_request.base.sha }}
  cancel-in-progress: true

jobs:
  merge-compatibility:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      # Deliberately checkout the synthetic merge SHA, unlike source-truth CI.
      - uses: actions/checkout@v4
        with:
          ref: refs/pull/${{ github.event.pull_request.number }}/merge
          fetch-depth: 0
          persist-credentials: false
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Show merge identity
        run: |
          echo "source_sha=${{ github.event.pull_request.head.sha }}"
          echo "base_sha=${{ github.event.pull_request.base.sha }}"
          echo "merge_sha=$(git rev-parse HEAD)"
          git diff --check HEAD^1 HEAD
      - name: Install CI dependencies (no provider credentials)
        run: python -m pip install -r requirements-production.txt -r requirements-test.txt
      - name: Compute ephemeral truthful reports for merged implementation
        shell: bash
        run: |
          set -euo pipefail
          python -m omni_prod.agent_os.audit --write
          python -m omni_prod.registry_audit --write
          python -m omni_prod.agent_os.departments --write
          git diff --check
          # Regenerated evidence is intentionally NOT committed: stale
          # verification must not be promoted by changes from the base branch.
          git status --short
      - name: Run integration compatibility test suite on merged tree
        run: python -m pytest -q --junitxml=merge-compatibility.xml
      - name: Run registry no-inflation gate
        if: success()
        run: python -m omni_prod.agent_os.audit
      - name: Store merge test results and computed reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: 148ai-merge-compatibility-report
          path: |
            merge-compatibility.xml
            AGENT_OS_REGISTRY.json
            docs/AGENT_OS_REGISTRY.md
            docs/AGENT_SKILL_STATUS.md
            docs/DEPARTMENT_MATRIX.md
            DEPARTMENT_MATRIX.json
            TRUTH_MATRIX.json
            docs/TRUTH_MATRIX.md
          if-no-files-found: warn
```


## DEPS

```
# Direct production pins for the Vercel requirements parser.
fastapi==0.128.2
uvicorn==0.48.0
pydantic==2.13.4
psycopg[binary,pool]==3.3.6
redis==8.1.0
rq==2.12.0
boto3==1.43.94
[project]
name = "148ai-v28-vercel-review"
version = "28.0.1"
requires-python = ">=3.12"
dependencies = [
  "fastapi==0.128.2",
  "uvicorn==0.48.0",
  "pydantic==2.13.4",
  "psycopg[binary,pool]==3.3.6",
  "redis==8.1.0",
  "rq==2.12.0",
  "boto3==1.43.94"
]
```
