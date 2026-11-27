"""The offer of a direction sketch inside a conversation turn (S6.3, slice 3).

A turn only OFFERS a sketch: it computes whether one is ready and whether its direction is new, and says so as an action
on the reply. It renders nothing, calls no model and writes nothing (the turn already waits for the conversation's own
call; a second one in the same request would double the customer's wait, and a fault here must never break the turn).
The card's own call (POST .../sketches, slice 3) does the rest.

The offer is made once per direction: a turn that changes nothing in the direction carries no new offer. Whatever the
turn decided is recorded with its reason in the stored message (`sketch`), server side, never silent: a not-ready sketch
says why. The three reasons of an off switch are not recorded (they would be on every turn of every account)."""
from __future__ import annotations

import logging

from . import copy_fp, direction_fp, ready

ACTION = 'direction_sketch'
QUIET = ('flag_off', 'account_not_listed', 'library_route_off')
_LOG = logging.getLogger(__name__)


def offered_before(messages) -> set[str]:
    """The direction fingerprints a conversation was already offered, from its stored messages (newest or oldest)."""
    seen = set()
    for m in messages or ():
        for action in (m.get('interpretation') or {}).get('actions') or ():
            if isinstance(action, dict) and action.get('type') == ACTION and action.get('direction_fp'):
                seen.add(action['direction_fp'])
    return seen


def offer(brief_row, *, account_id: str | None, has_version: bool, has_open_build: bool, messages=()) -> dict:   # messages: a list, or a function that reads it
    """{'action': the action to append or None, 'record': what the stored message says about the sketch or None}.
    Never raises: a failure is logged as SKETCH_OFFER_FAILED and recorded as the reason."""
    try:
        r = ready(brief_row.brief, account_id=account_id, has_version=has_version, has_open_build=has_open_build)
    except Exception as exc:                          # the turn goes on; the reason is kept
        _LOG.error('SKETCH_OFFER_FAILED %s: %s', type(exc).__name__, str(exc)[:200])
        return {'action': None, 'record': {'not_ready': f'offer_failed: {type(exc).__name__}'}}
    if not r.ok:
        return {'action': None, 'record': None if r.reason in QUIET else {'not_ready': r.reason}}
    fp = direction_fp(r.direction)
    if fp in offered_before(messages() if callable(messages) else messages):   # read only once a sketch is ready
        return {'action': None, 'record': {'offered': 'already', 'direction_fp': fp}}
    return {'action': {'type': ACTION, 'direction_fp': fp, 'copy_fp': copy_fp(r.direction),
                       'brief_revision': brief_row.revision},
            'record': {'offered': 'now', 'direction_fp': fp}}
