# 148AI M4.95 — Capability Foundation & Truth Lock

**Status:** implementation specification — not evidence of completion  
**Canonical source audited:** `148AI-M4.9-complete(1).bundle` / `148AI-M4.9-complete(1).zip`  
**Canonical M4.9 HEAD:** `aa1e983e2283358f47896c3c8ad1527198f6db3e`  
**Spec date:** 2026-10-02  
**Purpose:** close the architectural gap between “148AI can plan many product/media types” and “148AI can discover, price, route, execute, verify and account for every required capability without one-off integrations.”

---

## 1. Executive objective

M4.95 MUST NOT add Tripo, Meshy, Runway, ElevenLabs or any other provider as a hard-coded special case.

M4.95 establishes a provider-neutral execution foundation so every future provider is an adapter behind a stable contract:

`Prompt -> Intent -> Product Plan -> Capability Plan -> Budget Reservation -> Provider Selection -> Execution -> Artifact -> Verification -> Cost Settlement -> Product Build`

M4.95 is successful only when the system can answer, in machine-readable form, for every requested capability:

1. What exact capability is required?
2. Is 148AI currently able to execute it?
3. Which providers can satisfy it?
4. What are the constraints, expected format and rights requirements?
5. What is the conservative maximum variable cost before execution?
6. Which provider was selected and why?
7. What artifact/evidence was produced?
8. What did the provider actually cost, when the provider exposes actual usage/cost?
9. Did the capability pass its target-specific verification?
10. If it failed, was the failure explicit rather than converted into fake success?

---

## 2. Non-negotiable constraints inherited from M4.9

- Preserve the durable async build architecture. Provider work must never depend on API-process memory.
- Preserve `REAL EXECUTION OR EXPLICIT FAILURE`.
- Preserve tenant/project ownership checks.
- Preserve the existing reservation lifecycle and transactional outbox model.
- Preserve the M4 modification/version semantics: unverified candidates must not become current.
- Preserve rights/IP, quality and security gates.
- Preserve current working contracts unless the change is additive and all callers/tests are migrated.
- No secret values in DB rows, logs, artifacts or exported generated projects.
- No provider may be described as LIVE merely because an API key exists.
- No capability may be described as LIVE merely because source code or a generation manifest exists.
- No external provider may run if the pre-authorized hard spend ceiling cannot contain the conservative quote.

---

## 3. Current M4.9 facts that M4.95 builds on

### Existing reusable primitives

- `omni_prod/model_router.py`: cost/quality/latency selection for LLM model options.
- `omni_prod/routed_gateway.py`: local-primary + policy-controlled model fallback.
- `omni_prod/model_policy.py`: external-call budget/call-count enforcement.
- `omni_prod/media_pipeline.py`: `AssetKind`, `AssetRequest`, `CreativePlan`, `CreativeDirector`; already includes `MODEL3D` and `TEXTURE`.
- `omni_prod/media_gateway.py`: generic HTTP media generation adapter.
- `omni_prod/game_pipeline.py`: Godot/Unity/Unreal build-plan contracts.
- `omni_prod/mobile_pipeline.py`: Android/iOS build-plan contracts.
- `omni_prod/integrations.py`: initial platform integration registry.
- `omni_prod/integration_center.py`: configuration-readiness surface.
- `omni_prod/secrets_manager.py`: env/vault secret references.
- `omni_prod/storage.py`: S3-compatible artifact store.
- `omni_prod/usage.py`: generic usage primitives.
- `omni_prod/pricing.py` and `omni_prod/subscription_store.py`: plan budgets, usage authorization and durable provider-spend reservation/settlement.
- `infra/postgres/013_durable_async_builds.sql`: durable build requests, credit reservations, evidence and outbox.
- `omni_prod/worker_tasks.py`: async real-build execution and release gates.
- `omni_prod/universal_brain.py`: deterministic plan + creative plan + rights assessment.

### Current gap

These primitives do not yet form one universal chain from capability discovery to provider-backed artifact verification. In particular, media/3D planning exists without a production capability router and without provider-specific verified artifact materialization in the V28 build path.

---

## 4. Canonical capability taxonomy

Capability keys are stable dotted strings. Do not expose provider brands in capability keys.

### 4.1 Software lifecycle

- `software.plan`
- `software.architecture`
- `software.code.generate`
- `software.code.modify`
- `software.dependencies.install`
- `software.build`
- `software.test`
- `software.repair`
- `software.preview`
- `software.export`
- `software.deploy.web`

### 4.2 Product targets

- `target.web`
- `target.saas`
- `target.backend`
- `target.database`
- `target.android.source`
- `target.android.build`
- `target.ios.source`
- `target.ios.build`
- `target.desktop.source`
- `target.agent`
- `target.automation`
- `target.game.2d`
- `target.game.3d`

### 4.3 Image / 2D

- `media.image.generate`
- `media.image.edit`
- `media.image.remove_background`
- `media.image.upscale`
- `media.vector.generate`
- `media.texture.generate`
- `media.sprite.generate`

### 4.4 3D / animation

- `media.3d.mesh.generate`
- `media.3d.texture`
- `media.3d.multiview`
- `media.3d.retopology`
- `media.3d.optimize`
- `media.3d.rig`
- `media.3d.animate`
- `media.3d.retarget`
- `media.3d.export`
- `media.3d.scene.compose`

### 4.5 Audio / voice / music

- `media.audio.sfx`
- `media.audio.music`
- `media.audio.tts`
- `media.audio.stt`
- `media.audio.realtime_voice`
- `media.audio.dubbing`
- `media.audio.cleanup`

### 4.6 Video / film

- `media.video.generate`
- `media.video.edit`
- `media.video.lipsync`
- `media.video.captions`
- `media.video.upscale`
- `media.film.storyboard`
- `media.film.shot_plan`
- `media.film.render`

### 4.7 AI/data product capabilities

- `ai.embedding`
- `ai.rag.ingest`
- `ai.rag.retrieve`
- `ai.agent.tools`
- `ai.agent.memory`
- `ai.agent.eval`

### 4.8 Integrations

- `integration.payment`
- `integration.email`
- `integration.sms`
- `integration.messaging`
- `integration.maps`
- `integration.storage`
- `integration.database`
- `integration.source_control`
- `integration.oauth`
- `integration.analytics`
- `integration.webhook`

### 4.9 Publishing/ecosystem capabilities (truth-locked now, not claimed LIVE)

- `publish.web`
- `publish.android`
- `publish.ios`
- `publish.asset`
- `ecosystem.discover`
- `ecosystem.creator_profile`
- `ecosystem.like`
- `ecosystem.comment`
- `ecosystem.follow`
- `ecosystem.remix`
- `ecosystem.marketplace`
- `ecosystem.revenue_share`
- `game.multiplayer`
- `game.matchmaking`

The registry may add future keys, but existing keys must never be silently repurposed.

---

## 5. New core data contracts

### 5.1 `omni_prod/capabilities.py`

```python
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
from typing import Mapping, Any

class CapabilityStatus(str, Enum):
    LIVE = 'LIVE'
    PARTIAL = 'PARTIAL'
    NOT_CONFIGURED = 'NOT_CONFIGURED'
    NOT_IMPLEMENTED = 'NOT_IMPLEMENTED'
    BLOCKED = 'BLOCKED'

@dataclass(frozen=True)
class CapabilityDefinition:
    key: str
    family: str
    description: str
    artifact_kinds: tuple[str, ...] = ()
    dependency_keys: tuple[str, ...] = ()
    provider_backed: bool = False
    default_required: bool = True
    commercial_use_required: bool = True

@dataclass(frozen=True)
class CapabilityRequirement:
    id: str
    key: str
    purpose: str
    required: bool
    quantity: int = 1
    constraints: Mapping[str, Any] = field(default_factory=dict)
    dependency_ids: tuple[str, ...] = ()

@dataclass(frozen=True)
class CapabilityPlan:
    requirements: tuple[CapabilityRequirement, ...]
    target_keys: tuple[str, ...]
    notes: tuple[str, ...] = ()
```

Rules:
- `CapabilityDefinition.key` is globally unique.
- A plan references only keys present in the canonical registry.
- `quantity >= 1`.
- `dependency_ids` must form a DAG; cycles fail planning explicitly.
- Constraints are serializable and may include output format, duration, dimensions, polygon budget, language, region, commercial-use requirement, max latency, max cost, engine, platform, etc.

### 5.2 `omni_prod/capability_registry.py`

Required public surface:

```python
class CapabilityRegistry:
    def get(self, key: str) -> CapabilityDefinition: ...
    def contains(self, key: str) -> bool: ...
    def all(self) -> tuple[CapabilityDefinition, ...]: ...
    def dependency_closure(self, keys: tuple[str, ...]) -> tuple[str, ...]: ...
    def validate_plan(self, plan: CapabilityPlan) -> None: ...
```

The initial registry is code/static-data controlled. M4.95 does NOT add third-party dynamic marketplace code execution.

### 5.3 `omni_prod/provider_contracts.py`

```python
@dataclass(frozen=True)
class ProviderCapability:
    capability_key: str
    output_formats: tuple[str, ...]
    commercial_use: bool
    max_concurrency: int | None = None
    regions: tuple[str, ...] = ()

@dataclass(frozen=True)
class ProviderQuote:
    provider: str
    capability_key: str
    estimated_cost_usd: Decimal
    maximum_cost_usd: Decimal
    pricing_version: str
    unit_name: str
    units: Decimal
    expires_at: str | None = None

@dataclass(frozen=True)
class ProviderTaskHandle:
    provider: str
    provider_task_id: str
    capability_requirement_id: str
    idempotency_key: str

@dataclass(frozen=True)
class ProviderTaskState:
    status: str  # QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED
    progress: float | None = None
    error_code: str | None = None
    error_message: str | None = None

@dataclass(frozen=True)
class CapabilityArtifact:
    artifact_key: str
    mime_type: str
    sha256: str
    size_bytes: int
    provider: str
    capability_key: str
    metadata: Mapping[str, Any]
    provenance: Mapping[str, Any]

@dataclass(frozen=True)
class ProviderExecutionResult:
    artifacts: tuple[CapabilityArtifact, ...]
    actual_cost_usd: Decimal | None
    usage: Mapping[str, Any]
    evidence: Mapping[str, Any]

class CapabilityProvider(Protocol):
    name: str
    def capabilities(self) -> tuple[ProviderCapability, ...]: ...
    def health(self) -> str: ...
    def quote(self, requirement: CapabilityRequirement) -> ProviderQuote: ...
    def submit(self, requirement: CapabilityRequirement, *, idempotency_key: str) -> ProviderTaskHandle: ...
    def poll(self, handle: ProviderTaskHandle) -> ProviderTaskState: ...
    def collect(self, handle: ProviderTaskHandle) -> ProviderExecutionResult: ...
    def cancel(self, handle: ProviderTaskHandle) -> None: ...
```

Providers that are synchronous internally may return a completed task immediately, but the platform contract remains async-safe.

### 5.4 `omni_prod/provider_registry.py`

```python
class ProviderRegistry:
    def register(self, provider: CapabilityProvider) -> None: ...
    def providers_for(self, capability_key: str) -> tuple[CapabilityProvider, ...]: ...
    def get(self, name: str) -> CapabilityProvider: ...
```

Rules:
- duplicate provider names fail startup/test;
- no secret values are stored in registry objects returned by API surfaces;
- providers may be registered only from trusted server configuration/code in M4.95.

### 5.5 `omni_prod/provider_router.py`

```python
@dataclass(frozen=True)
class CapabilityRoutingPolicy:
    minimum_quality: int = 70
    maximum_cost_usd: Decimal | None = None
    maximum_latency_ms: int | None = None
    required_formats: tuple[str, ...] = ()
    require_commercial_use: bool = True
    allowed_providers: tuple[str, ...] = ()
    denied_providers: tuple[str, ...] = ()
    allow_fallback: bool = True

@dataclass(frozen=True)
class ProviderCandidate:
    provider: str
    quality: int
    latency_ms: int
    quote: ProviderQuote
    health: str
    formats: tuple[str, ...]
    commercial_use: bool

@dataclass(frozen=True)
class ProviderSelection:
    candidate: ProviderCandidate
    reason: str
    rejected: tuple[dict, ...]

class CapabilityProviderRouter:
    def select(
        self,
        *,
        requirement: CapabilityRequirement,
        candidates: tuple[ProviderCandidate, ...],
        policy: CapabilityRoutingPolicy,
    ) -> ProviderSelection: ...
```

Selection order when cost preference is enabled:
1. capability/format/license eligibility;
2. health not FAILED;
3. hard maximum-cost ceiling;
4. minimum quality;
5. maximum latency if specified;
6. lowest conservative `maximum_cost_usd`;
7. highest quality;
8. lowest latency;
9. stable lexical provider tie-breaker.

No eligible provider => explicit `NOT_CONFIGURED` or `BLOCKED`, never fallback to a fake artifact.

---

## 6. Capability planner / DAG

### New file: `omni_prod/capability_planner.py`

The planner converts the existing `UnifiedPlan` + `CreativePlan` into a deterministic capability DAG. A live model may enrich constraints but must not remove deterministic requirements.

Required interface:

```python
class CapabilityPlanner:
    def plan(self, *, prompt: str, unified_plan, creative_plan) -> CapabilityPlan: ...
```

Minimum deterministic mappings:

- any real build => code generation, install, build, test, repair, preview, export;
- Android target => `target.android.source`; signed/release request => `target.android.build`;
- iOS target => `target.ios.source`; signed/release request => `target.ios.build`;
- game3d => `target.game.3d`, `media.3d.mesh.generate`, `media.3d.texture` and relevant audio/image capabilities from the creative plan;
- `AssetKind.MODEL3D` => `media.3d.mesh.generate`;
- `AssetKind.TEXTURE` => `media.3d.texture`;
- `AssetKind.IMAGE`/`ICON` => `media.image.generate`;
- `AssetKind.AUDIO` => `media.audio.sfx`;
- `AssetKind.MUSIC` => `media.audio.music`;
- `AssetKind.VOICE` => `media.audio.tts` unless the prompt explicitly requires STT/realtime voice;
- `AssetKind.VIDEO` => `media.video.generate`;
- explicit multiplayer request => `game.multiplayer` with current availability NOT_IMPLEMENTED until real runtime is added;
- explicit WhatsApp/PayPal/etc. request maps to generic capability keys plus provider/integration constraints; an absent connector is NOT_CONFIGURED/NOT_IMPLEMENTED, not silently omitted.

The planner must preserve requirement IDs and dependency edges so provider outputs can be injected into later build steps.

---

## 7. Legacy adapters — preserve, wrap, do not rewrite

### 7.1 LLM adapter

New file: `omni_prod/providers/llm_provider.py`

Wrap the existing `RoutedModelGateway` for `software.plan`, `software.architecture`, `software.code.generate`, `software.code.modify`, and model-driven repair/evaluation capabilities. Do not remove `routed_gateway.py` or its current policy.

### 7.2 Generic media gateway adapter

New file: `omni_prod/providers/http_media_provider.py`

Wrap `HTTPMediaGateway` behind `CapabilityProvider`. The existing endpoint contract remains supported. Map current `AssetKind` values to capability keys. This adapter is not evidence of live media generation unless a configured endpoint is health-checked and an acceptance generation succeeds.

### 7.3 Future provider adapters

M4.95 defines but does not require production activation of:

- `providers/tripo_provider.py`
- `providers/meshy_provider.py`
- `providers/image_provider.py`
- `providers/voice_provider.py`
- `providers/video_provider.py`

Specific provider implementation belongs to M5 or an explicitly scoped provider integration task. The interfaces must make those adapters additive.

---

## 8. Provider execution service

### New file: `omni_prod/capability_executor.py`

```python
class CapabilityExecutionError(RuntimeError): ...

class CapabilityExecutor:
    def quote_plan(self, plan: CapabilityPlan, *, policies: dict[str, CapabilityRoutingPolicy]) -> tuple[ProviderSelection, ...]: ...
    def execute_plan(
        self,
        *,
        build_id: str,
        account_id: str,
        project_id: str,
        plan: CapabilityPlan,
        selections: tuple[ProviderSelection, ...],
    ) -> tuple[CapabilityArtifact, ...]: ...
```

Execution rules:
- perform topological ordering;
- only execute provider-backed requirements;
- persist each state transition before/after external work;
- derive idempotency key from `build_id + requirement_id + provider + pricing_version`;
- store produced bytes through `S3ArtifactStore` or canonical artifact storage interface;
- validate checksum and non-empty size;
- validate MIME/format against capability definition;
- run capability-specific validator before status `VERIFIED`;
- record provider actual cost/usage if reported;
- if actual cost is unavailable, record `actual_cost_usd = NULL` and retain quote basis; never invent actual cost;
- cancellation/timeout/failure remains failure unless another provider is explicitly re-routed and re-quoted within remaining reservation budget.

---

## 9. Artifact verification

### New file: `omni_prod/capability_verification.py`

Required initial validators:

- image: parse/decode image, dimensions > 0;
- audio: container/codec parse where available, duration > 0;
- video: container parse where available, duration > 0;
- 3D GLB/glTF: valid header/JSON/buffer references, non-empty mesh primitives; optional engine import checks when toolchain available;
- text/code artifact: non-empty + target-specific build/test evidence remains owned by current build engine;
- unknown format: cannot be VERIFIED merely because bytes exist; status remains PARTIAL/FAILED according to policy.

M4.95 does not need a world-class geometry QA engine, but it must distinguish a valid 3D file from arbitrary bytes.

---

## 10. Durable schema — migration 017

Create: `infra/postgres/017_capability_foundation.sql`

```sql
CREATE TABLE IF NOT EXISTS build_capability_requirements (
    build_id TEXT NOT NULL REFERENCES build_requests(build_id) ON DELETE CASCADE,
    requirement_id TEXT NOT NULL,
    capability_key TEXT NOT NULL,
    purpose TEXT NOT NULL,
    required BOOLEAN NOT NULL DEFAULT TRUE,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    constraints_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    dependency_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL CHECK (status IN (
        'PLANNED','QUOTED','RESERVED','QUEUED','RUNNING',
        'GENERATED','VERIFIED','FAILED','CANCELLED','NOT_CONFIGURED','BLOCKED'
    )),
    selected_provider TEXT,
    pricing_version TEXT,
    estimated_cost_usd NUMERIC(14,6),
    maximum_cost_usd NUMERIC(14,6),
    actual_cost_usd NUMERIC(14,6),
    artifact_key TEXT,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(build_id, requirement_id)
);

CREATE INDEX IF NOT EXISTS idx_build_capability_status
ON build_capability_requirements(build_id, status);

CREATE INDEX IF NOT EXISTS idx_build_capability_key
ON build_capability_requirements(capability_key, created_at DESC);

CREATE TABLE IF NOT EXISTS provider_usage_events (
    id BIGSERIAL PRIMARY KEY,
    build_id TEXT REFERENCES build_requests(build_id) ON DELETE SET NULL,
    account_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    requirement_id TEXT,
    capability_key TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_operation TEXT NOT NULL,
    provider_request_id TEXT,
    status TEXT NOT NULL,
    estimated_cost_usd NUMERIC(14,6),
    maximum_cost_usd NUMERIC(14,6),
    actual_cost_usd NUMERIC(14,6),
    unit_name TEXT,
    units NUMERIC(30,6),
    latency_ms INTEGER,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_provider_usage_account_created
ON provider_usage_events(account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_provider_usage_build
ON provider_usage_events(build_id, created_at);

CREATE INDEX IF NOT EXISTS idx_provider_usage_provider_capability
ON provider_usage_events(provider, capability_key, created_at DESC);
```

Do NOT store API keys, OAuth refresh tokens, raw user secrets or private signing keys in either table.

---

## 11. Repository layer

Create: `omni_prod/capability_repository.py`

Required production interface:

```python
class CapabilityRepository(Protocol):
    def create_plan(self, *, build_id: str, plan: CapabilityPlan) -> None: ...
    def requirements(self, *, build_id: str) -> tuple[dict, ...]: ...
    def transition(self, *, build_id: str, requirement_id: str, expected: str, target: str, **fields) -> bool: ...
    def record_usage(self, *, event: dict) -> int: ...
    def usage_for_build(self, *, build_id: str) -> tuple[dict, ...]: ...
```

Implement `PostgresCapabilityRepository` following the transaction/idempotency patterns already used in `job_repository.py`, `preview_repository.py` and `modification_repository.py`.

---

## 12. Budget model and reservation integration

### 12.1 Build-level quote

Before any external provider task runs:

1. capability planner creates requirements;
2. provider router obtains a conservative `maximum_cost_usd` for every paid requirement;
3. total build maximum = sum of required paid capability maxima + existing LLM external maximums;
4. reserve the build using the existing durable reservation flow with this conservative total;
5. only then enqueue/execute paid provider work.

### 12.2 Existing reservation lifecycle remains authoritative

Reuse `credit_reservations` and `PostgresSubscriptionService.reserve/settle/release` rather than inventing an independent monthly budget ledger.

Important current M4.9 behavior already handles provider overrun safely at settlement by charging only available user budget and treating excess as company overrun. M4.95 should reduce that risk by reserving a conservative maximum rather than an optimistic estimate.

### 12.3 Required economics invariants

- no paid call before reservation;
- concurrent builds cannot each see the same unreserved monthly provider budget;
- quote expiry forces re-quote before dispatch;
- provider fallback requires a new quote and must fit remaining reserved budget;
- retry of same idempotency key must not double-settle platform usage;
- provider-reported actual cost wins when trustworthy/available;
- unknown actual cost remains unknown, not fabricated;
- company overrun is explicitly recorded and monitored.

---

## 13. `universal_brain.py` integration

Modify `BrainDecision` additively:

```python
@dataclass(frozen=True)
class BrainDecision:
    plan: UnifiedPlan
    agents: dict
    creative: CreativePlan
    capabilities: CapabilityPlan
    rights: RightsAssessment
    principles: tuple[str, ...]
```

`OmniUniversalBrain.decide()` must call `CapabilityPlanner.plan()` after the unified and creative plans are known.

Compatibility rule: every current caller expecting `plan`, `agents`, `creative`, `rights` and `principles` continues working.

---

## 14. Async worker integration

Modify `omni_prod/worker_tasks.py` only after registry/router/repository unit tests are green.

Required order inside `_run_live_build_job`:

1. reload durable build request;
2. transition build QUEUED -> RUNNING;
3. run brain decision including capability plan;
4. persist capability plan;
5. resolve capability availability;
6. quote required external capabilities;
7. prove the build's existing reservation covers the conservative total;
8. execute provider-backed prerequisites whose artifacts are required by generation/build;
9. expose materialized artifact references to the generation/build pipeline through an explicit asset manifest;
10. run real AI source generation;
11. run build/test/repair;
12. run quality/security/rights + capability artifact verification;
13. store final version/evidence;
14. settle reservation with actual-known provider spend + conservative documented basis for unknown-cost providers;
15. READY only if every REQUIRED capability and existing release gate passes.

If a required capability is `NOT_IMPLEMENTED` or `NOT_CONFIGURED`, the build returns an explicit actionable status; it does not silently remove the requirement.

---

## 15. Asset manifest upgrade

Preserve current `assets/148ai-asset-manifest.json` compatibility.

Add materialization fields when execution occurs:

```json
{
  "id": "asset-003",
  "kind": "model3d",
  "capability_key": "media.3d.mesh.generate",
  "status": "VERIFIED",
  "provider": "provider-name",
  "artifact_key": "artifacts/...",
  "mime_type": "model/gltf-binary",
  "sha256": "...",
  "estimated_cost_usd": "0.40",
  "actual_cost_usd": "0.37",
  "pricing_version": "2026-10-02",
  "rights": {...},
  "provenance": {...}
}
```

Never put provider secret references or signed temporary download URLs into the exported project manifest.

---

## 16. API/readiness surfaces

Add customer/admin-safe read endpoints to `omni_prod/investor_app.py`:

- `GET /api/v28/capabilities`
  - returns capability definition + truthful status only;
  - no secret/config values.
- `GET /api/v28/providers/status`
  - authenticated/admin-safe summary of provider name, capability keys, configured boolean, health, pricing freshness; no secrets.
- `GET /api/v28/projects/{project_id}/builds/{build_id}/capabilities`
  - project-owner scoped;
  - returns per-requirement status, selected provider, artifact/evidence summary and cost fields.

Do not add a provider mutation endpoint in M4.95 unless a separate authenticated admin-management scope is approved.

---

## 17. Capability truth matrix rules

Create `CAPABILITY_MATRIX.md` in repository root.

Every row must contain:

- capability key;
- customer-facing label;
- current truth status;
- implementation evidence;
- provider requirement;
- configured provider(s);
- verification evidence required for LIVE;
- cost basis;
- current blocker/next task.

Allowed status values only:

- `LIVE`
- `PARTIAL`
- `NOT_CONFIGURED`
- `NOT_IMPLEMENTED`
- `BLOCKED`

`LIVE` requires current machine evidence, not roadmap text, a class name, a generated source skeleton, or credential presence.

---

## 18. M4.95 initial truth matrix — implementation priority

| Capability | M4.9 truth | M4.95 target |
|---|---|---|
| Durable async build | verified in M4.9 scope | preserve |
| Code generation | live path exists, external provider production depends on config | register + meter |
| Code repair | verified in M4.9 scope | register + meter |
| Preview | verified in M4.9 scope | register |
| Web deploy | partial / environment-dependent | truth-lock |
| Image generation | planning + generic gateway | provider-neutral executable contract |
| Image edit | not distinct | registry definition, not claimed live |
| 3D mesh | planning only | provider-neutral executable contract |
| 3D texture | planning only | provider-neutral executable contract |
| 3D rig/animation | not implemented | registry + NOT_IMPLEMENTED truth |
| Voice/TTS/STT | generic voice planning / roadmap | split capabilities + provider contract |
| Music/SFX | planning / roadmap | split capabilities + provider contract |
| Video | planning / roadmap | provider contract + heavy-cost policy |
| Android/iOS | partial source/build contracts | truth-lock |
| Desktop | not implemented | truth-lock |
| Agent target | internal agents != generated product target | truth-lock |
| Automation target | not implemented end-to-end | truth-lock |
| Multiplayer | not implemented | truth-lock |
| Integration marketplace | roadmap | truth-lock |
| Creator economy | roadmap | truth-lock |

---

## 19. Tests — mandatory M4.95 acceptance suite

### 19.1 Unit tests

Create:

- `tests/test_m495_capability_registry.py`
- `tests/test_m495_capability_planner.py`
- `tests/test_m495_provider_router.py`
- `tests/test_m495_provider_contracts.py`
- `tests/test_m495_capability_verification.py`
- `tests/test_m495_capability_economics.py`

Minimum assertions:

1. duplicate capability key rejected;
2. unknown capability in plan rejected;
3. dependency cycle rejected;
4. 3D game prompt creates `target.game.3d`, `media.3d.mesh.generate`, `media.3d.texture` requirements;
5. voice request maps TTS/STT/realtime according to request wording;
6. required unsupported capability remains explicit, not dropped;
7. unhealthy provider not selected;
8. non-commercial provider rejected when commercial use required;
9. wrong output format rejected;
10. provider over max-cost rejected before submission;
11. deterministic route tie-break;
12. fallback disabled means first provider failure does not silently reroute;
13. fallback enabled must re-quote and remain within budget;
14. arbitrary bytes cannot verify as GLB;
15. valid minimal GLB passes structural validator;
16. unknown actual cost stored as NULL;
17. actual cost is never replaced with estimate in `actual_cost_usd`;
18. artifact checksum mismatch fails verification.

### 19.2 PostgreSQL integration

Create `tests/integration/test_m495_capability_persistence.py`.

Verify:

- plan survives new repository instance/process;
- status transitions are compare-and-set/idempotent;
- duplicate provider usage idempotency does not double-account;
- tenant/project scoping;
- deleting/retiring a build does not leak capability metadata to another tenant;
- concurrent build reservations cannot exceed the monthly provider cap.

### 19.3 Provider contract fake-server integration

Create `tests/integration/test_m495_provider_adapter.py` using a deterministic local fake provider server.

Prove:

`plan -> quote -> reserve -> submit -> poll -> collect -> S3/local test artifact -> verify -> usage row -> settle`

This test must use real HTTP and real bytes, but no paid external provider.

### 19.4 M4.95 golden acceptance

Prompt:

> Build a browser-playable 3D delivery game with one drivable van, a warehouse environment, branded-but-original UI, engine sound, delivery success SFX and a menu soundtrack. Do not use any third-party brands.

Acceptance for M4.95 foundation (before Tripo/Meshy live integration):

- planner produces code + game + 3D + texture + audio + music capability DAG;
- every requirement has truthful status;
- paid-provider maximum quote can be aggregated before execution;
- if no 3D provider is configured, status is `NOT_CONFIGURED` and build does not claim success;
- with deterministic fake provider adapter configured, artifacts are stored, structurally verified and cost-accounted;
- existing code build path still passes regression suite.

---

## 20. Required regression gates

Before claiming M4.95 complete:

1. run baseline M4.9 tests before changes;
2. run focused M4.95 tests red -> green;
3. run complete non-live regression suite;
4. run PostgreSQL/Redis live integration where the repository's M4.9 parity tooling supports it;
5. run M4.9 lifecycle/clean-room checks;
6. rerun secret scan;
7. record exact commands/results in `STATUS.md` and M4.95 validation artifact;
8. do not change the meaning of any previous `VERIFIED` M4 milestone without documenting the regression.

---

## 21. Documentation changes

Modify:

- `PRODUCT_MISSION_AND_ACCEPTANCE.md`
  - add universal capability architecture and explicit 2D/3D/voice/video/provider truth rules;
  - add Discover/social/marketplace/multiplayer to long-term scope without claiming implementation.
- `STATUS.md`
  - add M4.95 section with objective evidence.
- `COST_MODEL.md`
  - create if absent; record actual provider quote/usage examples and heavy-user scenario.
- `CAPABILITY_MATRIX.md`
  - canonical human-readable truth table.
- `README_DEVELOPER_V25_EN.md` and/or current developer setup doc
  - document provider adapter registration and safe secret configuration.
- `.env.example`
  - names only, no values/secrets; provider-specific variables only when an adapter actually exists.

---

## 22. Definition of Done

M4.95 is complete only when all are true:

- capability registry exists and is tested;
- capability planner produces a deterministic DAG from real user intent;
- provider contract supports quote/submit/poll/collect/cancel;
- provider router enforces capability, cost, quality, format, commercial-use and health constraints;
- provider execution is durable/idempotent enough to survive worker retry;
- capability artifacts carry storage key, checksum, provenance and cost metadata;
- per-capability provider usage is durable;
- build-level conservative external maximum is reserved before paid execution;
- unsupported/unconfigured capabilities are explicit;
- no current M4.9 working path regresses;
- `CAPABILITY_MATRIX.md` and `STATUS.md` are updated from machine evidence;
- the M4.95 golden test passes with a deterministic fake provider stack;
- no specific commercial media/3D provider is falsely claimed live unless separately configured and externally verified.

---

## 23. Explicitly deferred to M5+

M4.95 is foundation, not a grab-bag of integrations. The following are deliberately deferred unless implemented as an independent reviewed task:

- live Tripo/Meshy 3D adapter;
- production image provider adapter;
- production video provider adapter;
- production TTS/STT/music provider adapter;
- full multiplayer runtime;
- creator Discover/feed/social graph;
- marketplace/revenue-share payout system;
- per-user customer integration OAuth vault;
- production Android/iOS store publishing;
- desktop target;
- CAD/AR/VR/XR.

M5 should choose a small number of real providers and prove one multi-capability product end to end through the M4.95 interfaces.
