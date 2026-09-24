from __future__ import annotations

def create_production_router(settings):
    """
    Returns a FastAPI APIRouter without forcing FastAPI imports at package import time.
    This lets the production overlay stay testable independently of the V10 app.
    """
    from fastapi import APIRouter, HTTPException
    from .health import readiness

    router = APIRouter(prefix="/_omni")

    @router.get("/health/live")
    def live():
        return {"ok": True}

    @router.get("/health/ready")
    def ready():
        result = readiness(settings)
        if not result.ok:
            raise HTTPException(
                status_code=503,
                detail={
                    "ok": False,
                    "database": result.database,
                    "redis": result.redis,
                },
            )
        return {
            "ok": True,
            "database": result.database,
            "redis": result.redis,
        }

    return router
