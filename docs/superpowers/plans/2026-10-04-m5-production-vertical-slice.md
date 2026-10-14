# 148AI M5 Production Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove one complete, durable, commercially credible Web/SaaS customer journey from account creation through real AI generation, real assets/infrastructure, verified preview, natural-language modification, real Vercel publishing, durable billing/cost settlement, rollback, observability, and restore evidence.

**Architecture:** Extend the verified M4.95 provider-neutral capability layer rather than creating parallel paths. Keep V28 durable async builds as the only public arbitrary-generation path, add versioned Build Contracts and a provider-neutral Web/SaaS Infrastructure Profile, and promote immutable verified releases through a real deployment adapter. Every external side effect is idempotent, tenant-scoped, secret-safe, and represented durably before the product can claim readiness.

**Tech Stack:** Python 3, FastAPI, PostgreSQL 16, Redis/RQ, S3-compatible object storage, existing M4.95 capability/provider layer, Vercel REST API adapter, Stripe API/webhooks, Postgres-compatible generated-app runtime bindings, S3-compatible generated-app storage, optional Resend/webhook outbound adapter, unittest/pytest-compatible suite.

**Spec:** `docs/superpowers/specs/2026-10-04-m5-production-vertical-slice-design.md`

## Global Constraints

- Preserve `REAL EXECUTION OR EXPLICIT FAILURE`.
- No public production path may silently use legacy deterministic/demo generation as arbitrary AI generation.
- No paid provider call before a durable conservative maximum reservation.
- Provider-reported actual usage/cost is recorded when available; unknown actual cost remains unknown.
- External paid tasks must be idempotent and resumable after worker/process failure.
- No plaintext secret values in DB rows, logs, build artifacts, exports, manifests, or API responses.
- Required capabilities that are unavailable or unconfigured block `READY`.
- Preview success is not production-publish success.
- Build success is not functional acceptance.
- Every published release points to immutable source/version/build/artifact/evidence records.
- Cross-tenant access is denied at every public resource boundary.
- Production publishing must support rollback to the previous verified release.
- External credentials, domains, Stripe live mode, and provider commercial approvals remain explicit `NOT_CONFIGURED/BLOCKED` gates when absent.
- Canonical creator identity store for M5 production is `creator_accounts` via `PostgresAccountService`; `AccountService` remains reviewer/test-only.
- First supported generated-app infrastructure profile is `managed_web_saas_v1`: Postgres-compatible relational DB + app-scoped durable auth/session tables + S3-compatible object storage + scheduled HTTP work + outbound webhook/email adapter. Provider brands remain outside canonical capability keys.
- `POST /api/v28/projects/{project_id}/builds` remains the canonical public arbitrary-generation entrypoint; the legacy singular `/build` path remains disabled in durable mode and must never be reintroduced as a fallback.
- Vercel is the first Web/SaaS production deployment adapter, but deployment contracts remain provider-neutral.
- Stripe is the first 148AI subscription processor; card data is never stored by 148AI.

## Review Focus

1. **Crash after irreversible external submit** — provider/deployment/billing retries must resume from stored external identity and never duplicate a paid/business effect. Covered by Tasks 8, 12, 13, 18.
2. **Cross-tenant guessed identifiers/object keys** — every project/build/version/artifact/preview/deployment/billing/evidence endpoint denies horizontal access. Covered by Tasks 3, 11, 15, 18.
3. **Unknown provider actual cost** — no estimate may be relabeled as actual; settlement basis remains explicit and margin state is truthful. Covered by Tasks 9 and 14.
4. **Preview/build succeeds but application behavior is broken** — release promotion requires target-specific functional acceptance, not compile/health alone. Covered by Tasks 10, 17, 18.
5. **External provider configured incorrectly or unavailable** — readiness must report `NOT_CONFIGURED/BLOCKED`, never fabricate successful deployment/media/auth. Covered by Tasks 7, 12, 13, 19.

---

### Task 1: Freeze M5 Baseline and Canonical Production Modes

**Files:**
- Create: `M5_VALIDATION.md`
- Create: `tests/test_m5_public_path_truth.py`
- Modify: `STATUS.md`
- Modify: `omni_prod/investor_app.py`

**Interfaces:**
- Consumes: M4.95 truth/status vocabulary and `_require_durable_backend()`.
- Produces: an executable invariant that durable V28 mode uses only `/builds` for arbitrary generation and reports reviewer/demo paths as non-production.

- [ ] **Step 1: Write failing tests** asserting durable mode rejects the singular synchronous arbitrary-generation route, memory persistence cannot claim M5 staging readiness, and M5 status starts as `M5_PARTIAL`.
- [ ] **Step 2: Run** `python -m unittest tests.test_m5_public_path_truth -v` and confirm RED on missing M5 truth guard.
- [ ] **Step 3: Implement** `m5_public_generation_mode() -> dict` in `omni_prod/investor_app.py` (or a focused helper module if investor_app would grow further) and write baseline evidence in `M5_VALIDATION.md`.
- [ ] **Step 4: Run targeted test and full suite**; expected targeted PASS and no M4.95 regression.
- [ ] **Step 5: Commit** `test(m5): freeze production path baseline`.

### Task 2: Canonical Creator Identity and Durable Session Lifecycle

**Files:**
- Create: `infra/postgres/018_identity_lifecycle.sql`
- Create: `omni_prod/identity_lifecycle.py`
- Create: `tests/test_m5_identity_lifecycle.py`
- Modify: `omni_prod/creator_accounts.py`
- Modify: `omni_prod/investor_app.py`

**Interfaces:**
- Consumes: `PostgresAccountService`, `issue_token`, `verify_token`.
- Produces: `IdentityService.register/login/logout/revoke_session/verify_email/request_password_reset/reset_password/list_sessions/request_account_deletion/request_data_export/record_consent`.

- [ ] **Step 1: Write failing tests** for email verification state, one-time reset token hashing/expiry, durable session revocation across service instances, consent version storage, deletion/export request state, and no token plaintext in DB/API.
- [ ] **Step 2: Run targeted tests** and verify RED because durable identity lifecycle tables/service do not exist.
- [ ] **Step 3: Add migration 018 and implement** immutable session IDs, hashed verification/reset tokens, account status, consent records, deletion/export request records; preserve existing account IDs/emails/password hashes.
- [ ] **Step 4: Wire routes** under `/api/v28/auth/*` without changing existing register/login response compatibility; revoked sessions must fail `me` and project access.
- [ ] **Step 5: Run targeted + `tests/integration/test_v28_creator_persistence.py` (when gated) + full suite; commit** `feat(m5): add durable identity lifecycle`.

### Task 3: Project Lifecycle Hardening

**Files:**
- Create: `infra/postgres/019_project_lifecycle.sql`
- Create: `omni_prod/project_lifecycle.py`
- Create: `tests/test_m5_project_lifecycle.py`
- Modify: `omni_prod/creator_accounts.py`
- Modify: `omni_prod/investor_app.py`

**Interfaces:**
- Consumes: canonical creator project IDs and tenant ownership checks.
- Produces: `rename_project`, `search_projects`, `archive_project`, `unarchive_project`, `delete_project`, `project_state` with tombstone/retention semantics.

- [ ] **Step 1: Write failing tests** for rename/search/archive/unarchive/delete/tombstone, idempotent delete, owner scoping, archived project exclusion by default, and project ID reuse prohibition.
- [ ] **Step 2: Verify RED** on absent lifecycle operations.
- [ ] **Step 3: Add migration 019 and service methods** using soft-delete/tombstone metadata; no hard delete of versions/build/evidence in the request transaction.
- [ ] **Step 4: Add tenant-scoped V28 routes** and negative cross-tenant tests for every operation.
- [ ] **Step 5: Run targeted + full suite; commit** `feat(m5): harden project lifecycle`.

### Task 4: Versioned Build Contract and Product Architect

**Files:**
- Create: `infra/postgres/020_m5_build_contracts.sql`
- Create: `omni_prod/build_contract.py`
- Create: `omni_prod/build_contract_repository.py`
- Create: `omni_prod/product_architect.py`
- Create: `tests/test_m5_product_architect.py`
- Modify: `omni_prod/autonomous_agents.py`
- Modify: `omni_prod/universal_brain.py`

**Interfaces:**
- Consumes: `ProductSpec`, `CapabilityPlan`, Master Skills/Agents registries, M4.95 dependency closure.
- Produces: `BuildContract`, `ClarificationQuestion`, `InfrastructureRequirement`, `ProductArchitect.compile(prompt, ...) -> BuildContract`, durable `BuildContractRepository`.

- [ ] **Step 1: Write failing tests** for high-confidence inference, low-confidence material clarification, required user roles/data/infrastructure/acceptance/cost fields, capability closure, and immutable contract revisions.
- [ ] **Step 2: Verify RED** before new contract classes exist.
- [ ] **Step 3: Implement** Build Contract schema with explicit `contract_version`, `status`, `unresolved_questions`, `capability_plan_fingerprint`, `acceptance`, `infrastructure`, `security`, and cost envelope references.
- [ ] **Step 4: Integrate ArchitectAgent output** without letting model output remove deterministic minimum capability requirements; persist each revision in migration 020 tables.
- [ ] **Step 5: Run targeted + full suite; commit** `feat(m5): add versioned product build contracts`.

### Task 5: Bind Durable Build Requests to Build Contracts

**Files:**
- Create: `tests/test_m5_build_contract_binding.py`
- Modify: `infra/postgres/020_m5_build_contracts.sql`
- Modify: `omni_prod/job_repository.py`
- Modify: `omni_prod/investor_app.py`
- Modify: `omni_prod/worker_tasks.py`

**Interfaces:**
- Consumes: `BuildContractRepository`, canonical `/builds` endpoint.
- Produces: every `build_request` references one immutable `build_contract_id`; worker loads exactly that contract revision.

- [ ] **Step 1: Write failing tests** proving prompt changes after enqueue cannot alter the worker contract, unresolved material questions block reservation/enqueue, and cross-project contract IDs are rejected.
- [ ] **Step 2: Verify RED** on missing build-contract foreign reference.
- [ ] **Step 3: Extend schema/repository** to persist `build_contract_id` and load it in worker; do not reconstruct architecture from mutable API state.
- [ ] **Step 4: Ensure build evidence records contract ID/fingerprint** and legacy rows remain readable with explicit legacy status.
- [ ] **Step 5: Run targeted + full suite; commit** `feat(m5): bind builds to immutable contracts`.

### Task 6: Generated-App Infrastructure Provisioner Contract

**Files:**
- Create: `omni_prod/infrastructure_contracts.py`
- Create: `omni_prod/infrastructure_registry.py`
- Create: `omni_prod/infrastructure_provisioner.py`
- Create: `tests/test_m5_infrastructure_contracts.py`
- Modify: `omni_prod/capability_registry.py`
- Modify: `omni_prod/capability_planner.py`

**Interfaces:**
- Produces: `InfrastructureKind`, `InfrastructureBinding`, `InfrastructureProfile`, `InfrastructureProvisioner.quote/provision/status/revoke`, profile key `managed_web_saas_v1`.
- First profile requires Postgres-compatible DB, app auth/session binding, S3-compatible storage, scheduled HTTP work, outbound webhook/email.

- [ ] **Step 1: Write failing tests** for complete profile dependency closure, resource ownership, environment separation, secret-reference-only outputs, idempotent provisioning, and explicit `NOT_CONFIGURED` when credentials are absent.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement provider-neutral contracts/registry**; add capability keys for DB/auth/storage/scheduled-work/outbound where not already represented.
- [ ] **Step 4: Integrate profile requirements into Capability Planner/Build Contract**; no product can be `READY` with missing required infrastructure binding.
- [ ] **Step 5: Run targeted + full suite; commit** `feat(m5): add generated app infrastructure contracts`.

### Task 7: First Managed Web/SaaS Infrastructure Profile

**Files:**
- Create: `infra/postgres/021_generated_app_bindings.sql`
- Create: `omni_prod/providers/managed_web_saas.py`
- Create: `tests/test_m5_managed_web_saas_profile.py`
- Create: `tests/integration/test_m5_managed_web_saas_live.py`
- Modify: `omni_prod/secrets_manager.py`

**Interfaces:**
- Consumes: Task 6 provisioner contracts.
- Produces: durable `generated_app_bindings` and one concrete adapter using configured Postgres-compatible DSN + S3-compatible store + app-scoped signing secret + scheduled HTTP/outbound binding.

- [ ] **Step 1: Write failing unit tests** for deterministic resource names, idempotency key, app-scoped secret references, preview/prod separation, revoke state, and zero secret leakage.
- [ ] **Step 2: Write gated integration test** requiring named M5 staging env vars; without them test must SKIP with a precise reason, never fake LIVE.
- [ ] **Step 3: Implement migration 021 + adapter**. Generated app credentials are distinct from control-plane provider credentials and are only exposed to the deployment environment that owns them.
- [ ] **Step 4: Add readiness surface** showing each infrastructure kind as LIVE/NOT_CONFIGURED/BLOCKED with evidence.
- [ ] **Step 5: Run unit + gated integration + full suite; commit** `feat(m5): implement managed web saas infrastructure profile`.

### Task 8: Real LLM Provider Usage Adapter and Code Generation Evidence

**Files:**
- Create: `omni_prod/provider_usage.py`
- Create: `tests/test_m5_llm_usage_evidence.py`
- Create: `tests/integration/test_m5_live_llm_usage.py`
- Modify: `omni_prod/providers/llm_provider.py`
- Modify: `omni_prod/routed_gateway.py`
- Modify: `omni_prod/worker_tasks.py`

**Interfaces:**
- Produces: normalized `ProviderUsage` (`input_tokens`, `output_tokens`, `cached_tokens`, `provider_reported_cost_usd|None`, `request_id`) attached to M4.95 usage events.

- [ ] **Step 1: Write failing tests** ensuring provider usage cannot be synthesized from estimates, request IDs survive into build evidence, and missing usage stays `None`.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Extend LLM gateway/provider wrapper** to return normalized provider usage while preserving existing completion API compatibility.
- [ ] **Step 4: Wire worker evidence** to provider usage and price catalog units; enforce no deterministic generator fallback on live build failure.
- [ ] **Step 5: Run targeted + gated live provider + full suite; commit** `feat(m5): capture real llm usage evidence`.

### Task 9: Real Image Provider and Optional Media Adapter

**Files:**
- Create: `omni_prod/providers/image_provider.py`
- Create: `omni_prod/providers/optional_media_provider.py`
- Create: `tests/test_m5_media_provider_adapters.py`
- Create: `tests/integration/test_m5_live_media_provider.py`
- Modify: `omni_prod/provider_registry.py`
- Modify: `omni_prod/provider_pricing.py`

**Interfaces:**
- Consumes: M4.95 `CapabilityProvider`, credential binding, artifact verifier, price catalog.
- Produces: one configured image adapter and one optional audio/voice-or-3D adapter selected by environment/config, each with quote/submit/poll/collect/cancel and durable external identity where paid.

- [ ] **Step 1: Write failing contract tests** for quote units, commercial-use metadata, output format validation, idempotency, crash resume, 429/backoff, actual usage when exposed, and `NOT_CONFIGURED` when absent.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement adapters** behind generic capability keys; provider names/config live only in registry/config.
- [ ] **Step 4: Add gated live tests** that create a real artifact, verify checksum/format/provenance, and record cost evidence.
- [ ] **Step 5: Run targeted + full suite; commit** `feat(m5): add live media provider adapters`.

### Task 10: Pre-Execution Quote, Reservation, Actual Settlement and Margin Gate

**Files:**
- Create: `tests/test_m5_build_economics.py`
- Modify: `omni_prod/provider_pricing.py`
- Modify: `omni_prod/subscription_store.py`
- Modify: `omni_prod/investor_app.py`
- Modify: `omni_prod/worker_tasks.py`

**Interfaces:**
- Consumes: Build Contract capability/infrastructure plan, provider catalog, normalized provider usage.
- Produces: one durable build authorization covering conservative maximum provider + infrastructure variable spend and explicit settlement basis/margin evidence.

- [ ] **Step 1: Write failing tests** for multi-provider max aggregation, margin floor denial, retry cost, unknown actual cost remaining NULL, reservation shortfall handling, and concurrent builds sharing the same user budget.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement build-level quote aggregation** before paid submit; no network quote is required to authorize because versioned local catalog provides conservative maximums.
- [ ] **Step 4: Settle from actual usage where available** and explicit fallback basis where not; persist `gross_contribution_usd` only when inputs are known enough to compute truthfully.
- [ ] **Step 5: Run targeted concurrency + full suite; commit** `feat(m5): reconcile build economics end to end`.

### Task 11: Functional Web/SaaS Acceptance and Preview Evidence

**Files:**
- Create: `omni_prod/web_saas_acceptance.py`
- Create: `tests/test_m5_web_saas_acceptance.py`
- Modify: `omni_prod/preview_runtime.py`
- Modify: `omni_prod/preview_repository.py`
- Modify: `omni_prod/worker_tasks.py`

**Interfaces:**
- Produces: `WebSaaSAcceptanceRunner.verify(preview, contract, personas) -> AcceptanceReport` and durable acceptance evidence linked to build/version/preview.

- [ ] **Step 1: Write failing tests** for health-only false positives, login/role/data CRUD, one background/integration path, responsive/API smoke requirements, and preservation of logs on preview crash.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement target-specific acceptance runner** using generated contract acceptance IDs; do not hard-code one demo domain.
- [ ] **Step 4: Require acceptance PASS before release eligibility**; preview remains a separate state from publish readiness.
- [ ] **Step 5: Run targeted + live-preview gated tests + full suite; commit** `feat(m5): verify web saas behavior before release`.

### Task 12: Durable Production Deployment Contract and Vercel Adapter

**Files:**
- Create: `infra/postgres/022_production_deployments.sql`
- Create: `omni_prod/deployment_contracts.py`
- Create: `omni_prod/deployment_repository.py`
- Create: `omni_prod/providers/vercel_deployment.py`
- Create: `tests/test_m5_vercel_deployment.py`
- Create: `tests/integration/test_m5_vercel_live.py`
- Modify: `omni_prod/deployments.py`
- Modify: `omni_prod/investor_app.py`

**Interfaces:**
- Produces: `DeploymentProvider.quote/deploy/status/cancel/rollback`, durable deployment attempt identity/idempotency, immutable `ReleaseRecord`, active release CAS.

- [ ] **Step 1: Write failing tests** for no-active-before-health, duplicate submit/retry, stored provider deployment ID, immutable release checksum, failed health, rollback only to VERIFIED release, and cross-tenant denial.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Add migration 022 + generic contracts/repository** preserving legacy deployments table compatibility.
- [ ] **Step 4: Implement Vercel adapter** using secret references, idempotency key, environment injection of generated-app bindings, polling/health probe, and no secret echo.
- [ ] **Step 5: Add gated live deployment test + full suite; commit** `feat(m5): deploy verified releases through vercel`.

### Task 13: Durable Stripe Billing Lifecycle

**Files:**
- Create: `infra/postgres/023_stripe_billing_lifecycle.sql`
- Create: `omni_prod/billing_repository.py`
- Create: `tests/test_m5_stripe_billing.py`
- Create: `tests/integration/test_m5_stripe_live.py`
- Modify: `omni_prod/stripe_billing.py`
- Modify: `omni_prod/investor_app.py`

**Interfaces:**
- Produces: durable Stripe event ledger keyed by event ID; subscription/customer/payment/invoice state; duplicate-safe webhook business effects across process restart.

- [ ] **Step 1: Write failing tests** for verified signature, forged/stale signature denial, duplicate event across fresh processor instance, subscription create/update/delete, past_due, cancellation, top-up record, invoice/payment references, refund/chargeback state representation.
- [ ] **Step 2: Verify RED** proving in-memory `_seen` is insufficient.
- [ ] **Step 3: Add migration 023 + repository** with unique Stripe event ID and transactional apply-once semantics.
- [ ] **Step 4: Replace process-memory dedupe** in production wiring while preserving a memory test adapter; expose billing history/status routes tenant-scoped.
- [ ] **Step 5: Run targeted + gated Stripe test-mode integration + full suite; commit** `feat(m5): make stripe billing lifecycle durable`.

### Task 14: End-to-End Correlation and Durable Operational Events

**Files:**
- Create: `infra/postgres/024_operational_events.sql`
- Create: `omni_prod/correlation.py`
- Create: `omni_prod/operational_events.py`
- Create: `tests/test_m5_observability.py`
- Modify: `omni_prod/observability.py`
- Modify: `omni_prod/worker_tasks.py`
- Modify: `omni_prod/capability_executor.py`
- Modify: `omni_prod/providers/vercel_deployment.py`

**Interfaces:**
- Produces: correlation identity propagated API -> build -> provider -> artifact -> preview -> deployment -> billing/cost; durable event stream plus metrics export.

- [ ] **Step 1: Write failing tests** for correlation preservation across queue payload/restart, provider request ID linkage, deployment linkage, customer-safe error reference, and secret redaction.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Add migration 024 and event repository**; process-memory metrics remain supplemental only.
- [ ] **Step 4: Wire structured events** at state transitions without logging secret values/raw auth headers.
- [ ] **Step 5: Run targeted + full suite; commit** `feat(m5): add durable cross-system observability`.

### Task 15: Backup and Restore Proof Orchestration

**Files:**
- Create: `infra/postgres/025_restore_proofs.sql`
- Create: `omni_prod/restore_proof.py`
- Create: `tests/test_m5_restore_proof.py`
- Create: `tests/integration/test_m5_restore_live.py`
- Modify: `omni_prod/backup_manifest.py`

**Interfaces:**
- Produces: `RestoreProofRunner.run(source_snapshot, isolated_target) -> RestoreProof` with snapshot identity, checksums, started/finished timestamps, measured RPO/RTO, integrity outcome.

- [ ] **Step 1: Write failing tests** for immutable snapshot identity, isolated-target requirement, checksum mismatch failure, no production mutation, and truthful EXTERNAL_PROOF_NEEDED state.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Add migration 025 + runner** wrapping provider-specific backup/restore hooks behind generic interfaces.
- [ ] **Step 4: Add gated staging restore integration test**; local mode may only report not externally proven.
- [ ] **Step 5: Run targeted + full suite; commit** `feat(m5): record staging backup restore proof`.

### Task 16: Security, Secret and Tenant Boundary Regression Gate

**Files:**
- Create: `tests/test_m5_security_boundaries.py`
- Modify: focused production modules only when a RED test exposes a real gap.

**Interfaces:**
- Consumes: identity, project, artifacts, preview, deployment, integration binding, billing/evidence APIs.
- Produces: one negative-test suite that blocks release on horizontal access or secret leakage.

- [ ] **Step 1: Write failing/negative tests** for user A accessing user B project/build/version/artifact/preview/deployment/billing/evidence, guessed storage key, `..`/encoded traversal, generated-code control-plane-secret access, forged callbacks, stale lease mutation, unauthorized publish, unverified rollback.
- [ ] **Step 2: Run test suite and classify every RED** as missing guard vs incorrect test; use systematic debugging before fixes.
- [ ] **Step 3: Implement minimal root-cause fixes** with no broad refactor.
- [ ] **Step 4: Run security suite + `secret_scan` against exported/generated artifacts/log fixtures**.
- [ ] **Step 5: Run full suite; commit** `test(m5): enforce security and tenant boundaries`.

### Task 17: Golden SaaS Fixture and Functional Acceptance Corpus

**Files:**
- Create: `tests/fixtures/m5_golden_saas_request.json`
- Create: `tests/fixtures/m5_golden_saas_acceptance.json`
- Create: `tests/test_m5_golden_contract.py`
- Modify: no production file unless test discovers a missing generic capability.

**Interfaces:**
- Produces: a replaceable capability-based Golden product fixture with two roles, durable relational CRUD, object upload, scheduled/background operation, outbound webhook/email, generated image, responsive UI, API, health/error surface.

- [ ] **Step 1: Define fixture acceptance IDs** tied to generic capabilities, not product-specific code paths.
- [ ] **Step 2: Write tests** proving the fixture requires every M5 workstream and cannot pass if any required capability is silently dropped.
- [ ] **Step 3: Run and verify fixture compiles into Build Contract/Capability DAG/infrastructure plan**.
- [ ] **Step 4: Verify modification request has its own acceptance delta and immutable base version**.
- [ ] **Step 5: Commit** `test(m5): define golden web saas product contract`.

### Task 18: M5 Golden E2E and Failure-Recovery Matrix

**Files:**
- Create: `tests/test_m5_golden_e2e.py`
- Create: `tests/test_m5_failure_matrix.py`
- Create: `tests/integration/test_m5_staging_e2e.py`
- Modify: `M5_VALIDATION.md`

**Interfaces:**
- Consumes: Tasks 1-17.
- Produces: one local deterministic E2E using contract-compliant fake external services plus one gated staging E2E using real configured services.

- [ ] **Step 1: Write Golden local E2E** covering account -> Build Contract -> max quote/reserve -> real code path adapter -> image artifact -> infrastructure bindings -> sandbox build/repair -> behavioral acceptance -> preview -> modification -> verified version -> deployment adapter -> settlement/evidence -> rollback.
- [ ] **Step 2: Write failure matrix** for worker death after provider submit, duplicate queue delivery, 429/Retry-After, timeout, corrupt asset, unknown actual cost, spend ceiling, preview crash, unhealthy deployment, duplicate deployment callback, duplicate Stripe webhook after restart, cross-tenant access.
- [ ] **Step 3: Run local Golden/failure suites** and fix only root-cause failures.
- [ ] **Step 4: Add gated staging E2E** that requires real Postgres/Redis/S3 + configured LLM/image + Vercel + Stripe test mode. Missing services yield explicit SKIP/BLOCKED evidence, not PASS.
- [ ] **Step 5: Commit** `test(m5): prove golden vertical slice and recovery matrix`.

### Task 19: M5 Readiness Truth Surface and External Proof Gate

**Files:**
- Create: `omni_prod/m5_readiness.py`
- Create: `tests/test_m5_readiness.py`
- Modify: `omni_prod/investor_app.py`
- Modify: `STATUS.md`
- Modify: `M5_VALIDATION.md`

**Interfaces:**
- Produces: `m5_readiness_payload()` with workstream status/evidence and final allowed status among `M5_VERIFIED_STAGING_WEB_SAAS_VERTICAL_SLICE`, `M5_IMPLEMENTED_NOT_EXTERNALLY_VERIFIED`, `M5_PARTIAL`, `M5_BLOCKED_EXTERNAL`.

- [ ] **Step 1: Write failing tests** that prohibit VERIFIED_STAGING when any required live proof is missing/skipped or any required workstream is PARTIAL.
- [ ] **Step 2: Verify RED**.
- [ ] **Step 3: Implement readiness aggregator** from machine evidence, not handwritten booleans; expose `/api/v28/m5/readiness` with no secrets.
- [ ] **Step 4: Update STATUS/validation docs from generated evidence** and ensure M4.95 status is preserved historically.
- [ ] **Step 5: Run targeted + full suite; commit** `feat(m5): expose evidence backed staging readiness`.

### Task 20: Final Whole-Branch Verification and M5 Release Candidate

**Files:**
- Modify: `M5_VALIDATION.md`
- Modify: `STATUS.md`
- Create: `M5_EXPORT_MANIFEST.md`

**Interfaces:**
- Consumes: entire M5 branch.
- Produces: verified release evidence and export hashes without claiming external proofs that did not run.

- [ ] **Step 1: Run full test suite** `python -m unittest discover -s tests -v`; expected 0 failures. Record exact pass/skip counts and names of externally gated skips.
- [ ] **Step 2: Run clean-room/lifecycle/security/Truth-Lock/M5 Golden gates** separately and record commands + outcomes.
- [ ] **Step 3: Run whole-branch code review** against the M5 spec/plan; fix Critical/Important findings with RED->GREEN evidence, then rerun full suite.
- [ ] **Step 4: Compute commit/ZIP/bundle SHA-256** and generate `M5_EXPORT_MANIFEST.md`; do not push/merge without the explicit integration decision.
- [ ] **Step 5: Commit** `chore(m5): finalize verified vertical slice evidence` and classify status truthfully from Task 19.

---

## Dependency Order

`1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> {8,9} -> 10 -> 11 -> 12 -> 13 -> 14 -> 15 -> 16 -> 17 -> 18 -> 19 -> 20`

Tasks 8 and 9 may be implemented independently after infrastructure/provider contracts exist, but both must finish before build economics/Golden E2E.

## Explicit Architectural Rulings

- **Ruling: canonical creator account store = PostgreSQL `creator_accounts` / `PostgresAccountService`.** Memory account service is test/reviewer only. Cost if wrong: migration complexity; benefit: no parallel identity source of truth.
- **Ruling: first generated-app profile = provider-neutral `managed_web_saas_v1`, not Supabase/Firebase hard-coding.** Live backing services may be vendor-specific configuration, but generated product contracts stay Postgres/S3/auth/schedule/outbound abstractions. Cost if wrong: adapter work; benefit: avoids lock-in in generated code.
- **Ruling: Product Architect extends `ProductSpec`/CapabilityPlan rather than replacing them.** Build Contract binds deterministic minimums + model-enriched intent. Cost if wrong: extra translation layer; benefit: preserves verified M4.95 contracts.
- **Ruling: no provider network quote is required before reservation.** Conservative max comes from versioned local catalog; optional provider quote after reservation may refine but never weaken the authorized ceiling.
- **Ruling: Vercel deployment becomes active only after provider identity + health + functional smoke.** API acceptance alone never means published.
- **Ruling: durable Stripe event ID is the business-effect idempotency key.** In-memory `_seen` is reviewer-only after M5.
- **Ruling: M5 does not claim production-ready if live external proofs are skipped.** The highest local-only status is `M5_IMPLEMENTED_NOT_EXTERNALLY_VERIFIED` or `M5_BLOCKED_EXTERNAL` where engineering is complete and named credentials/accounts are the only blocker.

## Self-Review Result

- **Spec coverage:** Sections 1-12 map to Tasks 1-20. Identity, project lifecycle, Build Contract, infrastructure, providers, economics, behavioral acceptance, deployment/rollback, Stripe, observability, restore, security and Golden E2E all have explicit owners.
- **Step scan:** Every task has a RED test, implementation boundary, verification command expectation and commit gate. No task asks the implementer to invent an undefined adjacent interface.
- **Type consistency:** `BuildContract`, `InfrastructureBinding/Profile`, `ProviderUsage`, `AcceptanceReport`, `ReleaseRecord`, `RestoreProof` are introduced before downstream consumers.
- **Review Focus:** all five highest-risk conditions have named task-level tests.
- **Proportion:** plan is intentionally implementation-oriented but does not transcribe production bodies; signatures/behaviors and test outcomes are pinned, implementation details remain to TDD.
