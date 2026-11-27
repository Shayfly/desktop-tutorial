"""Catalog governance applied where the worker loads its model catalog
(`model_catalog.parse_model_catalog`), i.e. on the real routing path.

For an entry that points at a managed paid provider API:
  * the price in force comes from the source-backed schedule (`prices`), so an
    announced change (Gemini 3.8 Flash on 2027-01-01) applies on its date even
    if the catalog JSON in WORKER_ENV still carries the old number;
  * no source-backed price -> until 2026-11-26 the route was disabled; since the
    owner's word of that day it stays routable with price_known False: an
    unknown price is still never treated as zero or as "whatever the JSON
    says" -- its calls are recorded with their tokens and an UNKNOWN cost;
  * a RETIRED model is disabled; an announced retirement adds a warning.
Entries for other hosts (self-hosted, test doubles) keep their catalog price.

OMNI_PRICE_GOVERNANCE=off disables the fail-closed rule (diagnostics only);
it is never set on the worker.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlsplit

from . import lifecycle, prices

MANAGED_HOSTS = {
    'generativelanguage.googleapis.com': 'gemini',
    'api.openai.com': 'openai',
    'api.anthropic.com': 'anthropic',
}


@dataclass(frozen=True)
class Governed:
    input_per_million: Decimal
    output_per_million: Decimal
    routable: bool
    lifecycle: str
    price_source: str
    notes: tuple[str, ...] = ()
    # The owner 2026-11-26: False when no trusted price exists. The route is NOT disabled for it any more (a missing
    # price never leaves a model out of a build); its calls are recorded with their tokens and an unknown cost.
    price_known: bool = True


def managed(base_url: str) -> bool:
    return (urlsplit(base_url).hostname or '') in MANAGED_HOSTS


def govern(*, model: str, base_url: str, input_per_million: Decimal, output_per_million: Decimal, when=None,
           catalog_price_known: bool = True) -> Governed:
    """`catalog_price_known` False: the catalog entry carries no price at all (its two numbers are a stand-in)."""
    notes = []
    life = lifecycle.state(model, when)
    warn = lifecycle.warning(model, when)
    if warn:
        notes.append(warn)
    if not managed(base_url):
        if not catalog_price_known:
            notes.append(f'no price for {model} in the catalog: its cost is recorded as unknown')
            return Governed(input_per_million, output_per_million, life != lifecycle.RETIRED, life,
                            'none (no price in the catalog)', tuple(notes), price_known=False)
        return Governed(input_per_million, output_per_million, life != lifecycle.RETIRED, life, 'catalog (unmanaged host)',
                        tuple(notes))
    row = prices.price_at(model, when)
    enforce = os.getenv('OMNI_PRICE_GOVERNANCE', 'enforce') != 'off'
    if row is None or row.input_per_million is None or row.output_per_million is None:
        notes.append(f'no source-backed token price for {model}')
        # The owner 2026-11-26 ("לא מחייב אם אין לנו את כל הנתונים ... אבל לעדכן"): the route stays; the catalog's own
        # number is not trusted, so the cost of its calls is unknown (price_known False) unless governance is off.
        return Governed(input_per_million, output_per_million, life != lifecycle.RETIRED, life,
                        'catalog (UNVERIFIED)', tuple(notes),
                        price_known=(not enforce) and catalog_price_known)
    if (row.input_per_million, row.output_per_million) != (input_per_million, output_per_million):
        notes.append(f'catalog price {input_per_million}/{output_per_million} replaced by schedule '
                     f'{row.input_per_million}/{row.output_per_million} effective {row.effective_from}')
    return Governed(row.input_per_million, row.output_per_million, life != lifecycle.RETIRED, life,
                    f'schedule {row.effective_from} {row.source_url}', tuple(notes))
