from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json

GENESIS = "0" * 64

@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    event_type: str
    actor_id: str
    resource_id: str
    timestamp: str
    payload: dict
    previous_hash: str
    event_hash: str

def _canonical(data: dict) -> bytes:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")

def create_event(
    *,
    sequence: int,
    event_type: str,
    actor_id: str,
    resource_id: str,
    payload: dict,
    previous_hash: str = GENESIS,
    timestamp: str | None = None,
) -> AuditEvent:
    if sequence < 1:
        raise ValueError("sequence must be >= 1")
    if not event_type or not actor_id or not resource_id:
        raise ValueError("event_type, actor_id and resource_id are required")
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
    if not isinstance(previous_hash, str) or len(previous_hash) != 64:
        raise ValueError("previous_hash must be a 64-char hex digest")
    try:
        int(previous_hash, 16)
    except ValueError as exc:
        raise ValueError("previous_hash must be hex") from exc
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    base = {
        "sequence": sequence,
        "event_type": event_type,
        "actor_id": actor_id,
        "resource_id": resource_id,
        "timestamp": ts,
        "payload": payload,
        "previous_hash": previous_hash,
    }
    digest = hashlib.sha256(_canonical(base)).hexdigest()
    return AuditEvent(event_hash=digest, **base)

def verify_chain(events: list[AuditEvent]) -> bool:
    prev = GENESIS
    expected_sequence = 1
    for e in events:
        if e.sequence != expected_sequence or e.previous_hash != prev:
            return False
        base = {
            "sequence": e.sequence,
            "event_type": e.event_type,
            "actor_id": e.actor_id,
            "resource_id": e.resource_id,
            "timestamp": e.timestamp,
            "payload": e.payload,
            "previous_hash": e.previous_hash,
        }
        if hashlib.sha256(_canonical(base)).hexdigest() != e.event_hash:
            return False
        prev = e.event_hash
        expected_sequence += 1
    return True
