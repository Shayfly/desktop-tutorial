"""Graded rejection, signals and the owner's alert (task document step 7, sections 10-11).

Rejection, three levels -- none of them touches the network:
  1. layer  (palette / font / layout): the same layer from the next card of the same pool.
  2. domain ("this does not look like a butcher"): the next card; the category joins the collect queue
     (`domain_rejected`), so it shows in the status report and never disappears quietly (decision 6).
  3. all: for THIS customer the category is skipped and the fallback goes one link up.
The negative is kept: what a customer rejected is never offered to that customer again.

Signals: `disliked` and `asked_another` are equal. The alert fires when 10 of the last 30 offers of a category were
rejected (counted since the owner's last change), and again every 5 further rejections. The count resets ONLY when
the owner changes something (replaces examples, widens the category) -- never because an alert fired.

Reading of "10 of 30", stated because the document does not define the window: rejections since the owner's last
change, among the offers since then, looking at the most recent 30 offers.
"""
from __future__ import annotations

from datetime import datetime, timezone

from . import reference_fallback as F
from .reference_store import OWNER, ReferenceStoreError

LAYERS = ('palette', 'font', 'layout')
ALERT_REJECTIONS, ALERT_WINDOW_OFFERS, ALERT_REPEAT = 10, 30, 5


def card_key(card_id: str) -> str:
    return f'card:{card_id}'


def layer_key(layer: str, card_id: str) -> str:
    if layer not in LAYERS:
        raise ReferenceStoreError(f'layer is one of {LAYERS}')
    return f'layer:{layer}:{card_id}'


def category_key(category: str) -> str:
    return f'all:{category}'


def _excluded(store, brief_id: str) -> tuple[set[str], set[str]]:
    keys = store.rejected_keys(brief_id)
    return ({k[5:] for k in keys if k.startswith('card:')}, {k[4:] for k in keys if k.startswith('all:')})


def next_offer(store, *, brief_id: str, category: str, now: datetime | None = None, want: int = 3) -> dict:
    """What A1 offers this customer now: the fallback, minus everything this customer already rejected. Every card
    offered is recorded (the alert counts offers)."""
    now = now or datetime.now(timezone.utc)
    cards, skipped = _excluded(store, brief_id)
    out = F.offer_for(store, category, now=now, brief_id=brief_id, want=want, exclude_cards=frozenset(cards),
                      skip_categories=frozenset(skipped))
    for c in out['cards']:
        store.record_offer(brief_id=brief_id, category=category, card_id=c.card_id, at=now)
    return out


def next_layer(store, *, brief_id: str, category: str, layer: str, now: datetime | None = None):
    """The same layer from the next card of the pool this customer has not rejected for that layer; None when the
    pool is used up (the caller then says so -- it never loops back to a rejected one)."""
    now = now or datetime.now(timezone.utc)
    keys = store.rejected_keys(brief_id)
    cards, skipped = _excluded(store, brief_id)
    out = F.offer_for(store, category, now=now, brief_id=brief_id, want=50, exclude_cards=frozenset(cards),
                      skip_categories=frozenset(skipped))
    for c in out['cards']:
        if layer_key(layer, c.card_id) not in keys:
            store.record_offer(brief_id=brief_id, category=category, card_id=c.card_id, component_key=f'layer:{layer}',
                               at=now)
            return c
    return None


def reject(store, *, brief_id: str, category: str, level: str, signal: str, card_id: str | None = None,
           layer: str | None = None, now: datetime | None = None) -> dict:
    """Record one rejection and say what happens next. level: 'layer' | 'domain' | 'all'."""
    now = now or datetime.now(timezone.utc)
    if level == 'layer':
        if not (card_id and layer):
            raise ReferenceStoreError('a layer rejection names the card and the layer')
        key = layer_key(layer, card_id)
    elif level == 'domain':
        if not card_id:
            raise ReferenceStoreError('a domain rejection names the card')
        key = card_key(card_id)
    elif level == 'all':
        key = category_key(category)
    else:
        raise ReferenceStoreError("level is 'layer', 'domain' or 'all'")
    store.record_rejection(brief_id=brief_id, category=category, component_key=key, signal=signal, scope=level, at=now)
    if level == 'domain':
        store.request_collect(category, 'domain_rejected', brief_id)
    return {'key': key, 'alert': check_alert(store, category, now=now)}


# ---------------------------------------------------------------------------------------------------- the alert

def _window_start(store, category: str) -> datetime | None:
    changes = [a['changed_at'] for a in store.alerts_for(category) if a['changed_at'] is not None]
    return max(changes) if changes else None


def check_alert(store, category: str, *, now: datetime | None = None) -> dict | None:
    """Fire (and record) the alert when it is due; None otherwise. Idempotent: the same count never fires twice."""
    now = now or datetime.now(timezone.utc)
    since = _window_start(store, category)
    offers, rejections = store.counts_since(category, since)
    recent_offers = offers[-ALERT_WINDOW_OFFERS:]
    if not recent_offers:
        return None
    in_window = [r for r in rejections if r >= recent_offers[0]]
    fired = [a for a in store.alerts_for(category) if a['changed_at'] is None and a['rejections'] > 0
             and (since is None or a['fired_at'] > since)]
    total = len(rejections)                       # since the owner's last change: this is what "5 more" counts
    if not fired:
        due = len(in_window) >= ALERT_REJECTIONS
    else:
        due = total >= max(a['rejections'] for a in fired) + ALERT_REPEAT
    if not due:
        return None
    alert = {'category': category, 'window_start': since or recent_offers[0], 'rejections': total,
             'offers': len(offers), 'fired_at': now, 'repeat': bool(fired)}
    store.record_alert(category=category, window_start=alert['window_start'], rejections=total, offers=len(offers),
                       at=now)
    return alert


def owner_changed(store, category: str, *, by: str, now: datetime | None = None) -> None:
    """The owner replaced examples or widened the category: the count starts again from here. Only the owner."""
    if by != OWNER:
        raise ReferenceStoreError('only the owner resets the rejection count (by changing the examples)')
    now = now or datetime.now(timezone.utc)
    store.record_alert(category=category, window_start=now, rejections=0, offers=0, at=now, changed_at=now)


def status_report(store, categories) -> dict:
    """What the status report shows the owner: every category whose alert is standing, and the collect queue."""
    standing = []
    for category in categories:
        since = _window_start(store, category)
        fired = [a for a in store.alerts_for(category) if a['changed_at'] is None and a['rejections'] > 0
                 and (since is None or a['fired_at'] > since)]
        if fired:
            last = max(fired, key=lambda a: a['rejections'])
            standing.append({'category': category, 'rejections': last['rejections'], 'offers': last['offers'],
                             'alerts': len(fired)})
    return {'alerts': standing, 'collect_queue': store.open_collect_requests()}
