# 148AI M4.95 Capability Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a universal capability registry, provider-neutral routing/execution contract, durable per-capability evidence/cost accounting, and truthful capability status without breaking the verified M4.9 async build/modification paths.

**Architecture:** Keep M4.9’s durable build, reservation, model routing, media planning, S3 storage and release gates. Add an additive capability layer between planning and external execution. Existing LLM/media gateways are wrapped, not replaced; specific commercial providers remain adapters behind the new contract.

**Tech Stack:** Python 3, FastAPI, PostgreSQL 16, Redis/RQ, S3-compatible object storage, existing M4.9 sandbox/build pipeline, unittest/pytest-compatible test suite.

**Spec:** `M4_95_CAPABILITY_FOUNDATION_SPEC.md`

## Global Constraints

- Preserve `REAL EXECUTION OR EXPLICIT FAILURE`.
- Preserve current M4.9 durable build and M4 modification contracts.
- No provider call before durable budget reservation.
- No secret values in DB/logs/artifacts/API payloads.
- `actual_cost_usd` is NULL when unknown; never replace unknown actual cost with an estimate.
- Unsupported/unconfigured required capabilities remain explicit and block READY.
- Provider brands never appear in canonical capability keys.
- All schema work is additive and idempotent.
- Status vocabulary: `LIVE`, `PARTIAL`, `NOT_CONFIGURED`, `NOT_IMPLEMENTED`, `BLOCKED`.

## Review Focus

1. **Concurrent paid builds:** two builds for the same account must not both spend the same remaining provider budget; integration test owns this.
2. **Retry/idempotency:** a retried worker/provider task must not duplicate external generation, provider usage rows, or settlement; provider execution/repository tests own this.
3. **Unsupported user intent:** a required 3D/video/multiplayer/integration capability must never be silently dropped; planner + worker tests own this.
4. **Misleading cost evidence:** estimated cost must never be reported as actual; provider usage tests own this.
5. **Artifact forgery/corruption:** bytes returned by a provider must not become VERIFIED without format/checksum validation; verification tests own this.

---

## File structure decision

### Create

- `omni_prod/capabilities.py` — immutable capability data contracts and status enum.
- `omni_prod/capability_registry.py` — canonical registry and plan validation.
- `omni_prod/capability_planner.py` — deterministic prompt/target/media -> capability DAG mapping.
- `omni_prod/provider_contracts.py` — quote/job/result/provider protocols.
- `omni_prod/provider_registry.py` — registered provider lookup by capability.
- `omni_prod/provider_router.py` — policy and deterministic provider selection.
- `omni_prod/capability_verification.py` — artifact structural validators.
- `omni_prod/capability_repository.py` — durable plan/state/usage persistence.
- `omni_prod/capability_executor.py` — quote/execute/store/verify flow.
- `omni_prod/providers/__init__.py`
- `omni_prod/providers/http_media_provider.py` — wrapper around current `HTTPMediaGateway`.
- `omni_prod/providers/llm_provider.py` — wrapper/bridge to current routed model gateway where appropriate.
- `infra/postgres/017_capability_foundation.sql`
- `tests/test_m495_capability_registry.py`
- `tests/test_m495_capability_planner.py`
- `tests/test_m495_provider_router.py`
- `tests/test_m495_provider_contracts.py`
- `tests/test_m495_capability_verification.py`
- `tests/test_m495_capability_economics.py`
- `tests/integration/test_m495_capability_persistence.py`
- `tests/integration/test_m495_provider_adapter.py`
- `CAPABILITY_MATRIX.md`
- `COST_MODEL.md` if absent.

### Modify

- `omni_prod/universal_brain.py` — add `CapabilityPlan` to `BrainDecision`.
- `omni_prod/media_pipeline.py` — compatibility mapping only; do not remove current AssetKind contract.
- `omni_prod/worker_tasks.py` — persist/execute capability plan in durable build flow after foundation is tested.
- `omni_prod/investor_app.py` — read-only capability/provider/build-capability endpoints.
- `omni_prod/integration_center.py` — expose provider readiness through new registry without secrets.
- `omni_prod/pricing.py` — no plan-price rewrite in M4.95; add helpers only if required for quote classification.
- `omni_prod/subscription_store.py` — preserve reserve/settle/release; only additive conservative-maximum integration if necessary.
- `PRODUCT_MISSION_AND_ACCEPTANCE.md`
- `STATUS.md`
- `.env.example` only for adapters actually implemented/configurable.

---

### Task 1: Freeze the M4.9 baseline and add M4.95 validation scaffold

**Files:**
- Create: `M4_95_VALIDATION.md`
- Modify: `STATUS.md`

**Interfaces:**
- Consumes: existing repository test commands and M4.9 status evidence.
- Produces: immutable baseline evidence used to distinguish M4.95 regressions.

- [ ] **Step 1: Re-run the current M4.9 non-live regression suite before code changes.**

Record exact command, pass/skip counts, Python version and timestamp in `M4_95_VALIDATION.md`.

- [ ] **Step 2: Run existing M4.9 clean-room/lifecycle checks that are supported in the environment.**

Record unavailable external credentials/toolchains as `NOT CONFIGURED`, not failure of unrelated tests.

- [ ] **Step 3: Commit baseline evidence.**

```bash
git add M4_95_VALIDATION.md STATUS.md
git commit -m "docs: freeze M4.9 baseline for M4.95"
```

---

### Task 2: Add canonical capability contracts and registry

**Files:**
- Create: `omni_prod/capabilities.py`
- Create: `omni_prod/capability_registry.py`
- Test: `tests/test_m495_capability_registry.py`

**Interfaces:**
- Produces: `CapabilityStatus`, `CapabilityDefinition`, `CapabilityRequirement`, `CapabilityPlan`, `CapabilityRegistry`.
- Consumed by: Tasks 3–12.

- [ ] **Step 1: Write failing registry tests.**

Tests must assert: unique keys; unknown key rejected; quantity > 0; dependency closure deterministic; cycle rejected; all taxonomy keys in spec exist.

- [ ] **Step 2: Run focused test and verify failure.**

```bash
python -m pytest tests/test_m495_capability_registry.py -q
```

Expected: FAIL because new modules do not exist.

- [ ] **Step 3: Implement data contracts and static canonical registry.**

Use exact names/signatures from the spec. Do not add dynamic plugin loading.

- [ ] **Step 4: Re-run focused test.**

Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add omni_prod/capabilities.py omni_prod/capability_registry.py tests/test_m495_capability_registry.py
git commit -m "feat: add universal capability registry"
```

---

### Task 3: Add deterministic capability planner and integrate Universal Brain

**Files:**
- Create: `omni_prod/capability_planner.py`
- Modify: `omni_prod/universal_brain.py`
- Test: `tests/test_m495_capability_planner.py`

**Interfaces:**
- Consumes: `UnifiedPlan`, `CreativePlan`, `CapabilityRegistry`.
- Produces: `CapabilityPlanner.plan(...) -> CapabilityPlan`; `BrainDecision.capabilities`.

- [ ] **Step 1: Write failing mapping tests.**

At minimum assert:
- 3D game -> `target.game.3d`, mesh, texture + software lifecycle;
- voice assistant -> TTS and, when requested, STT/realtime voice;
- video request -> video generation;
- unsupported multiplayer request remains as `game.multiplayer` requirement;
- current normal web prompt still gets existing web lifecycle requirements.

- [ ] **Step 2: Verify red test.**

```bash
python -m pytest tests/test_m495_capability_planner.py -q
```

- [ ] **Step 3: Implement `CapabilityPlanner.plan`.**

Deterministic plan requirements may be enriched later, never removed by model output.

- [ ] **Step 4: Add `capabilities` field to `BrainDecision` and update `to_dict`.**

Keep all existing fields and call sites backward-compatible.

- [ ] **Step 5: Run planner + existing universal-brain tests.**

- [ ] **Step 6: Commit.**

```bash
git add omni_prod/capability_planner.py omni_prod/universal_brain.py tests/test_m495_capability_planner.py
git commit -m "feat: plan capability DAGs from product intent"
```

---

### Task 4: Define universal provider contracts

**Files:**
- Create: `omni_prod/provider_contracts.py`
- Test: `tests/test_m495_provider_contracts.py`

**Interfaces:**
- Produces: `ProviderCapability`, `ProviderQuote`, `ProviderTaskHandle`, `ProviderTaskState`, `CapabilityArtifact`, `ProviderExecutionResult`, `CapabilityProvider`.

- [ ] **Step 1: Write validation/serialization tests.**

Assert non-negative quote costs, `maximum_cost_usd >= estimated_cost_usd`, non-empty provider/task/idempotency identifiers, legal terminal state names, actual cost optional.

- [ ] **Step 2: Run red test.**

- [ ] **Step 3: Implement contracts exactly from spec.**

- [ ] **Step 4: Run green test.**

- [ ] **Step 5: Commit.**

```bash
git add omni_prod/provider_contracts.py tests/test_m495_provider_contracts.py
git commit -m "feat: define provider-neutral capability contract"
```

---

### Task 5: Implement provider registry and deterministic capability router

**Files:**
- Create: `omni_prod/provider_registry.py`
- Create: `omni_prod/provider_router.py`
- Test: `tests/test_m495_provider_router.py`

**Interfaces:**
- Consumes: Task 4 provider contracts.
- Produces: `ProviderRegistry`, `CapabilityRoutingPolicy`, `ProviderCandidate`, `ProviderSelection`, `CapabilityProviderRouter.select`.

- [ ] **Step 1: Write failing route-policy tests.**

Cover health, cost ceiling, quality, latency, output format, commercial-use right, allow/deny lists, no candidates, deterministic tie-break.

- [ ] **Step 2: Run red test.**

- [ ] **Step 3: Implement registry duplicate checks and router.**

Do not call providers during `select`; selection uses already-produced quotes/metadata.

- [ ] **Step 4: Run green test.**

- [ ] **Step 5: Commit.**

```bash
git add omni_prod/provider_registry.py omni_prod/provider_router.py tests/test_m495_provider_router.py
git commit -m "feat: route capabilities by cost quality health and rights"
```

---

### Task 6: Add artifact verification primitives

**Files:**
- Create: `omni_prod/capability_verification.py`
- Test: `tests/test_m495_capability_verification.py`

**Interfaces:**
- Produces: `verify_capability_artifact(...)` or equivalent focused validator surface documented in module.
- Consumes: Task 4 `CapabilityArtifact` plus bytes loaded from canonical store.

- [ ] **Step 1: Write failing tests for corrupted checksum, empty bytes, fake GLB and valid minimal GLB.**

Also cover image/audio/video parsers only when dependencies already exist; do not add heavyweight media dependencies merely for M4.95.

- [ ] **Step 2: Run red test.**

- [ ] **Step 3: Implement checksum + minimal structural validators.**

GLB validation must at least verify magic/version/declared length and JSON/BIN chunk framing; random bytes must fail.

- [ ] **Step 4: Run green test.**

- [ ] **Step 5: Commit.**

```bash
git add omni_prod/capability_verification.py tests/test_m495_capability_verification.py
git commit -m "feat: verify generated capability artifacts"
```

---

### Task 7: Add migration 017 and durable capability repository

**Files:**
- Create: `infra/postgres/017_capability_foundation.sql`
- Create: `omni_prod/capability_repository.py`
- Test: `tests/integration/test_m495_capability_persistence.py`

**Interfaces:**
- Consumes: `DatabasePool`, `CapabilityPlan`.
- Produces: `PostgresCapabilityRepository.create_plan/requirements/transition/record_usage/usage_for_build`.

- [ ] **Step 1: Write migration schema exactly as spec and add migration discovery test if the repository has one.**

- [ ] **Step 2: Write PostgreSQL integration tests for persistence, CAS transitions, tenant scoping and duplicate/idempotent usage.**

- [ ] **Step 3: Run integration test and verify red/fail until repository exists.**

- [ ] **Step 4: Implement repository using existing DB transaction patterns.**

Use SQL parameterization; never interpolate capability/provider values into SQL strings.

- [ ] **Step 5: Run migration/integration green.**

- [ ] **Step 6: Commit.**

```bash
git add infra/postgres/017_capability_foundation.sql omni_prod/capability_repository.py tests/integration/test_m495_capability_persistence.py
git commit -m "feat: persist capability plans and provider usage"
```

---

### Task 8: Bridge existing media and model gateways into provider contracts

**Files:**
- Create: `omni_prod/providers/__init__.py`
- Create: `omni_prod/providers/http_media_provider.py`
- Create: `omni_prod/providers/llm_provider.py`
- Modify: `omni_prod/media_pipeline.py` only if a stable mapping helper is needed.
- Test: `tests/integration/test_m495_provider_adapter.py`

**Interfaces:**
- Consumes: current `HTTPMediaGateway`, `RoutedModelGateway`, Task 4 contract.
- Produces: provider adapters that expose current mechanisms through the new interface.

- [ ] **Step 1: Build deterministic local fake HTTP media provider used only by tests.**

- [ ] **Step 2: Write real-HTTP adapter lifecycle test: quote -> submit -> poll -> collect.**

- [ ] **Step 3: Implement `HTTPMediaCapabilityProvider` wrapper without changing the existing gateway contract.**

- [ ] **Step 4: Add LLM bridge only where it can report a conservative maximum cost and real route identity.**

Do not claim provider-measured actual token cost if current gateway does not expose it.

- [ ] **Step 5: Run adapter tests and existing media/model router tests.**

- [ ] **Step 6: Commit.**

```bash
git add omni_prod/providers omni_prod/media_pipeline.py tests/integration/test_m495_provider_adapter.py
git commit -m "feat: bridge existing gateways into capability providers"
```

---

### Task 9: Implement capability execution + storage + evidence

**Files:**
- Create: `omni_prod/capability_executor.py`
- Modify: `omni_prod/storage.py` only if a generic artifact-store protocol is needed; preserve `S3ArtifactStore` API.
- Test: extend `tests/integration/test_m495_provider_adapter.py`

**Interfaces:**
- Consumes: capability plan, provider selections, registry, repository, S3 artifact store, verifier.
- Produces: stored verified `CapabilityArtifact` records and durable usage events.

- [ ] **Step 1: Write failure-first execution tests.**

Cover provider error, timeout, invalid bytes, store failure, retry idempotency, unknown actual cost.

- [ ] **Step 2: Implement topological execution and durable transitions.**

- [ ] **Step 3: Persist provider usage/evidence after each external result.**

- [ ] **Step 4: Assert actual cost remains NULL when absent.**

- [ ] **Step 5: Run focused integration tests.**

- [ ] **Step 6: Commit.**

```bash
git add omni_prod/capability_executor.py omni_prod/storage.py tests/integration/test_m495_provider_adapter.py
git commit -m "feat: execute and verify provider-backed capabilities"
```

---

### Task 10: Integrate conservative capability quote with durable subscription reservation

**Files:**
- Modify: `omni_prod/subscription_store.py`
- Modify: `omni_prod/job_repository.py` only if build request needs an additive serialized capability summary.
- Test: `tests/test_m495_capability_economics.py`
- Test: `tests/integration/test_m495_capability_persistence.py`

**Interfaces:**
- Consumes: aggregate `maximum_cost_usd` from provider selections.
- Produces: reservation that contains the conservative maximum before provider dispatch.

- [ ] **Step 1: Write unit tests for aggregate maximum cost and quote expiry.**

- [ ] **Step 2: Write concurrency integration test proving two concurrent reservations cannot exceed one account's monthly provider cap.**

- [ ] **Step 3: Add the smallest additive reservation integration needed.**

Prefer passing the conservative aggregate through existing `estimated_provider_cost_usd` field rather than introducing a second budget system. Document that its semantic becomes “reserved conservative provider maximum” for M4.95 builds.

- [ ] **Step 4: Verify settlement keeps provider-reported actual distinct from reserved amount.**

- [ ] **Step 5: Run existing M1/M4 billing-reservation tests.**

- [ ] **Step 6: Commit.**

```bash
git add omni_prod/subscription_store.py omni_prod/job_repository.py tests/test_m495_capability_economics.py tests/integration/test_m495_capability_persistence.py
git commit -m "feat: reserve capability provider cost before execution"
```

---

### Task 11: Wire capability plan/execution into the durable live-build worker

**Files:**
- Modify: `omni_prod/worker_tasks.py`
- Modify: `omni_prod/investor_app.py` build creation path only where the conservative quote must exist before enqueue/reservation.
- Test: new focused worker tests or extend existing M4/M1 worker suites without weakening them.

**Interfaces:**
- Consumes: `BrainDecision.capabilities`, provider router/executor, durable repository, subscription reservation.
- Produces: required capability evidence included in build READY decision.

- [ ] **Step 1: Write test that required `NOT_CONFIGURED` 3D capability blocks READY and reports actionable status.**

- [ ] **Step 2: Write test that optional capability failure does not block READY but is visible in evidence.**

- [ ] **Step 3: Write test that fake provider stack can produce/stash/verify required asset before build continuation.**

- [ ] **Step 4: Implement worker ordering from spec.**

Do not call provider services in the HTTP request after returning 202 unless the existing reservation must synchronously know a quote; if quotes require network, add a durable preflight/quote job phase rather than lengthening the request path.

- [ ] **Step 5: Preserve existing quality/security/rights gate order and append capability gate deterministically.**

- [ ] **Step 6: Run full existing async build/worker tests.**

- [ ] **Step 7: Commit.**

```bash
git add omni_prod/worker_tasks.py omni_prod/investor_app.py tests
git commit -m "feat: enforce capability execution in durable builds"
```

---

### Task 12: Add truthful read APIs and readiness surface

**Files:**
- Modify: `omni_prod/investor_app.py`
- Modify: `omni_prod/integration_center.py`
- Test: add API tests following current FastAPI test patterns.

**Interfaces:**
- Produces:
  - `GET /api/v28/capabilities`
  - `GET /api/v28/providers/status`
  - `GET /api/v28/projects/{project_id}/builds/{build_id}/capabilities`

- [ ] **Step 1: Write authorization/secret-redaction tests first.**

- [ ] **Step 2: Add read-only endpoints.**

- [ ] **Step 3: Verify cross-tenant build capability metadata cannot be read.**

- [ ] **Step 4: Verify no API response contains secret value/ref resolution.**

- [ ] **Step 5: Commit.**

```bash
git add omni_prod/investor_app.py omni_prod/integration_center.py tests
git commit -m "feat: expose truthful capability readiness"
```

---

### Task 13: Upgrade exported asset evidence without breaking old manifests

**Files:**
- Modify: `omni_prod/media_pipeline.py`
- Modify: code that writes `assets/148ai-asset-manifest.json` after materialization.
- Test: extend current media/universal-pro tests.

**Interfaces:**
- Consumes: verified capability artifacts.
- Produces: backward-compatible plan + materialization fields.

- [ ] **Step 1: Write compatibility test for current manifest readers.**

- [ ] **Step 2: Write test that generated provider artifact includes capability key, provider, checksum, storage reference, estimate/actual distinction and provenance.**

- [ ] **Step 3: Implement additive fields only.**

- [ ] **Step 4: Run existing media tests.**

- [ ] **Step 5: Commit.**

```bash
git add omni_prod/media_pipeline.py tests
git commit -m "feat: record verified asset provenance and cost"
```

---

### Task 14: Capability Matrix, cost model and mission truth lock

**Files:**
- Create: `CAPABILITY_MATRIX.md`
- Create/update: `COST_MODEL.md`
- Modify: `PRODUCT_MISSION_AND_ACCEPTANCE.md`
- Modify: `STATUS.md`

**Interfaces:**
- Consumes: machine evidence from previous tasks.
- Produces: single human-readable source of truth.

- [ ] **Step 1: Populate every canonical capability with one allowed status.**

Never infer LIVE from a provider class existing.

- [ ] **Step 2: Update mission with 3D, speech, media, marketplace/social/multiplayer long-term scope.**

- [ ] **Step 3: Add measured/fake-stack M4.95 cost evidence and explicitly distinguish estimates from actual external billing.**

- [ ] **Step 4: Update STATUS with exact tests, timestamps, environment and blockers.**

- [ ] **Step 5: Commit.**

```bash
git add CAPABILITY_MATRIX.md COST_MODEL.md PRODUCT_MISSION_AND_ACCEPTANCE.md STATUS.md
git commit -m "docs: lock M4.95 capability and cost truth"
```

---

### Task 15: Golden acceptance and full regression

**Files:**
- Create/update: `M4_95_VALIDATION.md`
- Add acceptance fixture/test file following repository naming conventions.

**Interfaces:**
- Consumes: all M4.95 tasks.
- Produces: evidence suitable for claiming M4.95 complete.

- [ ] **Step 1: Run the M4.95 golden 3D delivery-game planning/fake-provider acceptance.**

Expected: capability DAG includes code/game/3D/texture/audio/music; required fake-provider artifacts verify; costs reconcile; build path does not claim a real commercial 3D provider.

- [ ] **Step 2: Run complete non-live regression suite.**

Expected: no M4.9 regression.

- [ ] **Step 3: Run PostgreSQL/Redis parity integration where supported.**

- [ ] **Step 4: Run clean-room, lifecycle and secret-scan gates.**

- [ ] **Step 5: Record exact evidence and remaining NOT_CONFIGURED/BLOCKED items.**

- [ ] **Step 6: Final commit.**

```bash
git add M4_95_VALIDATION.md STATUS.md CAPABILITY_MATRIX.md
git commit -m "release: verify M4.95 capability foundation"
```

---

## Self-review result

- **Spec coverage:** registry, planning, provider contract, routing, verification, persistence, budget reservation, worker integration, API truth surface, manifests, docs and golden acceptance are each assigned to a task.
- **Type consistency:** all downstream tasks consume the exact names defined by Tasks 2–5.
- **Risk coverage:** concurrency, retry/idempotency, unsupported intent, cost truth and artifact integrity each have an owning test task.
- **Scope control:** live commercial Tripo/Meshy/Runway/voice integrations remain M5; M4.95 proves provider-neutral architecture with deterministic fake provider execution.
- **No completion claim:** this plan describes work to perform; it is not evidence that M4.95 has been implemented.
