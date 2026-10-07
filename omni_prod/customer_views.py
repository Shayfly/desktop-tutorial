"""Customer-facing views: internal unit economics never leave the platform
(founder decision 2026-10-07 #29, extended to build status, plan view and
modification status).

Customers may see plan, credits/allowance, usage consumed/remaining,
customer-facing limits, add-on prices, build status and customer-facing
failure reasons. They never see provider cost, expected/metered/internal cost,
margins or margin floors, provider markup, internal credit value, the internal
QA budget or subsidy, reservation details or the economics policy. Internal
evidence stays complete in the database for internal/admin/finance use.
"""
from __future__ import annotations

import re
from typing import Any

from .pricing import PUBLIC_PLAN_FIELDS

# Whole sections that are internal economics or provider/routing internals.
INTERNAL_SECTIONS = frozenset({
    'economics', 'economics_quote', 'economics_settlement', 'economics_error', 'funding',
    'provider_usage', 'model_route_events', 'model_budget_binding', 'usage',
    'provider_spend_usd', 'provider_spend_basis', 'external_model_calls',
    'estimated_cost_usd', 'maximum_authorized_cost_usd',
})
# Customer-facing plan fields (plan price, allowance, limits) are allowed by
# decision #29 even though some contain words like "price" or "cost"; the
# single source of truth is pricing.PUBLIC_PLAN_FIELDS.
CUSTOMER_FACING_KEYS = frozenset(PUBLIC_PLAN_FIELDS)
# Any key made of these words (underscore-delimited) or ending in _usd.
_INTERNAL_KEY = re.compile(
    r'(?:^|_)(?:cost|costs|spend|margin|margins|budget|revenue|markup|subsidy|reservation|reservations|'
    r'contribution|valuation|price|prices|pricing|quote|quotes|settlement|funding|economics)(?:_|$)|_usd$',
    re.IGNORECASE)


def is_internal_key(key: Any) -> bool:
    k = str(key)
    if k in CUSTOMER_FACING_KEYS:
        return False
    return k in INTERNAL_SECTIONS or bool(_INTERNAL_KEY.search(k))


def strip_internal_economics(value: Any) -> Any:
    """Deep copy of `value` without internal economics keys (recursive)."""
    if isinstance(value, dict):
        return {k: strip_internal_economics(v) for k, v in value.items() if not is_internal_key(k)}
    if isinstance(value, (list, tuple)):
        return [strip_internal_economics(v) for v in value]
    return value


def unpriced_capabilities(unknown: list[str] | tuple[str, ...]) -> list[str]:
    """Customer-safe names from CostQuoteUnknown messages ("capability X ..." /
    "infrastructure Y ..."), without internal pricing bases or settings."""
    names = []
    for message in unknown or ():
        parts = str(message).split()
        if len(parts) >= 2 and parts[0] in ('capability', 'infrastructure'):
            names.append(parts[1])
    return sorted(set(names))
