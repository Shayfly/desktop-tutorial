"""Read-only, fail-closed bounded HTTP client for explicitly authorized targets.

This is NOT an arbitrary URL scanning API. Callers must supply an exact target
hostname allowlist for non-loopback deployments. Never accept untrusted hosts.
"""
from __future__ import annotations

import ipaddress
import json
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .models import ErrorClass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Even same-host redirects are blocked to avoid auth or origin ambiguity."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        raise urllib.error.HTTPError(req.full_url, code, "redirect blocked", headers, fp)


def validated_origin(url: str, allowed_hosts: tuple[str, ...] = ()) -> str:
    if not isinstance(url, str) or not url or any(c.isspace() or ord(c) < 32 for c in url):
        raise ValueError("Invalid deployment URL")
    try:
        p = urllib.parse.urlsplit(url)
        host = p.hostname
        port = p.port
    except ValueError as exc:
        raise ValueError("Invalid deployment URL") from exc
    if p.scheme not in ("http", "https") or not host or p.username is not None or p.password is not None:
        raise ValueError("Invalid deployment URL or embedded credentials")
    if p.query or p.fragment or p.path not in ("", "/") or port == 0:
        raise ValueError("Deployment URL must be an origin without path, query or fragment")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    loopback = (address is not None and address.is_loopback) or host.lower() == "localhost"
    if p.scheme == "http" and not loopback:
        raise ValueError("HTTPS is required for non-loopback deployments")
    if address is not None and not address.is_loopback:
        raise ValueError("IP literal targets other than loopback are forbidden")
    if not loopback and host.lower().rstrip(".") not in {h.lower().rstrip(".") for h in allowed_hosts}:
        raise ValueError("Deployment host is not in the explicit allowed-hosts list")
    if p.scheme == "http" and port is None:
        raise ValueError("Specify a port for local HTTP testing")
    return f"{p.scheme}://{p.netloc}"


def _classify_http(code: int, data: Any) -> tuple[ErrorClass, str]:
    if 300 <= code < 400:
        return ErrorClass.UNEXPECTED_REDIRECT, "Redirects are not followed"
    if code == 401:
        return ErrorClass.AUTHENTICATION_INVALID, "Authentication failed"
    if code == 403:
        return ErrorClass.HTTP_403, "Access denied; infrastructure or app origin is not proven"
    if code == 503:
        detail = data.get("detail") if isinstance(data, dict) else None
        detail = detail if isinstance(detail, dict) else data
        if isinstance(detail, dict):
            error = detail.get("error") or detail.get("error_code")
            migration = detail.get("missing_migration")
            if error == "conversation_not_ready" and migration == "036_intelligence_plane":
                return ErrorClass.MIGRATION_NOT_APPLIED, "Migration 036_intelligence_plane missing"
            if error in ("durable_backend_required", "database_not_ready"):
                return ErrorClass.DATABASE_NOT_READY, "Database backend unavailable"
    lookup = {500: ErrorClass.HTTP_500, 502: ErrorClass.HTTP_502,
              503: ErrorClass.HTTP_503, 504: ErrorClass.HTTP_504}
    return lookup.get(code, ErrorClass.HTTP_OTHER), f"HTTP {code}"


@dataclass(frozen=True)
class HttpOutcome:
    code: int | None
    data: Any
    error: ErrorClass
    summary: str


class SafeHttpClient:
    def __init__(self, base_url: str, *, token: str | None, allowed_hosts: tuple[str, ...],
                 timeout: float, max_bytes: int):
        self.base_url = validated_origin(base_url, allowed_hosts)
        if not 0 < timeout <= 60 or not 0 < max_bytes <= 8 * 1024 * 1024:
            raise ValueError("Unsafe timeout or maximum response size")
        self.timeout, self.max_bytes, self.token = timeout, max_bytes, token
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        )

    def get(self, path: str, *, require_auth: bool) -> HttpOutcome:
        if not path.startswith("/") or path.startswith("//") or any(c in path for c in "?#\\"):
            raise ValueError("Unsafe request path")
        if require_auth and not self.token:
            return HttpOutcome(None, None, ErrorClass.AUTHENTICATION_MISSING, "Credentials unavailable")
        headers = {"Accept": "application/json", "User-Agent": "148AI-PDV/1"}
        if require_auth:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(self.base_url + path, headers=headers, method="GET")
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                return self._read(response, response.status)
        except urllib.error.HTTPError as exc:
            with exc:
                return self._read(exc, exc.code)
        except (TimeoutError, socket.timeout):
            return HttpOutcome(None, None, ErrorClass.TIMEOUT, "Request timed out")
        except ssl.SSLError:
            return HttpOutcome(None, None, ErrorClass.TLS_FAILURE, "TLS handshake failed")
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, (TimeoutError, socket.timeout)):
                return HttpOutcome(None, None, ErrorClass.TIMEOUT, "Request timed out")
            if isinstance(reason, socket.gaierror):
                return HttpOutcome(None, None, ErrorClass.DNS_FAILURE, "Hostname resolution failed")
            if isinstance(reason, ssl.SSLError):
                return HttpOutcome(None, None, ErrorClass.TLS_FAILURE, "TLS handshake failed")
            return HttpOutcome(None, None, ErrorClass.HTTP_CONNECTION_FAILURE, "Connection failed")
        except OSError:
            return HttpOutcome(None, None, ErrorClass.HTTP_CONNECTION_FAILURE, "Connection failed")

    def _read(self, response: Any, code: int) -> HttpOutcome:
        if 300 <= code < 400:
            error, msg = _classify_http(code, None)
            return HttpOutcome(code, None, error, msg)
        body = response.read(self.max_bytes + 1)
        if len(body) > self.max_bytes:
            return HttpOutcome(code, None, ErrorClass.RESPONSE_TOO_LARGE, "Response size exceeded")
        try:
            data = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            if 200 <= code < 300:
                return HttpOutcome(code, None, ErrorClass.INVALID_JSON, "Expected JSON response")
            data = None
        if 200 <= code < 300:
            return HttpOutcome(code, data, ErrorClass.NONE, "HTTP success; contract pending")
        error, msg = _classify_http(code, data)
        return HttpOutcome(code, None, error, msg)
