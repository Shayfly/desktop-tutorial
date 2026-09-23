import io
import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient

from live_core.api import create_router
from live_core.store import MemoryStore


def zip_bytes(files: dict[str, str]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items():
            z.writestr(name, body)
    return out.getvalue()


def make_client():
    store = MemoryStore()
    app = FastAPI()
    app.include_router(create_router(store))
    return TestClient(app), store


def register(client: TestClient, email: str):
    r = client.post("/api/live/auth/register", json={"email": email, "password": "Strong-password-123"})
    assert r.status_code == 200, r.text
    data = r.json()
    return data["user"], {"Authorization": f"Bearer {data['token']}"}


def seeded_project(store: MemoryStore, owner_id: str):
    project = store.create_project(owner_id, "Secure app")
    blob1 = zip_bytes({"index.html": "<h1>Version one</h1>", "app.js": "const v=1;"})
    artifact1 = store.create_artifact(owner_id, project.id, "a" * 64, blob1)
    version1 = store.create_version(owner_id, project.id, artifact1.id, "first")
    store.set_active_version(project.id, owner_id, version1.id)

    blob2 = zip_bytes({"index.html": "<h1>Version two</h1>", "app.js": "const v=2;"})
    artifact2 = store.create_artifact(owner_id, project.id, "b" * 64, blob2)
    version2 = store.create_version(owner_id, project.id, artifact2.id, "second", parent_version_id=version1.id)
    store.set_active_version(project.id, owner_id, version2.id)
    return project, version1, version2


def test_other_user_cannot_export_restore_or_create_preview():
    client, store = make_client()
    alice, alice_headers = register(client, "alice@example.com")
    _, bob_headers = register(client, "bob@example.com")
    project, version1, _ = seeded_project(store, alice["id"])

    export = client.get(
        f"/api/live/projects/{project.id}/versions/{version1.id}/export",
        headers=bob_headers,
    )
    restore = client.post(
        f"/api/live/projects/{project.id}/versions/{version1.id}/restore",
        headers=bob_headers,
    )
    preview = client.post(
        f"/api/live/projects/{project.id}/versions/{version1.id}/preview",
        headers=bob_headers,
    )
    assert export.status_code in (403, 404)
    assert restore.status_code in (403, 404)
    assert preview.status_code in (403, 404)

    owner_export = client.get(
        f"/api/live/projects/{project.id}/versions/{version1.id}/export",
        headers=alice_headers,
    )
    assert owner_export.status_code == 200
    assert owner_export.content.startswith(b"PK")
    assert owner_export.headers["content-type"].startswith("application/zip")


def test_restore_preserves_history_and_only_changes_active_version():
    client, store = make_client()
    alice, headers = register(client, "restore@example.com")
    project, version1, version2 = seeded_project(store, alice["id"])

    r = client.post(
        f"/api/live/projects/{project.id}/versions/{version1.id}/restore",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["active_version_id"] == version1.id
    versions = store.list_versions(project.id, alice["id"])
    assert [v.id for v in versions] == [version1.id, version2.id]


def test_preview_handle_serves_verified_version_without_bearer_token():
    client, store = make_client()
    alice, headers = register(client, "preview@example.com")
    project, version1, _ = seeded_project(store, alice["id"])

    created = client.post(
        f"/api/live/projects/{project.id}/versions/{version1.id}/preview",
        headers=headers,
    )
    assert created.status_code == 200, created.text
    preview_url = created.json()["url"]
    assert preview_url.startswith("/preview/live/")

    rendered = client.get(preview_url)
    assert rendered.status_code == 200, rendered.text
    assert "Version one" in rendered.text
    assert rendered.headers["content-type"].startswith("text/html")


def test_build_status_includes_persisted_events_and_is_owner_scoped():
    client, store = make_client()
    alice, alice_headers = register(client, "events@example.com")
    _, bob_headers = register(client, "events-bob@example.com")
    project = store.create_project(alice["id"], "Events")
    build = store.create_build(alice["id"], project.id, "Build it")
    store.append_build_event(build.id, "planning", "Planning")
    store.append_build_event(build.id, "generating", "Generating")

    own = client.get(f"/api/live/builds/{build.id}", headers=alice_headers)
    other = client.get(f"/api/live/builds/{build.id}", headers=bob_headers)
    assert own.status_code == 200
    assert [event["stage"] for event in own.json()["events"]] == ["planning", "generating"]
    assert other.status_code in (403, 404)
