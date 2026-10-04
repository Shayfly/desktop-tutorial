from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from typing import Mapping

from .capabilities import CapabilityRequirement
from .provider_contracts import ProviderQuote
from .redis_circuit_breaker import RedisCircuitBreaker, RedisCircuitPolicy


@dataclass(frozen=True)
class CapabilityRoutingPolicy:
    minimum_quality: int = 70
    maximum_cost_usd: Decimal | None = None
    maximum_latency_ms: int | None = None
    required_formats: tuple[str, ...] = ()
    require_commercial_use: bool = True
    allowed_providers: tuple[str, ...] = ()
    denied_providers: tuple[str, ...] = ()
    allow_fallback: bool = True

    def __post_init__(self) -> None:
        if not 0 <= self.minimum_quality <= 100:
            raise ValueError("minimum_quality must be between 0 and 100")
        if self.maximum_cost_usd is not None and self.maximum_cost_usd < 0:
            raise ValueError("maximum_cost_usd must be >= 0")
        if self.maximum_latency_ms is not None and self.maximum_latency_ms < 0:
            raise ValueError("maximum_latency_ms must be >= 0")
        overlap = set(self.allowed_providers) & set(self.denied_providers)
        if overlap:
            raise ValueError(f"providers cannot be both allowed and denied: {sorted(overlap)}")


@dataclass(frozen=True)
class ProviderCandidate:
    provider: str
    quality: int
    latency_ms: int
    quote: ProviderQuote
    health: str
    formats: tuple[str, ...]
    commercial_use: bool

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("candidate provider must not be empty")
        if not 0 <= self.quality <= 100:
            raise ValueError("candidate quality must be between 0 and 100")
        if self.latency_ms < 0:
            raise ValueError("candidate latency_ms must be >= 0")


@dataclass(frozen=True)
class ProviderSelection:
    candidate: ProviderCandidate
    reason: str
    rejected: tuple[dict, ...]


class CapabilityProviderRouter:
    """Pure deterministic selector. It never performs provider I/O."""

    _BLOCKED_HEALTH = frozenset(
        {"FAILED", "OPEN", "RATE_LIMITED", "QUOTA_EXHAUSTED", "BLOCKED", "UNAVAILABLE"}
    )
    _ELIGIBLE_HEALTH = frozenset({"HEALTHY", "DEGRADED", "OK"})

    def select(
        self,
        *,
        requirement: CapabilityRequirement,
        candidates: tuple[ProviderCandidate, ...],
        policy: CapabilityRoutingPolicy,
    ) -> ProviderSelection:
        eligible: list[ProviderCandidate] = []
        rejected: list[dict] = []

        for candidate in candidates:
            if candidate.quote.provider != candidate.provider:
                raise ValueError(
                    f"quote provider {candidate.quote.provider} does not match candidate {candidate.provider}"
                )
            if candidate.quote.capability_key != requirement.key:
                raise ValueError(
                    f"quote capability {candidate.quote.capability_key} does not match requirement {requirement.key}"
                )

            reason = self._rejection_reason(candidate, policy)
            if reason is None:
                eligible.append(candidate)
            else:
                rejected.append({"provider": candidate.provider, "reason": reason})

        if not eligible:
            raise LookupError(
                f"no eligible provider for {requirement.key}; rejected={rejected}"
            )

        selected = min(
            eligible,
            key=lambda item: (
                item.quote.maximum_cost_usd,
                -item.quality,
                item.latency_ms,
                item.provider,
            ),
        )
        return ProviderSelection(
            candidate=selected,
            reason="eligible provider with lowest conservative maximum cost, then quality, latency and stable name",
            rejected=tuple(rejected),
        )

    def _rejection_reason(
        self,
        candidate: ProviderCandidate,
        policy: CapabilityRoutingPolicy,
    ) -> str | None:
        if policy.allowed_providers and candidate.provider not in policy.allowed_providers:
            return "provider not in allowed list"
        if candidate.provider in policy.denied_providers:
            return "provider denied by policy"

        health = candidate.health.strip().upper()
        if health in self._BLOCKED_HEALTH:
            return f"health state {health} blocks routing"
        if health not in self._ELIGIBLE_HEALTH:
            return f"health state {health or 'EMPTY'} is unknown and fails closed"

        if (
            policy.maximum_cost_usd is not None
            and candidate.quote.maximum_cost_usd > policy.maximum_cost_usd
        ):
            return "conservative maximum cost exceeds policy ceiling"
        if candidate.quality < policy.minimum_quality:
            return "quality below policy minimum"
        if (
            policy.maximum_latency_ms is not None
            and candidate.latency_ms > policy.maximum_latency_ms
        ):
            return "latency exceeds policy maximum"
        if policy.required_formats and not set(policy.required_formats).issubset(candidate.formats):
            return "required output format unavailable"
        if policy.require_commercial_use and not candidate.commercial_use:
            return "commercial-use rights unavailable"
        return None


def parse_retry_after_seconds(value: str | None, *, now: datetime | None = None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        seconds = int(text)
        return seconds if seconds >= 0 else None
    except ValueError:
        pass
    try:
        target = parsedate_to_datetime(text)
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        current = now or datetime.now(timezone.utc)
        return max(0, int((target - current).total_seconds()))
    except (TypeError, ValueError, OverflowError):
        return None


class ProviderQuotaCircuitManager:
    """Provider+capability-scoped distributed quota and failure gate.

    RedisCircuitBreaker already owns cross-instance failure state. This layer
    gives it provider-aware 429/quota semantics and dynamic cooldowns.
    """

    _QUOTA_CODES = frozenset(
        {"quota_exhausted", "insufficient_quota", "credits_exhausted", "billing_hard_limit"}
    )

    def __init__(
        self,
        redis,
        *,
        circuit_policy: RedisCircuitPolicy | None = None,
        default_rate_limit_seconds: int = 60,
        default_quota_seconds: int = 3600,
    ) -> None:
        if default_rate_limit_seconds < 1 or default_quota_seconds < 1:
            raise ValueError("provider cooldown defaults must be >= 1 second")
        self.redis = redis
        self.circuit_policy = circuit_policy or RedisCircuitPolicy()
        self.default_rate_limit_seconds = default_rate_limit_seconds
        self.default_quota_seconds = default_quota_seconds

    def _breaker(self, provider: str, capability_key: str) -> RedisCircuitBreaker:
        if not provider.strip() or not capability_key.strip():
            raise ValueError("provider and capability_key are required")
        return RedisCircuitBreaker(
            self.redis,
            name=f"provider:{provider}:{capability_key}",
            policy=self.circuit_policy,
        )

    def allow(self, provider: str, capability_key: str, *, now: float | None = None) -> bool:
        return self._breaker(provider, capability_key).allow(now=now)

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
        breaker = self._breaker(provider, capability_key)
        normalized_code = (error_code or "").strip().lower()
        if 200 <= status_code < 400:
            breaker.success()
            return

        retry_after_value = next(
            (value for key, value in headers.items() if key.lower() == "retry-after"),
            None,
        )
        retry_after = parse_retry_after_seconds(retry_after_value)

        if normalized_code in self._QUOTA_CODES or status_code == 402:
            breaker.force_open(
                now=now,
                recovery_seconds=max(retry_after or 0, self.default_quota_seconds),
            )
            return
        if status_code == 429:
            breaker.force_open(
                now=now,
                recovery_seconds=retry_after or self.default_rate_limit_seconds,
            )
            return
        if status_code >= 500 or status_code in {408, 409, 425}:
            breaker.failure(now=now)
