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
from . import copy_fp, direction_fp, direction_from_prompt, prompt_of, ready
from . import store as S
from .render import render
from .structure import content

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
           has_version: bool, has_open_build: bool, venice_profile: dict | None = None) -> tuple[S.Sketch, dict]:
    """(the sketch row, what became of its words: {'state': ..., 'reason': ...}). Raises NotReady."""
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
    if row.copy_state != 'none' or not created:
        return row, {'state': row.copy_state, 'reason': row.copy_reason}
    outcome = C.request(store, reservations, enqueue, row, d, venice_profile=venice_profile) \
        if reservations is not None and enqueue is not None else {'state': 'refused', 'reason': 'model_route_unavailable'}
    if outcome['state'] == 'refused':
        _LOG.info('SKETCH_WORDS_NOT_REQUESTED reason=%s', outcome['reason'])
    return store.get(row.id, project_id, account_id) or row, outcome


def _state(row: S.Sketch) -> str:
    return 'structure' if row.copy_state == 'none' else row.copy_state


def view(store: S.SketchStore, reservations, row: S.Sketch) -> dict:
    """The card's state. Finalises a pending sketch (never settles money: that is the reservation's own path)."""
    d = _direction_of(row)
    if row.copy_state == 'pending' and reservations is not None:
        row = C.finalise(store, reservations, row, d)
    words = row.copy
    if words is None and row.copy_from:
        source = store.get(row.copy_from, row.project_id, row.account_id)
        words = source.copy if source else None
    _html_content, placeholders = content(d, words, year=str(row.created_at.year if row.created_at else
                                                             datetime.date.today().year))
    t = d.to_dict()
    return {'id': row.id, 'draft': True, 'state': _state(row), 'reason': row.copy_reason if row.copy_state == 'failed' else None,
            'brief_revision': row.brief_revision,
            'direction': {'business': t['business'], 'palette': t['palette'], 'art_direction': t['art_direction'],
                          'pair': t['pair'], 'sections': t['sections'], 'titles': t['titles'],
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
