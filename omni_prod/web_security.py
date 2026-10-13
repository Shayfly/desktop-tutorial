from __future__ import annotations
from fastapi.middleware.cors import CORSMiddleware
import os
from .cors_policy import parse_and_validate_origins
from .preview_runtime import preview_frame_source

def configure_web_security(app,*,raw_origins:str,production:bool)->list[str]:
    origins=parse_and_validate_origins(raw_origins,production=production)
    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,
                       allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'],
                       allow_headers=['Authorization','Content-Type','Idempotency-Key'],
                       expose_headers=['X-Request-ID'],max_age=600)
    @app.middleware('http')
    async def security_headers(request,call_next):
        response=await call_next(request)
        response.headers.setdefault('X-Content-Type-Options','nosniff')
        response.headers.setdefault('X-Frame-Options','DENY')
        response.headers.setdefault('Referrer-Policy','no-referrer')
        response.headers.setdefault('Permissions-Policy','camera=(), microphone=(), geolocation=()')
        # M5-UX01: the creator workspace embeds running previews; only the
        # configured preview wildcard host may be framed.
        frame = preview_frame_source(os.getenv('PREVIEW_DOMAIN_TEMPLATE'))
        # img-src blob:/data: -- the workspace previews an image (and draws on a
        # screenshot) locally before it is uploaded.
        csp = ("default-src 'self'; img-src 'self' blob: data:; object-src 'none'; base-uri 'self'; "
               "frame-ancestors 'none'; form-action 'self'")
        if frame:
            csp += f"; frame-src 'self' {frame}"
        response.headers.setdefault('Content-Security-Policy', csp)
        response.headers.setdefault('Cross-Origin-Opener-Policy','same-origin')
        response.headers.setdefault('Cross-Origin-Resource-Policy','same-origin')
        if production:
            response.headers.setdefault('Strict-Transport-Security','max-age=31536000; includeSubDomains')
        return response
    return origins
