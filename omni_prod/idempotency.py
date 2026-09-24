from __future__ import annotations
import hashlib
import json
import re

_KEY = re.compile(r"^[A-Za-z0-9._:-]{8,160}$")

def validate_key(key: str) -> str:
    if not _KEY.fullmatch(key):
        raise ValueError("invalid idempotency key")
    return key

def request_fingerprint(payload: dict) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

class PostgresIdempotencyRepository:
    def __init__(self, database):
        self.database_url = database

    def claim(self, *, account_id: str, key: str, fingerprint: str) -> tuple[bool, str | None]:
        """
        Returns (created, existing_resource_id).
        If the same key exists with another fingerprint, raises ValueError.
        """
        from .db import transaction
        validate_key(key)
        with transaction(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT request_fingerprint, resource_id
                    FROM idempotency_keys
                    WHERE account_id = %s AND idempotency_key = %s
                    FOR UPDATE
                    """,
                    (account_id, key),
                )
                row = cur.fetchone()
                if row:
                    if row[0] != fingerprint:
                        raise ValueError("idempotency key reused with different payload")
                    return False, row[1]
                cur.execute(
                    """
                    INSERT INTO idempotency_keys(
                        account_id, idempotency_key, request_fingerprint
                    ) VALUES (%s, %s, %s)
                    """,
                    (account_id, key, fingerprint),
                )
                return True, None

    def attach_resource(self, *, account_id: str, key: str, resource_id: str) -> None:
        from .db import transaction
        with transaction(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE idempotency_keys
                    SET resource_id = %s
                    WHERE account_id = %s AND idempotency_key = %s
                    """,
                    (resource_id, account_id, key),
                )
                if cur.rowcount != 1:
                    raise KeyError("idempotency claim not found")
