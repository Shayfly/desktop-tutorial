from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Health:
    ok: bool
    database: bool
    redis: bool

def readiness(settings) -> Health:
    from . import db, queueing
    db_ok = db.ping(settings.database_url)
    redis_ok = queueing.ping(settings.redis_url)
    return Health(ok=db_ok and redis_ok, database=db_ok, redis=redis_ok)
