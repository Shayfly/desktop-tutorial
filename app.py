"""Vercel/ASGI entrypoint for the 148AI review surface.

The full production topology still requires external durable services (Postgres,
Redis/RQ, S3 and the isolated sandbox runner). This entrypoint deliberately does
not inject credentials or weaken production fail-closed checks.
"""

from omni_prod.investor_app import app

__all__ = ["app"]
