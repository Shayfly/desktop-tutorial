# STATUS — M1 async builds / M3 running preview / M4 natural-language modification

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

M4.95 machine truth SHA-256: `318691c9c510c3ddd06cbe434d0924477b66504b63ea662e2c7b3405292265d9`

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
