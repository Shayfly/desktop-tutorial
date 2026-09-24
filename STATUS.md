# STATUS — M1 async builds / M3 running preview / M4 natural-language modification

Required by `AGENTS.md`. Covers the M1–M3 work, the superseded modifier-engine
stub, and the M4 natural-language product-modification system built on top of
it (see §5 below — M4 uses the vocabulary required by its own directive;
§§1–4 keep the pre-existing 4-category format so this update stays in place
rather than rewriting sections it did not touch). Evidence and exact commands
are in `PATCH_APPLICATION_REPORT.md`. See `GOVERNANCE.md` for which other
documents in this repo are still current versus historical. Last updated
2026-09-24 (M4 section added).

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
"VERIFIED" below means real code executed against real unit tests (or, for
concurrency/version mechanics, the real `MemoryProjectWorkspace`), not that
it has run in production. `fastapi`, live Postgres and live Redis are not
installable/reachable in this build sandbox (a constraint that predates M4 —
see §2 above); every route/worker-import-boundary item below is
`NOT_CONFIGURED` for that reason alone, not because the code is wrong, and
is instead proven by static AST/signature inspection. Full evidence and
exact commands: `PATCH_APPLICATION_REPORT.md` (M4 section).

### By capability (M4A–G)

| Capability | Status | Evidence |
|---|---|---|
| M4A — durable `ModificationRequest` repository (create/get/transition/complete/accept/reject/rollback, optimistic concurrency) | `VERIFIED` | `tests/test_modification_repository.py` (43 tests, fake-pool + real `MemoryProjectWorkspace`, 2 independent mutation tests) |
| M4A — transactional outbox (`modification_outbox`, `FOR UPDATE SKIP LOCKED`, dispatch) | `VERIFIED` (logic) / `NOT_CONFIGURED` (no live Postgres/Redis to prove the relay end-to-end) | `tests/test_modification_repository.py::OutboxDispatchTests`; real dispatch needs `python -m omni_prod.build_outbox_relay`-equivalent + Redis |
| M4A — FastAPI routes (propose/status/candidate/accept/reject/rollback) | `IMPLEMENTED_NOT_VERIFIED` | `omni_prod/investor_app.py`; `ast.parse()` + duplicate-route + `inspect.signature()` cross-checks against real repository/worker signatures only — no live HTTP call possible without `fastapi` |
| M4A — worker entrypoint (`execute_modification_job`, lazy-imports investor_app internals) | `VERIFIED` (orchestration logic via dependency injection) / `IMPLEMENTED_NOT_VERIFIED` (the lazy-import wiring itself, since importing `investor_app` needs `fastapi`) | `tests/test_m4_worker.py` (11 tests against `_run_modification_job`) |
| M4B — versioned `ProductSpec` repository + `project_version_specs` (exact-version scoped, no `update()`) | `VERIFIED` (logic) / `NOT_CONFIGURED` (schema not applied to a live database) | `tests/test_spec_repository.py`; `infra/postgres/016_durable_modifications.sql` |
| M4C — intent routing reused (`system_bug`/`missing_requirement`/`change_request`/`ambiguous`) | `VERIFIED` | `tests/test_m4_acceptance.py::AcceptanceGH/I/J` |
| M4C — dedicated `change_request` path (`ProductEvolutionAgent`, real spec+repo generation, not forced into `RepairAgent`) | `VERIFIED` | `tests/test_product_evolution.py`, `tests/test_m4_acceptance.py::AcceptanceJ` |
| M4D — candidate isolation (never commits to `project_versions` until `accept()`) | `VERIFIED` | `tests/test_m4_acceptance.py::AcceptanceK`; `tests/test_m4_worker.py`'s `workspace.commit.assert_not_called()` |
| M4D — accept / reject / rollback | `PARTIAL` | promotion, conflict detection and rollback logic are `VERIFIED`; `accept()` is **not** atomic across `workspace.commit()` + `spec_repo.save()` + the final status `UPDATE` (three separate Postgres transactions — `workspace.commit()` must own its own connection for its advisory lock). A crash in that narrow window leaves a live promoted version with a stale `READY_FOR_REVIEW` row. Disclosed, not hidden — see `accept()`'s docstring and `AcceptanceN`'s docstring |
| M4D — optimistic concurrency (expected-source-version semantics) | `VERIFIED` | `tests/test_m4_acceptance.py::AcceptanceU` (the directive's own Version 10/11 scenario, reproduced verbatim against a real workspace) |
| M4E — verification pipeline reuse (build/tests/repair/quality/security/rights/target gates) | `VERIFIED` | `CandidateModificationEngine` calls the same `quality_fn`/`security_fn`/`RightsEngine`/`Executor` as the rest of the pipeline — `tests/test_m4_modification_engine.py`, `tests/test_m4_acceptance.py::AcceptanceM` |
| M4F — deterministic diff (repository + spec) | `VERIFIED` | `omni_prod/modification_diff.py`; `tests/test_modification_diff.py`, `tests/test_m4_acceptance.py::AcceptanceQR` (order-independence proven directly) |
| M4G — billing (reserve at request time, settle/release by real classification, not by spend) | `VERIFIED` (decision logic + idempotency) / `IMPLEMENTED_NOT_VERIFIED` (the route's `reserve()` call itself, same fastapi/Postgres constraint as above) | `tests/test_m4_worker.py::ResolveModificationBillingTests`; `tests/test_m4_acceptance.py::AcceptanceV` (new test — no prior coverage existed for `subscription_store.reserve()`'s own idempotency) |

### Required acceptance tests (A–W) and the concurrency requirement

All 24 (23 lettered + the concurrency requirement) are addressed in
`tests/test_m4_acceptance.py`; letters with deeper pre-existing coverage
point to it in their docstring.

| # | Claim | Status |
|---|---|---|
| A | POST returns 202 + durable id | `IMPLEMENTED_NOT_VERIFIED` — needs `fastapi`; durability it depends on (`create()`+`create_outbox()` committing first) is `VERIFIED` separately |
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
| N | accept promotes the candidate | `PARTIAL` — see M4D row above (disclosed non-atomic window) |
| O | reject leaves current version intact | `VERIFIED` |
| P | rollback restores an exact historical version | `VERIFIED` |
| Q/R | repository diff / spec diff are deterministic | `VERIFIED` |
| S | spec/version can't become mismatched | `VERIFIED` (schema PK + no `update()` path) / `NOT_CONFIGURED` for the live-schema half |
| T | retry (queued redelivery, completion redelivery) is idempotent | `VERIFIED` |
| U | concurrency — explicit conflict semantics | `VERIFIED` |
| V | reservation not double-charged on retry | `VERIFIED` |
| W | all existing regression tests remain green | `VERIFIED` — 309/309 non-fastapi tests pass (see `PATCH_APPLICATION_REPORT.md` for the exact command and count); the 8 fastapi-dependent modules are `NOT_CONFIGURED` (fail only at `ModuleNotFoundError: fastapi` on import, a pre-existing sandbox constraint, not a regression) |
| Concurrency requirement (Version 10/11 scenario) | Do not silently overwrite; B must rebase, stay alternate, or be an explicit forced accept | `VERIFIED` — reproduced verbatim in `AcceptanceU`: A accepts → Version 11; B's plain accept returns `reason='conflict'` and Version 11 is untouched; B's `force=True` accept is the explicit third option |

### Not implemented / out of scope for this M4 pass

- Live end-to-end run of the HTTP layer, Redis dispatch and Postgres schema — `NOT_CONFIGURED` (sandbox has no `fastapi`, Redis, or reachable Postgres; not a code gap).
- Full cross-transaction atomicity of `accept()` — `PARTIAL`, disclosed above; would need either a single connection spanning `workspace.commit()` and the status update, or a compensating-reconciliation job, neither of which exists yet.
- M5 and later milestones — out of scope by the directive's own stop condition; not started.
