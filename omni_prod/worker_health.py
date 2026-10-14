from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

@dataclass(frozen=True)
class WorkerHeartbeat:
    worker_id: str
    seen_at: datetime

def is_stale(heartbeat: WorkerHeartbeat, *, now: datetime, max_age_seconds: int) -> bool:
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    if heartbeat.seen_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return now - heartbeat.seen_at > timedelta(seconds=max_age_seconds)
