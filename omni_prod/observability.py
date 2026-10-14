from __future__ import annotations
import time
from fastapi.responses import PlainTextResponse
from .metrics import MetricsRegistry
from .request_id import normalize_request_id

def configure_observability(app, registry: MetricsRegistry):
    @app.middleware("http")
    async def observe_request(request, call_next):
        request_id = normalize_request_id(
            request.headers.get("X-Request-ID")
        )
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
            registry.inc("omni_http_requests_total", 1)
            if response.status_code >= 500:
                registry.inc("omni_http_5xx_total", 1)
            return response
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            registry.observe("omni_http_request_duration_ms", elapsed_ms)
            if "response" in locals():
                response.headers["X-Request-ID"] = request_id

    @app.get("/_omni/metrics")
    def metrics():
        return PlainTextResponse(
            registry.render_prometheus(),
            media_type="text/plain; version=0.0.4",
        )
