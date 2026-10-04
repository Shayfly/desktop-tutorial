# 148AI M5 — Production Vertical Slice Design

**Date:** 2026-10-04  
**Branch:** `milestone/m5-production-vertical-slice`  
**Base:** merged M4.95 capability foundation (`master` after `m4.95-capability-foundation-v2`)  
**Status:** design for review — not implementation evidence

## 1. Executive objective

M5 proves that 148AI is no longer only a strong engineering kernel plus provider-neutral capability framework. It must prove one complete, durable, commercially credible customer journey from account creation to a real published product, with truthful cost/evidence and crash-safe execution.

The canonical proof is:

`Account -> Prompt -> Product Plan -> Cost Quote -> Durable Reservation -> Real AI Generation -> Real Asset Generation -> Build -> Verify/Repair -> Live Preview -> Natural-Language Modification -> Version -> Production Publish -> Actual Cost Settlement -> Evidence`

M5 is not allowed to call a generated repository "ready" because source files exist, a provider returned success, or unit tests passed. Ready means the selected production target is actually runnable, verified, published through the chosen deployment adapter, and economically reconciled.

## 2. Product slice selected for M5

The first production slice is **Web/SaaS** because M4.9 already has the strongest evidence in that target and it exercises the largest number of reusable platform primitives without prematurely coupling the system to mobile stores or heavyweight game runtimes.

The generated product used for Golden E2E should be a non-trivial multi-user SaaS application with:

- authenticated users and at least two roles;
- durable relational data;
- file/object storage;
- one background or scheduled operation;
- one outbound integration/webhook or email flow;
- one real generated image/brand asset;
- one optional additional media capability (audio/voice or 3D) when configured;
- responsive UI;
- API/backend surface;
- production configuration separated from preview configuration;
- observable health endpoint and structured runtime errors.

The exact demo domain should remain replaceable. Acceptance is capability-based rather than hard-coded to one sample business.

## 3. Non-negotiable M5 rules

1. Preserve `REAL EXECUTION OR EXPLICIT FAILURE`.
2. No public production path may silently use legacy deterministic/demo generation as arbitrary AI generation.
3. No paid provider call before a durable conservative maximum reservation.
4. Provider-reported actual usage/cost is recorded when available; unknown actual cost remains unknown.
5. External paid tasks must be idempotent and resumable after worker/process failure.
6. No plaintext secret values in DB rows, logs, build artifacts, exports, manifests, or API responses.
7. Required capabilities that are unavailable or unconfigured block `READY`.
8. Preview success is not production-publish success.
9. Build success is not functional acceptance.
10. Every published release points to immutable source/version/build/artifact/evidence records.
11. Cross-tenant access is denied at every public resource boundary.
12. Production publishing must support rollback to the previous verified release.
13. External credentials, domains, Stripe live mode, and provider commercial approvals remain explicit `NOT_CONFIGURED/BLOCKED` gates when absent.

## 4. M5 architecture

### 4.1 Product Architect / Build Contract

M5 adds a bounded first version of the Product Architect for Web/SaaS. It consumes user intent and emits a durable Build Contract containing:

- product family and target;
- functional requirements;
- user roles/personas;
- data model requirements;
- required integrations;
- infrastructure requirements;
- capability DAG reference;
- acceptance criteria;
- security/privacy requirements;
- estimated/max variable cost;
- material unresolved questions;
- release target.

The architect follows **Ask Less — Infer More — Verify Everything**:
- high-confidence reversible decisions are inferred;
- medium-confidence decisions use safe defaults and are recorded;
- low-confidence decisions with material architecture/cost/legal/UX consequences become concise clarification questions.

The contract is versioned and becomes the binding input for generation and acceptance.

### 4.2 Canonical generation path

M5 public Web/SaaS generation must have one canonical path:

`Build Contract -> Capability Plan -> Reservation -> Provider Execution -> Repository/Assets -> Build/Test -> Repair Loop -> Verification -> Version Commit`

Any legacy deterministic repository factory remains test/demo-only and must be unreachable from the public arbitrary-generation path.

The code-generation stage must produce a genuine multi-file repository and capture:
- model/provider identity;
- prompt/context revision identity;
- token/usage evidence when exposed;
- generated file manifest;
- dependency manifest;
- repair attempts and deltas;
- final verification evidence.

### 4.3 Generated-app infrastructure provisioning

M5 introduces a **Web/SaaS Infrastructure Provisioner** abstraction. The Golden slice must support durable bindings for:

- PostgreSQL-compatible relational database;
- authentication/session service;
- object storage;
- environment/secrets references;
- background job / scheduled work primitive;
- outbound email or webhook primitive;
- preview and production environment separation.

The provisioner contract must distinguish:
- `PLATFORM_MANAGED` resources;
- `CUSTOMER_CONNECTED` resources;
- `BYOK` references.

M5 only needs one live implementation path for each required infrastructure class, but every binding is provider-neutral and recorded durably so M5.5 can expand customer connection workflows without rewriting generated products.

Generated products must not rely on `HostedDeploymentRuntime` or other process-memory runtime maps for production business data.

### 4.4 Identity lifecycle for the 148AI customer

M5 closes the minimum production account lifecycle required for a paid Web/SaaS staging product:

- register;
- email verification state;
- login;
- logout/session revocation;
- forgot/reset password;
- current-device/session management baseline;
- account deletion request lifecycle;
- user-data export request baseline;
- terms/privacy consent version recorded.

Google/Apple login adapters are included when credentials are configured. They must otherwise expose `NOT_CONFIGURED`, never fake success.

MFA/passkeys may remain M10 unless a security review promotes them earlier.

### 4.5 Durable project lifecycle

The customer project flow must support:

- create;
- list/search;
- rename;
- archive/unarchive;
- delete with safe retention/tombstone semantics;
- import ZIP/repository baseline where supported;
- build history;
- version history;
- diff/change summary;
- modification request history;
- restore/rollback;
- export;
- current preview and production release state.

All project/version/build/deployment access is tenant-scoped.

### 4.6 Live preview and modification

M5 uses the existing durable preview architecture and raises it to a product-quality Web/SaaS flow:

- preview lifecycle is durable and tenant-scoped;
- generated app must actually boot and answer health checks;
- frontend and API flows are exercised, not only the root page;
- logs and runtime errors attach to the build/preview evidence;
- modification requests operate against an immutable base version;
- only a verified candidate can become current;
- preview teardown remains idempotent.

A full Universal Live Workspace is M5.5/M6, but M5 must expose a coherent preview panel with status, logs/errors, version identity, and modification entry point.

### 4.7 Production deployment adapter

M5 introduces a real production deployment interface with **Vercel as the first Web/SaaS adapter** when credentials are configured.

Required deployment lifecycle:

`Verified Version -> Deployment Quote/Policy Check -> Immutable Release Package -> Provider Deploy -> Health Probe -> Public URL -> Record Release -> Optional Domain Bind -> Rollback`

The deployment record must contain:
- tenant/project/version/build IDs;
- deployment provider;
- provider deployment ID;
- environment;
- public URL;
- artifact/source checksum;
- deployment status;
- verification/health evidence;
- timestamps;
- previous deployment reference for rollback.

No route may record a deployment as active before the provider returns a real deployment identity and health verification succeeds.

When Vercel credentials are absent the status is `NOT_CONFIGURED`, while local/preview verification may still run.

### 4.8 Billing lifecycle

M5 upgrades the current Stripe baseline into a durable commercial lifecycle for the 148AI customer:

- Checkout session creation;
- durable webhook event ledger with unique event ID;
- subscription/customer/provider IDs persisted;
- plan activation/deactivation derived from verified events;
- duplicate delivery safe across process restarts;
- cancellation state;
- failed-payment / past-due state surfaced;
- plan/credit entitlement state;
- purchase/top-up record path;
- invoice/payment history references where exposed by provider;
- refund/chargeback states represented truthfully even if operations are initially admin/manual;
- test/live environment separation.

Stripe remains the payment processor; 148AI does not store card details.

### 4.9 Cost and margin reconciliation

M5 exercises the M4.95 economic architecture against real provider adapters.

Per build/action evidence must distinguish:
- price catalog version;
- conservative max quote;
- reserved amount;
- actual provider usage units;
- actual provider cost when available;
- unknown/unreported actual cost;
- retry/repair cost;
- sandbox/compute/storage/egress allocations included by policy;
- customer credits charged;
- gross contribution/margin evidence.

A production action is blocked when max authorized spend or minimum margin policy is violated.

### 4.10 Observability and supportability

M5 must have a per-request/per-build correlation identity propagated through API -> queue -> provider -> artifact -> preview/deploy evidence.

Minimum production observability:
- structured logs;
- durable build/deployment/provider events;
- queue/job state visibility;
- provider latency/error/rate-limit events;
- customer-visible error/reference ID;
- health/readiness endpoints;
- metrics export adapter suitable for a centralized backend;
- alertable failure categories.

A full on-call/SRE program is M10, but M5 cannot depend only on process-memory metrics for operational truth.

### 4.11 Backup / restore proof

For the selected production data stores, M5 must document and exercise at least one staging restore proof:
- backup artifact/snapshot identity;
- restore to isolated environment;
- integrity check;
- RPO/RTO evidence captured;
- no mutation of production during the drill.

The restore gate may be `EXTERNAL_PROOF_NEEDED` in local-only environments, but production staging cannot be accepted without evidence.

## 5. Provider scope for the M5 proof

M5 does not integrate dozens of providers. It proves the architecture with the smallest set that spans heterogeneous execution:

1. **LLM/code provider** — one real configured provider through the routed gateway.
2. **Image provider** — one real image generation/edit provider.
3. **Additional media provider** — choose audio/voice or 3D based on cost/config availability; the contract remains generic.
4. **Infrastructure providers** — one concrete DB/auth/storage path.
5. **Vercel** — first production web deployment adapter.
6. **Stripe** — billing lifecycle in test mode first, production-ready configuration gates explicit.

Provider selection is not hard-coded into canonical capability keys.

## 6. Security and tenant isolation gates

M5 acceptance must include explicit negative tests for:

- user A reading/modifying user B project, build, version, artifact, preview, deployment, integration binding, billing, or evidence;
- guessed object-storage keys;
- malicious project IDs/path traversal;
- secret value injection into logs/manifests/API responses;
- webhook replay/duplicate events;
- forged Stripe signatures;
- forged provider callbacks where callbacks are used;
- stale/expired execution lease mutation;
- unauthorized production publish;
- rollback to an unverified release;
- generated-code attempts to access control-plane secrets.

## 7. Golden E2E acceptance scenario

The M5 Golden scenario starts from a clean tenant and must prove:

1. User registers and reaches verified/eligible account state.
2. User creates a project using one natural-language description.
3. Product Architect emits a complete Build Contract; only material uncertainty blocks execution.
4. Capability DAG closes all required dependencies.
5. System returns a conservative cost/credit authorization before paid execution.
6. Reservation succeeds durably.
7. Real LLM provider produces a multi-file repository.
8. Real image provider produces at least one verified asset and it is injected into the repository.
9. Optional additional media capability is executed when configured; otherwise the capability is explicitly `NOT_CONFIGURED` and the Golden scenario uses a product whose required capabilities remain satisfiable.
10. Generated product receives durable DB/auth/storage bindings.
11. Dependency install/build executes in sandbox.
12. An intentionally injected or naturally occurring build/test defect is repaired through the real repair loop.
13. Functional acceptance verifies at least login/role/data/create/read/update path plus one integration/background path.
14. Live preview boots and is interactively reachable.
15. User requests a natural-language modification; a new candidate version is produced and verified before promotion.
16. Verified version is deployed through the real deployment adapter in staging/production mode when credentials are configured.
17. Public URL passes health and functional smoke checks.
18. Cost reservation settles against actual/provider evidence without relabeling estimates as actual.
19. Release evidence links account/project/build/version/providers/artifacts/tests/deployment/costs.
20. Previous verified deployment can be selected for rollback and the rollback is verified.

## 8. Failure-path acceptance

M5 is incomplete until the following scenarios are proven:

- worker dies after provider submit; restart resumes using stored provider task identity;
- duplicate queue delivery does not duplicate paid external work;
- provider 429 / Retry-After causes provider-specific backoff rather than global failure storm;
- provider timeout transitions to retry/fail according to policy and releases/settles budget correctly;
- provider returns malformed/corrupt asset; artifact never becomes VERIFIED;
- actual provider cost unavailable; ledger keeps actual as `NULL` and uses explicit settlement basis;
- build exceeds authorized provider spend; further paid calls are blocked;
- preview container crashes on boot; logs/evidence are preserved and no RUNNING success is reported;
- deployment provider accepts request but deployment health fails; release is not promoted active;
- deployment callback/retry is duplicated; state remains idempotent;
- Stripe webhook delivered repeatedly across process restart; one durable business effect;
- tenant attempts cross-resource access; denied;
- backup/restore drill proves restorable staging data before production acceptance.

## 9. M5 deliverable families

M5 implementation should be decomposed into explicit workstreams rather than one giant patch:

A. Product Architect / Build Contract  
B. Account lifecycle  
C. Project lifecycle hardening  
D. Infrastructure Provisioner  
E. Real provider adapters (LLM + image + one additional media)  
F. Preview/product acceptance  
G. Vercel deployment adapter + rollback  
H. Durable Stripe billing lifecycle  
I. Cost/usage/margin reconciliation  
J. Observability/correlation  
K. Backup/restore staging proof  
L. Golden E2E + security/failure regression

The implementation plan must order these by dependency and use TDD per workstream.

## 10. Explicit non-goals for M5

The following are important but do not block M5 if the architecture remains compatible:

- full multiplayer infrastructure;
- open-world game production;
- full mobile App Store / Play Store publishing;
- Desktop target factory;
- full generated Agent target;
- full generated Automation target;
- marketplace/discover/social/remix;
- creator payouts/revenue share;
- full enterprise SSO/SCIM/data residency suite;
- every media provider or every media type;
- universal click-to-edit workspace across all targets.

These remain M6-M11 work and must not be disguised as complete in M5.

## 11. M5 completion status vocabulary

M5 must end with one of these truthful outcomes:

- `M5_VERIFIED_STAGING_WEB_SAAS_VERTICAL_SLICE` — all local + staging external proofs required by M5 passed; live commercial production launch may still have explicit external configuration/legal gates.
- `M5_IMPLEMENTED_NOT_EXTERNALLY_VERIFIED` — code/tests exist but required provider/deployment/infrastructure proofs were not run.
- `M5_PARTIAL` — one or more required workstreams are missing or failing.
- `M5_BLOCKED_EXTERNAL` — engineering is ready but a named external credential/account/approval is the only remaining blocker for a particular proof.

Do not use `PRODUCTION_READY` as an M5 synonym.

## 12. Review focus before implementation planning

The implementation plan must explicitly resolve:

1. Which existing account model (`account_tenant`, `creator_accounts`, V28 wrappers) becomes canonical rather than multiplying auth stores.
2. Which generated-app durable auth/data/storage implementation is the first supported infrastructure profile.
3. Exact Vercel deployment API contract, idempotency key strategy, immutable release representation, and rollback semantics.
4. Durable Stripe webhook/event/subscription schema and migration path from in-memory `_seen`.
5. How preview/build/deploy correlation IDs flow through queues and provider calls.
6. How real provider actual usage maps into M4.95 price/usage units without inventing cost when APIs omit it.
7. How secret references are resolved for platform-managed providers without allowing generated apps to read control-plane credentials.
8. Which staging services are available for external proof; unavailable external services remain explicit gates rather than mocked success.
9. How legacy deterministic/demo generator paths are quarantined from public generation.
10. What exact Golden SaaS product fixture exercises every required M5 capability without turning the fixture itself into hard-coded product logic.
