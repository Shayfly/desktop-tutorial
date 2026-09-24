from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DeadLetterDecision:
    dead_letter: bool
    reason: str

def decide_dead_letter(
    *, attempts: int, max_attempts: int,
    retryable: bool, permanent: bool = False
) -> DeadLetterDecision:
    if attempts < 0 or max_attempts < 1:
        raise ValueError("invalid attempt counts")
    if permanent:
        return DeadLetterDecision(True, "permanent_error")
    if not retryable:
        return DeadLetterDecision(True, "non_retryable")
    if attempts >= max_attempts:
        return DeadLetterDecision(True, "attempts_exhausted")
    return DeadLetterDecision(False, "retry")
