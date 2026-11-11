from fastapi import FastAPI
from fastapi.testclient import TestClient

from live_core.api import create_router
from live_core.security import hash_password, new_session_token, verify_password
from live_core.store import MemoryStore


def test_password_round_trip():
    encoded = hash_password("correct horse battery staple")
    assert encoded.startswith("scrypt$")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_session_stores_only_digest():
    token, digest = new_session_token()
    assert token != digest
    assert len(digest) == 64


def test_register_bearer_me_and_logout():
    store = MemoryStore()
    app = FastAPI()
    app.include_router(create_router(store))
    client = TestClient(app)

    registered = client.post(
        "/api/live/auth/register",
        json={"email": "Test@Example.com ", "password": "strong-password-123"},
    )
    assert registered.status_code == 200, registered.text
    payload = registered.json()
    assert payload["user"]["email"] == "test@example.com"
    token = payload["token"]

    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/live/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "test@example.com"

    logged_out = client.post("/api/live/auth/logout", headers=headers)
    assert logged_out.status_code == 200
    assert client.get("/api/live/me", headers=headers).status_code == 401


def test_login_reuses_durable_account():
    store = MemoryStore()
    app = FastAPI()
    app.include_router(create_router(store))
    client = TestClient(app)
    credentials = {"email": "person@example.com", "password": "strong-password-123"}

    assert client.post("/api/live/auth/register", json=credentials).status_code == 200
    login = client.post("/api/live/auth/login", json=credentials)
    assert login.status_code == 200, login.text
    assert login.json()["user"]["email"] == "person@example.com"
