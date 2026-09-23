import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from live_core.api import create_router
from live_core.service import CustomerService
from live_core.store import MemoryStore


def test_prompt_first_build_auto_creates_project():
    store = MemoryStore()
    user = store.create_user("owner@example.com", "hash")
    service = CustomerService(store)

    project = service.ensure_project(user.id, "  Build a Hebrew first-grade writing game  ")

    assert project.owner_id == user.id
    assert project.title == "Build a Hebrew first-grade writing game"
    assert store.get_project(project.id, user.id) is not None


def test_project_cannot_be_reused_by_another_owner():
    store = MemoryStore()
    alice = store.create_user("alice@example.com", "hash")
    bob = store.create_user("bob@example.com", "hash")
    service = CustomerService(store)
    project = service.ensure_project(alice.id, "Build Alice app")

    with pytest.raises(KeyError):
        service.ensure_project(bob.id, "Change Alice app", project.id)


def test_live_build_endpoint_starts_prompt_first_then_runs_as_separate_request():
    store = MemoryStore()
    app = FastAPI()
    app.include_router(create_router(store))
    client = TestClient(app)
    auth = client.post(
        "/api/live/auth/register",
        json={"email": "builder@example.com", "password": "strong-password-123"},
    ).json()
    headers = {"Authorization": f"Bearer {auth['token']}"}

    started = client.post(
        "/api/live/builds",
        headers=headers,
        json={"prompt": "Build a tiny Hebrew learning game"},
    )
    assert started.status_code == 200, started.text
    payload = started.json()
    assert payload["project_id"]
    assert payload["stage"] == "planning"
    assert payload["status"] == "queued"
    assert payload["version_id"] is None

    before_run = client.get(f"/api/live/builds/{payload['id']}", headers=headers)
    assert before_run.status_code == 200
    assert [event["stage"] for event in before_run.json()["events"]] == ["planning"]

    ran = client.post(
        f"/api/live/builds/{payload['id']}/run",
        headers=headers,
        json={"target_markets": ["IL"]},
    )
    assert ran.status_code == 200, ran.text
    result = ran.json()
    assert result["stage"] == "ready", result
    assert result["status"] == "ready"
    assert result["version_id"]

    projects = client.get("/api/live/projects", headers=headers)
    assert projects.status_code == 200
    assert len(projects.json()["projects"]) == 1
    assert projects.json()["projects"][0]["id"] == result["project_id"]
    assert projects.json()["projects"][0]["active_version_id"] == result["version_id"]
