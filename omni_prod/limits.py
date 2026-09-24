from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Limit:
    name: str
    maximum: Decimal

@dataclass(frozen=True)
class LimitDecision:
    allowed: bool
    used: Decimal
    requested: Decimal
    maximum: Decimal
    remaining_after: Decimal

def check_limit(*, used: Decimal, requested: Decimal, limit: Limit) -> LimitDecision:
    if used < 0 or requested < 0 or limit.maximum < 0:
        raise ValueError("usage values cannot be negative")
    projected = used + requested
    remaining = max(Decimal("0"), limit.maximum - projected)
    return LimitDecision(
        allowed=projected <= limit.maximum,
        used=used,
        requested=requested,
        maximum=limit.maximum,
        remaining_after=remaining,
    )
