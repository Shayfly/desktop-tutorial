"""Negative controls for every /api/live/* route (#232 part B, decision of 2026-11-03).

The investor_app middleware exempts /api/live/ (line 98), so live_core's own
require_user is the only gate. These tests pin that gate route by route:

1. every protected route answers 401 with no token, a malformed header, an unknown
   token and a revoked token;
2. one user's token never reaches another user's projects, versions, builds,
   exports, restores or previews (404, never 200);
3. the protected-route list is pinned, so a new /api/live/* route without a
   matching entry here fails the suite instead of shipping untested.
"""

import io
import re
import zipfile

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from live_core.api import create_router
from live_core.store import MemoryStore

PUBLIC = {("POST", "/api/live/auth/register"), ("POST", "/api/live/auth/login")}

# Every protected /api/live/* route, with a body that would be valid if authenticated,
# so a 401 can only come from the auth gate and not from body validation.
PROTECTED = {
    ("POST", "/api/live/auth/logout"): None,
    ("GET", "/api/live/me"): None,
    ("GET", "/api/live/projects"): None,
    ("GET", "/api/live/projects/{project_id}/versions"): None,
    ("POST", "/api/live/builds"): {"prompt": "Build a small app"},
    ("POST", "/api/live/builds/{build_id}/run"): {"target_markets": []},
    ("GET", "/api/live/builds/{build_id}"): None,
    ("POST", "/api/live/projects/{project_id}/versions/{version_id}/restore"): None,
    ("GET", "/api/live/projects/{project_id}/versions/{version_id}/export"): None,
    ("POST", "/api/live/projects/{project_id}/versions/{version_id}/preview"): None,
}


def _router_live_routes():
    router = create_router(MemoryStore())
    found = set()
    for route in router.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api/live/"):
            for method in route.methods:
                found.add((method, route.path))
    return found


def _fill(path, **ids):
    return re.sub(r"\{(\w+)\}", lambda m: ids.get(m.group(1), "00000000-0000-0000-0000-000000000000"), path)


def _call(client, method, path, body, headers=None):
    return client.request(method, path, json=body, headers=headers or {})


def _zip(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return out.getvalue()


@pytest.fixture()
def world():
    store = MemoryStore()
    app = FastAPI()
    app.include_router(create_router(store))
    client = TestClient(app)

    def register(email):
        r = client.post("/api/live/auth/register", json={"email": email, "password": "Strong-password-123"})
        assert r.status_code == 200, r.text
        data = r.json()
        return data["user"]["id"], data["token"]

    alice_id, alice_token = register("alice-matrix@example.com")
    bob_id, bob_token = register("bob-matrix@example.com")
    project = store.create_project(alice_id, "Alice app")
    artifact = store.create_artifact(alice_id, project.id, "c" * 64, _zip({"index.html": "<h1>Alice</h1>"}))
    version = store.create_version(alice_id, project.id, artifact.id, "first")
    store.set_active_version(project.id, alice_id, version.id)
    build = store.create_build(alice_id, project.id, "Alice build")
    return {
        "client": client,
        "store": store,
        "alice": (alice_id, alice_token),
        "bob": (bob_id, bob_token),
        "ids": {"project_id": project.id, "version_id": version.id, "build_id": build.id},
    }


def test_protected_route_list_matches_the_router():
    # A new /api/live/* route must be added to PROTECTED or PUBLIC, or this fails.
    assert _router_live_routes() == set(PROTECTED) | PUBLIC


@pytest.mark.parametrize("method,path", sorted(PROTECTED))
@pytest.mark.parametrize(
    "case,headers",
    [
        ("no token", {}),
        ("not bearer", {"Authorization": "Basic abc"}),
        ("empty bearer", {"Authorization": "Bearer "}),
        ("unknown token", {"Authorization": "Bearer not-a-real-session-token"}),
    ],
)
def test_every_protected_route_rejects_missing_or_bad_tokens(world, method, path, case, headers):
    response = _call(world["client"], method, _fill(path, **world["ids"]), PROTECTED[(method, path)], headers)
    assert response.status_code == 401, (case, method, path, response.status_code, response.text)


@pytest.mark.parametrize("method,path", sorted(PROTECTED))
def test_every_protected_route_rejects_a_revoked_token(world, method, path):
    client = world["client"]
    _, token = world["bob"]
    out = client.post("/api/live/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert out.status_code == 200, out.text
    response = _call(client, method, _fill(path, **world["ids"]), PROTECTED[(method, path)],
                     {"Authorization": f"Bearer {token}"})
    assert response.status_code == 401, (method, path, response.status_code, response.text)


OWNER_SCOPED = [
    ("GET", "/api/live/projects/{project_id}/versions", None),
    ("POST", "/api/live/builds", {"prompt": "Change Alice app", "project_id": "{project_id}"}),
    ("POST", "/api/live/builds/{build_id}/run", {"target_markets": []}),
    ("GET", "/api/live/builds/{build_id}", None),
    ("POST", "/api/live/projects/{project_id}/versions/{version_id}/restore", None),
    ("GET", "/api/live/projects/{project_id}/versions/{version_id}/export", None),
    ("POST", "/api/live/projects/{project_id}/versions/{version_id}/preview", None),
]


def test_owner_scoped_list_covers_every_route_that_takes_another_users_id():
    takes_ids = {(m, p) for (m, p) in PROTECTED if "{" in p} | {("POST", "/api/live/builds")}
    assert {(m, p) for m, p, _ in OWNER_SCOPED} == takes_ids


@pytest.mark.parametrize("method,path,body", OWNER_SCOPED)
def test_another_users_token_never_reaches_alices_resources(world, method, path, body):
    ids = world["ids"]
    if body and body.get("project_id") == "{project_id}":
        body = {**body, "project_id": ids["project_id"]}
    _, bob_token = world["bob"]
    response = _call(world["client"], method, _fill(path, **ids), body, {"Authorization": f"Bearer {bob_token}"})
    assert response.status_code in (403, 404), (method, path, response.status_code, response.text)
    assert "Alice" not in response.text


def test_owner_still_reaches_her_own_resources(world):
    # Positive control: the isolation above is not just every route being broken.
    client, ids = world["client"], world["ids"]
    _, alice_token = world["alice"]
    headers = {"Authorization": f"Bearer {alice_token}"}
    assert client.get(f"/api/live/projects/{ids['project_id']}/versions", headers=headers).status_code == 200
    assert client.get(f"/api/live/builds/{ids['build_id']}", headers=headers).status_code == 200
    export = client.get(f"/api/live/projects/{ids['project_id']}/versions/{ids['version_id']}/export", headers=headers)
    assert export.status_code == 200 and export.content.startswith(b"PK")


def test_listings_do_not_leak_across_users(world):
    client = world["client"]
    _, alice_token = world["alice"]
    _, bob_token = world["bob"]
    alice = client.get("/api/live/projects", headers={"Authorization": f"Bearer {alice_token}"})
    bob = client.get("/api/live/projects", headers={"Authorization": f"Bearer {bob_token}"})
    assert [p["id"] for p in alice.json()["projects"]] == [world["ids"]["project_id"]]
    assert bob.json()["projects"] == []
    me = client.get("/api/live/me", headers={"Authorization": f"Bearer {bob_token}"})
    assert me.json()["id"] == world["bob"][0]


def test_bob_cannot_start_a_build_on_alices_project_and_no_build_is_created(world):
    client, store, ids = world["client"], world["store"], world["ids"]
    bob_id, bob_token = world["bob"]
    before = len(store.list_projects(world["alice"][0]))
    response = client.post("/api/live/builds", headers={"Authorization": f"Bearer {bob_token}"},
                           json={"prompt": "Take over Alice app", "project_id": ids["project_id"]})
    assert response.status_code == 404
    assert len(store.list_projects(world["alice"][0])) == before
    assert store.list_projects(bob_id) == []
