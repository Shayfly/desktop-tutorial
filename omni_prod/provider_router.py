from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
import time
from typing import Mapping, Sequence

from .capabilities import CapabilityRequirement
from .provider_contracts import ProviderQuote
from .redis_circuit_breaker import RedisCircuitBreaker, RedisCircuitPolicy


@dataclass(frozen=True)
class ProviderCandidate:
    provider: str
    quality: int
    latency_ms: int
    quote: ProviderQuote
    health: str
    output_formats: tuple[str, ...]
    commercial_use: bool

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must not be empty")
        if not 0 <= self.quality <= 100:
            raise ValueError("quality must be between 0 and 100")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")


@dataclass(frozen=True)
class CapabilityRoutingPolicy:
    minimum_quality: int = 0
    maximum_cost_usd: Decimal | None = None
    maximum_latency_ms: int | None = None
    required_formats: tuple[str, ...] = ()
    require_commercial_use: bool = True
    allowed_providers: tuple[str, ...] = ()
    denied_providers: tuple[str, ...] = ()
    healthy_states: tuple[str, ...] = ("HEALTHY", "DEGRADED")


@dataclass(frozen=True)
class ProviderSelection:
    candidate: ProviderCandidate
    rejected: tuple[Mapping[str, str], ...] = field(default_factory=tuple)


class CapabilityProviderRouter:
    """Deterministic hard-policy router for already-priced candidates.

    It deliberately does not call provider.quote(). Quotes are supplied by the
    local price-catalog / authorized quote stage so routing itself cannot cause
    unreserved paid network work.
    """

    def select(
        self,
        *,
        requirement: CapabilityRequirement,
        candidates: Sequence[ProviderCandidate],
        policy: CapabilityRoutingPolicy,
    ) -> ProviderSelection:
        rejected: list[dict[str, str]] = []
        eligible: list[ProviderCandidate] = []
        allowed = set(policy.allowed_providers)
        denied = set(policy.denied_providers)
        required_formats = set(policy.required_formats)

        for candidate in candidates:
            if candidate.quote.provider != candidate.provider:
                raise ValueError(
                    f"quote provider mismatch for {candidate.provider}: {candidate.quote.provider}"
                )
            if candidate.quote.capability_key != requirement.key:
                raise ValueError(
                    f"quote capability mismatch: expected {requirement.key}, "
                    f"got {candidate.quote.capability_key}"
                )

            reason: str | None = None
            if allowed and candidate.provider not in allowed:
                reason = "provider not in allowed list"
            elif candidate.provider in denied:
                reason = "provider denied by policy"
            elif candidate.health not in policy.healthy_states:
                reason = f"health state {candidate.health} is not eligible"
            elif candidate.quality < policy.minimum_quality:
                reason = "quality below minimum"
            elif (
                policy.maximum_cost_usd is not None
                and candidate.quote.maximum_cost_usd > policy.maximum_cost_usd
            ):
                reason = "cost exceeds maximum"
            elif (
                policy.maximum_latency_ms is not None
                and candidate.latency_ms > policy.maximum_latency_ms
            ):
                reason = "latency exceeds maximum"
            elif required_formats and not required_formats.issubset(set(candidate.output_formats)):
                reason = "required format unavailable"
            elif policy.require_commercial_use and not candidate.commercial_use:
                reason = "commercial use not permitted"

            if reason is not None:
                rejected.append({"provider": candidate.provider, "reason": reason})
                continue
            eligible.append(candidate)

        if not eligible:
            raise LookupError("no eligible provider for required capability")

        winner = min(
            eligible,
            key=lambda item: (
                item.quote.maximum_cost_usd,
                -item.quality,
                item.latency_ms,
                item.provider,
            ),
        )
        return ProviderSelection(candidate=winner, rejected=tuple(rejected))


def parse_retry_after_seconds(value: str | None, *, now: float | None = None) -> int | None:
    """Parse Retry-After seconds or HTTP-date, returning a non-negative delay."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        seconds = int(raw)
    except ValueError:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            reference = time.time() if now is None else now
            seconds = int(max(0, dt.timestamp() - reference))
        except (TypeError, ValueError, OverflowError):
            return None
    return seconds if seconds >= 0 else None


class ProviderQuotaCircuitManager:
    """Distributed provider+capability cooldown and failure-circuit state.

    429/quota blocks are tracked independently from transport/server-error
    circuits. This prevents one exhausted capability from becoming a global
    provider outage while still sharing state across worker instances via Redis.
    """

    def __init__(
        self,
        redis,
        *,
        circuit_policy: RedisCircuitPolicy | None = None,
        default_rate_limit_seconds: int = 30,
        default_quota_seconds: int = 3600,
    ) -> None:
        if default_rate_limit_seconds < 1 or default_quota_seconds < 1:
            raise ValueError("cooldown seconds must be >= 1")
        self.redis = redis
        self.circuit_policy = circuit_policy or RedisCircuitPolicy()
        self.default_rate_limit_seconds = default_rate_limit_seconds
        self.default_quota_seconds = default_quota_seconds

    @staticmethod
    def _slug(value: str) -> str:
        return value.replace(" ", "_")

    def _quota_key(self, provider: str, capability_key: str) -> str:
        return f"omni:provider-quota:{self._slug(provider)}:{self._slug(capability_key)}"

    def _breaker(self, provider: str, capability_key: str) -> RedisCircuitBreaker:
        return RedisCircuitBreaker(
            self.redis,
            name=f"provider:{self._slug(provider)}:{self._slug(capability_key)}",
            policy=self.circuit_policy,
        )

    def _blocked_until(self, provider: str, capability_key: str) -> float:
        raw = self.redis.hgetall(self._quota_key(provider, capability_key)) or {}
        value = raw.get(b"blocked_until", raw.get("blocked_until", 0))
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def allow(self, provider: str, capability_key: str, *, now: float | None = None) -> bool:
        reference = time.time() if now is None else now
        if reference < self._blocked_until(provider, capability_key):
            return False
        return self._breaker(provider, capability_key).allow(now=reference)

    def _block(self, provider: str, capability_key: str, *, until: float, reason: str) -> None:
        self.redis.hset(
            self._quota_key(provider, capability_key),
            mapping={"blocked_until": until, "reason": reason},
        )

    def record_http_result(
        self,
        *,
        provider: str,
        capability_key: str,
        status_code: int,
        headers: Mapping[str, str],
        error_code: str | None,
        now: float | None = None,
    ) -> None:
        reference = time.time() if now is None else now
        normalized_error = (error_code or "").lower()

        if 200 <= status_code < 400:
            self._block(provider, capability_key, until=0, reason="")
            self._breaker(provider, capability_key).success()
            return

        if status_code == 429 or normalized_error in {"rate_limit", "rate_limited"}:
            retry_after = parse_retry_after_seconds(headers.get("Retry-After"), now=reference)
            delay = retry_after if retry_after is not None else self.default_rate_limit_seconds
            self._block(
                provider,
                capability_key,
                until=reference + delay,
                reason="rate_limit",
            )
            return

        if normalized_error in {"quota_exhausted", "insufficient_quota", "quota"}:
            self._block(
                provider,
                capability_key,
                until=reference + self.default_quota_seconds,
                reason="quota_exhausted",
            )
            return

        if status_code >= 500 or normalized_error in {
            "server_error",
            "timeout",
            "transport_error",
        }:
            self._breaker(provider, capability_key).failure(now=reference)
