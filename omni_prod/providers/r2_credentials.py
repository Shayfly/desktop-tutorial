"""Cloudflare R2 temporary credentials signed only on a trusted server."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
import secrets
import time
from urllib.parse import urlsplit


def r2_account_id(endpoint: str) -> str:
    parts = urlsplit(endpoint)
    match = re.fullmatch(r"([a-f0-9]{32})\.r2\.cloudflarestorage\.com", parts.netloc)
    if (parts.scheme != "https" or not match or parts.path not in ("", "/")
            or parts.query or parts.fragment):
        raise ValueError("R2 requires a standard HTTPS account S3 endpoint")
    return match.group(1)


def _scope(policy: str) -> tuple[str, str]:
    from .managed_web_saas import scoped_object_policy

    try:
        doc = json.loads(policy)
        resource = doc["Statement"][0]["Resource"][0]
        match = re.fullmatch(
            r"arn:aws:s3:::([a-z0-9][a-z0-9.-]{1,61}[a-z0-9])/"
            r"(generated-apps/[A-Za-z0-9_-]+/(?:preview|production)/)\*", resource)
        if not match:
            raise ValueError
        bucket, prefix = match.groups()
        if doc != json.loads(scoped_object_policy(bucket, prefix)):
            raise ValueError
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        raise ValueError("R2 accepts only the managed per-app CRUD/list policy") from None
    return bucket, prefix


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class R2CredentialIssuer:
    """Implements the issuer contract without returning the parent secret.

    Only the exact managed CRUD/list policy is accepted. Local signing supports
    explicit actions, avoiding the broader API permission preset.
    """

    def __init__(self, *, endpoint: str, clock=None) -> None:
        self.account_id = r2_account_id(endpoint)
        self.audience = urlsplit(endpoint).netloc
        self.clock = clock or time.time

    def issue(self, *, operator_access_key, operator_secret_key, role_arn, policy,
              session_name, ttl_seconds) -> dict:
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 3600:
            raise ValueError("R2 credential TTL must be 1..3600 seconds")
        if not operator_access_key or not operator_secret_key:
            raise ValueError("R2 parent credentials are required")
        bucket, prefix = _scope(policy)
        issued = int(self.clock())
        claims = {
            "sub": self.account_id, "iss": operator_access_key, "aud": self.audience,
            "iat": issued, "exp": issued + ttl_seconds,
            "jti": secrets.token_hex(16), "bucket": bucket,
            "scope": "object-read-write",
            "actions": ["GetObject", "PutObject", "DeleteObject", "ListObjectsV1", "ListObjectsV2"],
            "paths": {"prefixPaths": [prefix], "objectPaths": []},
        }
        header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"},
                                  separators=(",", ":")).encode())
        payload = _b64url(json.dumps(claims, separators=(",", ":")).encode())
        signing_input = (header + "." + payload).encode("ascii")
        signature = hmac.new(operator_secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        jwt = signing_input.decode("ascii") + "." + _b64url(signature)
        return {
            # R2 intentionally reuses the parent's ID; the secret/token are scoped.
            "access_key_id": operator_access_key,
            "secret_access_key": hashlib.sha256(jwt.encode("ascii")).hexdigest(),
            "session_token": base64.b64encode(("jwt/" + jwt).encode("ascii")).decode("ascii"),
            "expires_at": datetime.fromtimestamp(issued + ttl_seconds, timezone.utc).isoformat().replace("+00:00", "Z"),
        }
