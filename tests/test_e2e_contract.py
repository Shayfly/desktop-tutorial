from fastapi import FastAPI
from fastapi.testclient import TestClient

from live_core.api import create_router
from live_core.store import MemoryStore


def test_customer_ready_flow_end_to_end_with_real_deterministic_runtime():
    store = MemoryStore()
    app = FastAPI()
    app.include_router(create_router(store))
    client = TestClient(app)

    email = "customer-e2e@example.com"
    password = "Strong-password-123"

    registered = client.post(
        "/api/live/auth/register",
        json={"email": email, "password": password},
    )
    assert registered.status_code == 200, registered.text
    first_token = registered.json()["token"]
    headers = {"Authorization": f"Bearer {first_token}"}

    first = client.post(
        "/api/live/builds",
        headers=headers,
        json={
            "prompt": "Build a small Hebrew first-grade writing practice web game with levels and stars",
            "target_markets": ["IL"],
        },
    )
    assert first.status_code == 200, first.text
    first_build = first.json()
    assert first_build["stage"] == "ready", first_build
    assert first_build["status"] == "ready"
    assert first_build["project_id"]
    assert first_build["version_id"]
    project_id = first_build["project_id"]
    first_version = first_build["version_id"]

    timeline = client.get(f"/api/live/builds/{first_build['id']}", headers=headers)
    assert timeline.status_code == 200, timeline.text
    stages = [event["stage"] for event in timeline.json()["events"]]
    assert stages[0] == "planning"
    assert "generating" in stages
    assert "running" in stages
    assert "testing" in stages
    assert stages[-1] == "ready"

    preview_create = client.post(
        f"/api/live/projects/{project_id}/versions/{first_version}/preview",
        headers=headers,
    )
    assert preview_create.status_code == 200, preview_create.text
    preview = client.get(preview_create.json()["url"])
    assert preview.status_code == 200, preview.text
    assert preview.headers["content-type"].startswith("text/html")
    assert preview.content.strip()

    second = client.post(
        "/api/live/builds",
        headers=headers,
        json={
            "project_id": project_id,
            "prompt": "Improve the same product by adding another learning level and clearer rewards",
            "target_markets": ["IL"],
        },
    )
    assert second.status_code == 200, second.text
    second_build = second.json()
    assert second_build["stage"] == "ready", second_build
    assert second_build["project_id"] == project_id
    assert second_build["version_id"] != first_version
    second_version = second_build["version_id"]

    history = client.get(f"/api/live/projects/{project_id}/versions", headers=headers)
    assert history.status_code == 200, history.text
    versions = history.json()["versions"]
    assert [version["id"] for version in versions] == [first_version, second_version]

    restored = client.post(
        f"/api/live/projects/{project_id}/versions/{first_version}/restore",
        headers=headers,
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["active_version_id"] == first_version

    exported = client.get(
        f"/api/live/projects/{project_id}/versions/{first_version}/export",
        headers=headers,
    )
    assert exported.status_code == 200, exported.text
    assert exported.content.startswith(b"PK")

    logged_out = client.post("/api/live/auth/logout", headers=headers)
    assert logged_out.status_code == 200
    rejected = client.get("/api/live/projects", headers=headers)
    assert rejected.status_code == 401

    login = client.post(
        "/api/live/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    second_headers = {"Authorization": f"Bearer {login.json()['token']}"}

    projects_after_login = client.get("/api/live/projects", headers=second_headers)
    assert projects_after_login.status_code == 200
    projects = projects_after_login.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["id"] == project_id
    assert projects[0]["active_version_id"] == first_version

    history_after_login = client.get(
        f"/api/live/projects/{project_id}/versions",
        headers=second_headers,
    )
    assert history_after_login.status_code == 200
    assert len(history_after_login.json()["versions"]) == 2

    export_after_login = client.get(
        f"/api/live/projects/{project_id}/versions/{first_version}/export",
        headers=second_headers,
    )
    assert export_after_login.status_code == 200
    assert export_after_login.content.startswith(b"PK")
