from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import os
from pathlib import Path
import secrets
import shutil
import sys
from threading import Lock
from urllib.parse import urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ZIP = ROOT / "omni_prod_runtime.zip"
RUNTIME_DIR = Path("/tmp/148ai_v28_runtime_shared")
_lock = Lock()
_loaded_app = None
_load_error: tuple[str, str] | None = None


class RuntimeBridgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.content.decode("utf-8"))


def get_runtime_load_error() -> tuple[str, str] | None:
    return _load_error


def load_v28_runtime():
    global _loaded_app, _load_error
    if _loaded_app is not None:
        return _loaded_app
    with _lock:
        if _loaded_app is not None:
            return _loaded_app
        try:
            if not RUNTIME_ZIP.is_file():
                raise FileNotFoundError("omni_prod_runtime.zip is missing")
            stamp = f"{RUNTIME_ZIP.stat().st_size}:{RUNTIME_ZIP.stat().st_mtime_ns}"
            marker = RUNTIME_DIR / ".ready"
            if not marker.exists() or marker.read_text(encoding="utf-8", errors="ignore") != stamp:
                if RUNTIME_DIR.exists():
                    shutil.rmtree(RUNTIME_DIR)
                RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(RUNTIME_ZIP, "r") as archive:
                    bad = archive.testzip()
                    if bad:
                        raise zipfile.BadZipFile(f"CRC failure: {bad}")
                    archive.extractall(RUNTIME_DIR)
                marker.write_text(stamp, encoding="utf-8")
            if str(RUNTIME_DIR) not in sys.path:
                sys.path.insert(0, str(RUNTIME_DIR))
            os.environ.setdefault("OMNI_CREATOR_PERSISTENCE", "memory")
            from omni_prod.investor_app import app as runtime_app

            _loaded_app = runtime_app
            _load_error = None
            return runtime_app
        except Exception as exc:
            _load_error = (type(exc).__name__, str(exc))
            raise RuntimeBridgeError(f"V28 runtime failed to load: {type(exc).__name__}: {exc}") from exc


async def _runtime_request_async(
    method: str,
    path: str,
    json_body=None,
    headers: dict[str, str] | None = None,
) -> RuntimeResponse:
    runtime = load_v28_runtime()
    parsed = urlsplit(path)
    body = b"" if json_body is None else json.dumps(json_body, separators=(",", ":")).encode("utf-8")
    header_map = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    if json_body is not None:
        header_map.setdefault("content-type", "application/json")
    header_map.setdefault("host", "148ai-runtime.local")
    raw_headers = [(key.encode("latin-1"), value.encode("latin-1")) for key, value in header_map.items()]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": parsed.path or "/",
        "raw_path": (parsed.path or "/").encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "root_path": "",
        "headers": raw_headers,
        "client": ("127.0.0.1", 14800),
        "server": ("148ai-runtime.local", 80),
    }
    request_sent = False
    started: dict = {}
    chunks: list[bytes] = []

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            started.update(message)
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    await runtime(scope, receive, send)
    response_headers: dict[str, str] = {}
    for key, value in started.get("headers", []):
        response_headers[key.decode("latin-1").lower()] = value.decode("latin-1")
    return RuntimeResponse(started.get("status", 500), response_headers, b"".join(chunks))


def runtime_request(method: str, path: str, json_body=None, headers: dict[str, str] | None = None) -> RuntimeResponse:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_runtime_request_async(method, path, json_body=json_body, headers=headers))
    raise RuntimeBridgeError("runtime_request cannot run inside an active event loop")


def _require_ok(response: RuntimeResponse, action: str) -> RuntimeResponse:
    if 200 <= response.status_code < 300:
        return response
    raise RuntimeBridgeError(f"{action} failed ({response.status_code}): {response.text[:800]}")


def generate_export(prompt: str, title: str, target_markets: list[str]) -> bytes:
    suffix = secrets.token_hex(10)
    credentials = {
        "email": f"runtime-{suffix}@148ai.local",
        "password": f"Runtime-{suffix}-Strong-Pass!",
    }
    registered = _require_ok(
        runtime_request("POST", "/api/v28/auth/register", json_body=credentials),
        "runtime registration",
    ).json()
    token = registered.get("token")
    if not token:
        raise RuntimeBridgeError("runtime registration returned no token")
    auth = {"authorization": f"Bearer {token}"}

    project_payload = _require_ok(
        runtime_request("POST", "/api/v28/projects", json_body={"title": title}, headers=auth),
        "runtime project creation",
    ).json()
    project_id = project_payload.get("id")
    if not project_id:
        raise RuntimeBridgeError(f"runtime project creation returned no id: {project_payload!r}")

    _require_ok(
        runtime_request(
            "POST",
            f"/api/v28/projects/{project_id}/build",
            json_body={"prompt": prompt, "target_markets": target_markets},
            headers=auth,
        ),
        "runtime build",
    )
    exported = _require_ok(
        runtime_request("GET", f"/api/v28/projects/{project_id}/export", headers=auth),
        "runtime export",
    )
    if not exported.content.startswith(b"PK"):
        raise RuntimeBridgeError(f"runtime export is not a ZIP: {exported.text[:300]}")
    return exported.content
