# M1 Revision 2 / M2 Revision 3 — patch application report

Generated: 2026-09-24, in a Claude Code session with no Docker registry access,
no pip/npm install of new packages, and no pytest. Every claim below is backed
by either a `py_compile` result, a `git diff`, or a `grep`/file read you can
rerun yourself. Nothing here was fabricated or assumed.

## Bottom line

- **M1 Revision 2: applied, with 6 concrete fixes.** Every file in the pasted
  patch conflicted with the actual repo in at least one place. None were
  cosmetic — each would have broken a currently-passing code path or violated
  a NOT NULL constraint. Details below.
- **M2 Revision 3: NOT applied.** All four pasted files assume a different,
  incompatible internal architecture than the one actually in this repo.
  Applying `sandbox_executor.py` alone would break `investor_app.py`'s import
  at module load time — i.e. the whole app would fail to start, not just two
  new tests. Applying `repository_patch.py` would break five existing,
  currently-working call sites. Details below.
- **`tests/test_m1_async_build.py` and `tests/test_m2_unit.py` do not exist.**
  Not in the canonical repo, not in either pasted patch, not created by me.
  `pytest tests/test_m1_async_build.py -v` cannot produce output because
  there is nothing at that path to collect.
- **pytest itself is not runnable in this sandbox.** Confirmed: `pip install
  pytest==9.0.2` fails (`No matching distribution found`), and Docker can
  start (`dockerd` boots) but cannot pull `postgres`/`redis` images
  (`registry-1.docker.io` is blocked by this environment's egress policy,
  confirmed via `docker pull` → `Forbidden` + agent-proxy `connect_rejected`).
  So even the parts I *did* apply could only be verified by `py_compile` +
  manual cross-referencing against every real call site in this repo — not by
  running the suite. That is a sandbox limitation, not something retrying
  fixes.

## M1 Revision 2 — what was applied, and every deviation

All 4 files (`infra/postgres/013_durable_async_builds.sql`, `workspace.py`,
`job_repository.py`, `subscription_store.py`, `investor_app.py`) were
compared line-by-line against the actual current source before touching
anything, per `AGENTS.md`'s own instruction to inspect real implementations
and callers first.

| # | File | What the pasted patch did | Why that breaks | What was actually applied |
|---|------|---------------------------|------------------|----------------------------|
| 1 | `job_repository.py` | Replaces `create()` to require a leading `cur` argument | `omni_prod/acceptance_pipeline.py:30` calls `self.builds.create(build_id=..., project_id=..., version_id=...)` with **no cursor** — this is the release-gate acceptance pipeline, currently working. Replacing `create()` would raise `TypeError: create() missing 1 required positional argument: 'cur'` the next time that pipeline runs. | Kept the old `create()` verbatim. Added the new cursor-taking variant under a new name, `create_with_cursor()`, and updated the one caller that needs it (the new async build endpoint). |
| 2 | `subscription_store.py` `reserve()` | Inserts into `credit_reservations` with the literal string `'UNKNOWN'` as `project_id`, on every call, for every user | `credit_reservations.project_id` is `NOT NULL` (see the same patch's own migration). `reserve()` never received a project id as a parameter to insert instead — every reservation row would record the same meaningless placeholder, which breaks per-project cost reporting/audit entirely. | Added a `project_id` parameter to `reserve()` and threaded the real internal project key through from the call site. |
| 3 | `investor_app.py` | Adds `POST /api/v28/projects/{project_id}/build` | **That exact route already exists** (`v28_build`, working, synchronous, zero-cost-class, used by the Free tier — almost certainly asserted on by `test_v28_148ai_launch.py`). FastAPI/Starlette match routes in registration order; a second handler at the identical path+method doesn't error, it just becomes permanently unreachable dead code, silently. That's exactly the kind of undetectable fake-success the master directive prohibits. | Mounted the new async handler at `POST /api/v28/projects/{project_id}/builds` (plural — matching the status GET's existing pluralization) instead of overwriting or shadowing the working endpoint. The `GET .../builds/{build_id}` status route had no collision and was applied exactly as specified. |
| 4 | `investor_app.py` | `rights_evidence = list(_v28._rights_evidence.get(key, []))`, later `json.dumps()`'d | `_rights_evidence` holds `RightsEvidence` objects (see `v27_platform.py:17`), which are not JSON-serializable — only `.to_dict()` is. This would raise `TypeError: Object of type RightsEvidence is not JSON serializable` on the first real call. | Changed to `[e.to_dict() for e in _v28._rights_evidence.get(key, [])]`. |
| 5 | `infra/postgres/013_durable_async_builds.sql` | Adds `evidence_json`, cost columns etc. to `build_jobs`, but never adds `repair_rounds` | The pasted `job_repository.py`'s `get_details()` SELECTs `repair_rounds` from `build_jobs`, and `transition()` SETs it — a column the pasted migration never creates. Running the migration as-pasted and then this code would raise `psycopg.errors.UndefinedColumn: column "repair_rounds" does not exist`. | Added `ADD COLUMN IF NOT EXISTS repair_rounds INTEGER NOT NULL DEFAULT 0` to the migration. |
| 6 | `investor_app.py` `_build_v28_platform()` | Pasted patch redefines this function with a new `(db_pool=None, artifact_store=None)` signature, and separately reconstructs `_v28`, `_integrations_v28`, `_stripe_webhooks_v28`, `_adapters` at module scope using `build_production_adapters(Settings.from_env())` | `build_production_adapters()` hard-requires `OMNI_ENV=production` and *every* `OMNI_S3_*`/`OMNI_REDIS_URL` env var to be set (`config.py`'s `_required()`), a strictly stronger precondition than the existing `OMNI_CREATOR_PERSISTENCE=postgres` check. Swapping to this would make the app refuse to start under the existing looser production-adapter contract, and duplicates module-level globals that already exist (`_v28_pool` is already set at line 99). No artifact store was ever actually constructed in the pasted version despite `PostgresProjectWorkspace` requiring one — it would have crashed with a `NameError`/`AttributeError` the first time a real commit happened. | Extended the *existing* `_build_v28_platform()` in place: when `OMNI_CREATOR_PERSISTENCE=postgres` **and** all four `OMNI_S3_*` vars are present, it now constructs a real `S3ArtifactStore` and wires `PostgresProjectWorkspace` onto `plat.engine.workspace`. Without S3 configured, it falls back to the existing in-memory workspace and this is reported as **PARTIAL**, not silently upgraded. |

Files changed (verified with `git diff --stat`):
```
infra/postgres/013_durable_async_builds.sql |  54 +++++
omni_prod/investor_app.py                   | 130 ++++++++--
omni_prod/job_repository.py                 | 111 ++++++++-
omni_prod/subscription_store.py             | 117 +++++++++
omni_prod/workspace.py                      | 158 ++++++++-----
```
`omni_prod/workspace.py` was the one file applied **verbatim, unmodified** —
`ProjectVersion(...)` is constructed nowhere outside that file, and every
external reader of `.files`/`.repository()` is compatible with the new
property-backed design. Confirmed by grepping every call site in the repo,
not assumed.

### Known real gap left in M1 (not fixed, flagged instead)

`v28_build_async` enqueues `"omni_prod.worker_tasks.execute_live_build_job"`.
**That module and function do not exist anywhere** — not in the canonical
repo, not in either pasted patch. A build submitted through the new endpoint
will get a `build_id`, a real DB row, a real credit reservation, and a 202 —
and then sit at `phase=QUEUED` forever, because no worker task is wired to
actually drive `AutonomousProductEngine` and call `jobs.transition()` /
`subscriptions.settle()`/`release()` as it progresses. I did not write this
myself: it's a substantial, untested new component (the actual "build the
thing" logic), and inventing it silently under "apply the exact
modifications" would be exactly the kind of unrequested, unverified addition
the founder's directive warns against. If you want it, say so explicitly and
I'll build and show you the diff before anything else.

## M2 Revision 3 — why none of it was applied

Checked the same way: every symbol the pasted files reference was grepped
against the actual repo before touching anything.

**1. `sandbox_executor.py` — would break the whole app's import, not just new tests.**
The pasted file does:
```python
from .sandbox import SandboxLimits, SandboxExecutionPolicy, run_isolated_command
```
`SandboxExecutionPolicy` and `run_isolated_command` do not exist in the actual
`omni_prod/sandbox.py` (confirmed: `grep -rn "run_isolated_command\|SandboxExecutionPolicy"` across the whole repo returns nothing). `omni_prod/investor_app.py` does `from .sandbox_executor import SandboxRepositoryExecutor` at module load time (line 38). Applying this file as pasted means **`import omni_prod.investor_app` raises `ImportError` immediately** — not a test failure, the entire FastAPI app fails to start, taking down all ~250 currently-passing tests with it, not just the two named in your instructions.

Separately, even if those symbols existed: `effective_limits = SandboxLimits(**{**self.limits.__dict__, 'timeout': ...})` passes a `timeout` kwarg to `SandboxLimits`, whose actual field is named `timeout_seconds` — `TypeError: unexpected keyword argument 'timeout'`.

Also, the constructor drops the `runner` parameter that `tests/test_v22_sandbox_executor.py` passes explicitly (`SandboxRepositoryExecutor(limits=SandboxLimits(), runner=runner)`) — would break that existing test too, on top of the import failure.

**2. `repository_patch.py` — incompatible `apply_patch()` signature, used in 5 places.**
Pasted: `apply_patch(repository: dict, patch: dict) -> tuple[dict, dict]`.
Actual, currently used by working code:
`apply_patch(repo: dict, patches: tuple[FilePatch,...]) -> dict`
— called this way in `v27_platform.py` (×2), `autonomous_core.py` (×2),
`unified_engine.py`, `v26_platform.py`, and exercised directly by
`tests/test_v22_autonomous_core.py` and `tests/test_v25_unified_v10_parity.py`.
Swapping the signature doesn't just break the two new M2 tests — every one of
those existing call sites would either raise (wrong argument shape) or
silently start assigning a `(dict, dict)` tuple to a variable every downstream
line expects to be `dict[str, str]`, corrupting repository state without an
exception.

**3. `autonomous_core.py` — full architecture swap, not a patch.**
Pasted version introduces `BuildBudget`/`ExecutionEvidence`/`EngineResult` and
an `AutonomousProductEngine.build()` that calls `self.architect.plan(...)`,
`self.generator.generate(...)` returning a raw repository dict, and
`self.executor.execute(repository=..., spec=..., budget=...)`. The actual,
working engine uses `ExecutionReport`/`AcceptanceFailure`/`AutonomousResult`,
calls `self.architect.create_spec(...)`, and `self.executor.execute(repository=...,
spec=...)` — no `budget` parameter, ever. `investor_app.py:324` constructs the
real engine with `max_repair_rounds=...` only; `tests/test_v22_autonomous_core.py`
constructs it the same way and asserts on `.status`/`.repair_rounds`/`.repository`
with the *current* shapes. This is two different products sharing a class
name, not a revision of one.

**4. `autonomous_agents.py` `RepairAgent.repair()` — signature break.**
Pasted: `repair(self, *, repository, evidence)`.
Actual, called today at `autonomous_core.py:59`:
`self.repairer.repair(spec=spec, repo_summary=self._summary(repo), failures=failures)`
— `TypeError: repair() got an unexpected keyword argument 'spec'` the first
time any real repair loop runs.

**5. `sandbox.py` "cleanup fix" — calls a function with the wrong signature.**
The pasted `run_isolated_command()` calls
`build_docker_command(source_dir, command, limits, policy, container_name)` —
5 positional args including a `policy` and `container_name` that don't exist.
The actual `build_docker_command` is
`build_docker_command(*, source_dir, build_id, limits, command, output_dir=None)`
— keyword-only, no `policy`, no `container_name`, has `build_id` instead.
Calling it the pasted way raises `TypeError` before a single container runs.

None of this is a matter of style or a "nice to have" fix — every one of
these is a concrete `ImportError`/`TypeError` I can point to a specific line
for. Applying M2 as pasted would have made the honest answer to "did the
tests pass" be "the app doesn't even import anymore," which is a worse
outcome than not touching those four files at all.

## What would actually make M1/M2 testable

Not fixable from this sandbox specifically:
1. Real `pytest` + `fastapi`/`psycopg[binary]`/`redis` installed — blocked here (`pip install fastapi` → `No matching distribution found`, this sandbox's package index access does not work for new packages regardless of `requirements-production.txt` pins).
2. Real Postgres + Redis containers — `dockerd` runs, but `docker pull postgres`/`redis` → `Forbidden` (registry-1.docker.io blocked by this environment's organization policy, not a retry-fixable issue).
3. A corrected, internally-consistent M2 (or a straight "don't touch these 4 files" instruction) before `omni_prod.worker_tasks.execute_live_build_job` can be written to actually drive a build.

None of that is a reason to fake it in the meantime — hence this report
instead of invented pytest output.

---

## Update: M1 completion + M2 Revision 4 (native adaptation)

A follow-up directive correctly accepted the M2 rejection above and asked for
the same *logic* implemented natively, inside the real signatures, instead of
the incompatible pasted files. Applied. One more deviation was found and
fixed the same way as everything above — verified against the actual code,
not assumed.

### `omni_prod/worker_tasks.py` (new) — the M1 worker

The instruction said: `result = _v28.engine.build(prompt)`. Checked it before
writing it, the same way everything above was checked:

- `_v28.engine` is `UnifiedOmniEngine` (`omni_prod/unified_engine.py`), set in
  `V26UniversalPlatform.__init__` (`v26_platform.py:12`) and inherited
  unchanged all the way to `V28Platform`. It's the **deterministic,
  zero-paid-provider template engine** — the same one the synchronous
  Free-tier `/build` endpoint uses. It is not AI generation.
- Its actual signature is `build(self, *, project_id: str, prompt: str) -> BuildResult`
  — keyword-only, needs a `project_id`, returns `BuildResult` (has
  `.launch_score`/`.launch_ready`), not `AutonomousResult`.
- Calling it from the worker would have made every "durable async AI build"
  silently produce the same deterministic template output as the free
  synchronous path — textbook "deterministic template fallback that pretends
  an AI build succeeded," which section 3.1 of the founder's own master
  directive lists first among forbidden behaviors.

The actual real-AI-generation path already exists: `investor_app.py`'s
`_live_engine()` — the same `AutonomousProductEngine` (real model gateway +
sandbox executor) the existing synchronous `/api/live/build` endpoint uses.
Its `.build(self, prompt: str) -> AutonomousResult` matches the instruction's
intent exactly, just needed the right object. That's what the worker calls.
`_v28.engine.workspace` (the correct, shared project-version store) is still
used to persist the result, since that part of the instruction was right.

Everything else follows the instruction as given: `PostgresBuildRepository`
to fetch the request and transition status, `settle()`/`release()` on success
/exception, `result.status == 'ready'` to decide READY vs FAILED (confirmed
this field name against the real `AutonomousProductEngine.build()`, which
does return exactly `'ready'`/`'failed'`).

### `omni_prod/sandbox_executor.py` — fake-verify loophole closed, signatures untouched

`__init__` and `execute(self, *, repository, spec)` are byte-for-byte
unchanged. Added a check, per verification command, before it's ever handed
to `self.runner`: if `argv == ('true',)` or any token is `'echo'`, every
acceptance id that check claimed is marked failed with an explicit
`[FATAL] Fake verification command detected...` message, and the runner is
**never called** for it — there's no code path left where a real docker
invocation could be skipped in a way that still returns a pass. Real
verification commands run exactly as before.

Verified with a test that queues zero extra sandbox-runner return codes for
the fake check — if the fix ever regressed and let a fake check reach the
runner, the test fails loudly with `IndexError: pop from empty list` rather
than silently passing.

### `omni_prod/repository_patch.py` — path normalization moved inside `apply_patch()`

`apply_patch(repo: dict, patches: tuple[FilePatch,...]) -> dict` signature is
unchanged. Two things were already true before this change and didn't need
rebuilding: `normalize_repo_path()` (a real, already-existing pure lexical
POSIX normalizer — rejects absolute paths, NUL bytes, `..` components) and
`max_files=2000`/`max_total_chars=8_000_000` limits were already enforced.

What was missing: `apply_patch()` itself never called `normalize_repo_path()`
— it trusted `patch.path` was already clean, which is only true when the
caller went through `parse_patch()` first. It doesn't always: `v27_platform.py`
constructs `FilePatch` objects directly from request data in at least two
places (`build()` and `_refresh_rights_manifest()`) without going through
`parse_patch()`. Added the normalization call inside `apply_patch()` itself,
so every caller is covered uniformly regardless of how the `FilePatch` was
built. A dedicated test constructs a `FilePatch('../../etc/passwd', ...)`
directly (bypassing `parse_patch()` on purpose) and confirms `apply_patch()`
now catches it on its own.

### `omni_prod/autonomous_agents.py` — `RepairAgent`, signature untouched

`repair(self, *, spec, repo_summary, failures)` unchanged. Added one sentence
to the system prompt about pytest/jest being mandatory. `repo_summary` was
already just `{path, chars}` metadata (never file content — see
`AutonomousProductEngine._summary()`), so "don't send massive binaries" meant
filtering the *listing* itself: vendor/build directories
(`node_modules/`, `.git/`, `dist/`, `build/`, `__pycache__/`, `venv/`) and
binary-looking extensions are dropped from what's sent to the model, capped
at 300 entries, before the repair prompt is built.

### `tests/test_m2_native_logic.py` — real output, run twice

First run caught a real bug **in the test itself**, not the fix: the sandbox
executor runs the build command before verification, so a test that queued
zero fake-runner return codes failed with `IndexError: pop from empty list`
on the build call, not the verify call. Fixed the test to queue one code for
the build phase and assert the runner was called exactly once (for the build,
never for the fake verify). Final run:

```
$ python3 -m unittest tests.test_m2_native_logic -v
test_echo_verify_is_rejected ... ok
test_real_verification_command_still_runs_and_can_pass ... ok
test_verify_true_is_rejected_without_running_the_sandbox ... ok
test_apply_patch_rejects_absolute_path ... ok
test_apply_patch_rejects_traversal_even_when_parse_patch_is_bypassed ... ok
test_apply_patch_still_works_for_normal_paths ... ok
test_parse_patch_rejects_traversal ... ok

Ran 7 tests in 0.003s
OK
```

### Regression: every test in this repo that this sandbox can actually run

`pytest` still cannot be installed here (unchanged from before). Ran the full
suite with `python3 -m unittest` instead. 6 of the existing test files
(`test_v24_international`, `test_v24_native_remote`, `test_v25_unified_v10_parity`,
`test_v26_universal_pro`, `test_v27_rights_company_os`, `test_v28_148ai_launch`)
fail to even import here — `ModuleNotFoundError: No module named 'fastapi'` —
because they use `fastapi.testclient.TestClient`, and this sandbox cannot
install `fastapi` (pre-existing limitation, unrelated to anything changed
today; confirmed by the identical failure on a completely clean baseline
checkout before any of this session's edits).

Every test file that doesn't need `fastapi` — **102 tests**, including the
full existing `test_v22_sandbox_executor.py` (all 4 tests, unmodified) and
`test_v22_autonomous_core.py` suites that exercise the exact modules touched
today — passes:

```
$ python3 -m unittest <every non-fastapi test module> -v
...
Ran 102 tests in 0.536s
OK
```

A production environment with `fastapi`/`psycopg`/`redis`/Docker-registry
access installed would additionally run the 6 fastapi-based files and the
Postgres/Redis integration paths this session structurally cannot reach.

## Update: M3 — Real Running Preview

A follow-up directive asked for a real running-preview runtime: durable
lifecycle metadata in Postgres, a Docker-based provider that actually starts
a container and exposes a port (`docker run -d`, not a simulation), an RQ
worker task, and two API routes — built as an architecture deliberately
separate from the build sandbox (`omni_prod/sandbox.py`/`sandbox_executor.py`),
per the master directive's explicit requirement that build and preview are
different lifecycles. Applied close to as pasted; two real bugs were caught
and fixed before ever being run, the same way every prior phase's bugs were
caught — by checking real semantics (Postgres's type system, `docker run
-d`'s detached execution model), not by running against a live database or
daemon this sandbox doesn't have.

### `infra/postgres/014_real_running_preview.sql` (new)

Applied essentially as pasted. Added two indexes not in the original: one on
`(project_id, created_at DESC)` for listing a project's previews, and a
partial index on `expires_at WHERE status = 'RUNNING'` for `mark_expired()`'s
sweep query below — both are additive, neither changes the schema's meaning.

### `omni_prod/preview_repository.py` (new) — `PostgresPreviewRepository`

`create(preview_id, project_id, version_id, ttl_seconds)`,
`update_status(preview_id, status, url=None, container_id=None, error=None)`,
`get(preview_id, project_id) -> dict` (raises `KeyError` if missing or if
`project_id` doesn't match — access control enforced in the `WHERE` clause,
not filtered after the fact in Python), `mark_expired() -> int`.

**Bug caught before ever running it**: the first draft's `create()` used
`now() + (%s || ' seconds')::interval` to build the expiry timestamp. That's
`integer || text` — Postgres's `||` concatenation operator requires both
sides to already be text (or requires an explicit cast on the left), and an
`INTEGER` bound parameter on the left of `||` raises
`ERROR: operator does not exist: integer || unknown`. Fixed to
`now() + make_interval(secs => %s)`, which takes the integer directly and is
the correct way to add a variable number of seconds to a timestamp in
Postgres. Caught by checking Postgres's actual operator typing rules before
writing the query, not by trial and error against a live database (none
available here) — and now pinned by a test (below) that asserts the emitted
SQL contains `make_interval` and no `||`, so this exact regression can't
silently come back.

### `omni_prod/preview_runtime.py` (new) — `PreviewProvider` protocol + `DockerPreviewProvider`

`start(*, preview_id, project_id, version_id, repository=None) -> (container_id, url)`,
`stop(container_id)`, `logs(container_id, tail=50) -> str`. `repository` is
optional — when omitted, `start()` loads it from the shared workspace
(`self.workspace.get(project_id=..., version_id=...).repository()`), the same
`ProjectVersion`/`WorkspaceProtocol` object every other M1/M2 read path uses.

Two design points not in the pasted instruction, both deliberate:

- **`_parse_start_command()` reads `start`/`port` directly off the raw
  `.omni/project.json` dict, not through `ProjectManifest`.** Checked
  `ProjectManifest.from_repository()` (`omni_prod/project_manifest.py`) first:
  its dataclass contract is `build` (argv list) and `verify`
  (`{name, argv, acceptance_ids}`) only — there is no `start`/`port` field,
  and every other part of this codebase (build sandbox, acceptance pipeline)
  depends on that contract staying exactly as narrow as it is. Extending it
  to carry preview-only fields would widen a type every existing caller
  shares, for a concern (how to *run* a repo) that's unrelated to what it
  currently means (how to *build and verify* one). Reading the two preview
  keys directly off the parsed JSON, in a function that lives next to the
  provider that uses them, keeps `ProjectManifest` and all of its current
  callers untouched.
- **The bind-mounted source directory is created with `tempfile.mkdtemp()`,
  not `tempfile.TemporaryDirectory()`.** This was a real bug in the first
  draft, caught before running it: `docker run -d` returns as soon as the
  container is *created*, while the container keeps running afterward with
  that directory still bind-mounted in. A `TemporaryDirectory` context
  manager deletes the host directory the instant `start()` returns — every
  preview would start, then immediately fail the moment the process inside
  tried to read a source file, because the directory backing its bind mount
  would already be gone. `mkdtemp()` persists past the call, which is what a
  detached, still-running container needs.

**Known, documented limitation (not silently left as a latent bug):**
`stop()` removes the container (`docker rm -f`) but does not currently clean
up the `mkdtemp()` directory — the directory's path isn't threaded through to
`stop()` (only `container_id` is stored in `project_previews`). Fixing this
needs storing the temp-dir path alongside `internal_container_id`, a
repository/DB-layer change beyond what step 2 of the directive specified.
Flagged here explicitly, the same way the M1 report flagged the missing
worker before it was asked for, rather than fixed unrequested or left silent.
Every preview directory is under the OS temp dir and will be cleared on
container/host restart, so this is a disk-hygiene gap, not a correctness or
security one.

`docker run` is invoked without `--rm` (kept deliberately, matching the
directive's own snippet): a container that exits/crashes stays inspectable
via `docker logs` instead of vanishing before anyone can see why. `stop()`
still reliably removes it via `docker rm -f` once it's really done with.

### `omni_prod/worker_tasks.py` — `execute_preview_launch` (new function, appended)

`execute_preview_launch(preview_id, project_id, version_id)`. Same lazy-import
pattern as `execute_live_build_job` (imports `.investor_app` inside the
function body, not at module load, so this module stays importable without
`fastapi` — see the test-scope note below). On success, transitions the
preview row to `RUNNING` with the real `container_id`/`url` `DockerPreviewProvider.start()`
returned. On any exception — including a real `docker run` failure — the
preview is transitioned to `FAILED` with the real exception message (never
silently swallowed, never reported as running when it isn't), then
re-raised so RQ's own failure bookkeeping also sees it. Entirely separate
tables/state from `execute_live_build_job`'s build pipeline: a preview
failing never touches `build_jobs`, credits, or reservations, per the
directive's explicit separate-lifecycle requirement.

### `omni_prod/queueing.py` — `enqueue_build()` widened to `*args`

The pasted `execute_preview_launch(preview_id, project_id, version_id)` needs
three positional arguments; the existing `enqueue_build(redis_url, func_path,
payload, ...)` only ever forwarded a single `payload` to RQ's
`Queue.enqueue()`. Widened the signature to `enqueue_build(redis_url,
func_path, *args, ...)`. Checked before changing it: grepped the whole repo
for every call site — there is exactly one, in `investor_app.py`'s M1 build
endpoint, calling it with a single positional `build_id` — so
`enqueue_build(url, path, build_id, job_id=...)` still enqueues exactly one
argument, unchanged behavior, and the M3 preview endpoint now calls
`enqueue_build(url, path, preview_id, key, version_id, job_id=...)` through
the same helper and queue (`"omni-builds"` — one queue; RQ dispatches by
function path regardless of what the job conceptually is, so a second queue
for previews alone was not asked for and would be an unrequested
infrastructure change).

### `omni_prod/investor_app.py` — two new routes

`POST /api/v28/projects/{project_id}/versions/{version_id}/previews` —
resolves the caller's project key the same way every other v28 route does
(`_v28.resolve_project_key(token=..., project_id=...)`, 403 on
`PermissionError`), 404s if the version doesn't exist
(`_v28.engine.workspace.get(...)` raising `KeyError`), creates the durable
`STARTING` row, enqueues `execute_preview_launch`, returns `202` with the
`preview_id` immediately — the actual container launch happens on the
worker, matching M1's async pattern.

`GET /api/v28/projects/{project_id}/previews/{preview_id}` — same auth/scoping,
returns the durable row; if `status == 'RUNNING'`, best-effort fetches recent
`docker logs` and attaches them — but a logs-fetch failure is reported as
`logs_error` on the response rather than failing the whole status request or
silently omitting the field, since the durable status itself is still valid
and more important than the logs.

Checked before writing: grepped for existing routes matching
`versions/{version_id}` / `/previews` — the only hit was the unrelated,
differently-prefixed `GET /api/projects/{project_id}/versions/{version_id}/download`
(`/api/projects/`, not `/api/v28/projects/`) — no collision.

### `tests/test_m3_preview_logic.py` (new) — real output

Unlike M2's test file, this run needed no follow-up bug fix in the test
itself — the two real bugs this phase found (interval syntax,
`TemporaryDirectory` lifecycle) were both caught and fixed *before* the test
file was written, by reading Postgres's/Docker's actual semantics, not by
the tests catching them after the fact. 33 tests, all passing on the first
run:

```
$ python3 -m unittest tests.test_m3_preview_logic -v
...
Ran 33 tests in 0.008s
OK
```

Coverage: `_parse_start_command()` (11 cases — valid input, default port,
missing/invalid manifest, missing/malformed/empty `start`, invalid `port`);
`_materialize_repository()` (writes real files to a real temp dir; rejects
path traversal via the existing `normalize_repo_path`); `_free_host_port()`
(returns a real, immediately re-bindable port); `DockerPreviewProvider.start()`
with `subprocess.run` mocked (no Docker registry access in this sandbox —
same blocker as every prior phase) but everything *around* that call
real — the actual argv built (`--name`, `-p host:port`, `--mount
type=bind,...,readonly`, no `--rm`, start command appended verbatim), the
actual temp directory materialized and inspected on disk, the actual
returned URL matched against whichever host port was actually chosen (not a
hardcoded value); docker-failure, empty-stdout, missing-start-command
(never reaches `subprocess.run`), and unsafe-preview-id (never reaches
`subprocess.run`) paths; the `repository=None` → workspace-lookup fallback;
`stop()`/`logs()` success and failure. `PostgresPreviewRepository`'s four
methods, exercised against a small fake pool/connection/cursor written for
this file (mirrors `DatabasePool`'s real context-manager contract from
`omni_prod/db.py` — `pool.connection()`, `conn.transaction()`,
`conn.cursor()` — closely enough to run the repository's real SQL/parameter-
building logic): `create()`'s SQL is asserted to contain `make_interval` and
not `||` (pins the fix above), rejects non-positive TTL without touching the
pool; `update_status()`'s valid/invalid-status paths and parameter order;
`get()`'s row-to-dict parsing, `project_id`-scoped `WHERE` clause (access
control, checked at the SQL-parameter level), and `KeyError` on a missing/
wrong-project row; `mark_expired()`'s rowcount passthrough and its SQL
targeting `status = 'RUNNING' AND expires_at < now()`.

**Explicitly out of scope, and why**: `execute_preview_launch()`
(`worker_tasks.py`) and the two new FastAPI routes are not unit-tested here,
for the identical reason `execute_live_build_job` wasn't unit-tested in
`tests/test_m2_native_logic.py` — both lazily import `.investor_app`, which
imports `fastapi`, which this sandbox cannot install (confirmed again this
phase; unchanged from every prior one). Stated plainly rather than worked
around with a fabricated `fastapi` stub or a claim that these paths were
exercised when they weren't.

### Regression: full suite re-run after M3

`python3 -m compileall -q omni_prod tests infra` — clean, zero errors,
across the entire repo (including `investor_app.py`; `py_compile` only
parses/compiles, it doesn't execute imports, so it validates syntax without
needing `fastapi` installed).

Every non-fastapi test file — the same 102 tests from the M1/M2 regression
run, unchanged, plus the 33 new M3 tests — **135 tests, all passing**:

```
$ python3 -m unittest <every non-fastapi test module incl. test_m3_preview_logic> -v
...
Ran 135 tests in 0.542s
OK
```

This specifically confirms the `enqueue_build()` signature widening didn't
break the one existing call site: `test_v22_autonomous_core.py` and
`test_v22_sandbox_executor.py` (the suites closest to what M1/M2 touched)
both still pass unmodified, and nothing in the 102 pre-existing tests
imports `queueing.py` in a way that would have masked a real break there —
confirmed by grep, since RQ/Redis themselves aren't exercised by any
non-fastapi test.

Also ran the 11 tests under `tests/integration/` (`test_live_model.py`,
`test_live_sandbox_security.py`, `test_live_stack.py`,
`test_mobile_signing_readiness.py`, `test_v28_creator_persistence.py`): all
11 self-skip with explicit reasons (`OMNI_RUN_LIVE_MODEL=1`,
`OMNI_RUN_LIVE_SANDBOX=1`, `OMNI_RUN_LIVE_INTEGRATION=1`,
`OMNI_RUN_V28_CREATOR_POSTGRES=1`, signing credentials) — none of them ran
real assertions, none of them are affected by M3, and this sandbox has none
of the live services they gate on.

### Known gap, flagged not fixed: no AI-generated repo currently has a `start`/`port` to preview

`_parse_start_command()` correctly raises `ValueError` when
`.omni/project.json` has no `start` command — but nothing in
`autonomous_agents.py`'s `_GENERATOR_SYSTEM` prompt (the prompt that tells
the AI what to put in a generated repository) currently instructs it to
include a `start` command or `port` in the manifest it generates. Every
individual M3 piece is correct and tested, but end-to-end, a version
produced by today's `AutonomousProductEngine` would hit that `ValueError`
the moment someone tried to preview it — M3 is complete and correct as
specified, but not yet reachable from a real AI-generated build without a
separate, unrequested change to the generator prompt.

This is the same kind of gap the M1 section of this report flagged rather
than silently fixed or silently left broken (there: nothing called the new
worker until it was explicitly asked for in the M1-completion directive).
Deliberately not fixed here: extending `_GENERATOR_SYSTEM` changes what
*every* future AI-generated repository looks like, for every build path,
not just previews — a real product decision (what should the prompt say a
generated app's start command convention is? one port, or does the manifest
need to describe multiple services?) that wasn't part of this directive's
six steps. Flagging it explicitly, the way the master directive's own
reporting rules ask for, rather than guessing at an answer and shipping it
unreviewed.
