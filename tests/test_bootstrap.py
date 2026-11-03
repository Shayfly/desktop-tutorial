"""Decision #232 (B2): live_core is installed into investor_app, which stays in place."""

import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app import app
from omni_prod import investor_app


def _paths():
    return {getattr(route, "path", None) for route in app.routes}


def test_app_is_still_the_investor_app_object():
    assert app is investor_app.app


def test_investor_app_routes_are_still_present():
    paths = _paths()
    for path in ("/", "/api/status", "/api/v28/me", "/api/v28/projects", "/api/live/build"):
        assert path in paths, path


def test_live_core_routes_are_installed():
    paths = _paths()
    for path in (
        "/api/live/auth/register",
        "/api/live/auth/login",
        "/api/live/builds",
        "/api/live/builds/{build_id}/run",
        "/api/live/projects/{project_id}/versions/{version_id}/preview",
        "/preview/live/{preview_id}/",
    ):
        assert path in paths, path


def test_no_duplicate_method_and_path():
    seen = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        for method in sorted(getattr(route, "methods", None) or {"WS"}):
            key = (method, path)
            assert key not in seen, key
            seen.add(key)


def test_live_paths_are_exempt_from_investor_auth_in_production(monkeypatch):
    # production_auth reads OMNI_ENV per request, so this exercises the real middleware.
    monkeypatch.setenv("OMNI_ENV", "production")
    client = TestClient(app)
    response = client.post("/api/live/auth/register")
    # 422 = the request reached live_core's own validation; 401 would mean investor auth blocked it.
    assert response.status_code == 422, response.text


def test_other_api_paths_stay_protected_in_production(monkeypatch):
    monkeypatch.setenv("OMNI_ENV", "production")
    client = TestClient(app)
    response = client.get("/api/v28/me")
    assert response.status_code == 401
    # The middleware's own body, not the handler's: line 101 still guards non-live paths.
    assert response.json() == {"detail": "authentication required"}


def test_ui_live_runner_is_served():
    client = TestClient(app)
    response = client.get("/ui/live-runner.js")
    assert response.status_code == 200
    assert "runPromptFirstBuild" in response.text


_ROOT = Path(__file__).resolve().parents[1]
_NO_DB_PROBE = r"""
import json
from fastapi.testclient import TestClient
from app import app
paths = sorted({getattr(r, "path", "") for r in app.routes})
client = TestClient(app)
live = client.post("/api/live/auth/login", json={"email": "probe@example.com", "password": "not-a-real-pass"})
status_ = client.get("/api/status")
print(json.dumps({
    "live_paths": [p for p in paths if p.startswith(("/api/live/", "/preview/live/"))],
    "live_status": live.status_code,
    "live_detail": live.json().get("detail", ""),
    "api_status": status_.status_code,
}))
"""


def _run_without_database():
    env = {k: v for k, v in os.environ.items()
           if k not in ("OMNI_DATABASE_URL", "DATABASE_URL", "OMNI_LIVE_PERSISTENCE", "OMNI_ENV")}
    done = subprocess.run([sys.executable, "-c", _NO_DB_PROBE], cwd=_ROOT, env=env,
                          capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_app_imports_without_any_database_configuration_and_live_routes_are_registered():
    # #232 decision (ג): registration happens at import, the store does not.
    result = _run_without_database()
    for path in ("/api/live/auth/register", "/api/live/me", "/api/live/builds", "/preview/live/{preview_id}/"):
        assert path in result["live_paths"], path


def test_missing_database_fails_the_live_request_explicitly_not_the_boot():
    result = _run_without_database()
    assert result["live_status"] == 503, result
    assert "OMNI_DATABASE_URL" in result["live_detail"], result
    # The rest of the app keeps serving.
    assert result["api_status"] == 200, result
