from __future__ import annotations

import html
import os
import sys
import zipfile
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

ROOT = Path(__file__).resolve().parent
RUNTIME_ZIP = ROOT / "omni_prod_runtime.zip"
RUNTIME_DIR = Path("/tmp/148ai_v28_runtime")
_lock = Lock()
_loaded_app = None
_load_error = None

os.environ.setdefault("OMNI_ENV", "development")
os.environ.setdefault("OMNI_CREATOR_PERSISTENCE", "memory")

bootstrap = FastAPI(title="148AI V28")

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
            return _loaded_app
        except Exception as exc:
            _load_error = (type(exc).__name__, str(exc))
            return None

@bootstrap.get("/api/health")
def health():
    return {"ok": True, "service": "148AI V28 bootstrap", "runtime_zip": RUNTIME_ZIP.is_file()}

@bootstrap.get("/api/startup-diagnostic")
def diagnostic():
    runtime = _load_runtime()
    if runtime is not None:
        return {"ok": True, "runtime": "148AI V28", "loaded": True}
    kind, message = _load_error or ("UnknownError", "Runtime did not load")
    return JSONResponse({"ok": False, "runtime": "148AI V28", "loaded": False,
                         "error_type": kind, "error": message[:1200],
                         "runtime_zip_exists": RUNTIME_ZIP.is_file()}, status_code=200)

@bootstrap.get("/", response_class=HTMLResponse)
def root():
    runtime = _load_runtime()
    if runtime is None:
        kind, message = _load_error or ("UnknownError", "Runtime did not load")
        return f"""<!doctype html><html><head><meta charset="utf-8"><title>148AI V28</title>
<style>body{{font-family:system-ui;background:#07101f;color:#eef6ff;padding:40px;max-width:900px;margin:auto}}code{{display:block;background:#0d1a2d;border:1px solid #233b5f;border-radius:12px;padding:16px;white-space:pre-wrap}}h1{{color:#2fd4ff}}</style></head>
<body><h1>148AI V28</h1><p>Bootstrap is online. The packaged V28 runtime could not load.</p>
<code>{html.escape(kind)}: {html.escape(message[:1200])}</code></body></html>"""
    return HTMLResponse("<!doctype html><html><body><h1>148AI V28 runtime loaded</h1><p>Runtime is available. Open <a href='/app/'>/app/</a>.</p></body></html>")

@bootstrap.api_route("/app/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"])
async def runtime_proxy(path: str, request: Request):
    runtime = _load_runtime()
    if runtime is None:
        kind, message = _load_error or ("UnknownError", "Runtime did not load")
        return JSONResponse({"ok": False, "error_type": kind, "error": message[:1200]}, status_code=503)
    # Re-dispatch to the ASGI app with /app stripped.
    scope = dict(request.scope)
    scope["path"] = "/" + path
    scope["raw_path"] = scope["path"].encode()\n    # The V28 UI uses root-relative /api/... calls. Keep the runtime aware that\n    # it is mounted below /app so generated URLs and routing stay consistent.\n    scope["root_path"] = "/app"
    response_started = {}
    chunks = []
    async def send(message):
        if message["type"] == "http.response.start":
            response_started.update(message)
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))
    await runtime(scope, request.receive, send)
    return HTMLResponse(content=b"".join(chunks), status_code=response_started.get("status", 200),
                        headers={k.decode(): v.decode() for k,v in response_started.get("headers", [])})

# Forward root-level runtime API calls used by the V28 browser UI.
# The HTML served from /app/ contains root-relative /api/... requests, so without
# this bridge registration/sign-in/build calls hit the bootstrap and return 404.
@bootstrap.api_route("/api/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"])
async def runtime_api_proxy(path: str, request: Request):
    # Keep bootstrap-owned diagnostics local.
    if path in {"health", "startup-diagnostic"}:
        return JSONResponse({"ok": False, "error": "reserved bootstrap route"}, status_code=404)
    runtime = _load_runtime()
    if runtime is None:
        kind, message = _load_error or ("UnknownError", "Runtime did not load")
        return JSONResponse({"ok": False, "error_type": kind, "error": message[:1200]}, status_code=503)
    scope = dict(request.scope)
    scope["path"] = "/api/" + path
    scope["raw_path"] = scope["path"].encode()
    scope["root_path"] = ""
    response_started = {}
    chunks = []
    async def send(message):
        if message["type"] == "http.response.start":
            response_started.update(message)
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))
    await runtime(scope, request.receive, send)
    return Response(content=b"".join(chunks), status_code=response_started.get("status", 200),
                    headers={k.decode(): v.decode() for k,v in response_started.get("headers", [])})

app = bootstrap
