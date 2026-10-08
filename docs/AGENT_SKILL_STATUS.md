# Agent/Skill status — computed by `python -m omni_prod.registry_audit --write`

Generated from `omni_prod/agent_catalog.py` (what the founder spec defines) and `omni_prod/runtime_bindings.py` (what runs, with evidence). Do not edit by hand.

Lifecycle: DEFINED (catalog only) → IMPLEMENTED (code) → CONNECTED (configuration/provider observed) → VERIFIED (worked in a real run with an id) · BLOCKED (named credential/service missing).

Totals: VERIFIED 15, CONNECTED 2, IMPLEMENTED 0, BLOCKED 0, DEFINED 32

## management

| Agent | Status | Implementation | Configuration | Verification | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|
| Request Interpreter | VERIFIED | ProductArchitect, ArchitectAgent | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | live (web/self_contained_v1) | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84; golden-rehearsal run 37820429767 — task-list prompt: ready, quality 86, 2 min | one model call per build (~$0.005) | no clarification questions are asked; planner adds login/roles although the request says "no login" |
| Product Analyst | VERIFIED | ArchitectAgent | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | live (web/self_contained_v1) | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84; mod_c14435dc9baa44bdac784d0c15ed9b85 -> v_0bc82ef7b33b4210 — natural-language change accepted 2026-10-08 22:55; spec A1-A6 | shared with request_interpreter | acceptance criteria only; no user stories or edge-case analysis |
| Capability Resolver | VERIFIED | CapabilityPlanner, BuildContract | OMNI_DATABASE_URL: ok (deploy-worker migrations + queue probe PASS) | live (web/self_contained_v1) | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 | $0 (deterministic) | keyword-based game detection misclassifies "משחק" (football match) |
| Solution Architect | VERIFIED | ArchitectAgent, GENERATION_CONSTRAINTS | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | live (web/self_contained_v1) | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 | shared with request_interpreter | one fixed stack (Python stdlib + SQLite in /tmp); no durable data or API-contract design |
| Project Orchestrator | VERIFIED | _run_live_build_job, AutonomousProductEngine, main | OMNI_REDIS_URL: ok (deploy-worker queue probe PASS); OMNI_DATABASE_URL: ok (deploy-worker migrations + queue probe PASS) | live (web/self_contained_v1) | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84; STATUS.md "Golden E2E #1: full chain from the founder's workspace" (2026-10-08 23:05) | $0 (deterministic) | fixed 4-step pipeline, not a task graph; no cancel; no resume of a half-finished build (janitor fails it) |
| Cost Controller | VERIFIED | RoutedModelGateway, PostgresSubscriptionService, qa_used_usd | OMNI_DATABASE_URL: ok (deploy-worker migrations + queue probe PASS) | live (web/self_contained_v1) | build-evidence run 37832677078 — QA real spend since paid tier $0.35; tests/test_provider_quota_and_dialects.py | $0 (deterministic) | no per-step cost shown to the user; no provider invoice reconciliation |

## software

| Agent | Status | Implementation | Configuration | Verification | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|
| UX Designer | DEFINED | — | — | not verified | — | — | not implemented |
| Frontend Developer | VERIFIED | GeneratorAgent | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | live (web/self_contained_v1) | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84; mod_c14435dc9baa44bdac784d0c15ed9b85 -> v_0bc82ef7b33b4210 — natural-language change accepted 2026-10-08 22:55; spec A1-A6 | part of ~$0.07 per build | no browser check of flows; UI quality gaps found by the founder: alert() errors, ISO dates, hidden filter state |
| Backend Developer | VERIFIED | GeneratorAgent | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | live (web/self_contained_v1) | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84; mod_c14435dc9baa44bdac784d0c15ed9b85 -> v_0bc82ef7b33b4210 — natural-language change accepted 2026-10-08 22:55; spec A1-A6 | shared with frontend_developer | input validation only when the user asks for it |
| Data Engineer | DEFINED ⚠ | — | — | not verified | — | — | not implemented |
| Identity & Access Engineer | DEFINED | — | — | not verified | — | — | not implemented |
| Integration Engineer | DEFINED | — | — | not verified | — | — | not implemented |
| Repository Maintainer | VERIFIED | PostgresProjectWorkspace, S3ArtifactStore, restore_version_with_spec | OMNI_DATABASE_URL: ok (deploy-worker migrations + queue probe PASS); OMNI_S3_ENDPOINT/OMNI_S3_BUCKET/OMNI_S3_ACCESS_KEY/OMNI_S3_SECRET_KEY: ok (deploy-worker storage probe PASS) | live (web/self_contained_v1) | mod_c14435dc9baa44bdac784d0c15ed9b85 -> v_0bc82ef7b33b4210 — natural-language change accepted 2026-10-08 22:55; spec A1-A6; ZIP of v_0bc82ef7b33b4210 opened by the founder 2026-10-08 22:59 | $0 | — |

## quality

| Agent | Status | Implementation | Configuration | Verification | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|
| QA Verifier | VERIFIED | RemoteSandboxRepositoryExecutor, PreviewReadyExecutor, QualityAwareExecutor | OMNI_SANDBOX_RUNNER_URL/OMNI_SANDBOX_SHARED_SECRET: ok (deploy-worker sandbox probe PASS (every deploy)) | live (web/self_contained_v1) | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84; golden-rehearsal run 37820429767 — task-list prompt: ready, quality 86, 2 min | $0 model cost (sandbox compute) | tests are written by the same model that writes the code; no independent behaviour/browser check of the running product |
| Security Reviewer | VERIFIED | hostile_repository_scan, evaluate_release_gates | none needed | live (web/self_contained_v1) | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 | $0 | static scan only; no authorization testing of the generated app |
| Repair Agent | VERIFIED | RepairAgent | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok); OMNI_SANDBOX_RUNNER_URL/OMNI_SANDBOX_SHARED_SECRET: ok (deploy-worker sandbox probe PASS (every deploy)) | live (web/self_contained_v1) | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84; golden-rehearsal run 37814985551 — 5 repair rounds converged | part of ~$0.07 per build | repairs the whole repository rather than a minimal patch |
| Preview Operator | VERIFIED | DockerPreviewProvider, make_handler | PREVIEW_DOMAIN_TEMPLATE/OMNI_PREVIEW_HOST_SUFFIX: ok (deploy-worker "Preview edge is up" PASS) | live (web/self_contained_v1) | https://prv-1760dedc67864c0186aa0cdf945bab0d.151-145-89-132.sslip.io — v_246bae81234e4c39 shown in the workspace | $0 (worker host) | data in /tmp is lost when the preview stops; temporary sslip.io address, open to anyone with the link |
| Release Agent | DEFINED | — | — | not verified | — | — | not implemented |
| Operations Agent | VERIFIED | run_once | OMNI_DATABASE_URL: ok (deploy-worker migrations + queue probe PASS) | live (platform) | tests/test_maintenance_live_postgres.py; deploy-worker "janitor started" | $0 | no alerting; no health monitoring of generated products |

## assets

| Agent | Status | Implementation | Configuration | Verification | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|
| Asset Planner | DEFINED | — | — | not verified | — | — | not implemented |
| Visual Creator | CONNECTED | PredictionImageProvider | REPLICATE_API_TOKEN: ok (Replicate authentication live-verified on Preview (STATUS 2026-10-06)) | unit tests only | tests/test_replicate_image_test.py | about $0.003 per image (FLUX Schnell list price) | no image has been generated live yet; not on the build path |
| Consistency Director | DEFINED | — | — | not verified | — | — | not implemented |
| Asset QA | DEFINED | — | — | not verified | — | — | not implemented |
| Asset Librarian | DEFINED | — | — | not verified | — | — | not implemented |

## media

| Agent | Status | Implementation | Configuration | Verification | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|
| Media Producer | DEFINED | — | — | not verified | — | — | not implemented |
| Scriptwriter | DEFINED | — | — | not verified | — | — | not implemented |
| Storyboard Director | DEFINED | — | — | not verified | — | — | not implemented |
| Video Creator | DEFINED | — | — | not verified | — | — | not implemented |
| Voice & Audio Producer | DEFINED | — | — | not verified | — | — | not implemented |
| Timeline Editor | DEFINED | — | — | not verified | — | — | not implemented |
| Media QA | DEFINED | — | — | not verified | — | — | not implemented |
| Publishing Operator | DEFINED | — | — | not verified | — | — | not implemented |

## games

| Agent | Status | Implementation | Configuration | Verification | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|
| Game Designer | DEFINED | — | — | not verified | — | — | not implemented |
| Game Architect | DEFINED | — | — | not verified | — | — | not implemented |
| Gameplay Developer | DEFINED | — | — | not verified | — | — | not implemented |
| Level Designer | DEFINED | — | — | not verified | — | — | not implemented |
| Game Asset Coordinator | DEFINED | — | — | not verified | — | — | not implemented |
| Save & Progression Engineer | DEFINED | — | — | not verified | — | — | not implemented |
| Playtest Agent | DEFINED | — | — | not verified | — | — | not implemented |
| Multiplayer Engineer | DEFINED | — | — | not verified | — | — | not implemented |

## automation

| Agent | Status | Implementation | Configuration | Verification | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|
| Automation Designer | DEFINED | — | — | not verified | — | — | not implemented |
| Connector Operator | DEFINED | — | — | not verified | — | — | not implemented |
| Scheduler Operator | DEFINED | — | — | not verified | — | — | not implemented |
| Automation QA | DEFINED | — | — | not verified | — | — | not implemented |
| Agent App Builder | DEFINED | — | — | not verified | — | — | not implemented |

## platform

| Agent | Status | Implementation | Configuration | Verification | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|
| Skill Builder | DEFINED | — | — | not verified | — | — | not implemented |
| Skill Evaluator | DEFINED | — | — | not verified | — | — | not implemented |
| Registry Auditor | CONNECTED | audit | none needed | unit tests only | tests/test_registry_audit.py | $0 | — |
| Provider Evaluator | VERIFIED | probe, cost_projection | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | live (platform) | model-probe run 37814803770 — 3 Gemini models ok; OpenAI/Anthropic refused: no credit | < $0.001 per probe | no quality benchmark across providers yet |

## Mismatches found

- Data Engineer: older registry says PARTIAL but no code on a runtime path serves this role
- 9 "integration" skills are PARTIAL in the registry but none runs on a verified path (treat as DEFINED until a runtime binding with evidence exists)
- 32 "media" skills are PARTIAL in the registry but none runs on a verified path (treat as DEFINED until a runtime binding with evidence exists)
- 8 "target" skills are PARTIAL in the registry but none runs on a verified path (treat as DEFINED until a runtime binding with evidence exists)
- every skill's "last_verified" is the 2026-10-04 metadata check, not a capability run

