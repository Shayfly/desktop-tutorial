"""Browser session transport: HttpOnly cookie for the web workspace, Bearer for API clients.

The token itself is unchanged (same identity service, same server-side
expiry/revocation). Only how a browser carries it changes:

* login/register set ``148ai_session`` as HttpOnly, SameSite=Strict, path=/,
  and Secure (always in production; can be disabled only outside production
  for plain-http local development). No max_age: a browser-session cookie;
  real expiry and revocation stay server-side.
* ``Authorization: Bearer`` keeps working and takes precedence, so existing
  API clients and tests are unaffected.
* A request authenticated by the cookie that changes state (anything but
  GET/HEAD/OPTIONS) must prove it is same-origin (Origin equal to the host or
  an allowed origin, or Sec-Fetch-Site: same-origin). Together with
  SameSite=Strict this blocks cross-site request forgery.
"""
from __future__ import annotations

import os
from typing import Iterable, Mapping
from urllib import parse

__all__ = ["COOKIE_NAME", "SessionTokenError", "browser_session_readiness", "cookie_settings",
           "extract_session_token"]

COOKIE_NAME = "148ai_session"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class SessionTokenError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _origin_of(url: str) -> str:
    parts = parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower() if parts.scheme and parts.netloc else ""


def _same_origin(request, allowed_origins: Iterable[str]) -> bool:
    headers = request.headers
    if str(headers.get("sec-fetch-site", "")).lower() == "same-origin":
        return True
    origin = str(headers.get("origin", "") or "").lower()
    if not origin or origin == "null":
        referer = str(headers.get("referer", "") or "")
        origin = _origin_of(referer) if referer else ""
    if not origin:
        return False
    own = f"{request.url.scheme}://{request.url.netloc}".lower()
    return origin == own or origin in {o.lower().rstrip("/") for o in allowed_origins}


def extract_session_token(request, *, allowed_origins: Iterable[str]) -> tuple[str, str]:
    raw = str(request.headers.get("authorization", "") or "")
    if raw.startswith("Bearer ") and raw[7:].strip():
        return raw[7:].strip(), "bearer"
    if raw:
        raise SessionTokenError(401, "authentication required")
    cookie = (getattr(request, "cookies", {}) or {}).get(COOKIE_NAME)
    if not cookie:
        raise SessionTokenError(401, "authentication required")
    if str(request.method).upper() not in _SAFE_METHODS and not _same_origin(request, allowed_origins):
        raise SessionTokenError(403, "cross-site request refused for cookie session")
    return cookie, "cookie"


def _secure(production: bool, env: Mapping[str, str]) -> bool:
    if production:
        return True
    return str(env.get("OMNI_SESSION_COOKIE_SECURE", "1")).strip() != "0"


def cookie_settings(*, production: bool, env: Mapping[str, str] | None = None) -> dict:
    env = os.environ if env is None else env
    return {"key": COOKIE_NAME, "httponly": True, "secure": _secure(production, env), "samesite": "strict", "path": "/"}


def browser_session_readiness(*, production: bool, env: Mapping[str, str] | None = None) -> dict:
    env = os.environ if env is None else env
    if not _secure(production, env):
        return {"status": "BLOCKED", "transport": "HTTPONLY_COOKIE",
                "reason": "session cookie is not Secure (OMNI_SESSION_COOKIE_SECURE=0); acceptable only for local http development"}
    return {"status": "PARTIAL", "transport": "HTTPONLY_COOKIE",
            "reason": ("HttpOnly + Secure + SameSite=Strict cookie with same-origin check on writes; "
                       "not yet verified on the deployed HTTPS origin")}
