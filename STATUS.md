# STATUS — M1 async builds / M3 running preview / modifier engine

Required by `AGENTS.md`. Covers only the M1–M3 work and the modifier-engine
stub applied in this repository so far. Evidence and exact commands are in
`PATCH_APPLICATION_REPORT.md`. See `GOVERNANCE.md` for which other documents
in this repo are still current versus historical. Last updated 2026-09-24.

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
- **`ModifierEngine` execution of `change_request`s.** Classification only; a
  billable "add a new capability" follow-up is never actually applied to the
  repository — see the class docstring in `omni_prod/modifier_engine.py` for
  why (it can reference no existing acceptance id, so `RepairAgent`'s
  "fix these failing criteria" framing doesn't fit it; it needs its own
  generation prompt, a real product decision not made here).
- **`ModifierEngine` is not wired to any route or worker task.** No
  `POST .../projects/{id}/modify`-style endpoint and no
  `execute_modifier_job` exist yet; nothing calls `ModifierEngine.modify()`
  outside `tests/test_modifier_engine.py`. It also has no durable
  `ProductSpec` to read for an existing project — this codebase does not
  persist the spec a project was generated against anywhere
  (`ProjectVersion` stores only the repository) — so a caller has to supply
  it from build time until that's added.
