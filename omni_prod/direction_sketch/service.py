"""What the three sketch routes do (S6.3, slice 3), apart from HTTP.

create()   recomputes READY and the direction from the LATEST brief (it trusts nothing from the client), makes or returns
           the sketch row, reuses the words of an earlier sketch of the same customer words (free: no model), and for new
           words asks copy.request() to reserve and queue the call -- without waiting for it.
view()     the state the customer's card shows: the direction in words, the placeholders, who pays, the words' state.
           It finalises a pending sketch from its reservation first (idempotent).
page()     the HTML of the sketch, rendered again from what the row recorded (the brief text it was made from), by the
           same functions the build uses.

It writes no plan, contract, approval or build row and never changes the brief."""
from __future__ import annotations

import datetime
import logging

from .. import section_library as L
from . import copy as C
from . import funding as F
from . import copy_fp, direction_fp, direction_from_prompt, prompt_of, ready
from . import store as S
from .render import render
from .structure import _title, content

_LOG = logging.getLogger(__name__)
STATES = ('structure', 'pending', 'written', 'failed')


class NotReady(RuntimeError):
    """The brief is not ready for a sketch; `reason` names the first condition that failed."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _direction_of(row: S.Sketch):
    return direction_from_prompt(row.record['prompt'])


def create(store: S.SketchStore, reservations, enqueue, brief_row, *, account_id: str, project_id: str,
           has_version: bool, has_open_build: bool, venice_profile: dict | None = None, price_ack=None,
           subscriptions=None, pool=None) -> tuple[S.Sketch, dict]:
    """(the sketch row, what became of its words: {'state': ..., 'reason': ...}). Raises NotReady, and, with `price_ack`,
    funding.PriceChanged and funding.CreditsRefused.

    The words of a sketch are free the first time (the company pays, copy.py), reused for free when the customer's words are
    the same (a change of colour, font or order), and otherwise ONE credit (funding.py), only when the customer sends the
    price they were shown as `price_ack`. Without it the answer says {'state': 'price_required', 'price': {...}}: the sketch is
    still delivered, drawn with placeholders."""
    r = ready(brief_row.brief, account_id=account_id, has_version=has_version, has_open_build=has_open_build)
    if not r.ok:
        raise NotReady(r.reason)
    d = r.direction
    dfp, cfp = direction_fp(d), copy_fp(d)
    prior = store.written_copy(project_id, account_id, cfp)
    _content, placeholders = content(d, prior.copy if prior and prior.copy else None, year=str(datetime.date.today().year))
    record = {'direction': d.to_dict(), 'prompt': prompt_of(brief_row.brief), 'placeholders': placeholders,
              'library': L.LIBRARY_VERSION}
    row, created = store.create(project_id=project_id, account_id=account_id, brief_revision=brief_row.revision,
                                brief_fingerprint=brief_row.fingerprint, direction_fp=dfp, copy_fp=cfp, record=record,
                                copy_from=prior.id if prior else None)
    if row.copy_state in ('written', 'pending'):
        return row, {'state': row.copy_state, 'reason': row.copy_reason}
    if reservations is None or enqueue is None:
        outcome = {'state': 'refused', 'reason': 'model_route_unavailable'}
    elif row.copy_state == 'none':
        outcome = C.request(store, reservations, enqueue, row, d, venice_profile=venice_profile)
        if outcome['state'] == 'refused' and F.needs_payment(outcome['reason']):
            outcome = {'state': 'price_required', 'reason': outcome['reason'], 'price': F.price()}
    else:                                       # a failed sketch is tried again only on purpose, and paid for
        outcome = {'state': 'price_required' if price_ack is not None else 'failed', 'reason': row.copy_reason,
                   'price': F.price()}
    if outcome['state'] == 'price_required' and price_ack is not None and subscriptions is not None and pool is not None:
        outcome = F.request_paid(store, reservations, enqueue, subscriptions, pool,
                                 store.get(row.id, project_id, account_id) or row, d, price_ack=price_ack,
                                 venice_profile=venice_profile)
    elif price_ack is not None and outcome['state'] != 'price_required':
        F.require_price(price_ack)              # an acknowledgement of a wrong price is refused even when nothing is charged
    if outcome['state'] in ('refused', 'price_required'):
        _LOG.info('SKETCH_WORDS_NOT_REQUESTED reason=%s', outcome.get('reason'))
    return store.get(row.id, project_id, account_id) or row, outcome


def _state(row: S.Sketch) -> str:
    return 'structure' if row.copy_state == 'none' else row.copy_state


def _price_offer(store: S.SketchStore, row: S.Sketch) -> dict | None:
    """The price of new words, when this sketch has none and the company's free one is gone (written, or its attempts used
    up). Never for the owner's own account (the company pays) and never for a sketch that has words or a call in flight."""
    from ..pricing import owner_account
    if row.copy_state not in ('none', 'failed') or owner_account(row.account_id):
        return None
    if store.free_taken(row.project_id, row.account_id) or store.attempts(row.project_id, row.account_id) >= C.FREE_ATTEMPTS:
        return F.price()
    return None


def view(store: S.SketchStore, reservations, row: S.Sketch, *, subscriptions=None, pool=None) -> dict:
    """The card's state. Finalises a pending sketch from its reservation and, for a sketch the customer paid for, settles or
    releases the credit (both idempotent). Its own words and its price; never an amount of the company's."""
    d = _direction_of(row)
    from .. import typography as T
    pair = T.pair(d.pair)
    if row.copy_state == 'pending' and reservations is not None:
        row = C.finalise(store, reservations, row, d)
        if subscriptions is not None and pool is not None:
            F.settle_or_release(store, reservations, subscriptions, pool, row)
    words = row.copy
    if words is None and row.copy_from:
        source = store.get(row.copy_from, row.project_id, row.account_id)
        words = source.copy if source else None
    _html_content, placeholders = content(d, words, year=str(row.created_at.year if row.created_at else
                                                             datetime.date.today().year))
    t = d.to_dict()
    return {'id': row.id, 'draft': True, 'price': _price_offer(store, row), 'state': _state(row), 'reason': row.copy_reason if row.copy_state == 'failed' else None,
            'brief_revision': row.brief_revision,
            'direction': {'business': t['business'], 'palette': t['palette'], 'art_direction': t['art_direction'],
                          'pair': t['pair'], 'sections': t['sections'], 'titles': t['titles'],
                          'fonts': [pair[role]['family'] for role in ('display', 'body')],
                          'outline': [_title(k, d.titles) for k in d.sections if k != 'hero'],
                          'colours': {k: v for k, v in d.contract['tokens'].items() if k.startswith('--color-')}},
            'words': 'model' if words else 'placeholders', 'placeholders': placeholders,
            'funding': {'none': 'free', 'company_first': 'free', 'owner': 'free', 'customer': 'credits'}[row.funding]
            if row.copy_state != 'none' else None,
            'created_at': row.created_at.isoformat() if row.created_at else None}


def page(store: S.SketchStore, row: S.Sketch) -> str:
    """The sketch's HTML (the draft page), from what the row recorded."""
    d = _direction_of(row)
    words = row.copy
    if words is None and row.copy_from:
        source = store.get(row.copy_from, row.project_id, row.account_id)
        words = source.copy if source else None
    year = str(row.created_at.year if row.created_at else datetime.date.today().year)
    html, _sha = render(d, content(d, words, year=year)[0])
    return html
