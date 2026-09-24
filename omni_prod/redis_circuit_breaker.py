from __future__ import annotations
from dataclasses import dataclass
import time

@dataclass(frozen=True)
class RedisCircuitPolicy:
    failure_threshold: int = 5
    recovery_seconds: int = 30

    def __post_init__(self):
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >=1")
        if self.recovery_seconds < 1:
            raise ValueError("recovery_seconds must be >=1")

class RedisCircuitBreaker:
    """
    Distributed breaker using Redis hashes.
    This is cross-instance state. Redis service behavior still requires live
    integration testing before production release.
    """
    def __init__(self, redis, *, name: str, policy: RedisCircuitPolicy):
        if not name or any(c.isspace() for c in name):
            raise ValueError("invalid circuit name")
        self.redis = redis
        self.policy = policy
        self.key = f"omni:circuit:{name}"

    def _state(self) -> tuple[str, int, float]:
        raw = self.redis.hgetall(self.key) or {}
        def get(name, default):
            return raw.get(name.encode(), raw.get(name, default))
        state = get("state", b"closed")
        if isinstance(state, bytes):
            state = state.decode()
        failures = int(get("failures", 0))
        opened_at = float(get("opened_at", 0) or 0)
        return str(state), failures, opened_at

    def allow(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        state, _, opened_at = self._state()
        if state == "closed":
            return True
        if state == "open" and now - opened_at >= self.policy.recovery_seconds:
            # NX probe key permits only one half-open probe across instances.
            probe = self.redis.set(
                f"{self.key}:probe",
                b"1",
                nx=True,
                ex=self.policy.recovery_seconds,
            )
            return bool(probe)
        return False

    def success(self) -> None:
        pipe = self.redis.pipeline()
        pipe.hset(self.key, mapping={
            "state": "closed",
            "failures": 0,
            "opened_at": 0,
        })
        pipe.delete(f"{self.key}:probe")
        pipe.execute()

    def failure(self, now: float | None = None) -> None:
        now = time.time() if now is None else now
        failures = int(self.redis.hincrby(self.key, "failures", 1))
        if failures >= self.policy.failure_threshold:
            self.redis.hset(self.key, mapping={
                "state": "open",
                "opened_at": now,
            })
            self.redis.delete(f"{self.key}:probe")
