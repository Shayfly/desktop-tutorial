# 148AI — Engineering Recovery Execution Contract (T01–T09)

**Adopted:** 2026-10-13 (founder directive).  
**Scope:** private founder-only single-user prototype first; do not conflate with commercial launch.  
**Source revision audited (PINNED):** `codex/148ai-verified-intake-2026-10-12@e7c1a0e6017ec203acf607086bd947063f560fde`.  
**Audit status:** **T01 PARTIAL / IN PROGRESS; T02–T09 NOT YET ACCEPTED.** Source modules for later tasks exist, but existence is not verified live E2E execution. This document creates execution criteria and records the *bounded* initial evidence; it does not implement the nine tasks.

## P0 additive founder directive — Project Readiness & Blocker Diagnosis (2026-10-13)

**Additional requirements, not a replacement for T01–T09:** every project must show its real readiness and why a build is blocked immediately; a founder-only diagnostic must identify the exact required dependencies, missing code/registries/providers/quotes/configuration and verified fix path, with safe client-visible alternatives and mobile usability. The photographed project says "buildable with constraints" but also "unpriced", and names `ai.agent.tools`, `integration.maps`, `media.audio.tts`, `outbound`, `target.agent`. Do not silently remove customer requirements or bypass cost/security gates to enable a button.

[**Binding detailed P0 UX and diagnosis addendum**](PROTOTYPE_READINESS_AND_BLOCKER_DIAGNOSTICS_P0_HE_2026-10-13.md) · [Tracked acceptance issue #26](https://github.com/Shayfly/desktop-tutorial/issues/26). Integrate into **T01, T03, T06, T07, T08 and T09** and verify in the actual protected Preview. This addendum is **SPECIFIED, not implemented**.

## Additive specifications (required; not replacements)

- **P0 Readiness and blocker diagnostics:** [customer/founder visible reasons, dependency provenance and safe unblock actions](PROTOTYPE_READINESS_AND_BLOCKER_DIAGNOSTICS_P0_HE_2026-10-13.md) (Issue #26).
- **Safe Build/Test/Repair core integration:** [reuse-first engineering integration specification, file-by-file code map, interfaces, sandbox/preview/cost guards, migration/test gates](BUILD_REPAIR_CORE_INTEGRATION_SPEC_HE_2026-10-13.md). It incorporates only the verified useful ideas from the proposed standalone FastAPI/E2B repair-loop prototype, **without introducing a second execution path**. Do not claim implementation from documentation alone.

## Core engineering rules (non-negotiable)

1. **Reuse Before Rewrite** — preserve functional existing architecture (FastAPI, Neon/Postgres, Redis/RQ, Oracle ARM64 runner, R2, Vercel) until a measured deficiency justifies replacement.
2. **Evidence Before Claims** — distinguish `DEFINED`, `IMPLEMENTED`, `WIRED`, `UNIT_TESTED`, `LIVE_VERIFIED`, `BLOCKED`. `READY` on a Vercel deployment does not mean an app/build is usable.
3. **Secure by Default** — isolate untrusted generated code, least privilege, private previews, scoped secrets, no arbitrary code execution in API/worker host.
4. **Cost per Verified Result** — optimize verified usable products per dollar, not raw token price. Quote → reserve → execute → meter actual → settle, with fail-closed ceilings and auditable evidence.
5. **Dependency order** — T01 is first; subsequent tasks must have independently verified input invariants, with other work allowed in isolated branches only if it does not claim a successor gate passed.
6. **Deploy discipline** — feature branch → PR → pinned-SHA CI → protected Preview with authorized automated access → Golden E2E evidence → Production only with separate approval. No secret values in issues, logs, screenshots or code.

## P0 execution tasks: DoD + evidence gates

| ID | Task | Owner domain / implementation focus | Verification to mark DONE | Initial assessment |
|---|---|---|---|---|
| **T01** | Baseline & Root-Cause Audit | Map repo branches/SHA, Vercel environments/deployments, variable **names only**, API routes, Oracle runner, Redis/RQ, Neon migrations and logs; reproduce first user-facing blocker on pinned revision. | Signed-off **Verified / Partial / Broken / Blocked** matrix with evidence and exact affected SHA, zero Production changes. | **PARTIAL** |
| **T02** | Durable Build State Machine | DRAFT → DISCOVERY → APPROVED → QUEUED → PLANNING → BUILDING → TESTING → REPAIRING → VERIFYING → PREVIEW_READY; FAILED/CANCELLED branches; atomic transitions, idempotency, heartbeat, leases, checkpoints, retry, dead-letter. Reconcile with existing state models instead of replacing them blindly. | Kill worker mid-build; resume/reconcile without lost accepted work, double reservation, or duplicate billing. Verify concurrency/race/timeout invariants. | **UNVERIFIED E2E** |
| **T03** | Real AI Discovery & Architect | Natural multilingual chat (Hebrew-first), budgeted model route through worker, structured JSON schema output, versioned frozen scope approval, executable agent/skill/provider DAG including dependency closure, cost and acceptance tests. No scripted questionnaire passed off as a model. | Real user prompt → clarifications → approved immutable requirements → validated build DAG → queued build with evidence. | **PARTIAL (code/test presence)** |
| **T04** | Secure Sandbox Execution | Existing isolated runner first; sandbox adapter boundary; optional E2B alternative **POC only**. Enforce CPU/memory/time/disk quotas, network allowlist/deny, no host/secret access, artifact transfer, cleanup. | Build real multi-file application and demonstrate secret/host escape probes fail; retain evidence. | **PARTIAL / ISOLATION UNVERIFIED** |
| **T05** | Build → Test → Repair → Verify | Real install/build/test, exit code/stdout/stderr, artifacts, error taxonomy, bounded contextual patch, same-failure guard, re-test, verification with acceptance evidence and bounded model spend. | Deliberately break compilation; autonomous repair returns a verified runnable app, with trace per attempt and no unbounded loops. | **UNVERIFIED E2E** |
| **T06** | Live Preview & Workspace | Private real preview, HTTP checks, auto-transition to visible build stage immediately on approval, durable chats/projects/versions, revisions and restores, functional responsive UI. | Browser opens live generated URL; change request causes verified new version and preview. Session restore remains coherent. | **BROKEN / NOT VERIFIED** |
| **T07** | Provider Router & FinOps | Catalog/availability, JSON validation, fallback by required skill/quality, per-provider quota/auth/error taxonomy, circuit breaker; reserve/measure/settle and cost-per-verified-build. | Exhaust one *known* provider quota: report exact provider and reason; bound spending before call; safe fallback or explicit pause with no budget overshoot. | **PARTIAL / PER-PROVIDER UNVERIFIED** |
| **T08** | Security, Recovery & Observability | RBAC, scoped secrets vault, private preview, input/output validators, trace by build_id, backups/restores, janitor, failure injection, CI gates, reproducible records. | Real backup-and-restore drill, fault/restart drill, isolation and security tests pass; each build maps to version, trace and settled cost. | **PARTIAL / LIVE GATES UNVERIFIED** |
| **T09** | Golden E2E Acceptance | Full real prompt → approve → plan → agent graph → code files → build → test/repair → verify → preview → change request → durable new version. | Two distinct repeated complete builds on same pinned deployed SHA, one injected compile failure repaired; re-login/session continuity; provenance, actual usage/price evidence, artifact URLs, external HTTP checks. | **NOT VERIFIED** |

**Completion tracking:** `0/9 fully accepted as of this initial audit`. T01 partially evidenced below; this is **not** zero implementation work.

## T01 — current bounded evidence (2026-10-13 review)

### GitHub / branch / Vercel

- GitHub repo: `Shayfly/desktop-tutorial`; default `main@e8f294902e90eefb87d54023218a279af385aae5` (old). The separate `milestone/pre-staging-2026-10-05@b68bbc64ae0254e428135f6cad79a0682005ad3c` contains diagnostic automation changes, not a verified integration release.
- UI/intake candidate: `codex/148ai-verified-intake-2026-10-12@e7c1a0e6017ec203acf607086bd947063f560fde`; PR #21 is draft, base `integration/148ai-release-audit-2026-10-12` and is **unstable** (checks failing). **Not merged to Production/main.**
- Vercel project `shayflys-projects/148aiv28` is a FastAPI project; current protected Preview deployed at `https://148aiv28-5x6y77v4r-shayflys-projects.vercel.app` for pinned candidate SHA. Vercel API reports deployment `READY`, project `live=false`; SSO protection enabled. Protection must remain in place for founder prototype.
- At pinned SHA: [Intake+Architecture CI SUCCESS](https://github.com/Shayfly/desktop-tutorial/actions/runs/38315444151); [Neon bootstrap SUCCESS](https://github.com/Shayfly/desktop-tutorial/actions/runs/38315444069).
- [v24-ci FAILURE](https://github.com/Shayfly/desktop-tutorial/actions/runs/38315444094): `tests/test_agent_os.py::AuditTests::test_committed_registry_is_current_and_not_inflated` mismatched generated counts (`61` vs `62`); `test_m4_acceptance` transitively fails. Do not mark entire suite passing because >1600 individual tests passed.
- [V11 Overlay CI FAILURE](https://github.com/Shayfly/desktop-tutorial/actions/runs/38315444061): same Agent OS registry mismatch.
- [intake-budget-pg FAILURE](https://github.com/Shayfly/desktop-tutorial/actions/runs/38315444059): `tests/test_real_docker_drain_recovery.py:271` expects `was OOM-killed` but received a timeout/exit-137 message. Inspect independently before changing production worker logic.
- [deployment-verify FAILURE](https://github.com/Shayfly/desktop-tutorial/actions/runs/38315479072): protected Preview returns HTTP 401 `PROTECTED`, missing authorized automation bypass; all subsequent live checks NOT_RUN. CI/Preview verification must use a scoped Vercel bypass secret without disabling preview protection.

### Oracle / runtime / budgets

- GitHub self-hosted runner `148ai-worker-01` was confirmed online/idle and successfully executed diagnostics on Oracle ARM64. Running Docker containers include worker, sandbox runner, preview router, preview worker, intake worker and janitor. Redis returned PONG and sandbox health HTTP 200. **These are service-health checks, not evidence that customer build E2E passed.**
- Oracle SSH enabled and internally reachable on port 22, but founder's Windows `Test-NetConnection 151.145.89.132 -Port 22` failed. Public TCP ports 80/443 reachable from an external GitHub runner; root inbound SSH cause remains not proven. Keep using runner; no new server purchase until measurements justify one. [Oracle diagnosis](https://github.com/Shayfly/desktop-tutorial/actions/runs/38307648883), [public ingress](https://github.com/Shayfly/desktop-tutorial/actions/runs/38307811591).
- Founder staging `INTERNAL_QA` grant confirmed **already active** (single-account). [Read-only QA budget audit](https://github.com/Shayfly/desktop-tutorial/actions/runs/38310057602): aggregate recorded USD `5.2670`, remaining `4.7330` under the **existing shared $10 internal QA reservation cap**, per-build max `$0.50`. *This is not a $10 balance at each provider.* The founder now states an assumed/test-credit `$10 per registered AI provider`: verify each provider billing/quota API or dashboard before showing such a figure; never synthesize balances. Where not measurable, mark `UNKNOWN`. Track per-provider spend, quota errors and fallbacks without billing surprises.
- Founder reported latest Preview `cost_quote_unknown` for `ai.agent.tools`, `integration.maps`, `media.audio.tts`, `outbound`, `target.agent`. **Reproduce with their exact approved project requirements**; audit incorrect compulsory classification vs genuinely required unavailable services vs missing provider quotes. Never silently delete required scope or fabricate zero-cost quotes. Present scoped alternatives for optional capabilities.
- Repository provides `qa_budget.py`, `entitlements.py`, `build_cost_plan.py`, `creator_plan.py`, `conversation/`, `agent_os/`, `model_gateway.py`, `preview_router.py`, `worker_tasks.py`, `remote_sandbox.py`, etc. Presence is not proof of runtime functionality. Intake model requires explicit environment switches, budget caps and worker queue route; default can be deterministic. Verify all route wiring and secrets names, **not secret values**.
- Full authoritative Neon migration state, full API route catalog, exact browser E2E and per-provider balances remain **NOT VERIFIED** in this initial T01 snapshot. Do not claim T01 DONE.

## T01 follow-up execution evidence — October 13, 2026

- Implementation PR [#25](https://github.com/Shayfly/desktop-tutorial/pull/25) was opened on isolated branch `fix/148ai-t01-ci-recovery-2026-10-13`. Genuine Docker OOM/recovery test deadline was separated from an unrelated four-second global deadline: the OOM flag assertion remains mandatory; final real-Docker CI still required.
- Existing offline self-hosted regeneration ran successfully in [Actions run 38323026110](https://github.com/Shayfly/desktop-tutorial/actions/runs/38323026110), creating registry-evidence commit `209db23c7b665b15954d551972a0184a72f723d8`; this is generated truth **not promotion to verified**. One subsequent V11 Overlay CI job already passed on the recovery branch; final exact-SHA full CI awaits completed runs.
- [Read-only founder staging DB audit 38323104154](https://github.com/Shayfly/desktop-tutorial/actions/runs/38323104154): `creator_projects`, `project_briefs`, `m5_build_contracts`, `build_jobs`, `schema_migrations` present; latest applied migration **37**. Latest six founder-associated stored build contracts are all `READY`, requiring only native build capabilities; no founder build_jobs in that DB. This does **not** reproduce the founder's earlier `cost_quote_unknown` screenshot, so do not assert the live error is fixed. Trace whether the affected request predates these contracts, uses another project, or was evaluated against a different deployment/configuration.
- Source tree currently contains additive **migration 038** (`infra/postgres/038_conversation_attachments.sql`), which is **not** present in audited running DB. Image/screenshot attachment persistence is therefore not verified on that staging DB. Perform verified backup+restore and code/DB deployment parity checks before any migration.
- Source code inventory found **178** `@app` route decorators in `omni_prod/investor_app.py` including the creator conversation, approvals, plans, durable builds, preview, versions and modifications. Decorator presence is **NOT** a passing HTTP or permission verification.
- Vercel protected preview verification remains HTTP 401 `PROTECTED`; neither this issue nor PR #25 removes authentication. A CI bypass requires scoped secret management; no token value is to be committed or exposed.

### Immediate blocker classification

| Gate | Observed | Next proof |
|---|---|---|
| Founder screenshot: quote unknown for five capabilities | **BROKEN UI admission** | Reproduce original request on same approved brief revision; capture required/optional capability DAG and provider quotes. |
| Agent OS generated registry mismatch | **ROOT CAUSE IDENTIFIED / GENERATED OUTPUT REFRESHED** | Full exact-SHA v24 + V11 CI green after report update. |
| Worker recovery OOM vs global timeout | **TEST BUG PATCHED** | Real Docker + ephemeral Postgres CI completes and proves OOMKilled, recovery. |
| Staging schema 37 vs source migration 038 | **VERSION DRIFT** | Backup/restore; preview staging migration + integrity/rollback checks. |
| Protected Preview automation | **BLOCKED** | Authorized bypass, pinned-SHA live HTTP/browser smoke without public exposure. |
| Product Golden E2E | **NOT VERIFIED** | Two billable opt-in QA test builds after gates, reconcile actual provider spend. |

## Initial reproducibility / release gates

1. Pin Git branch and deployment SHA, capture `/api/status` and user-facing `/api/v28/m5/status` authenticated or via approved private automation access. Capture server identity/build version so Preview requests cannot land on wrong SHA.
2. Reproduce creator project `cost_quote_unknown` on same pinned SHA and same approved user brief. Record plan payload *minus PII/secrets*, list required/optional capability classifications and matching provider pricing.
3. Classify individual failures under `code | cause | owner | repro | expected | observed | patch SHA | test SHA | evidence URL | status`.
4. Fix CI root cause first: generated Registry source-of-truth drift; independently inspect Docker OOM-versus-deadline test. No cosmetic skip, broad suppression, or manufactured GREEN.
5. Establish authorized Vercel bypass in **CI secret storage only**, keep deployment SSO protection on. Prevent secret leaks into logs or previews.
6. Finish T01 inventory: live worker/queue, Postgres migrations, names-only envs, routes, cache/version parity, backup/restore state, provider readiness and actual spend. Do not run paid requests in the **audit**.
7. Then tackle T02–T09 in dependency order, with per-stage gate and dual-build Golden E2E at the end.

## Technology constraints

- **Oracle vs Hetzner:** measure architecture, price, CPU/RAM availability, connectivity and ARM64 compatibility before switching hosting.
- **E2B or substitute:** prove isolation and economics behind a replaceable `SandboxAdapter` interface, not a mandatory dependency.
- **LangGraph / Temporal:** do not adopt without a specific demonstrated deficiency in the existing agent runtime.
- **Redis/RQ and Neon:** reuse with verified crash recovery, migrations, locks, backups and traces.
- **Master Skills Registry & Master Agents Registry:** must be executable, versioned source of truth; do not mark merely described capabilities as runnable.
- **Provider quota notification:** when verified upstream exhaustion occurs, show the specific provider, error category (`quota_exhausted`, `billing_exhausted`, `rate_limited`, `unauthorized`, `unknown`), check time, the alternatives attempted and next action. A `429` alone does **not** prove zero balance.

## Acceptance label definitions

- **BROKEN** = reproducible failure at a required gate.
- **PARTIAL** = implemented component(s), incomplete mandatory verification.
- **BLOCKED** = external permission/provider/protection prevents assessment, not proof app logic is wrong.
- **VERIFIED** = pinned SHA + real execution + repeatable evidence for the stated narrow behavior only.
- **DONE** = meets the task's entire DoD in the specified environment; all security and budget invariants intact.

### Release decision

**NOT LIVE / NOT PROTOTYPE-ACCEPTED**. A healthy server, protected Vercel `READY`, and a successful unit-test subset are insufficient. Founder acceptance requires two real independent end-to-end builds, a deliberate repair, working private preview, conversational modification producing a new durable version, session persistence, and actual settled provider costs inside authorized budgets. This document is an execution contract and **not** certification that those outcomes already occurred.
