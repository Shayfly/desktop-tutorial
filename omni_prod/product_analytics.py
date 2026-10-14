from __future__ import annotations
from dataclasses import dataclass, asdict
from statistics import median

@dataclass(frozen=True)
class BuildMetric:
    status: str
    duration_ms: int
    repair_rounds: int
    cost_usd: float
    quality_score: int

@dataclass(frozen=True)
class ProductMetrics:
    builds: int
    success_rate: float
    median_duration_ms: int
    p95_duration_ms: int
    median_repair_rounds: float
    avg_cost_per_ready_usd: float
    avg_quality_score: float

    def to_dict(self): return asdict(self)

def summarize(metrics: list[BuildMetric]) -> ProductMetrics:
    if not metrics: return ProductMetrics(0,0,0,0,0,0,0)
    durations=sorted(max(0,m.duration_ms) for m in metrics)
    idx=min(len(durations)-1, max(0, int(round((len(durations)-1)*0.95))))
    ready=[m for m in metrics if m.status=='ready']
    return ProductMetrics(
        builds=len(metrics),
        success_rate=round(len(ready)/len(metrics),4),
        median_duration_ms=int(median(durations)),
        p95_duration_ms=durations[idx],
        median_repair_rounds=float(median([m.repair_rounds for m in metrics])),
        avg_cost_per_ready_usd=round(sum(m.cost_usd for m in ready)/len(ready),6) if ready else 0,
        avg_quality_score=round(sum(m.quality_score for m in metrics)/len(metrics),2),
    )
