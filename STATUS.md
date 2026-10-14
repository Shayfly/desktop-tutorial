# Update 2026-10-14 — conversational provider vertical slice

Baseline: verified PR #30 source head `b5f0625` (stacked on PR #28 source head `e364151`). This update does **not** claim a live provider-backed staging conversation. No paid provider call, manually initiated deployment, merge, secret change, flag change, database migration, or authentication bypass was made. GitHub/Vercel automatically created a PR Preview deployment and completed its deployment check; spend for this work was **$0**.

**Implemented and independently verified**
- The browser now distinguishes each assistant reply as model-generated, deterministic fallback, or a response that did not need a model, using the server's per-message status.
- Added a portable conversation-slice regression through `ConversationSupervisor` and `ReservedWorkerInterpreter`: bounded contextual follow-up, reservation/queue seam, evidence-bound requirements, invalid evidence rejection, message persistence contract, and a separate approval action. This test uses an in-memory store and a settled reservation test double; it is **not** a real provider, PostgreSQL, Redis, or live E2E.
- Local baseline before this change: `python -m unittest tests.test_conversation_os tests.test_intake_assistant_he tests.test_intake_worker_route tests.test_model_catalog_routing -v` — 80 tests passed, 4 PostgreSQL-dependent tests skipped after installing the missing FastAPI runtime dependency.
- Final focused local verification: `python -m unittest tests.test_conversation_os tests.test_intake_assistant_he tests.test_intake_worker_route tests.test_model_catalog_routing tests.test_intake_budget_pg -v` — **86 tests passed, 10 PostgreSQL-dependent tests skipped**. `node --check omni_prod/assets/app.js`, `python -m compileall -q omni_prod tests`, and `git diff --check` passed.
- On source head `b5f0625`, read-only CI records show `v24-ci` run 38488749440, `intake-budget-pg` run 38488749457, V11 Overlay CI run 38488749470, and intake/architecture regression run 38488749466 completed successfully. The earlier Linux full-suite evidence at `a799936` is 1,682 passed / 172 skipped / 324 subtests; it is not a new full-suite result for this worktree.
- On implementation commit `00c01c53964ce3d8b00f8107ad283632820bb70d`, PR CI passed: `v24-ci` runs 38490498580/38490515291 (`test`, `customer-ui`, `compose-config`); V11 Overlay CI 38490498602/38490515318 (`validate`); `intake-budget-pg` 38490498636/38490515186 (`pg`); intake/architecture regression 38490515248 (`deterministic-regressions`). The Preview deployment completed automatically. No merge-candidate compatibility run is reported for this milestone.

**Implemented but awaiting external live verification**
- The source path already includes worker-only provider routing, durable reservations, response validation, persistent Postgres conversation/brief repositories, cost settlement, and explicit revision-bound customer approval. The new UI disclosure and regression coverage do not change that live status.
- Current staging flags/caps were reported configured after the earlier worker-switch correction. Secret names may exist in GitHub, but secret values, validity, worker/provider reachability and actual provider usage are unknown.
- Previous runtime evidence: read-only run `38312763134` found the staging intake worker switch off; staging-only action `38313019963` enabled it and later Preview flags/caps were configured. This is configuration evidence only.

**Blocked by a named credential/service**
- Authenticated Preview E2E is blocked by protected deployment authentication: on implementation commit `00c01c53964ce3d8b00f8107ad283632820bb70d`, deployment-verify run [38490544184](https://github.com/Shayfly/desktop-tutorial/actions/runs/38490544184) returned HTTP 401 `PROTECTED`; verdict `BLOCKED`, 0 journey checks executed and all 10 mandatory checks skipped. Earlier source-head run [38488792854](https://github.com/Shayfly/desktop-tutorial/actions/runs/38488792854) had the same blocker. Required service/configuration: authorized `VERCEL_AUTOMATION_BYPASS_SECRET` or an equivalent approved authenticated test identity. Do not bypass the gate.
- This Windows worktree has no `OMNI_DATABASE_URL`, `OMNI_REDIS_URL`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OMNI_INTAKE_MODEL`, `OMNI_INTAKE_VIA_WORKER`, or Docker executable. Live Postgres persistence, Redis/RQ, provider configuration, and isolated build/preview therefore cannot be verified locally. Provider credential validity must be checked by the authorized owner without sharing values.

**Not implemented / not verified**
- No real provider-backed customer response, actual usage/cost settlement, durable staging conversation/restart recovery, or two-account isolation was observed in this milestone.
- No live Architect -> Agent OS -> Build -> Repair -> Preview path was attempted. The existing tests and source are not staging evidence; continue only after the first conversational slice passes the protected staging gate.
- Merge-candidate compatibility remains unverified; its workflow is milestone-target-only, and no run was observed for this milestone. Do not claim compatibility from a base-branch or synthetic prior run.

# 2026-10-12 — P0 session evidence (partial verification)

Read [the current evidence and gap report](docs/evidence/148ai_p0_2026-10-12.md) before interpreting historical status entries below. Final local focused regressions: 23 pass. Earlier exact-revision CI passed full pytest with 1607 passed / 172 skipped; palette changes require new CI. Golden AI/build/preview E2E is NOT_VERIFIED. Draft PR #21; no merge/Production/live migration/paid provider authorization.

# STATUS — M1 async builds / M3 running preview / M4 natural-language modification

## Update 2026-10-11 ~22:00 Asia/Jerusalem — deploy gate, rollback after 038, real-Docker rehearsal, evidence export, isolation (LOCAL ONLY, nothing pushed)

Branch `claude/fix-static-site-acceptance-2026-10-11` (base a3cc9abc). Tested commit: **f419f58** (full suite below). Later commits only touch STATUS.md.

**Implemented and independently verified (local, on this commit)**
- Deploy gate fails closed (`omni_prod/active_jobs.py`, `drain.sh`): exit 2 when DB/Redis/URL/table/args cannot be verified, stale heartbeat still blocks (only `--acknowledge-stale <exact id>` releases, never passed by the workflow), intake (CLAIMED/EXECUTING even with an expired lease), STARTING previews, every RQ started-registry (incl. unregistered `omni-preview-host-*`) and busy RQ workers block; re-check immediately before and after the stop; a refusal before the stop leaves `not-stopped` so `recover.sh` touches nothing. Tests: `tests/test_worker_deploy_recovery.py` (GateInDrainTests, ActiveJobGateTests; the real-RQ test ran with a local Redis).
- Code rollback after 038 without DROP/deleted attachments/hidden version: `python -m omni_prod.migrate --accept-newer 38` (exact versions, only newer than the package; unlisted version / gap / checksum drift still abort), `deploy-worker.yml` dispatch input `accept_newer_migrations`. Tests: `tests/test_migration_rollback_tolerance.py` (isolated throw-away PG; attachment row survives old->new round trip). The previous worker code (2a2bba6) was also run locally against a DB at 038: `migrate` fails (as before), the worker boots and listens.
- Real Docker (engine 29.8.2 started in this sandbox, `docker compose` 5.5.1): `tests/test_real_docker_drain_recovery.py`, 8 scenarios against isolated PG + Redis, unmodified drain.sh/recover.sh: clean deploy, active job, Redis/DB/missing-URL failure, rollback-image save failure (fault injection around real docker, labelled), timeout->137, real OOM (engine OOMKilled flag), migration failure, startup failure; every scenario ends with all four services running the previous image. 8 passed.
- Evidence export extended (generated files + `.omni/project.json`, failed checks with evidence, credit reservation, `--files-dir`), `omni_prod/failure_replay.py` (offline CRUD-requirement / missing-coverage / real-defect separation, SYNTHETIC test data only), `omni_prod/isolation_check.py` (non-secret identities, SHARED/ISOLATED/UNKNOWN).

**Full suite on f419f58:** 1697 passed, 43 skipped, 0 failed, 288 subtests passed (551 s). Skips: 11 need a live Redis on 127.0.0.1:6379 (not provided; the new tests use `OMNI_TEST_REDIS_URL`), 4+3 live preview/sandbox hosts (`OMNI_RUN_LIVE_PREVIEW`/`LIVE_SANDBOX`), 4 migrated live Postgres, 3 `OMNI_RUN_LIVE_INTEGRATION`, 3 `omni-sandbox:latest` image absent (registry pulls blocked), the rest each name a missing credential/service (QStash, LLM, image provider, R2, Android/Xcode signing, clean-room DB, fixture URL) or are documented duplicates. None is counted as a pass.

**Implemented but awaiting external live verification**
- The same drain/recover scripts on the real Oracle host with the real images/compose/.env (the sandbox proves script logic on a real engine, not the host). NO-GO until the person approves a rehearsal when no build is running.
- One-off evidence export of the exact "חגית" build (not run): needs the `bld_<hex>` and someone with worker-host access (or read-only DB + `OMNI_S3_*`). See docs/DEPLOY_RECOVERY_REHEARSAL_HE.md section 4.
- Effective isolation check: needs `vercel env pull` files for preview/production and the worker `.env` produced by the owner. Known already (read-only Vercel API): `OMNI_DATABASE_URL`, `OMNI_REDIS_URL`, `OMNI_SECRET_KEY` are ONE record for production+preview => SHARED DB, SHARED Redis (=> shared queues). `OMNI_S3_*` are separate records, values unknown.

**Blocked by a named credential/service**: live DB state (active jobs, "חגית" data), Vercel runtime logs, billing API (404), deployment-verify bypass secret, a new restore-verified backup (needs a dispatch on the milestone ref — approval).

**Not implemented / open**: no route to roll back to code older than this branch through the workflow (only image-level `recover.sh`, no migration); no API-side pause of work intake (a job starting between the last gate check and SIGTERM and running past 25 min is cut off and reported); backup restore checks 14 tables and not `conversation_attachments`; scheduled backup still not installed; "חגית" is NOT shown fixed. No Mock/Replay presented as proof of a new build; no paid call made; no push, merge, deploy, migration or secret change.


## Update 2026-10-11 ~19:30 Asia/Jerusalem — project "חגית" failed build: content-only site acceptance (LOCAL ONLY, nothing pushed)

Base: a3cc9abc (PR #17 head). Branch `claude/fix-static-site-acceptance-2026-10-11`. No push, merge, deploy, live migration, secret change or paid call was made; spend by this work: $0.

**Customer failure (from the founder's screenshot, not from job evidence):** `BEHAVIOR: ... 2 failed check(s); missing acceptance coverage: A2,A4,A5; missing required behavior kinds: data_create,responsive`.

### 1. Implemented and independently verified (offline, this commit)
- Structured content-only handling: a new non-delegable question `content_only`; the binding brief block gets `Product kind: CONTENT-ONLY website` only after an explicit "yes" with sign-in NONE and no personal data; `ProductArchitect.compile` records `static_content_site` only from that approved block (free text never qualifies); `acceptance_scope` then waives **data_create only**. data_read, responsive and api_smoke stay required; missing/unknown contract, any login/role, personal data, external integration, storage/scheduled/outbound infra, or a CRUD product keep the full floor.
- "No personal data" in Hebrew/English is read from the request; delegation never decides `content_only`.
- A WhatsApp *link* (wa.me, "קישור/כפתור וואטסאפ") is no longer inferred as an SMS/messaging integration (architect, intake contract, feasibility answer).
- Conversation: a bare "תתחיל/בוא נתחיל/go" with an existing brief returns the `approve_build` action (no auto-approval); content added after the brief is complete (prices, texts, links) is recorded verbatim in the brief `content` field as a new revision, which invalidates any earlier approval via the fingerprint; the "ready" sentence is not repeated.
- Repair feedback now states which kinds are NOT_REQUIRED and that criteria mapped only to them stay uncovered (target of the "A2,A4,A5 missing" loop).
- Tests: `tests/test_content_only_site.py` (13) fail without the fix (collection error) and pass with it, including a real local HTTP run of `WebSaaSAcceptanceRunner`.
- Full suite on the fix: 1627 passed, 44 skipped, 3 failed → the 3 were registry/department files made stale by the code change; regenerated with the canonical generators (`python -m omni_prod.agent_os.audit --write`, `python -m omni_prod.agent_os.departments --write`) and re-run green. **Side effect: real-server evidence for discovery requirement_extraction / smart_question_generation / safe_default_selection is now STALE (REAL_SERVER_VERIFIED → IMPLEMENTED; Truth Matrix 22 → 19) until re-verified on a real server.**

### 2. Implemented, awaiting external live verification
- Everything above on the real worker/Preview. The failed job itself has NOT been reproduced: its approved brief/contract, A2/A4/A5 definitions, generated files, `.omni/project.json`, per-round failures and spend are not accessible from here (UNVERIFIED which of scope / mapping / data defect / responsive defect / stagnation applies).

### 3. Blocked by a named credential/service
- Job evidence export (authenticated project/job APIs / DB read), worker runtime SHA and flags, Preview/Production env isolation values, `VERCEL_AUTOMATION_BYPASS_SECRET` for deployment-verify (HTTP 401 PROTECTED), live migration 038.

### 4. Not implemented
- Inspector activation, candidate-before-accept, durable resume, paid Golden E2E proof; an actual reproduction of the "חגית" job.

### Follow-up commit (same day, local only): spec/prompt support, worker drain/recovery, scheduled backup, evidence export
- **Generator/ProductSpec:** the generator sees only the ProductSpec, so for an approved content-only contract the floor spec is now `site-content` + responsive + health (no platform-auth/rbac/data), and the Architect/Generator/Repair system prompts carry `CONTENT_ONLY_RULES` (static page, no DB/login/record API, plan limited to data_read/responsive/api_smoke, every acceptance id attached to a real check). Removing only the data_create check while still telling the model to build CRUD is thereby closed (offline tests; the model's behaviour itself is UNVERIFIED until one paid build).
- **Deploy recovery (`infra/worker-host/drain.sh`, `recover.sh`, `deploy-worker.yml`):** drains all four consumers (worker, intake-worker, intake-maintain, preview-worker); fails the deploy BEFORE migrations on a failed stop, exit 137, OOM or a still-running container; records previous images; `recover.sh` restores the previous consumers on drain/migrate/start/listen failure without touching the DB or volumes. Verified only with a fake `docker` (8 tests incl. a mutation check); NOT run on the real host.
- **Scheduled backup:** root cause confirmed by design (GitHub fires `schedule` only from the default branch). `infra/backup-scheduler/backup-scheduler.yml` (inactive here) dispatches `backup-restore.yml` on the milestone branch and fails if the last success is older than 30 h. Needs a one-file PR on `main` (Vercel builds Production from `main`: owner decision; changing the default branch is NOT proposed) and a later real-cron verification.
- **Evidence export:** `omni_prod/evidence_export.py` (one-off via stdin into the already-deployed worker image: no merge, no worker deploy) + `docs/FAILED_BUILD_EVIDENCE_EXPORT_HE.md` (+ a later-convenience workflow); schema-tested against the local PostgreSQL. Not run against the failed build.
- **Review fixes (2026-10-11, second round):** (1) drain is blocked when an existing consumer's image cannot be inspected/tagged or listed; (2) `recover.sh` fails when a recorded service has no rollback image, `up` fails, a service is not running afterwards or the worker is not listening; (3) the export uses only the approval whose `used_by_build_id` is exactly the build (and a matching brief/contract fingerprint) and reports MISSING/AMBIGUOUS instead of substituting; (4) the backup scheduler now separates DISPATCHED / STARTED / SUCCEEDED and is green only when the NEW run succeeds; it is NOT installed or active, the default branch is not to be changed, and a real cron run must still be verified after an approved install. Regression tests fail on the previous code (6 recovery/scheduler + 4 export).
- **Pre-merge safety assessment (2026-10-11 ~20:00):** `omni_prod/active_jobs.py` + a gate step before the drain (waits up to 20 min for RUNNING builds/changes, then fails WITHOUT draining; queued work is not interrupted; stale heartbeats are reported, not blocking). Simulation (fresh local DB, old code 2a2bba6 → 037, data, new code → 038): data preserved; **old code's `omni_prod.migrate` ABORTS on a DB at 038 ("applied migration missing from package: 38")**, so rolling back by redeploying old code through deploy-worker needs the manual 038 rollback first (`DROP TABLE conversation_attachments` + `DELETE FROM schema_migrations WHERE version=38`, simulated: other tables untouched, old migrate clean, 038 re-applies). Live facts read today: Preview `/api/v28/deployment` = a3cc9abc, applied_max 37, 038 missing (MIGRATIONS_PENDING); last backup 20261011T123608Z restore-verified (55 versions rebuilt, 14 tables, migrations 37); Vercel DB/Redis variables are ONE record shared by Preview and Production.
- **Runtime facts re-read (Vercel API):** latest Preview `dpl_536b1wK6…` READY at `a3cc9abc`, target null (no Production change); worker last recorded deploy `2a2bba6` (Actions 38130249079, per the handoff); live DB version, live flags and the failed job's data: UNVERIFIED (no access).


## Update 2026-10-11 ~15:30 Asia/Jerusalem — Conversation UX, image attachments, Visual Edit, 3-pane workspace

**Branch `claude/visual-edit-workspace-2026-10-11` (stacked on PR #16). Not merged. $0: no paid model call, no paid flag, no secret change, no production deploy.** Details and gap list: `docs/VISUAL_EDIT_AND_ATTACHMENTS.md`.

**Vercel state checked first**:
- Production = `main` @ `e8f2949` (2026-10-06, old code).
- Integration Preview = `2a2bba6` (READY).
- PR #11, #15 and #16 exist only as their own branch previews.

**Implemented and independently verified (local; real FastAPI + PostgreSQL + real preview router over TLS; real Chromium desktop 1440×900 and mobile 390×844)**
- **Conversation:** short decision names; values taken from the request are verified, not re-asked; "don't know"/"what?" gets the reason, then the options (never the same sentence twice). Approved requirements are still never changed silently.
- **Image attachments** (migration 038 `conversation_attachments`, additive):
  - PNG/JPEG/WebP decided from bytes; SVG refused (415); 3 MB / 8000 px / 6 per message / 40 per project.
  - Owner-only (another account gets 403/404); `nosniff` + sandbox CSP; bytes deleted with the attachment.
  - Shown in the thread; the reply says plainly that images are **not analyzed**.
- **Visual Edit:**
  - Pick an element in the live preview (mouse or touch); the preview inspector wraps the unchanged router, off unless `OMNI_PREVIEW_INSPECTOR=1`.
  - The element is located in the stored source (file:line). Ambiguous → the person chooses, and the server refuses a guessed target (409).
  - Screenshot with box/drawing marks.
  - The change goes through the existing modifications pipeline; before/after comparison and undo use the existing previews and rollback.
- **Layout:** desktop chat (right) | preview (centre) | edit tools (left), all resizable, project list as a drawer; mobile tabs Chat / Preview / Edit; "Agent tasks" moved under "Build progress" as collapsible technical details.
- **Evidence:**
  - `docs/evidence/visual_edit/walkthrough_result.json`: **23/23** checks, screenshots 01–16.
  - The Wave A UI walkthrough still passes (two steps adapted to the drawer/tabs).
  - Test-only substitutes: local-file object storage, a local process instead of a preview container, and a harness-written modification candidate (no model).
- **Tests:**
  - `tests/test_visual_edit.py` (real PostgreSQL) and `tests/test_conversation_ux.py`.
  - The 036→037 upgrade test is now scoped to ≤ 037, because 038 exists.
  - Neon bootstrap regenerated and verified on an empty PostgreSQL (34 migrations).
  - Full suite: **1564 passed, 2 failed, 44 skipped** before that scoping. One failure was the upgrade test, now passing. The other was `test_m4_acceptance` W, whose nested run included that same failure; it passes when run alone after the fix.

**Implemented but awaiting external live verification**: the inspector on the real preview host (env flags + worker deploy); one real targeted modification on the worker (paid); S3/R2 attachment storage on Vercel.

**Blocked**: image analysis by a vision model (no vision route and no approved budget).

**Not implemented**: preview of a candidate before accepting it; picking inside apps whose own CSP forbids `'self'` scripts (screenshot marking still works). After PR #11 merges, `schema_manifest.REQUIRED_MIGRATION` must become 38.

## Update 2026-10-11 ~17:00 Asia/Jerusalem — Master directive stages 1–4/6: plan-governed execution (G1), approved criteria as test basis (G3), escalated intake lane

**Branch `claude/plan-driven-execution-2026-10-11` (from `2a2bba6`). Not merged. $0 spent: no paid model call, no paid flag, no secret change, no production deploy.** Full audit and Beta/Production blockers: `docs/SYSTEM_WIDE_GAP_AUDIT.md`.

**Implemented and independently verified (real PostgreSQL 16 locally; real engine loop with local stub agents; no provider)**
- G1 plan-governed execution behind `OMNI_PLAN_DRIVEN=1`:
  - The approved ExecutionGraph (durable `agent_tasks`) admits every model call and every verification run; dependencies are checked under a row lock.
  - Out-of-order, repeated, over-limit and over-budget steps stop the build with `plan_violation`.
  - Spend is charged to its plan task (`AgentRuntime.charge`, metered or authorized worst case). Over budget → task BLOCKED.
  - The plan's repair limit tightens the engine (never widens it).
  - A superseded (lost) worker is refused.
  - Violations are sticky, even if a caller swallows them.
  - Legacy recording is unchanged without the flag. `build_control.py` is untouched, so no verified evidence was invalidated.
- G3: approved `intake-requirements/1` acceptance criteria travel with the plan binding.
  - In plan-governed builds they are merged into the spec as `APPROVED-AC*`, so behavioural acceptance must cover each one.
  - New mandatory release check `acceptance/approved_criteria_covered`: FAIL or NOT_RUN blocks READY.
- Stage 1: HIGH/RISKY intake turns escalate to task class `conversation_complex` (preferred 85, mandatory 70).
  - The quote, the reservation payload and the worker call use the same task; a mismatch is released before execution.
  - MEDIUM stays on the standard lane; LOW uses no model.
- Stage 2: the plan states per-task `permissions`, the final `deliverable`, the preview's mandatory checks and `execution_mode`. The graph fingerprint is unchanged.
- Tests:
  - `tests/test_plan_driven_execution.py`: 30 tests (17 need real PostgreSQL), added to CI job `intake-budget-pg`, which applies migrations and fails on any skip.
  - Updated lane test; new supervisor escalation test.
  - Affected suites: 186 passed.
  - Full suite: **1541 passed, 1 failed, 44 skipped**. The failure is `test_maintenance_live_postgres` (order-dependent; passes alone: 2 passed).
  - Generators current: `omni_prod.agent_os.audit` (registry unchanged) and `omni_prod.intelligence.matrix --write` (new task class).

**Implemented but awaiting external live verification**: all of the above on a real build (G2, about $0.15 per build, founder approval) and a real escalated intake turn (paid intake activation).

**Blocked**: G2/G9/G10 (paid budget), G6 (`VERCEL_AUTOMATION_BYPASS_SECRET`), G5 (PR #11 merge approval).

**Not implemented**: parallel dispatcher and resume from a task checkpoint (G1b; documented in `plan.execution_mode.not_yet`), G11, non-web families.

## Update 2026-10-11 ~15:30 Asia/Jerusalem — Issue #12: atomic intake budget reservations, complexity routing, requirements preservation

**Branch `feature/intake-budget-complexity-router` (= PR #13 + Issue #12). Not merged. No paid model call, no paid flag enabled, no secret change, no production deploy.** Design, state machine, lock-order proof, migration/rollback: `docs/INTAKE_BUDGET_RESERVATIONS.md`.

**Implemented and independently verified (real PostgreSQL 16.15 + real Redis 8 / RQ 2.12 locally; provider = in-process transport behind the real RoutedModelGateway)**
- Migration 037 (additive): reservations, budget scopes (lock anchors), reservation-scope links, transactional outbox, append-only events; `intake_messages.cost_usd` nullable (UNKNOWN). Neon bootstrap regenerated + verified on an empty PostgreSQL (33 migrations); 036→037 upgrade with data verified, idempotent.
- `intake/budget.py`: QUOTE (full envelope: 1 call, 0 retries, 0 fallback, every allowed model, fail closed without price/catalog) → RESERVE (sorted anchor locks, settled + outstanding sums, project / rolling-24 h / campaign ≤ $10 caps, idempotency key) → CLAIM → EXECUTING marker (committed before the call) → SETTLE (CONFIRMED / CONFIRMED_ZERO / ESTIMATED, or UNKNOWN with NULL amount and the quote held) → RECONCILE (expired EXECUTING → UNKNOWN, never released; CLAIMED/stale RESERVED → RELEASED) → resolve_unknown only with billing evidence.
- Worker execution (`intake/reservation_worker.py`) and `intake-maintain` service (outbox relay + reconcile). No unreserved paid path remains (legacy job refuses; direct API-host model calls refused).
- Strict cost metering: timeouts / HTTP errors / missing usage → UNKNOWN (not $0); the silent `'0'` cost of the intake path removed.
- Deterministic complexity classifier (LOW/MEDIUM/HIGH/RISKY with prior turns); LOW → no model; others → standard lane, floor 70 unchanged; low-risk sub-70 lane disabled (no qualification record).
- Requirements preservation: confirmed values never overwritten by model output (or material fields by any output) — conflicts asked back; strict model-output type/size validation; contract to the Chief Architect unchanged (`intake-requirements/1`, fingerprint-bound); approvals stay server-bound.
- Tests (all real, none mocked for DB concurrency): `tests/test_intake_budget_pg.py` 25 (60-way project saturation, 55-way daily, 60-way campaign, 110 mixed ops with `pg_stat_database.deadlocks` unchanged + a live deadlock negative control, rolling-24 h boundary, 50-way idempotency, double settlement, crash before/after provider, outbox crash/replay, 50 concurrent duplicate deliveries → 1 provider call, real RQ duplicate jobs → 1 call, timeout / 429 / 500 → UNKNOWN, verified zero, overrun flag, tenant isolation, end-to-end supervisor turns incl. 50 concurrent turns, migration path); `tests/test_intake_complexity.py` (129 contextual turns, 109 Hebrew/mixed, 71 sensitive, 0 false negatives); `tests/test_intake_requirements_preservation.py` 10; rewritten `tests/test_intake_worker_route.py`. Intake files 68 passed ×3 consecutive runs. Full suite: **1514 passed, 0 failed, 43 skipped** (base `73fc445` in the same environment: 1468 passed, 1 failed — the environment-only `test_m4_acceptance` W, which is flaky, not fixed).
- New CI workflow `intake-budget-pg` runs these tests against PostgreSQL 16 + Redis service containers and fails if any is skipped.

**Implemented but awaiting external live verification**: real Hebrew extraction quality, billed tokens vs quote bound (overrun flagged, not prevented), Vercel bundle including `model-catalog.json` (`vercel.json includeFiles`).

**Blocked**: activation — founder budget approval + non-secret flags (`OMNI_INTAKE_MODEL`, `OMNI_INTAKE_VIA_WORKER`, caps, `OMNI_REDIS_URL` on Vercel); acceptance-campaign entry point not wired.

**Not implemented**: change of the build pipeline's `_release_rejected` HTTP-error-is-free assumption (out of scope; intake does not rely on it).

## Update 2026-10-11 11:40 Asia/Jerusalem — Hebrew-first live Intake Assistant (prepared, NOT activated)

**Branch `claude/intake-assistant-he-2026-10-11` (from pre-staging `4cc9b91` + merge of `claude/wave-a2-worker-intake-2026-10-11`). Not merged. $0 — no model call made. Activation runbook: `docs/INTAKE_ASSISTANT_ACTIVATION.md`.**

**Implemented and independently verified (test doubles; no provider calls)**
- Worker-routed model intake (A2) on the current integration base: RQ `omni-intake`, `intake-worker` service, API-side re-validation, deterministic fallback on timeout/queue/provider error.
- `omni_prod/intake/mode.py`: single fail-closed source of truth for whether a paid model may answer — switch + per-project cap + **new rolling-24 h cap across projects** + per-message reserve; a call starts only if spent + reserve ≤ cap (no overshoot); spend read lazily, unreadable spend ⇒ deterministic.
- Truthful label: `/conversation` reported `interpreter: "model"` whenever the switch was on (even with zero budget) — now reports the mode that will actually answer.
- Hebrew-first prompt `intake-prompt/2-he-first`; Hebrew-aware evidence matching (niqqud, bidi marks, gershayim/geresh, maqaf; letters and final forms untouched) — fabricated/empty quotes still dropped; calls bounded (4,000 chars in, 700 tokens out) on both API and worker paths.
- Cost estimate from source-backed prices: gemini-3.1-flash-lite $0.0016/message upper bound; proposed acceptance test ≤ $0.05.
- Tests: `tests/test_intake_assistant_he.py` + updated `tests/test_intake_worker_route.py` — targeted 91 passed; full suite 1468 passed, 1 failed (`test_m4_acceptance` W, environment-only, also on base), 43 skipped.

**Blocked**: activation needs founder budget approval + non-secret flags on Vercel/worker. **Not verified**: any real Hebrew conversation with a model (no paid call made).

## Update 2026-10-11 03:30 Asia/Jerusalem — controlled pre-staging integration: BLOCKED at the merge step

- Founder authorized merging PR #8 into `milestone/pre-staging-2026-10-05` (directive 03:15). Pre-merge gates verified: integration head still `67a0765` (no newer commits), PR #8 mergeable/clean, all checks on `8fe5998` success (v24-ci, V11, Neon bootstrap, compose-config, fresh-postgres), fast-forward possible, migration 036 additive (3 new tables, `IF NOT EXISTS`, no change to existing tables), deploy-worker drains workers then runs `python -m omni_prod.migrate` then `up -d`. Rollback point: `67a0765` (revert the merge on the integration branch; 036 tables are unused by the old code and can stay).
- **The merge itself was refused by this session's safety layer** (both the fast-forward push and the GitHub PR merge call). Nothing was merged or deployed; worker still `67a0765`; migration 036 NOT applied; the new UI is NOT on pre-staging.
- Unblock: the founder clicks **Merge** on PR #8 (or merges `8fe5998` into the integration branch). That push triggers deploy-worker (migration 036 + worker `8fe5998`) and the Vercel Preview of the integration branch.
- Prepared meanwhile (branch `claude/wave-a2-worker-intake-2026-10-11`, `3194ecd`, not in PR #8): real-model intake routed through the worker (`intake-worker` service, `omni-intake` queue), OFF until authorized; tests with doubles only.

## Update 2026-10-11 10:45 Asia/Jerusalem — PR #11 security hardening of the deployment verifier (implementation: Claude; independent review: ChatGPT)

**Branch `claude/wave-a-fix-conversation-schema-2026-10-11` (PR #11). Not merged. No production deploy, no secret change, $0.** Review: `docs/DEPLOYMENT_VERIFY_SECURITY_REVIEW.md`.

**Implemented and independently verified (local, real HTTP over loopback; real FastAPI + PostgreSQL)**
- High: secret leak on redirect **reproduced** (Bearer token + bypass secret delivered to a second host after a 302) and fixed — redirects never followed; secrets only sent to the validated origin.
- High: SSRF — origin-only target, https except loopback, no IP literals/credentials/path/query, exact host or anchored suffix allowlist, all resolved addresses must be public.
- No cookie jar, no env proxies, 1 MiB response cap, per-request timeout + overall deadline, classified network failures (no crash), evidence without bodies/tokens + final scrub, full 40-hex SHA (+ optional trusted deployment-metadata SHA), production writes refused without explicit flag, server-controlled ids validated.
- Canonical contract: declared required checks; a missing/downgraded/NOT_RUN mandatory check ⇒ BLOCKED; FAIL ⇒ FAILED (takes precedence).
- PR #9 compared; its hardening and test shapes merged into PR #11 (PR #9 itself not merged).
- Tests `tests/test_deployment_verification.py`: 35 passed (+27 subtests) — attacks (cross/same-origin redirect, post-login redirect, cookies, echoed Authorization, path-steering id, 19 SSRF URL shapes, private/metadata DNS), network failures (refused, reset mid-journey, timeout, oversize, non-JSON), wrong credentials (bad bypass, no token, rejected token), SHA (short, malformed, mismatch, trusted mismatch, missing), schema mismatch, production guard, CLI exit codes 0/1/2/3.
- Full suite: 1479 passed, 1 failed (`test_m4_acceptance` W — environment-only, also failing on base), 43 skipped.
- Real local servers (`docs/evidence/verification/`): 036 DB → VERIFIED (exit 0); 035 DB → FAILED schema_compatible + conversation (exit 1); wrong SHA → FAILED (exit 1); `https://evil.example` → configuration error (exit 3).

**Implemented but awaiting external live verification**
- Workflow now runs only for `vercel[bot]` deployments (creator confirmed on real run 38114225915), non-Production, host suffix `-shayflys-projects.vercel.app`. Verdict on the protected Preview will remain BLOCKED until the bypass secret exists.

**Blocked by a named credential/service**
- `VERCEL_AUTOMATION_BYPASS_SECRET` (GitHub secret, from Vercel "Protection Bypass for Automation") — founder action.
- Promotion gating on the check (Vercel Deployment Checks / branch protection) — founder action.
- Merge decision — independent review (ChatGPT) + founder.

- Real-run regression found and fixed: run 38120874664 produced no result because argparse took the dash-leading host suffix for an option; the workflow now uses `--allowed-host-suffix=…` and a bad command line still writes a BLOCKED result (exit 3).

- Independent review findings R1–R3 fixed in `verification_contract.py`: exact full-SHA promotion binding (no prefixes, unbound promotion refused); timestamp/TTL validity window (future-dated, missing, non-finite, inverted, invalid TTL refused); mandatory NOT_APPLICABLE fails closed unless a versioned NA policy names the check; plus verdict recomputation at promotion (forged verdicts refused). `tests/test_deployment_verification.py`: 43 passed (+58 subtests). Full suite 1488 passed, 1 failed (`test_m4_acceptance` W, environment-only, also on base), 43 skipped.

- Closure review (`docs/DEPLOYMENT_VERIFY_SECURITY_REVIEW.md` §C1–C5): three promotion-gate bypasses found on `5ad2ccc` (forged empty required list, self-authorizing NA policy in the evidence, duplicate check names) — **fixed**: `may_promote` takes `required` / `na_policy` from the caller (`DEPLOYMENT_REQUIRED_CHECKS`), never from evidence; duplicates block; `ForgedEvidenceTests` 6. Deployment binding verified three ways for `5ad2ccc` (GitHub run head_sha = Vercel deployment `dpl_B6def4hWWTkGVtz8hsxbgZagciQB` = app-reported SHA, schema COMPATIBLE). Checkout `persist-credentials: false`. DNS rebinding: accepted residual risk for pre-staging, IP-pinning fix specified. `test_m4_acceptance` W: fails identically on unchanged base `4cc9b91`; its nested suite passes there (exit 0, 1303 tests OK) — log-tail check artefact of local live-PG warnings (`docs/evidence/verification/baseline_failure_m4_acceptance_W.json`). Full suite: 1493 passed, 2 failed (the W test above; `test_maintenance_live_postgres` order-dependent locally, 3/3 pass alone), 43 skipped. `tests/test_deployment_verification.py`: 49 passed (+67 subtests).

**Residual risks (not fixed)**: DNS rebinding between the address check and connect; `vercel.app` suffix trust relies on Vercel team-slug hostnames (mitigated by the `vercel[bot]` gate); app-reported SHA is self-reported; synthetic rows accumulate in the shared pre-staging DB.

## Update 2026-10-11 08:20 Asia/Jerusalem — Vercel "Server error" fixed + Continuous Verification P0.1–P0.4

**Branch `claude/wave-a-fix-conversation-schema-2026-10-11`. $0 spent. No production deploy, no secret change, no model call.**

Root cause of the red "Server error": `psycopg.errors.UndefinedTable: relation "execution_plans"/"intake_messages" does not exist` (Vercel runtime errors, deployment `dpl_42B7ngrpgoMCqxnLF2K4DUG3r5K8`, commit `8fe5998`): the branch Preview ran the Wave A API against the shared pre-staging DB before migration 036 was applied. Fix `b6a99c1` (503 `conversation_not_ready` + guided fallback, builds unaffected). The founder merged PR #8 (merge `4cc9b91`, 2026-10-11 01:10 UTC); deploy-worker run 38100955911 succeeded incl. "Apply database migrations".

**Implemented and independently verified**
- Migration 036 applied on the shared pre-staging DB — read from the real Vercel Preview `dpl_AcJCaecSiEBVCk6fz7vtawtVn2iE` (`19d76d7`): `GET /api/v28/deployment` → `schema.status=COMPATIBLE, applied_max=36, missing=[]`.
- No runtime errors on Vercel after 2026-10-11 00:25 UTC (both error groups belong to the pre-036 deployment).
- P0.1 coverage map: `docs/VERIFICATION_COVERAGE_MAP.md` (generated products well covered; the platform's own Vercel API had no post-deployment check — why the incident shipped).
- P0.3 canonical verdict `verification-result/1` (`omni_prod/verification_contract.py`): never VERIFIED by default; FAIL→FAILED; NOT_RUN/UNKNOWN→BLOCKED; skips need reasons; promotion gate refuses wrong-commit/artifact or expired evidence; `quality-report/1` maps onto it.
- P0.2/P0.4 deployment verification: `GET /api/v28/deployment` (commit, env, required vs applied migrations via `omni_prod/schema_manifest.py`, drift-tested) + `tools/deployment_verify.py` (SHA, schema, register→project→conversation→persistence→memory, anonymous denial, cross-user isolation; synthetic users) + workflow `deployment-verify` on every Vercel `deployment_status`.
- Local real-server evidence (`docs/evidence/verification/`): VERIFIED with 036; FAILED on 035 DB (schema + conversation 503); FAILED on wrong SHA.
- Tests: `tests/test_deployment_verification.py` 17 (scenarios A, E, J, auth bypass, leak, protected, unreachable, no token leakage). Full suite 1462 passed, 1 failed (`test_m4_acceptance` W, environment-only, also failing on base), 43 skipped.

**Implemented but awaiting external live verification**
- `deployment-verify` ran for real on GitHub (run 38113948928) against the Vercel Preview → **BLOCKED** (HTTP 401, Vercel deployment protection). Working as designed (never VERIFIED without evidence).

**Blocked by a named credential/service**
- Full journey on Vercel needs Vercel "Protection Bypass for Automation" stored as GitHub secret `VERCEL_AUTOMATION_BYPASS_SECRET` (founder action; not created by me).
- Gating Vercel promotion on the check needs Vercel Deployment Checks / branch protection (founder action).
- Live AI conversation: OFF (needs approved budget + `OMNI_INTAKE_MODEL`).

**Not implemented**: P0.5–P0.12 (repair loop over deployment failures, security gate expansion, visual QA on the platform UI, handoff contracts, requirement→test traceability, defect intelligence, dashboards, adversarial suite); paid Golden E2E (NOT RUN).

Note: PR #9 (`chatgpt/pdv-001-candidate-2026-10-11` → this branch, "PDV-001" standalone post-deployment verifier, 37 loopback tests) overlaps with `tools/deployment_verify.py`; not merged, needs a decision on which verifier to keep (or merge its hardening — host allowlist, redirect blocking — into this one).

## Update 2026-10-11 03:05 Asia/Jerusalem — Wave A (intelligence plane, Conversation OS, workspace UI) — IN PROGRESS, not merged

**Branch `claude/wave-a-intelligence-platform-2026-10-11` (base `c20503a` = `c874998` + PR #7). Not merged, not deployed. $0 spent. Live AI conversation NOT verified (no model call was made).** Baseline/source of truth: `docs/WAVE_A_BASELINE.md`. Handoff: `docs/CONTINUATION_HANDOFF.md` (Wave A section).

Commits: `17d246e` (A1–A2), `a138ccc` (A3–A9 + UI), plus this docs commit.

**Implemented and independently verified (local, real PostgreSQL / real Chromium; no provider calls)**
- A1 Provider Matrix (`PROVIDER_MATRIX.json`, `docs/PROVIDER_MATRIX.md`, generated; `--check` fails on drift/inflation): 14 entries; REAL_EXECUTION_VERIFIED only gemini-3.8-flash / 3.1-flash-lite / 3.5-flash-lite (ledger ok calls > 0); OpenAI/Anthropic CONNECTION_TESTED + INSUFFICIENT_CREDIT; media candidates NOT_CONNECTED. Effective-dated, source-backed prices (3.8-flash doubles 2027-01-01, applied automatically by the catalog loader); managed models without a source-backed price fail closed; retired models never routed.
- A2 Routing safety: explicit task classes; architecture now prefers the quality-85 model; mandatory floors (no silent downgrade); durable circuit breakers (migration 036 `provider_health`), CREDIT_EXHAUSTED/AUTH_INVALID skip the route across builds until reset or one half-open trial after 24 h.
- A3 Intake: deterministic HE/EN interpreter + confidence policy + `intake-requirements/1` contract; model interpreter exists but is OFF (`OMNI_INTAKE_MODEL=1` and a per-project `OMNI_INTAKE_MODEL_BUDGET_USD` > 0 required) and tested only with test doubles. Benchmark 12 cases (6 HE / 6 EN, author-written fixtures — regression check, not proof of real-world understanding).
- A4 Chief Architect + Execution Graph + feasibility gate + agent/skill router; web plan = 15 tasks bound to real engine stages; non-web families planned but non-executable (UNSUPPORTED); sign-in/payments BLOCKED until connected.
- A5 18 departments (`DEPARTMENT_MATRIX.json`): READY 3 · PARTIAL 7 · IMPLEMENTED 5 · NOT_IMPLEMENTED 3 (computed). Agents 54 (+ intake_agent, chief_architect, UNIT_TESTED).
- Conversation Supervisor + durable memory (intake_messages, execution_plans, 10-section memory view) + API (`/conversation`, `/memory`, `/builds/{id}/plan`); build admission binds the approved plan and refuses infeasible ones (409 `capability_not_feasible`).
- Worker: `PlanBoundRecorder` pre-creates the DAG as durable agent_tasks and moves them with the real stages; failures block downstream tasks; unreached tasks end CANCELLED, never SUCCEEDED (live PostgreSQL tests).
- A7: cost per verified success by codegen model, Wilson 95 % interval, minimum sample 10.
- UI: conversation-first workspace (sidebar with projects/search/collapse/mobile drawer · one chat with quick replies and real actions · resizable / enlargeable / closable preview); old mode-choice composer removed. Real-browser walkthrough (`tools/ui_conversation_walkthrough.py`) against a real FastAPI + PostgreSQL server: multi-turn HE + EN, persistence across reload and project switch, drag 605→859 px, enlarge 1416 px, close/reopen, no mobile horizontal scroll. Screenshots: `docs/evidence/wave_a/`.

**Tests:** targeted Wave A suites 130 passed. Full suite with the real web stack (fastapi/starlette/httpx/boto3 fetched from GitHub sources; PyPI unreachable here): base `c20503a` 3 failed (stale truth matrix — fixed by regeneration; nested `test_m4_acceptance` W subprocess — environment; `test_maintenance_live_postgres` — flaky locally, passes alone). Branch (`a138ccc`): **1444 passed, 1 failed, 43 skipped** — the one failure is the same nested `test_m4_acceptance` W environment failure as on the base; no new failure (base: 1372 passed, 3 failed). CI on the branch: check the runs for the head commit (pending at save time).

**Not done / blocked:** migration 036 not applied to the shared pre-staging DB (happens only via the deploy-worker on the integration branch); therefore a Vercel Preview of this branch shows the new UI but the conversation API needs 036 → **not deployed/usable on Preview yet**. No LLM key on Vercel. A6 extra handoff contract checks and A8 multimodal adapters NOT_IMPLEMENTED (matrix entries only). Modification flow from chat reuses the existing pipeline (offer + confirm button) — not exercised end-to-end here (needs the worker). Paid 10-build gate NOT RUN.


## Update 2026-10-11 01:20 Asia/Jerusalem — Production Assurance v2 (G0–G3, free work only) + handoff

**Level: PRE_STAGING_READY candidate. Not PRIVATE_BETA_READY. $0 spent in this round. Handoff: `docs/CONTINUATION_HANDOFF.md`.**

- Deployed code on pre-staging: `67a0765` (deploy-worker 38083162363, migration 035). Rollback point: `8ce71c0`.
- **G0**: truth vocabulary in code; LIVE requires production → **0 LIVE**; agents 52 = REAL_SERVER_VERIFIED 23 · UNIT_TESTED 6 · IMPLEMENTED 8 · BLOCKED 4 · NOT_IMPLEMENTED 11; skills 427 = REAL_SERVER_VERIFIED 102 · UNIT_TESTED 24 · IMPLEMENTED 28 · BLOCKED 9 · NOT_IMPLEMENTED 264. Truth matrix 36 rows (`TRUTH_MATRIX.json`): 25 REAL_SERVER_VERIFIED, 3 UNIT_TESTED, 3 BLOCKED, 5 NOT_IMPLEMENTED; no customer-visible feature without real-server evidence. Audit: `docs/G0_AUDIT_2026-10-10.md` (7 findings fixed, 6 open).
- **G1**: release policy (NOT_RUN ≠ PASS; mandatory checks block READY), durable stage rows (`build_stage_results`), forward-only phases, legacy/patch paths 410 on staging/production.
- **G2**: visual QA desktop+mobile with screenshots; layout rules enforced (0 false positives on stored products); contrast/labels advisory (real WCAG defects in 3/5 working products — founder decision).
- **G3**: write-ahead cost ledger (in-flight call = bounded unknown exposure), Gemini thinking metered, unit economics report.
- Real-server evidence (free): free checks 18/18 (38083312245); gate-replay 0/55 blocking (38083647077); verify-replay policy agrees 12/12, 5/5 current products READY (38083686082); economics (38083624196).
- Ledger economics (60 days): 32 builds, 11 READY (34%), cost per successful build $0.153, 53% of spend on failed builds, gemini-3.8-flash 41% call success.
- **Not run**: 10-build paid Golden E2E acceptance gate (budget unverified until Gemini invoice reconciliation); crash and backup runs on the current code.
- Tests: local 1167 passed, 9 failed + 14 errors = environment baseline (fastapi/boto3 absent); CI green up to `67a0765`.

## Update 2026-10-10 21:30 Asia/Jerusalem — Executive directive: task 0 (audit access) + P0 build reliability (deterministic part)

**Level: unchanged — PRE_STAGING_READY candidate. Paid testing frozen: no verified budget remainder until the Gemini bill is reconciled (directive budget policy). No money spent in this section.**

- Commits (fast-forward to the active branch, CI green each): `f4b80ba`, `f39bec9`, `e573ab5` (deployed: deploy-worker 38071999051; free checks 38072386506 16/16 PASS). Rollback point: `f90accb`.
- Audit access: `docs/AUDIT_ACCESS.md` (repository, active branch vs. old default `main`, servers, truth documents, evidence runs).

| P0 item | State | Evidence |
|---|---|---|
| 1 repair sees all relevant source, incl. large files | VERIFIED on real data | gate-replay 38071513038: entry file in the repair prompt for 44/44 stored versions; all code files for 43/44 (97.9% of code chars); the one omission (a >16k test file) is included when a failure names it (`focus_paths`, unit-tested) |
| 2 a repair that worsens the product is discarded | TESTED (unit) + seen live 2026-10-09 | `autonomous_core.progress`, tests `test_repair_stop_loss.py` |
| 3 good version kept before each repair, rollback | IMPLEMENTED + TESTED; not yet in a real build | every verified candidate stored as `build-rounds/<build>/<round>-<sha>.zip` with decision/progress (`round_snapshots` evidence); loop rolls back to the best |
| 4/5 checks while files are produced; cross-file consistency | VERIFIED on real data (no false positive) | `consistency_gate.py` (syntax, local import names, page/acceptance routes vs server, assets, manifest) runs before the sandbox, ON by default; replay: 0 blocking findings on 44 stored working versions |
| 6 usability/a11y/security/performance/design checks | PARTIAL | a11y advisories (labels, lang/dir, alt) — 17 on stored versions; security scan + model review existed; no automated performance or design scoring |
| 7 focused repair from real errors | IMPLEMENTED | consistency failures give `file:line` + fix before any sandbox run |
| 8 no READY while mandatory acceptance fails | TESTED | `tests/test_release_blocks_on_failed_acceptance.py`; failure message now names the checks still failing |
| Acceptance gate: ≥10 diverse Golden E2E builds, ≥90% | **NOT RUN** | needs paid builds; blocked by the budget policy until the Gemini bill is reconciled |

- Free re-verification (verify-replay 38072167057): the 12 newest stored versions through the current production chain without the model review — **5/5 versions built by the current pipeline PASS** (incl. today's READY builds); 7 older versions (built before behavioural acceptance / preview contract v2) FAIL the stricter gates, as expected.
- Tests: local 1127 passed, 9 failed + 14 errors = baseline (environment); regression guardian 0 problems; CI green.

## Update 2026-10-09 20:10 Asia/Jerusalem — Autonomous Completion Directive: Agent OS, self-testing platform, build reliability, cost truth

**Level reached: PRE_STAGING_READY candidate (pre-staging deployed and verified on the real server). Not PRIVATE_BETA_READY, not PUBLIC_BETA_READY, not production.**

**Commits** (task branch `claude/g0-baseline-2026-10-09`, fast-forward merged to `milestone/pre-staging-2026-10-05`, no force push)
- Start of this program: `d1c7482` (= rollback point). Final, deployed: `bdc5e9c` (deploy-worker 37965865051; free checks 37966155212 16/16 PASS).
- Merged in order: `724705d` Agent OS/Skills OS + migration 034 · `d57ebd2` agent-graph checks · `c4cdb4a` router fitted output · `9feb3bb` progress-aware repair, tolerant JSON, decoded-JSON text match · `2b4bafd` crash-safe cost ledger · `54620a4` · `67392df` relative dates / no special-casing / review ranking · `20b4bcc` thinking tokens metered · `039574f` gemini-3-8-flash `reasoning_effort=low` · `bdc5e9c` repair sees the main file + evidence refresh.
- Migrations: 30 applied, latest **034 `agent_runtime`** (additive: `agent_runs`, `agent_tasks`, `agent_handoffs`, `agent_memory`, `platform_check_results`). Rollback: code → `git revert` to `d1c7482` and redeploy; 034 needs no down-migration (new tables only, nothing reads them when the recorder is off: `OMNI_AGENT_RECORDER=0`).

**Agent OS / Skills OS (computed by `python -m omni_prod.agent_os.audit --write`; CI fails on inflation)**
- Agents 52: LIVE 30 · PARTIAL 7 · NOT_CONFIGURED 1 · NOT_IMPLEMENTED 11 · BLOCKED 3. Skills 427: LIVE 132 · PARTIAL 29 · NOT_CONFIGURED 1 · NOT_IMPLEMENTED 257 · BLOCKED 8. Registry: `AGENT_OS_REGISTRY.json`, `docs/AGENT_OS_REGISTRY.md`; matrices `PLATFORM_CAPABILITY_MATRIX.json`, `PLATFORM_REGRESSION_MATRIX.json` (17 areas), `GOLDEN_E2E_MATRIX.json`, `FAILURE_INJECTION_MATRIX.json`.
- LIVE = implementation + fresh real-server run whose code is unchanged since (digests in `omni_prod/registry_evidence_lock.json`). Every real build now writes a durable agent task graph; paid run 37961193099: 14 agents SUCCEEDED, independent verification links (quality gate verifies release/acceptance/browser/security/cost/QA), no self-verification, no open tasks. Recovery closes the lost worker's run as `superseded`.

### 1. Implemented and independently verified (real server, current or named commit)
- Free checks 37966155212 (`bdc5e9c`) 16/16: migrations, builder health, 42 versions intact, demo/publish refused, private preview (anonymous 401), owner token, share link only while shared, data survives restart and new version, queued/running cancel, journal, scoping, agent graph closed for a cancelled build.
- Golden SaaS build 37961193099 (`039574f`): discovery → approval → build READY (2 repairs) → browser check → QA review → preview → behavioural acceptance PASS (7 checks, 5 acceptance IDs) → restart; **settled $0.105302 at metered usage incl. thinking tokens**.
- Crash recovery 37954236866 (`2b4bafd`): worker SIGKILLed at the 2nd model call → requeued once → READY; ledger holds both workers; **settled = ledger sum ($0.070368)**. Repeated in 37962802899 (`039574f`): recovery + settlement PASS again ($0.199043 = ledger), but that build then failed verification (see 4).
- Backup/restore 37962179844 (`039574f`): restored into empty PostgreSQL 18, 42/42 versions rebuilt from artifacts, 14/14 preview data files, 34 migrations equal.
- Failure injection: 16/17 PASS (14 unit/integration + 2 real-server: worker kill, deploy during build); invalid OAuth BLOCKED (no generated-app OAuth).
- Regression guardian + capability auditor run in CI (`v24-ci`) on every push.

### 2. Implemented, awaiting external live verification
- `bdc5e9c` repair prompt includes the main file (>16k chars) and files named in failures — unit-tested, deployed, **no paid build run on it yet** (budget).
- Modification (change) flow: last real run 2026-10-08 (`mod_c14435dc`); not re-run on this code.

### 3. Blocked by a named credential/service
- OpenAI: HTTP 429 "no credits remaining"; Anthropic: HTTP 400 "credit balance too low" — every build falls back to Gemini; cross-provider review/repair diversity unavailable.
- Exact Gemini spend reconciliation needs the Google AI Studio / Cloud billing page (founder access).
- Image provider not configured on the worker; no commercial video/voice/music provider contracted.

### 4. Not implemented / open defects
- Build reliability is not yet acceptable: 7 paid builds today on evolving code → 2 READY (37950195508, 37961193099), 5 failed after 5 repairs; each failure was diagnosed and fixed (see commits) but the latest fix set has only 1 paid success; the crash-stage build (book list) failed verification on `039574f`.
- Generated-app sign-in/roles, automation, 2D games, media pipeline: NOT_IMPLEMENTED (agents/skills say so).
- The call in flight at a worker crash cannot be metered (provider may bill it).

**Cost truth correction**: Gemini's OpenAI-compatible usage reports thinking only in `total_tokens`; until `20b4bcc` metered cost excluded it. Spend audit 37966168410: QA guard (all-time, what the $10 cap counts) **$4.527** + rehearsals outside the guard ≈ $1.81 → **≈ $6.34 metered**. Conservative upper bound (gemini-3.8-flash pre-fix calls at worst case, +$1.93): **≈ $8.27 of $10**. Paid testing stopped; remaining is ≈ $3.66 metered / ≈ $1.73 conservative.

**Tests**: local full suite 1108 passed, 53 skipped, 9 failed + 14 errors — identical to the baseline (fastapi/boto3 absent locally); regression guardian 0 problems; CI v24-ci, V11 Overlay CI, Neon bootstrap CI green on every merged commit.

## Update 2026-10-09 14:45 Asia/Jerusalem — merged to pre-staging and verified on the real server (founder approval 13:38)

**Status of this package: deployed to pre-staging, real-server checks passed with named failures below. Not LIVE, not production.**

**Merge and deploy**
- Rollback point (active branch before merge): `9db2d53294b15ce1ab929251be16ce7f0ad37c53`.
- Merge = fast-forward pushes, no force, no history rewrite: `9db2d53..efd8d9d` (the approved package), then fixes found by the checks: `89949e5`, `2afaa22`, `38f7a26`, `c49ebff`, `697245d`, `301d631`, then workflow-only `224171f`, `4ef5378`.
- Worker deployed at `301d631` (Deploy build worker 37924206187: drain 4 s, migrations, preview-data self-test PASS, browser probe PASS, sandbox PASS, queue PASS). Vercel `dpl_CZpf3HNimghmxQMyhxP5owTr3nef` READY on `301d631`; the deployed `app.js` contains the stop/log/offline/data-note code. No Vercel runtime errors in the last hour.
- Migrations: 27 applied, latest 031 (`build_cancel_and_events`); the three new columns and `build_events` present.

**Real-server checks** (workflow `postdeploy-checks`, synthetic account `qa-postdeploy-*@example.com`, API code of the deployed image served on the worker host against the real Neon/Upstash/R2/preview worker/Caddy; the Vercel URL itself is behind Vercel Authentication and only its assets/routes were fetched)
- Free stage, run 37924447917 — all PASS:
  - migrations; builder health (1 build worker idle, sandbox runner 200);
  - existing data: 6 projects, all 24 versions loaded from R2 and checksummed, 0 failures;
  - demo builds → 410, every promote → 501 `publish_not_available`;
  - projects list + journal endpoint;
  - preview creation (`data_storage=persistent`); data survives a preview restart (`v1:2` → `v1:2`) and a new version (`v2:2`);
  - queued build stopped via the API → `cancelled`, reservation RELEASED;
  - running build (claimed by the real worker with a stop request) stopped before any model call: `cancelled_by_user`, 0 model calls, spend 0, reservation RELEASED;
  - journal readable incrementally (`after=`), latest build restored, cancel via another project → 404.
- Paid stage, run 37924920646 — one build, model ceiling **$0.15** enforced (binding: reserved 0.50, effective 0.15):
  - discovery (recommend mode) → plan → approval → build `bld_fde8abb01e4d4085aa180282e6026fb4` → **ready**, 5 repair rounds, version `v_bd07926c05d64deb`;
  - browser check inside the build: passed (1 form, 0 findings); QA model review: 3 rounds, last with 0 blocking;
  - live journal shows phases, agents and each test round;
  - preview RUNNING, `data_storage=persistent`, acceptance report **stored**, page answers 200 afterwards, restart RUNNING.
  - **Exact paid cost: $0.1209** (16 model calls, 110,365 input tokens; settled to reported tokens × catalog price; Gemini only).

**Real-server failures found and fixed during the checks (no mocks, no fallbacks)**
1. Every discovery-based plan was blocked (`can_build=false`): the brief text 148AI writes ("clear message", "Logo") triggered messaging and image capabilities. Fixed in `c49ebff` (detection reads the user's words + the sign-in decision); tests `tests/test_brief_capability_detection.py`. G2 had never been exercised end-to-end before this.
2. A build enqueued while the worker was stopped for a drain was taken by the stopped worker's open Redis read and stayed QUEUED with credits reserved (`bld_a99ca1119c8f445aa4f6243c330d6a46`, cancelled at $0). Fixed in `697245d`: the janitor re-dispatches QUEUED work missing from the queue after 3 minutes; tests `tests/test_janitor_redispatch.py`.

**Failures still open (named, not hidden)**
- **Behavioural acceptance of the paid build: FAIL** (release not eligible). The model-written acceptance plan vs the generated app: create → HTTP 400, page text mismatch, delete step unresolved. It runs after the preview starts and does not feed the repair loop yet.
- **Acceptance demands `auth`/`role` checks even for an approved no-sign-in product** (`acceptance_scope` only exempts `integration`), so such a product can never be release-eligible.
- **Settlement is not "actual usage only" in the customer ledger**: the provider reports tokens but not cost, so the reservation settles at its conservative $0.50 (`CONSERVATIVE_RESERVATION`). The QA budget counts the measured $0.12.
- **Public previews are found and scanned by internet bots within minutes** (router log: `/application.yml`, `/.gitconfig`, GraphQL probes). The hostnames are published in certificate-transparency logs (on-demand TLS), so an unguessable URL is not private. Data entered in a preview must be treated as public until previews get access control.
- Cancel/live log cover builds, not changes; no resume after a worker crash; no backup/restore of product data; the Vercel edge could not be exercised with a session from this environment.

**Tests**: local full suite 1023 passed, 53 skipped, 9 failed + 14 errors — identical to the baseline (environmental: fastapi/boto3 absent locally); CI v24-ci, V11 Overlay CI and Neon bootstrap CI green on every merged commit.

**QA spend**: database-counted builds/changes ≈ $3.43 (incl. this build's $0.12) + rehearsals $1.74 → ≈ **$5.17 of $10**; remaining ≈ $4.83. The customer-ledger view of the same builds (conservative settlements) is higher and is not a cost.

**Next (not started; section 21 waits for the founder)**: fix the two acceptance defects above, preview access control, then a founder session in the workspace.

## Update 2026-10-09 10:20 Asia/Jerusalem — stop + live log, durable preview data, no fake publish (task branch, awaiting integration)

Task branch `claude/g0-baseline-2026-10-09` at `da8d952` (CI v24-ci, V11 Overlay CI and Neon bootstrap CI green). **Not yet on the active branch**: the fast-forward to `milestone/pre-staging-2026-10-05` (which deploys the worker and applies migration 031) waits for the founder's go-ahead in this session. Worker idle at the check (worker-diagnostics 37898263049: last job 00:55 UTC).

**Implemented and independently verified (locally / CI; not yet deployed)**
- **Neon bootstrap includes 030 and 031** (`0159126`): the fresh-Postgres CI that failed on G2 (37867037351) passes again; locally 27 exact migrations verified.
- **Stop a build (directive §10)** (`3f2dd65`, migration 031).
  - Queued build: cancelled at once by the API, reservation released, the worker's claim then fails.
  - Running build: the worker checks before every model call (`RoutedModelGateway.before_call`) and every sandbox run; it ends `cancelled` / `cancelled_by_user`, creates no version, and settles only what was spent (release if nothing paid).
  - Owner-scoped (another tenant gets 404). Tests: `tests/test_build_cancel_and_log.py` (unit + live Postgres, 13).
  - Limit: builds only, not modifications; a stop takes effect at the next step (a model call can take minutes).
- **Live log (directive §12)**: `build_events` in customer language (phases, which agent is working, each test round and its first failure, stop). `GET builds/{id}/events`, `GET builds/latest` (a reload brings back a running build with its stop button).
- **Product data of a preview survives restart and a new version (directive §13)** (`7c1078c`).
  - One directory per project on the preview host (`OMNI_PREVIEW_DATA_ROOT`, mounted at `/data`); stopping/expiring a preview never deletes it.
  - Behavioural acceptance probes now run on a scratch copy of the version (no data mount), so synthetic records never enter the product's data.
  - `project_previews.data_storage` and the workspace say "persistent" or "temporary".
  - deploy-worker gains a $0 self-test with real containers (2 hits → restart as v2 reads 2; scratch reads 0; other project reads 0). **Runs on the first deploy after integration.**
  - Limits: no backup, no size quota, no migration of old data when a new version changes its schema.
- **No fake publish, no shadow builds (gap map #11)** (`da8d952`): in the durable deployment the deterministic builds (demo/v25/v26/v27) answer 410 and the in-memory promote routes answer 501 `publish_not_available` (CI endpoint test).
- **Workspace states (directive §11)**: offline banner, timeout vs no connection vs server error, data-storage note on the preview, track after reload/stop. Checked in Chromium against a mock API (desktop + 390 px, restore, stop → stopping → cancelled, offline): no page errors.
- **G5 rule**: `skill.ui_states` now requires a banner to show again on every message (the library bug); the rehearsal report includes `browser_check`.

**Merge plan and rollback (written before the merge, founder approval 2026-10-09 13:38)**
- Target before merge: `milestone/pre-staging-2026-10-05` = `9db2d53294b15ce1ab929251be16ce7f0ad37c53` (rollback point). Merge = fast-forward push, no force, no history rewrite.
- Migration 031 is additive only: two nullable columns on `build_jobs`, one nullable column (with CHECK) on `project_previews`, a new table `build_events` + index. No backfill, no rewrite, no drop; code at `9db2d53` ignores all of it, so a code rollback needs no schema change.
- Code rollback: push a revert commit of `0159126..409d19d` onto the active branch (never force-push); deploy-worker redeploys the old worker (drain first). The schema stays.
- Optional schema removal (only with a separate approval, after the code rollback): `DROP TABLE build_events; ALTER TABLE build_jobs DROP COLUMN cancel_requested_at, DROP COLUMN cancel_requested_by; ALTER TABLE project_previews DROP COLUMN data_storage; DELETE FROM schema_migrations WHERE version = 31;` — this deletes the live logs only.
- Known window: Vercel and the worker deploy in parallel; until deploy-worker has applied 031 (a few minutes, after the drain), the API's preview status read (`data_storage`) and the new log/stop endpoints can return 500. Worker idle at merge time.
- Preview data directories (`/var/lib/omni-preview/data/p-*`) are never deleted by a rollback.

**QA spend — honest total against the $10 ceiling**
- Recorded in the database (builds + changes, all-time, build-evidence 37864934013): **$3.31**.
- Golden rehearsals do not write the database; their authorized spend from the run annotations: 37700287077 $0.101, 37700596406 $0.098, 37701168910 $0.467, 37701990475 $0.391, 37814985551 $0.210, 37820429767 $0.072, 37840698696 $0.069, 37841459920 $0.125, 37857189740 $0.098, 37858017258 $0.110 = **$1.74**.
- Conservative total ≈ **$5.05 used, ≈ $4.95 left** (list-price authorizations; real provider billing may be lower; model probes not included, a few cents). No spend in this update.

**Awaiting live (after integration)**
- Deploy: drain, migration 031, the preview-data self-test.
- One rehearsal (~$0.10) to see `browser_check` inside the real pipeline.
- Founder session: discovery → approve → build → stop one build → live log → preview data kept after "refresh preview".

**Not implemented (still open for Partner Review)**
- Cancel/live log for modifications; resume after a worker crash (the janitor still fails a lost build after 45 min).
- Data backup/restore of generated apps; visual screenshot QA; publishing to a real target.
- The three Partner Review scenarios (§21) and the partner pack (§23) — need the deployed version and a founder/new-user session.

## Update 2026-10-09 03:15 Asia/Jerusalem — Master directive G0; preview fix; deploy drain; honest QA count

Directive: `docs/MASTER_EXECUTION_DIRECTIVE_2026-10-09_HE.md`. The G0 baseline, deploy-trigger map, ownership and work packages are in `docs/G0_BASELINE_2026-10-09_HE.md`. Claude now works on task branch `claude/g0-baseline-2026-10-09` and fast-forwards the active branch only when tests pass and no build is running.

**Implemented and independently verified**
- **"Nothing responds" in the founder's library preview — root cause and fix (`ab253f7`).**
  - What happened: preview `prv_c242ef7e…` passed every behaviour probe (POST books/members/loans/return, DELETE; router log). `record_acceptance` then raised `IndeterminateDatatype` because the `jsonb_build_object` key was untyped. The launch job tore the container down, and every click after that got 502.
  - Evidence: worker-diagnostics 37861985721 (preview-worker traceback and router log).
  - Fix: `%s::text`, plus the live-Postgres test `test_preview_acceptance_report_is_recorded_on_real_postgres`, which fails with the same error without the fix. Deployed in Deploy build worker 37862267177.
- **A deploy no longer replaces a worker mid-job (directive §18).**
  - How: deploy-worker first runs `docker compose stop -t 1500 worker preview-worker`. That is an RQ warm shutdown: the running job finishes and no new one is taken. It runs before migrations and before any container is replaced. Compose also sets `stop_grace_period` 25m/5m.
  - Proof:
    - worker-diagnostics 37862864855 enqueued `time.sleep(240)`;
    - the push of `51bb631` deployed with Deploy build worker 37862903906;
    - the "drain" notice reads "workers stopped after 213s (worker was running: 1; exit 0)";
    - migrations started only after that (00:08:44 UTC).
  - Cost: $0.

- **Real-browser check of every generated product (directive §17).**
  - What runs: `omni_prod/browser_probe.py`. It needs no knowledge of the product: it fills each form by field type and submits it twice, then reports page errors, dead forms, vanishing feedback and 5xx responses. These become a repairable BROWSER failure.
  - Where it runs: in its own image `omni-browser-sandbox` (Debian chromium + Playwright, `--network none`, read-only, non-root), via the sandbox-runner profile `browser`. Build evidence records `browser_check`.
  - Verified locally on the exact library version `v_f65e904334`: it reports `feedback_disappears`. With the one-line fix it reports no findings. Fixtures for a dead form and a JS error are also caught (`tests/test_browser_probe.py`, 9 tests).
  - Verified on the worker host: Deploy build worker 37864475043 reports "browser-probe: PASS working=[] message-bug=['feedback_disappears']".
  - Not yet exercised inside a real founder build.
- **Drain also held during a real build.**
  - Founder build `bld_e2043208…` started 00:23:52 UTC.
  - Deploy 37864475043 drained for 65 s, and the build finished `ready` at 00:26:04 (build-evidence 37864934013).
- **Approval idempotency (directive §5).**
  - Behaviour: a second approval of the same plan revision returns the existing queued/running/ready build. There is no second build and no second reservation. A failed build still allows a retry.
  - Mechanism: an advisory lock on (project, contract) plus a check for an existing build.
  - Proof: a live-Postgres race test fails without the lock (two builds) and passes with it. The endpoint test is `test_second_approval_of_the_same_plan_returns_the_existing_build` (CI v24-ci 37864338119).
  - UI: in-flight guard and a "this plan is already building" message.

**Implemented, awaiting live (founder in the workspace)**
- **G2 — discovery conversation, ProjectBrief, server-bound approval (`9db2d53`, deployed: Vercel dpl_3Hio8MbtAzFrUucJXCEvswaqttg4, migration 030 applied by Deploy build worker).**
  - Engine: `omni_prod/discovery.py`. Questions include the simple ones (colour, font, style, logo, references, audience, content). They come in small groups. Facts already stated are not asked again. "No preference — choose for me" is recorded as delegated. Contradictions must be decided by the user. Changing an answer drops answers that depend on it. Guided and recommend modes are both available.
  - Brief: immutable revisions with compare-and-set.
  - Approval: bound to user, project, brief revision + fingerprint, contract + fingerprint, budget quote and a 30-minute TTL. It is consumed exactly once.
  - Builds without an approval → 409 `approval_required`.
  - "No sign-in" now means no sessions, a single user and no RBAC floor in the contract.
  - Tests:
    - engine;
    - live Postgres: CAS race, approval used/stale/expired/bound;
    - endpoints: CI v24-ci on `9db2d53`.
  - UI: checked in a real browser against the real engine with a local harness (desktop and 390 px, refresh restore, change → new plan). The deployed `app.js` contains the new flow.
  - **Not yet verified:** a founder session on the deployed workspace (this sandbox cannot reach vercel.app interactively).

**Implemented, awaiting live**
- **QA budget no longer hides cost behind a date.**
  - `OMNI_QA_BUDGET_SINCE` now counts only together with `OMNI_QA_FREE_TIER_EVIDENCE` (a reference to billing proof). Without that reference the count is all-time and the ignored date is recorded in build evidence.
  - With the current Vercel env (no evidence), the counted QA use returns to the all-time figure. Now $3.31 all-time versus $0.60 since 17:12 (build-evidence 37864934013, 2026-10-09 00:30 UTC).
  - The founder can supply the Google billing view to restore the date. Until then the conservative figure stands.

**Found, not yet fixed (G5)**
- The generated library site hides every status message after the first one: `showBanner` leaves `style.display='none'`.
  - Found by running the exact version in a real browser locally.
  - HTTP acceptance cannot see it. WP-G5a adds a real-browser check.

## Update 2026-10-08 23:05 Asia/Jerusalem — Golden E2E #1: full chain from the founder's workspace

**Verified end to end, one continuous path, founder at the keyboard (Vercel Preview `fe84c4d`+, worker `3a4d822`):**
login → project "אתר לניהול משימות" → plan/quote → QA reservation → queue → worker → Gemini (paid tier) →
multi-file repository → sandbox build + tests + repair (2 rounds) → quality 84 → R2 artifact → version
`v_246bae81234e4c39` → live preview with a real Hebrew UI (`prv-1760dedc…sslip.io`) → natural-language change
`mod_c14435dc9baa44bdac784d0c15ed9b85` (READY_FOR_REVIEW 22:04, restored after reload, accepted 22:55) → new
version `v_0bc82ef7b33b4210` with spec A1–A6 (A5 date window → HTTP 400 + DD/MM/YYYY, A6 visible filter +
reset after add; code checked through build-evidence) → ZIP downloaded and opened by the founder (22:59).
Real QA spend counted since paid tier: $0.35.

Still open (honest): the new version reports a bad date with `alert()`, shows the "done" button on finished
tasks and renders via innerHTML of server-escaped text; earlier version double-escaped apostrophes. These are
product-quality gaps for the generation baseline, not pipeline failures. Release acceptance asks for three
different prompts: two done (league rehearsal/founder builds, tasks); one more pending.

## Update 2026-10-08 22:40 Asia/Jerusalem — first founder build with a real UI; change flow; real QA spend

- **Build → Preview with a real UI: PASS (founder, from the workspace).** `bld_f419acd1317a40afab5a7bd287841048`
  (project "אתר לניהול משימות", 21:30–21:35, 2 repair rounds, quality 84) → `v_246bae81234e4c39`; preview
  `https://prv-1760dedc67864c0186aa0cdf945bab0d.151-145-89-132.sslip.io` showed the Hebrew task form,
  filter and table; the founder added tasks, filtered and deleted (screenshots 21:36–21:41).
- Defects the founder found in the generated product (open, platform level): no input validation (due
  date 2356 accepted), ISO dates, an active filter is not shown and hides new tasks; the planner adds
  login/roles requirements although the request says "בלי התחברות". To do: a product-quality baseline
  for generation (validation, clear errors, visible filter state, local date format).
- Fixed: HTTP 500 on approving a plan (`build contract fingerprint mismatch`: title cut at 80 chars after
  a space; 409 for a stale contract); "+ New project" with a name dialog and an empty request box.
- Change flow: `mod_c8d186268bee413e9a03197ee15d8de6` (21:45–21:51) and `mod_c14435dc9baa44bdac784d0c15ed9b85`
  (22:00–22:04) both READY_FOR_REVIEW, but the panel kept saying "sent" and a second click created a
  second candidate. Fixed: latest-modification route + restore after reload, one change at a time,
  30 s request timeout with polling retries (real-Postgres + Chromium checks). Accept/version/ZIP of the
  change: pending founder action.
- QA budget: the cap ($10, founder decision #23) counted reservations ($9.15 "used", 22 rows) while real
  provider cost was ~ $0 before 17:12 UTC (Gemini free tier) and ~ $0.30 after. Founder 22:25: "$10 real,
  all providers together". `qa_used_usd` now counts provider-reported actuals or the spend ledger;
  `OMNI_QA_BUDGET_SINCE=2026-10-08T17:12:00Z` set on Vercel Preview (plain, non-secret).

## Update 2026-10-08 21:00 Asia/Jerusalem — first founder build after the provider work

- `bld_78e2699472054c918890c5daddafc205` (founder, football project, 20:39): FAILED
  `preview_not_ready` after 5 repair rounds: tests passed, quality 82, but "/" was a 382-char page.
  Route events: `gpt-6.1-sol` 429 no credits (skipped, $0), `gemini-3.8-flash` failed twice
  ("invalid model response shape" after 71 s; read timeout at 120 s), so repairs fell back to
  Flash-Lite. Spend ledger $0.163, 16 calls.
- Fixes: Gemini timeouts 300 s (3.8-flash) / 180 s; the shape error now names finish_reason
  and returned keys; the preview smoke test also reads same-origin scripts/styles the page links
  (a UI built by `/app.js` passes) and quotes the start of a rejected page so repair sees it;
  the workspace marks `preview_not_ready` on the generation step. Tests added.

## Update 2026-10-08 20:40 Asia/Jerusalem — providers connected, paid Gemini, measured build cost

- `ff6b4f6` deployed (run 37739774562): quota answers disable a route for the build, refused
  calls release their reservation, budget-fit fallback, failure codes `model_budget_exhausted` /
  `model_unavailable`; OpenAI (`gpt-6-luna`, `gpt-6.1-sol`) and Anthropic (`claude-sonnet-5-5`,
  native Messages API) in the catalog. Deploy notice: all 6 catalog models CONFIGURED (keys from
  GitHub secrets `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).
- Model probe 37814803770 (after the founder enabled Gemini billing, Tier 1 prepay): 3 Gemini
  models **PASS**; OpenAI **FAIL** "no credits remaining" (HTTP 429); Anthropic **FAIL** "credit
  balance is too low" (HTTP 400). Blocked by: prepaid credit in both accounts (founder).
- Rehearsal 37814985551 (Gemini only, Hebrew league prompt): `ready`, 5 repair rounds, quality
  82/pass, 13 calls, 650 s. Measured tokens 26,570 in / 22,248 out; metered at list price
  ≈ $0.075 (flash-lite 7 calls ≈ $0.018, 3.8-flash 3 calls ≈ $0.057). Ledger (conservative,
  calls without reported usage kept at worst case) $0.2096.

## Update 2026-10-08 02:50 Asia/Jerusalem — root cause of bld_ccd38bd0; status review

Full review (Hebrew): `docs/STATUS_REVIEW_2026-10-08_HE.md`. No operation running.

- `bld_ccd38bd00a2f430ab2d92b2962c91544` (founder, 02:36) FAILED `worker_exception` /
  `ModelPolicyViolation: external model budget exceeded`. Earlier hypothesis (worker env
  budget below the reservation) is **wrong**: build-evidence run 37704279388 shows
  `worker_env_budget_usd=0.50, reserved_llm_usd=0.50, effective_budget_usd=0.50`.
- Verified cause: `gemini-3.8-flash` answered `HTTP 429 You exceeded your current quota`
  10 times (~250 ms each, free tier); every rejected call stayed in the ledger at its
  worst case ($0.045–0.050), so 14 calls "spent" $0.4739 while the provider charged $0.
  The gateway also retried the same model twice after a quota 429.
- Status: model routing PASS (events); quota handling **FAIL**; cost reconciliation
  **FAIL** for rejected calls (recorded spend ≠ provider cost). Not fixed yet (review
  action 1). Gemini daily quotas reset at midnight Pacific (ai.google.dev rate-limits).
- `build-evidence.yml` now publishes budget binding, call count, spend and the last 12
  route events (model, ok, latency, cap, error) — amounts only, no secrets.
- Environments checked: branch/Vercel Preview `bd6ea0d` (READY, dpl_95PZjXrvHrWM6UBJQee9bD5XqFg3);
  worker `4712ab7` (same product code); Vercel Production 148aiv28 = `main@e8f2949`,
  148ai = `main@0f7acea`; neither is connected to the worker.
- Superseded below: §3 "Preview router blocked — needs domain control" (the sslip.io edge
  runs since 2026-10-08 00:49).

## Update 2026-10-07 16:10 Asia/Jerusalem — worker host (Queue → Worker)

- Oracle access: SSH timed out because the security-list ingress rule allowed
  `5.29.18.127/32` while the founder's public IP had changed. The founder
  updated the rule; `Test-NetConnection 151.145.89.132 -Port 22` →
  `TcpTestSucceeded: True`; SSH as `ubuntu` works. Host: Ubuntu 24.04.5 LTS,
  `aarch64`.
- Runner: `infra/worker-host/bootstrap.sh` copied to the host by paste and
  checked (`sha256 61cfad15…114c`, 55 lines = the committed file), run with a
  registration token entered with `read -s` (never in chat or shell history).
  Runner `148ai-worker-01`, labels `self-hosted, Linux, ARM64, omni-worker`,
  status **Idle** (GitHub runners page, founder screenshot). Independent
  evidence through the GitHub API: deploy run 37610280053 was picked up by
  runner `148ai-worker-01` and failed explicitly at "Write environment file"
  with the annotation `GitHub secret WORKER_ENV is not set` (the secret did not
  exist yet).
- `WORKER_ENV` created by the founder (values never seen by this session). The
  Vercel copies are `sensitive` and cannot be read back, so the values came
  from their sources: Neon `148ai-db` and Upstash `148ai-redis` (Vercel Storage
  `.env.local`), a new R2 account token `148ai-worker` scoped to
  `omni-artifacts` only, and a new Gemini API key `148ai-worker` (free tier).
  `OMNI_SECRET_KEY` is deliberately not set on the worker: the build path
  shares no secret with the web app (control-plane tokens are minted and
  verified only by Vercel); to be set before production.
- Deploy run 37624945100 (`workflow_dispatch`, `2464394`): every step PASS —
  write env, build images, **apply database migrations**
  (`python -m omni_prod.migrate`), start, worker logged `Listening on`.
  Which migration versions were applied is NOT VERIFIED from here (job logs
  are blocked by the egress proxy).
- Queue → Worker: "Listening on" proves the worker started, not that it
  consumes the queue. Added a deploy step that enqueues a side-effect-free
  probe job (`socket.gethostname`) on `omni-builds` through the same Redis and
  passes only if the running worker container on this host executes it.
  Checked locally against a real Redis server and RQ 2.12.0 (source from
  GitHub): PASS when the worker runs; FAIL when the executing host is not the
  expected container; FAIL (status `queued`) when no worker runs. Status:
  IMPLEMENTED, result pending the deploy run of this commit.
- Vercel: `2464394` READY on 148aiv28 (`dpl_8PdrfGMYy6CRYxRXvTCLQJFriApT`).
- Duplicate Vercel project **148ai disconnected from Git** by the founder
  (16:54, 148ai → Settings → Git → Remove Connection; project kept, not
  deleted). Verification: the push of this STATUS change must create a
  deployment on 148aiv28 only, none on 148ai.

### 16:50 — probe result, diagnosis, fix

- Deploy run 37625977649 (`8365b33`): steps 1–7 PASS, the new probe step
  FAILED: `job ee96cb33… status=queued executed_on=None
  expected=175a9b4f3ac1` (annotation). The probe did its job: the worker
  logged `Listening on` but did not execute the job.
- Diagnosis on the host (founder ran read-only scripts over SSH, outputs in
  screenshots): worker container up, no restarts, log ends at `cleaning
  registries`; queue 0, intermediate 1 (the probe id had been moved out of the
  queue but never executed); Upstash reports `redis_version 8.4.0`. Upstash
  wakes blocked BLMOVE/BLPOP clients correctly: after 6–91 s of blocking,
  plain/MULTI/non-transactional pushes, 60 s and 405 s timeouts all woke in
  ~5 s. Three fresh RQ 2.12 workers (default, with scheduler, ttl 60) on
  temporary queues each executed a job in 0.7–1.5 s.
- **Queue → Worker: PASS on the running worker.** The unchanged probe run
  against the live worker (container `175a9b4f3ac1`, up ~30 min): `status=
  finished executed_on=175a9b4f3ac1 expected=175a9b4f3ac1
  enqueued_from=3d8677914941` (a different container). Registries before the
  probe: started 0, finished 0, failed 0, so the first worker run executed no
  earlier queued jobs (no unintended provider calls).
- Cause of the deploy-time failure (reproduced locally on real Redis, not
  proven on Upstash): a consumer blocked in BLMOVE that never reads its reply
  takes the next pushed job. With a frozen blocked consumer and a plain RQ
  worker as deployed, the probe ends exactly as on the host (`status=queued`,
  queue 0, intermediate 1). The likely source on the host is the previous
  container's BLMOVE still registered after `docker compose up` replaced it.
  RQ's intermediate-queue cleanup would later mark such a job FAILED ("stuck in
  intermediate queue"), so a real build enqueued in that window would fail.
- Second finding: the RQ scheduler (enabled, but nothing uses scheduled jobs)
  polls Redis every second, ~4 commands/s ≈ 10M/month, against Upstash's free
  500K/month.
- Fix (`omni_prod/worker.py`): scheduler disabled; dequeue wait bounded to
  120 s (`OMNI_WORKER_TTL_SECONDS`, default 135; ~86K idle commands/month);
  before consuming, the worker pushes a decoy id (no job behind it) to the
  front of the queue and reports whether a stale consumer took it (bounded to
  3 rounds; untaken decoys are removed; RQ skips and cleans ids without a
  job). Real-Redis check: with a frozen consumer the old worker loses the
  probe, the fixed worker logs `stale consumers absorbed before start: 1` and
  executes it; without one it logs `0`, leaves no decoy and no scheduler keys.
  Tests: `tests/test_worker_entrypoint.py` (8, stdlib). The deploy run now
  also publishes the worker's start-up lines as annotations.
- **Result, deploy run 37631079254 (`5cd8412`): every step PASS, including
  the probe right after the worker container was replaced** — `PASS job
  2b778f2e… executed by worker b186ba0f… in container 72f63493b9ae on this
  host`; start-up: `worker ttl 135s, dequeue wait 120s, scheduler disabled`,
  `stale consumers absorbed before start: 0`. CI on `5cd8412`: `v24-ci` and
  `V11 Overlay CI` PASS. Honest reading: no stale consumer appeared on this
  replacement, so the earlier deploy-time loss is explained by reproduction,
  not observed twice on Upstash; the absorber stays as a guard and reports
  on every start. **Queue → Worker: PASS** (running worker and right after a
  deploy).

### 17:00 — preparing Quote → Budget Reservation

- Vercel Preview (148aiv28, target `preview` only, type plain, non-secret,
  set through the Vercel API): `OMNI_ENV=staging`, `OMNI_QA_BUILD_MAX_USD=0.50`,
  `OMNI_QA_BUDGET_TOTAL_USD=10` (founder caps), `OMNI_EXTERNAL_BUDGET_USD=0.50`,
  `OMNI_EXTERNAL_CALLS_PER_BUILD=40`, `OMNI_ZERO_COST_MODE=0`,
  `OMNI_ALLOW_EXTERNAL_FALLBACK=1` (same model policy as the worker's
  `WORKER_ENV`). `OMNI_ENV=staging` changes nothing else in the app (every
  other check compares with `production`). Takes effect with the next Preview
  deployment.
- Bug found before first use: the "Internal entitlement" workflow wrote `.env`
  from `WORKER_ENV` only, without the host sandbox secret, so `docker compose`
  would refuse to run (`OMNI_SANDBOX_SHARED_SECRET:?required`). Both
  workflows now call one script, `infra/worker-host/write-env.sh` (also strips
  CR from pasted secrets). Checked locally: missing secret → explicit error;
  CRLF input → clean `.env`, mode 600, names only printed.
- Next: Preview deployment with the new settings; INTERNAL_QA grant for the
  founder's 148AI account; founder runs the product flow on Preview (login →
  project → prompt → plan → build) — the plan view must show
  `build_authorization=PRICED` and the build start must create a QA-funded
  reservation.

### 17:20 — Golden E2E #1 on Preview (founder in the browser)

- "Internal entitlement" workflow: GitHub answered 404 to the first dispatch
  (a workflow is dispatchable only after it ran once or is on the default
  branch); it now registers itself with one read-only `list` run on push.
  Two more defects fixed before it worked: GitHub runs steps with `bash -e`,
  so a refusal ended the step before its reason was published, and the
  one-line reason came out empty because docker compose can end stderr with
  blank lines. Run 37633588436 `list` → `[]` (table from migration 029
  exists). Grant for the address in the founder's decision →
  `refused: account not found`; the founder confirmed his 148AI account
  address, grant run 37634623482 → `granted ent_96e09ec0… account
  usr_vrMiNf0RiWiSO_1N INTERNAL_QA staging`. The worker host found the account
  the founder logs into on Preview, so worker and web app share one database.
- **User → Login → Project: PASS** on Preview `a17f52f`
  (`148aiv28-gf5t3gzw8…`): existing account, existing project. Creating a
  second project was refused with `Free project limit reached` (free-plan
  rule, by design).
- **Project → Prompt → Product Plan: PASS** on Preview: roles admin/member,
  data users/items/activity, infrastructure database and sessions
  `SELF_CONTAINED` (demand-driven, no managed services).
- **Product Plan → Quote: FAIL** on Preview: `build_authorization=
  NOT_AUTHORIZED`, blocker "not available on your current plan", approve
  button disabled. Cause: the plan view priced the build as the free customer
  plan while build admission funds an INTERNAL_QA account from the QA budget
  (with the model budget now 0.50 the customer path refuses paid variable
  cost). Fix: one shared decision `_internal_qa_funding()` for the plan view
  and admission; the plan view quotes with the same funding and runs the same
  QA cap checks read-only (`qa_budget.preauthorize_qa_build`, own transaction,
  no writes). Tests: `tests/test_qa_plan_parity.py` (11). The plan view also
  showed raw keys (`st_NOT_AUTHORIZED`, `st_SELF_CONTAINED`); translations
  added, static cache bumped to `148ai-v28-static-4`. Re-verification on
  Preview pending.

### 17:45 — first real build on Preview

- **Product Plan → Quote: PASS** on Preview `24e992a`
  (`148aiv28-8yff44gmw…`): pricing "Authorized" (PRICED), infrastructure
  "built into the app" (SELF_CONTAINED), no blockers, approve enabled.
- Founder approved. **Quote → Budget Reservation: PASS** (the build was
  accepted and reached the worker, which happens only after the QA-funded
  reservation commits in the admission transaction). **Queue → Worker: PASS
  with a real build job**: the worker ran planning, contract, infrastructure
  (self-contained) and assets, then failed explicitly before any model call:
  `AttributeError: 'PostgresCapabilityRepository' object has no attribute
  'create_plan'`. **Worker → Real AI Provider: NOT VERIFIED** (not reached).
- Cause: the worker's capability stage calls `create_plan()` and
  `transition()`; the Postgres repository only had `save_plan()`; all worker
  tests used the memory twin. Fix: both methods on the Postgres repository
  with the memory twin's semantics (idempotent plan, plan drift raises,
  compare-and-set transition, KeyError for a missing requirement).
  **Checked on a real PostgreSQL 16** (all migrations, psycopg from source in
  pure-Python mode) with the Golden E2E #1 contract: prepare →
  READY_FOR_BUILD (10 native requirements PLANNED), prepare again idempotent,
  finalize_native → all VERIFIED, stale compare-and-set False, missing
  requirement KeyError, different plan → drift error.
- Found on the way: `python -m omni_prod.migrate` failed on an empty
  database (`schema_migrations` is created by migration 005, after 001–004
  need it). The runner now creates the bookkeeping table first (same DDL);
  applied all 25 migrations to an empty PostgreSQL 16, second run "none".
- The progress view showed "quality, security and rights gates" as passed for
  this failed build although they never ran (unknown phase was treated as
  "done"). Steps after the failing step are now shown as skipped; static
  cache `148ai-v28-static-5`.
- Tests: `tests/test_worker_repository_parity.py` (10; they fail on the old
  code). Local full run: the same 18 environment-only failures as the clean
  baseline (FastAPI/psycopg not installable here; CI has them).
- Still open: the failure message shows the raw exception text to the
  customer (fine for staging diagnostics, not for launch).

### 18:10 — second real build: first real provider call, stuck status

- Build `bld_2f248e2339cb4ad9848a7ebb5c0c4ed6` (Preview `f39d637`): the
  capability fix held (assets step passed). **Worker → Real AI Provider:
  reached, FAIL**: worker log `ModelGatewayError: all model routes failed:
  model request failed: HTTP Error 503: Service Unavailable` at the
  architect's first `complete_json`. A direct call from the worker host with
  the same key and headers (founder over SSH): `gemini-3.1-flash-lite HTTP
  503 "This model is currently experiencing high demand. Spikes in demand are
  usually temporary." status UNAVAILABLE`. Model codes and prices in the
  catalog were re-checked against Google's models and pricing pages today
  (both exist, prices match).
- **Defect: the failed build stayed "running" in the UI for 20+ minutes.**
  The worker's failure handler crashed with `TypeError: Object of type
  Decimal is not JSON serializable` while writing the FAILED status, so no
  terminal status was ever written. Fix: `omni_prod/evidence_json.py`
  (Decimal → exact string, datetime, enum, set, path; unknown objects are
  never stringified because a repr can carry credentials); terminal
  transitions never fail on evidence encoding (a marker with the reason and
  the evidence keys is stored instead). Used by build and modification
  status writes, capability transitions and preview acceptance. The stuck
  row `bld_2f248e…` remains RUNNING in the database (evidence of the bug; the
  billing resolution ran before the crash).
- Provider overload handling: HTTP errors now carry the provider's own
  message, status and Retry-After; a 429/5xx answer is retried on the same
  route (2 retries, 2 s / 6 s, Retry-After capped at 20 s) before
  escalating; every retry is a separate attempt, budget-checked and recorded
  in the Attempt Ledger; non-transient errors escalate at once; the final
  error lists each route's reason. Catalog: `gemini-3.5-flash-lite`
  ($0.30 / $2.50 per 1M, free tier, official pricing page 2026-10-07) added
  as a second Flash-Lite capacity pool.
- Tests: `tests/test_evidence_json.py` (5), `tests/test_model_transient_retry.py`
  (8). Known open item: no reaper yet for builds whose worker dies mid-run
  (e.g. a worker redeploy during a build) — they would stay RUNNING.

### 18:20 — third real build: real model answer, spec shape

- Build on Preview `f822dd7`: ended **FAILED** with a visible reason
  (`ValueError: requirement id/text required`) — the terminal-status fix
  works (no more endless "running"). The error is raised while validating the
  architect's answer, i.e. after a successful provider call: **Worker → Real
  AI Provider: PASS** (a real Gemini response reached the pipeline; 503
  retries/fallback in place). Next failing transition: **Multi-file Project
  (spec → generation): FAIL** on the spec shape.
- Cause: `_ARCHITECT_SYSTEM` named only the top-level fields; the
  requirement/acceptance keys that `ProductSpec.from_dict` reads (`id`,
  `text`, `kind`, `mandatory`; `id`, `requirement_id`, `text`) were never
  stated, so the model invented its own. Fix: the prompt states the exact
  shape, allowed kinds and id rules; one corrective round sends the
  validator's exact error with the invalid answer; a second invalid answer
  fails the build explicitly naming both errors. Both rounds are ordinary
  recorded, budget-checked calls. Tests: `tests/test_architect_spec_shape.py`
  (4).

### 19:10 — fourth real build: spec PASS, manifest shape

- Deploy run for `67d40be`: start-up reported `stale consumers absorbed
  before start: 1` — the previous worker's blocked request was still
  registered on Upstash after the container was replaced, and the decoy
  satisfied it. This is the first direct observation of the cause found at
  16:50; the probe then passed.
- Build on Preview `67d40be`: the architect's spec was accepted (the shape
  fix works); the generator's repository was rejected with `ValueError: at
  least one verification command required`, 0 repair rounds, billing
  `settled`. Cause: same class as the spec — the generator/repair prompts
  never stated the `.omni/project.json` keys (`build`, `verify[].name`,
  `argv`, `acceptance_ids`), and the parse error aborted the build before the
  repair loop. Fix: `project_manifest.MANIFEST_SHAPE` (parsed by the test
  suite to stay consistent with the parser) in both prompts; an invalid,
  missing or unknown-id manifest is now a failed verification report for
  every acceptance criterion with the parser's reason and the shape as
  evidence, so the repair loop can fix it; nothing runs in the sandbox for it.
  Tests: `tests/test_manifest_shape.py` (5); `tests/test_v22_sandbox_executor.py`
  updated to the new contract (rejected as failed verification, sandbox not
  called).

### 19:30 — fifth real build: sandbox runner had no docker client

- Build on Preview `e2cc4c7`: spec and generated repository accepted (both
  shape fixes hold; the manifest now parses), then the first sandbox command
  failed: `RemoteSandboxError: HTTP Error 500`. New read-only workflow
  `worker-diagnostics.yml` (container state, sandbox image architecture,
  recent worker and sandbox-runner logs as annotations, secret shapes
  redacted; no checkout/compose/restart) — runs 37650560125 and a dispatched
  short-tail run — showed the runner's traceback: `FileNotFoundError: [Errno
  2] No such file or directory: 'docker'` in `sandbox.run_sandbox`. The
  runner image installed `docker.io` with `--no-install-recommends` and ended
  up without a docker binary, while its `/health` still answered 200, so the
  deploy looked green. Sandbox image `omni-sandbox:latest` is arm64; both
  containers running, 0 restarts.
- Fix: the runner image installs `docker-cli` (fallback `docker.io`) and the
  image build fails without `docker --version`; `/health` returns 503 without
  the client or the daemon socket (compose then never starts the worker);
  the worker deploy runs a real snippet through the same signed sandbox path
  and fails unless it ran and the sandbox has no network. Tests:
  `tests/test_sandbox_runner_health.py` (5; the HTTP ones run in CI).
- Deploy of `89e26df`: images built with the client, but the new sandbox
  probe failed: `returncode=2 stdout=''` — the run now reaches Docker, and
  python inside the sandbox could not open the script. Cause (same as the
  M4.9 fix in the local executor, missing in the remote runner): the runner's
  temp directories are 0700 and owned by root, the sandbox runs as uid 10001.
  The runner now makes the source root 0755 and the output root 0777 before
  the run; the probe's failure annotation now includes stderr.

### 20:30 — sixth real build: through the sandbox, stopped at R2

- Deploy of `6a5f8b3`: sandbox probe PASS (`code ran in the isolated sandbox
  (3, 12), network blocked`), queue probe PASS, stale consumer absorbed: 1.
- Build on Preview `6a5f8b3` ended **FAILED** with a visible reason after the
  runner served six signed `/run` calls with HTTP 200 (diagnostics run,
  sandbox-runner log): the generated repository was built and verified in the
  isolated sandbox, then `workspace.commit` failed on Cloudflare R2:
  `InvalidArgument ... Credential access key has length 34, should be 32`.
  **Build → Tests → Verification: reached and executed in the real sandbox**
  (pass/fail of the individual checks is not visible in this failure's
  evidence because the commit came first). **Durable Artifact (R2): FAIL** —
  the R2 Access Key ID in `WORKER_ENV` has two extra characters (value never
  seen; the founder pasted it today).
- Guard: `write-env.sh` now checks every `WORKER_ENV` line for surrounding
  spaces or quotes and the R2 key lengths (32 / 64), reporting variable names
  and lengths only, and fails the deploy before anything starts. Deploy runs
  after the guard report: `OMNI_S3_ACCESS_KEY has 34 characters` (no spaces,
  quotes or non-ASCII characters — the pasted value itself differs). Optional
  secret `WORKER_ENV_OVERRIDES` (NAME=value lines replacing the same keys) so
  one value can be corrected without re-pasting the whole secret. Founder
  action: new R2 token for the worker, two lines in `WORKER_ENV_OVERRIDES`.

### 21:00–22:55 — first READY build; modification path hardened

Transition status after this window (Preview `148aiv28`, branch alias
`148aiv28-git-milestone-pre-staging-2026-10-05-shayflys-projects.vercel.app`):

| Transition | Status | Evidence |
|---|---|---|
| Build → Tests → Verification | PASS | `bld_534476042257416091da55cb4c03ae0e`: verification passed, 1 repair round, quality 86/80 (traceability 100%) — read through `build-evidence.yml` |
| Durable Artifact (R2) | PASS | deploy `storage-probe` write/read-back/delete PASS (worker); build status `ready` with artifact key; web tier lists versions and the founder downloaded the ZIP after the Preview S3 vars were corrected |
| ZIP | PASS | founder downloaded and opened the archive (`app`, `tests`, `README`, `.omni`, …) |
| Modification (rerun on the football version) | PASS | `mod_6ddd35a851a045929528e4bd6acc7768`: source `v_8a6a2c68eab74054` (football, restored with its spec via `/rollback`), `change_request`, 0 repair rounds, verification + gates passed, accepted 20:44:46Z, billing settled $0.0180 (2 calls). New spec adds A8 "removing a team deletes it from the standings and updates the table" |
| New Version (rerun) | PASS | `v_c7fca05db84a4ef3`, 14 files, spec stored with it |
| Modification (first attempt) | PASS (mechanics) / FAIL (base) | `mod_090791ebff9f41f58ae1284f9eeec642`: classified `change_request`, evolved spec, verified, READY_FOR_REVIEW, accepted by the founder 20:12:45Z, billing settled $0.0182 (2 calls). It ran against the wrong base: the failed second product had been committed as the newest version. Fixed: failed builds are no longer versions. Rerun on the football version pending |
| New Version | PASS (mechanics) | `v_38b3f001967c4211`, 13 files, spec stored with it (A7 = the added delete capability) |
| Preview (mechanics) | PASS | 2026-10-08 00:49: `v_88a6539c08574dda` (modification `mod_de87d44898204e4bba5d7d95737e451c`, 2 repair rounds added the preview contract) ran at `https://prv-b5eefafd3ad64bc89af89b2aae43cb0c.151-145-89-132.sslip.io` inside the workspace iframe: Caddy on-demand certificate, router, preview container. |
| Product is a real website | FAIL | The page showed "OK": the generated app is a `LeagueManager` class + unit tests and a handler that returns "OK" at `/`; criteria A4–A7 (responsive UI, RTL, persistence, bundle) are claimed by tests that do not exercise them. Fix: the sandbox smoke test now requires `GET /` to return an HTML user interface with real controls, and the generator must test through HTTP. Not yet re-run. |
| Preview (first launch) | superseded | Founder chose a free temporary address. Deployed: preview-worker, router, Caddy on-demand TLS for `*.151-145-89-132.sslip.io`; deploy check `preview-edge: PASS`; Oracle security list 80/443 opened by the founder. First launch on `v_c7fca05db84a` → `NOT_PREVIEWABLE: preview contract requires schema_version 2, got None` (generated manifest had no preview keys). Fix: preview keys in the shared manifest example + `PreviewReadyExecutor` (contract required, app started in the sandbox and its health path polled; failure is repairable). Needs a new version produced after this fix |

Defects found by real runs and fixed (each with a test):
- R2 credentials: worker key was 34 chars, then SignatureDoesNotMatch, then a
  63-char secret. The founder's browser paste in Chrome returned a stale value;
  values were typed. Deploy now runs a real **storage probe** (write, read-back,
  delete through `S3ArtifactStore`); the 32/64 length check is a warning only.
  `WORKER_ENV_OVERRIDES` reports applied names.
- Sandbox: `compileall` failed on the read-only source mount (`./__pycache__`).
  Bytecode/pytest caches go to tmpfs (`PYTHONPYCACHEPREFIX`); the deploy
  sandbox probe now compiles in the read-only workspace.
- Uncovered acceptance criteria now fail verification (repairable) instead of
  passing and then failing the quality gate with no repair round.
- Planner: the word "משחק" (a football *match*) classified the product as a
  3D game and added unpriced game assets — workaround in the prompt; **not
  fixed** (keyword list in `media_pipeline._GAME_TERMS`).
- Web version list downloaded every archive (`len(v.files)`); uses the durable
  `file_count`.
- Live build never stored its ProductSpec → versions could not be modified.
  Version and spec are now committed in one transaction.
- Modification admission ignored the INTERNAL_QA entitlement →
  `modification_admission.admit_modification` funds entitled accounts from the
  QA budget (same caps/lock as builds).
- Modification/repair agents saw only `{path, chars}`; source files now carry
  their content (bounded 16k/file, 64k total); the evolution prompt requires a
  test and a `verify` entry for every new acceptance id.
- UI kept polling forever on `NEEDS_CLARIFICATION`/`CONFLICT`.
- **Decision change:** a build that fails verification/quality/security is not
  committed as a project version (only a rights-only block still is). The
  previous behaviour made the failed product "current" and the next
  modification targeted it. `/restore` now copies the ProductSpec
  (`/rollback`, used by the UI, already did); real-Postgres test added.
- Spec language: the architect and evolution prompts now write title,
  summary, requirements and acceptance in the request's language (a Hebrew
  request produced an English "what was built" panel).
- Workspace UX (founder feedback): once a project has a version the page leads
  with "what was built" (title, summary, features from the stored spec via
  `/history`), then "what would you like to change"; "new build from scratch"
  is a secondary button. Checked in Chromium with mocked API data.
- Build `bld_8029266bf1164a71995667f89309e832` (founder's second product):
  verification passed, quality 78/80 with zero repair rounds — a root-level
  `test_app.py` was not counted as tests, and quality was never sent to
  repair. Test detection fixed (that build would score ≥ 80); the executor now
  turns a quality shortfall into repairable failures (`QualityAwareExecutor`),
  and a quality-only final failure is reported as `quality_gate_failed`.

Verification commands: `python -m unittest discover -s tests` (925+ tests, the
same 18 environment-only failures as the baseline, no new ones); real Postgres
16 with migrations 001–029: `tests/test_m4d2_live_postgres.py` (14) and
`tests/test_golden_mod_path_live_postgres.py` (2) — build→spec persisted,
QA modification admitted with `funding_source='internal_qa'`, settled.

Added 2026-10-08 01:30: `omni_prod.maintenance` (janitor service) expires
previews and removes their containers, and fails builds RUNNING > 45 min as
`worker_lost` with the reservation released (real-Postgres tests); INTERNAL_QA
accounts get a staging project cap (`OMNI_QA_MAX_PROJECTS`, default 20) and
archived projects no longer count; build failures show a customer-facing
Hebrew/English reason with the raw message under "technical details".

Build `bld_85cc573b473341e9b3f10d248d743ff1` (02:29 UTC+3, Hebrew football
prompt) FAILED after 5 repair rounds: A3–A7 never covered. Causes: the
architect wrote criteria no sandbox test can check (Lighthouse >90, 80%
coverage, browser localStorage, a JS confirm dialog) and the build repair
agent saw only `{path, chars}` (never the manifest). Fixed: architect must
write HTTP/HTML-testable criteria (3–6); build repair uses the bounded content
summary. Not yet re-run.

Workspace UX backlog (founder approved, to do after Golden E2E #1 passes; extended 2026-10-08 20:50):
1. **stop/cancel button** with server-side cancellation between steps, spend stopped, unused reservation released (none exists: no route, no worker check);
2. **build-button lock** while a build runs (founder double-clicked "build" on 2026-10-08);
3. **live activity log** of actions and results (spec written, files written, test A2 failed, repair round 2/5, app started) -- actions, not raw model reasoning;
4. time estimate and progress from past builds;
5. start the preview automatically when a build finishes / a project with a version opens;
6. completion notification (sound/browser, later email);
7. version diff in plain words ("added a delete button");
8. live cost ("12 of 60 credits used");
9. in-app file viewer;
10. failure with a next action (retry, simplify the request);
11. mobile layout for the workspace;
12. original request and Hebrew product description at the top of the project.

Open (superseded items struck): ~~failed builds also commit restorable versions~~; the build row
`bld_2f248e2339cb4ad9848a7ebb5c0c4ed6` is still RUNNING; no reaper; raw
exception text shown to customers; revoke R2 tokens `148ai-worker`,
`148ai-worker-2`.

## Update 2026-10-07 14:10 Asia/Jerusalem

- CI on `089f5bd` FAILED (`v24-ci` run 37549999227, `V11 Overlay CI` run
  37549999186). Job logs are not reachable from this environment (blob
  storage blocked by the egress proxy). Root cause found by reproduction: the
  new HTTP plan-view test flagged the customer's own plan fields
  (`monthly_price_usd`, `annual_price_usd`, `allowed_cost_classes`) as internal
  economics; the internal-key filter now exempts exactly
  `pricing.PUBLIC_PLAN_FIELDS`, with stdlib tests that reproduce it. `v24-ci`
  now publishes failing test names as annotations so future failures are
  readable without logs. Evidence: `6076a5a` — `v24-ci` run 37610280545 PASS
  (full `pytest -q`), `V11 Overlay CI` run 37610279936 PASS.
- Consolidated Preview deployment: `6076a5a` on 148aiv28 READY
  (`dpl_2EghHZo7Wfx887nmq296BUjVd8Ew`); 148ai built and failed again
  (`dpl_7ozoDtVogXEbggoRLiXEiN2M2sta`) — Git disconnect still pending.
- Probe re-run on the deployed code: `self_contained_web_v1`, contract READY,
  `[database:SELF_CONTAINED, auth_session:SELF_CONTAINED]`, quote PRICED,
  unknown `[]`. Plan → Quote stays IMPLEMENTED_NOT_VERIFIED_IN_PREVIEW: the
  Preview is behind Vercel authentication, the shell cannot reach it and the
  Vercel connector is disconnected, so the on-Preview check needs the founder
  (or a reconnected connector). Note: Preview has no model budget configured
  yet, so its quote covers infrastructure and capabilities with a $0 model
  budget; the model/QA budget configuration belongs to Quote → Budget
  Reservation and needs migrations 027–029 applied by the first worker deploy.
- Preview: `92ba0bc` deployed READY on 148aiv28 (the Hobby rate limit lifted
  for that push); `089f5bd` was rate limited again. The fix push is the
  consolidated deployment of everything since.
- Worker host: Oracle instance `148ai-worker-01` exists (founder). The
  self-hosted runner has NOT registered: the queued "Deploy build worker" run
  for `089f5bd` has been pending since 00:04 UTC with no runner. SSH times out.
  Not diagnosable from this environment (no raw outbound TCP, runner/secret
  APIs not permitted through the proxy). Queue → Worker: BLOCKED.

## Golden E2E #1 — current truth, 2026-10-07 04:15 Asia/Jerusalem (supersedes earlier sections of today)

Vercel projects (verified via the Vercel API; names, domains and states only):
- `canonical_vercel_project`: **148aiv28** (`prj_I1ur58ZVxYXQpu1c6W6p5rVZ3q0G`, framework FastAPI, every `OMNI_*` setting lives here).
- `canonical_preview_project`: **148aiv28** — Preview deployments of `milestone/pre-staging-2026-10-05`; last READY `6877d43` (`dpl_AHQ4is6m68oFbeRa52n9nJFfY2Mk`).
- `canonical_production_project`: **148aiv28** — Production `main@e8f2949` (`dpl_9izMa4N2Ca1oMkwLcTM8JqXNgm4f`), domain `148aiv28.vercel.app`.
- **Preview and Production are the same project (148aiv28).**
- Duplicate: **148ai** (`prj_q7vvMotR8xV1VCQjcSEU3A9JFzbX`), domain `148ai.vercel.app`, no environment variables, no framework, every production deployment in ERROR since 2026-09-23, latest deployment ERROR. It is connected to the same repository, so every push costs two deployments. **Git disconnect is pending a dashboard action** (148ai → Settings → Git → Disconnect): the Vercel API available to this session has no disconnect operation and the CLI is not authenticated here; no undocumented workaround was applied. Do not delete the project.

| Transition | Status | Evidence |
|---|---|---|
| User → Login → Project | NOT VERIFIED (from this environment) | Preview host not reachable from the audit shell |
| Project → Prompt → Product Plan | PASS (offline, deterministic) | `python3 tools/golden_e2e_quote_probe.py`: contract READY |
| Product Plan → Quote | **IMPLEMENTED_NOT_VERIFIED_IN_PREVIEW** | Expected: priced quote for the Golden E2E #1 product. Observed (offline, admission-identical arguments, real production provisioner wiring with nothing configured): `infrastructure_profile=self_contained_web_v1`, `required_infrastructure=[database:SELF_CONTAINED, auth_session:SELF_CONTAINED]`, `quote=PRICED`, `unknown=[]`. Preview still runs `6877d43` because every push since `ca548a1` was answered "Deployment rate limited — retry in 24 hours". Not PASS until the deployed Preview proves it |
| Everything after Quote | NOT VERIFIED | The next first failing transition will be determined only after the Preview check, not assumed |

After the Vercel window resets: (1) one consolidated deployment of the branch head, (2) re-run the probe, (3) verify Plan → Quote on Preview (plan view `build_authorization=PRICED`), (4) only then determine the next first failing transition.

Implemented today (CI evidence per commit in the sections below and in git history):
- **Capabilities are demand-driven** (founder principle, replaces the earlier
  `OMNI_BUILD_INFRA_PROFILE` switch, which no code reads any more; the Preview
  variable of that name is unused and may be deleted in the dashboard). The
  contract includes only infrastructure the product asks for: persistence and
  sessions are embedded SQLite (`SELF_CONTAINED`) unless a managed database is
  required; uploads → object storage, reminders/cron → scheduled work,
  email/SMS/webhooks → outbound, each `PLATFORM_MANAGED` with a real quote.
  148AI's own artifact storage (R2) never adds product storage. Contracts that
  ask for all five managed kinds are byte-identical to before (fingerprints
  compared old vs new code). Acceptance requires `integration` only when the
  contract needs outbound, scheduled work or an external integration; the
  lineage SQL feeding this was executed on a real Postgres 16 with every
  migration. Tests: `tests/test_demand_driven_infrastructure.py` (founder
  cases 1–4, storage separation, acceptance scope, lookup, plan view).
- **No internal economics in customer views** (decision #29 extended): build
  status and modification status evidence pass through
  `strip_internal_economics`; the plan view reports `build_authorization`
  (PRICED / UNKNOWN / NOT_AUTHORIZED), `credits_required` and the customer
  allowance instead of provider USD; admission 402 details name unpriced
  capabilities without internal pricing bases, margins or QA budget numbers;
  the build-start response returns credits, not economics; legacy live-build
  responses no longer include routing cost events; the UI shows credits and
  verification only. Tests: `tests/test_customer_economics_views.py`.

## Golden E2E #1 transition truth — 2026-10-07 02:45 Asia/Jerusalem (corrects the 2026-10-06 audit)

The 2026-10-06 audit named Queue → Worker as the first failing transition by
code inspection, assuming admission succeeds. Reproduced evidence shows
admission fails earlier, at Plan → Quote.

| Transition | Status | Evidence |
|---|---|---|
| User → Login → Project | NOT VERIFIED (from this environment) | Preview host not reachable from the audit shell |
| Project → Prompt → Product Plan | PASS (deterministic, offline) | `python3 tools/golden_e2e_quote_probe.py`: contract `READY` for a task-tracker prompt |
| Product Plan → Quote | **FAIL on the Preview build before the fix; fixed in code (see the update below)** | Every contract requires 5 `PLATFORM_MANAGED` kinds (database, auth_session, object_storage, scheduled_http, outbound). The configured provisioner prices each kind only from `OMNI_GENAPP_PROVISIONING_MAXIMUM_USD`, which is ABSENT from Vercel Preview (env names listed via Vercel API, values never read). Probe with every Preview variable present in its most favourable valid form: all 5 kinds `provisioning cost not configured; unknown, not zero` → `CostQuoteUnknown` → HTTP 402 `cost_quote_unknown` |
| Quote → Budget Reservation | BLOCKED | Founder account is on the free plan (refused for paid builds by design). Internal QA path implemented; needs migrations 027–029 applied, `OMNI_ENV=staging` + QA caps on Preview, and an INTERNAL_QA grant |
| Queue → Worker | FAIL | No RQ consumer anywhere. Worker host implemented (`infra/worker-host/`); BLOCKED on founder: server, runner token, `WORKER_ENV` |
| Worker → generated-app infrastructure | UNKNOWN | Worker requires all 5 kinds LIVE before any model call. Preview has Infisical, a GENAPP Neon database, GENAPP S3 and QStash variables; none was ever provisioned or verified live; no outbound email config |
| Worker → Real AI Provider | NOT CONFIGURED | No provider key on the worker (Gemini key pending) |
| Build → Tests → Verification → Repair | NOT CONFIGURED | Sandbox runs on the worker host |
| Durable Artifact (R2) | NOT VERIFIED | Preview secret replaced 2026-10-06 22:17; `/r2-diagnostics` check pending (needs the founder's session) |
| Preview → Modification → New Version → ZIP | NOT CONFIGURED | Preview runtime host / `PREVIEW_DOMAIN_TEMPLATE` absent |

- Architecture conflict raised to the founder (Operating Contract, decision
  22): the contract floor requires managed per-product infrastructure, while
  decision #25 makes generated application code standard-library only (it
  cannot use a provisioned Postgres or S3 without drivers). Options and
  recommendation in `docs/DECISIONS_2026-10-07_HE.md` (open question).

## Plan → Quote fix — 2026-10-07 03:40 Asia/Jerusalem (decisions #27–#29)

- Expected: a Golden E2E #1 prompt yields a priced quote. Observed: 402
  `cost_quote_unknown` (5 unpriceable managed kinds). Root cause: every
  contract required managed infrastructure that the stdlib-only app could
  not even use. Minimal fix (founder decision #27): versioned profile
  `self_contained_web_v1`, bound into the immutable contract.
- Implemented and verified:
  * Contract: `database` and `auth_session` with connection mode
    `SELF_CONTAINED`; spec stack "Python standard library / SQLite (sqlite3) /
    Web UI served by the app"; `platform-data` requires embedded SQLite data
    that later requests and a fresh app instance read back. Managed contracts
    are byte-identical (same fingerprints) when the profile is not selected.
  * Quote: self-contained kinds are not quoted (nothing is provisioned).
    `OMNI_BUILD_INFRA_PROFILE=self_contained_web_v1 python3
    tools/golden_e2e_quote_probe.py` → `quote: PRICED`, `unknown: []`, using
    the same arguments as admission (capability quotes required).
  * Worker infrastructure stage: nothing provisioned; evidence lists embedded
    kinds as "not provisioned; verified only by the app's tests and preview
    acceptance" and object storage / scheduled work / outbound as
    `NOT_VERIFIED`. Nothing is reported LIVE.
  * Preview acceptance: the floor comes from the contract (version lineage
    through promoted modifications, scoped to the project), never from
    generated files. Self-contained: `integration` steps are never executed
    or counted and are listed as `not_verified_steps`; an acceptance ID
    covered only by such a step stays missing (FAIL). Unknown profile or a
    failed lookup → strict managed floor. The lineage SQL was executed against
    a real Postgres 16 with all migrations applied: direct build, a
    two-modification chain, a version-id collision across projects, unknown
    version and foreign project all resolved correctly.
  * Image generation (#28): requested only on explicit logo/branding or
    hero/illustration intent (games keep their assets); build evidence
    `asset_capabilities` reports `NOT_REQUIRED` otherwise. Replicate/image
    stays NOT_VERIFIED in the registry.
  * Public pricing (#29): the catalog and every customer subscription view
    carry only customer-facing fields; regression test with a closed field
    list and a forbidden-term scan, mutation-checked against the old payload.
- Configuration (superseded the same day by demand-driven derivation):
  `OMNI_BUILD_INFRA_PROFILE=self_contained_web_v1` was set on Vercel Preview
  only; no code reads it any more.
- **Not deployed yet (BLOCKED by Vercel):** every push since `ca548a1` got
  GitHub status "Deployment rate limited — retry in 24 hours" (Hobby build
  rate limit). Preview still runs `6877d43` (dpl_AHQ4is6m68oFbeRa52n9nJFfY2Mk),
  so none of today's fixes — QA entitlement, dependency gate, budget binding,
  pricing fix, self-contained profile — are live on Preview. Contributing
  cause: a second Vercel project `148ai` is connected to the same repository
  and builds (and fails) on every push, doubling deployment usage. Pushes are
  now batched; the first push after the window resets deploys the branch head.
- Open finding for the founder (not changed, outside the approved scope):
  customer-facing build status (`GET .../builds/{id}` → `evidence`) and the
  plan preview (`economics`) still return internal economics (reservation,
  revenue basis, margin, per-call cost estimates).
- New first failing transition on Preview: Quote → Budget Reservation
  (free plan refused; the internal QA path needs migrations 027–029 applied by
  the first worker deploy, `OMNI_ENV=staging` + QA caps on Preview, and the
  INTERNAL_QA grant). Then Queue → Worker (no worker host).

## Founder decisions implemented — 2026-10-07

- **Explicit INTERNAL_QA entitlement** (decision #24) — migration 029
  `internal_entitlements` (account id + `staging` scope, audited grant and
  revocation), `python -m omni_prod.entitlements`, manual GitHub workflow
  `Internal entitlement` on the worker host. Email allow-list removed. QA
  enabled only with `OMNI_ENV=staging`, never in production.
- **QA budget separate from the customer plan** — `credit_reservations.
  funding_source`. Found and fixed while implementing: `settle()` and
  `release()` moved customer plan counters for QA reservations (a refund or a
  release subtracted spend that was never added; a shortfall was charged to
  the customer plan). QA caps (decision #23: $0.50 per build, $10 total) count
  only `internal_qa` reservations.
- **Dependency allowlist** (decision #25) — `omni_prod/dependency_policy.py`,
  `DependencyGateExecutor` around the sandbox executor (builds and
  modifications): stdlib-only application code, `pytest==8.3.5` for tests,
  no install steps, no Node toolchain; violations return
  `UNSUPPORTED_DEPENDENCY` without starting the sandbox and end a build with
  `error_code=unsupported_dependency`. Drift test ties the image pins to the
  policy. Prompts carry the policy (prompt version changes accordingly).
- **Attempt counters** (section 9) — migration 028: retry / repair /
  regenerate / escalation / fallback counts on every attempt row.
- Evidence: `226d6f7` — `v24-ci` 37544737507 PASS (full `pytest -q`),
  `Neon bootstrap CI` 37544740584 PASS (migrations 001–029 on a fresh
  Postgres), `V11 Overlay CI` PASS. Tests: `test_qa_budget` (18),
  `test_entitlements` (7), `test_dependency_policy` (17),
  `test_attempt_ledger` (13); stdlib failure set identical to baseline.
- Not configured yet (deliberately): Vercel Preview `OMNI_ENV=staging` and QA
  caps. Enabling QA before migration 029 is applied would turn every Preview
  build request into an explicit 503 `qa_entitlement_store_unavailable`; the
  per-build sizing also depends on the open infrastructure decision
  (reservation = model budget + image + infrastructure + retry ≤ $0.50).

## Instrumentation for Golden E2E — 2026-10-07 (founder decisions: `docs/DECISIONS_2026-10-07_HE.md`)

- CI on `ca548a1`: `v24-ci` (full `pytest -q`) and `V11 Overlay CI` PASS.
  `Neon bootstrap CI` FAILED — root cause: migration 027 was not added to
  `infra/staging/bootstrap_neon_empty.sql` (the verifier requires every
  migration verbatim). Fix: `tools/generate_neon_bootstrap.py` (proven to
  reproduce the previous bootstrap byte-for-byte for 001–026, only the
  provenance line differs) regenerated the file; `--check` detects drift.
  Evidence: on `257805f` `Neon bootstrap CI` run 37542833694 PASS (bootstrap
  applied to a fresh Postgres, all 23 migration checksums match, rerun
  refused), `v24-ci` run 37542833739 PASS, `V11 Overlay CI` PASS.
- **Worker budget bound to the reservation** (Budget Reservation → Worker
  invariant, found while preparing staging config): the worker built its
  model budget from its own env, so a VPS budget larger than the Vercel
  admission budget could spend money that was never reserved. Fix:
  `bind_model_budget_to_reservation` lowers (never raises) the gateway's
  whole-build budget to the durable quote's `components.llm_maximum_usd`;
  a $0 reservation blocks every paid call. Recorded as
  `model_budget_binding` in build evidence. Requests without a component
  breakdown (pre-M5) are recorded as `legacy_unbound`.
  Tests: `tests/test_worker_budget_binding.py` (5).
- Implemented, verified locally with stdlib tests, awaiting live run:
  * **Basic stop-loss** — `AutonomousProductEngine.build`: the sandbox is
    deterministic, so a repair that leaves the repository unchanged or
    returns it to an already-verified state stops the loop
    (`no_progress_repository_unchanged` / `no_progress_repository_cycle`)
    instead of paying for identical rounds. `stop_reason` is recorded in the
    build evidence as `repair_stop_reason`. Modification-job repair loop is
    unchanged (out of scope for Golden E2E transition order).
    Tests: `tests/test_repair_stop_loss.py` (5).
  * **Attempt Ledger** — `infra/postgres/027_task_attempts.sql`, `omni_prod/attempt_ledger.py`.
    One row per provider call and per verification run: task type, provider,
    model, served model version, provider request id, trace id, policy /
    routing-policy / prompt / price-catalog versions (content-addressed),
    selection reason, selected candidate, candidate set, fallback rank,
    authorized / expected (NULL until an estimator exists) / metered /
    provider-reported / reconciled (NULL until reconciliation) cost, tokens,
    latency, outcome ok|error|unknown (timeouts are `unknown` and still count
    their full authorized cost), verification class, failure reason,
    final outcome, data-governance fields (training_eligible=false).
  * **Task tagging** — architecture / codegen / repair / classification /
    modification via `TaskTaggedGateway`; sandbox runs recorded as
    `verification` attempts with PASS / REPAIRABLE_FAIL / RETRYABLE_FAIL.
  * Persisted by the worker on every terminal path (`_persist_build_attempts`);
    a ledger write failure is logged and never changes the build outcome.
  * **Migrations on deploy** — `python -m omni_prod.migrate` (checksum-verified
    runner) runs in the worker deploy workflow before the worker starts.
  * **Internal QA budget** — `omni_prod/qa_budget.py` (superseded the same
    day by the explicit entitlement model, see above).
- Not implemented yet: modification-job ledger persistence, stop-loss in the
  modification repair loop, reconciliation process, expected-cost estimator.

## Golden E2E #1 truth audit — 2026-10-06 23:15 Asia/Jerusalem

- Repository truth: working line is `milestone/pre-staging-2026-10-05`
  (HEAD `7b59c3a`; PR #4 `f9174fc` plus 28 later commits). `main` is still
  `e8f2949` (two weeks old). Vercel Production runs `main@e8f2949`
  (dpl_9izMa4N2Ca1oMkwLcTM8JqXNgm4f); Preview runs `7b59c3a`
  (dpl_J5g95XX2uuY4SoWudynPzFxa938C).
- Implemented and independently verified: CI on `7b59c3a` passes —
  GitHub Actions `v24-ci` run 37514462833 (full `pytest -q`, hostile static
  suite, international gate) and `V11 Overlay CI` run 37514462750.
  Live Preview `GET /api/status` returns 200 and reports `live_ready=false`
  (docker gate false, live build switch off).
- Infrastructure matrix (Preview, names only, from Vercel project env):
  Postgres `OMNI_DATABASE_URL` configured; Redis `OMNI_REDIS_URL` configured;
  R2 `OMNI_S3_*` configured (signature failure under investigation, see below);
  QStash `QSTASH_*` configured; Replicate token configured.
  NOT CONFIGURED: `OMNI_ENV`, `OMNI_PUBLIC_BASE_URL`, `OMNI_ALLOWED_ORIGINS`,
  `OMNI_ENABLE_LIVE_BUILD`, any reachable model endpoint (primary defaults to
  `http://127.0.0.1:8001/v1`; `OMNI_EXTERNAL_MODELS_JSON` absent; zero-cost
  mode blocks external spend), `OMNI_SANDBOX_RUNNER_URL`/shared secret,
  `PREVIEW_DOMAIN_TEMPLATE`, preview runtime host.
- First failing transition (by code inspection, reproducible): `POST
  /api/v28/projects/{id}/builds` enqueues `execute_live_build_job` into RQ on
  Redis and returns 202. No RQ consumer (`python -m omni_prod.worker`) runs
  anywhere, and Vercel Functions cannot host it. QStash is used only as a
  generated-app scheduler capability (`managed_web_saas.py`); it is NOT the
  build dispatcher, so "QStash delivery" is not on the build path.
  Status: Queue → Worker = FAIL (no executor). Worker → model = NOT CONFIGURED.
  Worker → isolated sandbox = NOT CONFIGURED.
- Implemented, verified locally (stdlib tests) and awaiting CI: priced
  multi-provider model catalog (`omni_prod/model_catalog.py`,
  `OMNI_MODEL_CATALOG_JSON`) routed by cost/quality per call inside the
  existing `RoutedModelGateway`; 16 new tests in
  `tests/test_model_catalog_routing.py`; stdlib `unittest discover` failure set
  identical before/after (22 environment import errors, no new failures).
- Implemented, awaiting external live verification: worker host
  (`infra/worker-host/`: compose with RQ worker + Docker sandbox runner,
  `bootstrap.sh`, `.github/workflows/deploy-worker.yml` on a self-hosted runner).
  Blocked by: founder-created Hetzner server, runner registration token and
  `WORKER_ENV` GitHub secret; at least one model provider key.
- Known limitation (not fixed): the sandbox image is Python 3.12 + pytest with
  `--network none`; generated apps can only use the standard library at test
  time. Node/FastAPI generated stacks need a richer pinned image.
- Not verified from this audit environment (PyPI and the Preview host are not
  reachable from it): auth E2E over HTTPS, live DB/Redis round trips, R2 write
  with the secret updated 2026-10-06 22:17.

## R2 runtime diagnosis — 2026-10-06 21:49 Asia/Jerusalem

- Implemented and independently verified: authenticated Preview-only read-only
  `/r2-diagnostics` reports credential lengths and 12-character SHA-256 prefixes,
  actual S3 client settings, SDK versions and deployment revision. It never
  returns credentials or performs storage/provider requests. 22 targeted tests
  passed: `python -m pytest tests/test_r2_config_diagnostic.py
  tests/test_r2_storage_signing.py tests/test_replicate_image_test.py
  tests/test_replicate_connection.py -q -p no:cacheprovider`.
- Live evidence: deployment be421cd loaded access prefix `99a6d983e8e3` and
  secret prefix `cba61814b378` in both environment and the actual boto3 client.
  The independently successful local PUT used secret prefix `6abc7f5dbebd`.
  Endpoint has no bucket path; region auto, signature s3v4, addressing path,
  request checksums when_required; boto3 1.43.94 and botocore 1.43.108.
- Blocked: Preview secret value is the old value. Founder must replace only
  OMNI_S3_SECRET_KEY with the locally verified secret; credentials remain
  write-only and are never requested in chat. Image generation is unverified.
- Not implemented in this diagnostic: automatic credential replacement or
  new paid image submission. Production configuration is unchanged.

## Replicate connection — 2026-10-06

- Implemented and independently verified: saved `REPLICATE_API_TOKEN` selects
  the existing prediction-image pipeline; official-model submit uses the
  Replicate model endpoint and input-only body. Existing configured providers
  are preserved. Submission journal, spend authorization and artifact checks
  remain in the existing pipeline. 51 targeted tests pass via
  `python -m pytest tests/test_replicate_connection.py tests/test_m5_media_provider_adapters.py tests/test_v28_148ai_launch.py -q -p no:cacheprovider`.
- Implemented but awaiting external live verification: authenticated
  `GET/POST /api/v28/providers/replicate/check` calls `GET /v1/account`, returns no
  token/account data, and starts no billable prediction. Token verification is
  distinct from generation verification. Preview deployment verification pending.
- Blocked: real image generation still requires the configured durable build
  worker, submission journal and artifact storage; a key alone is not LIVE.
  Full Windows baseline: 818 passed, 28 failed, 58 skipped; failures include
  temporary-directory permission errors and the nested acceptance run. These
  failures predate this change and are not claimed fixed.
  Post-change full run (`python -m pytest tests -q -p no:cacheprovider --tb=short`):
  826 passed, the same 28 failed, 58 skipped; all 8 new tests pass.
- Not implemented: standalone image-generation UI, audio/video/3D through
  Replicate. This change wires images into the existing build capability flow.

Required by `AGENTS.md`. Covers the M1–M3 work, the superseded modifier-engine
stub, and the M4 natural-language product-modification system built on top of
it (see §5 below — M4 uses the vocabulary required by its own directive;
§§1–4 keep the pre-existing 4-category format so this update stays in place
rather than rewriting sections it did not touch). Evidence and exact commands
are in `PATCH_APPLICATION_REPORT.md`. See `GOVERNANCE.md` for which other
documents in this repo are still current versus historical. Last updated
2026-09-24 (M4 section added; M4D.1 atomic expected-version accept
remediation, M4D.2 live PostgreSQL/FastAPI/Redis verification, M4D.2b
exact dependency parity + real worker execution, and M4.9 genuine live
sandbox execution + full accept/rollback lifecycle proof all applied the
same day — see §5). **M4 = VERIFIED_LIVE_INFRA as of M4.9; M5 is now
authorized to begin.**

## 1. Implemented and independently verified

| Capability | Evidence |
|---|---|
| Preview contract v2 parsing, runtime allowlist, `NOT_PREVIEWABLE` | `tests/test_m3_preview_logic.py` (unit) |
| Hardened `docker run` (cpu/mem/pids limits, read-only root, cap-drop ALL, no-new-privileges, tmpfs `/tmp` mode 1777, uid 65534, read-only source mount) | live Docker 29.4.3: `tests/integration/test_live_preview_runtime.py`, `docker inspect` assertions |
| Docker-allocated host port on one interface + `docker port` lookup | live Docker test |
| HTTP health probe; RUNNING only after it passes; crash/timeout → FAILED with exit code + log tail | unit tests (event order) + live Docker test |
| Full teardown (container + workdir) on every failure path and on stop | live Docker test: 0 containers / 0 workdirs left |
| Async build worker: verification + quality + security + rights gates before READY | unit tests (`_run_live_build_job`) |
| `ModifierEngine`: classifies a follow-up against an existing project (`system_bug`/`missing_requirement`/`change_request`/`ambiguous`, reusing `ChangeClassifierAgent`/`ChangeAssessment`) and, for the two free-repair categories, actually re-runs `RepairAgent` + the sandbox `Executor` against the real repository until it passes or `max_repair_rounds` is exhausted | `tests/test_modifier_engine.py` (10 tests; one deliberate mutation of the `change_request` guard confirmed caught, not committed) |
| Billing: settle on spend, release only with no external spend | unit tests against real `model_policy.authorize_model_call` ledger |
| Outbox relay logic | unit tests (fake pool) |
| Frontend async-first build flow with demo-mode fallback | Node `vm` harness run against real `app.js` |
| Regression | 197/197 non-fastapi tests pass (187 pre-existing unmodified + 10 new `ModifierEngine` tests) |

## 2. Implemented, awaiting external live verification

- FastAPI routes: `POST /api/v28/projects/{id}/builds`, `GET .../builds/{build_id}`,
  410 guards on sync build routes, `POST/GET/DELETE` previews — `fastapi`
  is not installable in the build sandbox; routes are compiled + statically
  checked only.
- Migrations 013/014/015 and all repository SQL against real Postgres.
- RQ/Redis dispatch, host-scoped cleanup queues, `python -m omni_prod.build_outbox_relay`.
- Preview runtime on the official `python:3.11-slim` / `node:20-slim` images
  (verified only on a locally imported Python 3.11 image; registry blocked).

## 3. Blocked by a named service / deployment decision

- **Preview router** for `PREVIEW_DOMAIN_TEMPLATE` (wildcard DNS, TLS, proxy
  to `PostgresPreviewRepository.get_route()`) — needs domain control.
- **Schedulers** for `build_outbox_relay` and `PostgresPreviewRepository.mark_expired()`.
- **Worker topology**: preview workers must consume
  `omni-preview-host-$OMNI_PREVIEW_RUNTIME_HOST` in addition to `omni-builds`.
- S3-compatible storage (`OMNI_S3_*`) — required for async builds and previews.

## 4. Not implemented

- Expiry sweep that stops containers (EXPIRED only changes DB state; DELETE cleans it up).
- Live log streaming (needs a distributed logging pipeline).
- Dependency install / image build stage for previews (M4).
- Egress network policy for preview containers.
- Provider-measured token usage (only an authorized-estimate spend ledger exists).
- ~~**`ModifierEngine` execution of `change_request`s.**~~ **SUPERSEDED by M4**
  (§5 below): `CandidateModificationEngine` now runs a dedicated
  product-evolution path (`ProductEvolutionAgent`) for `change_request`,
  instead of forcing it through `RepairAgent`. `ModifierEngine` itself
  (`omni_prod/modifier_engine.py`) is unchanged and still only free-repairs
  `system_bug`/`missing_requirement`; it is no longer the intended
  entry point for modifications.
- ~~**`ModifierEngine` is not wired to any route or worker task.**~~
  **SUPERSEDED by M4** (§5 below): the M4 routes/worker
  (`POST .../versions/{version_id}/modifications` →
  `execute_modification_job`) are the wired path now; `ModifierEngine`
  itself remains unwired, which is fine since M4 does not call it. M4 also
  adds the durable, version-scoped `ProductSpec` this bullet said was
  missing — see `PostgresSpecRepository` / migration `016`.

## 5. M4 — Natural-Language Product Modification

Per the M4 directive's own "STATUS DISCIPLINE": `LIVE` / `VERIFIED` /
`PARTIAL` / `IMPLEMENTED_NOT_VERIFIED` / `NOT_CONFIGURED` / `NOT_IMPLEMENTED`
/ `BLOCKED`. **M4 is not `LIVE`** — nothing in this repository is deployed;
"VERIFIED" below means real code executed against real tests — unit tests,
or (as of **M4D.2**, see below) real PostgreSQL, real FastAPI and real
Redis/RQ, running in this sandbox — not that it has run in production.

**Update, M4D.2 (2026-09-24):** the paragraph below describing `fastapi`/
Postgres/Redis as unreachable in this sandbox was true through M4D.1 and
is **no longer true**: a normal `pip install`/`apt-get install`/`docker
pull` of these packages is still genuinely blocked here (confirmed, not
assumed — see M4D.2's own section below), but real PostgreSQL 16 and real
Redis servers were already present and startable in this image, and real
fastapi/psycopg/redis-py/rq were made importable via a disclosed
git-clone-vendoring workaround. Every route/worker-import-boundary item
that used to read `NOT_CONFIGURED` purely for lack of `fastapi` has been
superseded — see the M4D.2 section under M4D.1 below for what is now
genuinely `VERIFIED` live versus what remains a structural proof or is
out of scope. The paragraph immediately below is kept, unedited, as the
accurate description of the constraint through the end of M4D.1, since
§§1–4 and the M1–M3 sections of this document still operate under it.

Original (M4–M4D.1) framing, unchanged: `fastapi`, live Postgres and live
Redis were not installable/reachable in this build sandbox (a constraint
that predates M4 — see §2 above); every route/worker-import-boundary item
below was `NOT_CONFIGURED` for that reason alone, not because the code was
wrong, and was instead proven by static AST/signature inspection. Full
evidence and exact commands: `PATCH_APPLICATION_REPORT.md` (M4 section).

### By capability (M4A–G)

| Capability | Status | Evidence |
|---|---|---|
| M4A — durable `ModificationRequest` repository (create/get/transition/complete/accept/reject/rollback, optimistic concurrency) | `VERIFIED` | `tests/test_modification_repository.py` (43 tests, fake-pool + real `MemoryProjectWorkspace`, 2 independent mutation tests) |
| M4A — transactional outbox (`modification_outbox`, `FOR UPDATE SKIP LOCKED`, dispatch) | `VERIFIED` (logic, and the enqueue+outbox-row half live — see **M4D.2**) / `IMPLEMENTED_NOT_VERIFIED` (the `dispatch_pending_outbox()` relay path specifically — not exercised live in M4D.2, only the direct-enqueue-succeeds path was) | `tests/test_modification_repository.py::OutboxDispatchTests` (logic); `tests/test_m4d2_live_fastapi_redis.py::LiveRedisRQTests` (live enqueue) |
| M4A — FastAPI routes (propose/status/candidate/accept/reject/rollback) | `VERIFIED` — live, via a real ASGI `TestClient` against real Postgres | See **M4D.2** below; superseded the static-only proof this row previously cited |
| M4A — worker entrypoint (`execute_modification_job`, lazy-imports investor_app internals) | `VERIFIED` (orchestration logic via dependency injection) / see **M4D.2b** for the real-dequeue-and-execute proof of `execute_modification_job` itself | `tests/test_m4_worker.py` (11 tests against `_run_modification_job`); `tests/test_m4d2_live_fastapi_redis.py` (real HTTP enqueue of the real job into Redis, and real `rq.SimpleWorker` dequeue/execution/failure-handling proven using **dedicated test job functions**, not `execute_modification_job` itself — see the correction in **M4D.2b** below); `tests/test_m4d2b_*` (real dequeue and real execution of `execute_modification_job` itself) |
| M4B — versioned `ProductSpec` repository + `project_version_specs` (exact-version scoped, no `update()`) | `VERIFIED` (logic and live — see **M4D.2**) | `tests/test_spec_repository.py`; `infra/postgres/016_durable_modifications.sql`; `tests/test_m4d2_live_postgres.py` (applied for real, read/written for real) |
| M4C — intent routing reused (`system_bug`/`missing_requirement`/`change_request`/`ambiguous`) | `VERIFIED` | `tests/test_m4_acceptance.py::AcceptanceGH/I/J` |
| M4C — dedicated `change_request` path (`ProductEvolutionAgent`, real spec+repo generation, not forced into `RepairAgent`) | `VERIFIED` | `tests/test_product_evolution.py`, `tests/test_m4_acceptance.py::AcceptanceJ` |
| M4D — candidate isolation (never commits to `project_versions` until `accept()`) | `VERIFIED` | `tests/test_m4_acceptance.py::AcceptanceK`; `tests/test_m4_worker.py`'s `workspace.commit.assert_not_called()` |
| M4D — accept / reject / rollback | `VERIFIED` — both the algorithm/concurrency logic AND live PostgreSQL infrastructure | See **M4D.1** (algorithm) and **M4D.2** (live Postgres) below — this row previously read `PARTIAL`, then `IMPLEMENTED_NOT_VERIFIED` for live Postgres; both superseded |
| M4D — optimistic concurrency (expected-source-version semantics) | `VERIFIED` — algorithm AND live PostgreSQL (real advisory locks, real concurrent connections) | See **M4D.1** and **M4D.2** below |

### M4D.1 — atomic expected-version accept (remediation, 2026-09-24)

An independent architecture review of the original M4D `accept()` correctly
identified it as **production-blocking**: it called `workspace.commit()`
unconditionally and only compared `new_version.parent_id` to the expected
source version *after* the row already existed in `project_versions` — so a
concurrent accept could be told "conflict, not accepted" while the
project's real current version had already silently mutated to the
rejected candidate's content. A post-commit check is not sound optimistic
concurrency; the review's own summary — "a modification must NEVER change
the current ProjectVersion and then return conflict" — was correct, and the
bug was real, not hypothetical (reproduced directly by grepping
`workspace.py`: both `MemoryProjectWorkspace.commit()` and
`PostgresProjectWorkspace.commit()` had no compare-and-swap at all before
this fix; `current()` is simply "the most recently inserted row").

**Fix.** `workspace.commit()` (both implementations) now takes an optional
`expected_current_version_id`; the compare against the REAL current version
happens under the same lock (`MemoryProjectWorkspace`'s `self._lock`) or the
same `pg_advisory_xact_lock`-held transaction (`PostgresProjectWorkspace`,
via a plain `SELECT` on the same cursor, immediately before the `INSERT`)
that would perform the write. A mismatch raises `VersionConflict` **before**
any row is written — never audited after. `modification_repository.accept()`
no longer performs a separate pre-check-then-commit-then-post-check
sequence; it opens ONE transaction, shares its cursor with
`workspace.commit(cur=..., expected_current_version_id=...)` and
`spec_repo.save(cur=...)` (which already supported a `cur` parameter for
exactly this), and the whole promotion — status validation, the version
insert, the spec insert, and the final `ACCEPTED` update — is one atomic
unit. This also closes the M4D `PARTIAL` row above: the three/four-
transaction promotion window is gone for the Postgres path (proven via
`FakeConn.transactions == 1` in `test_modification_repository.py`'s happy-
path test). `rollback()` was brought in line the same way for consistency.

`VersionConflict` replaces the old `conflict_detected_at_commit` reason
entirely — there is no longer a "the write already happened, but..." case
to name. `investor_app.py`'s accept route was simplified to match (single
`reason == 'conflict'` check) and re-verified statically (AST parse, no
duplicate routes, `inspect.signature()` cross-checks — same method used
throughout this report for `fastapi`-blocked code).

**What "VERIFIED" means here, precisely** — this is real, not a facade:
- A genuine two-real-OS-thread test
  (`tests/test_m4d1_atomic_accept.py::TrueConcurrencyTests`), synchronized
  with a `threading.Barrier` so both threads are dispatched into
  `workspace.commit()` at the same instant, against the real (thread-safe,
  `RLock`-protected) `MemoryProjectWorkspace` — not a simulated or
  single-threaded race. Stress-run 40 consecutive times with zero flakiness
  before being accepted into the suite (see `PATCH_APPLICATION_REPORT.md`).
  A 10-way fan-in variant proves the same property beyond the minimal A/B
  case.
- Mutation tests against **both** `MemoryProjectWorkspace.commit()` and
  `PostgresProjectWorkspace.commit()`: the expected-version compare is
  temporarily replaced with a mutant that omits it, the exact M4D.1 bug is
  shown to reappear (a stale commit silently succeeds and corrupts
  `current()`), then the real method is restored and re-confirmed correct
  — automated, part of the permanent suite, not a one-off manual check.
- The full required-test list from the M4D.1 directive: staged failures at
  each point in the merged transaction (before the version insert, after
  the version insert but before the spec write, before the final status
  update), retry-after-crash / duplicate-delivery idempotency,
  force-accept (both the real-override and the no-op-when-nothing-to-
  override cases), rollback after an accepted modification, and two
  invariant tests (every promoted version has exactly one spec; a
  failed/conflicted accept never changes `current()`, asserted by object
  identity, not just by id equality).

**What is honestly still not proven, and why.** `PostgresProjectWorkspace`'s
SQL-level guard is proven only against a fake cursor (statement order:
`pg_advisory_xact_lock` → `SELECT` current → compare-then-raise-with-no-
`INSERT`, or `INSERT`) — structurally correct and matches exactly how
`workspace.commit()` already worked pre-M4D.1 (same lock, same statement
shape, just with the compare added), but never executed against a real
Postgres server, because this sandbox has none. The genuinely convincing
remaining step, not done here, is the same class of true-concurrency test
run against **real** Postgres connections and a real `pg_advisory_xact_lock`
under concurrent load — the in-sandbox `MemoryProjectWorkspace` thread test
proves the *algorithm* is correct, not that Postgres's actual lock
semantics behave as assumed under real network/connection-pool conditions.
**M4 is not `LIVE`. This fix is not "production-closed"** — it is
`VERIFIED` at the logic/algorithm level with real concurrency, and
`IMPLEMENTED_NOT_VERIFIED` for the live-Postgres half, exactly like every
other Postgres-dependent path in this report.

> **Update, M4D.2 (below):** the "genuinely convincing remaining step" this
> paragraph describes — the same class of true-concurrency test run against
> real Postgres connections and a real `pg_advisory_xact_lock` under
> concurrent load — has since been done for real. See the "M4D.2 — live
> infrastructure verification" section immediately below for the live
> evidence. This paragraph is left otherwise unedited because it accurately
> describes what M4D.1, on its own, did and did not prove; M4D.2 is what
> closes the gap it identifies. M4 as a whole is still not `LIVE` (see
> M4D.2's own "still not proven" subsection for what remains).

Evidence: `tests/test_workspace_version_conflict.py` (14 tests, the
mechanism), `tests/test_m4d1_atomic_accept.py` (14 tests — 1 intentional
skip pointing at where that scenario is actually covered — the required
list plus the two mutation tests), `tests/test_modification_repository.py`
(unchanged count, 43 tests, `AcceptTests` rewritten for the new design).

### M4D.2 — live infrastructure verification (2026-09-24)

M4D.1 closed the algorithmic gap and was accepted "at the algorithmic/
concurrency-design evidence level"; M4D.2's directive required the
remaining half — actually running against real PostgreSQL, real FastAPI,
and real Redis/RQ, not fakes or structural proofs — and, critically, doing
the environment discovery itself rather than declaring `BLOCKED_BY_ENVIRONMENT`
because these services weren't preinstalled.

**Environment discovery (commands and results, in order):**
- `docker ps` → daemon not running; `dockerd` itself failed to start under
  the default init script (`ulimit: error setting limit (Operation not
  permitted)` — a nested-container privilege constraint), but started
  successfully when invoked directly with `--storage-driver=vfs` and
  properly detached (`setsid nohup dockerd ...`). Docker itself: **usable**.
  `docker pull python:3.11-slim` → `Error response from daemon: Get
  "https://registry-1.docker.io/v2/": Forbidden` — Docker Hub itself:
  **genuinely blocked** by this sandbox's network egress policy.
- `psql`, `pg_ctlcluster`, and a PostgreSQL 16 data directory were already
  present in the image (`pg_lsclusters` showed cluster `16/main` on port
  5432, status `down`). `pg_ctlcluster 16 main start` → **started
  successfully**. This is a real, native (non-Docker) PostgreSQL 16.13
  server, not a stub.
- `redis-server`/`redis-cli` binaries were already present.
  `redis-server --daemonize yes --port 6379` → `redis-cli ping` → `PONG`.
  Real, native Redis 7.0.15.
- `pip3 install fastapi==0.128.2 ...` → `ERROR: Could not find a version
  that satisfies the requirement` (no index). `curl -v https://pypi.org/…`
  → `HTTP/2 403`, header `x-deny-reason: host_not_allowed`, body `Host not
  in allowlist: pypi.org`. PyPI (and `files.pythonhosted.org`, same
  result): **genuinely blocked**, a real, explicit organization policy
  denial, not a technical hiccup — per this sandbox's own proxy runbook,
  not retried or routed around.
- `apt-get update` / `apt-get install python3-fastapi python3-psycopg
  python3-redis python3-rq ...` → `E: Failed to fetch
  http://archive.ubuntu.com/... 403 Forbidden` for every package (`apt-
  cache policy` had shown candidate versions from the image's stale local
  index only, not a live, reachable mirror). Debian/Ubuntu package
  installation: **genuinely blocked**, same network policy.
- **All three installation avenues (PyPI, apt, Docker Hub) were tried and
  confirmed blocked before falling back to anything else** — this is not
  a "not preinstalled, so skip it" conclusion.
- `git clone https://github.com/psycopg/psycopg.git` (and
  `fastapi/fastapi`, `redis/redis-py`, `rq/rq`) → **succeeded**. GitHub's
  git-clone protocol is reachable from this sandbox even though
  `raw.githubusercontent.com`/`codeload.github.com` (plain HTTPS content
  fetch) and PyPI/apt/Docker Hub are not. The real upstream source of each
  package (commits `psycopg@ab5646a`, `fastapi@50113da`,
  `redis-py@722eb64`, `rq@90a67a1`, all cloned 2026-09-24) was made
  importable via a `PYTHONPATH` vendor directory
  (`/tmp/m4d2_vendor`, reproduced by `tools/m4d2_setup_live_infra.sh`,
  written for this directive) instead of a normal `pip install`. One
  additional micro-dependency, `annotated-doc` (a five-line PEP 727 `Doc`
  marker class with zero runtime effect on validation/routing — confirmed
  by reading its one class body, which is byte-for-byte the same as
  `typing_extensions.Doc`, already installed), was re-provided as a
  one-line local shim rather than fetched, since it has no standalone git
  repo. This is disclosed in every affected file's module docstring, in
  `tools/m4d2_setup_live_infra.sh`, and here — not hidden.
- The one deliberate, disclosed substitution beyond that: `boto3`/S3 (used
  by the real `S3ArtifactStore` for repository-content blobs) is also
  PyPI-only and out of scope for M4D.2's Postgres/Redis/FastAPI sections —
  a real, working, disk-backed store implementing the exact same
  `put_bytes`/`get_bytes` interface (`DiskArtifactStore`, in
  `tests/test_m4d2_live_postgres.py`) stands in for it. Nothing about
  Postgres, FastAPI, Redis, or RQ themselves is substituted anywhere.

**Result: M4D.2 `VERIFIED_LIVE_INFRA`** — not `BLOCKED_BY_ENVIRONMENT` —
because genuine, exhaustive effort (three independent installation
avenues, each actually attempted and confirmed blocked, not assumed)
found a real path to real infrastructure.

**C — real PostgreSQL concurrency** (`tests/test_m4d2_live_postgres.py::RealConcurrencyTests`,
3 tests): two genuinely independent `psycopg` connections (proven distinct
by differing real `pg_backend_pid()` values), synchronized with a real
`threading.Barrier`, racing `accept()` for two candidates from the same
`project_id`/source version. FACT, each run: exactly one promotion, the
loser durably `CONFLICT` with `promoted_version_id` left `NULL`, zero
orphan `project_versions`/`project_version_specs` rows, `current()` is the
winner. A 10-way fan-in variant proves the same property at wider
concurrency. A dedicated advisory-lock test takes the *exact* lock id
`PostgresProjectWorkspace.commit()` would (same SHA-256 formula) on a raw
connection, holds it, and proves `accept()` for that project genuinely
blocks until released while `accept()` for a *different* project is
completely unaffected (real serialization boundary, not simulated).

**D — real transaction-rollback** (`RealTransactionRollbackTests`, 6
tests): a cursor wrapper that lets every real SQL statement before a
chosen call number execute for real, then raises — Postgres's own
`conn.transaction()` context manager performs the real `ROLLBACK`, not a
fake one. All three directive cases covered (after the version INSERT/
before the spec INSERT; after the spec INSERT/before the final UPDATE;
"during" the final UPDATE — the UPDATE genuinely executes inside the open
transaction before the simulated crash). FACT, each case, verified via a
*separate* connection afterward: no orphan `project_versions` row, no
orphan spec row, `modification_requests.status` still `READY_FOR_REVIEW`,
`promoted_version_id` still `NULL`. Retry-after-crash and duplicate-
delivery-after-success are also real (same modification id, real Postgres,
no double promotion). `force=True` and rollback-after-accept are exercised
against live Postgres too.

**E — concurrency stress**: 20 repeated 2-way races + 3 repeated 10-way
fan-ins in `RealConcurrencyStressTests`, plus the whole 14-test file run 6
times consecutively (1 development run + 5 explicit stress runs) with
**zero failures, zero exceptions, zero flakiness** across every run.

**F — FastAPI real-path** (`tests/test_m4d2_live_fastapi_redis.py::LiveFastAPIModificationFlowTests`,
5 tests): the real `omni_prod.investor_app.app` (131 routes; the entire
module now imports cleanly under real `fastapi`), served by a real
`fastapi.testclient.TestClient`, with `OMNI_CREATOR_PERSISTENCE=postgres`
so `_v28_pool`/`_v28.accounts` are the real `PostgresAccountService`/
`PostgresSubscriptionService`, and `_v28.engine.workspace` swapped (the
one disclosed substitution above) to a real `PostgresProjectWorkspace`.
Real HTTP round trips for register → create project → propose
modification (real credit reservation via `subscriptions.reserve()`,
really committed to Postgres) → candidate → accept (200, persisted
`ACCEPTED`/`promoted_version_id`, `current()` really advanced) → a second,
conflicting accept (real **409**, `reason: conflict`, `current()`
untouched) → a duplicate accept of an already-accepted modification (real
**422**, `invalid_status`) → reject (real 200, `current()` provably
unchanged, and accept afterward is 422) → cross-account access (real
**403**). Every one of these previously showed `IMPLEMENTED_NOT_VERIFIED`
in this document for lack of a live HTTP call; all now `VERIFIED`.

**G — Redis/RQ real-path** (`LiveRedisRQTests`, 3 tests): confirmed Redis/
RQ genuinely is part of M4's production path (`v28_propose_modification`
calls `omni_prod.queueing.enqueue_build`, real `rq.Queue.enqueue`).
Real HTTP propose → real `rq.Queue` contains a real job (`fetch_job`
returns it, `func_name == 'omni_prod.worker_tasks.execute_modification_job'`,
correct args) → `dispatch: 'enqueued'` (not the outbox-relay
`'deferred'` fallback, proving Redis really was reachable at that moment).
A second test enqueues a small, self-contained real job through the same
real `enqueue_build()` helper and drains it with `rq.SimpleWorker` — real
dequeue, real execution, independently verified by a row the job body
itself writes to Postgres (not merely `job.is_finished`). A third proves
worker-failure recovery: a real job that raises is marked `failed` by rq
without crashing the worker, which then successfully processes a
follow-up job. **Disclosed adaptation**: `rq.SimpleWorker` (in-process,
no fork) is used instead of the default `rq.Worker` (which forks a child
per job) because this test process already holds an open `psycopg`
connection pool at fork time — forking with a live SSL socket open is a
well-known hazard, and it reproduced exactly the predicted failure
(`SSL SYSCALL error: EOF detected`) on the first real run, for jobs left
over from another test. `SimpleWorker` is real, unmodified `rq` code, not
a mock of the queue or the worker; it simply avoids that specific,
test-process-only hazard. The `execute_modification_job` production
entrypoint itself is never actually driven to a classification decision
in these tests, because that requires a live LLM provider — a
pre-existing, already-disclosed constraint (see §2 above) unrelated to
M4D.2's Postgres/Redis/FastAPI scope; the modification lifecycle from
`READY_FOR_REVIEW` onward is instead driven via the real repository
methods (`transition_running`/`complete`) worker_tasks.py itself calls,
which is what sections C/D/E/F above exercise at the HTTP and Postgres
layers.

**H — connection-pool/transaction-boundary check** (`TransactionBoundaryTests`,
2 tests): proven from PostgreSQL's own server state, not application-level
counting. One test captures `txid_current()` immediately after each real
`INSERT INTO project_versions` / `INSERT INTO project_version_specs` /
`UPDATE modification_requests` statement `accept()` issues, on the SAME
connection — all three come back identical, which is only possible if
Postgres assigned them to one transaction (a transaction id is stable for
its own lifetime and assigned lazily on first write). The other confirms
`pg_stat_database.xact_rollback` shows zero for a successful accept() and
`xact_commit` advances by at least one (a genuine, disclosed finding along
the way: `pg_stat_database` flushes asynchronously per backend, so the
first version of this test read the counter before the flush landed and
failed — fixed by polling briefly rather than reading once, left visible
in the test's own docstring rather than silently patched over).

**I — full regression after live-infrastructure verification**: the
combined suite (35 test modules, excluding
`test_m4d2_live_fastapi_redis.py`, which the module's own docstring
requires running standalone since it bakes `OMNI_CREATOR_PERSISTENCE=postgres`
into `omni_prod.investor_app`'s module-level globals at import time) —
**487/487 tests pass, 2 expected skips**, run twice consecutively with
identical results. `test_m4d2_live_fastapi_redis.py` run standalone,
separately — **8/8 pass**, run twice consecutively. Combined: **495/495**.
This includes, for the first time in this project's history, all 8
previously `NOT_CONFIGURED` fastapi-dependent regression files
(`test_v23_investor_grade`, `test_v24_auth`, `test_v24_international`,
`test_v24_native_remote`, `test_v25_unified_v10_parity`,
`test_v26_universal_pro`, `test_v27_rights_company_os`,
`test_v28_148ai_launch` — 136 tests total) actually executing rather than
failing on `ModuleNotFoundError: fastapi` at import. M4D.1's mutation
tests and true-concurrency tests are unmodified and included in this run
— nothing was removed or weakened to make M4D.2 pass.

**What remains genuinely `IMPLEMENTED_NOT_VERIFIED` or out of scope after
M4D.2** (FACT vs. STRUCTURAL PROOF vs. BLOCKED vs. NOT APPLICABLE, per the
directive's own reporting split):
- FACT: everything in C/D/E/F/G/H/I above — real Postgres 16.13, real
  Redis 7.0.15, real FastAPI 0.141.1/Starlette 1.0.0/Pydantic 2.13.3, real
  `rq` 2.12.0/redis-py 8.0.0/psycopg 3.x (pre-release `dev` source from
  `master`, version string reads `0.0.0.0` since no build step ran to
  inject it — the code itself, not the string, is what was exercised),
  all really running, really connected to.
- STRUCTURAL PROOF (unchanged from M4D.1, not newly claimed live): the
  Docker/S3 path (`S3ArtifactStore` + real AWS/S3) — not exercised; the
  disk-backed stand-in is real code but not S3.
- BLOCKED, confirmed with commands and exact error text above, not
  assumed: `pip install`/`apt-get install` of these same packages from
  their normal package registries; `docker pull` from Docker Hub.
- NOT APPLICABLE: this M4D.2 pass's own installation method
  (git-clone vendoring) is a **test/verification-environment workaround**,
  not a production deployment mechanism — a real deployment installs
  `requirements-production.txt` normally via `pip` on infrastructure with
  ordinary package-registry access, which this sandbox specifically lacks.
  This does not change what was verified about the *application code*;
  it is a statement about this one sandbox's network policy.

**M4 is still not `LIVE`.** M4D.2 verifies that M4D.1's fix behaves
correctly against real PostgreSQL, real FastAPI, and real Redis/RQ, all
running in this sandbox — it does not constitute a production deployment,
does not touch real user data, and per the directive's own instruction,
`VERIFIED_LIVE_INFRA` does not automatically mean `PRODUCTION_DEPLOYED`.
**M5 has not been started.**

Evidence: `tests/test_m4d2_live_postgres.py` (14 tests), `tests/test_m4d2_live_fastapi_redis.py`
(8 tests), `tests/m4d2_rq_job_target.py` (real job bodies for the RQ
tests), `tools/m4d2_setup_live_infra.sh` (the reproducible runbook). Full
commands, exact output, and version numbers: `PATCH_APPLICATION_REPORT.md`'s
M4D.2 section.

### M4D.2b — dependency parity + real worker execution (2026-09-24)

Two verification gaps in M4D.2's own evidence and documentation, found by
an independent review and accepted as real:

**1. RQ documentation overclaim, corrected.** The M4A worker-entrypoint
capability-table row above previously read "real `rq` dequeue of a real
`execute_modification_job` job" — but M4D.2's own `LiveRedisRQTests`
(section G, `PATCH_APPLICATION_REPORT.md`) explicitly fetched that real
job from Redis, then **cancelled and deleted it without running a
worker on it**, and proved the real `rq.SimpleWorker` dequeue/execute/
fail path only with **dedicated test job functions**
(`tests/m4d2_rq_job_target.py`), not `execute_modification_job` itself.
The table row above is now corrected; this section documents the real
fix (item 2 below closes the gap for real, rather than just fixing the
wording).

**2. Exact production dependency parity, verified.** M4D.2's vendored
packages were HEAD of each GitHub repo's default branch, not the exact
versions `requirements-production.txt` pins. Read directly:

```
$ cat requirements-production.txt
fastapi==0.128.2
uvicorn==0.48.0
pydantic==2.13.4
psycopg[binary,pool]==3.3.6
redis==8.1.0
rq==2.12.0
boto3==1.43.94
```

Every package was re-vendored (`tools/m4d2b_setup_parity_infra.sh`,
building a separate `/tmp/m4d2b_vendor`, leaving M4D.2's own
`/tmp/m4d2_vendor` untouched and independently re-runnable) from the
**exact upstream git tag** for its pin — not master/main HEAD:

| Package | Pin | Exact tag checked out | Was HEAD the same commit? |
|---|---|---|---|
| fastapi | 0.128.2 | `0.128.2` | No |
| psycopg | 3.3.6 | `3.3.6` (separate `git worktree`, since psycopg/psycopg_pool are independently-versioned packages in one repo) | No |
| psycopg_pool | (unpinned by `psycopg[pool]`) | `pool-3.3.3` (latest — no constraint to violate) | Yes (M4D.2's HEAD already was this tag) |
| redis-py | 8.1.0 | `v8.1.0` | No |
| rq | 2.12.0 | `v2.12` | **No — M4D.2's HEAD was 1 commit past this tag** (a `codeql-action` GitHub Actions version bump, unrelated to `rq`'s own source; `rq.__version__` read "2.12.0" either way, which is exactly the kind of overclaim-by-coincidence this parity pass exists to catch) |
| starlette | *(unpinned — transitive via fastapi)* | `0.50.0` — the latest tag satisfying fastapi 0.128.2's own declared `starlette>=0.40.0,<0.51.0` (its `pyproject.toml`, read directly) | N/A — M4D.2 never vendored starlette at all; it used whatever was pre-installed (**1.0.0** — see below) |

**Real, material finding:** the pre-installed `starlette` was **1.0.0**,
which is *outside* fastapi 0.128.2's own declared compatible range
(`<0.51.0`) — a real non-parity condition M4D.2 never checked. This pass
vendors the correct `0.50.0` and confirms the app still imports and
serves real requests correctly under it (`fastapi.testclient.TestClient`
round-trip re-verified — see below).

**Known, disclosed, unavoidable gap: `pydantic`.** The pin is
`pydantic==2.13.4`; the pre-installed version is `2.13.3`. `pydantic`
2.13.4 requires `pydantic-core==2.46.4` **exactly** (`pydantic/pydantic`'s
own `pyproject.toml` at tag `v2.13.4`, read directly). `pydantic-core` is
a compiled Rust/PyO3 extension — building it needs `cargo` to fetch crate
dependencies from `crates.io`/`index.crates.io`, and:
```
$ curl -sS -o /dev/null -w "%{http_code}\n" https://index.crates.io/config.json
403
```
genuinely blocked, confirmed the same way PyPI/apt/Docker Hub were in
M4D.2 — a different host, the same egress policy. `rustc`/`cargo`
themselves are present in this sandbox, but with no reachable crate
registry a real build is not possible here. The pre-installed `pydantic`
2.13.3 is paired with its own correctly-matching `pydantic-core` 2.46.3
(`pydantic` 2.13.3's own `pyproject.toml` pins exactly that — a real,
internally consistent, already-installed release, not a mismatched
hack) and is used as the closest available option (directive's option
**C**, "use an existing cached wheel/package if available"). This is a
genuine, disclosed, one-patch-version gap — not claimed as parity.

After building the parity vendor, every M4D.2/M4D.2b live suite was
re-run against it, plus a direct `fastapi.testclient.TestClient`
round-trip smoke test of the new fastapi/starlette pairing:
```
$ PYTHONPATH=/tmp/m4d2b_vendor python3 -c "from fastapi import FastAPI; from fastapi.testclient import TestClient; ..."
200 {'ok': True}
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... python3 -m unittest tests.test_m4d2_live_postgres        # 14/14 OK
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... M4D2_REDIS_URL=... python3 -m unittest tests.test_m4d2_live_fastapi_redis   # 8/8 OK
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... python3 -m unittest <34 combined modules>                 # 487/487 OK (2 skips)
$ PYTHONPATH=/tmp/m4d2b_vendor python3 -m compileall -q omni_prod tests tools                                  # exit 0
```
All pass under exact parity, identical counts to M4D.2's HEAD-based run.

**3. Real production-job execution through RQ, proven.** The directive
required actually dequeuing and executing the real
`omni_prod.worker_tasks.execute_modification_job` through a real RQ
worker — not a substitute test job — while replacing only the external
LLM dependency at its documented boundary. That boundary already exists
in production for exactly this purpose:
`omni_prod.model_runtime_config.ModelRuntimeConfig.from_env()`'s
*primary* model route defaults to a **local**, non-external endpoint
(`OMNI_LOCAL_MODEL_URL=http://127.0.0.1:8001/v1`, `external=False`;
`OMNI_ZERO_COST_MODE=1` and `OMNI_ALLOW_EXTERNAL_FALLBACK=0` are also the
defaults), and `omni_prod.routed_gateway.RoutedModelGateway` enforces
`if primary.endpoint.external: raise ValueError(...)`. `tests/m4d2b_local_model_server.py`
is a real HTTP server bound to a real loopback TCP port, implementing the
exact OpenAI-chat-completions-compatible protocol
`OpenAICompatibleGateway.complete()` speaks, returning deterministic
(marker-based, disclosed in its own docstring) responses instead of a
real hosted model's output — because this sandbox has no route to one, a
pre-existing constraint, not new to M4D.2b.

Rather than reuse M4D.2's in-process `rq.SimpleWorker` substitution, this
pass runs the real, default `rq.Worker` (which forks a child process per
job) in a **genuinely separate OS process**
(`tests/m4d2b_worker_process.py`, launched via `subprocess.run`), per the
directive's stated preference. This avoids the fork-after-open-pool
SSL-socket hazard M4D.2 hit (traced to rq's own source: the job's dotted
import — and therefore `omni_prod.investor_app`'s connection pool — is
only ever touched inside the *forked child*, per
`rq/worker/worker_classes.py::Worker.fork_work_horse` ->
`rq/worker/base.py::BaseWorker.main_work_horse` -> `perform_job` ->
`job.perform()`; as long as the parent process never opens a live
connection before calling `.work()`, nothing corrupted is inherited by
the fork — verified empirically, not just reasoned about). Labeled per
the directive's own vocabulary: **`REAL_RQ_SEPARATE_PROCESS_WORKER_VERIFIED`**
(`tests/test_m4d2b_parity_and_worker.py`, 3 tests, all passing, re-run 4
times consecutively with zero flakiness):

- `test_real_worker_process_dequeues_and_executes_execute_modification_job_ambiguous_path`
  — real HTTP propose -> real Redis job (`func_name ==
  'omni_prod.worker_tasks.execute_modification_job'`) -> the separate
  worker process dequeues and executes it for real -> real
  `ChangeClassifierAgent.classify()` call over real HTTP to the local
  test model server -> real `QUEUED -> RUNNING -> NEEDS_CLARIFICATION`
  transition, independently confirmed via the real HTTP status route and
  directly via `PostgresModificationRepository`.
- `test_real_worker_process_system_bug_path_hits_real_sandbox_docker_image_blocker`
  — the real classify/repair loop this time genuinely reaches
  `SandboxRepositoryExecutor.execute()` -> a real `docker run
  omni-sandbox:latest ...` subprocess. The real failure this produced
  turned out to be a **previously-unknown Docker-CLI-version
  incompatibility**: `omni_prod/sandbox.py`'s `--mount
  type=bind,...,rw` flag syntax is rejected by this sandbox's Docker
  29.4.3 (`invalid field 'rw' must be a key=value pair`) — a different
  real docker failure than the already-disclosed image-pull-forbidden
  block, equally real and equally unmodified. `run_sandbox()` captures
  this as a normal `ExecutionReport(passed=False)`, not an exception, so
  the real outcome is a cleanly completed `FAILED` modification
  (`error_code='verification'`, the real docker stderr preserved
  verbatim in `evidence_json`, `repair_rounds=3`, billing correctly
  `released` not `settled`) — proof that a real, uncontrived worker
  failure is recorded correctly and leaves fully recoverable durable
  state (current() untouched, the modification still normally gettable).
  `omni_prod/sandbox.py` is out of M4D.2b's scope (M2-era code, unrelated
  to M4's accept/reject/rollback pipeline) and is **deliberately left
  unfixed** here — flagged for whoever owns that module next.
- `test_duplicate_delivery_of_the_same_modification_does_not_reexecute_or_duplicate_state`
  — a second, independent RQ delivery (different job id, same
  `modification_id`) of the real production function, run through a
  second separate-process worker run: `jobs.transition_running()`'s own
  guard makes it a real no-op (identical `completed_at`, no version
  promoted or duplicated).

**What was not, and could not be, proven:** a `READY_FOR_REVIEW` (fully
passing) candidate via `execute_modification_job` — that requires the
real sandbox-executor Docker image (`omni-sandbox:latest`) to actually
build or pull, which remains blocked for the same reason M4D.2 already
disclosed (Docker Hub 403) *and* now, independently, for the `--mount`
flag incompatibility above. Both are genuine infrastructure/tooling
limits, not gaps papered over with a mock. A real hosted LLM and real
S3 remain out of reach, unchanged from M4D.2.

**Status discipline (directive item 4), applied literally:**
- PostgreSQL concurrency/atomicity: `VERIFIED_LIVE_INFRA` (unchanged).
- FastAPI execution: `VERIFIED_LIVE_INFRA` at exact production version
  parity for fastapi/starlette/psycopg/psycopg_pool/redis-py/rq; **one
  disclosed non-parity exception** — pydantic 2.13.3 vs. the 2.13.4 pin
  (pydantic-core==2.46.4 unbuildable here; see above).
- Redis production enqueue: `VERIFIED_LIVE_INFRA` (unchanged).
- RQ production `execute_modification_job` execution:
  `VERIFIED_LIVE_INFRA` (`REAL_RQ_SEPARATE_PROCESS_WORKER_VERIFIED`) for
  the `NEEDS_CLARIFICATION` and sandbox-verification-`FAILED` terminal
  paths; a `READY_FOR_REVIEW` terminal path remains
  `IMPLEMENTED_NOT_VERIFIED` (blocked on the real sandbox image, as
  above).
- **`M4 VERIFIED_LIVE_INFRA`** — per the directive: this does **not**
  mean `PRODUCTION_DEPLOYED` or `FULL_EXTERNAL_E2E`; real external
  LLM/S3/provider execution, and a real, successfully-passing sandboxed
  code-verification run, remain separately unverified, both for
  pre-existing reasons unrelated to M4's own accept/reject/rollback
  correctness.

Regression after M4D.2b, exact-parity vendor: 487/487 combined + 8/8
(`test_m4d2_live_fastapi_redis`, standalone) + 3/3
(`test_m4d2b_parity_and_worker`, standalone) = **498/498**, 2 expected
skips. **M5 has not been started.**

Evidence: `tests/test_m4d2b_parity_and_worker.py` (3 tests),
`tests/m4d2b_local_model_server.py`, `tests/m4d2b_worker_process.py`,
`tools/m4d2b_setup_parity_infra.sh`. Full command transcripts, exact
tag/commit table, and the exact real docker error text:
`PATCH_APPLICATION_REPORT.md`'s M4D.2b section.

| M4E — verification pipeline reuse (build/tests/repair/quality/security/rights/target gates) | `VERIFIED` | `CandidateModificationEngine` calls the same `quality_fn`/`security_fn`/`RightsEngine`/`Executor` as the rest of the pipeline — `tests/test_m4_modification_engine.py`, `tests/test_m4_acceptance.py::AcceptanceM` |
| M4F — deterministic diff (repository + spec) | `VERIFIED` | `omni_prod/modification_diff.py`; `tests/test_modification_diff.py`, `tests/test_m4_acceptance.py::AcceptanceQR` (order-independence proven directly) |
| M4G — billing (reserve at request time, settle/release by real classification, not by spend) | `VERIFIED` (decision logic + idempotency, AND the route's `reserve()` call itself, live — see **M4D.2**) | `tests/test_m4_worker.py::ResolveModificationBillingTests`; `tests/test_m4_acceptance.py::AcceptanceV`; `tests/test_m4d2_live_fastapi_redis.py` (every propose call reserves real credits via `PostgresSubscriptionService.reserve()` against real Postgres) |

### Required acceptance tests (A–W) and the concurrency requirement

All 24 (23 lettered + the concurrency requirement) are addressed in
`tests/test_m4_acceptance.py`; letters with deeper pre-existing coverage
point to it in their docstring.

| # | Claim | Status |
|---|---|---|
| A | POST returns 202 + durable id | `VERIFIED` — live, via real `fastapi.testclient.TestClient` against real Postgres (`tests/test_m4d2_live_fastapi_redis.py::test_full_http_propose_accept_flow_persists_to_real_postgres`); durability it depends on (`create()`+`create_outbox()` committing first) remains separately `VERIFIED` at the unit level too |
| B | API process never executes synchronously | `VERIFIED` (static AST proof, no import needed) |
| C | queue payload reloads from DB | `VERIFIED` |
| D | Redis enqueue failure stays recoverable via outbox | `VERIFIED` |
| E/F | exact source version / exact spec for that version loaded | `VERIFIED` |
| G/H | `system_bug`/`missing_requirement` run the real repair loop | `VERIFIED` |
| I | `ambiguous` executes nothing | `VERIFIED` |
| J | `change_request` runs the dedicated evolution path | `VERIFIED` |
| K | source version unchanged while candidate builds | `VERIFIED` |
| L | failed candidate can never be accepted | `VERIFIED` |
| M | gate failure never reaches `READY_FOR_REVIEW` | `VERIFIED` |
| N | accept promotes the candidate | `VERIFIED` — see **M4D.1** above; the promotion path (status validate → candidate read → version insert → spec insert → final status update) now executes inside one merged transaction with an atomic expected-version guard, proven by real 2-thread and 10-thread barrier-synchronized concurrency tests plus mutation tests |
| O | reject leaves current version intact | `VERIFIED` |
| P | rollback restores an exact historical version | `VERIFIED` |
| Q/R | repository diff / spec diff are deterministic | `VERIFIED` |
| S | spec/version can't become mismatched | `VERIFIED` (schema PK + no `update()` path), including live: migrations 001–016 applied to a real PostgreSQL 16 database and exercised for real in **M4D.2** |
| T | retry (queued redelivery, completion redelivery) is idempotent | `VERIFIED` |
| U | concurrency — explicit conflict semantics | `VERIFIED` |
| V | reservation not double-charged on retry | `VERIFIED` |
| W | all existing regression tests remain green | `VERIFIED` — as of **M4.9**, 501/501 tests pass across the full suite (488/488 in the combined run + 8/8 `test_m4d2_live_fastapi_redis.py` + 3/3 `test_m4d2b_parity_and_worker.py` + 1/1 `test_m49_clean_room.py` + 1/1 `test_m49_lifecycle.py`, all standalone-required for the same documented reason — module-level `omni_prod.investor_app` globals), plus 3/3 in the previously-always-skipped `tests/integration/test_live_sandbox_security.py` when explicitly enabled. 17 skips, all pre-existing, gated integration tests (opt-in env vars / unavailable signing credentials), not new. Supersedes the 309/309 (pre-M4D.1), 337/337 (post-M4D.1, pre-M4D.2), 495/495 (M4D.2, HEAD-based vendor), and 498/498 (M4D.2b) counts this row previously cited — see `PATCH_APPLICATION_REPORT.md` for the exact commands and §M4.9 for the full breakdown |
| Concurrency requirement (Version 10/11 scenario) | Do not silently overwrite; B must rebase, stay alternate, or be an explicit forced accept | `VERIFIED` — reproduced verbatim in `AcceptanceU`: A accepts → Version 11; B's plain accept returns `reason='conflict'` and Version 11 is untouched; B's `force=True` accept is the explicit third option |

### Not implemented / out of scope for this M4 pass

- ~~Live end-to-end run of the HTTP layer, Redis dispatch and Postgres schema~~ — **closed by M4D.2** (see above): real PostgreSQL 16, real Redis, and real FastAPI (via a disclosed git-clone-vendoring workaround for the Python packages themselves — `pip`/`apt`/`docker pull` remain genuinely blocked in this sandbox, confirmed not assumed) were exercised for real. What remains out of scope: a genuinely separate, forked/exec'd worker OS process in full production topology (M4D.2's RQ tests use `rq.SimpleWorker`, in-process, for a disclosed reason — see M4D.2's §G above) and the real S3/`boto3` path (a real disk-backed stand-in was used instead, out of scope for M4D.2's Postgres/Redis/FastAPI sections).
- ~~Full cross-transaction atomicity of `accept()`~~ — **closed by M4D.1** (algorithm) and **M4D.2** (live Postgres): `accept()` shares a single cursor across `workspace.commit()` and the status update inside one transaction, and this was proven both structurally (fake-cursor/statement-order) and, as of M4D.2, from PostgreSQL's own `txid_current()`/`pg_stat_database` counters during real concurrent execution.
- ~~A genuinely-passing `READY_FOR_REVIEW` candidate via `execute_modification_job`, and the accept/rollback lifecycle built on top of one~~ — **closed by M4.9** (see below): the real sandbox image now builds, runs, and is proven secure; a real, non-mocked candidate reaches `READY_FOR_REVIEW`; and it was really accepted and really rolled back.
- M5 and later milestones — out of scope by the directive's own stop condition; not started until M4.9 (below) explicitly authorizes it.

### M4.9 — genuine live sandbox execution: image built, security proven, full lifecycle closed (2026-09-24)

M4D.2b left one real gap open, disclosed at the time (its own §9 test
docstring): `execute_modification_job`'s sandbox-verification path had
never actually run a container, for two independently-real reasons —
`omni_prod/sandbox.py`'s `--mount ...,rw` flag was invalid syntax for
this sandbox's Docker 29.4.3, and no working `omni-sandbox:latest` image
existed (Docker Hub pulls are blocked here, same as every earlier
milestone). M4.9's own directive (items 7–12) required closing this for
real, with a fresh clean-room run, real negative security tests, exact
image provenance, direct invariant verification, and a real (non-mocked)
accept+rollback lifecycle proof — in that order, with M5 only authorized
once all of it passed. All of it passed; details below, full transcripts
and exact commands in `PATCH_APPLICATION_REPORT.md`'s M4.9 section.

**1. The real `--mount` defect (task #47).** `build_docker_command()`'s
output-mount line built `f"type=bind,src={output},dst=/output,rw"` —
`--mount` has no `rw` field (that syntax belongs to `-v`/`--volume`, not
`--mount`); a bind mount is read-write by default when `readonly` is
omitted, so the fix is deleting the invalid token, not adding a real one.
Confirmed via direct `docker run --mount ...` probes before and after.
Full pre-M4.9 regression (34 tests across the sandbox-adjacent modules)
stayed green.

**2. A real `omni-sandbox:latest`, with exact, reproducible provenance
(task #48).** A first attempt — `docker import` of a full snapshot of
this build container's own filesystem (6.07GB) — was abandoned: this
sandbox's Docker uses the `vfs` graph driver, which copies the ENTIRE
accumulated filesystem on every image layer (no copy-on-write), so even
a 3-instruction Dockerfile exhausted the whole session disk allowance.
The real fix: `strace -f -e trace=openat,open,stat,lstat,access,readlink,newfstatat`
against a real `pytest -q` run exercising the stdlib surface this
codebase's own tests use, parsed for every path actually, successfully
opened (387 real paths — the python3.11 interpreter, the full stdlib, and
every shared library its C-extension modules actually `dlopen`'d), plus
the ELF interpreter path (`/lib64/ld-linux-x86-64.so.2`, added by hand
since the kernel opens it directly via `PT_INTERP`, never as a traced
`openat()`). Copied (dereferencing symlinks) into a 27MB staging root,
`docker import`ed into `omni-sandbox-minimal:m49local`
(`sha256:1f21f853aafc2e79832a64d2d6ff18a9b399cd7962d9cb2a1b8ce89b0bd50276`
after one follow-up fix, below), verified immediately under the FULL
production security flag set (not relaxed) — real pass, with pytest's own
cache-write failure against the read-only `/workspace` mount itself real,
positive evidence that restriction was live. pytest 8.3.5 + pluggy 1.6.0
+ iniconfig v2.3.0 vendored via `git clone`/`git checkout <tag>` (PyPI is
blocked), exposed via `PYTHONPATH`, with two small hand-written
`_version.py` shims (setuptools_scm's real build-time step never ran) —
each individually commented and disclosed in place.

Follow-up fix, found while proving the pipeline end-to-end (below):
`infra/sandbox/Dockerfile`'s own `CMD` uses a bare `"python"` (PATH-resolved,
not an absolute path); the minimal image initially had only
`/usr/bin/python3.11`. Added `/usr/bin/python3`/`/usr/bin/python` symlinks
to the same staging root and `ENV PATH=/usr/bin`, matching the original
spec exactly. **Final `omni-sandbox:latest` digest:
`sha256:6834400bb7810ada027f02dd685d7eb2cae4b684b38745d0c8a1488a86702532`**,
29.4MB, built in under a second, real command:
`docker build --no-cache -t omni-sandbox:latest -f Dockerfile .` (exact
Dockerfile, with its own full provenance narrative, in
`PATCH_APPLICATION_REPORT.md`'s M4.9 section).

**3. Clean-room end-to-end success run (task #49, directive item 7).**
Real, second, independently-discovered production bug found and fixed
along the way: `SandboxRepositoryExecutor.execute()` materializes the
repository into `tempfile.TemporaryDirectory()`, which Python always
creates at mode `0700` regardless of umask — fine for a same-uid caller,
but that directory is bind-mounted into the sandbox container, which runs
as a genuinely different, unprivileged uid (`10001`, per `SandboxLimits`)
— so no sandboxed process could even traverse into its own mounted
repository (real `PermissionError: ... '/workspace/pytest.ini'`, pytest's
own config-discovery). Never caught before M4.9 because no container had
ever gotten far enough to try. Fixed: `os.chmod(root, 0o755)` /
`os.chmod(out, 0o777)` after materializing content — full regression
(485 passed, 17 skipped at that point) confirmed no regression.

New test `tests/test_m49_clean_room.py` (standalone) is the first test in
this codebase's history to drive a `ModificationRequest` to a genuine,
non-mocked `READY_FOR_REVIEW`: real `classify()` (against the same
disclosed local-model-server stand-in M4D.2b established) → real
free-repair loop → real `docker run omni-sandbox:latest` verification,
which genuinely PASSES → real quality gate → real security scan → real
rights gate, all passing for real. Clean-room isolation, independently
verified immediately before the official run: a dedicated, freshly
created+migrated Postgres database (`m49_clean_room`, not `m4d2_test`,
confirmed 0 rows beforehand), `redis-cli FLUSHALL` (confirmed `DBSIZE 0`),
and the exact `omni-sandbox:latest` digest above re-verified via
`docker inspect` immediately before running — no unknown pre-existing
image assumed, no IDs reused from any earlier run. Official run: **1
passed**. Final Postgres state, verified directly: exactly 1
`modification_requests` row (`READY_FOR_REVIEW`), exactly 1
`modification_candidates` row, exactly 1 `project_versions` row — no
orphans.

**4. Sandbox security negative tests (task #50, directive item 8).** New
test `tests/test_m49_sandbox_security.py` (3 tests, part of the ordinary
combined suite). Every check is real evidence collected from *inside* a
running `docker run omni-sandbox:latest` container, or a real attempted
violation — never asserted from the `docker run` argv alone:

| Requirement | Real evidence |
|---|---|
| not running as root | `os.getuid()`/`os.getgid()` inside the container: `10001`/`10001` |
| `no-new-privileges` active | `/proc/self/status` `NoNewPrivs: 1` (kernel ground truth) |
| `cap-drop=ALL` active | real raw-socket creation (needs `CAP_NET_RAW`) → real `PermissionError: Operation not permitted` |
| PID limit enforced | real fork loop against `SandboxLimits(pids=8)`: exactly 7 forks succeed, the 8th genuinely raises `OSError: [Errno 11] Resource temporarily unavailable` |
| memory limit configured **and** effective | cgroup `memory.limit_in_bytes` = 1073741824 (exact); a real attempt to allocate+touch 1.5GB gets real-OOM-killed — `docker run` returns real exit `137`, allocation stops at 1000MB (never reaching 1050MB) |
| CPU limit configured | cgroup `cpu.cfs_quota_us`/`cpu.cfs_period_us` = exactly 1.5 cpus |
| host filesystem not writable outside allowed mounts; root filesystem read-only | real write attempts to `/etc`, `/usr/bin`, and the read-only `/workspace` mount all fail with real `OSError: [Errno 30] Read-only file system`; `/tmp` (tmpfs) and `/output` (rw mount) proven genuinely writable as a positive control |
| network disabled | real outbound TCP connect → real `OSError: [Errno 101] Network is unreachable` |

Isolation was never weakened to get a passing build, per the directive's
own instruction — every probe above ran under production
`SandboxLimits()` defaults except the PID test, which deliberately used a
*smaller* limit (`pids=8`) purely to make real exhaustion fast, not to
relax anything. As a bonus, the pre-existing, previously-always-skipped
`tests/integration/test_live_sandbox_security.py` (gated behind
`OMNI_RUN_LIVE_SANDBOX=1`) now genuinely passes for the first time in
this project's history: 3/3.

**5. `READY_FOR_REVIEW` invariant, verified directly (task #51, directive
item 10).** `tools/m49_ready_invariant_check.py` connects to Postgres
directly (raw `psycopg`, not the repository ORM, not the HTTP API) and
checks every sub-item of item 10 against raw row/JSON content for the
real modification task #49 produced: generation completed (real
`started_at`/`completed_at`), sandbox command executed successfully
(real, non-empty `build_log_tail`), build/test exit status successful,
verification gates passed (quality score 89/100, 0 security findings),
candidate version + `ProductSpec` + diff all real and present, state is
`READY_FOR_REVIEW`, and no partial/orphan state anywhere (exactly one
`modification_requests` row, exactly one `modification_candidates` row,
no extra `project_versions` rows, `promoted_version_id`/`accepted_at`/
`rejected_at` all still null). Result: `M49_READY_INVARIANT_ALL_PASS`.

**6. Complete version lifecycle — accept, verify, rollback, verify
(task #52, directive item 11).** New test `tests/test_m49_lifecycle.py`
(standalone), reusing the SAME real candidate from task #49 — no mocked
repository state anywhere in this proof. A. real HTTP `POST .../accept`
→ real 200, new real version `v_babb1198473a40fe`. B. verified directly:
Postgres `current()` now returns that version, with repository content
byte-identical to the accepted candidate; raw-row check confirms its
`parent_id` is the seed version. C. a real, persisted `ProductSpec` row
exists for the new version, matching the candidate's spec. D. real HTTP
`POST /rollback` targeting the original seed version → real 200, a
*third*, brand-new version `v_45963a10dd86444a` (rollback re-commits, it
never rewrites the old row). E. verified EXACTLY restored: `current()`
now returns that version, with repository content proven
**byte-identical** to the original seed repository (real dict equality,
not a heuristic), and explicitly different from the superseded accepted
candidate. Final independent `psql` snapshot: exactly 3
`project_versions` rows for this project, in the correct real chain
(seed → accepted → rollback-of-seed); `modification_requests` shows
exactly 1 row, `status=ACCEPTED`.

**7. Full regression.** Combined suite (excluding the now five
standalone-required live-infra files): **488 passed, 17 skipped** (all 17
are pre-existing, gated integration tests requiring explicit opt-in env
vars or unavailable credentials — Android/iOS signing, `OMNI_RUN_LIVE_*`
flags — not new skips M4.9 introduced). Standalone:
`test_m4d2_live_fastapi_redis.py` 8/8,
`test_m4d2b_parity_and_worker.py` 3/3 (one of its two real-failure tests'
docstring and specific build-log assertion were honestly updated in
place — not silently — to track a NEW real failure mode the M4.9 fixes
themselves produced further downstream; see `PATCH_APPLICATION_REPORT.md`),
`test_m49_clean_room.py` 1/1, `test_m49_lifecycle.py` 1/1. **Combined
total: 501/501**, plus the newly-real 3/3 in
`test_live_sandbox_security.py` when explicitly enabled.

**8. Final status (directive item 12).** All of M4.9 items 7–12 passed.
**`M4 = VERIFIED_LIVE_INFRA`**, with the explicit limitation the
directive itself names: this is still not `PRODUCTION_DEPLOYED` and not
`FULL_EXTERNAL_E2E` — a real hosted LLM provider and real S3 remain out
of reach in this sandbox (unchanged since M4D.2), and this milestone's
real sandbox image is a disclosed, documented substitute for
`infra/sandbox/Dockerfile`'s own `python:3.12-slim` base (Python 3.11.15
here, not 3.12; PyPI-installed dependencies here vendored instead), not
that exact image. The pydantic 2.13.3 vs. 2.13.4 patch-version gap
(M4D.2b) remains a documented production-CI verification item and does
not block M5. **Per the directive's own item 12: M4 work stops here, and
M5 architecture/implementation planning is now authorized to begin** —
no M5 requirements have been given yet in this engagement, so no M5 work
has started.

## 6. M4.95 — Capability Foundation & Truth Lock V2 (2026-10-04)

**Status: VERIFIED_LOCAL_PROVIDER_NEUTRAL_FOUNDATION.** Tasks 1–16 are implemented and verified in this execution environment. This status is intentionally narrower than `PRODUCTION_DEPLOYED` or `FULL_EXTERNAL_E2E`.

Canonical execution plan: `docs/superpowers/plans/2026-10-04-m495-capability-foundation-v2-plan.md`.
Design authority: `docs/superpowers/specs/2026-10-04-m495-capability-foundation-design.md`.
World-class gap baseline: `docs/148AI_WORLD_CLASS_COMPLETENESS_AUDIT_V2_2026-10-04.md`.
Validation evidence: `M4_95_VALIDATION.md`.

Fresh pre-change baseline: `518` tests, `OK`, `47` skipped.
Fresh post-M4.95 full regression: `633` tests, `OK`, `47` skipped.
Focused Golden/failure/recovery gate: `22` tests, `OK`.

Verified locally: canonical Capability/Skills/Agents registries; dependency closure; provider-neutral contracts and routing; provider+capability 429/quota cooldown; streaming artifact integrity; durable execution attempt identity, lease/resume and `provider_task_id`; credential-binding abstraction; crash-safe capability execution; versioned local price/authorization/actual-cost truth; durable worker capability gate; tenant-scoped readiness evidence; artifact provenance/export evidence; machine truth drift enforcement; provider-neutral heterogeneous Golden E2E; localhost HTTP fake-provider integration; paid-provider durable-result guard; file-backed streaming provider artifacts.

Not re-claimed as live in this environment: clean-room/lifecycle Postgres proof (`psycopg` unavailable), isolated Docker sandbox proof, live Postgres/Redis/S3, commercial media/3D providers, and mobile signing. The historical M4.9 live-infra evidence remains recorded above but is not substituted for current evidence.

The Golden E2E uses an in-process fake multimodal provider with structurally valid artifacts. It proves the universal execution/verification/evidence contract, **not** that a named commercial provider is LIVE.

M4.95 machine truth SHA-256: `3dc33a3e605662d2a6d7884a73a575938b8a6c55ad4788b48915c364a915c92a`

## M5 Production Vertical Slice — 2026-10-04

Current machine-facing classification: **M5_PARTIAL**. M5 implementation has started from the verified M4.95 baseline. Durable deployments use the plural `/builds` asynchronous pipeline as the canonical arbitrary-generation path; developer memory mode is not staging or production proof. Production readiness remains prohibited until M5 acceptance, recovery/security, deployment/billing, full regression and external staging proofs are complete.


## Infisical generated-app secret adapter — 2026-10-06

### Implemented and independently verified
- Opt-in Infisical Universal Auth/v4 SecretWriter: create/read/rotate/delete,
  missing-delete handling, permission failures, response validation, token expiry,
  deterministic project/environment reference separation, supplied-env wiring.
- Vault remains the default and its writer remains supported.
- Test-first evidence: commit fbbc04b, v24-ci run 37386465951/job 112020832639:
  9 intended new test failures for missing Infisical support; the full-suite
  aggregate regression test also failed because it includes those tests.
- Implementation evidence: commit e0924b8, v24-ci run 37386690727/job 112021563213:
  `python -m pytest -q` = 819 passed, 55 skipped, 1 warning, 95 subtests passed.
  Compileall, hostile static suite, international gate and compose-config passed.
  These are automated fixture/regression results, not live Infisical evidence.
  Warning: Starlette's AnyIO BlockingPortal alias is deprecated.

### Implemented but awaiting external live verification
- The Infisical writer has not authenticated to the founder's live account from
  the deployed Vercel server. Live create/read/rotate/delete proof is pending.
- Configuration-level readiness stays PARTIAL; only per-binding verification
  may mark an actual infrastructure binding LIVE.
- See docs/INFISICAL_GENERATED_APP_SECRETS.md for configuration and rollback limits.

### Blocked by a named credential/service
- The intended Vercel Preview environment must explicitly select
  OMNI_GENAPP_SECRET_STORE_PROVIDER=infisical and receive this tested source.
- Generated-app-only database admin DSN, scoped object credential issuer/bucket,
  scheduler, image provider and their cost quotes remain separate blockers.
- No real secret values were read, logged, copied into this repository or tested.

### Not implemented
- Automatic migration of live Vault values to Infisical.
- Infisical as the general control-plane/model-provider secret resolver.


## 2026-10-06 — Opt-in generated-app Cloudflare R2 adapter

1. **Implemented and independently verified (unit/CI, not live R2):**
   source revision e5ce74c281e6e82ad355aaa9b0556709f6afbb1e passed v24-ci
   (https://github.com/Shayfly/desktop-tutorial/actions/runs/37456953208)
   and V11 Overlay CI
   (https://github.com/Shayfly/desktop-tutorial/actions/runs/37456953187).
   compileall, pytest (828 passed, 56 skipped, 1 warning, 119 subtests passed),
   hostile static suite, international gate and compose-config passed.
   The test-first revision 83eba3b5d8ae2b9cb703aec6ddafc56d24128ef2 failed
   collection because the R2 issuer did not yet exist, as intended.
2. **Implemented but awaiting verification:** local HS256 temporary credential
   issuer; strict managed CRUD/list policy translation; R2/static readiness and
   wiring; protocol tests; independently gated R2 CRUD/isolation integration test.
   The default AWS STS path is preserved. See docs/R2_GENERATED_APP_CREDENTIALS.md.
3. **Blocked by a named service/access:** live Cloudflare R2 verification needs a
   trusted test runner with the founder's Preview settings injected. No keys
   were read in chat or committed. Screenshots establish bucket/config presence,
   not provider verification. CI deliberately skips the live test without opt-in.
4. **Not implemented in this change:** automatic credential refresh and expiry-safe
   existing-binding reuse; immediate per-session revocation; full runtime
   cross-app verification. The saved system audit still applies.

Validation commands: `python -m compileall -q omni_prod tests`,
`python -m pytest -q`, `python scripts/run_hostile_static_suite.py`,
`python scripts/run_international_gate.py`.
Real test: `M5_R2_LIVE=1 python -m pytest -q tests/integration/test_r2_generated_storage_live.py`
with securely injected staging variables. This is a command to run, not a passed
live result.


## 2026-10-06 — QStash scheduler connector

1. **Implemented and independently verified:** baseline 23d48ff passed v24-ci
   https://github.com/Shayfly/desktop-tutorial/actions/runs/37458399389 .
   Source ed9af69d529f4796e3cf2135c55fdb347dd53bae passed v24-ci
   https://github.com/Shayfly/desktop-tutorial/actions/runs/37460855718
   and V11 Overlay CI
   https://github.com/Shayfly/desktop-tutorial/actions/runs/37460855680 .
   compileall, pytest (846 passed, 58 skipped, 1 warning, 158 subtests passed),
   hostile static suite, international gate and compose-config all passed.
   These are unit/CI proofs; live QStash administrative and delivery tests did not run.
2. **Implemented, awaiting live verification:** QStash schedule create/get/cancel,
   publish with deduplication, safe transport, signature verifier requiring a durable
   replay claim, saved-variable readiness and API-access check. A QStash binding is
   BLOCKED until per-app authenticated delivery is proven, even if API access passes.
3. **Blocked by a named service/access:** real administrative tests require a trusted
   runner with QSTASH_URL/QSTASH_TOKEN; optional schedule lifecycle test also requires
   an operator-owned harmless QSTASH_TEST_DESTINATION. No founder keys were read.
4. **Not implemented here:** tenant-scoped durable schedule API, production delivery
   gateway/inbox, retry/crash recovery and generated-app callback wiring. Provider
   JWT replay rejection alone is not exactly-once business execution.

See docs/QSTASH_SCHEDULER_CONNECTOR.md. Commands:
`python -m compileall -q omni_prod tests`; `python -m pytest -q`;
`python scripts/run_hostile_static_suite.py`;
`python scripts/run_international_gate.py`.
Live administrative test:
`M5_QSTASH_LIVE=1 python -m pytest -q tests/integration/test_qstash_scheduler_live.py`.
These live commands are instructions, not passed evidence.

## Replicate live connection investigation — 2026-10-06

The authenticated Preview account check returned upstream 403 even after the
user configured billing, rotated the token and redeployed. The safe diagnostic
reported token_format_valid=true, response_kind=other and category=unknown.
No billable generation was started; connection and generation remain unverified.

A separate HTTP 500 was traced in Vercel runtime logs to stale PostgreSQL SSL
connections during session authentication. DatabasePool now uses the official
ConnectionPool.check_connection callback before checkout. Regression tests also
confirm arbitrary writes are not replayed. Both GitHub workflows passed for
9025f7316916ee9bd1943d3ab355cc5a56be135a.

The 403 hypothesis is the Python-urllib client identification: Ultralytics documents
Replicate CDN rejecting that default from datacenter IPs, while Replicate's own
Python client supplies a named User-Agent. Requests now identify as 148AI/1.0,
with Accept: application/json, for the Replicate API only. No browser impersonation,
challenge solving, access-control changes or token disclosure are involved.
Sources:
- https://github.com/ultralytics/replicate/blob/main/replicate_metadata.py
- https://github.com/replicate/replicate-python/blob/main/replicate/client.py

12 targeted tests passed for authentication safety, request headers, rejection
categories and database checkout behavior. Live verification of the named-client
request is still pending; neither connection nor media generation is marked LIVE.

## Replicate one-image Preview test (2026-10-06)
Implemented and locally verified: fixed FLUX Schnell one-image test, authenticated Preview-only routes, explicit $0.003 approval and same-origin POST, one durable submission per account, fail-closed unknown submission, verified private S3 image retrieval. Uses existing migration 026 submission journal and existing S3 workspace storage; no ephemeral state or additional schema.
Verification: python -m pytest tests/test_replicate_image_test.py tests/test_replicate_connection.py tests/test_database_pool_health.py -q -p no:cacheprovider — 18 passed. Tests include recovery across service instances, account isolation, no authentication/no confirmation rejection, ambiguous-submit non-replay and stored image retrieval without further provider calls.
Awaiting external live verification: paid POST, provider completion, artifact download and storage on the newly deployed Preview. No image has yet been generated by this test. Authentication to Replicate was separately live verified (connection_verified=true) on p40n0qijl.

## Replicate test storage preflight (2026-10-06)
Live image submission was blocked before the provider POST because HeadBucket returned false; no image was submitted. Underlying storage error was swallowed by the generic ping, so object access failure is not yet established.
Replaced the image-test-specific preflight with a small private object write/read/integrity probe; no credential or raw service error is returned. Recognized failure category and operation are exposed for diagnosis. The shared S3 ping is unchanged. Scope-permission hypothesis awaits live verification.
Local verification: python -m pytest tests/test_replicate_image_test.py tests/test_replicate_connection.py tests/test_database_pool_health.py -q -p no:cacheprovider — 20 passed. Live object probe and paid image generation still pending.

## R2 request signing compatibility (2026-10-06)
Live latest redeploy rchseos0u still reports write SignatureDoesNotMatch. Root cause is not yet conclusively attributed to credentials or SDK.
Independently reproduced locally with real pinned boto3 1.43.94/botocore 1.43.108 and synthetic credentials: before-send capture (no network) shows x-amz-sdk-checksum-algorithm, aws-chunked encoding, STREAMING signature. Official R2 compatibility table lists the optional checksum algorithm header unsupported for PutObject. R2-only client now uses SigV4, region auto, path addressing and checksum calculation/validation when_required. Standard S3 unchanged; private SHA256 storage verification retained.
Verification: python -m pytest tests/test_r2_storage_signing.py tests/test_replicate_image_test.py tests/test_replicate_connection.py tests/test_database_pool_health.py -q -p no:cacheprovider — 22 passed. New regression captures actual signed request before transmission and confirms unsupported trailers absent, SigV4 present, SHA256 metadata retained; AWS region/defaults preserved.
Awaiting live storage probe on new Preview. No claim that SignatureDoesNotMatch is fixed live and no paid image proof.


## 2026-10-11: PR17 branch reconciliation with PR11

PR11 is integrated into the PR17 branch only. Schema compatibility now requires migration 038, matching the attachment migration already present in PR17. Existing drift checks remain intact. This branch push is authorized to trigger Preview; no milestone/main merge, worker deployment, live migration, or secret change is authorized by this reconciliation. Local verification covers 48 deployment verification tests; full application and PostgreSQL validation must be confirmed by CI on the resulting commit. Preview protection, unscheduled default-branch backups, and worker recovery/drain risks remain release blockers; this entry does not claim production readiness.
