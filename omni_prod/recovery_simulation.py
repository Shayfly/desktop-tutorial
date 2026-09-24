from __future__ import annotations
from .circuit_breaker import CircuitBreaker, CircuitPolicy, CircuitState
from .dead_letter import decide_dead_letter
from .outbox import new_event
from .worker_lease import renew, can_claim

def run_recovery_simulation() -> dict:
    event = new_event(
        topic="build.ready",
        aggregate_id="b1",
        payload={"version": "v1"},
    )

    breaker = CircuitBreaker(
        CircuitPolicy(failure_threshold=2, recovery_seconds=10)
    )
    assert breaker.allow(0)
    breaker.failure(0)
    assert breaker.allow(1)
    breaker.failure(1)
    assert breaker.state == CircuitState.OPEN
    assert not breaker.allow(5)
    assert breaker.allow(12)
    breaker.success()
    assert breaker.state == CircuitState.CLOSED

    lease = renew(owner="w1", now=0, ttl_seconds=10)
    assert not can_claim(lease, now=5, owner="w2")
    assert can_claim(lease, now=11, owner="w2")

    dead = decide_dead_letter(
        attempts=3, max_attempts=3, retryable=True
    )
    assert dead.dead_letter

    return {
        "event_dedupe": event.dedupe_key,
        "circuit": "closed",
        "lease_recovered": True,
        "dead_letter_reason": dead.reason,
    }
