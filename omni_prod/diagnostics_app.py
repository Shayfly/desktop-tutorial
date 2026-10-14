from __future__ import annotations
import os
from fastapi import FastAPI
from .api_routes import create_production_router
from .config import Settings
from .metrics import MetricsRegistry
from .observability import configure_observability
from .preflight import run_preflight
from .web_security import configure_web_security

settings = Settings.from_env()
production = settings.environment == "production"

app = FastAPI(title="Omni Creator Production Diagnostics")
registry = MetricsRegistry()
configure_web_security(
    app,
    raw_origins=os.environ.get("OMNI_ALLOWED_ORIGINS", ""),
    production=production,
)
configure_observability(app, registry)
app.include_router(create_production_router(settings))

@app.get("/_omni/preflight")
def preflight():
    report = run_preflight()
    return {
        "ready": report.ready,
        "issues": [
            {"code": i.code, "message": i.message, "blocking": i.blocking}
            for i in report.issues
        ],
        "capabilities": report.capabilities,
    }
