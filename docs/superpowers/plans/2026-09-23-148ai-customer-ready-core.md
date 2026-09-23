# 148AI Customer-Ready Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the deployed 148AI site support a durable prompt-first customer flow that actually generates, runs, validates, previews, versions, restores and exports a deterministic/local product without requiring a live external AI model.

**Architecture:** Keep `omni_prod_runtime.zip` as the existing deterministic generation engine, but stop using its process-memory user/project state as the production source of truth. Add a small `live_core` layer in the repository for durable auth/project/build/version state, invoke the packaged runtime through a narrow adapter for generation, persist small pilot artifacts in PostgreSQL, execute supported generated web artifacts in a bounded temporary workspace, and expose a prompt-first UI with a persisted build timeline. The first customer-ready execution target is the current deterministic static/web output; unsupported generated project types must fail explicitly rather than pretending to be previewable.

**Tech Stack:** Python 3.12, FastAPI 0.128.2, psycopg 3.3.6 + psycopg_pool, Pydantic 2.13.4, PostgreSQL, vanilla browser JavaScript/CSS, pytest, FastAPI TestClient, existing packaged V28 runtime.

**Spec:** `docs/superpowers/specs/2026-09-23-148ai-customer-ready-core-design.md`

## Global Constraints

- No live external AI model is required in this milestone.
- The deterministic/local V28 generation path remains the generator for this milestone.
- Production must never silently fall back to process-memory persistence.
- Generated output must execute/validate before a build can be marked `ready`.
- Canonical visible stages are `planning`, `generating`, `running`, `testing`, `repairing`, `ready`, `failed`.
- English and Hebrew are the required complete customer locales; Hebrew is RTL.
- Existing V28 rights/integrations/company-OS capabilities remain available as advanced/fallback runtime routes where they still work.
- Small pilot build artifacts may be persisted as PostgreSQL `BYTEA` with an explicit 5 MiB cap; object storage is a later milestone.
- First live execution target is deterministic static/web output. Unsupported artifact shapes fail explicitly.

## Review Focus

1. A production process starts without `DATABASE_URL` — expected: startup/first live-core request fails closed with a clear configuration error, never memory fallback.
2. A user attempts to read/export/restore another user's project/version — expected: 404/403 without leaking ownership details.
3. A generated artifact contains path traversal entries (`../`) or exceeds the artifact cap — expected: build fails before extraction/persistence.
4. The generated web bundle contains invalid JavaScript or no usable entry point — expected: timeline reaches `failed`, never `ready`.
5. The browser refreshes during/after a build — expected: persisted build/version state reloads and the known terminal/current stage remains visible.

---

## File Structure

Create:
- `live_core/__init__.py` — package marker.
- `live_core/config.py` — environment and production fail-closed configuration.
- `live_core/security.py` — password hashing and opaque session tokens.
- `live_core/store.py` — domain records and store protocol.
- `live_core/postgres_store.py` — PostgreSQL implementation and schema bootstrap.
- `live_core/runtime_bridge.py` — narrow adapter around the packaged V28 runtime.
- `live_core/executor.py` — safe artifact extraction and bounded execution/validation.
- `live_core/service.py` — prompt-first orchestration, build timeline, version/restore/export rules.
- `live_core/api.py` — FastAPI routes for auth/projects/builds/preview/export.
- `tests/test_config.py`
- `tests/test_auth.py`
- `tests/test_projects.py`
- `tests/test_runtime_bridge.py`
- `tests/test_executor.py`
- `tests/test_build_flow.py`
- `tests/test_api_security.py`
- `tests/test_i18n_contract.py`

Modify:
- `app.py` — mount the new live-core routes before the legacy runtime passthrough and remove production memory defaulting.
- `ui/index.html` — prompt-first customer shell and build timeline markup.
- `ui/app.js` — auth, prompt-first auto-project flow, timeline, improve/restore/export and i18n.
- `ui/app.css` — timeline, RTL and responsive states.
- `.github/workflows/verify.yml` — run the new test suite and UI contract checks.
- `README.md` — document new live-core architecture and required deployment environment.

---

### Task 1: Production configuration and durable store boundary

**Files:**
- Create: `live_core/__init__.py`
- Create: `live_core/config.py`
- Create: `live_core/store.py`
- Create: `live_core/postgres_store.py`
- Create: `tests/test_config.py`
- Modify: `requirements.txt`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `Settings.from_env() -> Settings`
- Produces: `build_store(settings: Settings) -> Store`
- Produces: `Store` protocol methods used by later tasks.

- [ ] **Step 1: Write the fail-closed configuration test**

```python
# tests/test_config.py
import pytest
from live_core.config import Settings, ConfigurationError


def test_production_requires_database_url(monkeypatch):
    monkeypatch.setenv("OMNI_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        Settings.from_env()


def test_local_mode_allows_memory_store(monkeypatch):
    monkeypatch.setenv("OMNI_ENV", "development")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    s = Settings.from_env()
    assert s.persistence == "memory"
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `pytest tests/test_config.py -q`
Expected: import/module failure because `live_core.config` does not exist.

- [ ] **Step 3: Implement configuration and store protocol**

```python
# live_core/config.py
from dataclasses import dataclass
import os

class ConfigurationError(RuntimeError):
    pass

@dataclass(frozen=True)
class Settings:
    env: str
    database_url: str | None
    persistence: str
    artifact_limit_bytes: int = 5 * 1024 * 1024
    execution_timeout_seconds: int = 15

    @classmethod
    def from_env(cls):
        env = os.getenv("OMNI_ENV", "development").lower()
        db = os.getenv("DATABASE_URL")
        if env == "production" and not db:
            raise ConfigurationError("DATABASE_URL is required in production")
        return cls(env=env, database_url=db, persistence="postgres" if db else "memory")
```

Define `UserRecord`, `SessionRecord`, `ProjectRecord`, `VersionRecord`, `BuildRecord`, `ArtifactRecord` dataclasses and a `Store` protocol with create/get/update methods needed by Tasks 2-6. Implement a test-only/local `MemoryStore` in `store.py`; implement `PostgresStore` in `postgres_store.py` with `CREATE TABLE IF NOT EXISTS` schema for users, sessions, projects, versions, builds and artifacts.

- [ ] **Step 4: Add PostgreSQL schema ownership indexes and artifact cap field**

Use UUID primary keys, `owner_id` foreign keys, unique lower-cased email, hashed session token, immutable version rows, build stage/status, artifact SHA-256/size/bytes, and indexes on `(owner_id, project_id)` and `(project_id, created_at)`.

- [ ] **Step 5: Run configuration/store tests**

Run: `pytest tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add live_core tests/test_config.py requirements.txt pyproject.toml
git commit -m "feat: add fail-closed live persistence boundary"
```

---

### Task 2: Durable email/password auth and session ownership

**Files:**
- Create: `live_core/security.py`
- Create: `tests/test_auth.py`
- Modify: `live_core/store.py`
- Modify: `live_core/postgres_store.py`
- Create/Modify: `live_core/api.py`

**Interfaces:**
- Produces: `hash_password(password: str) -> str`
- Produces: `verify_password(password: str, encoded: str) -> bool`
- Produces: `new_session_token() -> tuple[str, str]` where first is bearer token and second is SHA-256 digest stored server-side.
- Produces routes: `POST /api/live/auth/register`, `POST /api/live/auth/login`, `POST /api/live/auth/logout`, `GET /api/live/me`.

- [ ] **Step 1: Write failing auth tests**

```python
# tests/test_auth.py
from live_core.security import hash_password, verify_password, new_session_token


def test_password_round_trip():
    encoded = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_session_stores_only_digest():
    token, digest = new_session_token()
    assert token != digest
    assert len(digest) == 64
```

Add API tests proving register→bearer→`/me` works and logout invalidates the session.

- [ ] **Step 2: Run tests and confirm failure**

Run: `pytest tests/test_auth.py -q`
Expected: missing module/functions/routes.

- [ ] **Step 3: Implement password/session primitives using stdlib**

Use `hashlib.scrypt` with a random 16-byte salt, encoded as `scrypt$<salt_b64>$<digest_b64>`. Use `secrets.token_urlsafe(32)` for bearer tokens and store only `sha256(token).hexdigest()`.

- [ ] **Step 4: Implement auth API with owner lookup**

Reject passwords under 10 characters, normalize email with `strip().lower()`, never return password hash/session digest, and use a shared dependency `require_user(request) -> UserRecord` for all protected live-core routes.

- [ ] **Step 5: Run auth tests**

Run: `pytest tests/test_auth.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add live_core tests/test_auth.py
git commit -m "feat: add durable account sessions"
```

---

### Task 3: Durable projects, versions and prompt-first project creation

**Files:**
- Create: `tests/test_projects.py`
- Modify: `live_core/store.py`
- Modify: `live_core/postgres_store.py`
- Modify: `live_core/api.py`
- Create: `live_core/service.py`

**Interfaces:**
- Produces: `CustomerService.ensure_project(owner_id, prompt, project_id=None) -> ProjectRecord`
- Produces: `POST /api/live/builds` accepting `{prompt, project_id?}`.
- Produces: `GET /api/live/projects` and `GET /api/live/projects/{project_id}/versions`.

- [ ] **Step 1: Write failing prompt-first test**

```python
def test_prompt_first_build_auto_creates_project(service, user):
    project = service.ensure_project(user.id, "Build a Hebrew first-grade writing game")
    assert project.owner_id == user.id
    assert project.title
```

Add an ownership test proving another user cannot load the project.

- [ ] **Step 2: Run tests and verify failure**

Run: `pytest tests/test_projects.py -q`
Expected: missing service/project behavior.

- [ ] **Step 3: Implement prompt-derived project title and ownership checks**

Use a deterministic title fallback: trim whitespace and take the first 56 visible characters of the prompt; never require a separate project-create click for the first build.

- [ ] **Step 4: Add immutable version and build record creation methods**

Every build attempt gets a unique `build_id`. Successful generated output creates a new immutable version; restore changes only the project's `active_version_id`.

- [ ] **Step 5: Run project tests**

Run: `pytest tests/test_projects.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add live_core tests/test_projects.py
git commit -m "feat: add prompt-first durable projects"
```

---

### Task 4: Narrow adapter to the existing deterministic V28 generator

**Files:**
- Create: `live_core/runtime_bridge.py`
- Create: `tests/test_runtime_bridge.py`
- Modify: `app.py`

**Interfaces:**
- Produces: `load_v28_runtime() -> ASGIApp`
- Produces: `runtime_request(method, path, json_body=None, headers=None) -> RuntimeResponse`
- Produces: `generate_export(prompt: str, title: str, target_markets: list[str]) -> bytes`

- [ ] **Step 1: Write a failing synthetic ASGI request test**

```python
def test_runtime_status_bridge(runtime_bridge):
    r = runtime_bridge.request("GET", "/api/status")
    assert r.status_code == 200
    assert r.json()["product"] == "148AI"
```

Add a contract test for the existing sequence used by the current UI: register temporary runtime account → create temporary runtime project → build → export. The test must assert the export starts with ZIP magic `b"PK"` and is non-empty.

- [ ] **Step 2: Run the bridge tests and capture exact runtime response shapes**

Run: `pytest tests/test_runtime_bridge.py -vv`
Expected initially: FAIL. Use the failure payloads to align the adapter to the packaged runtime rather than guessing field names.

- [ ] **Step 3: Refactor runtime loading out of `app.py`**

Move the existing lazy unzip/import logic into `live_core/runtime_bridge.py` without changing `omni_prod_runtime.zip`. `app.py` imports the shared loader for legacy passthrough and live-core generation.

- [ ] **Step 4: Implement `generate_export` as one same-instance runtime transaction**

Create a random temporary runtime account, create a runtime project, invoke `/api/v28/projects/{id}/build`, then fetch `/api/v28/projects/{id}/export` with the returned bearer token. Keep this runtime identity internal; the customer's durable account is owned by live-core and is never copied into runtime memory.

- [ ] **Step 5: Verify the real packaged generator contract**

Run: `pytest tests/test_runtime_bridge.py -vv`
Expected: PASS, including ZIP export contract.

- [ ] **Step 6: Commit**

```bash
git add app.py live_core/runtime_bridge.py tests/test_runtime_bridge.py
git commit -m "feat: bridge deterministic V28 generation"
```

---

### Task 5: Isolated artifact validation, execution and persisted build timeline

**Files:**
- Create: `live_core/executor.py`
- Create: `tests/test_executor.py`
- Create: `tests/test_build_flow.py`
- Modify: `live_core/service.py`
- Modify: `live_core/store.py`
- Modify: `live_core/postgres_store.py`

**Interfaces:**
- Produces: `validate_zip(blob: bytes, max_bytes: int) -> ArtifactManifest`
- Produces: `execute_web_artifact(blob: bytes, timeout_seconds: int) -> ExecutionResult`
- Produces: `CustomerService.build(owner_id, prompt, project_id=None) -> BuildRecord`

- [ ] **Step 1: Write malicious/archive validation tests**

```python
import io, zipfile, pytest
from live_core.executor import validate_zip, UnsafeArtifact


def zip_bytes(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, body in files.items():
            z.writestr(name, body)
    return out.getvalue()


def test_rejects_path_traversal():
    blob = zip_bytes({"../escape.txt": "no"})
    with pytest.raises(UnsafeArtifact):
        validate_zip(blob, 5 * 1024 * 1024)


def test_requires_web_entrypoint():
    blob = zip_bytes({"README.txt": "no app"})
    with pytest.raises(UnsafeArtifact, match="index.html"):
        validate_zip(blob, 5 * 1024 * 1024)
```

- [ ] **Step 2: Write stage persistence test**

```python
def test_successful_build_records_stage_progression(service, user, fake_generator, fake_executor):
    b = service.build(user.id, "Build a tiny web game")
    assert b.stage == "ready"
    assert service.store.get_build_events(b.id) == [
        "planning", "generating", "running", "testing", "ready"
    ]
```

Add a failure test where executor returns non-zero/invalid JS and assert terminal stage is `failed`, no active version is promoted, and customer-safe error text exists.

- [ ] **Step 3: Implement ZIP safety and bounded execution**

Use `tempfile.TemporaryDirectory()`. Reject absolute paths, `..`, symlinks and files outside the extracted root. Require `index.html` for the first supported customer path. Run JavaScript syntax checks only through an allowlisted command `node --check <file>` when JS files exist; hard timeout from settings. If `node` is unavailable in the runtime, return explicit execution capability failure instead of marking ready. Also parse/serve `index.html` and require a successful local file/static smoke before ready.

- [ ] **Step 4: Implement persisted build events**

Before each boundary call `store.append_build_event(build_id, stage, safe_message)`. The browser reads the persisted event list; it is not reconstructed from frontend state.

- [ ] **Step 5: Persist successful artifact/version only after execution**

Compute SHA-256, enforce 5 MiB cap, store artifact bytes, create immutable version, then set project `active_version_id`; never promote a failed artifact.

- [ ] **Step 6: Run executor/build tests**

Run: `pytest tests/test_executor.py tests/test_build_flow.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add live_core tests/test_executor.py tests/test_build_flow.py
git commit -m "feat: execute builds and persist build timeline"
```

---

### Task 6: Preview, restore and authenticated export

**Files:**
- Create: `tests/test_api_security.py`
- Modify: `live_core/api.py`
- Modify: `live_core/service.py`

**Interfaces:**
- Produces: `GET /api/live/builds/{build_id}` with persisted events.
- Produces: `POST /api/live/projects/{project_id}/versions/{version_id}/restore`.
- Produces: `GET /api/live/projects/{project_id}/versions/{version_id}/export`.
- Produces: `POST /api/live/projects/{project_id}/versions/{version_id}/preview` returning a high-entropy preview URL/handle.
- Produces: `GET /preview/live/{preview_id}/{path:path}` for generated static assets.

- [ ] **Step 1: Write cross-user security tests**

```python
def test_other_user_cannot_export(client, alice_headers, bob_headers, alice_project):
    r = client.get(
        f"/api/live/projects/{alice_project.id}/versions/{alice_project.active_version_id}/export",
        headers=bob_headers,
    )
    assert r.status_code in (403, 404)
```

Add equivalent restore and preview-creation tests.

- [ ] **Step 2: Write restore-history test**

Create two versions, restore version 1, assert both rows still exist and only `active_version_id` changes.

- [ ] **Step 3: Implement authenticated blob export**

Return `application/zip` with `Content-Disposition: attachment; filename="148AI-<project-id>.zip"`. Verify user owns both project and version.

- [ ] **Step 4: Implement preview serving from persisted ZIP**

Generate a random 256-bit preview handle linked to owner/project/version. Extract requested relative asset from the verified ZIP without writing arbitrary paths. Serve correct content types and default `/` to `index.html`. Preview handles contain no 148AI credentials.

- [ ] **Step 5: Run API security tests**

Run: `pytest tests/test_api_security.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add live_core tests/test_api_security.py
git commit -m "feat: secure preview restore and export"
```

---

### Task 7: Prompt-first customer UI, real Hebrew and visible timeline

**Files:**
- Modify: `ui/index.html`
- Modify: `ui/app.js`
- Modify: `ui/app.css`
- Create: `tests/test_i18n_contract.py`

**Interfaces:**
- Consumes `/api/live/*` from Tasks 2-6.
- Customer actions: build from one prompt, refresh timeline, preview, improve same project, versions/restore, export.

- [ ] **Step 1: Write i18n contract test before UI changes**

```python
# tests/test_i18n_contract.py
import re
from pathlib import Path


def test_primary_ui_has_english_and_hebrew_dictionary():
    js = Path("ui/app.js").read_text("utf-8")
    for key in ["headline", "promptPlaceholder", "build", "planning", "generating", "running", "testing", "repairing", "ready", "failed", "preview", "export"]:
        assert re.search(rf"\b{key}\b", js), key
    assert "document.documentElement.dir" in js
```

- [ ] **Step 2: Replace manual project-first main flow**

Primary logged-in layout contains one large prompt and one Build button. Existing project list becomes recent-project navigation. Product-type chips move under Advanced and do not block Build.

- [ ] **Step 3: Change Build to one prompt-first request**

`build()` posts `{prompt, project_id: selectedProjectId || null}` to `/api/live/builds`. It renders the returned build ID immediately and polls `/api/live/builds/{id}` until `ready` or `failed` with bounded polling/backoff.

- [ ] **Step 4: Render persisted timeline**

Map stage keys to localized labels and mark completed/current/failed states. On page load, if the active project has a latest build, fetch and render its persisted stage/events.

- [ ] **Step 5: Implement real EN/HE dictionary and persisted locale**

Keep a single `I18N` object with matching English/Hebrew keys, save locale in `localStorage`, set `lang` and `dir`, and update every primary visible label/placeholder/button. Hebrew uses `dir="rtl"` and CSS logical properties where needed.

- [ ] **Step 6: Fix export to authenticated fetch/blob**

```javascript
async function exportVersion(projectId, versionId) {
  const r = await fetch(`/api/live/projects/${projectId}/versions/${versionId}/export`, {headers: auth()});
  if (!r.ok) throw new Error(`Export failed (${r.status})`);
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = '148AI-project.zip'; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
```

- [ ] **Step 7: Run browser syntax + i18n tests**

Run: `node --check ui/app.js && pytest tests/test_i18n_contract.py -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add ui tests/test_i18n_contract.py
git commit -m "feat: ship prompt-first customer workspace"
```

---

### Task 8: Mount live-core API and preserve legacy advanced routes

**Files:**
- Modify: `app.py`
- Modify: `README.md`
- Modify: `vercel.json` only if runtime duration/config must change after measured build timing.

**Interfaces:**
- `app.py` serves UI and mounts live-core routes before `/{path:path}` runtime fallback.
- Legacy `/api/v28/*` remains reachable only for advanced/runtime capabilities still used by the UI or diagnostics.

- [ ] **Step 1: Add bootstrap integration test**

Assert `/`, `/_148ai/health`, `/api/live/*` and `/api/status` all route to the intended layer without catch-all shadowing.

- [ ] **Step 2: Remove unconditional production memory default**

Delete `os.environ.setdefault("OMNI_CREATOR_PERSISTENCE", "memory")` from the production bootstrap path. Local test/runtime compatibility can set memory explicitly inside runtime bridge calls where required.

- [ ] **Step 3: Mount live-core router before catch-all**

Create `settings = Settings.from_env()` lazily for live-core so health can still report a clear config problem. In production, protected customer routes fail closed if durable config is absent.

- [ ] **Step 4: Update README deployment requirements**

Document `DATABASE_URL`, artifact cap, deterministic/no-live-model policy, supported first execution target, and the difference between `api/live` customer state and legacy V28 advanced runtime routes.

- [ ] **Step 5: Run bootstrap tests**

Run: `pytest -q`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app.py README.md vercel.json tests
git commit -m "feat: mount customer-ready live core"
```

---

### Task 9: CI gate and deployed E2E acceptance

**Files:**
- Modify: `.github/workflows/verify.yml`
- Create: `tests/test_e2e_contract.py`

**Interfaces:**
- CI validates runtime ZIP integrity, Python/JS syntax, all live-core unit/integration tests, and the deterministic prompt-first flow.

- [ ] **Step 1: Add local end-to-end contract test**

The test must execute:
`register → build(prompt, no project id) → persisted stages → ready → preview creation → second build on same project → two versions → restore first → export → logout/login → same project/version history`.

Use the real packaged runtime adapter for generation when practical in CI; if runtime build duration makes that unsuitable for every unit run, keep one dedicated integration test and fake only the generator in fast unit tests.

- [ ] **Step 2: Extend GitHub Actions**

Run `pytest -q`, `python -m py_compile app.py live_core/*.py`, `node --check ui/app.js`, existing runtime ZIP integrity checks, and the bootstrap customer UI smoke.

- [ ] **Step 3: Verify CI on the repair branch/PR**

Expected: all required checks green. Do not promote on skipped core tests.

- [ ] **Step 4: Deploy a Vercel preview with durable DB configuration**

Required environment: `OMNI_ENV=production`, `DATABASE_URL=<connected PostgreSQL URL>`. This is the point where an external database connection is mandatory; if Vercel access or DB credentials are unavailable, stop and request only that external authorization/configuration step.

- [ ] **Step 5: Run deployed acceptance manually/API-driven**

Verify from the live preview URL: register/login, Hebrew switch, prompt-first build, visible stage progression, interactive preview, follow-up change, version history, restore, authenticated ZIP export, refresh, logout/login persistence.

- [ ] **Step 6: Verify runtime logs**

Confirm no 401 immediately after successful auth, no silent memory fallback, no secrets in build logs, and no core 5xx errors during the acceptance sequence.

- [ ] **Step 7: Final verification commit/PR note**

Record exact CI run, deployed preview URL and acceptance result in the PR. Only after this evidence exists may the branch be considered ready to merge/promote.

---

## Self-Review

- Spec coverage: durable auth/state, prompt-first flow, deterministic generation, actual run/test gate, visible persisted timeline, preview, change/version/restore, authenticated export, EN/HE RTL and deployed E2E are each mapped to a task.
- Explicitly deferred: live external models/router, Redis workers, object storage, full OAuth/email lifecycle, media engines, signed mobile/store publishing and enterprise billing.
- No core task depends on those deferred systems.
- Review-focus cases are exercised by Tasks 1, 5, 6 and 7.
- Type/interface names are consistent across tasks: `Settings`, `Store`, `CustomerService`, `BuildRecord`, `RuntimeBridge`/runtime request functions, artifact executor and `/api/live` routes.
