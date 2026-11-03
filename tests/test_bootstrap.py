"""Decision #232 (B2): live_core is installed into investor_app, which stays in place."""

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
