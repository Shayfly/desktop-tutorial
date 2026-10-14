from __future__ import annotations
from datetime import datetime, timezone
import json
from .secret_redaction import redact

def make_event(
    *,
    event_type: str,
    request_id: str,
    resource_id: str | None = None,
    message: str = "",
    fields: dict | None = None,
) -> dict:
    if not event_type or not request_id:
        raise ValueError("event_type and request_id are required")
    safe_fields = {}
    for key, value in (fields or {}).items():
        safe_fields[str(key)] = redact(str(value))
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "request_id": request_id,
        "resource_id": resource_id,
        "message": redact(message),
        "fields": safe_fields,
    }

def event_json(**kwargs) -> str:
    return json.dumps(make_event(**kwargs), sort_keys=True, ensure_ascii=False)
