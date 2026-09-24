from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Lease:
    owner: str
    expires_at: float

def can_claim(lease: Lease | None, *, now: float, owner: str) -> bool:
    if not owner:
        raise ValueError("owner required")
    if lease is None:
        return True
    if lease.owner == owner:
        return True
    return now >= lease.expires_at

def renew(*, owner: str, now: float, ttl_seconds: float) -> Lease:
    if not owner:
        raise ValueError("owner required")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be >0")
    return Lease(owner=owner, expires_at=now + ttl_seconds)
