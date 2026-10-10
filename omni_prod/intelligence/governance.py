"""Catalog governance applied where the worker loads its model catalog
(`model_catalog.parse_model_catalog`), i.e. on the real routing path.

For an entry that points at a managed paid provider API:
  * the price in force comes from the source-backed schedule (`prices`), so an
    announced change (Gemini 3.8 Flash on 2027-01-01) applies on its date even
    if the catalog JSON in WORKER_ENV still carries the old number;
  * no source-backed price -> the route is disabled (fail closed: an unknown
    price is never treated as zero or as "whatever the JSON says");
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


def managed(base_url: str) -> bool:
    return (urlsplit(base_url).hostname or '') in MANAGED_HOSTS


def govern(*, model: str, base_url: str, input_per_million: Decimal, output_per_million: Decimal, when=None) -> Governed:
    notes = []
    life = lifecycle.state(model, when)
    warn = lifecycle.warning(model, when)
    if warn:
        notes.append(warn)
    if not managed(base_url):
        return Governed(input_per_million, output_per_million, life != lifecycle.RETIRED, life, 'catalog (unmanaged host)',
                        tuple(notes))
    row = prices.price_at(model, when)
    enforce = os.getenv('OMNI_PRICE_GOVERNANCE', 'enforce') != 'off'
    if row is None or row.input_per_million is None or row.output_per_million is None:
        notes.append(f'no source-backed token price for {model}')
        return Governed(input_per_million, output_per_million, not enforce and life != lifecycle.RETIRED, life,
                        'catalog (UNVERIFIED)', tuple(notes))
    if (row.input_per_million, row.output_per_million) != (input_per_million, output_per_million):
        notes.append(f'catalog price {input_per_million}/{output_per_million} replaced by schedule '
                     f'{row.input_per_million}/{row.output_per_million} effective {row.effective_from}')
    return Governed(row.input_per_million, row.output_per_million, life != lifecycle.RETIRED, life,
                    f'schedule {row.effective_from} {row.source_url}', tuple(notes))
