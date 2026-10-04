"""M5 Task 8: normalized, provider-reported LLM usage.

``ProviderUsage`` records what a model provider *reported* for one call:
token counts, cached tokens, the provider's own cost figure if it gave one,
and the request identity needed to reconcile against the provider's bill.

Truth rules:

* Nothing here is ever derived from an estimate. ``source`` can only be
  ``provider_response``; constructing usage from an estimate is rejected.
* A field the provider did not report stays ``None`` -- never 0.
* ``provider_reported_cost_usd`` is only the provider's explicit number.
* The ledger de-duplicates by provider request identity so re-recording the
  same call (redelivery, retry of the evidence write) never double counts.
* Actual external cost is known only when *every* authorized external call
  left a usage record with a provider-reported cost; otherwise it is None.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping
import uuid

__all__ = ["ProviderUsage", "ProviderUsageLedger", "parse_openai_compatible_usage"]

_REQUEST_ID_HEADERS = ("x-request-id", "request-id", "openai-request-id", "x-amzn-requestid", "cf-ray")


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)
    return None


def _cost(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite() or amount < 0:
        return None
    return amount


def _header(headers: Any, name: str) -> str | None:
    if headers is None:
        return None
    getter = getattr(headers, "get", None)
    if getter is None:
        return None
    for candidate in (name, name.title(), name.upper()):
        value = getter(candidate)
        if value:
            return str(value).strip() or None
    if isinstance(headers, Mapping):
        for key, value in headers.items():
            if str(key).lower() == name and value:
                return str(value).strip() or None
    return None


@dataclass(frozen=True)
class ProviderUsage:
    provider: str
    model: str
    external: bool
    request_id: str | None
    request_id_source: str | None
    response_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    cached_tokens: int | None
    provider_reported_cost_usd: Decimal | None
    usage_reported: bool
    source: str = "provider_response"
    usage_key: str = field(default="")

    def __post_init__(self) -> None:
        if self.source != "provider_response":
            raise ValueError("ProviderUsage can only come from a provider response, never an estimate")
        if not str(self.provider).strip() or not str(self.model).strip():
            raise ValueError("provider and model identity are required")
        for name in ("input_tokens", "output_tokens", "cached_tokens"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError(f"{name} must be a non-negative integer or None")
        if self.provider_reported_cost_usd is not None:
            if not isinstance(self.provider_reported_cost_usd, Decimal) or self.provider_reported_cost_usd < 0:
                raise ValueError("provider_reported_cost_usd must be a non-negative Decimal or None")
        if not self.usage_key:
            identity = self.request_id or self.response_id
            key = (f"{self.provider}\0{identity}" if identity
                   # No provider identity: a fresh key, so distinct calls are never merged.
                   else f"{self.provider}\0anon-{uuid.uuid4().hex}")
            object.__setattr__(self, "usage_key", key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider, "model": self.model, "external": self.external,
            "request_id": self.request_id, "request_id_source": self.request_id_source,
            "response_id": self.response_id, "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens, "cached_tokens": self.cached_tokens,
            "provider_reported_cost_usd": (None if self.provider_reported_cost_usd is None
                                           else str(self.provider_reported_cost_usd)),
            "usage_reported": self.usage_reported, "source": self.source,
        }


def parse_openai_compatible_usage(payload: Any, headers: Any, *, provider: str, model: str,
                                  external: bool) -> ProviderUsage:
    """Normalize an OpenAI-compatible (or Anthropic-style) response's usage block."""
    data = payload if isinstance(payload, Mapping) else {}
    usage = data.get("usage") if isinstance(data.get("usage"), Mapping) else None
    request_id, request_id_source = None, None
    for name in _REQUEST_ID_HEADERS:
        value = _header(headers, name)
        if value:
            request_id, request_id_source = value, f"header:{name}"
            break
    response_id = str(data.get("id")).strip() if data.get("id") else None
    if request_id is None and response_id:
        request_id, request_id_source = response_id, "response_id"

    input_tokens = output_tokens = cached_tokens = None
    cost = None
    if usage is not None:
        input_tokens = _non_negative_int(usage.get("prompt_tokens", usage.get("input_tokens")))
        output_tokens = _non_negative_int(usage.get("completion_tokens", usage.get("output_tokens")))
        details = usage.get("prompt_tokens_details")
        if isinstance(details, Mapping) and "cached_tokens" in details:
            cached_tokens = _non_negative_int(details.get("cached_tokens"))
        elif "cache_read_input_tokens" in usage:
            cached_tokens = _non_negative_int(usage.get("cache_read_input_tokens"))
        elif "cached_tokens" in usage:
            cached_tokens = _non_negative_int(usage.get("cached_tokens"))
        cost = _cost(usage.get("cost", usage.get("total_cost")))

    return ProviderUsage(
        provider=provider, model=model, external=external, request_id=request_id,
        request_id_source=request_id_source, response_id=response_id,
        input_tokens=input_tokens, output_tokens=output_tokens, cached_tokens=cached_tokens,
        provider_reported_cost_usd=cost, usage_reported=usage is not None,
    )


class ProviderUsageLedger:
    """Per-build, de-duplicated collection of provider-reported usage."""

    def __init__(self, events: Iterable[ProviderUsage] = ()) -> None:
        self._events: dict[str, ProviderUsage] = {}
        for event in events:
            self.record(event)

    def record(self, usage: ProviderUsage | None) -> bool:
        if usage is None:
            return False
        if usage.usage_key in self._events:
            return False
        self._events[usage.usage_key] = usage
        return True

    def events(self) -> tuple[ProviderUsage, ...]:
        return tuple(self._events.values())

    @property
    def last(self) -> ProviderUsage | None:
        return next(reversed(self._events.values()), None) if self._events else None

    def actual_external_cost_usd(self, *, authorized_external_calls: int) -> Decimal | None:
        external = [e for e in self._events.values() if e.external]
        if authorized_external_calls <= 0:
            return Decimal("0") if not external else None
        if len(external) != authorized_external_calls:
            return None
        if any(e.provider_reported_cost_usd is None for e in external):
            return None
        return sum((e.provider_reported_cost_usd for e in external), Decimal("0"))

    def summary(self, *, authorized_external_calls: int, authorized_estimate_usd: Decimal | None = None) -> dict:
        events = self.events()

        def total(name: str) -> int | None:
            values = [getattr(e, name) for e in events]
            if not values or any(v is None for v in values):
                return None
            return sum(values)

        actual = self.actual_external_cost_usd(authorized_external_calls=authorized_external_calls)
        external_events = [e for e in events if e.external]
        if authorized_external_calls == 0:
            basis = "NO_EXTERNAL_CALLS"
        elif actual is not None:
            basis = "PROVIDER_REPORTED"
        elif len(external_events) != authorized_external_calls:
            basis = "UNKNOWN_AUTHORIZED_CALLS_WITHOUT_USAGE"
        else:
            basis = "UNKNOWN_PROVIDER_DID_NOT_REPORT_COST"
        return {
            "usage_events": [e.to_dict() for e in events],
            "request_ids": [e.request_id for e in events if e.request_id],
            "input_tokens": total("input_tokens"),
            "output_tokens": total("output_tokens"),
            "cached_tokens": total("cached_tokens"),
            "authorized_external_calls": authorized_external_calls,
            "external_usage_records": len(external_events),
            "actual_cost_usd": None if actual is None else str(actual),
            "actual_cost_basis": basis,
            "authorized_estimate_usd": None if authorized_estimate_usd is None else str(authorized_estimate_usd),
            "truth_note": "actual_cost_usd is provider-reported or null; authorized_estimate_usd is a budget ledger, not a cost.",
        }
