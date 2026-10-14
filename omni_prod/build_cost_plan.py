"""M5 remediation: one conservative cost plan per durable build.

Before credits are reserved, every variable cost the Build Contract requires
is priced together:

  total_authorized_variable_usd =
      LLM maximum (whole-build external model budget)
    + required paid capability maxima (same router the worker uses)
    + generated-app infrastructure provisioning maxima (LIVE bindings reuse at 0)
    + platform infrastructure maximum (operator setting, if any)
    + retry reserve

Rules:
* The Build Contract's capability plan decides what is required. Optional
  capabilities without an assignment are not priced (and will not run).
* An unknown required quote is never invented: ``CostQuoteUnknown`` blocks the
  build before any reservation. It subclasses PermissionError so existing API
  handlers map it to 402 like other authorization failures.
* The full total is reserved once, durably, before anything is enqueued.
  No later, separate reservation exists for image/media.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Iterable, Mapping, Sequence

from .capability_worker import DEFAULT_NATIVE_BUILD_CAPABILITIES
from .provider_contracts import ProviderQuote
from .provider_pricing import BuildEconomicsQuote, aggregate_build_quote

__all__ = ["BuildCostInputs", "CostQuoteUnknown", "build_economics_quote", "collect_build_cost_inputs",
           "reserve_and_enqueue"]

_ZERO = Decimal("0")


class CostQuoteUnknown(PermissionError):
    def __init__(self, unknown: Sequence[str]) -> None:
        self.unknown = tuple(unknown)
        super().__init__("required cost quote is unknown; build not authorized: " + "; ".join(self.unknown))


@dataclass(frozen=True)
class BuildCostInputs:
    capability_quotes: tuple[tuple[str, str, ProviderQuote], ...]   # (requirement_id, key, quote)
    skipped_optional: tuple[str, ...]
    infrastructure: tuple[tuple[str, Decimal, Decimal, str], ...]    # (kind, est, max, basis)

    @property
    def capability_maximum_usd(self) -> Decimal:
        return sum((q.maximum_cost_usd for _, _, q in self.capability_quotes), _ZERO)

    @property
    def infrastructure_estimated_usd(self) -> Decimal:
        return sum((e for _, e, _, _ in self.infrastructure), _ZERO)

    @property
    def infrastructure_maximum_usd(self) -> Decimal:
        return sum((m for _, _, m, _ in self.infrastructure), _ZERO)


def collect_build_cost_inputs(
    contract,
    *,
    capability_assignments: Mapping[str, Any],
    infrastructure_quotes: Iterable[Any] | None,
    require_capability_quotes: bool = False,
    require_infrastructure_quotes: bool = False,
    native_keys: Iterable[str] = DEFAULT_NATIVE_BUILD_CAPABILITIES,
) -> BuildCostInputs:
    native = set(native_keys)
    unknown: list[str] = []
    priced: list[tuple[str, str, ProviderQuote]] = []
    skipped: list[str] = []
    for requirement in contract.capability_plan.requirements:
        if requirement.key in native:
            continue
        assignment = capability_assignments.get(requirement.id)
        if assignment is None:
            if requirement.required and require_capability_quotes:
                unknown.append(f"capability {requirement.key} has no configured provider quote")
            elif not requirement.required:
                skipped.append(requirement.id)
            continue
        quote = assignment.quote
        if quote.capability_key != requirement.key:
            raise ValueError("capability quote does not match its requirement")
        priced.append((requirement.id, requirement.key, quote))

    infra: list[tuple[str, Decimal, Decimal, str]] = []
    quoted_kinds = set()
    for quote in infrastructure_quotes or ():
        kind = getattr(quote.kind, "value", quote.kind)
        quoted_kinds.add(kind)
        maximum = getattr(quote, "provisioning_maximum_usd", None)
        if maximum is None:
            unknown.append(f"infrastructure {kind} provisioning cost is unknown ({quote.basis})")
            continue
        estimate = getattr(quote, "provisioning_estimated_usd", None)
        infra.append((kind, maximum if estimate is None else estimate, maximum, quote.basis))
    if require_infrastructure_quotes:
        for requirement in contract.infrastructure:
            # SELF_CONTAINED kinds are embedded in the generated app: nothing is
            # provisioned, so there is no provisioning cost to quote (#27).
            if getattr(requirement, "connection_mode", "PLATFORM_MANAGED") == "SELF_CONTAINED":
                continue
            if requirement.required and requirement.kind not in quoted_kinds:
                unknown.append(f"infrastructure {requirement.kind} has no quote")
    if unknown:
        raise CostQuoteUnknown(unknown)
    return BuildCostInputs(tuple(priced), tuple(skipped), tuple(infra))


def build_economics_quote(
    *,
    llm_quotes: Sequence[ProviderQuote],
    cost_inputs: BuildCostInputs | None,
    platform_infrastructure_estimated_usd: Decimal,
    platform_infrastructure_maximum_usd: Decimal,
    retry_reserve_usd: Decimal,
    revenue_usd: Decimal | None,
    minimum_margin: Decimal | None,
) -> tuple[BuildEconomicsQuote, dict]:
    inputs = cost_inputs or BuildCostInputs((), (), ())
    capability_quotes = tuple(q for _, _, q in inputs.capability_quotes)
    quote = aggregate_build_quote(
        provider_quotes=tuple(llm_quotes) + capability_quotes,
        infrastructure_estimated_usd=Decimal(platform_infrastructure_estimated_usd) + inputs.infrastructure_estimated_usd,
        infrastructure_maximum_usd=Decimal(platform_infrastructure_maximum_usd) + inputs.infrastructure_maximum_usd,
        retry_reserve_usd=Decimal(retry_reserve_usd),
        revenue_usd=revenue_usd,
        minimum_margin=minimum_margin,
    )
    llm_max = sum((q.maximum_cost_usd for q in llm_quotes), _ZERO)
    components = {
        "llm_maximum_usd": str(llm_max),
        "capability_maximum_usd": str(inputs.capability_maximum_usd),
        "capability_authorization_usd": str(inputs.capability_maximum_usd),
        "capabilities": [
            {"requirement_id": rid, "capability_key": key, "provider": q.provider,
             "estimated_cost_usd": str(q.estimated_cost_usd), "maximum_cost_usd": str(q.maximum_cost_usd),
             "pricing_version": q.pricing_version}
            for rid, key, q in inputs.capability_quotes
        ],
        "skipped_optional_capabilities": list(inputs.skipped_optional),
        "generated_app_infrastructure_maximum_usd": str(inputs.infrastructure_maximum_usd),
        "generated_app_infrastructure": [
            {"kind": kind, "estimated_usd": str(e), "maximum_usd": str(m), "basis": basis}
            for kind, e, m, basis in inputs.infrastructure
        ],
        "platform_infrastructure_maximum_usd": str(Decimal(platform_infrastructure_maximum_usd)),
        "retry_reserve_usd": str(Decimal(retry_reserve_usd)),
        "reservation_usd": str(quote.total_authorized_variable_usd),
        "rule": "one durable reservation of the full conservative total before any paid external effect",
    }
    return quote, components


def reserve_and_enqueue(*, quote: BuildEconomicsQuote, reserve: Callable[[Decimal], Any], enqueue: Callable[[], Any]):
    """Reserve the whole conservative total; enqueue only after it succeeded."""
    decision = reserve(quote.total_authorized_variable_usd)
    if not getattr(decision, "allowed", False):
        raise PermissionError(getattr(decision, "reason", "reservation denied"))
    enqueue()
    return decision
