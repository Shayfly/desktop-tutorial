from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable

from .capabilities import CapabilityRequirement
from .provider_contracts import ProviderQuote


class PriceStatus(str, Enum):
    PUBLIC_LIST_PRICE = "PUBLIC_LIST_PRICE"
    NEGOTIATED_CONTRACT = "NEGOTIATED_CONTRACT"
    VOLUME_TIER = "VOLUME_TIER"
    CUSTOMER_PAYS_DIRECTLY = "CUSTOMER_PAYS_DIRECTLY"
    UNKNOWN_NOT_APPROVED = "UNKNOWN_NOT_APPROVED"


@dataclass(frozen=True)
class ProviderPriceEntry:
    provider: str
    capability_key: str
    operation: str
    unit_name: str
    estimated_unit_cost_usd: Decimal | None
    maximum_unit_cost_usd: Decimal | None
    status: PriceStatus
    effective_from: str
    effective_to: str | None = None
    source_reference: str | None = None

    def __post_init__(self) -> None:
        for name in ("provider", "capability_key", "operation", "unit_name", "effective_from"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        if self.estimated_unit_cost_usd is not None and self.estimated_unit_cost_usd < 0:
            raise ValueError("estimated_unit_cost_usd must be >= 0")
        if self.maximum_unit_cost_usd is not None and self.maximum_unit_cost_usd < 0:
            raise ValueError("maximum_unit_cost_usd must be >= 0")
        if (
            self.estimated_unit_cost_usd is not None
            and self.maximum_unit_cost_usd is not None
            and self.maximum_unit_cost_usd < self.estimated_unit_cost_usd
        ):
            raise ValueError("maximum_unit_cost_usd must be >= estimated_unit_cost_usd")
        if self.status == PriceStatus.UNKNOWN_NOT_APPROVED:
            if self.estimated_unit_cost_usd is not None or self.maximum_unit_cost_usd is not None:
                raise ValueError("UNKNOWN_NOT_APPROVED entries must not carry guessed prices")
        elif self.status != PriceStatus.CUSTOMER_PAYS_DIRECTLY:
            if self.estimated_unit_cost_usd is None or self.maximum_unit_cost_usd is None:
                raise ValueError("approved provider prices require estimate and maximum")


class ProviderPriceCatalog:
    def __init__(self, *, version: str, entries: Iterable[ProviderPriceEntry]) -> None:
        if not version.strip():
            raise ValueError("price catalog version must not be empty")
        self.version = version
        self._entries: dict[tuple[str, str, str], ProviderPriceEntry] = {}
        for entry in entries:
            key = (entry.provider, entry.capability_key, entry.operation)
            if key in self._entries:
                raise ValueError(f"duplicate provider price entry: {key}")
            self._entries[key] = entry

    def get(self, *, provider: str, capability_key: str, operation: str | None = None) -> ProviderPriceEntry:
        if operation is None:
            matches = [entry for (p, c, _), entry in self._entries.items() if p == provider and c == capability_key]
            if len(matches) == 1:
                return matches[0]
            if not matches:
                raise LookupError(f"no price entry for {provider}/{capability_key}")
            raise LookupError(f"multiple price operations for {provider}/{capability_key}; operation is required")
        key = (provider, capability_key, operation)
        try:
            return self._entries[key]
        except KeyError as exc:
            raise LookupError(f"no price entry for {provider}/{capability_key}/{operation}") from exc

    def quote(
        self,
        *,
        provider: str,
        requirement: CapabilityRequirement,
        operation: str | None = None,
        units: Decimal | None = None,
    ) -> ProviderQuote:
        entry = self.get(provider=provider, capability_key=requirement.key, operation=operation)
        if entry.status == PriceStatus.UNKNOWN_NOT_APPROVED:
            raise RuntimeError(
                f"provider price is {PriceStatus.UNKNOWN_NOT_APPROVED.value}: "
                f"{provider}/{requirement.key}/{entry.operation}"
            )
        resolved_units = Decimal(requirement.quantity) if units is None else Decimal(units)
        if resolved_units < 0:
            raise ValueError("units must be >= 0")
        if entry.status == PriceStatus.CUSTOMER_PAYS_DIRECTLY:
            estimated = Decimal("0")
            maximum = Decimal("0")
        else:
            assert entry.estimated_unit_cost_usd is not None
            assert entry.maximum_unit_cost_usd is not None
            estimated = entry.estimated_unit_cost_usd * resolved_units
            maximum = entry.maximum_unit_cost_usd * resolved_units
        return ProviderQuote(
            provider=provider,
            capability_key=requirement.key,
            estimated_cost_usd=estimated,
            maximum_cost_usd=maximum,
            pricing_version=self.version,
            unit_name=entry.unit_name,
            units=resolved_units,
        )

    def public_snapshot(self) -> dict:
        entries = []
        for key in sorted(self._entries):
            entry = self._entries[key]
            entries.append({
                "provider": entry.provider,
                "capability_key": entry.capability_key,
                "operation": entry.operation,
                "unit_name": entry.unit_name,
                "status": entry.status.value,
                "effective_from": entry.effective_from,
                "effective_to": entry.effective_to,
            })
        return {"version": self.version, "currency": "USD", "entries": entries}



@dataclass(frozen=True)
class BuildEconomicsQuote:
    provider_estimated_usd: Decimal
    provider_maximum_usd: Decimal
    infrastructure_estimated_usd: Decimal
    infrastructure_maximum_usd: Decimal
    retry_reserve_usd: Decimal
    total_estimated_variable_usd: Decimal
    total_authorized_variable_usd: Decimal
    pricing_versions: tuple[str, ...]
    revenue_usd: Decimal | None
    minimum_margin: Decimal | None
    conservative_contribution_usd: Decimal | None
    conservative_margin: Decimal | None
    margin_floor_passed: bool | None

    def __post_init__(self) -> None:
        numeric = (
            self.provider_estimated_usd, self.provider_maximum_usd,
            self.infrastructure_estimated_usd, self.infrastructure_maximum_usd,
            self.retry_reserve_usd, self.total_estimated_variable_usd,
            self.total_authorized_variable_usd,
        )
        if any(Decimal(v) < 0 for v in numeric):
            raise ValueError("build economics costs must be non-negative")
        if self.provider_maximum_usd < self.provider_estimated_usd:
            raise ValueError("provider maximum must cover estimate")
        if self.infrastructure_maximum_usd < self.infrastructure_estimated_usd:
            raise ValueError("infrastructure maximum must cover estimate")
        if self.revenue_usd is not None and self.revenue_usd < 0:
            raise ValueError("revenue_usd must be non-negative")
        if self.minimum_margin is not None and not Decimal("-1") <= self.minimum_margin <= Decimal("1"):
            raise ValueError("minimum_margin must be between -1 and 1")

    def to_dict(self) -> dict:
        return {
            "provider_estimated_usd": str(self.provider_estimated_usd),
            "provider_maximum_usd": str(self.provider_maximum_usd),
            "infrastructure_estimated_usd": str(self.infrastructure_estimated_usd),
            "infrastructure_maximum_usd": str(self.infrastructure_maximum_usd),
            "retry_reserve_usd": str(self.retry_reserve_usd),
            "total_estimated_variable_usd": str(self.total_estimated_variable_usd),
            "total_authorized_variable_usd": str(self.total_authorized_variable_usd),
            "pricing_versions": list(self.pricing_versions),
            "revenue_usd": None if self.revenue_usd is None else str(self.revenue_usd),
            "minimum_margin": None if self.minimum_margin is None else str(self.minimum_margin),
            "conservative_contribution_usd": None if self.conservative_contribution_usd is None else str(self.conservative_contribution_usd),
            "conservative_margin": None if self.conservative_margin is None else str(self.conservative_margin),
            "margin_floor_passed": self.margin_floor_passed,
            "cost_truth": "CONSERVATIVE_MAXIMUM",
        }


def aggregate_build_quote(
    *,
    provider_quotes: Iterable[ProviderQuote],
    infrastructure_estimated_usd: Decimal = Decimal("0"),
    infrastructure_maximum_usd: Decimal = Decimal("0"),
    retry_reserve_usd: Decimal = Decimal("0"),
    revenue_usd: Decimal | None = None,
    minimum_margin: Decimal | None = None,
) -> BuildEconomicsQuote:
    quotes = tuple(provider_quotes)
    infra_est = Decimal(infrastructure_estimated_usd)
    infra_max = Decimal(infrastructure_maximum_usd)
    retry = Decimal(retry_reserve_usd)
    if infra_est < 0 or infra_max < 0 or retry < 0:
        raise ValueError("build economics inputs must be non-negative")
    if infra_max < infra_est:
        raise ValueError("infrastructure maximum must cover estimate")
    provider_est = sum((Decimal(q.estimated_cost_usd) for q in quotes), Decimal("0"))
    provider_max = sum((Decimal(q.maximum_cost_usd) for q in quotes), Decimal("0"))
    total_est = provider_est + infra_est
    total_max = provider_max + infra_max + retry
    revenue = None if revenue_usd is None else Decimal(revenue_usd)
    min_margin = None if minimum_margin is None else Decimal(minimum_margin)
    contribution = None
    margin = None
    passed = None
    if revenue is not None:
        if revenue < 0:
            raise ValueError("revenue_usd must be non-negative")
        contribution = revenue - total_max
        margin = None if revenue == 0 else contribution / revenue
        if min_margin is not None:
            passed = False if margin is None else margin >= min_margin
    versions = tuple(sorted({q.pricing_version for q in quotes}))
    return BuildEconomicsQuote(
        provider_estimated_usd=provider_est,
        provider_maximum_usd=provider_max,
        infrastructure_estimated_usd=infra_est,
        infrastructure_maximum_usd=infra_max,
        retry_reserve_usd=retry,
        total_estimated_variable_usd=total_est,
        total_authorized_variable_usd=total_max,
        pricing_versions=versions,
        revenue_usd=revenue,
        minimum_margin=min_margin,
        conservative_contribution_usd=contribution,
        conservative_margin=margin,
        margin_floor_passed=passed,
    )


def enforce_margin_floor(quote: BuildEconomicsQuote) -> BuildEconomicsQuote:
    if quote.revenue_usd is None or quote.minimum_margin is None or quote.margin_floor_passed is None:
        raise PermissionError("build margin gate requires an explicit revenue basis and minimum margin")
    if not quote.margin_floor_passed:
        raise PermissionError(
            f"build variable-cost margin below floor: {quote.conservative_margin} < {quote.minimum_margin}"
        )
    return quote

def validate_live_quote_within_reservation(
    *,
    local_quote: ProviderQuote,
    live_quote: ProviderQuote,
    reserved_maximum_usd: Decimal,
) -> ProviderQuote:
    if live_quote.provider != local_quote.provider or live_quote.capability_key != local_quote.capability_key:
        raise ValueError("live quote identity does not match local quote")
    reserved = Decimal(reserved_maximum_usd)
    if reserved < 0:
        raise ValueError("reserved maximum must be >= 0")
    if live_quote.maximum_cost_usd > reserved:
        raise PermissionError(
            f"live provider quote exceeds durable reservation: {live_quote.maximum_cost_usd} > {reserved}"
        )
    return live_quote


def contribution_evidence(
    *,
    revenue_usd: Decimal,
    actual_provider_cost_usd: Decimal | None,
    conservative_provider_cost_usd: Decimal,
    infra_cost_usd: Decimal = Decimal("0"),
    payment_fee_usd: Decimal = Decimal("0"),
    support_allocation_usd: Decimal = Decimal("0"),
) -> dict:
    values = [revenue_usd, conservative_provider_cost_usd, infra_cost_usd, payment_fee_usd, support_allocation_usd]
    if any(Decimal(v) < 0 for v in values):
        raise ValueError("economics inputs must be non-negative")
    if actual_provider_cost_usd is not None and Decimal(actual_provider_cost_usd) < 0:
        raise ValueError("actual_provider_cost_usd must be non-negative when known")
    provider_cost = (
        Decimal(actual_provider_cost_usd)
        if actual_provider_cost_usd is not None
        else Decimal(conservative_provider_cost_usd)
    )
    contribution = (
        Decimal(revenue_usd)
        - provider_cost
        - Decimal(infra_cost_usd)
        - Decimal(payment_fee_usd)
        - Decimal(support_allocation_usd)
    )
    margin = None if Decimal(revenue_usd) == 0 else contribution / Decimal(revenue_usd)
    return {
        "revenue_usd": Decimal(revenue_usd),
        "provider_cost_usd": provider_cost,
        "provider_cost_truth": "ACTUAL" if actual_provider_cost_usd is not None else "CONSERVATIVE",
        "infra_cost_usd": Decimal(infra_cost_usd),
        "payment_fee_usd": Decimal(payment_fee_usd),
        "support_allocation_usd": Decimal(support_allocation_usd),
        "contribution_usd": contribution,
        "contribution_margin": margin,
    }
