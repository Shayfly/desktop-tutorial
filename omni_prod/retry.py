from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 30.0

    def __post_init__(self):
        if self.max_attempts < 1: raise ValueError('max_attempts must be >= 1')
        if self.base_delay_seconds <= 0: raise ValueError('base_delay_seconds must be > 0')
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError('max_delay_seconds must be >= base_delay_seconds')

def retry_delay(policy: RetryPolicy, attempt: int) -> float:
    if attempt < 1: raise ValueError('attempt must be >= 1')
    return min(policy.max_delay_seconds, policy.base_delay_seconds * (2 ** (attempt - 1)))

def can_retry(policy: RetryPolicy, attempt: int, retryable: bool) -> bool:
    return retryable and attempt < policy.max_attempts
