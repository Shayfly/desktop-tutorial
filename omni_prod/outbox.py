from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import uuid

@dataclass(frozen=True)
class OutboxEvent:
    id: str
    topic: str
    aggregate_id: str
    payload: dict
    dedupe_key: str
    created_at: str

def deterministic_dedupe_key(*, topic: str, aggregate_id: str, payload: dict) -> str:
    raw = json.dumps(
        {"topic": topic, "aggregate_id": aggregate_id, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def new_event(*, topic: str, aggregate_id: str, payload: dict) -> OutboxEvent:
    if not topic or not aggregate_id:
        raise ValueError("topic and aggregate_id required")
    if not isinstance(payload, dict):
        raise TypeError("payload must be dict")
    return OutboxEvent(
        id=str(uuid.uuid4()),
        topic=topic,
        aggregate_id=aggregate_id,
        payload=payload,
        dedupe_key=deterministic_dedupe_key(
            topic=topic, aggregate_id=aggregate_id, payload=payload
        ),
        created_at=datetime.now(timezone.utc).isoformat(),
    )

class PostgresOutboxRepository:
    def enqueue(self, cur, event: OutboxEvent) -> None:
        sql = (
            "INSERT INTO outbox_events"
            "(id,topic,aggregate_id,payload,dedupe_key,created_at) "
            "VALUES (%s,%s,%s,%s::jsonb,%s,%s) "
            "ON CONFLICT (dedupe_key) DO NOTHING"
        )
        cur.execute(sql, (
            event.id, event.topic, event.aggregate_id,
            json.dumps(event.payload), event.dedupe_key, event.created_at
        ))

    def claim_batch(self, cur, *, limit: int = 100) -> list[tuple]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit out of range")
        sql = (
            "SELECT id,topic,aggregate_id,payload,dedupe_key "
            "FROM outbox_events "
            "WHERE published_at IS NULL AND available_at<=NOW() "
            "ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT %s"
        )
        cur.execute(sql, (limit,))
        return list(cur.fetchall())

    def mark_published(self, cur, event_id: str) -> None:
        cur.execute(
            "UPDATE outbox_events SET published_at=NOW(),last_error=NULL WHERE id=%s",
            (event_id,),
        )

    def mark_failed(self, cur, event_id: str, error: str) -> None:
        sql = (
            "UPDATE outbox_events SET attempts=attempts+1,last_error=%s,"
            "available_at=NOW()+LEAST(INTERVAL '10 minutes', "
            "INTERVAL '2 seconds' * POWER(2, attempts)) WHERE id=%s"
        )
        cur.execute(sql, (error[:1000], event_id))
