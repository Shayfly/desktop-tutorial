# Issue 29 recovery verification — 2026-10-14

This follow-up is based on the latest PR #28 source head, `e364151` (`fix/docker-oom-rehearsal-20261013`). It does not merge or deploy that branch.

## CI and registry status

At `e364151`, the source CI and synthetic merge-candidate compatibility checks passed. The merge-candidate run [38469185825](https://github.com/Shayfly/desktop-tutorial/actions/runs/38469185825) ran the full suite on the synthetic merge tree: **1,677 passed, 172 skipped, 320 subtests passed**. The `v24-ci` run [38469185912](https://github.com/Shayfly/desktop-tutorial/actions/runs/38469185912) also passed.

The Agent OS consistency check exposed a Windows-only false stale status: Git checked out LF source files with CRLF, while the freshness auditor hashed raw working-tree bytes. `omni_prod/registry_audit.py` now normalizes CRLF before hashing, and `tests/test_registry_audit.py` covers line-ending-only changes. This keeps evidence freshness consistent with Git's normalized source content without treating actual code changes as fresh.

The first follow-up run also exposed a CI cancellation race: push and pull-request events shared concurrency groups in `v24-ci`, V11 Overlay CI, `intake-budget-pg`, and the intake gates. Those groups now include the event name, with a regression test in `tests/test_ci_workflow_concurrency.py`, so one event cannot cancel the other.

The separate [deployment verification run 38469273807](https://github.com/Shayfly/desktop-tutorial/actions/runs/38469273807) is **blocked**, not green: the protected Preview returned HTTP 401 because no valid Vercel automation-bypass token was supplied. The verifier correctly stopped before its authenticated journey; weakening this gate would turn an unverified deployment into a false success.

## Application-flow evidence

| Area | Verified in this run | Not verified here |
|---|---|---|
| AI conversation | Local conversation, language/UX, retry, and deterministic intake regression tests passed. | A real model-backed conversation and durable production persistence. |
| Architect approval | Requirements, brief fingerprints, plan binding, and approval-policy unit tests passed. | Live PostgreSQL approval/revision transactions; no `M4D2_DATABASE_URL` was configured. |
| Build, repair, and cost | Worker/build state, repair-round, acceptance, and metered-cost regression tests passed. | A real queued build using paid model providers or production cost settlement. |
| Preview | Preview access, router, and smoke regressions passed. | A live Docker preview or authenticated private Preview; Docker is unavailable in this Windows environment. |

The portable local regression set completed with **250 passed, 48 skipped, and 70 subtests passed**. Tests requiring Linux worker-host shell/container behavior and POSIX preview-storage semantics were excluded from that clean run; an initial Windows run confirmed those host assumptions (`bash`/container commands, `/root` paths, and `os.chown`). The upstream Linux merge-candidate run includes the full suite. Skipped tests and mocked-provider tests are not evidence of live infrastructure.

## Phase 0-1 — conversational AI audit

Baseline before this change: branch `shayfly-148ai-engineering-recovery`, commit `c105c54d6aaac521aeadd5eb413f962106d324a5`, based on `fix/docker-oom-rehearsal-20261013` at `e36415182151668da4fec1f6a38f13c78f2277ae`. The local environment is Windows/Python 3.13.5 with no database, Redis, provider-key, or intake-activation variables configured.

The customer chat is not a general-purpose model completion endpoint. `omni_prod/assets/app.js` calls `POST /api/v28/projects/{project_id}/conversation`; `investor_app.py` authenticates the project and delegates to `ConversationSupervisor`, which uses the deterministic interpreter unless the model switch, project/daily budgets, durable reservation service, and worker route are all available. Standard and escalated requirement turns can use `ReservedWorkerInterpreter`; greetings, quick answers, and non-requirement intents intentionally do not call a model. Paid calls remain opt-in and worker-only.

The latest available runtime evidence is historical and branch-scoped: read-only run `38312763134` found the staging intake worker disabled; run `38313019963` enabled that worker, and Preview-scoped switches and hard caps were configured. That is evidence of a configuration correction, **not** proof that a customer received a model response. For the current PR head, deployment verification run [38482557570](https://github.com/Shayfly/desktop-tutorial/actions/runs/38482557570) stopped at HTTP 401 `PROTECTED`, before authenticated chat E2E. Therefore the exact proven historical cause is the disabled worker switch; the current live response path remains `BLOCKED` pending authorized Preview E2E.

This change closes two observability gaps without enabling or contacting a provider: the API now reports `model-via-worker` only when the server has its durable database and Redis enqueue dependencies, and each saved assistant message exposes `ai_status` (`model`, `fallback`, or `not_used`). The chat labels deterministic fallback replies explicitly instead of letting a configured global route imply that a particular answer came from AI. The broader local conversation-to-preview regression set passed **148 tests, 35 skipped, 39 subtests**; the Preview smoke fixture now writes Hebrew content as UTF-8 on Windows. JavaScript syntax and `git diff --check` passed.

| Capability | Status | Entry points / source | Dependencies and tests | Failure mode and corrective action |
|---|---|---|---|---|
| Real AI conversation | `BLOCKED` | `assets/app.js` → `investor_app.py` conversation API → `conversation/supervisor.py` → `intake/worker_route.py` → `intake/reservation_worker.py` | Worker queue, migration 037, provider credentials, activation flags and caps; `test_intake_assistant_he.py`, `test_intake_worker_route.py`, `test_conversation_os.py` | Source path is implemented, but no authenticated real-model turn was observed. Run the capped Preview acceptance journey with authorized access; do not infer success from flags or deployment readiness. |
| Conversation and brief persistence | `IMPLEMENTED_NOT_VERIFIED` | `conversation/store.py`, `brief_repository.py`, conversation GET/POST endpoints | Postgres migrations 036-037; in-memory/idempotency and schema tests in `test_conversation_os.py`, budget integration in `test_intake_budget_pg.py` | Local database is absent. Verify account isolation, restart recovery, and duplicate submission against the authorized staging database. |
| Requirements, Architect plan, and approval | `VERIFIED_TEST_ONLY` | `discovery.py`, `planning/architect.py`, build-contract and approval endpoints in `investor_app.py` | Registries, brief revisions and PostgreSQL approval state; `test_conversation_os.py`, `test_discovery_and_approval.py`, `test_m5_build_contract_binding.py` | Unit/regression coverage is not a live customer approval transaction. Exercise revision binding and duplicate approval in staging. |
| Durable build, verification, and repair | `VERIFIED_TEST_ONLY` | Build API in `investor_app.py`, worker pipeline in `worker_tasks.py`, `repair_loop.py` | RQ/Redis, worker host, isolated sandbox; `test_build_state_machine.py`, `test_j3_three_repair_round_policy.py`, `test_worker_deploy_recovery.py` | No live worker-host build or controlled repair was run here. Verify crash/retry and bounded repair on staging. |
| Authenticated Preview, versions, and export | `BLOCKED` | Preview/version/export endpoints in `investor_app.py`, `preview_runtime.py`, `preview_access.py` | Protected Preview authorization and isolated preview runtime; `test_preview_access.py`, `test_preview_router.py`, `test_preview_smoke.py`, `tests/integration/test_live_preview_runtime.py` | HTTP 401 prevented authenticated E2E; Docker is unavailable locally. Obtain the approved bypass and verify actual health, access controls, modification, and export. |
| Cost reservation and settlement | `VERIFIED_TEST_ONLY` | `intake/budget.py`, `intake/reservation_worker.py`, `routed_gateway.py` | Migration 037, PostgreSQL and provider usage records; `test_intake_budget_pg.py`, `test_actual_cost_settlement.py` | No provider call or live settlement was authorized here. The proposed capped acceptance run is estimated only; actual spend remains $0 in this session. |

## Readiness

The source and merge-compatibility CI gates are green at the inspected PR head, and the Windows registry-freshness mismatch is covered by a regression test. Authenticated deployment verification, real PostgreSQL durability, worker-host recovery, paid model execution, and live Docker preview remain open operational gates. No production changes or paid provider calls were made.
