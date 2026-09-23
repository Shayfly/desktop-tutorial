from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from live_core.api import create_router
from live_core.config import ConfigurationError, Settings, build_store
from live_core.runtime_bridge import RUNTIME_ZIP, get_runtime_load_error, load_v28_runtime

ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"

bootstrap = FastAPI(title="148AI", docs_url=None, redoc_url=None)

_live_settings: Settings | None = None
_live_store = None
_live_error: str | None = None
try:
    _live_settings = Settings.from_env()
    _live_store = build_store(_live_settings)
except ConfigurationError as exc:
    _live_error = str(exc)
except Exception as exc:
    _live_error = f"{type(exc).__name__}: {exc}"

if _live_store is not None:
    bootstrap.include_router(create_router(_live_store))
else:
    @bootstrap.api_route(
        "/api/live/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )
    async def live_core_unavailable(path: str, request: Request):
        return JSONResponse(
            {"detail": _live_error or "148AI durable customer core is not configured"},
            status_code=503,
        )


def _load_runtime():
    try:
        return load_v28_runtime()
    except Exception:
        return None


async def _dispatch_runtime(request: Request, path: str | None = None):
    runtime = _load_runtime()
    if runtime is None:
        kind, message = get_runtime_load_error() or ("UnknownError", "Runtime did not load")
        return JSONResponse({"ok": False, "error_type": kind, "error": message[:1200]}, status_code=503)
    scope = dict(request.scope)
    if path is not None:
        scope["path"] = path
        scope["raw_path"] = path.encode()
    scope["root_path"] = ""
    started = {}
    chunks = []

    async def send(message):
        if message["type"] == "http.response.start":
            started.update(message)
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    await runtime(scope, request.receive, send)
    headers = {}
    for key_bytes, value_bytes in started.get("headers", []):
        key, value = key_bytes.decode(), value_bytes.decode()
        if key.lower() not in {"content-length", "transfer-encoding"}:
            headers[key] = value
    return Response(content=b"".join(chunks), status_code=started.get("status", 200), headers=headers)


@bootstrap.get("/_148ai/health")
def health():
    runtime_loaded = _load_runtime() is not None
    live_configured = _live_store is not None
    return {
        "ok": True,
        "service": "148AI",
        "runtime_zip": RUNTIME_ZIP.is_file(),
        "runtime_loaded": runtime_loaded,
        "live_core": {
            "configured": live_configured,
            "persistence": _live_settings.persistence if _live_settings else None,
            "environment": _live_settings.env if _live_settings else None,
            "error": _live_error,
        },
    }


@bootstrap.get("/_148ai/diagnostic")
def diagnostic():
    runtime = _load_runtime()
    runtime_payload: dict[str, object]
    if runtime is not None:
        runtime_payload = {"loaded": True}
    else:
        kind, message = get_runtime_load_error() or ("UnknownError", "Runtime did not load")
        runtime_payload = {"loaded": False, "error_type": kind, "error": message[:1200]}
    return {
        "ok": runtime is not None and _live_store is not None,
        "product": "148AI",
        "runtime": runtime_payload,
        "live_core": {
            "configured": _live_store is not None,
            "persistence": _live_settings.persistence if _live_settings else None,
            "error": _live_error,
        },
    }


@bootstrap.get("/", response_class=HTMLResponse)
def customer_home():
    page = UI_DIR / "index.html"
    if page.is_file():
        return page.read_text(encoding="utf-8")
    return HTMLResponse("<h1>148AI</h1><p>UI package missing.</p>", status_code=503)


@bootstrap.get("/ui/{asset_name}")
def customer_asset(asset_name: str):
    allowed = {
        "app.css": "text/css; charset=utf-8",
        "app.js": "application/javascript; charset=utf-8",
        "live-runner.js": "application/javascript; charset=utf-8",
    }
    if asset_name not in allowed:
        return Response(status_code=404)
    path = UI_DIR / asset_name
    if not path.is_file():
        return Response(status_code=404)
    return Response(path.read_bytes(), media_type=allowed[asset_name], headers={"Cache-Control": "public,max-age=300"})


@bootstrap.api_route("/app", methods=["GET", "HEAD"])
@bootstrap.api_route("/app/", methods=["GET", "HEAD"])
def old_app_redirect():
    return RedirectResponse("/", status_code=307)


@bootstrap.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def runtime_passthrough(path: str, request: Request):
    return await _dispatch_runtime(request, "/" + path)


app = bootstrap
