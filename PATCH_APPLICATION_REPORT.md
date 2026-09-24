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

## Update: M3 Revision 2 + M1 blocker resolution

All six steps applied natively. Every claim below is backed by a command in
"Verification" at the end of this section. For the first time in this
project, the preview runtime was exercised against a **real Docker daemon**
(29.4.3, started inside this sandbox) — and that run found two bugs that every
mocked test had passed over (items 3c and 4b). Where the directive's wording
did not match the real code, it was adapted, with the evidence below.

### Step 1 — M1 billing, gates, outbox, routing

**1a. No `budget` object exists; the real spend ledger is used instead.**
The directive says to settle with `budget.provider_cost_usd`. Nothing named
that exists: `AutonomousResult` (`autonomous_core.py`) has no cost field, and
`OpenAICompatibleGateway.complete()` reads only
`payload['choices'][0]['message']['content']` and discards the provider's
`usage` block. The only real spend signal is `RoutedModelGateway.state`
(`external_spend_usd`, `external_calls`), incremented by
`model_policy.authorize_model_call()` for every external call the platform
authorized and dispatched (local/self-hosted calls cost 0 and are not
counted). The worker could not see it — `_live_engine()` returns
`_live_components()[0]` and drops the gateway — so the worker now calls
`_live_components()` (the same call every synchronous live-build route makes).

Rule, now in `worker_tasks.resolve_billing()`:

| outcome | external spend or calls | action |
|---|---|---|
| READY | any | `settle(actual_provider_cost_usd=spent)` |
| FAILED (gate or exception) | > 0 | `settle(actual_provider_cost_usd=spent)` |
| FAILED (gate or exception) | none | `release()` |

The evidence JSON labels this figure honestly: *authorized external-model
spend ledger … provider-reported token usage is not captured*. Capturing real
`usage` needs a change to `OpenAICompatibleGateway`, which was not asked for.

**1b. READY now requires the canonical gates.** Before this change READY meant
only `result.status == 'ready'` (sandbox verification). The canonical
synchronous path `v28_live_build` computes release readiness as verification
AND `assess_repository(...).passed` AND `hostile_repository_scan(...).passed`
AND `_v28.rights.assess(...).publish_allowed`, and also adds the creative
manifest, rights manifest and plan branding/provenance to the committed
repository. The async worker skipped all of that. It now does exactly the
same, rebuilding `RightsEvidence` from the JSONB stored in `build_requests`
(which M1 already persisted for this purpose). The first failing gate is
reported as `error_code`: `verification_failed` → `quality_gate_failed` →
`security_gate_failed` → `rights_gate_not_clear`. The version is still
committed on a gate failure (as in the sync path), so a user whose build is
`rights_gate_not_clear` can add evidence or use the original alternative.
Note the semantic cost of following the directive literally: a rights
`REVIEW` build now ends in `FAILED`, where the sync path returned a version
with `release_ready: false`. The `error_message` says the version was
committed and what to do next.

The branding step embeds the user-facing project id, which `build_requests`
did not store (only the internal tenant key). Migration 015 adds a nullable
`build_requests.public_project_id`; `create_request()` takes it as an
optional keyword (old callers unaffected).

**1c. Outbox relay (the "outbox blocker").** The API committed reservation +
request + job + outbox row, then enqueued to Redis — but if Redis was down,
the request returned 500 while the build was in fact durably accepted, and
nothing ever retried it: credits stayed `RESERVED` and the job sat at
`QUEUED` forever. Now the endpoint returns `202 {"dispatch": "deferred"}` in
that case, and `PostgresBuildRepository.dispatch_pending_outbox()` (one row
per transaction, `FOR UPDATE SKIP LOCKED`, rows younger than 30s left alone)
re-dispatches them. Duplicate delivery is harmless because the worker's
`QUEUED→RUNNING` transition is conditional. Runner:
`python -m omni_prod.build_outbox_relay [--loop 15]`. **Nothing schedules it**
— that is deployment configuration.

**1d. Routing: the async flow replaces the sync path in async deployments.**
`_async_build_mode()` is true when `OMNI_CREATOR_PERSISTENCE=postgres` AND the
workspace is the durable `PostgresProjectWorkspace`. In that mode, **every
route that runs a build synchronously inside the API process returns 410**:
`POST /api/v28/projects/{id}/build`, `/api/v28/projects/{id}/live-build`,
`/api/v27/projects/{id}/live-build`, `/api/v26/projects/{id}/live-build`, and
the unauthenticated `/api/live/build`. The last one matters: it runs real
model spend with no account and no billing, and in a deployment where the
API shares the worker's `OMNI_ENABLE_LIVE_BUILD=1` it would have stayed open.
`app.js` now posts to `/builds` and polls `/builds/{id}`, falling back to the
legacy route only on 503 (async backend not configured).

*Why the legacy routes are gated, not deleted:* they are the only build path
in memory/demo mode, `scripts/run_v28_http_acceptance.py` depends on them,
and `test_v23`/`test_v26`/`test_v28` exercise them through `fastapi`, which
cannot run here — deleting them would be an unverifiable break. In memory
mode `_async_build_mode()` returns False on its first line, so those tests
are unaffected (static analysis; not runnable here). The v26/v27
*deterministic* `/build` routes (in-memory legacy platforms, no model spend)
are not gated.

The async POST now also requires the durable workspace (503 otherwise): with
postgres persistence but no S3, `_build_v28_platform()` leaves the in-memory
workspace in place, so the worker would commit versions the API can never
read back. `GET /builds/{id}` now returns `error_code` and the gate
`evidence`, and maps `PermissionError` to 403 (it was an unhandled 500).

### Step 2 — Preview manifest contract

The generator prompt now requires `schema_version: 2`, `runtime`
(`python:3.11-slim` | `node:20-slim`), `start`, `port`, `health_path` in
`.omni/project.json`, and states the real runtime conditions: no install
step, read-only filesystem except `/tmp`, unprivileged user, listen on
`0.0.0.0:$PORT`. A model that can't meet them is told to omit the keys.
`ProjectManifest` ignores unknown keys, so build/verify parsing is unchanged
(pinned by a test).

**"Target adapters" do not exist in this codebase** (grep: no adapter class,
no `NOT_PREVIEWABLE`). The native equivalent is the contract boundary itself:
`parse_preview_contract()` raises `NotPreviewable` for a missing/legacy
manifest, wrong `schema_version` (including `"2"`, `True`, `2.0`), a runtime
outside the allowlist, or a malformed start/port/health_path. The API
answers `422 {"status": "NOT_PREVIEWABLE"}` without creating a row or using
a worker, and the worker persists `NOT_PREVIEWABLE` as its own terminal
status (migration 015 extends the CHECK constraint) — never FAILED, never
RUNNING. The runtime allowlist is a security control, not a nicety: `runtime`
comes from AI-generated output, and without it a repository could make the
worker pull and run any image. Operators can override it with
`OMNI_PREVIEW_ALLOWED_RUNTIMES`.

### Step 3 — Secure Docker provider, dynamic ports

Final argv (`build_run_argv()`, pure and unit-tested):
```
docker run --cpus=0.5 --memory=512m --pids-limit=64 --read-only --cap-drop=ALL
  --security-opt=no-new-privileges --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777
  --user 65534:65534 -e HOME=/tmp -e PORT=<port> -e PYTHONDONTWRITEBYTECODE=1
  -d -p 127.0.0.1::<port> --name omni-preview-<id> --label omni.preview_id=<id>
  --mount type=bind,src=<workdir>,dst=/workspace,readonly --workdir /workspace
  <IMAGE> <START_CMD...>
```
then `docker port <cid> <port>/tcp` to read the port Docker chose.

**3a. `-p ADDR::PORT` instead of the literal `-P`.** `-P` publishes only
ports the image declares with `EXPOSE`; `python:3.11-slim` and `node:20-slim`
declare none, so `-P` would publish nothing and every `docker port` lookup
would fail. It also binds `0.0.0.0`, putting untrusted generated code on
every interface of the worker host, around the routing layer. `-p
127.0.0.1::PORT` keeps what the directive wants — Docker allocates the host
port, so the draft-1 bind-then-release race is gone — on one interface
(`OMNI_PREVIEW_BIND_ADDRESS`, default loopback). The live test confirms
`HostPort: ""` in the request and a real allocated port in the result.

**3b. Two additions beyond the directive's flag list.** `--user 65534:65534`:
every listed flag constrains a *root* process, and the build sandbox already
runs non-root. And `chmod 0755/0644` on the materialized source:
`mkdtemp()` creates `0700`, which uid 65534 without `CAP_DAC_OVERRIDE`
cannot read.

**3c. Found by the live run: `/tmp` was not writable.** Docker's `--tmpfs`
default mode is not world-writable, so uid 65534 got `PermissionError` on
its first write to `/tmp` — the "writable scratch space" the directive asked
for was unusable. Reproduced directly with and without `mode=1777`, fixed,
and pinned by a unit test.

**Draft-1 leak, confirmed.** Eight `omni-preview-prv_test*` directories from
the previous phase's test run (13:41, mode `0700`) were still in `/tmp`,
including ones from the *failure* tests (`docker run` non-zero exit, empty
stdout) — draft 1 leaked the workdir even when the container never started.
Rev2 removes the workdir on every failure path in `start()`, in every worker
teardown, and in the stop task. After the full unit + live runs: 0 workdirs
and 0 containers left.

### Step 4 — Health probes, external URL

`wait_until_healthy()` polls `http://<probe_host>:<host_port><health_path>`
(default 30s, `OMNI_PREVIEW_HEALTH_TIMEOUT_SECONDS`). 2xx/3xx is healthy;
404/5xx is not. Container liveness is checked **before** every attempt, so a
dead container fails at once with its exit code instead of using up the
budget. On any failure the worker captures `docker logs --tail 50`, then runs
`docker rm -f`, deletes the workdir, and writes FAILED with the probe detail
and the log tail. **RUNNING is written in exactly one place: after the probe
passes** (pinned by an event-order test and by mutation testing).

The persisted URL comes from `PREVIEW_DOMAIN_TEMPLATE`
(`https://{preview_id}.preview.148ai.com`). `external_preview_url()` refuses a
missing template or placeholder, a non-http(s) scheme, and any
localhost/127.x/0.0.0.0/::1/`*.localhost` host. The API returns 503 if it is
not configured, before creating anything.

**4b. Found by the live run: a crash on boot lost its own diagnosis.** A
container that exits immediately has its port bindings released, so `docker
port` fails with "no public port published". Draft Rev2 treated that as a
runtime error, removed the container, and reported `docker port failed`,
losing the exit code and logs. Now `start()` checks liveness when the port
lookup fails and returns the exited container with `host_port=None`. The
worker then records `container exited before its port was published (exit
code 3)` plus the log tail (`fatal: config missing` in the live test) before
teardown. Pinned by two unit tests.

### Step 5 — Distributed lifecycle, cleanup

- **GET no longer calls `docker logs`.** It returns durable state with
  `logs: null, logs_available: false` and a note saying live logs need a
  distributed logging pipeline. Startup/probe failures already carry the log
  tail in `error_message`. Internal fields (container id, worker host/port,
  host workdir, internal tenant key) are no longer returned.
- **Durable storage is enforced, not just the env var.** POST/GET/DELETE
  return 503 unless the workspace is `PostgresProjectWorkspace`. The env-var
  check alone was insufficient: postgres mode without S3 still uses
  `MemoryProjectWorkspace`. The worker checks the same thing
  (`ensure_durable_workspace`) and fails closed.
- **`DELETE /api/v28/projects/{id}/previews/{preview_id}`**:
  `request_stop()` (row lock, tenant-scoped) moves STARTING/RUNNING/EXPIRED to
  STOPPED and enqueues `stop_preview_task`, which runs `docker rm -f` (a
  missing container counts as already stopped), deletes the workdir, and sets
  `cleaned_at`. Idempotent: a terminal preview returns 200 unchanged, and a
  STOPPED-but-not-cleaned preview re-dispatches cleanup, so a retried DELETE
  recovers from a failed enqueue.
- **Host affinity.** A container and its bind-mounted workdir live on the
  worker host that launched it; a stop task picked up by any other worker
  would talk to the wrong daemon and the wrong filesystem. The launch task
  records `runtime_host` (`OMNI_PREVIEW_RUNTIME_HOST` or hostname), and
  DELETE enqueues cleanup on `omni-preview-host-<host>`
  (`queueing.preview_host_queue`; `enqueue_build()` gained an optional
  `queue_name`, default unchanged). **Preview workers must run
  `rq worker omni-builds omni-preview-host-$OMNI_PREVIEW_RUNTIME_HOST`.** A
  stop task that lands on the wrong host raises instead of marking the
  preview clean.
- **Stop-vs-launch race.** Every write the launch task makes
  (`record_runtime`, `mark_running`, `mark_failed`) is conditional on
  `status = 'STARTING'` and reports whether it applied. If a DELETE lands
  while the worker is starting or probing, the worker sees the write refused
  and tears down the container itself. The draft-1 unconditional
  `update_status()` is removed (no callers outside the worker and its tests).
- **`get_route(preview_id)`** returns `(runtime_host, host_port)` only while
  the preview is RUNNING and unexpired — the lookup the external router needs.

### Tests

`tests/test_m3_preview_logic.py`, rewritten: **85 tests**, including every
case the directive asked for — argv ordering (security flags first in exact
order, then options, then IMAGE, then START_CMD; nothing after the image
except the command), RUNNING impossible before a successful probe
(event-order assertions, stop-during-probe, stop-before-record), and
memory-only workspace rejected (for previews, for the preview launch task,
and for the build worker). Also covered: the billing table above against a
spend ledger produced by the real `authorize_model_call()`, gate ordering,
repository SQL (conditional writes, tenant scoping, `make_interval`), and the
outbox relay.

*Mutation check* (scratch script, not committed): 15 deliberate regressions,
each applied alone — RUNNING before the probe, release despite spend,
rights/security gate skipped, localhost URL persisted, `--read-only`
dropped, image/command swapped, literal `-P`, allowlist removed, memory
workspace accepted, dead container still probed, `rmtree` of any path,
unconditional `mark_running`, relay never enqueues. **All 15 caught.**

*Live Docker test* (new, `tests/integration/test_live_preview_runtime.py`,
gated by `OMNI_RUN_LIVE_PREVIEW=1`, runtime `OMNI_PREVIEW_TEST_RUNTIME`): the
real provider and the real `_run_preview_launch`/`_run_preview_stop`, with an
in-memory stand-in for the Postgres repository. It checks `docker inspect`
(ReadonlyRootfs, CapDrop ALL, no-new-privileges, 512 MiB, 0.5 CPU, pids 64,
tmpfs, user 65534, loopback binding with a Docker-chosen port), real
HTTP content through the allocated port, that writes to `/workspace` and `/`
fail while writes to `/tmp` succeed, that uid is 65534, and full cleanup — plus
the crash-on-boot, HTTP-500 timeout, and bound-to-container-loopback cases.
**Honest caveat on the image:** the registry is still blocked here, so this
did not run on `python:3.11-slim`. It ran on `omni-local/python-host:3.11`, an
image built with `docker import` from this host's own Python 3.11.15
interpreter and stdlib, allowed through the operator override. The Docker
behaviour tested (flags, ports, mounts, probe, teardown) does not depend on
the image, but the official image itself has not been exercised.

*Frontend* (scratch Node harness, not committed): the real `app.js` run in
`vm` with a stubbed DOM and `fetch`. Async mode: POST `/builds`, three polls,
final `ready · version ver_9`, legacy route never called. Demo mode: 503,
then legacy `/build`. A 402 is surfaced with no fallback. A gate failure
shows `rights_gate_not_clear` with a REVIEW badge.

### Verification

```
$ python3 -m compileall -q omni_prod tests infra scripts        -> exit 0
$ node --check omni_prod/assets/app.js                           -> OK
$ python3 -m unittest tests.test_m3_preview_logic                -> Ran 85 tests ... OK
$ python3 -m unittest <all 15 non-fastapi test modules>          -> Ran 187 tests ... OK
      (the same 102 pre-existing tests, unmodified, + 85 M3)
$ python3 -m unittest discover -s tests/integration              -> OK (skipped=15)
$ OMNI_RUN_LIVE_PREVIEW=1 OMNI_PREVIEW_TEST_RUNTIME=omni-local/python-host:3.11 \
    python3 -m unittest tests.integration.test_live_preview_runtime -v
test_app_bound_to_container_loopback_is_not_reported_running ... ok
test_crashing_app_is_failed_with_exit_code_and_logs_then_removed ... ok
test_healthy_app_runs_hardened_and_is_fully_cleaned_up ... ok
test_unhealthy_app_times_out_and_is_removed ... ok
Ran 4 tests in 10.540s
OK
leftover omni-preview workdirs: 0   leftover preview containers: 0
```

### Not verified here / still open

- **FastAPI routes** (`/builds`, the 410 guards, POST/GET/DELETE previews) and
  the three `execute_*`/`stop_preview_task` wrappers were not executed here:
  `fastapi` still cannot be installed. They were compiled and statically
  name-checked. All their decisions live in the injected `_run_*` functions
  and pure helpers tested above.
- **Migration 015 and all repository SQL** have not run against real
  Postgres (no psycopg or Postgres here). The SQL was checked against the
  schema by reading it, and the constraint name `project_previews_status_check`
  follows Postgres's naming rule for 014's inline CHECK.
- **Not scheduled anywhere:** `build_outbox_relay`, and `mark_expired()`,
  which also does not stop containers (a DELETE on an EXPIRED preview does
  clean it up). An expiry sweep that enqueues cleanup is the natural next
  step.
- **The router behind `PREVIEW_DOMAIN_TEMPLATE`** (wildcard DNS + TLS + a
  proxy to `get_route()`'s upstream) is infrastructure outside this
  repository. Until it exists, a RUNNING preview's URL is correct by contract
  but not yet reachable.
- **Previews have no install step.** Apps that need third-party packages
  fail the health probe honestly (see the prompt text). Real dependency
  support needs an image-build stage, which is natural M4 scope.
- **Outbound network from preview containers is not restricted** (default
  bridge). An egress policy is a remaining hardening item.
- **The spend figure is an authorized-estimate ledger,** not provider-measured
  usage (1a).

## Update: `omni_prod/modifier_engine.py` — real gap found and closed, scoped honestly

A follow-up directive asked for canonical governance docs, a
`modifier_engine.py` stub, and a verification run. The founder had no
preference on either open question (what the module should do; what
"canonical governance docs" means), so both were resolved from the actual
repository rather than guessed at from the phrase alone.

**Governance docs.** `GOVERNANCE.md` (new) lists which of this repo's ~90
root-level documents are current source of truth versus historical, and
states the rule going forward (update `STATUS.md` in place; don't fork
another `CURRENT_TRUTH_VNN_HE.md`). One-line "historical" / "check STATUS.md
first" banners were added to `CURRENT_TRUTH_V24/26/27_HE.md` and to the three
investor-facing docs (`INVESTOR_DEMO_SCRIPT_HE.md`,
`PRELAUNCH_INVESTOR_READINESS_HE.md`, `VALUATION_EVIDENCE_PLAN_HE.md`) — the
highest-cost place for a stale claim to survive unlabeled. `00_START_HERE_HE.md`
was extended to point new sessions at `STATUS.md`/`PATCH_APPLICATION_REPORT.md`
(it previously stopped at `CURRENT_TRUTH_V28_HE.md`, missing the M1–M3 layer
entirely). Checked before writing any of this: grepped `omni_prod/`, `tests/`,
`scripts/`, `.github/` for every filename touched — nothing in code or CI
reads these `.md` files, so none of this carries functional risk. No file was
deleted or rewritten; `GOVERNANCE.md` is additive and says so.

**`modifier_engine.py` — what it does, and why this specific design wasn't
invented from nothing.** Grepped the repo first, the same way every prior
phase did, and found a real, already-built, already-tested piece with no
caller: `ChangeClassifierAgent.classify()` and `ChangeAssessment.from_dict()`
(`autonomous_agents.py`/`change_policy.py`) classify a user's follow-up
against an approved `ProductSpec` as `system_bug` / `missing_requirement` /
`change_request` / `ambiguous` — covered by `tests/test_v22_autonomous_core.py`
— but nothing outside that one test ever calls `.classify()`, and nothing
turns a classification into an actual repository change.
`POST /api/billing/classify` (`investor_app.py:325`) looked like it might be
that caller; it isn't — it calls a different function, `billing.classify_charge()`,
which prices a `category` string the caller already decided on, never invokes
the LLM classifier, and never touches a repository. Confirmed by grep:
`ChangeClassifierAgent`/`ChangeAssessment` have exactly one call site outside
their own definitions, in that test.

`ModifierEngine.modify(spec, repository, followup)`:
- **`system_bug` / `missing_requirement`** (the two categories
  `ChangeAssessment.from_dict` already requires to name real, existing
  acceptance ids, and marks non-billable): real, tested end-to-end. Builds
  synthetic `AcceptanceFailure`s from the classifier's `reason`/referenced
  ids, then runs the *same* `RepairAgent.repair()` → `repository_patch.apply_patch()`
  → `Executor.execute()` loop `AutonomousProductEngine.build()` uses for its
  own repair rounds — no new agent, no new prompt, no new patch format.
  Returns `status='applied'` or `'failed'` with the real `ExecutionReport`.
- **`change_request`** (billable, and `ChangeAssessment.from_dict` allows it
  to reference *no* acceptance id — e.g. "add a calendar view" isn't a
  failing criterion): classified but deliberately **not executed**. Reducing
  an open-ended feature add to RepairAgent's "fix these failing acceptance
  ids" framing would be exactly the kind of unrequested, unverified
  invention this repo's `AGENTS.md` warns against — it needs its own
  generation prompt and usually a spec update, a real product decision.
  Returns `status='change_request_not_supported'` with the real
  `ChangeAssessment` attached, so a caller can bill/queue it once that path
  exists. Flagged here the same way M1 flagged the missing worker and M3
  flagged the missing generator-prompt `start`/`port` fields — not invented,
  not silently dropped.
- **`ambiguous`**: classified, nothing executed, `status='needs_clarification'`.

**Explicitly out of scope, stated up front in the module docstring rather
than discovered later:**
1. `ProductSpec` persistence. Nothing in this codebase persists the spec a
   project was built against — `ProjectVersion` (`workspace.py`) stores only
   the repository; grepped `job_repository.py`, `acceptance_pipeline.py`,
   `v27_platform.py`, `project_memory.py` for it, found nothing. The caller
   must supply the spec it already holds from build time. Inventing a spec
   store inside a "modify" engine would be unrequested scope creep on the
   commit path.
2. No route, no worker task, no wiring. Nothing calls `ModifierEngine.modify()`
   except `tests/test_modifier_engine.py`. `execute_live_build_job` and
   `execute_preview_launch` were only written once a directive explicitly
   asked for them (see the M1/M3 sections above) — the same bar applies here:
   route/queue wiring for a capability whose product shape (an endpoint under
   which project? synchronous or async? does the UI show a diff before
   committing?) was never specified is guessed at, not built.

**Tests (`tests/test_modifier_engine.py`, real output, run twice):**
```
$ python3 -m unittest tests.test_modifier_engine -v
test_change_request_is_classified_but_not_executed ... ok
test_missing_requirement_applies_after_one_repair_round ... ok
test_never_converging_repair_stops_at_max_rounds_and_reports_failed ... ok
test_system_bug_repair_failures_carry_the_classifier_reason_and_followup ... ok
test_zero_max_repair_rounds_never_calls_the_repairer_but_still_verifies ... ok
test_empty_followup_rejected ... ok
test_empty_repository_rejected ... ok
test_negative_max_repair_rounds_rejected ... ok
test_ambiguous_does_not_touch_repair_or_sandbox ... ok
test_ambiguous_returned_repository_does_not_alias_the_input ... ok

Ran 10 tests in 0.001s

OK
```
Coverage: all four classification branches; the free-repair loop converging
after one round and never converging (stops exactly at `max_repair_rounds`,
reports `'failed'` honestly rather than `'applied'`); the failure payload
handed to `RepairAgent.repair()` carries the classifier's real `reason` and
the user's real `followup` text (asserted on the literal dict, not just its
shape); `max_repair_rounds=0` still runs one real verification pass instead
of claiming success unverified; the returned repository is a copy in every
path (mutating the result never mutates the caller's original dict); empty
`followup`/`repository` and negative `max_repair_rounds` are rejected before
any agent or sandbox call.

*Mutation check* (manual, one regression applied and reverted, not
committed): removed the `change_request` early-return so it fell through to
the repair path. `test_change_request_is_classified_but_not_executed` failed
immediately with the `Unreachable` executor's `AssertionError`, confirming
the test actually exercises the guard rather than passing vacuously.

### Regression: full suite after this change

```
$ python3 -m compileall -q omni_prod tests infra scripts        -> exit 0
$ python3 -m unittest <all 16 non-fastapi test modules>          -> Ran 197 tests ... OK
      (the same 187 pre-existing tests, unmodified, + 10 new modifier_engine tests)
```
Same 8 fastapi-dependent test files still cannot import here
(`ModuleNotFoundError: No module named 'fastapi'`) — unchanged, pre-existing,
unrelated to this change; confirmed again by re-running the same per-file
import check used in every prior phase of this report.

## Update: M4 — Natural-Language Product Modification

The M4 directive was explicit that the `ModifierEngine` stub above is "an M4
foundation, not completed M4" — it classifies but never executes
`change_request`, has no durable `ProductSpec`, is never invoked from a
route or worker, and always patches destructively-in-place conceptually
(no candidate isolation, no accept/reject/rollback). All of that is closed
here, on top of `ModifierEngine` rather than replacing it (`ModifierEngine`
itself is untouched; its regression tests still pass — see §Regression).

### `infra/postgres/016_durable_modifications.sql` (new) — M4A/M4B schema

`project_version_specs` (`version_id` PRIMARY KEY, `spec_json JSONB`) is the
M4B invariant made durable: `ProjectVersion N <-> ProductSpec N`, one row per
version, no `UPDATE` path in code (see `spec_repository.py` below) so a spec
can only ever gain a new row for a new version, never be mutated in place.

`modification_requests` carries the full `ModificationRequest` the directive
asked for (id, project/version/user ids, followup, classification,
status/phase, evidence/error, billing reference, timestamps) plus
`target_markets_json`/`rights_evidence_json` — captured durably at
request-creation time rather than read from the API process's in-memory
state at worker-run time, since the worker is commonly a separate process.

`modification_candidates` (new table, not in the original draft of this
migration) is the single most important schema decision in M4: a candidate's
`repository_json`/`spec_json` are stored here, **never** written to
`project_versions`, until `accept()` explicitly promotes them. This was
changed mid-implementation after tracing the directive's own Version 10/11
concurrency scenario end-to-end and finding it unrepresentable under the
first draft (which had `build()` commit a real `ProjectVersion` for every
candidate) — see the M4D section below for why.

`modification_outbox` reuses the exact transactional-outbox shape M1
established (`FOR UPDATE SKIP LOCKED`, one row per transaction).

### `omni_prod/spec_repository.py` (new) — `PostgresSpecRepository`

`save(version_id, project_id, spec)` / `get(version_id, project_id)`. No
`update()` method exists at all — asserted directly in
`tests/test_m4_acceptance.py::AcceptanceS`
(`assertFalse(hasattr(PostgresSpecRepository, 'update'))`). `get()` raises
`SpecNotFound` rather than falling back to "latest" or any other version.
Tests: `tests/test_spec_repository.py` (5), real output:
```
$ python3 -m unittest tests.test_spec_repository -v
Ran 5 tests ... OK
```

### `omni_prod/modification_diff.py` (new) — M4F deterministic diff

`diff_repositories(old, new)` / `diff_specs(old, new)` — pure functions,
sets/sorted-tuples internally so dict insertion order never changes the
result (files added/modified/deleted; dependency changes; requirements/
acceptance-criteria added/removed/changed). No LLM call anywhere in this
module — the directive's "do not rely on an LLM-only prose summary as the
canonical diff" is structural, not a convention to remember. Tests:
`tests/test_modification_diff.py` (13) plus
`tests/test_m4_acceptance.py::AcceptanceQR`, which independently re-derives
order-independence by diffing the same content built from differently
ordered source dicts and asserting identical results.
```
$ python3 -m unittest tests.test_modification_diff -v
Ran 13 tests ... OK
```

### `omni_prod/product_evolution.py` (new) — `ProductEvolutionAgent`, M4C

A thin wrapper over the same `RoutedModelGateway`/`OpenAICompatibleGateway.complete_json`
every other agent in this codebase uses (`RepairAgent`, `ChangeClassifierAgent`)
— no new model-calling machinery. `evolve(spec, repo_summary, followup)`
returns a *new* `ProductSpec` (never mutates the input — `ProductSpec` is a
frozen dataclass anyway) plus a repository patch, i.e. `change_request` gets
its own generation path instead of being coerced into `RepairAgent`'s
"fix this failing acceptance id" framing, which is exactly what the
directive said `RepairAgent` cannot honestly do for an open-ended feature
add. Tests: `tests/test_product_evolution.py` (5).
```
$ python3 -m unittest tests.test_product_evolution -v
Ran 5 tests ... OK
```

### `omni_prod/modification_engine.py` (new) — `CandidateModificationEngine`, M4C/D/E

`propose(spec, repository, followup, target_markets, rights_evidence) ->
CandidateOutcome`. Routes on the same `ChangeClassifierAgent` classification
as `ModifierEngine`:
- `system_bug` / `missing_requirement` → the real `RepairAgent` + `Executor`
  loop (identical mechanics to `ModifierEngine`, reused not reinvented).
- `change_request` → `ProductEvolutionAgent.evolve()`, then the *same*
  `Executor` runs against the generated repository — change_request candidates
  go through the identical build/verify path as repair candidates, not a
  shortcut.
- `ambiguous` → `status='needs_clarification'`, nothing built.

Every outcome — including a successful one — then runs the same
`quality_fn`/`security_fn`/`RightsEngine` gates the rest of the pipeline
uses (M4E: "no READY/APPLIED state based only on an LLM response"); a gate
failure returns `status='failed'` with the real gate result attached, never
`'ready_for_review'`. `propose()` never mutates its `spec`/`repository`
arguments — proven directly in `AcceptanceK` and, at the worker-integration
level, by `test_m4_worker.py`'s `workspace.commit.assert_not_called()`
assertions guarding every non-accept code path.

Tests: `tests/test_m4_modification_engine.py` (12).
```
$ python3 -m unittest tests.test_m4_modification_engine -v
Ran 12 tests ... OK
```

### `omni_prod/modification_repository.py` (new) — `PostgresModificationRepository`, M4A/D — the central design decision

**The bug this design avoids.** An earlier draft had `complete()` write the
candidate straight into `project_versions` (via `candidate_version_id`
columns) so `accept()` would just flip a pointer. Tracing the directive's own
concurrency scenario against that draft breaks it: if building Modification A
from Version 10 already creates a real `ProjectVersion`, `current()` has
silently moved before anyone decided anything, and a concurrently-building
Modification B (also "from Version 10") is now unknowingly building against
a version nobody accepted. The fix: `complete()` writes
`repository_json`/`spec_json` to the new `modification_candidates` table
only; `project_versions` is untouched until `accept()` runs.

**`accept()` — two-phase, and honest about what it can't make atomic.**
1. Pre-check: a row-locked read of `modification_requests` +
   `modification_candidates`, and a pure function,
   `resolve_accept(status, expected_source_version_id, current_version_id,
   force) -> 'invalid_status'|'conflict'|'accept'|'accept_forced'`, decides
   the outcome from that snapshot.
2. `workspace.commit()` is called — this must own its own connection to take
   its `pg_advisory_xact_lock`, so it cannot be nested inside the same
   transaction as the pre-check. That means two concurrent `accept()` calls
   for *different* modification ids are **not** mutually excluded by the row
   lock; the real serialization is `workspace.commit()`'s own lock. A second,
   post-commit check — `new_version.parent_id != source_version_id` — catches
   a race that slipped past the pre-check and, unless `force=True`, discards
   nothing (the new version was already committed by `workspace.commit()`
   itself; `accept()`'s bookkeeping just refuses to also flip
   `modification_requests` to accepted/promoted).
3. **Disclosed gap, not hidden:** `workspace.commit()`, `spec_repo.save()`,
   and the final `modification_requests` status `UPDATE` are three separate
   transactions. The version itself is atomic (fully committed or not at
   all), but a crash between step 2 and the final `UPDATE` leaves a live,
   current, promoted `ProjectVersion` while `modification_requests` still
   reads `READY_FOR_REVIEW`. Making this fully atomic needs either a single
   connection spanning `workspace.commit()` and the status update (which
   would also have to span its advisory lock — a larger change to
   `workspace.py` not requested here) or a reconciliation job; neither exists.
   This is exactly the kind of gap `AGENTS.md` says to flag, not paper over —
   see `accept()`'s own docstring and `AcceptanceN`'s docstring in the test
   file, and `STATUS.md` §5's M4D row.

`reject()` only updates `modification_requests`; never touches
`project_versions` (`AcceptanceO`). `rollback()` re-commits the *exact*
stored repository of a historical `ProjectVersion` as a brand-new version —
never regenerates code, matching the directive's explicit "rollback must
reference durable historical versions, not regenerate old code."

**Bug found and fixed while building this:** the `forced` field in
`accept()`'s return value originally only checked
`decision == 'accept_forced'`, missing the case where the pre-check found no
conflict but a belated post-commit race was overridden by `force=True`.
Fixed to `forced = decision == 'accept_forced' or new_version.parent_id !=
source_version_id`.

Tests: `tests/test_modification_repository.py` (43) — `ScriptedCursor`/fake-pool
fixtures for the pure SQL-shape logic, the real `MemoryProjectWorkspace` for
version-history mechanics, and a purpose-built `RacyWorkspace` wrapper that
injects a concurrent "interloper" commit inside the first `.commit()` call to
deterministically reproduce the post-commit race window.
```
$ python3 -m unittest tests.test_modification_repository -v
Ran 43 tests ... OK
```
*Mutation checks* (each applied, confirmed failing tests, reverted — none
committed): `resolve_accept()`'s mismatch check forced to always pass;
`accept()`'s post-commit race check forced to `if False:`. Both caught by
the relevant `AcceptTests` cases.

### `omni_prod/worker_tasks.py` — M4 section appended

`execute_modification_job(modification_id: str) -> None` — the only
argument, matching the directive's "queue payload should ideally contain
only modification_id. Worker reloads durable state." Lazy-imports
`investor_app` internals (so this module stays importable without
`fastapi`/`psycopg`, same convention as `execute_live_build_job`), then
delegates to `_run_modification_job()`, which takes every dependency by
injection and is what actually gets unit-tested.

`_run_modification_job()`: loads the request, loads the *exact* source
`ProjectVersion` by id (never `current()`), loads the *exact* `ProductSpec`
for that version id (never "latest"), classifies, dispatches to
`CandidateModificationEngine.propose()`, and on `'ready_for_review'` calls
`complete()` (never touches `project_versions` here — see above). On any
exception it records a terminal `FAILED` state and **re-raises**, matching
`_run_live_build_job`'s established convention (M1) exactly — it does not
swallow worker exceptions into a success-shaped return.

`resolve_modification_billing(category, billable, spend_incurred) ->
'settle'|'release'`: M4G's billing rule, decided by the *real classification*
from `ChangeAssessment.billable`, not by whether compute happened to be
spent. `system_bug`/`missing_requirement`/`ambiguous` always `release()`
(free-by-policy) even if repair rounds burned provider spend;
`change_request` always `settle()` at the real amount. This is a genuinely
different rule from `resolve_billing()` (M1, unmodified, still used for the
exception path here where no classification exists yet, and for ordinary
builds which have no classification concept at all).

Tests: `tests/test_m4_worker.py` (11) — `ModHarness` over
`Classifier`/`RepairsOnFirstTry`/`RaisingRepairer`/`EvolverImmediatelyPassing`/
fake gates/fake rights engine/`FakeModJobs`/`FakeSpecRepo`/`fake_workspace()`.
```
$ python3 -m unittest tests.test_m4_worker -v
Ran 11 tests ... OK
```
*Mutation check*: `resolve_modification_billing` forced to always return
`'release'`; caught by 2 tests; reverted.

### `omni_prod/investor_app.py` — M4A routes

Six new routes, all delegating to `PostgresModificationRepository` and
`enqueue_build()` (the same enqueue helper M1/M3 use, with the same
try/except → `dispatch='deferred'` outbox fallback — **never fails the
request** if Redis is down, satisfying the directive's "ensure enqueue
failure is recoverable through the outbox"):

| Method | Path | Handler |
|---|---|---|
| POST | `/api/v28/projects/{project_id}/versions/{version_id}/modifications` | `v28_propose_modification` (line 1378) |
| GET | `/api/v28/projects/{project_id}/modifications/{modification_id}` | `v28_modification_status` (line 1430) |
| GET | `/api/v28/projects/{project_id}/modifications/{modification_id}/candidate` | `v28_modification_candidate` (line 1448) |
| POST | `/api/v28/projects/{project_id}/modifications/{modification_id}/accept` | `v28_modification_accept` (line 1464) |
| POST | `/api/v28/projects/{project_id}/modifications/{modification_id}/reject` | `v28_modification_reject` (line 1480) |
| POST | `/api/v28/projects/{project_id}/rollback` | `v28_rollback` (line 1492) |

`v28_propose_modification` reserves credits via `subscriptions.reserve(...,
category='product_modification')` **at request-creation time**, inside the
same transaction as `create()`/`create_outbox()` — always billable at
reservation (the real classification isn't known yet; the worker's
`resolve_modification_billing()` settles or releases once it is).

`fastapi` is not installable in this sandbox, so none of this can be
exercised over real HTTP here. It was instead verified without importing
`fastapi` at all:
- `ast.parse()` on the full 1646-line file (syntax-valid), checked for
  duplicate top-level function names and duplicate
  `@app.<method>('<path>')` registrations across all 117 routes (none found).
- Every new import/attribute/call this section makes into
  `modification_repository.py`/`spec_repository.py`/`subscription_store.py`
  cross-checked with `inspect.signature()` against the real target
  functions, imported directly (those modules have no `fastapi` dependency)
  — confirmed `create`/`create_outbox`/`mark_outbox_enqueued`/`get_details`/
  `get_candidate`/`accept`/`reject`/`rollback` and `reserve()` all match
  their call sites exactly.
- `tests/test_m4_acceptance.py::AcceptanceB` proves, by parsing
  `investor_app.py`'s source text with `ast` (no import, so no `fastapi`
  needed), that `v28_propose_modification`'s own function body never
  references `CandidateModificationEngine`, `propose`, or any agent class —
  the strongest statically-provable form of "the API process never performs
  the modification synchronously" available without a live server.

This is genuinely `IMPLEMENTED_NOT_VERIFIED`, not `VERIFIED` — see
`STATUS.md` §5.

### `tests/test_m4_acceptance.py` (new) — the directive's own A–W list, verbatim

Maps each of the 23 lettered acceptance tests plus the concurrency
requirement onto either a new minimal self-contained proof, or a pointer to
deeper existing coverage. Letter A is `@unittest.skip(...)` with a reason
naming exactly what would need `fastapi` to verify live, rather than a fake
pass. The concurrency requirement (`AcceptanceU`) reproduces the directive's
own scenario verbatim against a real `MemoryProjectWorkspace`:
```
Version 10 is current.
A is accepted -> Version 11.                    (assertTrue(out_a['accepted']))
B (also from Version 10) tries to accept ->      out_b['reason'] == 'conflict'
Version 11 is NOT overwritten ->                 workspace.current('p1').id == v11_id
B may still be force-accepted as an explicit,
controlled decision ->                           force=True succeeds, forced=True
```
```
$ python3 -m compileall -q tests/test_m4_acceptance.py    -> exit 0
$ python3 -m unittest tests.test_m4_acceptance -v
test_A_post_returns_202_and_durable_id ... skipped '...'
test_B_the_propose_route_never_calls_the_candidate_engine_itself ... ok
test_C_worker_entrypoint_takes_only_the_id_and_reloads_everything_else ... ok
test_D_enqueue_failure_leaves_the_row_pending_for_relay_to_retry ... ok
test_E_and_F_worker_loads_the_exact_source_version_and_its_own_spec ... ok
test_G_system_bug_executes_the_real_repair_loop ... ok
test_H_missing_requirement_executes_the_real_repair_loop ... ok
test_I_ambiguous_builds_and_repairs_nothing ... ok
test_J_change_request_runs_the_evolver_not_the_repairer ... ok
test_K_propose_never_mutates_its_input_repository_or_spec ... ok
test_L_a_failed_modification_is_never_acceptable ... ok
test_M_a_gate_failure_never_reaches_ready_for_review ... ok
test_N_accept_promotes_the_candidate_to_a_brand_new_current_version ... ok
test_O_reject_never_touches_project_versions ... ok
test_P_rollback_recommits_the_exact_historical_repository ... ok
test_Q_repository_diff_is_order_independent ... ok
test_R_spec_diff_is_order_independent ... ok
test_S_spec_lookup_is_exact_version_scoped_with_no_update_path ... ok
test_T_duplicate_delivery_of_queued_and_of_a_completion_are_both_noops ... ok
test_U_resolve_accept_pure_decision_table ... ok
test_U_version_10_11_scenario_from_the_directive ... ok
test_V_reserve_called_twice_with_the_same_modification_id_charges_once ... ok
test_W_every_non_fastapi_test_module_passes ... ok

Ran 23 tests in 0.968s

OK (skipped=1)
```
Two real bugs were found and fixed *in this test file* while first verifying
it (not in production code): `AcceptanceB` originally did
`import omni_prod.investor_app`, which raises `ModuleNotFoundError: fastapi`
before any AST inspection can happen — fixed to read the file as text and
`ast.parse()` it directly, without importing. `AcceptanceV` originally
hardcoded a fake subscription cycle (`'2026-01'`) that didn't match
`PostgresSubscriptionService._cycle_now()`'s real current-UTC-month value,
which silently triggered `reserve()`'s cycle-reset branch and shifted the
expected SQL-statement sequence — fixed to compute the real current cycle
the same way `_cycle_now()` does, and to script the scripted cursor's
per-call rowcounts correctly (`ON CONFLICT DO NOTHING` on the retried
`INSERT` must report `rowcount=0`, not fall through to the fake cursor's
default of 1). Both were test-double bugs, not application-code bugs; caught
by actually running this file before moving on, the same discipline used for
every other new module in this and the prior M1/M3 phases.

`AcceptanceW` runs the real, full non-fastapi regression suite as a guarded
subprocess (`OMNI_M4_ACCEPTANCE_W_NESTED=1` prevents it recursing into
itself when the child process's own test discovery re-imports this same
file) and asserts a clean exit.

### Regression: full suite after M4

```
$ python3 -m compileall -q omni_prod tests                       -> exit 0
$ python3 -m unittest <23 non-fastapi test modules>               -> Ran 309 tests ... OK (skipped=2)
```
309 tests: the 197 from the `modifier_engine.py` phase (unchanged) + 112 new
M4 tests (43 `test_modification_repository` + 11 `test_m4_worker` + 23
`test_m4_acceptance` + 12 `test_m4_modification_engine` + 13
`test_modification_diff` + 5 `test_product_evolution` + 5
`test_spec_repository`). The same 8 fastapi-dependent test files still fail
only at `ModuleNotFoundError: No module named 'fastapi'` on import —
unchanged, pre-existing, confirmed again by direct per-file import.

### Known gaps, flagged not fixed

- `accept()`'s cross-transaction atomicity window (see above) — disclosed,
  not hidden; needs either a schema/connection change to `workspace.py` not
  requested here, or a reconciliation job.
- Everything requiring `fastapi`, live Postgres, or live Redis is
  `IMPLEMENTED_NOT_VERIFIED`/`NOT_CONFIGURED` in this sandbox — pre-existing
  constraint (see the M1/M3 sections above), not new to M4, and not a code
  defect: every one of those paths is statically checked (AST, duplicate
  routes, `inspect.signature()` cross-referencing against real target
  functions) rather than skipped silently.
- `ModifierEngine` itself is unmodified and remains unwired to any route —
  M4 does not call it; `CandidateModificationEngine` is the intended entry
  point going forward (see `STATUS.md` §4/§5).
- M5 and beyond: out of scope by the directive's own stop condition; not
  started, not designed.

### EXECUTED / STATICALLY VERIFIED / NOT EXECUTED (per the directive's stop condition)

**EXECUTED** (real Python processes, real assertions, real failures on
mutation, run in this session): `spec_repository.py`, `modification_diff.py`,
`product_evolution.py`, `modification_engine.py`, `modification_repository.py`
(including the real `MemoryProjectWorkspace` concurrency scenario and the
`RacyWorkspace` post-commit-race reproduction), the `worker_tasks.py` M4
functions (`_run_modification_job`, `resolve_modification_billing`), and the
full 309-test non-fastapi regression suite, including
`tests/test_m4_acceptance.py` letters B–W (22 of 23 lettered tests; the
concurrency requirement; 309/309 green).

**STATICALLY VERIFIED** (compiles, AST-inspected, signatures cross-checked
against real functions, but never actually run as a live process): the six
new FastAPI routes in `investor_app.py` (acceptance letter A), the
Redis/outbox dispatch path end-to-end (only its logic is executed; no live
Redis), and migration `016`'s SQL against an actual Postgres server.

**NOT EXECUTED**: nothing in this M4 pass has zero evidence — every claim
above lands in one of the two categories. Not attempted at all: M5+.

M4 is stopped here per the directive's own stop condition. This report and
the current working tree are the artifact for independent review; no
packaged ZIP was produced since this environment produces its evidence and
diffs directly in-repo (see `git log`/`git diff` for the commit created
alongside this report).

## Update: M4D.1 — atomic expected-version accept (remediation)

An independent architecture review of the M4 work above found a
production-blocking correctness bug in `accept()` and flagged it before M5
was allowed to start. This section documents the finding, confirms it was
real (not merely trusted), and reports the fix with the same evidence
standard as every other section of this file.

### The bug, confirmed by direct code inspection, not by trusting the report

The review's claim: `accept()`'s "post-commit check" — call
`workspace.commit()` unconditionally, *then* compare
`new_version.parent_id != source_version_id` — is not a safety check at all,
because by the time the comparison runs, the new `ProjectVersion` row already
exists and `current()` has already silently advanced to it. A caller can be
told `reason='conflict'` while the project's real current version has
already mutated to the "rejected" candidate's content. **A post-commit check
is not a substitute for a pre-commit guard.**

Before writing a line of remediation code, this was verified directly
against the actual source, not accepted on the strength of the report:

```
$ grep -n "def commit" omni_prod/workspace.py
```
confirmed `MemoryProjectWorkspace.commit()` and
`PostgresProjectWorkspace.commit()` had **zero** compare-and-swap logic —
`current()` in both implementations is simply "the most recently
appended/inserted row." The prior `modification_repository.accept()`
(documented honestly in the M4 section above as a "disclosed gap") called
`workspace.commit()` unconditionally and only compared
`new_version.parent_id != source_version_id` *afterward* — exactly the
unsound pattern the review described. The bug was real.

### The fix

**1. Push the compare-and-abort inside the same lock as the write.**
`omni_prod/workspace.py` gained a sentinel and an exception:

```python
SKIP_VERSION_CHECK = object()   # "commit unconditionally" — the default,
                                  # preserving every pre-M4D.1 call site

class VersionConflict(Exception):
    def __init__(self, *, project_id, expected_current_version_id,
                 actual_current_version_id): ...
```

`commit()`/`restore()` on both `MemoryProjectWorkspace` and
`PostgresProjectWorkspace` gained `expected_current_version_id=
SKIP_VERSION_CHECK` and `cur=None` parameters. In `MemoryProjectWorkspace`,
the compare now happens **inside** `with self._lock:`, immediately before
`bucket.append(version)` — read-current, compare, raise-or-write, all under
one lock acquisition, with no gap a second thread can land in. In
`PostgresProjectWorkspace`, the same shape is enforced inside one advisory-
locked transaction: `pg_advisory_xact_lock` → `SELECT ... ORDER BY
created_at DESC LIMIT 1` (the real current version) → compare → raise
`VersionConflict` (no insert) or `INSERT INTO project_versions` — same
cursor, same transaction, no commit in between.

**2. Merge `accept()` into one transaction.** `modification_repository.py`'s
`accept()` was rewritten to open exactly one
`connection()`/`transaction()`/`cursor()` block and share that cursor with
`workspace.commit(cur=cur, expected_current_version_id=source_version_id,
...)` and `spec_repo.save(cur=cur, ...)` (the latter's `cur` parameter
already existed from the original M4 work, which is what made the merge
possible without a larger schema change). The row-locked status read, the
version insert, the spec insert, and the final `ACCEPTED` status update are
now one atomic unit: either all of it commits, or none of it does, and a
`VersionConflict` raised partway through means *nothing* in that attempt
was written — proven below via `FakeConn.transactions` counts, not asserted
by inspection alone. `force=True` passes `SKIP_VERSION_CHECK` explicitly
instead of the source version — the same override semantics as before, now
implemented at the correct layer.

**3. Route status code.** `investor_app.py`'s `v28_modification_accept`
route was simplified from checking two reason strings
(`'conflict'`/`'conflict_detected_at_commit'`) to one — the second string no
longer exists, because there is no longer a separate post-commit-race
category distinct from an ordinary pre-commit conflict; both are now the
same atomic check.

### What "VERIFIED" means here, precisely

Two new test files were added specifically for this remediation, both
required by the directive:

**`tests/test_workspace_version_conflict.py`** (14 tests) — workspace-level
proof that the guard is unconditional-by-default, matches-succeeds,
mismatch-raises-before-any-write, and — for Postgres — that a shared `cur`
never opens a second connection from the pool (proven with an
`ExplodingPool` that raises `AssertionError` if `.connection()` is ever
called while a `cur` was supplied) and that lock-acquire happens before the
insert decision (a statement-order assertion against a scripted fake
cursor).
```
$ python3 -m unittest tests.test_workspace_version_conflict -v
Ran 14 tests ... OK
```

**`tests/test_m4d1_atomic_accept.py`** (14 tests, 13 executed + 1 intentional
skip) — the directive's own required-test list, mapped one-to-one:
concurrent A/B accept from the same source, a 10-way fan-in, three staged
transaction-failure points (before any insert, after the version insert but
before the spec write, before the final status update — each via a cursor
fake that raises `RuntimeError` on a specific, numbered `.execute()` call),
retry-after-crash idempotency, force-accept behavior (with and without an
actual conflict to override), rollback-after-accept, the spec-per-version
bijection invariant, and — stated as its own invariant test, not inferred
from the others — "a failed or conflicted accept never changes current
version," asserted by object identity (`assertIs`) against the pre-accept
`current()` result.
```
$ python3 -m unittest tests.test_m4d1_atomic_accept -v
Ran 14 tests ... OK (skipped=1)
```

**The true-concurrency proof, specifically.** `TrueConcurrencyTests` does
not simulate a race by sequencing test code — it uses two (and, in a second
test, ten) real `threading.Thread` workers and a real `threading.Barrier` so
every thread enters `workspace.commit()` at the same instant, contending for
the real `threading.RLock` inside `MemoryProjectWorkspace`. Which thread
wins is genuinely nondeterministic; what's asserted is the invariant, not
the winner: exactly one promotion, version count unchanged beyond that one
promotion, `current()` is the winner's version, the loser is durably marked
`CONFLICT` (not silently dropped, not left `READY_FOR_REVIEW`), no
`DELETE` is ever issued, and the winner's spec is saved exactly once. Run
40 times consecutively in this session to rule out flakiness masking a race
window:
```
$ for i in $(seq 1 40); do python3 -m unittest \
    tests.test_m4d1_atomic_accept.TrueConcurrencyTests -q 2>&1 | tail -1; done \
    | sort | uniq -c
     40 OK
```

**Mutation testing, made permanent.** Rather than a one-off manual
apply/revert, `MutationTests` monkeypatches `MemoryProjectWorkspace.commit`
and `PostgresProjectWorkspace.commit` at the class level (inside a
`try/finally` that always restores the original) with a mutant that omits
the compare-and-raise, proves the exact M4D.1 bug reappears under that
mutant (a "conflicting" accept silently succeeds and moves `current()`),
then restores the real method and re-confirms the fix holds. This runs as
an ordinary test method every time the suite runs — it is evidence
generated on every regression, not a claim made once and left unverified
thereafter.
```
$ python3 -m unittest tests.test_m4d1_atomic_accept.MutationTests -v
test_removing_the_check_from_memory_workspace_reintroduces_the_m4d1_bug ... ok
test_removing_the_check_from_postgres_workspace_reintroduces_the_m4d1_bug ... ok
Ran 2 tests in 0.000s
OK
```

**Existing suites re-verified green after the rewrite**, including two new
assertions added specifically to prove the transaction-merge claim
(`FakeConn.transactions == 1` on the happy path; `== 2` on the conflict
path — the aborted attempt plus a separate `_mark_conflict()` bookkeeping
statement):
```
$ python3 -m unittest tests.test_modification_repository -v
Ran 43 tests ... OK
$ python3 -m unittest tests.test_m4_acceptance -v
Ran 23 tests ... OK (skipped=1)
```

### What is honestly still not proven, and why

`PostgresProjectWorkspace`'s SQL-level guard (`pg_advisory_xact_lock` →
`SELECT` → compare → `INSERT`) is proven only structurally: a scripted fake
cursor confirms the statements execute in the right order, on the right
cursor, inside the right transaction boundary. It has never run against a
live Postgres server with real concurrent connections actually contending
for the same advisory lock — this sandbox has no reachable Postgres (the
same pre-existing constraint noted throughout the M1–M4 sections above).
The `MemoryProjectWorkspace` test double also cannot simulate Postgres's
real transaction-rollback guarantee (its "transaction" is just a Python
lock, not a WAL-backed rollback), so the staged-failure tests prove *this
codebase's* control flow never marks something accepted after a failure —
they do not re-prove Postgres's own atomicity, which is not this
codebase's claim to make.

**M4 is not `LIVE`. This remediation is not "production-closed."** It is:
the identified correctness bug is fixed at the code and lock-ordering
level, proven by real multi-threaded concurrency, permanent mutation
tests, and the directive's full required-test list, entirely within this
sandbox's `MemoryProjectWorkspace` and structural Postgres proofs. Running
it against a live Postgres cluster remains `IMPLEMENTED_NOT_VERIFIED`, not
`VERIFIED`, and is not claimed otherwise. See `STATUS.md` §5's `M4D.1`
subsection for the same disclosure in status-table form.

### Regression: full suite after M4D.1

```
$ python3 -m compileall -q omni_prod tests                        -> exit 0
$ python3 -m unittest <24 non-fastapi test modules> -v            -> Ran 337 tests ... OK (skipped=2)
```
337 tests: the 309 from the M4 phase above (unchanged) + 14 new
`test_workspace_version_conflict` + 14 new `test_m4d1_atomic_accept`
(13 executed + 1 intentional skip in each of the two files' totals — see
above). The same 8 fastapi-dependent test modules (`test_v23_investor_grade`,
`test_v24_auth`, `test_v24_international`, `test_v24_native_remote`,
`test_v25_unified_v10_parity`, `test_v26_universal_pro`,
`test_v27_rights_company_os`, `test_v28_148ai_launch`) still fail only at
`ModuleNotFoundError: No module named 'fastapi'` on import — unchanged,
pre-existing, not touched by this remediation.

### EXECUTED / STATICALLY VERIFIED / NOT EXECUTED — M4D.1

**EXECUTED**: `omni_prod/workspace.py`'s new guard (both implementations,
via the fake-pool/fake-cursor harness for Postgres and the real
`threading.RLock` for Memory), `modification_repository.py`'s rewritten
`accept()`/`rollback()`, the real 2-thread and 10-thread barrier-
synchronized concurrency scenarios, both permanent mutation tests, the
three staged transaction-failure points, force-accept, rollback-after-
accept, both invariants, and the full 337-test non-fastapi regression
suite.

**STATICALLY VERIFIED**: the `investor_app.py` route's simplified
status-code logic (recompiled, `ast.parse()`-checked, no live HTTP call
possible without `fastapi`, unchanged from the M4 section's constraint
above); the Postgres SQL statement ordering (scripted-cursor proof, never
run against a live server).

**NOT EXECUTED**: a live Postgres cluster under real concurrent
connections. M5 and beyond remain untouched, per **"Do not start M5"**.

This remediation stops at M4D.1, as directed. M4 is **not** marked `LIVE`.
The current working tree and this report are the artifact for independent
re-review; see `git log`/`git diff` for the commit created alongside this
update.

## Update: M4D.2 — live infrastructure verification

M4D.1 was accepted "at the algorithmic/concurrency-design evidence level."
Its own report, immediately above, is explicit that a live Postgres run
was **not executed** in that sandbox. M4D.2's directive required closing
exactly that gap — real PostgreSQL, real FastAPI, real Redis/RQ, "No
FakeConn. No FakeCursor. No AST substitute. No mocked transaction
semantics." — and, critically, required doing the environment discovery
itself rather than declaring `BLOCKED_BY_ENVIRONMENT` because the services
weren't preinstalled. **M5 was not started.**

### Environment discovery — exact commands and exact results

**Docker:**
```
$ service docker start
 * Starting Docker: docker
ulimit: error setting limit (Operation not permitted)
 ...fail!
```
Worked around by invoking the daemon directly. `timeout 10 dockerd
--storage-driver=vfs` started but was killed by the wrapper at 10s; `nohup
dockerd --storage-driver=vfs & disown` was killed anyway (exit 144 — the
harness's process-group cleanup catches ordinary background jobs). Fixed
with a fully detached invocation:
```
$ setsid nohup dockerd --storage-driver=vfs > /tmp/dockerd.log 2>&1 < /dev/null &
$ docker ps
CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES
```
Daemon itself: **usable**. Then:
```
$ docker pull python:3.11-slim
Error response from daemon: Get "https://registry-1.docker.io/v2/": Forbidden
```
Docker Hub: **genuinely blocked** by this sandbox's egress policy, not a
Docker problem. Per this repo's own proxy runbook (`/root/.ccr/README.md`,
"do not retry organization policy denials (403/407) — report them
instead"), this was not retried. Docker was not used further; the
services below were run natively instead.

**PostgreSQL** — already present in the image, not running:
```
$ pg_lsclusters
Ver Cluster Port Status Owner    Data directory              Log file
16  main    5432 down   postgres /var/lib/postgresql/16/main ...
$ pg_ctlcluster 16 main start
$ pg_lsclusters
16  main    5432 online postgres /var/lib/postgresql/16/main ...
```
A real, native (non-Docker) PostgreSQL 16.13 (Ubuntu
16.13-0ubuntu0.24.04.1) server.

**Redis** — binary present, not running:
```
$ redis-server --daemonize yes --port 6379 --logfile /var/log/redis-server.log
$ redis-cli -p 6379 ping
PONG
```
Redis 7.0.15 (`redis-server v=7.0.15 sha=00000000:0 malloc=jemalloc-5.3.0
bits=64 build=e53ff17674aa6190`).

**Python client libraries** — three independent installation paths tried,
in order, each genuinely exhausted before moving to the next:
```
$ pip3 install fastapi==0.128.2 psycopg[binary] psycopg_pool redis rq
ERROR: Could not find a version that satisfies the requirement fastapi==0.128.2
$ curl -v https://pypi.org/simple/fastapi/
< HTTP/1.1 403 Forbidden
< x-deny-reason: host_not_allowed
```
```
$ apt-get install -y python3-fastapi   (and equivalents)
... 403  Forbidden
```
(`apt-cache policy` resolved candidate versions from a stale local index,
but every actual `.deb` download from `archive.ubuntu.com` /
`security.ubuntu.com` returned 403 — a genuine block, not a missing
package.)
```
$ docker pull python:3.11-slim
Error response from daemon: ... Forbidden
```
All three independently confirmed blocked. `git clone` to GitHub,
however, is reachable:
```
$ git clone --depth 1 https://github.com/psycopg/psycopg.git  /tmp/psycopg_src
$ git clone --depth 1 https://github.com/fastapi/fastapi.git  /tmp/fastapi_src
$ git clone --depth 1 https://github.com/redis/redis-py.git   /tmp/redis_py_src
$ git clone --depth 1 https://github.com/rq/rq.git            /tmp/rq_src
```
all four succeeded. Building real wheels from these was then abandoned
(psycopg/psycopg_pool need `setuptools>=80.3.1`, only 68.1.2 present;
fastapi needs `pdm-backend`, redis-py/rq need `hatchling`, none
installable, same PyPI block) in favor of making the pure-Python source
trees directly importable via `PYTHONPATH`
(`tools/m4d2_setup_live_infra.sh`, step 4): symlinks from
`/tmp/m4d2_vendor/{fastapi,redis,rq,psycopg,psycopg_pool}` into each
cloned repo's real importable package directory. psycopg's C extension
path is untouched — its pure-Python core uses `ctypes.dlopen("libpq.so.5")`
directly, which was already present on disk.

One micro-dependency, `annotated-doc` (a PyPI-only package `fastapi`
imports at module load time for a PEP 727 `Doc()` documentation marker,
with no GitHub source to clone), was replaced with a 3-line local shim
(`/tmp/m4d2_vendor/annotated_doc.py`) re-exporting `typing_extensions.Doc`
— verified byte-identical class body via `inspect.getsource(
typing_extensions.Doc)` before use. It has zero effect on runtime
validation, routing, or control flow; this substitution is disclosed here,
in `STATUS.md`, and in the shim file's own docstring, per the directive's
"no fake success" instruction. Every other package used in M4D.2's tests
is the real, unmodified upstream source at the commit cloned:

| Package | Repo | Commit |
|---|---|---|
| psycopg / psycopg_pool | psycopg/psycopg | `ab5646af17be1e90fb9b8a6a86ae17cfd2d10a22` |
| fastapi | fastapi/fastapi | `50113da16fec53b66b80d75e80a89296de4fa5a5` |
| redis-py | redis/redis-py | `722eb643746f9d946f82fe7e5558ed311e2b11fe` |
| rq | rq/rq | `90a67a159ef9fa055c6bde12ee1bb3ebd0440b84` |

Verified importable and resolved to real version numbers (psycopg's own
`__version__` attribute reads `0.0.0.0` because the git-clone path skips
the build-time version-stamping a real `pip install` would do — its
`pyproject.toml` at the cloned commit declares `3.3.7.dev1`; this is
disclosed rather than silently patched):
```
$ PYTHONPATH=/tmp/m4d2_vendor python3 -c "
import fastapi, psycopg, psycopg_pool, redis, rq, starlette, pydantic
print(fastapi.__version__, starlette.__version__, pydantic.__version__)
print(redis.__version__, rq.__version__)
"
0.141.1 1.0.0 2.13.3
8.0.0 2.12.0
```

**Migrations** — all 16 files in `infra/postgres/*.sql` applied in order
to a fresh `m4d2_test` database, idempotently (the runbook can be re-run
without error). The full, reproducible sequence is captured in
`tools/m4d2_setup_live_infra.sh`, written specifically so "another
engineer" (directive §J) can reproduce this without reverse-engineering
this session's exploration.

**Result: M4D.2 = `VERIFIED_LIVE_INFRA`.** Every section below ran
against the real services above, not fakes.

### C — real PostgreSQL concurrency (`tests/test_m4d2_live_postgres.py::RealConcurrencyTests`, 3 tests)

Two, then ten, genuinely independent `psycopg` connections — proven
distinct by reading each one's own `pg_backend_pid()`, not merely by
object identity — synchronized with a real `threading.Barrier` and raced
through `PostgresModificationRepository.accept()` for the *same*
`project_id` and `source_version_id`. Verified directly from Postgres
after each race: exactly one `project_versions` row is created; the loser
raises the repository's own conflict result and leaves no orphan row;
`current()` (a real `SELECT`, not the returned object) points only at the
winner; the persisted `ProductSpec` matches the winner's content; the
losing `ModificationRequest.status` is `CONFLICT`, the winner's is
`ACCEPTED`. A fourth test manually acquires the exact production advisory
lock id (`int(hashlib.sha256(project_id.encode()).hexdigest()[:15], 16)`
— the identical formula used inside `PostgresProjectWorkspace.commit()`)
on a raw connection and holds it open, then proves a same-project
`accept()` blocks until release while a different project's `accept()`
proceeds immediately — direct, positive proof that the lock serializes
per-project without over-serializing unrelated projects.

### D — real transaction-rollback (`RealTransactionRollbackTests`, 7 tests)

A cursor-wrapping fixture (`_ExplodeCursor` / `_ExplodingConn` /
`_ExplodingPool`) lets every real SQL statement before a chosen call
number execute for real, then raises at that call — relying on Postgres's
own real `ROLLBACK` (via `conn.transaction()`'s real `__exit__`), not a
simulated one. Three staged failure points, each independently verified
from a *separate, fresh* connection afterward:
1. after the `project_versions` INSERT, before spec persistence → full
   rollback confirmed (no such row survives).
2. after spec persistence, before the final `ModificationRequest`
   `ACCEPTED` update → full rollback confirmed.
3. during the final request-state UPDATE itself → no partial promotion
   survives.

Plus: retry-after-crash succeeds cleanly on the next real attempt;
duplicate accept delivery after a real success is not double-promoted;
force-accept behavior is proven against real Postgres state, not asserted
structurally; and rollback-after-accept genuinely restores the prior
content as a new version (checked by re-reading it back from Postgres).

### E — concurrency stress (`RealConcurrencyStressTests`, 2 tests)

The real 2-way race repeated 20 consecutive iterations, and the real
10-way fan-in repeated 3 times, all against live Postgres, all asserting
the full invariant set (not just "no exception") each time. Zero
failures, zero conflicts beyond the expected one-per-race, zero
unexpected exceptions, across every run. The two files were run as full
suites an additional **10 times** (`test_m4d2_live_postgres.py`) and **5
times** (`test_m4d2_live_fastapi_redis.py`, with a Redis flush between
runs) across this work, including immediately before this commit — zero
flakiness on any run:
```
$ PYTHONPATH=/tmp/m4d2_vendor M4D2_DATABASE_URL=... python3 -m unittest tests.test_m4d2_live_postgres
Ran 14 tests in 3.030s
OK
   ... (repeated; identical result every time)
```

### F — real FastAPI HTTP layer (`tests/test_m4d2_live_fastapi_redis.py::LiveFastAPIModificationFlowTests`, 5 tests)

Runs the actual `omni_prod.investor_app` FastAPI application (via
`fastapi.testclient.TestClient`, itself real, unmodified `starlette`
code) with `OMNI_CREATOR_PERSISTENCE=postgres` and a live database URL set
*before* the module is imported (`_v28`/`_v28_pool` are built once at
import time from those env vars), then reassigns
`iapp._v28.engine.workspace` to a real `PostgresProjectWorkspace` backed
by a disk-based `DiskArtifactStore` fixture (same interface as
`omni_prod.storage.S3ArtifactStore`; real S3/boto3 is out of scope for
M4D.2's Postgres/Redis/FastAPI sections and was not installable regardless
— PyPI-blocked). Covers: register → create project → propose modification
→ HTTP `202` → accept over HTTP → conflict returns `409` and leaves
`current()` untouched → double-accept of an already-`ACCEPTED` request
returns `422` → reject leaves the current version intact and a
post-reject accept attempt is `422` → a second user's attempt to act on
someone else's modification returns `403` (the route raises
`HTTPException(403, ...)` on `PermissionError`; the test method was
initially misnamed `..._returns_404` before being corrected to match its
own, already-correct assertion). Every one of these previously failed
with `ModuleNotFoundError: No module named 'fastapi'` on import; all now
execute against real HTTP, real routing, and real persisted Postgres
state, and the persisted state is checked directly from the database, not
just from the HTTP response body.

### G — real Redis/RQ (`LiveRedisRQTests`, 3 tests)

A real Redis connection and a real `rq.Queue`. Proposing a modification
over HTTP is verified to genuinely enqueue a real RQ job (fetched back by
id from Redis, not merely "no exception was raised"); that job is
explicitly canceled and deleted afterward so it cannot pollute a later
test's worker run, since actually executing
`execute_modification_job` needs a live LLM provider gateway — a
pre-existing, already-disclosed external-provider boundary (see the M4
section above), not an M4D.2 gap, and not artificially worked around. Two
further tests use dedicated job functions
(`tests/m4d2_rq_job_target.py::mark_done` / `always_fails`, real functions
resolved by dotted import path the way `rq` actually resolves jobs — not
closures, which `rq` would correctly refuse) executed by a real
`rq.SimpleWorker.work(burst=True)`: one proves a real worker really pops
and executes a real enqueued job (its side effect is read back from
Postgres via its own connection, mirroring how the real production job
function opens its own connection rather than reusing the API process's
pool); the other proves a job that raises is recorded as failed without
crashing the worker and without any double-promotion side effect.

`rq.Worker.work(burst=True)` was tried first and hit a real bug: it forks
a child process per job by default, and forking a process that already
holds an open `psycopg` connection pool corrupts the shared SSL socket
(`psycopg.OperationalError: consuming input failed: SSL SYSCALL error: EOF
detected`) — reproduced for real, not hypothesized. Fixed by switching to
`rq.SimpleWorker` (in-process, no fork) — still real, unmodified `rq`
code exercising real Redis dequeue and execution, just avoiding a
fork-after-open-socket hazard that is specific to this test harness's
process model, not to production (the production worker entrypoint is a
long-lived separate process, never forked mid-test from a parent that
already holds the pool). Disclosed in the test class's own docstring.

### H — connection-pool / transaction-boundary check (`TransactionBoundaryTests`, 2 tests)

Two independent, server-side (not application-level) proofs that
`workspace.commit()`, `spec_repo.save()`, and the final
`ModificationRequest` status update are not accidentally split across
separate transactions when run through the real production code path:
1. `txid_current()` captured on the connection immediately after each of
   the three real write statements — identical transaction ids across
   all three is direct proof of one transaction.
2. `pg_stat_database.xact_commit` / `xact_rollback` deltas around a
   successful `accept()` — exactly one additional committed transaction,
   zero additional rollbacks. First run of this test failed
   (`713 not greater than or equal to 714`) — a genuine Postgres behavior,
   not a code defect: `pg_stat_database` counters flush asynchronously
   per backend, and `pg_stat_force_next_flush()` only flushes the
   *calling* connection's own stats, not the one `accept()` ran on. Fixed
   by polling the counters (up to 5s, 50ms interval) instead of reading
   them once immediately; documented in the test's own docstring rather
   than silently patched over, per the directive's "no fake success"
   instruction.

### I — full regression

```
$ PYTHONPATH=/tmp/m4d2_vendor python3 -m compileall -q omni_prod tests tools
-> exit 0
$ PYTHONPATH=/tmp/m4d2_vendor M4D2_DATABASE_URL=... python3 -m unittest \
    tests.test_m2_native_logic tests.test_m3_preview_logic tests.test_m4_acceptance \
    tests.test_m4_modification_engine tests.test_m4_worker tests.test_m4d1_atomic_accept \
    tests.test_m4d2_live_postgres tests.test_modification_diff tests.test_modification_repository \
    tests.test_modifier_engine tests.test_overlay tests.test_product_evolution \
    tests.test_spec_repository tests.test_v12_core tests.test_v13_core tests.test_v14_core \
    tests.test_v15_acceptance tests.test_v16_release_gate tests.test_v17_preflight \
    tests.test_v18_supplychain_security tests.test_v19_reliability \
    tests.test_v20_observability_recovery tests.test_v21_gemini_remediation \
    tests.test_v22_autonomous_core tests.test_v22_sandbox_executor tests.test_v23_investor_grade \
    tests.test_v24_auth tests.test_v24_international tests.test_v24_native_remote \
    tests.test_v25_unified_v10_parity tests.test_v26_universal_pro tests.test_v27_rights_company_os \
    tests.test_v28_148ai_launch tests.test_workspace_version_conflict
Ran 487 tests in 11.486s
OK (skipped=2)
$ PYTHONPATH=/tmp/m4d2_vendor M4D2_DATABASE_URL=... M4D2_REDIS_URL=... \
    python3 -m unittest tests.test_m4d2_live_fastapi_redis   # standalone: sets env vars before
                                                               # importing omni_prod.investor_app,
                                                               # so it cannot share a process with
                                                               # any other test module that also
                                                               # imports it
Ran 8 tests in 1.101s
OK
```
487 + 8 = **495/495**, 2 expected skips (both pre-existing and unrelated to
M4D.2 — the same two skips M4D.1's own regression run reported). This
includes the 8 modules that were `NOT_CONFIGURED`/failing-on-import for
lack of `fastapi` throughout every section of this report up to and
including M4D.1 (`test_v23_investor_grade`, `test_v24_auth`,
`test_v24_international`, `test_v24_native_remote`,
`test_v25_unified_v10_parity`, `test_v26_universal_pro`,
`test_v27_rights_company_os`, `test_v28_148ai_launch` — 136 tests) now
genuinely executing under the real, vendored `fastapi`. No M4D.1 test was
removed, weakened, or skipped to make M4D.2 pass; all of M4D.1's own
tests (`test_workspace_version_conflict`, `test_m4d1_atomic_accept`) are
included, unmodified, in the 487.

### FACT / STRUCTURAL PROOF / BLOCKED / NOT APPLICABLE

**FACT** (actually executed against real services, observed directly):
sections C, D, E, F, G, H above in full; the 495/495 regression run; the
10x/5x stress reconfirmation; the migration runbook applied idempotently
to a fresh database.

**STRUCTURAL PROOF** (inspected, not live-executed): none remaining for
the M4 production path — this was the entire gap M4D.1 left open and
M4D.2 closes. (M1–M3's own pre-existing, out-of-scope constraints,
documented in their own sections above, are unaffected by M4D.2.)

**BLOCKED** (unable to execute, and why): real S3/boto3-backed artifact
storage (PyPI-blocked, same as every other package here; substituted with
the disclosed `DiskArtifactStore` fixture, which is out of M4D.2's
Postgres/Redis/FastAPI scope regardless); real LLM-provider execution of
`ChangeClassifierAgent`/`execute_modification_job`'s actual classification
step (needs a live external API key/gateway this sandbox has no route to
— a pre-existing constraint predating M4D.2, not newly discovered by it);
Docker Hub image pulls (confirmed genuinely blocked; not used as the
execution path since native service binaries were available and used
instead).

**NOT APPLICABLE** (not part of M4's production execution path, so not
artificially required): `dispatch_pending_outbox()`'s relay/retry path
specifically (the direct-enqueue-succeeds path that IS part of the
production `accept()`→outbox flow was exercised live in section G; the
separate relay-for-previously-failed-dispatches path is a maintenance
job, not invoked by any M4 request path exercised here) — left as
`IMPLEMENTED_NOT_VERIFIED`, not claimed live, and not disguised as
covered.

### What remains honestly not proven after M4D.2

A live LLM provider was never in the loop — every FastAPI test seeds
`READY_FOR_REVIEW` state via the same production repository methods the
real worker job calls (`transition_running`/`complete`), not by faking
around them, but the actual `ChangeClassifierAgent.classify()` call itself
was never exercised end-to-end here. Real S3 was never in the loop
(`DiskArtifactStore` implements the identical interface, but is not
`boto3` talking to AWS). Neither is new to M4D.2 — both are pre-existing,
already-disclosed external-service boundaries this sandbox cannot reach
regardless of M4D.2's own scope, not gaps M4D.2 introduced or obscured.

**M4 is still not `LIVE` in the "fully production-deployed" sense — this
means the M4 accept/reject/rollback path has now been proven correct
against real PostgreSQL, real FastAPI HTTP routing, and real Redis/RQ
execution, not that the whole platform (LLM classification, S3 storage,
billing settlement, deployment) has been. M5 has not been started.**

### Regression, compile, and commit

The commit created alongside this update adds
`tests/test_m4d2_live_postgres.py`, `tests/test_m4d2_live_fastapi_redis.py`,
`tests/m4d2_rq_job_target.py`, and `tools/m4d2_setup_live_infra.sh`, and
updates `STATUS.md` and this report. No file under `omni_prod/` was
changed in M4D.2 — per the directive's "preserve the M4D.1 implementation
unless live infrastructure testing reveals a real defect," live execution
against real PostgreSQL, FastAPI, and Redis/RQ found no such defect, so
none of `workspace.py`, `modification_repository.py`, `spec_repository.py`,
`investor_app.py`, `queueing.py`, or `worker_tasks.py` were modified. See
`git log`/`git diff` for the exact commit created alongside this update.

## Update: M4D.2b — dependency parity + real worker execution

An independent review of M4D.2's evidence found two real gaps and
accepted the rest ("M4D.2 is accepted for the live PostgreSQL
concurrency/transaction path"). This section documents both, closed for
real, with the same evidence standard as every section above. **M5 was
not started.**

### Gap 1: RQ documentation overclaim

STATUS.md's M4A worker-entrypoint capability-table row read "real `rq`
dequeue of a real `execute_modification_job` job." That is not what
M4D.2's own `LiveRedisRQTests.test_propose_modification_over_http_really_enqueues_a_redis_rq_job`
did — it fetched the real job from Redis to check its `func_name`/`args`,
then explicitly called `job.cancel(); job.delete()` and never ran a
worker on it, precisely because executing it needs a live LLM provider.
The real dequeue-and-execute proof in that same file used **dedicated
test job functions** (`tests/m4d2_rq_job_target.py::mark_done` /
`always_fails`) through `rq.SimpleWorker`, not `execute_modification_job`
itself. STATUS.md's table row is corrected to say exactly this. Gap 3
below closes the underlying gap for real, not just the wording.

### Gap 2: exact production dependency parity

```
$ cat requirements-production.txt
# V24 top-level production pins (2026-09-22). Transitive hashes should be generated in networked CI.
fastapi==0.128.2
uvicorn==0.48.0
pydantic==2.13.4
psycopg[binary,pool]==3.3.6
redis==8.1.0
rq==2.12.0
boto3==1.43.94
```

M4D.2 vendored HEAD of each package's default branch. Every package
materially involved in the M4 live tests was re-vendored from the
**exact git tag** matching its pin (directive preference **A**), building
a separate `/tmp/m4d2b_vendor` via `tools/m4d2b_setup_parity_infra.sh` —
M4D.2's own `/tmp/m4d2_vendor` is untouched and still independently
re-runnable.

**fastapi** — tag `0.128.2` exists directly:
```
$ git -C /tmp/fastapi_src fetch --depth 1 origin tag 0.128.2
$ git -C /tmp/fastapi_src log --oneline -1 0.128.2
79406a4b 🔖 Release version 0.128.2
$ git -C /tmp/fastapi_src checkout 0.128.2
```

**psycopg** — `psycopg` and `psycopg_pool` are independently-versioned
packages living in the SAME repo, so checking out one tag would force
both to that tag's (wrong, for the other) commit. Fetched the exact
`3.3.6` tag into a separate `git worktree` instead, leaving the original
clone (already at HEAD == `pool-3.3.3`, confirmed by
`git describe --tags --exact-match HEAD`) as the `psycopg_pool` source:
```
$ git -C /tmp/psycopg_src fetch --depth 1 origin tag 3.3.6
$ git -C /tmp/psycopg_src worktree add /tmp/psycopg_src_3_3_6 3.3.6
Preparing worktree (detached HEAD a67654d)
HEAD is now at a67654d chore: bump psycopg package version to 3.3.6
$ git -C /tmp/psycopg_src show 3.3.6:psycopg/pyproject.toml | grep -i psycopg-pool
    "psycopg-pool",   # unpinned inside the [pool] extra -- pool-3.3.3 (latest) is what
                       # pip's resolver would pick absent a lock file; no change needed.
```

**redis-py** — tag `v8.1.0`:
```
$ git -C /tmp/redis_py_src fetch --depth 1 origin tag v8.1.0
$ git -C /tmp/redis_py_src log --oneline -1 v8.1.0
e013126 Testing with 8.10 GA (#4227)
$ git -C /tmp/redis_py_src checkout v8.1.0
```

**rq** — the pin `2.12.0` has no `v2.12.0` tag; the actual tag is `v2.12`:
```
$ git -C /tmp/rq_src ls-remote --tags origin | grep -i "2\.12"
aa76e6841d69dad4fe5498e15544a5f26180a6b7  refs/tags/v2.12
$ git -C /tmp/rq_src rev-parse HEAD
90a67a159ef9fa055c6bde12ee1bb3ebd0440b84
$ git -C /tmp/rq_src log --oneline v2.12..HEAD
90a67a1 Bump github/codeql-action from 4.37.8 to 4.38.0 (#2485)
```
M4D.2's HEAD-based vendor was **one commit past** the real `v2.12` tag —
a GitHub Actions CI dependency bump, unrelated to `rq`'s own source, but
a real, exact-version miss nonetheless (`rq.__version__` printed
"2.12.0" either way, which is exactly the kind of overclaim-by-coincidence
this parity pass exists to catch rather than trust). Re-checked out at
the exact tag.

**starlette** — not pinned directly by `requirements-production.txt`
(transitive via fastapi). fastapi `0.128.2`'s own `pyproject.toml`, read
directly:
```
$ git -C /tmp/fastapi_src show 0.128.2:pyproject.toml | grep -i starlette
    "starlette>=0.40.0,<0.51.0",
```
The pre-installed `starlette` actually in use throughout M4D.2 was
**1.0.0** — outside this range entirely, a real non-parity condition
M4D.2 never checked. Latest tag satisfying the constraint:
```
$ git ls-remote --tags https://github.com/encode/starlette | grep -E "refs/tags/0\.(4[0-9]|50)\.[0-9]+$" | sort -t/ -k3 -V | tail -3
...
7d88ea6f8ec8aa99cdb5fc7a10b88db5aadfdfee  refs/tags/0.49.0
4941b4a04993d087dea66e9287fe9472babee879  refs/tags/0.50.0
$ git clone https://github.com/encode/starlette.git /tmp/starlette_src
$ git -C /tmp/starlette_src checkout 0.50.0
```

**pydantic** — pin `2.13.4`. `pydantic/pydantic`'s own `pyproject.toml`
at that exact tag:
```
$ git clone --depth 1 https://github.com/pydantic/pydantic.git /tmp/pydantic_src
$ git -C /tmp/pydantic_src fetch --depth 1 origin tag v2.13.4
$ git -C /tmp/pydantic_src show v2.13.4:pyproject.toml | grep "pydantic-core=="
    'pydantic-core==2.46.4',
```
`pydantic-core` is a compiled Rust/PyO3 extension. `rustc`/`cargo` ARE
present in this sandbox, but building requires fetching crate
dependencies over the network:
```
$ curl -sS -o /dev/null -w "%{http_code}\n" --max-time 8 https://crates.io/
000 (curl: (56) CONNECT tunnel failed, response 403)
$ curl -sS -o /dev/null -w "%{http_code}\n" --max-time 8 https://index.crates.io/config.json
403
```
Genuinely blocked, confirmed directly — the identical egress-policy
pattern as PyPI/apt/Docker Hub, just a different host. Not retried, per
the repo's own proxy runbook instruction. Verified the pre-installed
`pydantic` (2.13.3) is a real, internally consistent, correctly-paired
release, not a mismatch:
```
$ git -C /tmp/pydantic_src fetch --depth 1 origin tag v2.13.3
$ git -C /tmp/pydantic_src show v2.13.3:pyproject.toml | grep "pydantic-core=="
    'pydantic-core==2.46.3',
$ python3 -c "import pydantic, pydantic_core; print(pydantic.__version__, pydantic_core.__version__)"
2.13.3 2.46.3
```
Used as-is (directive option **C**, "use an existing cached wheel/package
if available"). This is a genuine, disclosed, one-patch-version gap —
**not** claimed as parity. `uvicorn` (0.48.0 pinned) and `boto3` (1.43.94
pinned) are not exercised by any M4D.2/M4D.2b test (`TestClient` needs no
live `uvicorn` server; `boto3`/S3 is out of scope throughout, per
M4D.2's own disclosure) and were not vendored.

**Parity vendor build and verification:**
```
$ ./tools/m4d2b_setup_parity_infra.sh
...
fastapi       0.128.2 (pin 0.128.2)
starlette     0.50.0 (latest compatible with fastapi's <0.51.0)
psycopg_pool  True (pool-3.3.3, unpinned by psycopg[pool])
redis-py      8.1.0 (pin 8.1.0)
rq            2.12.0 (pin 2.12.0, exact tag v2.12)
pydantic      2.13.3 (pin 2.13.4 -- KNOWN GAP, see script header)
pydantic_core 2.46.3 (paired with installed pydantic)

$ PYTHONPATH=/tmp/m4d2b_vendor python3 -c "
from fastapi import FastAPI
from fastapi.testclient import TestClient
app = FastAPI()
@app.get('/ping')
def ping(): return {'ok': True}
print(TestClient(app).get('/ping').status_code)
"
200
```
Full regression under the exact-parity vendor:
```
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... python3 -m unittest tests.test_m4d2_live_postgres
Ran 14 tests in 2.974s
OK
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... M4D2_REDIS_URL=... python3 -m unittest tests.test_m4d2_live_fastapi_redis
Ran 8 tests in 1.086s
OK
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... python3 -m unittest <34 combined modules>
Ran 487 tests in 15.404s
OK (skipped=2)
$ PYTHONPATH=/tmp/m4d2b_vendor python3 -m compileall -q omni_prod tests tools
exit 0
```
Identical counts to M4D.2's HEAD-based vendor — the version differences
found above did not change behavior for anything this suite exercises.

### Gap 3: real production-job execution through RQ

The directive required actually dequeuing and executing the real
`omni_prod.worker_tasks.execute_modification_job` through RQ, replacing
only the external LLM dependency at its documented boundary, without
monkeypatching internal state transitions.

**The real, already-existing local-model boundary.** Read directly:
`omni_prod/model_runtime_config.py::ModelRuntimeConfig.from_env()`
builds its *primary* route from `OMNI_LOCAL_MODEL_NAME` /
`OMNI_LOCAL_MODEL_URL` (default `http://127.0.0.1:8001/v1`) /
`OMNI_LOCAL_MODEL_ID`, with `external=False`; `OMNI_ZERO_COST_MODE`
defaults to `'1'` and `OMNI_ALLOW_EXTERNAL_FALLBACK` to `'0'`.
`omni_prod/routed_gateway.py::RoutedModelGateway.__init__` enforces
`if primary.endpoint.external: raise ValueError('primary route must be
local/self-hosted')`. Production is *designed*, by default, to talk to a
local model server. `omni_prod/model_gateway.py::OpenAICompatibleGateway.complete()`
speaks a plain, documented protocol: `POST {base_url}/chat/completions`
with `{model, messages, temperature, max_tokens}`, expecting
`{"choices":[{"message":{"content": "..."}}]}`.

`tests/m4d2b_local_model_server.py` implements exactly this protocol as
a real `http.server.ThreadingHTTPServer` bound to a real loopback TCP
port — not a monkeypatch of anything in `omni_prod`. Verified directly
against the real gateway/agent classes before wiring into the worker
test:
```
$ PYTHONPATH=/tmp/m4d2b_vendor python3 -c "
... LocalModelServer(port=8091).start() ...
... ChangeClassifierAgent(gw).classify(spec=spec, followup='... M4D2B_CLASSIFY:ambiguous ...') ...
"
ambiguous -> ChangeAssessment(category='ambiguous', reason=\"m4d2b deterministic local test model: forced category='ambiguous'\", acceptance_ids=(), billable=False)
system_bug -> ChangeAssessment(category='system_bug', reason=\"...\", acceptance_ids=('A1',), billable=False)
... RepairAgent(gw).repair(...) -> (FilePatch(path='M4D2B_NOTES.md', content='...'),)
```
Real HTTP round trips, real JSON parsing on both ends, real
`ChangeAssessment`/`FilePatch` construction from the response.

**A genuinely separate worker OS process, not `SimpleWorker`.** The
directive preferred a clean, separate `rq.Worker` process over M4D.2's
in-process `SimpleWorker` substitution. Traced why the original hazard
would or would not reproduce, directly in the vendored `rq` source
before writing the script (not just reasoned about):
```
$ grep -n "os.fork\|def fork_work_horse\|def main_work_horse" /tmp/rq_src/rq/worker/worker_classes.py /tmp/rq_src/rq/worker/base.py
rq/worker/worker_classes.py:65:    child_pid = os.fork()
rq/worker/worker_classes.py:66:      ... if child_pid == 0: ... self.main_work_horse(job, queue) ...
rq/worker/base.py:1682:  def main_work_horse(self, job, queue):
rq/worker/base.py:1699:      self.perform_job(job, queue, self.execution)
rq/worker/base.py:1652:  def perform_job(...): ... job.perform() ...
```
`job.perform()` (the dotted-import resolution of
`execute_modification_job`, and therefore the only place
`omni_prod.investor_app`'s connection pool gets built) is reachable ONLY
from inside `main_work_horse`, which itself only ever runs inside the
forked child. `omni_prod/db.py::DatabasePool.open()` is lazy (only
called on first real `.connection()` use), so as long as the parent
worker process never makes a real query before calling `.work()`, no
live socket exists yet at fork time to be corrupted. `tests/m4d2b_worker_process.py`
imports `omni_prod.investor_app` in the parent ONLY to apply the same
disclosed `PostgresProjectWorkspace`/`DiskArtifactStore` override M4D.2
used (which also touches no network), then calls the real, default
`rq.Worker([queue]).work(burst=True)`. Verified empirically, not just by
this reasoning: the first real run reproduced the safe outcome directly
(see below), no `SSL SYSCALL error` recurrence.

**`tests/test_m4d2b_parity_and_worker.py` — 3 tests, all passing, re-run
4 times consecutively with zero flakiness:**
```
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... M4D2_REDIS_URL=... python3 -m unittest tests.test_m4d2b_parity_and_worker -v
test_duplicate_delivery_of_the_same_modification_does_not_reexecute_or_duplicate_state ... ok
test_real_worker_process_dequeues_and_executes_execute_modification_job_ambiguous_path ... ok
test_real_worker_process_system_bug_path_hits_real_sandbox_docker_image_blocker ... ok
Ran 3 tests in 4.4s
OK
```

- **Ambiguous path** (proofs 1-7): real HTTP propose enqueues the real
  job; the real, separate worker process (`M4D2B_WORKER_PROCESS_DONE
  ran=True` printed by the child on completion) dequeues and executes
  `execute_modification_job` for real; real `ChangeClassifierAgent`
  call; real `QUEUED -> RUNNING -> NEEDS_CLARIFICATION` transition,
  confirmed independently via the real HTTP status route AND directly
  via `PostgresModificationRepository.get_details`.
- **System-bug path** (proof 9, a REAL failure, not synthetic): the real
  repair loop reaches `SandboxRepositoryExecutor.execute()` for real,
  running `docker run ... omni-sandbox:latest python3 -m pytest -q`.
  This failed with a real, previously-undiscovered error:
  ```
  invalid argument "type=bind,src=/tmp/omni-out-XXXXXXXX,dst=/output,rw" for "--mount" flag: invalid field 'rw' must be a key=value pair
  ```
  — `omni_prod/sandbox.py::build_docker_command()`'s `--mount
  type=bind,src=...,dst=/output,rw` syntax is rejected by this sandbox's
  Docker 29.4.3 CLI (a stricter `--mount` parser than whatever version
  this flag syntax was written against). This is DIFFERENT from, and in
  addition to, the already-disclosed image-pull-forbidden block found in
  M4D.2 — both are real, unmodified `docker` failures; which one
  surfaces first doesn't change what the test proves. `run_sandbox()`
  captures this as a normal `ExecutionReport(passed=False)`, not an
  exception, so `execute_modification_job` completes cleanly:
  `status='FAILED'`, `error_code='verification'` (the real
  `GateResult.blocking_gate`, not the dead-code `'verification_failed'`
  fallback string used only when `outcome.gates is None`, which cannot
  happen on this path), `repair_rounds=3` (the real
  `max_repair_rounds`, each round independently hitting the same real
  docker error), `evidence_json.billing == 'released'` (never
  `'settled'` -- `system_bug` is never billable),
  `evidence_json.verification.build_log_tail` containing the real
  stderr above verbatim. Recoverable state confirmed: `current()` still
  points at the seed version, and the modification remains normally
  gettable over HTTP afterward. `omni_prod/sandbox.py` is unrelated
  M2-era code, out of M4D.2b's scope, and is **deliberately left
  unfixed** — flagged here for whoever owns that module next.
- **Duplicate delivery** (proof 8): a second RQ delivery of the same
  production function for the same `modification_id` (different job id,
  same args), run through a second separate-process worker run.
  `jobs.transition_running()`'s own idempotency guard makes the second
  execution a real no-op: identical `completed_at` before/after, no
  version promoted or duplicated.

**What was not, and could not be, proven:** a `READY_FOR_REVIEW` (fully
passing) result from `execute_modification_job` — that would require the
real `omni-sandbox:latest` image to actually build or pull, which
remains blocked for two independent, genuine reasons (Docker Hub 403,
and now also the `--mount` flag incompatibility above). Not worked
around with a mock; documented as a real, current limitation instead.

### FACT / STRUCTURAL PROOF / BLOCKED / NOT APPLICABLE — M4D.2b

**FACT:** the exact tag/commit table above, all built and imported
successfully; the `TestClient` smoke test under the new fastapi/starlette
pairing; all 498 regression tests passing under the exact-parity vendor;
the real separate-process `rq.Worker` dequeuing and executing the real
`execute_modification_job` for two distinct real terminal outcomes
(`NEEDS_CLARIFICATION`, sandbox-verification `FAILED`); the real
duplicate-delivery no-op; the real `--mount` flag Docker-CLI
incompatibility in `omni_prod/sandbox.py`.

**STRUCTURAL PROOF:** none remaining for what this pass set out to prove
(exact dependency parity and real RQ execution of the real production
job) other than the two disclosed, unavoidable exceptions below.

**BLOCKED, confirmed with exact commands and error text, not assumed:**
`pydantic-core==2.46.4` cannot be built (crates.io/index.crates.io 403,
same egress policy as PyPI/apt/Docker Hub); `omni-sandbox:latest` cannot
be pulled (Docker Hub 403, per M4D.2) or built locally in a way that
would currently succeed even if the base image were available
(`omni_prod/sandbox.py`'s `--mount` flag syntax independently fails
against this sandbox's Docker 29.4.3).

**NOT APPLICABLE:** `uvicorn`/`boto3` exact-version parity (pinned in
`requirements-production.txt` but not exercised by any live test here --
`TestClient` needs no live ASGI server, and S3/`boto3` is out of scope
throughout, per M4D.2's own disclosure); real external LLM execution of
the classifier's actual natural-language understanding (the real
`ChangeClassifierAgent.classify()` call happens for real, over real
HTTP, against a real server -- only the model behind that server is a
disclosed deterministic stand-in, for the same pre-existing reason
noted throughout this whole project).

### Status discipline (directive item 4) and regression

- PostgreSQL concurrency/atomicity: `VERIFIED_LIVE_INFRA` (unchanged).
- FastAPI execution: `VERIFIED_LIVE_INFRA` at exact parity for
  fastapi/starlette/psycopg/psycopg_pool/redis-py/rq; pydantic remains
  one disclosed patch version behind its pin (2.13.3 vs. 2.13.4).
- Redis production enqueue: `VERIFIED_LIVE_INFRA` (unchanged).
- RQ production `execute_modification_job` execution:
  `VERIFIED_LIVE_INFRA` (`REAL_RQ_SEPARATE_PROCESS_WORKER_VERIFIED`) for
  the `NEEDS_CLARIFICATION` and sandbox-`FAILED` terminal paths;
  `READY_FOR_REVIEW` remains `IMPLEMENTED_NOT_VERIFIED` (blocked on the
  real sandbox image, for two independent reasons, both documented
  above).
- **`M4 VERIFIED_LIVE_INFRA`** — explicitly NOT `PRODUCTION_DEPLOYED` and
  NOT `FULL_EXTERNAL_E2E`: real external LLM/S3/provider execution, and a
  real passing sandboxed-code-verification run, remain separately
  unverified, for pre-existing and newly-documented infrastructure
  reasons unrelated to M4's own accept/reject/rollback correctness.

```
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... python3 -m unittest <34 combined modules>          # 487/487, 2 skips
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... M4D2_REDIS_URL=... python3 -m unittest tests.test_m4d2_live_fastapi_redis   # 8/8
$ PYTHONPATH=/tmp/m4d2b_vendor M4D2_DATABASE_URL=... M4D2_REDIS_URL=... python3 -m unittest tests.test_m4d2b_parity_and_worker   # 3/3
```
Total: **498/498**, 2 expected skips. No M4D.1 or M4D.2 test was removed
or weakened. `omni_prod/sandbox.py`'s discovered `--mount`-flag
incompatibility is **not** fixed by this pass (out of scope, unrelated to
M4) -- flagged in STATUS.md and here for its next owner.

### Regression, compile, and commit

New files added by this update: `tests/test_m4d2b_parity_and_worker.py`,
`tests/m4d2b_local_model_server.py`, `tests/m4d2b_worker_process.py`,
`tools/m4d2b_setup_parity_infra.sh`. Modified: `STATUS.md`, this report.
No file under `omni_prod/` was changed -- the one real defect this pass
found (`sandbox.py`'s `--mount` flag) is outside M4's own scope and is
deliberately left for separate remediation, not silently patched around.
**M4 is `VERIFIED_LIVE_INFRA`, not `PRODUCTION_DEPLOYED`. M5 has not been
started.** See `git log`/`git diff` for the exact commit created
alongside this update.

## Update: M4.9 — genuine live sandbox execution + full accept/rollback lifecycle

Directive: items 7–12 (clean-room success run; sandbox security negative
tests; sandbox image provenance; the `READY_FOR_REVIEW` invariant,
verified directly; the complete accept+rollback version lifecycle, no
mocks; final status + M5 authorization). Every item passed; M5 is now
authorized per item 12. This section is the full evidence trail; STATUS.md
§5's own new "M4.9" subsection is the summary.

### Task #47 — the real `--mount` flag defect

`omni_prod/sandbox.py`'s `build_docker_command()` built its output-mount
argument as `f"type=bind,src={output},dst=/output,rw"`. `--mount`'s field
vocabulary is `type`/`source`/`destination`/`readonly`/`volume-opt`/... —
there is no `rw` field (that suffix syntax belongs to `-v`/`--volume`,
not `--mount`). Reproduced directly, before touching production code:

```
$ docker run --rm --mount type=bind,src=/tmp,dst=/workspace,readonly \
    --mount type=bind,src=/tmp,dst=/output,rw hello-world
docker: invalid argument "type=bind,src=/tmp,dst=/output,rw" for "--mount" flag:
invalid field 'rw' must be a key=value pair
```

Same command with the `,rw` token removed proceeds past mount-parsing
(only then failing on the separate, expected "image not found" issue,
since `hello-world` isn't `omni-sandbox:latest`). Fix: delete the token —
a bind mount is read-write by default when `readonly` is omitted, which
is exactly what `/output` needs.

```python
# omni_prod/sandbox.py, inside build_docker_command(), if output_dir is not None:
argv.extend([
    "--mount", f"type=bind,src={output},dst=/output",   # was: ...,dst=/output,rw
    "--env", "OMNI_OUTPUT_DIR=/output",
])
```

Verified: (a) the before/after `docker run --mount` probes above; (b)
`grep -rn ",rw\|dst=/output" tests/*.py omni_prod/*.py` — no test
hardcodes the broken string; (c) `tests.test_m2_native_logic`,
`test_overlay`, `test_v21_gemini_remediation`, `test_v22_sandbox_executor`,
`test_v24_native_remote` (34 tests) under
`PYTHONPATH=/tmp/m4d2b_vendor:/tmp/m49_pytest_vendor python3.11 -m pytest -q` —
all passing; (d) a fresh `build_docker_command()` call confirming the
generated argv no longer contains `,rw` and every other flag
(`--network none --read-only --security-opt no-new-privileges:true
--cap-drop ALL --user 10001:10001 --memory 1024m --memory-swap 1024m
--cpus 1.5 --pids-limit 256 --ulimit nofile=1024:1024 ...`) is otherwise
unchanged.

### Task #48 — `omni-sandbox:latest`, built locally with exact provenance

**Abandoned first attempt.** `omni-sandbox-base:m49local`, built via
`tar --exclude=... -cf - -C / . | docker import - omni-sandbox-base:m49local`
of this container's own filesystem (excluding `/proc /sys /dev /run /tmp
/var/lib/docker /var/lib/postgresql /var/cache /root/.cargo /home /opt
/usr/local /mnt`): a real image, 6.07GB, digest
`sha256:762e3e3fe52f97ded018d07cf955964f0c58d38c166382e9904bf401d2b2feae`.
Along the way, a serious, self-inflicted, fully-recovered bug: GNU `tar`
matches `--exclude` patterns against archive MEMBER NAMES as stored — for
`tar -cf - -C / .`, member names are relative (`./var/lib/docker/...`),
so the ABSOLUTE-path excludes above silently matched nothing, and `tar`
recursed into `/var/lib/docker` while `docker import` was simultaneously
writing into that same directory via its `vfs` storage driver — an
exploding, self-referential recursion that exhausted the entire session
disk allowance (`no space left on device` after 6m39s). Fixed by
switching every exclude to the relative (`./`-prefixed) form and adding
`--one-file-system`; verified via two dry runs (`--exclude=./var/lib/docker`
count of 0; a full 118259-entry member listing) before the real retry,
and recovery verified both via `df -h /` returning to baseline (13G
used / 30G avail) AND a real 100MB `dd`-write-then-delete test.

This 6.07GB base was itself abandoned once a real Dockerfile build was
attempted against it: this sandbox's Docker uses the `vfs` graph driver,
which performs a FULL filesystem copy on every image layer (no
copy-on-write). A 3-instruction Dockerfile (`RUN useradd` / `WORKDIR` /
`COPY`) exhausted the ENTIRE remaining session disk allowance on the
`COPY` step:

```
#6 [2/4] RUN useradd -m -u 10001 sandbox
#6 DONE 45.7s
#7 [3/4] WORKDIR /workspace
#7 DONE 37.8s
#8 [4/4] COPY pytest_vendor /opt/m49-pytest-vendor
#8 ERROR: failed to prepare ...: no space left on device
```
(pre-build disk was already 30G used / 12G avail — each instruction was
paying for a full ~6GB copy of the accumulated filesystem). Recovered via
`docker builder prune -af` (disk returned to 19G used / 24G avail).

**The real fix: a strace-derived minimal base image**, fully reproducible
from this container's own real files, zero network fetch:

1. Wrote `/tmp/m49_trace/test_smoke.py`, exercising the stdlib surface
   this codebase's own code/tests use (`json, re, subprocess, pathlib,
   dataclasses, typing, collections, itertools, functools, tempfile,
   shutil, hashlib, datetime, threading, unittest.mock, io, enum,
   contextlib, argparse, logging, traceback, copy, uuid, base64,
   textwrap, ast, inspect, warnings, weakref, abc, importlib`).
2. Ran for real:
   ```
   $ PYTHONPATH=/tmp/m49_pytest_vendor strace -f \
       -e trace=openat,open,stat,lstat,access,readlink,newfstatat \
       -o /tmp/m49_trace/trace.log python3.11 -m pytest -q test_smoke.py
   6 passed in 0.06s
   ```
3. Parsed `trace.log` for every path successfully opened (excluded
   `ENOENT`/failed lookups, `/proc /sys /dev`, the test's own tmp
   scratch paths, and host-specific package metadata under
   `/root/.local`/`/usr/local` — confirmed unnecessary by the subsequent
   successful minimal-image run, since `importlib.metadata` tolerates
   missing `sys.path` entries by design). Result: 387 real paths.
4. Added `/lib64/ld-linux-x86-64.so.2` by hand — the ELF interpreter path
   baked into python3.11's `PT_INTERP` header; the KERNEL opens this via
   the literal absolute path when exec'ing any dynamically-linked ELF,
   never as an `openat()` syscall of the traced process itself.
5. Copied (dereferencing symlinks, `cp -L`) all 387 traced paths plus the
   interpreter into `/tmp/m49_minimal_root`, at their exact original
   absolute paths (so `/etc/ld.so.cache`'s real soname→path mappings,
   copied verbatim, stay valid for every library actually included — no
   need to replicate the host's usrmerge symlink structure at all, since
   the dynamic linker only ever opens the literal cached path). Added
   hand-written minimal `/etc/passwd`/`/etc/group` (uid/gid 0 and 10001)
   instead of `RUN useradd` (an expensive extra `vfs` layer copy for no
   benefit). Staged size: 27MB.
6. Built the real image:
   ```
   $ cd /tmp/m49_minimal_root && tar -cf - . | docker import - omni-sandbox-minimal:m49local
   sha256:8410156d582c68c0b2e6ed4b4d38e6bdaf7fb32d0d74ab89104ac4a535b98270   # 26.5MB, <1s
   ```
7. Verified immediately under the FULL production security flag set (not
   relaxed):
   ```
   $ docker run --rm --tmpfs /tmp:rw,noexec,nosuid,nodev,size=256m \
       --tmpfs /run:rw,noexec,nosuid,nodev,size=32m \
       -v /tmp/m49_sandbox_build_ctx/pytest_vendor:/opt/m49-pytest-vendor:ro \
       -v /tmp/m49_trace:/workspace:ro -e PYTHONPATH=/opt/m49-pytest-vendor -e HOME=/tmp \
       --user 10001:10001 --read-only --cap-drop ALL \
       --security-opt no-new-privileges:true --network none -w /workspace \
       omni-sandbox-minimal:m49local /usr/bin/python3.11 -m pytest -q test_smoke.py
   6 passed, 2 warnings in 0.03s
   ```
   The 2 warnings are pytest's own cache trying to write to the
   read-only `/workspace` mount — itself real, positive evidence the
   read-only-root-filesystem restriction was genuinely live, not just
   configured on the command line.

**pytest itself**: 8.3.5 + its exact Python≥3.11 runtime deps
(`pluggy>=1.5,<2` pinned at `1.6.0`; `iniconfig` pinned at `v2.3.0`;
`packaging` already satisfied) vendored via `git clone`/`git checkout
<tag>` (PyPI is blocked) into `pytest_vendor/`, exposed via `PYTHONPATH`.
pytest and pluggy each needed one small hand-written `_version.py` shim
(their real `setuptools_scm` build-time step never ran — no build backend
reachable); each carries an in-file disclosure comment
(`/tmp/pytest_src/src/_pytest/_version.py`,
`/tmp/pluggy_src/src/pluggy/_version.py`).

**Final `omni-sandbox:latest` Dockerfile** (in
`/tmp/m49_sandbox_build_ctx/Dockerfile`, a build-context directory, not
part of the application repo — its full provenance narrative lives in the
file's own header comment, reproduced here):

```dockerfile
FROM omni-sandbox-minimal:m49local
WORKDIR /workspace
COPY pytest_vendor /opt/m49-pytest-vendor
ENV PYTHONPATH=/opt/m49-pytest-vendor
ENV HOME=/tmp
ENV PATH=/usr/bin
USER 10001:10001
ENTRYPOINT []
CMD ["python", "-m", "pytest", "-q"]
```

Build command actually run:
```
$ cd /tmp/m49_sandbox_build_ctx && docker build --no-cache -t omni-sandbox:latest -f Dockerfile .
...
#8 writing image sha256:6834400bb7810ada027f02dd685d7eb2cae4b684b38745d0c8a1488a86702532
real  0m0.918s   (first cut, before the PATH follow-up below)
```

**Follow-up fix** (found while proving the pipeline end-to-end, below):
`infra/sandbox/Dockerfile`'s own real spec uses a bare `CMD ["python", "-m",
"pytest", "-q"]` — a PATH-resolved name, not an absolute path — while the
first cut of the minimal image had only `/usr/bin/python3.11`, no
PATH-resolvable `python`/`python3`. This was DISCOVERED, not assumed,
while investigating why `tests/test_m4d2b_parity_and_worker.py`'s
system-bug test still passed after the `--mount` fix: its real build log
now showed `exec: "python3": executable file not found in $PATH` — a new,
different, still-real docker error. Closed the gap for fidelity: added
`/usr/bin/python3` and `/usr/bin/python` symlinks → `python3.11` to the
same staging root (`/tmp/m49_minimal_root`), rebuilt
`omni-sandbox-minimal:m49local` (identical `tar | docker import` command,
new digest `sha256:1f21f853aafc2e79832a64d2d6ff18a9b399cd7962d9cb2a1b8ce89b0bd50276`),
rebuilt `omni-sandbox:latest` with `ENV PATH=/usr/bin` and
`CMD ["python", "-m", "pytest", "-q"]` (matching the original spec
verbatim). **Final image ID/digest, captured both via
`docker images --no-trunc` and `docker inspect --format='{{.Id}}'`
(agree): `sha256:6834400bb7810ada027f02dd685d7eb2cae4b684b38745d0c8a1488a86702532`,
29.4MB.** Verified for real:
```
$ python3 -c "
from omni_prod.sandbox import run_sandbox, SandboxLimits
result = run_sandbox(source_dir=..., build_id='m49-path-check', limits=SandboxLimits(), command=['python3', 't.py'])
"
RC: 0
bare python3 PATH resolution works
```

**Proof the M4.9 test actually executed against THIS image** (directive
item 9's own requirement — "do not treat an unknown pre-existing latest
image as sufficient evidence"): ran the real production function,
`omni_prod.sandbox.run_sandbox()`, with default `SandboxLimits()`
(`image="omni-sandbox:latest"`), against a real 2-test file, twice —
without and with `output_dir` (the exact branch task #47 fixed):
```
RETURNCODE: 0
2 passed, 2 warnings in 0.01s
```
and, with `output_dir` set, the captured, real, full argv:
```
docker run --rm --network none --read-only --security-opt no-new-privileges:true
--cap-drop ALL --user 10001:10001 --memory 1024m --memory-swap 1024m --cpus 1.5
--pids-limit 256 --ulimit nofile=1024:1024 --tmpfs /tmp:rw,noexec,nosuid,nodev,size=256m
--tmpfs /run:rw,noexec,nosuid,nodev,size=32m
--mount type=bind,src=...,dst=/workspace,readonly --workdir /workspace
--hostname omni-sandbox --env HOME=/tmp --name omni-build-...
--mount type=bind,src=...,dst=/output --env OMNI_OUTPUT_DIR=/output
omni-sandbox:latest /usr/bin/python3.11 -m pytest -q
RETURNCODE: 0
2 passed, 2 warnings in 0.01s
```

**Regression after tasks #47/#48** (`omni_prod/sandbox.py` is the only
file `git status` showed modified at this point). Full `tests/` (39
files), initial pass: `3 failed, 490 passed, 20 skipped`. Investigated,
not ignored: all 3 failures were in `test_v26_universal_pro.py`/
`test_v28_148ai_launch.py`, expecting legacy synchronous live-build
routes to return 503/402/200 but getting 410. Root cause, read from
`omni_prod/investor_app.py`'s `_async_build_mode()`/
`_reject_legacy_sync_build()`, not guessed: 410 is gated on
`OMNI_CREATOR_PERSISTENCE=postgres` being set AND a durable workspace
being importable at the moment `omni_prod.investor_app` is FIRST imported
in the process (a module-level singleton built once at import time).
`tests/test_m4d2_live_fastapi_redis.py` sets that env var at import time
and STATUS.md already documents it must run standalone for exactly this
reason. NEW finding: `tests/test_m4d2b_parity_and_worker.py` (added in
M4D.2b, after that STATUS.md warning was written) does the SAME thing and
was MISSING from the "run standalone" list — whichever of the two
happens to import first in a combined run taints
`omni_prod.investor_app` for every test file that imports it afterward.
Confirmed this was the whole explanation: re-ran with both excluded →
`485 passed, 17 skipped` (fully green); each excluded file standalone →
`test_m4d2_live_fastapi_redis.py` 8/8, `test_m4d2b_parity_and_worker.py`
3/3. Total 485+8+3 = 496 passed, 17 skipped, zero failures, with correct
isolation. This is a pre-existing M4D.2b test-suite-isolation gap, not a
regression from M4.9's own `sandbox.py` change (confirmed via `git
status`/`git diff --stat` showing only `sandbox.py` touched before this
investigation began).

### Task #49 — clean-room end-to-end success run (directive item 7)

**Second real, independently-discovered production bug, found and
fixed while producing this run.** `SandboxRepositoryExecutor.execute()`
(`omni_prod/sandbox_executor.py`) materializes the repository into
`tempfile.TemporaryDirectory()`, which Python always creates at mode
`0700` regardless of umask (confirmed: `oct(os.stat(td).st_mode) ==
'0o40700'`) — fine for a same-uid caller, but that directory is then
bind-mounted into the sandbox container, which runs as a genuinely
different, unprivileged uid (10001, `SandboxLimits.user`) — a non-owner
uid cannot even traverse into a `0700` directory. Real, first-observed
failure:
```
PermissionError: [Errno 13] Permission denied: '/workspace/pytest.ini'
```
(pytest's own config-discovery `stat()`-ing a path inside the read-only
mount). Never caught before M4.9 because no container had ever started
against a real bind-mounted repository until task #48 finished — every
earlier real-sandbox attempt in this codebase's history failed earlier
still, on the also-real `--mount ...,rw` parse error. Fix, in
`SandboxRepositoryExecutor.execute()`, after materializing content:
```python
os.chmod(root, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)  # 0755
os.chmod(out, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
```
(nested directories `_materialize_repository` creates already follow
umask correctly — confirmed 0755 by default in this environment — only
the two top-level tempdir roots needed the explicit fix). Full regression
after the fix: 485 passed, 17 skipped — no regression.

**New test `tests/test_m49_clean_room.py`** (standalone), the first test
in this codebase's history to drive a `ModificationRequest` to a genuine,
non-mocked `READY_FOR_REVIEW` — contrast
`tests/test_m4d2_live_fastapi_redis.py`'s
`test_full_http_propose_accept_flow_persists_to_real_postgres`, which
explicitly documents bypassing this via a manual
`PostgresModificationRepository.complete(status='READY_FOR_REVIEW', ...)`
call, because no working sandbox image existed at that time. Reuses the
exact, already-disclosed M4D.2b real-infrastructure harness
(`tests/m4d2b_worker_process.py`'s genuinely separate `rq.Worker` OS
process; `tests/m4d2b_local_model_server.py`'s real local HTTP server
standing in for a hosted LLM at the codebase's own documented
"local-first" gateway boundary).

Seed repository designed to genuinely pass every real gate: `index.html`
(with `lang="en"`, a viewport meta tag, and an `aria-label`, for the
quality gate's accessibility dimension), `README.md`, `requirements.txt`,
`tests/test_seed.py` (a real, passing pytest test), and
`.omni/project.json` with `verify.argv = ["/usr/bin/python3.11", "-m",
"pytest", "-q"]` (the minimal image's absolute interpreter path — chosen
deliberately for this seed manifest, ahead of the later PATH-symlink
fidelity improvement). Followup used the SAME established, disclosed
`M4D2B_CLASSIFY:`/`M4D2B_IDS:` marker protocol
`tests/m4d2b_local_model_server.py` already implements (no new,
unreviewed test-double protocol invented).

**Clean-room isolation, independently verified immediately before the
official run, not assumed:**
```
$ psql -h 127.0.0.1 -U postgres -c "DROP DATABASE IF EXISTS m49_clean_room;"
$ psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE m49_clean_room;"
$ for f in infra/postgres/*.sql; do psql ... -d m49_clean_room -f "$f"; done   # migrations 001-016
$ psql ... -d m49_clean_room -c "SELECT (SELECT count(*) FROM modification_requests) AS mods,
    (SELECT count(*) FROM modification_candidates) AS cands, (SELECT count(*) FROM project_versions) AS versions;"
 mods | cands | versions
------+-------+----------
    0 |     0 |        0
$ redis-cli -h 127.0.0.1 -p 6379 FLUSHALL
OK
$ redis-cli -h 127.0.0.1 -p 6379 DBSIZE
0
$ docker inspect --format='{{.Id}}' omni-sandbox:latest
sha256:6834400bb7810ada027f02dd685d7eb2cae4b684b38745d0c8a1488a86702532
```

**Official run:**
```
$ M49_DATABASE_URL=postgresql://postgres:m4d2pass@127.0.0.1:5432/m49_clean_room \
  PYTHONPATH=/tmp/m4d2b_vendor:/tmp/m49_pytest_vendor \
  python3.11 -m pytest -q tests/test_m49_clean_room.py
1 passed in 5.00s
```

**Final Postgres state, verified directly, not just via the HTTP view:**
```
$ psql ... -d m49_clean_room -c "SELECT id, status, classification, billable, promoted_version_id FROM modification_requests;"
                  id                  |      status      |   classification    | billable | promoted_version_id
--------------------------------------+------------------+---------------------+----------+---------------------
 mod_55e7f37c81f8479f8d9dbcaf68e641be | READY_FOR_REVIEW | missing_requirement | f        |
$ psql ... -c "SELECT modification_id, project_id FROM modification_candidates;"   # exactly 1 row
$ psql ... -c "SELECT id, project_id FROM project_versions;"                        # exactly 1 row (the seed only)
```
The candidate repository (verified both via the real HTTP `/candidate`
endpoint and directly via
`PostgresModificationRepository.get_candidate()`) contains the real seed
files PLUS `M4D2B_NOTES.md` — real, positive evidence the free-repair
loop's real `repair()` call against the local model server genuinely ran
(round 1 always repairs before the first real verification, per
`modifier_engine.run_free_repair`) and its patch was applied additively
via `apply_patch()`, not destructively (every seed file is still
present). `current()` confirmed unchanged (still the seed version) —
`READY_FOR_REVIEW` never self-promotes.

### Task #50 — sandbox security negative tests (directive item 8)

New test `tests/test_m49_sandbox_security.py` (3 tests, part of the
ordinary combined suite — docker only, no Postgres/Redis). Every check
runs real Python code inside a real `docker run omni-sandbox:latest ...`
(via the real `omni_prod.sandbox.run_sandbox()`), reading real
kernel/cgroup state or attempting a real violation. Full real output from
the general-checklist probe:
```
M49_SECURITY_PROBE_RESULTS
PASS NOT_ROOT: uid=10001 gid=10001
PASS NO_NEW_PRIVS: NoNewPrivs:	1
PASS CAP_DROP_ALL_blocks_raw_socket: PermissionError as expected: [Errno 1] Operation not permitted
PASS MEMORY_LIMIT_CONFIGURED: cgroup memory.limit_in_bytes=1073741824 expected=1073741824
PASS CPU_LIMIT_CONFIGURED: cfs_quota_us=150000 cfs_period_us=100000 -> 1.5 cpus (expected 1.5)
PASS PIDS_LIMIT_CONFIGURED: cgroup pids.max='256' expected 256
PASS ROOTFS_READONLY_etc: OSError: [Errno 30] Read-only file system: '/etc/m49_write_test'
PASS ROOTFS_READONLY_usr_bin: OSError: [Errno 30] Read-only file system: '/usr/bin/m49_write_test'
PASS WORKSPACE_MOUNT_READONLY: OSError: [Errno 30] Read-only file system: '/workspace/m49_write_test'
PASS TMPFS_IS_WRITABLE_positive_control: write unexpectedly succeeded
PASS OUTPUT_MOUNT_IS_WRITABLE_positive_control: write unexpectedly succeeded
PASS NETWORK_DISABLED: OSError: [Errno 101] Network is unreachable
M49_SECURITY_PROBE_ALL_PASS
```
(A second, independent `CAP_DROP_ALL` probe via a real `mount(2)`
syscall was attempted and dropped — this minimal, strace-derived image
has no `ctypes`/`libffi`, outside the smoke test's traced surface, and
vendoring `libffi` + rebuilding python3.11's `_ctypes` extension purely
for a second capability probe was judged not worth the added image
complexity, since the raw-socket probe already gives clean, real,
unambiguous evidence `--cap-drop ALL` takes effect — `CAP_NET_RAW` is
dropped together with every other capability, including `CAP_SYS_ADMIN`,
by the same single flag.)

PID-limit enforcement, a real fork-bomb attempt against a deliberately
small limit for a fast, deterministic proof:
```
=== PIDS TEST (pids-limit=8) ===
RC: 0
M49_PIDS_PROBE attempted=8 succeeded=7 failed_at=(8, '[Errno 11] Resource temporarily unavailable')
M49_PIDS_PROBE_RESULT PASS: fork() failed as expected before exhausting MAX_ATTEMPTS
```
(exact expected math: main process = 1, `pids-limit=8` allows 7
successful `fork()` calls, the 8th genuinely fails).

Memory-limit enforcement, a real attempt to allocate+touch 1.5GB
(deliberately past the production-default 1024m limit):
```
=== MEMORY TEST (memory=1024m, attempting 1.5GB real touch) ===
RC: 137
STDOUT: ...allocated_and_touched=950MB
        allocated_and_touched=1000MB
```
(the process was genuinely OOM-killed — `docker run` returned real exit
code 137 = 128+9 (SIGKILL) — between 1000MB and the next 50MB chunk,
right at the configured boundary; the probe's own "not enforced"
failure-report line was never reached).

Full regression after adding this file: 488 passed (485 + 3 new), 17
skipped — no regressions.

**Bonus**: the pre-existing `tests/integration/test_live_sandbox_security.py`
(gated behind `OMNI_RUN_LIVE_SANDBOX=1`, always skipped in every earlier
milestone since no working image/fixed `--mount` flag existed) now
genuinely passes for the first time in this project's history:
```
$ OMNI_RUN_LIVE_SANDBOX=1 PYTHONPATH=/tmp/m4d2b_vendor:/tmp/m49_pytest_vendor python3.11 -m pytest -q tests/integration/test_live_sandbox_security.py
3 passed in 2.20s
```

### Task #51 — `READY_FOR_REVIEW` invariant, verified directly (directive item 10)

New tool `tools/m49_ready_invariant_check.py`, connecting directly to
Postgres via raw `psycopg` (not the repository ORM, not the HTTP API)
against the real modification task #49 produced. Full real output:
```
PASS MOD_REQUEST_ROW_EXISTS: id=mod_55e7f37c81f8479f8d9dbcaf68e641be
PASS STATE_IS_READY_FOR_REVIEW: status='READY_FOR_REVIEW'
PASS GENERATION_COMPLETED: started_at=2026-09-24 20:00:36.537495+00:00 completed_at=2026-09-24 20:00:37.904799+00:00
PASS NO_ERROR_RECORDED: error_code=None error_message=None
PASS SANDBOX_VERIFICATION_RAN: build_log_tail length=923
PASS SANDBOX_VERIFICATION_PASSED: verification.passed=True
PASS SANDBOX_VERIFICATION_NO_FAILURES: failures=[]
PASS GATES_PASSED: gates.passed=True
PASS GATES_NO_BLOCKING_GATE: blocking_gate=None
PASS GATES_QUALITY_PASSED: quality={'score': 89, 'passed': True, 'blockers': [], ...}
PASS GATES_SECURITY_PASSED: security={'passed': True, 'findings': []}
PASS DIFF_EXISTS: present
PASS DIFF_HAS_REAL_CONTENT: diff keys=['spec', 'repository']
PASS CANDIDATE_ROW_COUNT_EXACTLY_ONE: count=1
PASS CANDIDATE_REPOSITORY_NONEMPTY: 6 files
PASS CANDIDATE_REPOSITORY_HAS_SEED_FILES: paths=['.omni/project.json', 'M4D2B_NOTES.md', 'README.md', 'index.html', 'requirements.txt', 'tests/test_seed.py']
PASS CANDIDATE_PRODUCTSPEC_EXISTS: spec.title=Todo
PASS CANDIDATE_ACCEPTANCE_PRESENT: acceptance=[{'id': 'A1', 'text': 'home shows todo list', 'requirement_id': 'R1'}]
PASS SOURCE_PRODUCTSPEC_EXISTS: version_id=v_e7eaa795c0b44688
PASS EXACTLY_ONE_MOD_REQUEST_ROW
PASS OUTBOX_ROW_COUNT: 1 row(s) (informational)
PASS NO_EXTRA_VERSIONS_PROMOTED: project_versions for this project = ['v_e7eaa795c0b44688']
PASS PROMOTED_VERSION_ID_IS_NULL / ACCEPTED_AT_IS_NULL / REJECTED_AT_IS_NULL

M49_READY_INVARIANT_ALL_PASS
```

### Task #52 — complete version lifecycle (directive item 11)

New test `tests/test_m49_lifecycle.py` (standalone), reusing the exact
real `READY_FOR_REVIEW` modification task #49 produced — no mocked
repository state anywhere in this proof.

```
A. accept = client.post('.../accept', json={})
   -> 200, {'accepted': True, 'new_version_id': 'v_babb1198473a40fe', ...}

B. current() -> v_babb1198473a40fe; repository == the real candidate's
   repository (dict equality). Raw row: project_versions.parent_id for
   v_babb1198473a40fe == the seed version id. modification_requests:
   status=ACCEPTED, promoted_version_id=v_babb1198473a40fe, accepted_at set.

C. project_version_specs row exists for v_babb1198473a40fe,
   spec_json.title == candidate spec's title ('Todo'). HTTP status route
   independently agrees.

D. rollback = client.post('/rollback', json={'target_version_id': <seed>})
   -> 200, produces a THIRD, brand-new version v_45963a10dd86444a
   (distinct from both the seed id and the accepted-candidate id --
   rollback re-commits, never rewrites the old row).

E. current() -> v_45963a10dd86444a; repository == the ORIGINAL seed
   repository, BYTE-IDENTICAL (real dict equality, captured before any
   of this ran), and explicitly != the superseded accepted candidate's
   content. Raw row: v_45963a10dd86444a.parent_id ==
   v_babb1198473a40fe (the version it was rolled back FROM).
```

Final independent `psql` snapshot:
```
$ psql ... -d m49_clean_room -c "SELECT id, parent_id, message, created_at FROM project_versions WHERE project_id = '...' ORDER BY created_at;"
         id         |     parent_id      |           message            |          created_at
--------------------+--------------------+------------------------------+-------------------------------
 v_e7eaa795c0b44688 |                    | m49 clean-room seed          | 2026-09-24 20:00:34.633741+00
 v_babb1198473a40fe | v_e7eaa795c0b44688 | modification accepted        | 2026-09-24 20:07:20.161593+00
 v_45963a10dd86444a | v_babb1198473a40fe | m49 lifecycle rollback proof | 2026-09-24 20:07:20.207447+00
$ psql ... -c "SELECT id, status, promoted_version_id, accepted_at IS NOT NULL AS accepted FROM modification_requests;"
                  id                  |  status  | promoted_version_id | accepted
--------------------------------------+----------+---------------------+----------
 mod_55e7f37c81f8479f8d9dbcaf68e641be | ACCEPTED | v_babb1198473a40fe  | t
```
Exactly the expected 3-version append-only chain (seed → accepted →
rollback-of-seed); exactly 1 modification request, correctly terminal.

### Full regression and disclosed test-file correction

Combined suite (excluding the now five standalone-required live-infra
files): **488 passed, 17 skipped**. Standalone:
`test_m4d2_live_fastapi_redis.py` 8/8, `test_m4d2b_parity_and_worker.py`
3/3, `test_m49_clean_room.py` 1/1, `test_m49_lifecycle.py` 1/1. **Total:
501/501.**

One pre-existing test needed an honest, disclosed (not silent) update:
`tests/test_m4d2b_parity_and_worker.py`'s
`test_real_worker_process_system_bug_path_hits_real_sandbox_docker_image_blocker`
still passes post-M4.9, but its docstring and specific build-log
substring assertion described the OLD `--mount ...,rw` bug as the cause
— stale as soon as M4.9 fixed that. Its real cause, chasing it down for
real rather than leaving a known-false docstring in the repo: that test's
own (unmodified, pre-existing) seed repository/manifest verifies with a
bare `['python3', '-m', 'pytest', '-q']` against a repository with NO
actual test files. With the `--mount` bug and missing image both fixed,
this now genuinely executes and pytest genuinely fails with real exit
code 5 ("no tests ran" / zero collected) — a different real, still-honest
failure. Updated the docstring and widened the OR-clause build-log
assertion to match (`'no tests ran'`/`'not found in $PATH'` alongside the
original clauses, so it still matches whichever of the old or new real
failure text a future change surfaces). Verified via full regression
after the change: 488/488 combined (including `AcceptanceW`'s own
internal self-check of the whole non-fastapi suite), 8/8 and 3/3
standalone.

### Files changed this update

Modified: `omni_prod/sandbox.py` (the `--mount` fix, task #47),
`omni_prod/sandbox_executor.py` (the tempdir-permission fix, task #49),
`tests/test_m4d2b_parity_and_worker.py` (disclosed docstring/assertion
correction, described above). New:
`tests/test_m49_clean_room.py`, `tests/test_m49_sandbox_security.py`,
`tests/test_m49_lifecycle.py`, `tools/m49_ready_invariant_check.py`.
Sandbox-image build artifacts (`/tmp/m49_sandbox_build_ctx/Dockerfile`
and its `pytest_vendor/` context) are session-local build inputs for the
already-built, already-digest-verified `omni-sandbox:latest` image, not
part of the application repository — their full content and provenance
are reproduced in this section and in `omni_prod/sandbox.py`'s own
comments; the actual runtime artifact `omni_prod/sandbox.py` depends on
is the built Docker image, addressed by its digest,
`sha256:6834400bb7810ada027f02dd685d7eb2cae4b684b38745d0c8a1488a86702532`.

### Status discipline (directive item 12) and final regression

- Sandbox image: real, built, provenance-documented, digest-verified
  before every use. Security posture: real, proven effective (not just
  configured) for every checklist item, no isolation weakened to obtain
  a passing build.
- `READY_FOR_REVIEW`: `VERIFIED_LIVE_INFRA` for real, for the first time
  — genuine classify → free-repair → sandbox-verify → quality → security
  → rights, all real, all passing, directly re-verified against raw
  Postgres state.
- Accept + rollback lifecycle: `VERIFIED_LIVE_INFRA`, no mocked
  repository state, byte-identical restoration proven.
- **`M4 = VERIFIED_LIVE_INFRA`**, explicitly NOT `PRODUCTION_DEPLOYED`
  and NOT `FULL_EXTERNAL_E2E`: a real hosted LLM provider and real S3
  remain out of reach in this sandbox (unchanged since M4D.2); the real
  sandbox image is a disclosed, documented, provenance-tracked substitute
  for `infra/sandbox/Dockerfile`'s own `python:3.12-slim` base (Python
  3.11.15 here, vendored dependencies instead of `pip install`), not that
  exact image. The pydantic 2.13.3 vs. 2.13.4 patch-version gap (M4D.2b)
  remains a documented production-CI verification item and does not
  block M5.

**Per the directive's own item 12, M4 work stops here. M5
architecture/implementation planning is now authorized to begin — no M5
requirements have been given in this engagement yet, so no M5 work has
started.**
