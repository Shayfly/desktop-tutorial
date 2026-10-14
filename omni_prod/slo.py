from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class SLOTarget:
    max_error_rate: float
    max_p95_ms: float
    min_samples: int = 100

    def __post_init__(self):
        if not 0 <= self.max_error_rate <= 1:
            raise ValueError("invalid max_error_rate")
        if self.max_p95_ms <= 0:
            raise ValueError("max_p95_ms must be positive")
        if self.min_samples < 1:
            raise ValueError("min_samples must be >=1")

@dataclass(frozen=True)
class SLOResult:
    status: str
    samples: int
    error_rate: float
    p95_ms: float | None

def percentile95(values: list[float]) -> float:
    if not values:
        raise ValueError("values required")
    ordered = sorted(values)
    idx = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[idx]

def evaluate_slo(
    target: SLOTarget,
    *,
    latencies_ms: list[float],
    errors: int,
) -> SLOResult:
    samples = len(latencies_ms)
    if errors < 0 or errors > samples:
        raise ValueError("errors must be between 0 and samples")
    if any(x < 0 or not math.isfinite(x) for x in latencies_ms):
        raise ValueError("invalid latency")
    if samples < target.min_samples:
        return SLOResult("insufficient_data", samples, 0 if samples == 0 else errors/samples, None)
    error_rate = errors / samples
    p95 = percentile95(latencies_ms)
    status = "pass" if (
        error_rate <= target.max_error_rate and p95 <= target.max_p95_ms
    ) else "fail"
    return SLOResult(status, samples, error_rate, p95)
