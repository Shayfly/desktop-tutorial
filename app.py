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
from live_core.config import Settings, build_store

# Fails loudly (ConfigurationError) when OMNI_DATABASE_URL is missing and memory
# persistence was not explicitly requested. No silent fallback to DATABASE_URL.
app.include_router(create_router(build_store(Settings.from_env())))

# Blocker 4: serve ui/ (index.html, app.js, app.css, live-runner.js) under /ui/.
app.mount("/ui", StaticFiles(directory=Path(__file__).resolve().parent / "ui"), name="ui")

__all__ = ["app"]
