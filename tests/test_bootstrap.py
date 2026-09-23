import importlib
import sys

from fastapi.testclient import TestClient


def import_app(monkeypatch, *, env="development", database_url=None):
    monkeypatch.setenv("OMNI_ENV", env)
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def test_bootstrap_mounts_live_core_before_legacy_runtime(monkeypatch):
    module = import_app(monkeypatch)
    client = TestClient(module.app)

    home = client.get("/")
    assert home.status_code == 200
    assert 'id="timeline"' in home.text
    assert '/ui/live-runner.js' in home.text

    runner = client.get("/ui/live-runner.js")
    assert runner.status_code == 200
    assert "runPromptFirstBuild" in runner.text

    registered = client.post(
        "/api/live/auth/register",
        json={"email": "bootstrap@example.com", "password": "Strong-password-123"},
    )
    assert registered.status_code == 200, registered.text
    assert registered.json()["token"]

    legacy = client.get("/api/status")
    assert legacy.status_code == 200, legacy.text
    assert legacy.json()["product"] == "148AI"

    health = client.get("/_148ai/health")
    assert health.status_code == 200
    assert health.json()["live_core"]["configured"] is True
    assert health.json()["live_core"]["persistence"] == "memory"


def test_production_without_database_keeps_health_but_live_api_fails_closed(monkeypatch):
    module = import_app(monkeypatch, env="production")
    client = TestClient(module.app)

    health = client.get("/_148ai/health")
    assert health.status_code == 200
    assert health.json()["live_core"]["configured"] is False
    assert "DATABASE_URL" in health.json()["live_core"]["error"]

    blocked = client.post(
        "/api/live/auth/register",
        json={"email": "blocked@example.com", "password": "Strong-password-123"},
    )
    assert blocked.status_code == 503
    assert "DATABASE_URL" in blocked.json()["detail"]

    legacy = client.get("/api/status")
    assert legacy.status_code == 200
    assert legacy.json()["product"] == "148AI"
