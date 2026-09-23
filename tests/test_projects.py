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


def test_live_build_endpoint_auto_creates_project_for_authenticated_user():
    store = MemoryStore()
    app = FastAPI()
    app.include_router(create_router(store))
    client = TestClient(app)
    auth = client.post(
        "/api/live/auth/register",
        json={"email": "builder@example.com", "password": "strong-password-123"},
    ).json()
    headers = {"Authorization": f"Bearer {auth['token']}"}

    created = client.post(
        "/api/live/builds",
        headers=headers,
        json={"prompt": "Build a tiny Hebrew learning game"},
    )
    assert created.status_code == 200, created.text
    payload = created.json()
    assert payload["project_id"]
    assert payload["stage"] == "planning"

    projects = client.get("/api/live/projects", headers=headers)
    assert projects.status_code == 200
    assert len(projects.json()["projects"]) == 1
    assert projects.json()["projects"][0]["id"] == payload["project_id"]
