# 148AI M4.95 Capability Foundation — Implementation Plan V2

**Authority:** `docs/superpowers/specs/2026-10-04-m495-capability-foundation-design.md`

**Baseline:** M4.9 commit `aa1e983e2283358f47896c3c8ad1527198f6db3e`

**Execution rule:** TDD for production behavior. `REAL EXECUTION OR EXPLICIT FAILURE`. No capability/provider is LIVE because a class, manifest, API key, or mock exists.

## Global invariants

- Required capabilities are never silently dropped.
- External paid execution requires conservative durable authorization before submit.
- Estimates are never stored as actual provider cost.
- Provider execution identity must survive retry/crash/restart without duplicate paid submit.
- Artifacts are VERIFIED only after structural/checksum/size validation.
- Tenant/project ownership checks apply at API, repository, credential, and artifact boundaries.
- Secrets never appear in DB plaintext, logs, artifacts, exported projects, or API payloads.
- Machine registries are canonical; docs/status are generated/validated against them rather than maintained as independent truth.

## Revised task order

1. **Baseline Evidence** — fresh M4.9 regression, clean-room/lifecycle evidence, environment truth, validation scaffold.
2. **Capability Registry** — immutable capability contracts, taxonomy, deterministic dependency closure, cycle rejection.
3. **Master Skills + Master Agents Registries** — machine-readable skills/agents, permissions, dependencies, allowed skills, verification metadata and cross-registry validation.
4. **Capability Planner + Dependency Closure** — deterministic intent/target/media -> capability DAG with unsupported required capability preservation.
5. **Universal Provider Contracts + Durable Execution Identity** — quote/submit/poll/collect/cancel contracts, idempotency key, provider task identity, progress and terminal state semantics.
6. **Provider Registry/Router + Quota Semantics** — quality/cost/latency/format/license/health routing plus provider-aware 429, Retry-After, quota exhaustion, cooldown and distributed circuit-breaker integration.
7. **Artifact Verification + Large Artifact Strategy** — checksum/mime/format validation, size caps, GLB/media structural checks, streaming/hash contract for large artifacts.
8. **Durable Capability Repository + Execution Attempts** — migration, requirements, usage events, execution attempts, provider_task_id, uniqueness/idempotency, lease/resume/CAS transitions.
9. **Provider Adapters + Credential Binding** — bridges for existing gateways and credential binding modes (`PLATFORM_MANAGED`, `CUSTOMER_CONNECTED`, `BYOK`) with only truthfully configured modes LIVE.
10. **Capability Executor + Crash/Retry/Resume** — topological execution, store/verify/evidence, duplicate-delivery safety, resume after worker death without duplicate external submit.
11. **Price Catalog + Quote/Reserve/Actual/Settlement** — versioned local conservative price catalog, max authorization, optional post-reservation provider quote, actual usage where available, unknown actual stays NULL, contribution/margin evidence.
12. **Worker Integration** — capability planning/execution in durable live-build worker, required capability gates before READY, timeouts/cancellation.
13. **Truth/Readiness APIs + Tenant Security** — authenticated capability/provider/build evidence APIs, tenant ownership, redaction, honest LIVE/PARTIAL/NOT_CONFIGURED/NOT_IMPLEMENTED/BLOCKED.
14. **Artifact Evidence/Export + Backward Compatibility** — provenance/cost/verification metadata in manifests/versions/exports, legacy manifest compatibility.
15. **Machine Truth Lock + CI Drift Checks** — capability/skills/agents/provider/cost registry coherence; code/docs/status taxonomy drift blocks CI.
16. **Golden E2E + Full Regression** — normal path plus worker-kill/restart, duplicate delivery, provider 429/quota, large artifact, cross-tenant denial, unknown actual cost, unsupported required capability, full regression.

## Gate to M5

M5 may begin only when Tasks 1–16 have objective evidence and the golden E2E proves a heterogeneous capability build can survive retry/restart without fake success or duplicate provider spend. Full per-user OAuth/BYOK onboarding UI may remain M5.5 if M5 uses `PLATFORM_MANAGED` credentials through the same credential-binding abstraction.
