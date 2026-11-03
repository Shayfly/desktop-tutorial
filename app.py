"""Vercel/ASGI entrypoint for the 148AI review surface.

The full production topology still requires external durable services (Postgres,
Redis/RQ, S3 and the isolated sandbox runner). This entrypoint deliberately does
not inject credentials or weaken production fail-closed checks.

Decision #232 (B2): live_core is installed into investor_app as a router.
investor_app keeps its app object; nothing here replaces or removes it.
"""

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from omni_prod.investor_app import app
from live_core.api import create_router
from live_core.config import Settings, build_store, live_enabled

# Routes are registered at import; the store is built by the first /api/live/*
# request that needs it. A missing OMNI_DATABASE_URL fails that request with an
# explicit 503 (ConfigurationError), never the boot. No fallback to DATABASE_URL.
# Kill switch: until OMNI_LIVE_ENABLED is on, every live_core route answers 503
# before any store or database access.
app.include_router(create_router(
    store_factory=lambda: build_store(Settings.from_env()),
    enabled=live_enabled,
))

# Blocker 4: serve ui/ (index.html, app.js, app.css, live-runner.js) under /ui/.
app.mount("/ui", StaticFiles(directory=Path(__file__).resolve().parent / "ui"), name="ui")

__all__ = ["app"]
