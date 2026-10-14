from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

class UsageKind(str, Enum):
    AI_INPUT_TOKENS = "ai_input_tokens"
    AI_OUTPUT_TOKENS = "ai_output_tokens"
    BUILD_SECONDS = "build_seconds"
    STORAGE_BYTES = "storage_bytes"
    EGRESS_BYTES = "egress_bytes"

@dataclass(frozen=True)
class UsageEvent:
    account_id: str
    project_id: str
    kind: UsageKind
    quantity: Decimal
    provider: str | None = None
    model: str | None = None

    def __post_init__(self):
        if self.quantity < 0:
            raise ValueError("usage quantity cannot be negative")
        if not self.account_id or not self.project_id:
            raise ValueError("account_id and project_id are required")

@dataclass(frozen=True)
class Rate:
    kind: UsageKind
    unit_price: Decimal

def cost(event: UsageEvent, rates: dict[UsageKind, Rate]) -> Decimal:
    rate = rates.get(event.kind)
    if rate is None:
        raise KeyError(f"missing rate for {event.kind.value}")
    return (event.quantity * rate.unit_price).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )
