"""Graded fallback (task document step 6, section 9): which references A1 may offer for a category, and what it says
when there are none.

The rule, unchanged from the document:
  distance 0 -- the category itself;
  distance 1 -- its neighbours in appendix B's order;
  distance 2 -- their neighbours;
  no third link. After two links: `weak` + "ללא ייחוס", and the category joins the collect queue.
A link to another vertical is taken only where appendix B marks it `cross_vertical`.

A1 never waits and never fails here: an empty category returns a result that says so, with `attribution` false, and
the queue entry is already written (decision 6). A1 also never reaches the network -- this reads the store only.
"""
from __future__ import annotations

from datetime import datetime

from . import reference_catalog as C

MAX_LINKS = 2


def _rank(distance: int) -> int:
    return distance


def chain(category: str) -> list[tuple[str, int, bool]]:
    """(category, distance, crossed_a_vertical) up to two links, nearest first, each category once."""
    C.check(category)
    out = [(category, 0, False)]
    seen = {category}
    frontier = [(category, False)]
    for distance in (1, 2):
        nxt = []
        for node, crossed in frontier:
            for neighbour, cross in C.neighbours(node):
                if neighbour in seen:
                    continue
                seen.add(neighbour)
                nxt.append((neighbour, crossed or cross))
                out.append((neighbour, distance, crossed or cross))
        frontier = nxt
    return out


def offer_for(store, category: str, *, now: datetime | None = None, brief_id: str | None = None,
              want: int = 3, exclude_cards=frozenset(), skip_categories=frozenset()) -> dict:
    """What A1 may offer for this category.

    {'cards': [...], 'category': <where they came from>, 'distance': 0|1|2, 'cross_vertical': bool,
     'status': 'ok'|'weak', 'attribution': bool, 'collect_requested': 'empty_category'|'weak_category'|None}

    `status: weak` means no reference survived two links: the cards list is empty and the offer carries no
    attribution ("ללא ייחוס"). The caller still offers -- from the component catalogue and the must-have table --
    but never claims a reference it does not have.
    """
    for node, distance, crossed in chain(category):
        if node in skip_categories:            # this customer rejected everything from here (step 7, level 3)
            continue
        cards = [c for c in store.approved_for(node, now=now) if c.card_id not in exclude_cards]
        if cards:
            if distance and C.collectable(category) and not store_has_open(store, category):
                store.request_collect(category, 'empty_category', brief_id)
            return {'cards': cards[:want], 'category': node, 'distance': distance, 'cross_vertical': crossed,
                    'status': 'ok', 'attribution': True,
                    'collect_requested': 'empty_category' if distance else None}
    if C.collectable(category) and not store_has_open(store, category):
        store.request_collect(category, 'weak_category', brief_id)
    return {'cards': [], 'category': category, 'distance': None, 'cross_vertical': False, 'status': 'weak',
            'attribution': False, 'collect_requested': 'weak_category' if C.collectable(category) else None}


def store_has_open(store, category: str) -> bool:
    return any(q['category'] == category for q in store.open_collect_requests())
