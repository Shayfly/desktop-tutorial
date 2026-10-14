from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

@dataclass(frozen=True)
class ModelOption:
    provider: str
    model: str
    quality: int          # 1..100
    latency_ms: int
    input_per_million: Decimal
    output_per_million: Decimal
    enabled: bool = True

@dataclass(frozen=True)
class RoutingPolicy:
    minimum_quality: int = 70
    maximum_latency_ms: int | None = None
    prefer_cost: bool = True

def estimated_cost(
    option: ModelOption,
    *,
    input_tokens: int,
    output_tokens: int
) -> Decimal:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts cannot be negative")
    million = Decimal(1_000_000)
    return (
        (Decimal(input_tokens) / million) * option.input_per_million
        + (Decimal(output_tokens) / million) * option.output_per_million
    )

def select_model(
    options: Iterable[ModelOption],
    *,
    policy: RoutingPolicy,
    input_tokens: int,
    output_tokens: int,
) -> ModelOption:
    eligible = [
        o for o in options
        if o.enabled
        and o.quality >= policy.minimum_quality
        and (policy.maximum_latency_ms is None or o.latency_ms <= policy.maximum_latency_ms)
    ]
    if not eligible:
        raise LookupError("no eligible model")
    if policy.prefer_cost:
        return min(
            eligible,
            key=lambda o: (
                estimated_cost(o, input_tokens=input_tokens, output_tokens=output_tokens),
                -o.quality,
                o.latency_ms,
                o.provider,
                o.model,
            ),
        )
    return max(
        eligible,
        key=lambda o: (o.quality, -o.latency_ms),
    )
