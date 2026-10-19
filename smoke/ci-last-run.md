# v24-ci — last main run (2026-10-19T17:37:09Z)

- commit: `baf070a59b7b8b5922ffa0032fff0b23e92ef761`
- run_id: [39295200919](https://github.com/Shayfly/desktop-tutorial/actions/runs/39295200919) (attempt 1)
- test job: **FAILURE**
- tests: **FAIL** — 1799 passed, 3 failed, 181 skipped
- AcceptanceW: **FAIL**

## Failing tests

- FAIL `tests.test_agent_os.TruthMatrixTests.test_model_instruction_alone_is_not_verified`
- FAIL `tests.test_conversation_os.DepartmentTests.test_every_agent_in_exactly_one_department_and_files_current`
- FAIL `tests.test_m4_acceptance.AcceptanceW.test_W_every_non_fastapi_test_module_passes`

## CostClass behavioural proofs

- `test_m5_plan_build_class::test_amateur_costs_less_than_studio_for_the_same_task`: **PASS**
- `test_worker_budget_binding::test_pro_keeps_its_class_budget_when_worker_env_is_lower`: **PASS**
- `test_m5_plan_build_class::test_pro_and_studio_get_different_allowlists`: **PASS**
- `test_m5_plan_build_class::test_margin_holds_on_every_paid_tier_in_the_worst_case`: **PASS**

## Per module

| module | PASS/FAIL | passed | failed | skipped |
|---|---|---|---|---|
| `integration` | PASS | 6 | 0 | 34 |
| `test_acceptance_coverage` | PASS | 3 | 0 | 0 |
| `test_actual_cost_settlement` | PASS | 14 | 0 | 2 |
| `test_agent_os` | FAIL | 14 | 1 | 5 |
| `test_amateur_cost_class_lock` | PASS | 5 | 0 | 0 |
| `test_architect_assignment_gate` | PASS | 5 | 0 | 0 |
| `test_architect_spec_shape` | PASS | 4 | 0 | 0 |
| `test_architect_website_no_crud` | PASS | 1 | 0 | 0 |
| `test_asset_requirements` | PASS | 6 | 0 | 0 |
| `test_attempt_ledger` | PASS | 13 | 0 | 0 |
| `test_auth_error_mapping` | PASS | 7 | 0 | 0 |
| `test_backup_restore` | PASS | 3 | 0 | 0 |
| `test_behavior_acceptance_in_build` | PASS | 5 | 0 | 0 |
| `test_brief_capability_detection` | PASS | 4 | 0 | 0 |
| `test_browser_probe` | PASS | 5 | 0 | 4 |
| `test_build_cancel_and_log` | PASS | 8 | 0 | 5 |
| `test_build_state_machine` | PASS | 3 | 0 | 3 |
| `test_ci_workflow_concurrency` | PASS | 1 | 0 | 0 |
| `test_company_loss` | PASS | 5 | 0 | 0 |
| `test_consistency_gate` | PASS | 14 | 0 | 0 |
| `test_content_only_site` | PASS | 17 | 0 | 0 |
| `test_conversation_os` | FAIL | 33 | 1 | 4 |
| `test_conversation_ux` | PASS | 5 | 0 | 0 |
| `test_crash_recovery_and_change_parity` | PASS | 0 | 0 | 5 |
| `test_customer_economics_views` | PASS | 11 | 0 | 0 |
| `test_customer_flow_rejects` | PASS | 8 | 0 | 0 |
| `test_customer_font_security` | PASS | 1 | 0 | 0 |
| `test_database_pool_health` | PASS | 2 | 0 | 0 |
| `test_db_fingerprint` | PASS | 4 | 0 | 0 |
| `test_demand_driven_infrastructure` | PASS | 17 | 0 | 0 |
| `test_dependency_policy` | PASS | 17 | 0 | 0 |
| `test_deploy_rollback_snapshot` | PASS | 9 | 0 | 0 |
| `test_deployment_endpoint_public` | PASS | 2 | 0 | 0 |
| `test_deployment_verification` | PASS | 51 | 0 | 0 |
| `test_discovery_and_approval` | PASS | 9 | 0 | 7 |
| `test_discovery_endpoints` | PASS | 7 | 0 | 0 |
| `test_economics_report` | PASS | 7 | 0 | 0 |
| `test_entitlements` | PASS | 7 | 0 | 0 |
| `test_evidence_export` | PASS | 6 | 0 | 4 |
| `test_evidence_json` | PASS | 5 | 0 | 0 |
| `test_failure_injection` | PASS | 12 | 0 | 0 |
| `test_failure_replay` | PASS | 5 | 0 | 0 |
| `test_financial_journal_guard` | PASS | 2 | 0 | 0 |
| `test_golden_mod_path_live_postgres` | PASS | 0 | 0 | 6 |
| `test_history_without_artifact_download` | PASS | 1 | 0 | 0 |
| `test_infisical_secret_store` | PASS | 10 | 0 | 0 |
| `test_intake_assistant_he` | PASS | 18 | 0 | 0 |
| `test_intake_budget_pg` | PASS | 2 | 0 | 23 |
| `test_intake_complexity` | PASS | 11 | 0 | 0 |
| `test_intake_credits_by_plan` | PASS | 2 | 0 | 0 |
| `test_intake_explicit_intent_regression` | PASS | 3 | 0 | 0 |
| `test_intake_family_intent` | PASS | 2 | 0 | 0 |
| `test_intake_palette_preservation` | PASS | 4 | 0 | 0 |
| `test_intake_palette_regression` | PASS | 3 | 0 | 0 |
| `test_intake_product_family_regression` | PASS | 3 | 0 | 0 |
| `test_intake_requirements_preservation` | PASS | 11 | 0 | 0 |
| `test_intake_worker_route` | PASS | 7 | 0 | 0 |
| `test_intelligence_plane` | PASS | 30 | 0 | 1 |
| `test_isolation_check` | PASS | 6 | 0 | 0 |
| `test_j1_j2_existing_engine_integration` | PASS | 16 | 0 | 0 |
| `test_j1_real_agent_feature_flag` | PASS | 5 | 0 | 0 |
| `test_j3_three_repair_round_policy` | PASS | 4 | 0 | 0 |
| `test_janitor_redispatch` | PASS | 3 | 0 | 1 |
| `test_legacy_paths_guard` | PASS | 3 | 0 | 0 |
| `test_live_build_stores_spec` | PASS | 2 | 0 | 0 |
| `test_m2_native_logic` | PASS | 7 | 0 | 0 |
| `test_m3_preview_logic` | PASS | 85 | 0 | 0 |
| `test_m495_asset_evidence` | PASS | 2 | 0 | 0 |
| `test_m495_capability_executor` | PASS | 8 | 0 | 0 |
| `test_m495_capability_planner` | PASS | 8 | 0 | 0 |
| `test_m495_capability_registry` | PASS | 11 | 0 | 0 |
| `test_m495_capability_repository` | PASS | 12 | 0 | 0 |
| `test_m495_capability_verification` | PASS | 9 | 0 | 0 |
| `test_m495_golden_acceptance` | PASS | 1 | 0 | 0 |
| `test_m495_provider_adapters_credentials` | PASS | 10 | 0 | 0 |
| `test_m495_provider_contracts` | PASS | 10 | 0 | 0 |
| `test_m495_provider_pricing_economics` | PASS | 7 | 0 | 0 |
| `test_m495_provider_router` | PASS | 11 | 0 | 0 |
| `test_m495_skills_agents_registry` | PASS | 14 | 0 | 0 |
| `test_m495_subscription_settlement` | PASS | 1 | 0 | 0 |
| `test_m495_truth_lock` | PASS | 6 | 0 | 0 |
| `test_m495_truth_readiness_api` | PASS | 3 | 0 | 0 |
| `test_m495_worker_capabilities` | PASS | 4 | 0 | 0 |
| `test_m49_clean_room` | PASS | 0 | 0 | 1 |
| `test_m49_lifecycle` | PASS | 0 | 0 | 1 |
| `test_m49_sandbox_security` | PASS | 0 | 0 | 3 |
| `test_m4_acceptance` | FAIL | 21 | 1 | 1 |
| `test_m4_modification_engine` | PASS | 12 | 0 | 0 |
| `test_m4_worker` | PASS | 11 | 0 | 0 |
| `test_m4d1_atomic_accept` | PASS | 13 | 0 | 1 |
| `test_m4d2_live_fastapi_redis` | PASS | 0 | 0 | 8 |
| `test_m4d2_live_postgres` | PASS | 0 | 0 | 14 |
| `test_m4d2b_parity_and_worker` | PASS | 0 | 0 | 3 |
| `test_m5_browser_session` | PASS | 8 | 0 | 0 |
| `test_m5_build_contract_binding` | PASS | 8 | 0 | 0 |
| `test_m5_build_economics` | PASS | 33 | 0 | 0 |
| `test_m5_creator_workspace` | PASS | 12 | 0 | 0 |
| `test_m5_economics_reconciliation` | PASS | 16 | 0 | 0 |
| `test_m5_generated_app_storage_isolation` | PASS | 8 | 0 | 0 |
| `test_m5_identity_lifecycle` | PASS | 8 | 0 | 0 |
| `test_m5_infrastructure_contracts` | PASS | 26 | 0 | 0 |
| `test_m5_llm_usage_evidence` | PASS | 14 | 0 | 0 |
| `test_m5_managed_web_saas_profile` | PASS | 18 | 0 | 0 |
| `test_m5_media_provider_adapters` | PASS | 21 | 0 | 0 |
| `test_m5_migration_numbering` | PASS | 4 | 0 | 0 |
| `test_m5_plan_build_class` | PASS | 20 | 0 | 0 |
| `test_m5_planner_target_detection` | PASS | 7 | 0 | 0 |
| `test_m5_product_architect` | PASS | 8 | 0 | 0 |
| `test_m5_project_lifecycle` | PASS | 6 | 0 | 0 |
| `test_m5_public_path_truth` | PASS | 4 | 0 | 0 |
| `test_m5_ssrf_guard` | PASS | 14 | 0 | 0 |
| `test_m5_web_saas_acceptance` | PASS | 11 | 0 | 1 |
| `test_maintenance_live_postgres` | PASS | 0 | 0 | 2 |
| `test_manifest_shape` | PASS | 5 | 0 | 0 |
| `test_migration_rollback_tolerance` | PASS | 5 | 0 | 3 |
| `test_model_catalog_routing` | PASS | 17 | 0 | 0 |
| `test_model_gateway_idempotency` | PASS | 3 | 0 | 0 |
| `test_model_json_parsing` | PASS | 10 | 0 | 0 |
| `test_model_transient_retry` | PASS | 8 | 0 | 0 |
| `test_modification_context` | PASS | 4 | 0 | 0 |
| `test_modification_diff` | PASS | 13 | 0 | 0 |
| `test_modification_repository` | PASS | 43 | 0 | 0 |
| `test_modifier_engine` | PASS | 10 | 0 | 0 |
| `test_overlay` | PASS | 4 | 0 | 0 |
| `test_plan_driven_execution` | PASS | 13 | 0 | 14 |
| `test_preview_access` | PASS | 0 | 0 | 5 |
| `test_preview_data_durability` | PASS | 9 | 0 | 0 |
| `test_preview_router` | PASS | 4 | 0 | 0 |
| `test_preview_smoke` | PASS | 6 | 0 | 0 |
| `test_product_evolution` | PASS | 5 | 0 | 0 |
| `test_profit_protection` | PASS | 20 | 0 | 0 |
| `test_provider_quota_and_dialects` | PASS | 23 | 0 | 0 |
| `test_public_pricing_economics` | PASS | 8 | 0 | 0 |
| `test_qa_budget` | PASS | 20 | 0 | 0 |
| `test_qa_plan_parity` | PASS | 12 | 0 | 0 |
| `test_qstash_scheduler` | PASS | 18 | 0 | 0 |
| `test_quality_repairable` | PASS | 6 | 0 | 0 |
| `test_r2_config_diagnostic` | PASS | 2 | 0 | 0 |
| `test_r2_generated_credentials` | PASS | 9 | 0 | 0 |
| `test_r2_storage_signing` | PASS | 2 | 0 | 0 |
| `test_real_docker_drain_recovery` | PASS | 0 | 0 | 8 |
| `test_registry_audit` | PASS | 16 | 0 | 0 |
| `test_rehearsal` | PASS | 3 | 0 | 0 |
| `test_release_blocks_on_failed_acceptance` | PASS | 2 | 0 | 0 |
| `test_release_policy` | PASS | 18 | 0 | 1 |
| `test_repair_sees_main_file` | PASS | 4 | 0 | 0 |
| `test_repair_stop_loss` | PASS | 11 | 0 | 0 |
| `test_replicate_connection` | PASS | 10 | 0 | 0 |
| `test_replicate_image_test` | PASS | 8 | 0 | 0 |
| `test_requirement_ledger` | PASS | 7 | 0 | 0 |
| `test_reservation_worker_sigterm` | PASS | 2 | 0 | 0 |
| `test_sandbox_callers_real_policy` | PASS | 5 | 0 | 0 |
| `test_sandbox_cleanup` | PASS | 4 | 0 | 0 |
| `test_sandbox_runner_health` | PASS | 8 | 0 | 0 |
| `test_secret_scan_ci_exemption` | PASS | 7 | 0 | 0 |
| `test_skills_runtime_and_review` | PASS | 13 | 0 | 0 |
| `test_spec_language` | PASS | 5 | 0 | 0 |
| `test_spec_repository` | PASS | 5 | 0 | 0 |
| `test_task_quality_routing` | PASS | 6 | 0 | 0 |
| `test_universal_family_skill_resolution` | PASS | 10 | 0 | 0 |
| `test_uploaded_logo` | PASS | 8 | 0 | 0 |
| `test_v12_core` | PASS | 7 | 0 | 0 |
| `test_v13_core` | PASS | 6 | 0 | 0 |
| `test_v14_core` | PASS | 9 | 0 | 0 |
| `test_v15_acceptance` | PASS | 7 | 0 | 0 |
| `test_v16_release_gate` | PASS | 9 | 0 | 0 |
| `test_v17_preflight` | PASS | 6 | 0 | 0 |
| `test_v18_supplychain_security` | PASS | 8 | 0 | 0 |
| `test_v19_reliability` | PASS | 9 | 0 | 0 |
| `test_v20_observability_recovery` | PASS | 8 | 0 | 0 |
| `test_v21_gemini_remediation` | PASS | 7 | 0 | 0 |
| `test_v22_autonomous_core` | PASS | 12 | 0 | 0 |
| `test_v22_sandbox_executor` | PASS | 4 | 0 | 0 |
| `test_v23_investor_grade` | PASS | 10 | 0 | 0 |
| `test_v24_auth` | PASS | 5 | 0 | 0 |
| `test_v24_international` | PASS | 43 | 0 | 0 |
| `test_v24_native_remote` | PASS | 12 | 0 | 0 |
| `test_v25_unified_v10_parity` | PASS | 19 | 0 | 0 |
| `test_v26_universal_pro` | PASS | 10 | 0 | 0 |
| `test_v27_rights_company_os` | PASS | 15 | 0 | 0 |
| `test_v28_148ai_launch` | PASS | 23 | 0 | 0 |
| `test_v7_content_only_provenance` | PASS | 2 | 0 | 0 |
| `test_v7_readiness_regression` | PASS | 10 | 0 | 0 |
| `test_v7_semantic_intake_architect` | PASS | 10 | 0 | 0 |
| `test_v7_semantic_marker_provenance` | PASS | 3 | 0 | 0 |
| `test_v7_visitor_no_login_boundary` | PASS | 3 | 0 | 0 |
| `test_vercel_entrypoint` | PASS | 3 | 0 | 0 |
| `test_visual_edit` | PASS | 14 | 0 | 5 |
| `test_visual_qa` | PASS | 5 | 0 | 2 |
| `test_website_requirements_regression` | PASS | 2 | 0 | 0 |
| `test_worker_budget_binding` | PASS | 5 | 0 | 0 |
| `test_worker_deploy_recovery` | PASS | 29 | 0 | 4 |
| `test_worker_entrypoint` | PASS | 8 | 0 | 0 |
| `test_worker_repository_parity` | PASS | 10 | 0 | 0 |
| `test_workspace_version_conflict` | PASS | 14 | 0 | 0 |

_Test names and counts only; failure messages are not published._
