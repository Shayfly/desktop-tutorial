# Agent/Skill status — computed by `python -m omni_prod.registry_audit --write`

Generated from `omni_prod/agent_catalog.py` (roles), `omni_prod/skill_catalog.py` (directive §9 skills) and `omni_prod/runtime_bindings.py` (what runs, with evidence). Do not edit by hand.

Dimensions are separate: implementation · configuration · verification (scope + freshness) · blocked. VERIFIED always names what the run asserted, and only counts while the implementation is unchanged since the commit that ran; otherwise the row is STALE and needs re-verification.

Roles (61): VERIFIED 6, STALE 10, CONNECTED 3, DEFINED 42

Skills in the §9 catalog (137): VERIFIED 16, STALE 20, TESTED 17, IMPLEMENTED 7, NOT_IMPLEMENTED 77

## management

| Agent | Status | Implementation | Configuration | Verification | Blocked | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|---|
| Request Interpreter | STALE | ProductArchitect, ArchitectAgent | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | STALE — was verified for: a Hebrew prompt becomes a build contract for a single-page web app at b0a0cfa; code changed since: omni_prod/autonomous_agents.py, omni_prod/product_architect.py | — | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 [workspace@beb67b4]; golden-rehearsal run 37820429767 — task-list prompt: ready, quality 86, 2 min [worker-host@782dafd]; bld_8263a2a1905346399747f4fe8b92e919 -> v_f65e904334b04776 — founder library build 2026-10-09 02:30; HTTP behaviour probes passed [workspace@b0a0cfa] | one model call per build (~$0.005) | no discovery conversation: at most one heuristic question (see discovery_lead); planner adds login/roles although the request says "no login" |
| Product Analyst | STALE | ArchitectAgent | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | STALE — was verified for: acceptance criteria A1..An derived for the requested product at 3a4d822; code changed since: omni_prod/autonomous_agents.py | — | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 [workspace@beb67b4]; mod_c14435dc9baa44bdac784d0c15ed9b85 -> v_0bc82ef7b33b4210 — natural-language change accepted 2026-10-08 22:55; spec A1-A6 [workspace@3a4d822] | shared with request_interpreter | acceptance criteria only; no user stories or edge-case analysis |
| Capability Resolver | VERIFIED | CapabilityPlanner, BuildContract | OMNI_DATABASE_URL: ok (deploy-worker migrations + queue probe PASS) | VERIFIED for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI (fresh: bld_f419acd1317a40afab5a7bd287841048@beb67b4) | — | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 [workspace@beb67b4] | $0 (deterministic) | keyword-based game detection misclassifies "משחק" (football match) |
| Solution Architect | STALE | ArchitectAgent, GENERATION_CONSTRAINTS | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | STALE — was verified for: the fixed stdlib stack is planned consistently at beb67b4; code changed since: omni_prod/autonomous_agents.py, omni_prod/dependency_policy.py | — | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 [workspace@beb67b4] | shared with request_interpreter | one fixed stack (Python stdlib + SQLite in /tmp); no durable data or API-contract design |
| Project Orchestrator | STALE | _run_live_build_job, AutonomousProductEngine, main | OMNI_REDIS_URL: ok (deploy-worker queue probe PASS); OMNI_DATABASE_URL: ok (deploy-worker migrations + queue probe PASS) | STALE — was verified for: the fixed build pipeline runs to ready at 3a4d822; code changed since: omni_prod/worker_tasks.py | — | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 [workspace@beb67b4]; STATUS.md "Golden E2E #1: full chain from the founder's workspace" (2026-10-08 23:05) [workspace@3a4d822] | $0 (deterministic) | fixed 4-step pipeline, not a task graph; no cancel; no resume of a half-finished build (janitor fails it) |
| Cost Controller | STALE | RoutedModelGateway, PostgresSubscriptionService, qa_used_usd | OMNI_DATABASE_URL: ok (deploy-worker migrations + queue probe PASS) | STALE — was verified for: QA budget cap enforced before a build is admitted at d8a01fa; code changed since: omni_prod/routed_gateway.py | — | build-evidence run 37864934013 — QA counted all-time $3.31 [worker-host@d8a01fa]; tests/test_provider_quota_and_dialects.py; tests/test_qa_budget.py — a start date needs free-tier evidence | $0 (deterministic) | no per-step cost shown to the user; no provider invoice reconciliation; spend ledger is tokens x catalog price, not a supplier-confirmed cost |
| Discovery Lead | CONNECTED | next_group, answer, PostgresBriefRepository | OMNI_DATABASE_URL: ok (deploy-worker migrations + queue probe PASS) | unit tests only | — | tests/test_discovery_and_approval.py — engine + live-Postgres revisions and approvals | $0 (deterministic) | not yet used by the founder in the workspace; a fixed question bank; no model phrasing; domains: web apps/business systems only |
| Customer Success & Handover Agent | DEFINED | — | — | not verified | — | — | — | not implemented |
| Product Economics Analyst | DEFINED | — | — | not verified | — | — | — | not implemented |

## software

| Agent | Status | Implementation | Configuration | Verification | Blocked | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|---|
| UX Designer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Frontend Developer | VERIFIED | GeneratorAgent | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | VERIFIED for: prompt -> ready build (library, business rules); HTTP acceptance: create/read/conflict/return/delete (fresh: bld_8263a2a1905346399747f4fe8b92e919@b0a0cfa) | — | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 [workspace@beb67b4]; mod_c14435dc9baa44bdac784d0c15ed9b85 -> v_0bc82ef7b33b4210 — natural-language change accepted 2026-10-08 22:55; spec A1-A6 [workspace@3a4d822]; bld_8263a2a1905346399747f4fe8b92e919 -> v_f65e904334b04776 — founder library build 2026-10-09 02:30; HTTP behaviour probes passed [workspace@b0a0cfa] | part of ~$0.07 per build | generated library hid every message after the first (found by the browser check, 2026-10-09); UI quality gaps found by the founder: alert() errors, ISO dates, hidden filter state |
| Backend Developer | VERIFIED | GeneratorAgent | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | VERIFIED for: prompt -> ready build (library, business rules); HTTP acceptance: create/read/conflict/return/delete (fresh: bld_8263a2a1905346399747f4fe8b92e919@b0a0cfa) | — | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 [workspace@beb67b4]; mod_c14435dc9baa44bdac784d0c15ed9b85 -> v_0bc82ef7b33b4210 — natural-language change accepted 2026-10-08 22:55; spec A1-A6 [workspace@3a4d822]; bld_8263a2a1905346399747f4fe8b92e919 -> v_f65e904334b04776 — founder library build 2026-10-09 02:30; HTTP behaviour probes passed [workspace@b0a0cfa] | shared with frontend_developer | input validation only when the user asks for it; data in /tmp (not durable) |
| Data Engineer | DEFINED ⚠ | — | — | not verified | — | — | — | not implemented |
| Identity & Access Engineer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Integration Engineer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Repository Maintainer | VERIFIED | PostgresProjectWorkspace, S3ArtifactStore, restore_version_with_spec | OMNI_DATABASE_URL: ok (deploy-worker migrations + queue probe PASS); OMNI_S3_ENDPOINT/OMNI_S3_BUCKET/OMNI_S3_ACCESS_KEY/OMNI_S3_SECRET_KEY: ok (deploy-worker storage probe PASS) | VERIFIED for: change classified and applied; tests passed on the new version; version promoted on accept; export ZIP of a promoted version (fresh: mod_c14435dc9baa44bdac784d0c15ed9b85@3a4d822, ZIP@3a4d822) | — | mod_c14435dc9baa44bdac784d0c15ed9b85 -> v_0bc82ef7b33b4210 — natural-language change accepted 2026-10-08 22:55; spec A1-A6 [workspace@3a4d822]; ZIP of v_0bc82ef7b33b4210 opened by the founder 2026-10-08 22:59 [workspace@3a4d822] | $0 | — |
| Brand & Design Director | DEFINED | — | — | not verified | — | — | — | not implemented |

## quality

| Agent | Status | Implementation | Configuration | Verification | Blocked | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|---|
| QA Verifier | VERIFIED | RemoteSandboxRepositoryExecutor, PreviewReadyExecutor, QualityAwareExecutor, ProductReviewExecutor, BrowserFlowExecutor, WebSaaSAcceptanceRunner | OMNI_SANDBOX_RUNNER_URL/OMNI_SANDBOX_SHARED_SECRET: ok (deploy-worker sandbox probe PASS (every deploy)); GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | VERIFIED for: real browser: working fixture passes, vanishing-message fixture caught (fresh: deploy-worker@d8a01fa) | — | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 [workspace@beb67b4]; golden-rehearsal run 37820429767 — task-list prompt: ready, quality 86, 2 min [worker-host@782dafd]; bld_8263a2a1905346399747f4fe8b92e919 -> v_f65e904334b04776 — founder library build 2026-10-09 02:30; HTTP behaviour probes passed [workspace@b0a0cfa]; golden-rehearsal run 37841459920 — skills on: QA review round 1 by gemini-3.8-flash, 0 blocking; ready, quality 86 [worker-host@dbd1232]; deploy-worker run 37864475043 — browser-probe PASS both ways on the host [worker-host@d8a01fa] | one review call per round (~$0.01); browser check $0 | same model vendor writes and reviews (allowed by directive §17; separate run); browser check not yet exercised inside a founder build; no screenshots or visual inspection yet |
| Security Reviewer | STALE | hostile_repository_scan, evaluate_release_gates | none needed | STALE — was verified for: static hostile-pattern scan gates release at beb67b4; code changed since: omni_prod/worker_tasks.py | — | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 [workspace@beb67b4] | $0 | static scan only; no authorization testing of the generated app |
| Repair Agent | STALE | RepairAgent | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok); OMNI_SANDBOX_RUNNER_URL/OMNI_SANDBOX_SHARED_SECRET: ok (deploy-worker sandbox probe PASS (every deploy)) | STALE — was verified for: failing sandbox tests repaired within the round limit at ff6b4f6; code changed since: omni_prod/autonomous_agents.py | — | bld_f419acd1317a40afab5a7bd287841048 -> v_246bae81234e4c39 — founder build from the workspace, 2026-10-08 21:30-21:35, quality 84 [workspace@beb67b4]; golden-rehearsal run 37814985551 — 5 repair rounds converged [worker-host@ff6b4f6] | part of ~$0.07 per build | repairs the whole repository rather than a minimal patch |
| Preview Operator | STALE | DockerPreviewProvider, make_handler, PostgresPreviewRepository | PREVIEW_DOMAIN_TEMPLATE/OMNI_PREVIEW_HOST_SUFFIX: ok (deploy-worker "Preview edge is up" PASS) | STALE — was verified for: preview container started and routed over HTTPS at beb67b4; code changed since: omni_prod/preview_repository.py, omni_prod/preview_runtime.py | — | https://prv-1760dedc67864c0186aa0cdf945bab0d.151-145-89-132.sslip.io — v_246bae81234e4c39 shown in the workspace [workspace@beb67b4]; tests/test_golden_mod_path_live_postgres.py::test_preview_acceptance_report_is_recorded_on_real_postgres — acceptance recording fixed 2026-10-09 (library preview was torn down) | $0 (worker host) | data in /tmp is lost when the preview stops; temporary sslip.io address, open to anyone with the link; acceptance recording fix not yet seen on a founder preview |
| Release Agent | DEFINED | — | — | not verified | — | — | — | not implemented |
| Operations Agent | VERIFIED | run_once | OMNI_DATABASE_URL: ok (deploy-worker migrations + queue probe PASS) | VERIFIED for: janitor process running (fresh: deploy-worker@d8a01fa) | — | tests/test_maintenance_live_postgres.py; deploy-worker "janitor started" [worker-host@d8a01fa] | $0 | no alerting; no health monitoring of generated products |
| Requirements Traceability Auditor | DEFINED | — | — | not verified | — | — | — | not implemented |
| Accessibility & Localization Reviewer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Privacy & IP Steward | DEFINED | — | — | not verified | — | — | — | not implemented |
| Partner Readiness Reviewer | DEFINED | — | — | not verified | — | — | — | not implemented |

## assets

| Agent | Status | Implementation | Configuration | Verification | Blocked | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|---|
| Asset Planner | DEFINED | — | — | not verified | — | — | — | not implemented |
| Visual Creator | CONNECTED | PredictionImageProvider | REPLICATE_API_TOKEN: ok (Replicate authentication live-verified on Preview (STATUS 2026-10-06)) | unit tests only | — | tests/test_replicate_image_test.py | about $0.003 per image (FLUX Schnell list price) | no image has been generated live yet; not on the build path |
| Consistency Director | DEFINED | — | — | not verified | — | — | — | not implemented |
| Asset QA | DEFINED | — | — | not verified | — | — | — | not implemented |
| Asset Librarian | DEFINED | — | — | not verified | — | — | — | not implemented |

## media

| Agent | Status | Implementation | Configuration | Verification | Blocked | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|---|
| Media Producer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Scriptwriter | DEFINED | — | — | not verified | — | — | — | not implemented |
| Storyboard Director | DEFINED | — | — | not verified | — | — | — | not implemented |
| Video Creator | DEFINED | — | — | not verified | — | — | — | not implemented |
| Voice & Audio Producer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Timeline Editor | DEFINED | — | — | not verified | — | — | — | not implemented |
| Media QA | DEFINED | — | — | not verified | — | — | — | not implemented |
| Publishing Operator | DEFINED | — | — | not verified | — | — | — | not implemented |

## games

| Agent | Status | Implementation | Configuration | Verification | Blocked | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|---|
| Game Designer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Game Architect | DEFINED | — | — | not verified | — | — | — | not implemented |
| Gameplay Developer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Level Designer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Game Asset Coordinator | DEFINED | — | — | not verified | — | — | — | not implemented |
| Save & Progression Engineer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Playtest Agent | DEFINED | — | — | not verified | — | — | — | not implemented |
| Multiplayer Engineer | DEFINED | — | — | not verified | — | — | — | not implemented |

## automation

| Agent | Status | Implementation | Configuration | Verification | Blocked | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|---|
| Automation Designer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Connector Operator | DEFINED | — | — | not verified | — | — | — | not implemented |
| Scheduler Operator | DEFINED | — | — | not verified | — | — | — | not implemented |
| Automation QA | DEFINED | — | — | not verified | — | — | — | not implemented |
| Agent App Builder | DEFINED | — | — | not verified | — | — | — | not implemented |

## platform

| Agent | Status | Implementation | Configuration | Verification | Blocked | Evidence | Cost | Remaining gap |
|---|---|---|---|---|---|---|---|---|
| Skill Builder | DEFINED | — | — | not verified | — | — | — | not implemented |
| Skill Evaluator | DEFINED | — | — | not verified | — | — | — | not implemented |
| Registry Auditor | CONNECTED | audit | none needed | unit tests only | — | tests/test_registry_audit.py | $0 | — |
| Provider Evaluator | STALE | probe, cost_projection | GEMINI_API_KEY/OMNI_MODEL_CATALOG_JSON: ok (deploy-worker run 37739774562 notice "model catalog": gemini-* CONFIGURED; model-probe 37814803770 ok) | STALE — was verified for: model availability probe at ff6b4f6; code changed since: omni_prod/rehearsal.py | — | model-probe run 37814803770 — 3 Gemini models ok; OpenAI/Anthropic refused: no credit [worker-host@ff6b4f6] | < $0.001 per probe | no quality benchmark across providers yet |
| Integration & Secret Steward | DEFINED | — | — | not verified | — | — | — | not implemented |
| Reliability & Recovery Engineer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Performance & Resource Engineer | DEFINED | — | — | not verified | — | — | — | not implemented |
| Release & Change Coordinator | STALE | .github/workflows/deploy-worker.yml, PostgresBuildRepository.claim_contract_build | none needed | STALE — was verified for: no worker replacement mid-job at d8a01fa; code changed since: .github/workflows/deploy-worker.yml, omni_prod/job_repository.py | — | deploy-worker run 37862903906 — drained 213 s for a running job, exit 0 [worker-host@51bb631]; deploy-worker run 37864475043 + build bld_e204320872c8 — founder build finished ready while the deploy drained 65 s [worker-host@d8a01fa]; tests/test_golden_mod_path_live_postgres.py::test_two_parallel_approvals_of_one_plan_create_one_build | $0 | branch ownership is a written rule, not enforced by a tool; no rollback step in the workflow |

## Skills catalog (directive §9)

| Skill | Area | Kind | Status | Implementation | Depends on | Verification | Gap |
|---|---|---|---|---|---|---|---|
| intent.parse | discovery | EXECUTABLE | STALE | ProductArchitect | — | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI; prompt -> ready build (library, business rules); HTTP acceptance: create/read/conflict/return/delete at b0a0cfa; code changed since: omni_prod/product_architect.py | one pass, no conversation |
| domain.classify | discovery | EXECUTABLE | VERIFIED | CapabilityPlanner | intent.parse | VERIFIED for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI (fresh: bld_f419acd1317a40afab5a7bd287841048@beb67b4) | keyword based; "משחק" misread |
| requirements.extract | discovery | EXECUTABLE | STALE | ArchitectAgent | intent.parse | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI; change classified and applied; tests passed on the new version; version promoted on accept at 3a4d822; code changed since: omni_prod/autonomous_agents.py | — |
| questions.select | discovery | EXECUTABLE | TESTED | next_group | requirements.extract | unit tests only | deterministic question bank (web/business systems); not yet used by a founder |
| answers.merge | discovery | EXECUTABLE | TESTED | answer | questions.select | unit tests only | — |
| ambiguity.resolve | discovery | WORKFLOW | TESTED | next_group, answer | questions.select, answers.merge | unit tests only | — |
| contradiction.detect | discovery | VALIDATOR | TESTED | contradictions | requirements.extract | unit tests only | one rule (no sign-in + personal data + outside users) |
| preferences.delegate | discovery | EXECUTABLE | TESTED | answer | questions.select | unit tests only | — |
| references.ingest | discovery | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| brief.summarize | discovery | EXECUTABLE | TESTED | summary | answers.merge | unit tests only | — |
| acceptance.define | discovery | EXECUTABLE | STALE | ArchitectAgent | requirements.extract | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI at beb67b4; code changed since: omni_prod/autonomous_agents.py | — |
| brief.revise | approval | EXECUTABLE | TESTED | PostgresBriefRepository.save | brief.summarize | unit tests only | — |
| approval.bind | approval | EXECUTABLE | TESTED | PostgresBriefRepository.create_approval, PostgresBuildRepository.claim_contract_build | brief.revise | unit tests only | — |
| approval.validate | approval | VALIDATOR | VERIFIED | BuildContract.verify_fingerprint | approval.bind | VERIFIED for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI (fresh: bld_f419acd1317a40afab5a7bd287841048@beb67b4) | — |
| approval.invalidate | approval | EXECUTABLE | TESTED | PostgresBriefRepository.consume | approval.bind | unit tests only | — |
| scope.diff | approval | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| change.classify | approval | EXECUTABLE | STALE | ChangeClassifierAgent | — | STALE — was verified for: change classified and applied; tests passed on the new version; version promoted on accept at 3a4d822; code changed since: omni_prod/autonomous_agents.py | — |
| brand.profile | design | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| palette.propose | design | INSTRUCTION | IMPLEMENTED | VISUAL_DESIGN | — | none | model chooses; user not asked |
| typography.select | design | INSTRUCTION | IMPLEMENTED | VISUAL_DESIGN | — | none | model chooses; user not asked |
| design.tokens | design | VALIDATOR | IMPLEMENTED | VISUAL_DESIGN | palette.propose, typography.select | none | CSS heuristic only (not a design approval, §11) |
| screen.plan | design | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| states.define | design | INSTRUCTION | IMPLEMENTED | UI_STATES | — | none | — |
| responsive.verify | design | VALIDATOR | NOT_IMPLEMENTED | — | — | none | not implemented (static @media check only) |
| visual.compare | design | VALIDATOR | NOT_IMPLEMENTED | — | — | none | not implemented |
| accessibility.check | design | VALIDATOR | NOT_IMPLEMENTED | — | — | none | not implemented |
| locale.verify | design | INSTRUCTION | IMPLEMENTED | TEXT_LOCALE | — | none | — |
| capabilities.resolve | planning | EXECUTABLE | VERIFIED | CapabilityPlanner | requirements.extract | VERIFIED for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI (fresh: bld_f419acd1317a40afab5a7bd287841048@beb67b4) | — |
| dependencies.close | planning | VALIDATOR | TESTED | MasterSkillsRegistry.dependency_closure | capabilities.resolve | unit tests only | — |
| architecture.plan | planning | EXECUTABLE | STALE | ArchitectAgent | capabilities.resolve | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI at beb67b4; code changed since: omni_prod/autonomous_agents.py | one fixed stack |
| api.contract | planning | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| data.schema | planning | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| tasks.graph | planning | WORKFLOW | NOT_IMPLEMENTED | — | — | none | not implemented (fixed pipeline) |
| risk.classify | planning | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| repository.inspect | code | EXECUTABLE | VERIFIED | PostgresProjectWorkspace | — | VERIFIED for: change classified and applied; tests passed on the new version; version promoted on accept (fresh: mod_c14435dc9baa44bdac784d0c15ed9b85@3a4d822) | — |
| context.select | code | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented (whole repository is sent) |
| code.generate | code | EXECUTABLE | VERIFIED | GeneratorAgent | architecture.plan, approval.validate | VERIFIED for: prompt -> ready build (library, business rules); HTTP acceptance: create/read/conflict/return/delete (fresh: bld_8263a2a1905346399747f4fe8b92e919@b0a0cfa) | — |
| code.patch | code | EXECUTABLE | STALE | RepairAgent | tests.run | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI at beb67b4; code changed since: omni_prod/autonomous_agents.py | rewrites the repository, not a minimal patch |
| frontend.build | code | EXECUTABLE | STALE | GeneratorAgent | code.generate | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI at beb67b4; code changed since: omni_prod/autonomous_agents.py | — |
| backend.build | code | EXECUTABLE | STALE | GeneratorAgent | code.generate | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI at beb67b4; code changed since: omni_prod/autonomous_agents.py | — |
| dependencies.lock | code | VALIDATOR | STALE | DependencyGateExecutor | — | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI at beb67b4; code changed since: omni_prod/dependency_policy.py | allowlist gate (no install step) |
| diff.review | code | VALIDATOR | VERIFIED | ProductReviewExecutor | code.generate | VERIFIED for: model review of the code (fresh: golden-rehearsal@dbd1232) | reviews the whole code, not a diff |
| migration.create | data | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented (generated apps) |
| migration.verify | data | VALIDATOR | NOT_IMPLEMENTED | — | — | none | not implemented |
| data.constraints | data | INSTRUCTION | STALE | DATA_INTEGRITY | — | STALE — was verified for: prompt -> ready build (library, business rules); HTTP acceptance: create/read/conflict/return/delete at b0a0cfa; code changed since: omni_prod/skills_runtime.py | library build: duplicate member answered 409 |
| data.persistence.verify | data | VALIDATOR | TESTED | selftest, DockerPreviewProvider.ensure_data_dir | — | unit tests only | previews only (one directory per project on the preview host); no backup, no size quota, no schema migration of old data |
| data.backup | data | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| data.restore | data | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| tenant.isolation.verify | data | VALIDATOR | NOT_IMPLEMENTED | — | — | none | not implemented (generated apps) |
| auth.configure | identity | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented (generated apps) |
| authorization.verify | identity | VALIDATOR | NOT_IMPLEMENTED | — | — | none | not implemented |
| secrets.resolve | identity | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented (generated apps) |
| integration.configure | identity | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| integration.probe | identity | VALIDATOR | VERIFIED | probe | — | VERIFIED for: availability of each catalog model (fresh: model-probe@ff6b4f6) | model providers only |
| webhook.verify | identity | VALIDATOR | NOT_IMPLEMENTED | — | — | none | not implemented |
| connection.revoke | identity | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| binding.validate | identity | VALIDATOR | NOT_IMPLEMENTED | — | — | none | not implemented |
| sandbox.prepare | execution | EXECUTABLE | STALE | build_docker_command | — | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI at beb67b4; code changed since: omni_prod/sandbox.py | — |
| app.start | execution | VALIDATOR | VERIFIED | PreviewReadyExecutor | sandbox.prepare | VERIFIED for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI (fresh: bld_f419acd1317a40afab5a7bd287841048@beb67b4) | — |
| runtime.readiness | execution | VALIDATOR | STALE | DockerPreviewProvider | app.start | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI at beb67b4; code changed since: omni_prod/preview_runtime.py | — |
| task.checkpoint | execution | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| task.resume | execution | EXECUTABLE | NOT_IMPLEMENTED | — | task.checkpoint | none | not implemented |
| task.cancel | execution | EXECUTABLE | TESTED | BuildControl, PostgresBuildRepository.request_cancel | — | unit tests only | builds only (not modifications); stops at a step boundary, not inside a model call |
| operation.deduplicate | execution | EXECUTABLE | TESTED | PostgresBuildRepository.claim_contract_build | — | unit tests only | — |
| effects.compensate | execution | EXECUTABLE | IMPLEMENTED | run_once | — | none | janitor releases reservations of lost builds; nothing else |
| resources.cleanup | execution | EXECUTABLE | TESTED | sweep_stale_containers, run_once | — | unit tests only | — |
| tests.plan | quality | EXECUTABLE | STALE | ArchitectAgent | acceptance.define | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI at beb67b4; code changed since: omni_prod/autonomous_agents.py | — |
| tests.run | quality | VALIDATOR | STALE | RemoteSandboxRepositoryExecutor | sandbox.prepare | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI; prompt -> ready build (task list); quality gate >= 80 at 782dafd; code changed since: omni_prod/remote_sandbox.py | — |
| api.behavior.verify | quality | VALIDATOR | VERIFIED | WebSaaSAcceptanceRunner | runtime.readiness | VERIFIED for: prompt -> ready build (library, business rules); HTTP acceptance: create/read/conflict/return/delete (fresh: bld_8263a2a1905346399747f4fe8b92e919@b0a0cfa) | — |
| browser.flow.verify | quality | VALIDATOR | VERIFIED | BrowserFlowExecutor | app.start | VERIFIED for: working fixture passes; vanishing-message fixture caught (fresh: deploy-worker@d8a01fa) | not yet inside a founder build |
| visual.inspect | quality | VALIDATOR | NOT_IMPLEMENTED | — | browser.flow.verify | none | not implemented (no screenshots) |
| security.negative_test | quality | VALIDATOR | VERIFIED | hostile_repository_scan | — | VERIFIED for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI (fresh: bld_f419acd1317a40afab5a7bd287841048@beb67b4) | static scan only |
| failure.reproduce | quality | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| repair.patch | quality | EXECUTABLE | STALE | RepairAgent | tests.run | STALE — was verified for: failing tests repaired at ff6b4f6; code changed since: omni_prod/autonomous_agents.py | — |
| regression.verify | quality | VALIDATOR | STALE | RemoteSandboxRepositoryExecutor | tests.run | STALE — was verified for: change classified and applied; tests passed on the new version; version promoted on accept at 3a4d822; code changed since: omni_prod/remote_sandbox.py | reruns the version's own tests |
| artifact.commit | delivery | EXECUTABLE | VERIFIED | PostgresProjectWorkspace | — | VERIFIED for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI (fresh: bld_f419acd1317a40afab5a7bd287841048@beb67b4) | — |
| version.restore | delivery | EXECUTABLE | TESTED | restore_version_with_spec | — | unit tests only | — |
| preview.verify | delivery | VALIDATOR | STALE | PostgresPreviewRepository | runtime.readiness, api.behavior.verify | STALE — was verified for: prompt -> ready build (library, business rules); HTTP acceptance: create/read/conflict/return/delete at b0a0cfa; code changed since: omni_prod/preview_repository.py | acceptance recording fixed 2026-10-09 |
| project.export | delivery | EXECUTABLE | VERIFIED | S3ArtifactStore | artifact.commit | VERIFIED for: export ZIP of a promoted version (fresh: ZIP@3a4d822) | — |
| release.prepare | delivery | WORKFLOW | NOT_IMPLEMENTED | — | — | none | not implemented |
| deployment.publish | delivery | EXECUTABLE | NOT_IMPLEMENTED | — | release.prepare | none | not implemented (promote is in memory only) |
| deployment.verify | delivery | VALIDATOR | NOT_IMPLEMENTED | — | deployment.publish | none | not implemented |
| deployment.rollback | delivery | EXECUTABLE | NOT_IMPLEMENTED | — | deployment.publish | none | not implemented |
| handover.generate | delivery | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| cost.quote | cost | EXECUTABLE | STALE | omni_prod/investor_app.py, build_economics_quote | — | STALE — was verified for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI at beb67b4; code changed since: omni_prod/investor_app.py | — |
| budget.reserve | cost | EXECUTABLE | VERIFIED | PostgresSubscriptionService, authorize_qa_build | cost.quote | VERIFIED for: recorded spend counted once per build (fresh: build-evidence@d8a01fa) | — |
| usage.record | cost | EXECUTABLE | STALE | RoutedModelGateway | — | STALE — was verified for: recorded spend counted once per build at d8a01fa; code changed since: omni_prod/routed_gateway.py | tokens x catalog price, not supplier-confirmed |
| cost.estimate | cost | EXECUTABLE | IMPLEMENTED | cost_projection | — | none | — |
| cost.reconcile | cost | VALIDATOR | NOT_IMPLEMENTED | — | usage.record | none | not implemented (no supplier invoice) |
| budget.settle | cost | EXECUTABLE | VERIFIED | PostgresSubscriptionService | budget.reserve | VERIFIED for: prompt -> build contract (task list); model-generated code; sandbox tests passed; version committed to R2; preview served a real UI (fresh: bld_f419acd1317a40afab5a7bd287841048@beb67b4) | — |
| margin.calculate | cost | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| budget.guard | cost | VALIDATOR | STALE | RoutedModelGateway, authorize_qa_build | budget.reserve | STALE — was verified for: recorded spend counted once per build at d8a01fa; code changed since: omni_prod/routed_gateway.py | — |
| assets.plan | assets | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| image.generate | assets | EXECUTABLE | TESTED | PredictionImageProvider | — | unit tests only | no image generated live; not on the build path |
| image.edit | assets | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| image.cutout | assets | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| asset.inspect | assets | VALIDATOR | NOT_IMPLEMENTED | — | — | none | not implemented |
| consistency.verify | assets | VALIDATOR | NOT_IMPLEMENTED | — | — | none | not implemented |
| asset.store | assets | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| provenance.record | assets | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented (provenance.json is written for code builds only) |
| script.write | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| storyboard.create | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| shots.plan | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| video.generate | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| voice.generate | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| speech.transcribe | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| music.generate | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| captions.align | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| timeline.compose | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| media.render | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| media.verify | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| media.export | media | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| game.rules | games | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| engine.select | games | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| scene.build | games | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| controls.bind | games | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| physics.configure | games | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| levels.generate | games | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| save.load | games | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| game.playtest | games | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| multiplayer.sync | games | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| game.performance | games | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| trigger.configure | automation | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| workflow.execute | automation | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| schedule.configure | automation | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| connector.invoke | automation | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| automation.replay | automation | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| agent.configure | automation | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| memory.configure | automation | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| agent.evaluate | automation | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| skill.propose | extension | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| skill.implement | extension | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| skill.evaluate | extension | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| verification.refresh | extension | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| readiness.audit | extension | EXECUTABLE | NOT_IMPLEMENTED | — | — | none | not implemented |
| registry.audit | extension | VALIDATOR | TESTED | audit | — | unit tests only | — |
| provider.benchmark | extension | VALIDATOR | VERIFIED | probe | — | VERIFIED for: availability of each catalog model (fresh: model-probe@ff6b4f6) | availability only, no quality benchmark |

## Runtime prompt skills (web)

| Skill | Kind | Status | Wiring | Verification | Evidence | Remaining gap |
|---|---|---|---|---|---|---|
| skill.request_fidelity@1 | INSTRUCTION | STALE | injected into: architect, generator, evolution, reviewer | STALE — was verified for: guidance injected; model review found no blocking issue at dbd1232; code changed since: omni_prod/skills_runtime.py | golden-rehearsal run 37841459920 — skills_applied recorded in the build; QA review against their checklists, 0 blocking | the plan view still lists "login and sessions" from ProductArchitect for a "no login" request |
| skill.form_validation@1 | INSTRUCTION + VALIDATOR | STALE | injected into: generator, repair, evolution, reviewer | STALE — was verified for: guidance injected; model review found no blocking issue at dbd1232; code changed since: omni_prod/skills_runtime.py | golden-rehearsal run 37841459920 — skills_applied recorded in the build; QA review against their checklists, 0 blocking | no HTTP probe sends invalid input to the running app yet |
| skill.ui_states@1 | INSTRUCTION | STALE | injected into: generator, repair, evolution, reviewer | STALE — was verified for: guidance injected; model review found no blocking issue at dbd1232; code changed since: omni_prod/skills_runtime.py | golden-rehearsal run 37841459920 — skills_applied recorded in the build; QA review against their checklists, 0 blocking | checked by code review and the browser flow check; no screenshots |
| skill.text_locale@1 | INSTRUCTION + VALIDATOR | STALE | injected into: generator, repair, evolution, reviewer | STALE — was verified for: guidance injected; model review found no blocking issue at dbd1232; code changed since: omni_prod/skills_runtime.py | golden-rehearsal run 37841459920 — skills_applied recorded in the build; QA review against their checklists, 0 blocking | — |
| skill.data_integrity@1 | INSTRUCTION | STALE | injected into: architect, generator, repair, evolution, reviewer | STALE — was verified for: guidance injected; model review found no blocking issue at dbd1232; code changed since: omni_prod/skills_runtime.py | golden-rehearsal run 37841459920 — skills_applied recorded in the build; QA review against their checklists, 0 blocking | no conflict/404 probe against the running app yet |
| skill.visual_design@1 | INSTRUCTION + VALIDATOR | STALE | injected into: generator, repair, evolution, reviewer | STALE — was verified for: CSS heuristic passed; model review 0 blocking at 727af63; code changed since: omni_prod/skills_runtime.py | golden-rehearsal run 37858017258 — library prompt: ready, quality 86, design static check passed, review 0 blocking | checked by a CSS heuristic and code review, not by looking at a screenshot (directive §11: not a design approval); not yet seen by the founder in a preview |

## Mismatches found

- Data Engineer: older registry says PARTIAL but no code on a runtime path serves this role
- every older-registry skill's "last_verified" is the 2026-10-04 metadata check, not a capability run

