"""The editor: a second agent that reviews every proposal before the customer sees it (docs/spec/first-agent.md
section 4, v0.2).

Blocks ONLY on completeness and feasibility (Michael 2026-11-15: price never blocks). A block goes back to the first
agent with its reason -- never to the customer. Excess rows (no content) are removed and said. The price is computed
(price_v0) and shown as an estimate.
"""
from __future__ import annotations

from ..price_v0 import estimate
from .structure import KIND_SECTIONS


def review(cards: list[dict], *, canon, waived: tuple[str, ...] = ()) -> dict:
    """cards: one structure card per product (they stack); one shared price. waived: fact keys the customer chose
    to leave out (e.g. 'hours'), which then do not block."""
    if not cards:
        raise ValueError('a proposal has at least one structure card')
    blocks, removed, kept_cards = [], [], []
    have = {k for k in ('phone', 'address', 'hours', 'email') if canon is not None and canon.values(k)}
    for card in cards:
        allowed = KIND_SECTIONS[card['kind']]
        rows = []
        for row in card['rows']:
            if row['key'] not in allowed:
                blocks.append({'rule': 'feasibility', 'row': row['key'], 'kind': card['kind'],
                               'why': f"a {card['kind']} cannot hold a '{row['key']}' section"})
                continue
            missing = [n for n in row['needs'] if n not in have and n not in waived]
            if missing:
                blocks.append({'rule': 'completeness', 'row': row['key'], 'missing': missing,
                               'why': f"'{row['key']}' needs {', '.join(missing)} from the customer, or a waiver"})
                rows.append(row)
                continue
            if not row['has_content'] and not row['needs']:
                removed.append({'row': row['key'], 'why': 'no content: excess section removed'})
                continue
            rows.append(row)
        kept_cards.append({**card, 'rows': rows})
    sections = sum(len(c['rows']) for c in kept_cards)
    price = estimate(sections=sections, media=any(c.get('media') for c in kept_cards))
    return {'ok': not blocks, 'blocks': blocks, 'removed': removed, 'cards': kept_cards, 'price': price,
            'shown_to_customer': not blocks}
