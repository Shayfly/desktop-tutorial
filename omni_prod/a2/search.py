"""1.1 search (docs/spec/gemini-a2.md section 3): 30-60 candidates covering the three fallback tiers.

Tier 1: the vertical, Hebrew/Israel. Tier 2: the vertical, any language. Tier 3: the vertical's category (one of the 10
global categories), any language. Offline, the candidates come from a list (`source: "library"`); live Gemini grounding
is not wired here until the cost is approved, and asking for it fails loudly.

The customer's free description is never stored: only its sha256 (the library must not hold a customer's words).
"""
from __future__ import annotations

import hashlib

from .contract import candidate_id, checked, now_z, run_id

MIN_CANDIDATES, MAX_CANDIDATES = 30, 60
TIERS = (1, 2, 3)
_TIER_LANGUAGE = {1: 'he', 2: 'en', 3: 'en'}


class LiveSearchNotEnabled(RuntimeError):
    pass


def from_library(*, vertical: str, category: str, audience: str, style: str, entries: list[tuple[str, int]],
                 description: str | None = None, at: str | None = None) -> dict:
    """entries: (https url, tier) in rank order. Duplicates count once; above 60 the rest is cut and counted.
    Every tier is queried and recorded, also when it returned nothing (a tier with 0 is said, not dropped)."""
    at = at or now_z()
    seen, ranked = set(), []
    for url, tier in entries:
        if tier not in TIERS:
            raise ValueError(f'tier must be one of {TIERS}, not {tier!r}')
        if url not in seen:
            seen.add(url)
            ranked.append((url, tier))
    kept, truncated = ranked[:MAX_CANDIDATES], max(0, len(ranked) - MAX_CANDIDATES)
    per_tier = {t: sum(1 for _, x in kept if x == t) for t in TIERS}
    status = 'ok' if len(kept) >= MIN_CANDIDATES and all(per_tier.values()) else 'insufficient'
    inputs = {'audience': audience, 'style': style}
    if description:
        inputs['description_sha256'] = hashlib.sha256(description.encode('utf-8')).hexdigest()
    doc = {'kind': 'search_run', 'run_id': run_id('search', vertical, category, audience, style, at),
           'vertical': vertical, 'category': category, 'inputs': inputs,
           'queries': [{'tier': t, 'language': _TIER_LANGUAGE[t],
                        'returned': sum(1 for _, x in ranked if x == t)} for t in TIERS],
           'candidates': [{'candidate_id': candidate_id(u), 'url': u, 'tier': t, 'source': 'library'} for u, t in kept],
           'coverage': {'tier1': per_tier[1], 'tier2': per_tier[2], 'tier3': per_tier[3], 'status': status},
           'at': at}
    if truncated:
        doc['truncated'] = truncated
    return checked(doc)


def live(**_kw):
    raise LiveSearchNotEnabled('live search (Gemini grounding) is not enabled: it waits for the cost decision '
                               '(docs/spec/gemini-a2.md sections 7-8)')
