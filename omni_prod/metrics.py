from __future__ import annotations
from dataclasses import dataclass, field
import math
import re

_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")

@dataclass
class MetricsRegistry:
    counters: dict[str, float] = field(default_factory=dict)
    observations: dict[str, list[float]] = field(default_factory=dict)

    def inc(self, name: str, amount: float = 1.0) -> None:
        self._validate(name)
        if amount < 0:
            raise ValueError("counter increment cannot be negative")
        self.counters[name] = self.counters.get(name, 0.0) + amount

    def observe(self, name: str, value: float) -> None:
        self._validate(name)
        if not math.isfinite(value) or value < 0:
            raise ValueError("observation must be finite and non-negative")
        self.observations.setdefault(name, []).append(value)

    def render_prometheus(self) -> str:
        lines = []
        for name in sorted(self.counters):
            lines.append(f"{name} {self.counters[name]}")
        for name in sorted(self.observations):
            values = self.observations[name]
            if not values:
                continue
            lines.append(f"{name}_count {len(values)}")
            lines.append(f"{name}_sum {sum(values)}")
        return "\n".join(lines) + ("\n" if lines else "")

    @staticmethod
    def _validate(name: str) -> None:
        if not _NAME.fullmatch(name):
            raise ValueError(f"invalid metric name: {name}")
