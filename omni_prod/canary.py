from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CanaryPolicy:
    initial_percent: int = 5
    step_percent: int = 20
    error_rate_threshold: float = 0.02
    min_requests: int = 100

    def __post_init__(self):
        if not 1 <= self.initial_percent <= 100: raise ValueError('invalid initial_percent')
        if not 1 <= self.step_percent <= 100: raise ValueError('invalid step_percent')
        if not 0 <= self.error_rate_threshold <= 1: raise ValueError('invalid threshold')
        if self.min_requests < 1: raise ValueError('min_requests must be >=1')

@dataclass(frozen=True)
class CanaryObservation:
    requests: int
    errors: int

    @property
    def error_rate(self) -> float:
        return 0.0 if self.requests == 0 else self.errors / self.requests

def evaluate_canary(policy: CanaryPolicy, observation: CanaryObservation, current_percent: int) -> str:
    if observation.requests < policy.min_requests:
        return 'hold'
    if observation.error_rate > policy.error_rate_threshold:
        return 'rollback'
    if current_percent >= 100:
        return 'complete'
    return 'advance'
