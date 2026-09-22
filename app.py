from __future__ import annotations

import html
import os
import sys
import zipfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

ROOT = Path(__file__).resolve().parent
RUNTIME_ZIP = ROOT / "omni_prod_runtime.zip"
RUNTIME_DIR = Path("/tmp/148ai_v28_runtime")
MARKER = RUNTIME_DIR / ".ready"

os.environ.setdefault("OMNI_ENV", "development")
os.environ.setdefault("OMNI_CREATOR_PERSISTENCE", "memory")

try:
    if not RUNTIME_ZIP.exists():
        raise FileNotFoundError(f"Runtime package missing: {RUNTIME_ZIP.name}")

    if not MARKER.exists():
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(RUNTIME_ZIP, "r") as zf:
            zf.extractall(RUNTIME_DIR)
        MARKER.write_text("148AI V28", encoding="utf-8")

    sys.path.insert(0, str(RUNTIME_DIR))
    from omni_prod.investor_app import app  # noqa: E402,F401

except Exception as exc:
    # Keep the Vercel function alive and expose only a sanitized startup diagnostic.
    # This lets us identify packaging/runtime problems without leaking secrets.
    startup_error_type = type(exc).__name__
    startup_error_message = str(exc).replace(str(ROOT), "<app>").replace(str(RUNTIME_DIR), "<runtime>")

    app = FastAPI(title="148AI V28 startup diagnostics")

    @app.get("/", response_class=HTMLResponse)
    def startup_diagnostics() -> str:
        return f"""
        <!doctype html>
        <html><head><meta charset='utf-8'><title>148AI V28 Diagnostics</title>
        <style>body{{font-family:system-ui;background:#07101f;color:#eef6ff;padding:40px;max-width:900px;margin:auto}}code{{display:block;background:#0d1a2d;border:1px solid #233b5f;border-radius:12px;padding:16px;white-space:pre-wrap}}h1{{color:#2fd4ff}}</style></head>
        <body><h1>148AI V28 runtime diagnostic</h1><p>The Vercel function started, but the V28 runtime import failed.</p>
        <code>{html.escape(startup_error_type)}: {html.escape(startup_error_message)}</code>
        </body></html>
        """

    @app.get("/api/startup-diagnostic")
    def startup_diagnostic_json() -> JSONResponse:
        return JSONResponse({
            "ok": False,
            "runtime": "148AI V28",
            "error_type": startup_error_type,
            "error": startup_error_message,
            "runtime_zip_exists": RUNTIME_ZIP.exists(),
        })
