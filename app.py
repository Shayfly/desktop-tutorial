from __future__ import annotations

import html
import os
import sys
import zipfile
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse

ROOT = Path(__file__).resolve().parent
RUNTIME_ZIP = ROOT / "omni_prod_runtime.zip"
RUNTIME_DIR = Path("/tmp/148ai_v28_runtime")\nUI_DIR = ROOT / "ui"
_lock = Lock()
_loaded_app = None
_load_error = None

os.environ.setdefault("OMNI_ENV", "development")
os.environ.setdefault("OMNI_CREATOR_PERSISTENCE", "memory")

bootstrap = FastAPI(title="148AI V28", docs_url=None, redoc_url=None)

def _load_runtime():
    global _loaded_app, _load_error
    if _loaded_app is not None:
        return _loaded_app
    with _lock:
        if _loaded_app is not None:
            return _loaded_app
        try:
            if not RUNTIME_ZIP.is_file():
                raise FileNotFoundError("omni_prod_runtime.zip is missing")
            marker = RUNTIME_DIR / ".ready"
            if not marker.exists():
                RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(RUNTIME_ZIP, "r") as zf:
                    bad = zf.testzip()
                    if bad:
                        raise zipfile.BadZipFile(f"CRC failure: {bad}")
                    zf.extractall(RUNTIME_DIR)
                marker.write_text("148AI V28", encoding="utf-8")
            if str(RUNTIME_DIR) not in sys.path:
                sys.path.insert(0, str(RUNTIME_DIR))
            from omni_prod.investor_app import app as runtime_app
            _loaded_app = runtime_app
            _load_error = None
            return runtime_app
        except Exception as exc:
            _load_error = (type(exc).__name__, str(exc))
            return None

async def _dispatch_runtime(request: Request, path: str | None = None):
    runtime = _load_runtime()
    if runtime is None:
        kind, message = _load_error or ("UnknownError", "Runtime did not load")
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
    for k, v in started.get("headers", []):
        key, value = k.decode(), v.decode()
        if key.lower() not in {"content-length", "transfer-encoding"}:
            headers[key] = value
    return Response(content=b"".join(chunks), status_code=started.get("status", 200), headers=headers)

@bootstrap.get("/_148ai/health")
def health():
    return {"ok": True, "service": "148AI V28", "runtime_zip": RUNTIME_ZIP.is_file(), "runtime_loaded": _load_runtime() is not None}

@bootstrap.get("/_148ai/diagnostic")
def diagnostic():
    runtime = _load_runtime()
    if runtime is not None:
        return {"ok": True, "runtime": "148AI V28", "loaded": True}
    kind, message = _load_error or ("UnknownError", "Runtime did not load")
    return JSONResponse({"ok": False, "error_type": kind, "error": message[:1200]}, status_code=200)

@bootstrap.get("/", response_class=HTMLResponse)
def customer_home():
    page = UI_DIR / "index.html"
    if page.is_file():
        return page.read_text(encoding="utf-8")
    return HTMLResponse("<h1>148AI</h1><p>UI package missing.</p>", status_code=503)

@bootstrap.get("/ui/{asset_name}")
def customer_asset(asset_name: str):
    allowed = {"app.css": "text/css; charset=utf-8", "app.js": "application/javascript; charset=utf-8"}
    if asset_name not in allowed:
        return Response(status_code=404)
    path = UI_DIR / asset_name
    if not path.is_file():
        return Response(status_code=404)
    return Response(path.read_bytes(), media_type=allowed[asset_name], headers={"Cache-Control": "public,max-age=300"})

@bootstrap.api_route("/app", methods=["GET","HEAD"])
@bootstrap.api_route("/app/", methods=["GET","HEAD"])
def old_app_redirect():
    return RedirectResponse("/", status_code=307)

@bootstrap.api_route("/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"])
async def runtime_passthrough(path: str, request: Request):
    # V28 is now mounted at the site root. API, assets, preview, export and
    # generated-runtime routes all pass through without fragile path rewriting.
    return await _dispatch_runtime(request, "/" + path)

app = bootstrap
