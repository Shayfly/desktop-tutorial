"""QStash server-side scheduler connector; no configuration is live proof.

Callers must authorize tenant ownership and persist schedule IDs. Incoming
delivery verification requires a durable atomic replay claim supplied by the
consumer. Parent token/signing keys must never be given to generated apps.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from urllib import error, parse, request

_ORIGINS = {"https://qstash.upstash.io", "https://qstash-eu-central-1.upstash.io",
            "https://qstash-us-east-1.upstash.io"}


class QStashError(RuntimeError):
    """Safe error: never contains provider payloads, tokens or destination URLs."""


def validate_qstash_origin(url: str) -> str:
    origin = url.rstrip("/")
    if origin not in _ORIGINS:
        raise ValueError("QStash requires a supported HTTPS API origin")
    return origin


def _destination(url: str) -> str:
    parts = parse.urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or parts.username
            or parts.password or parts.fragment or parts.port not in (None, 443)
            or any(c in url for c in "\r\n")):
        raise ValueError("scheduler destination must be an approved HTTPS URL")
    return url


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class QStashClient:
    def __init__(self, *, base_url: str, token: str, allowed_destinations=(), opener=None):
        self.base_url = validate_qstash_origin(base_url)
        if not token or any(c in token for c in "\r\n"):
            raise ValueError("QStash token is required")
        self._token = token
        self._allowed = frozenset(_destination(u) for u in allowed_destinations)
        self._open = opener or request.build_opener(_NoRedirect()).open

    def __repr__(self):
        return "QStashClient(token=[REDACTED])"

    def _call(self, method, path, *, payload=None, headers=None, missing_ok=False):
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
        if body is not None and len(body) > 65536:
            raise ValueError("scheduler payload exceeds 64 KiB")
        req = request.Request(self.base_url + path, data=body, method=method,
                              headers={"Authorization": "Bearer " + self._token,
                                       "Content-Type": "application/json", **(headers or {})})
        try:
            with self._open(req, timeout=10) as resp:
                status = int(getattr(resp, "status", 200))
                if not 200 <= status < 300:
                    raise QStashError("QStash request rejected")
                raw = resp.read(262145)
                if len(raw) > 262144:
                    raise QStashError("QStash response too large")
            return json.loads(raw) if raw else None
        except error.HTTPError as exc:
            status = exc.code
            exc.close()
            if missing_ok and status == 404:
                return None
            raise QStashError(f"QStash request failed (HTTP {status})") from None
        except QStashError:
            raise
        except Exception:
            raise QStashError("QStash request failed") from None

    def _target(self, destination):
        if destination not in self._allowed:
            raise ValueError("scheduler destination not allowlisted")
        return parse.quote(destination, safe="")

    @staticmethod
    def _id(schedule_id):
        if not isinstance(schedule_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", schedule_id):
            raise ValueError("invalid schedule identifier")
        return schedule_id

    def check_access(self) -> bool:
        # Read-only authentication check, not delivery proof.
        return isinstance(self._call("GET", "/v2/schedules"), list)

    def create(self, *, destination, cron, schedule_id, payload):
        sid = self._id(schedule_id)
        if not isinstance(cron, str) or not re.fullmatch(r"[0-9*/?,\- ]{1,128}", cron) or len(cron.split()) != 5:
            raise ValueError("a five-field numeric cron expression is required")
        result = self._call("POST", "/v2/schedules/" + self._target(destination), payload=payload,
                            headers={"Upstash-Cron": cron, "Upstash-Schedule-Id": sid,
                                     "Upstash-Retries": "2", "Upstash-Timeout": "10s",
                                     "Upstash-Redact-Fields": "body,headers"})
        if not isinstance(result, dict) or result.get("scheduleId") != sid:
            raise QStashError("QStash returned an invalid schedule identifier")
        return sid

    def publish(self, *, destination, payload, deduplication_id):
        did = self._id(deduplication_id)
        result = self._call("POST", "/v2/publish/" + self._target(destination), payload=payload,
                            headers={"Upstash-Deduplication-Id": did, "Upstash-Retries": "2",
                                     "Upstash-Timeout": "10s", "Upstash-Redact-Fields": "body,headers"})
        if not isinstance(result, dict) or not isinstance(result.get("messageId"), str) or not result["messageId"]:
            raise QStashError("QStash returned an invalid message identifier")
        return result["messageId"]

    def get(self, schedule_id):
        return self._call("GET", "/v2/schedules/" + self._id(schedule_id), missing_ok=True)

    def cancel(self, schedule_id):
        self._call("DELETE", "/v2/schedules/" + self._id(schedule_id), missing_ok=True)


def _decode(part):
    if not isinstance(part, str) or not re.fullmatch(r"[A-Za-z0-9_-]+={0,2}", part):
        raise ValueError
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


class QStashReceiver:
    def __init__(self, *, current_key, next_key, clock=None):
        if not current_key or not next_key:
            raise ValueError("both QStash signing keys are required")
        self._keys = (current_key.encode(), next_key.encode())
        self._clock = clock or time.time

    def __repr__(self):
        return "QStashReceiver(keys=[REDACTED])"

    def verify(self, *, signature: str, body: bytes, destination: str, claim_once):
        """Validate provider delivery then claim jti atomically in durable storage.

        claim_once(jti, expiry) must return True exactly once across processes.
        A rejected duplicate raises a safe error; consumers may return 200 for
        already-completed work but must not run the side effect again.
        """
        try:
            if not callable(claim_once) or not isinstance(body, bytes) or len(body) > 1048576:
                raise ValueError
            if not isinstance(signature, str) or len(signature) > 16384:
                raise ValueError
            header, payload, signed = signature.split(".")
            metadata = json.loads(_decode(header), object_pairs_hook=_unique_object)
            claims = json.loads(_decode(payload), object_pairs_hook=_unique_object)
            if metadata != {"alg": "HS256", "typ": "JWT"}:
                raise ValueError
            expected = _decode(signed)
            data = (header + "." + payload).encode("ascii")
            if not any(hmac.compare_digest(hmac.new(key, data, hashlib.sha256).digest(), expected)
                       for key in self._keys):
                raise ValueError
            now = int(self._clock())
            times = [claims.get(k) for k in ("exp", "nbf", "iat")]
            if any(type(v) is not int for v in times):
                raise ValueError
            exp, nbf, iat = times
            if exp <= now or nbf > now or iat > now or nbf >= exp or iat >= exp:
                raise ValueError
            if claims.get("iss") != "Upstash" or claims.get("sub") != destination:
                raise ValueError
            digest = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode().rstrip("=")
            if not isinstance(claims.get("body"), str) or not hmac.compare_digest(claims["body"].rstrip("="), digest):
                raise ValueError
            jti = claims.get("jti")
            if not isinstance(jti, str) or not 1 <= len(jti) <= 256:
                raise ValueError
        except Exception:
            raise QStashError("invalid QStash delivery signature") from None
        # Storage failure must propagate safely and fail closed, not be called invalid signature.
        try:
            claimed = claim_once(jti, exp)
        except Exception:
            raise QStashError("QStash replay protection unavailable") from None
        if claimed is not True:
            raise QStashError("duplicate QStash delivery")
        return {"delivery_id": jti, "expires_at": exp}
