from __future__ import annotations
import re
import uuid

_VALID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")

def normalize_request_id(value: str | None) -> str:
    if value and _VALID.fullmatch(value):
        return value
    return uuid.uuid4().hex
