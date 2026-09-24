from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass(frozen=True)
class CircuitPolicy:
    failure_threshold: int = 5
    recovery_seconds: float = 30.0

    def __post_init__(self):
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >=1")
        if self.recovery_seconds <= 0:
            raise ValueError("recovery_seconds must be >0")

@dataclass
class CircuitBreaker:
    policy: CircuitPolicy
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    opened_at: float | None = None
    half_open_probe_in_flight: bool = False

    def allow(self, now: float) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.opened_at is not None and now - self.opened_at >= self.policy.recovery_seconds:
                self.state = CircuitState.HALF_OPEN
                self.half_open_probe_in_flight = False
            else:
                return False
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_probe_in_flight:
                return False
            self.half_open_probe_in_flight = True
            return True
        return False

    def success(self) -> None:
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.opened_at = None
        self.half_open_probe_in_flight = False

    def failure(self, now: float) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.opened_at = now
            self.half_open_probe_in_flight = False
            return
        self.failures += 1
        if self.failures >= self.policy.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = now
