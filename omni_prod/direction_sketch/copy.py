"""The words of a direction sketch: one small model call, reserved, metered and recorded like every intake call
(S6.3, slice 2). The structure of the sketch (colours, fonts, outline) is deterministic and free (omni_prod/direction_sketch);
only the headline, the opening line and the service titles are written by a model, and the model never chooses a colour,
a font or a section.

Money (the owner, 2026-11-26: "the first sketch in each project is on us, up to $0.10"; 2026-11-27: a further sketch costs
1 credit and is charged only for new wording):

* AT MOST $0.10 PER CALL. A quote above SKETCH_MAX_USD is refused before anything is reserved (`sketch_over_cap`).
* AT MOST $0.10 IN ALL on the company's account per project: the first sketch's call is reserved on its own scope,
  `sketch-free:{account}:{project}`, with that cap. `reserve()` checks it under the scope lock, and an UNKNOWN call keeps
  holding its full quote, so failed attempts count and the total can never pass it.
* ONE FREE SKETCH PER PROJECT: the partial unique index of migration 049. A failed call frees the slot again, at most
  FREE_ATTEMPTS times per project (every loop has a bound).
* The owner's own account is funded by the company on every sketch (`funding = 'owner'`), outside the index, bounded by the
  same safety bound as his conversations.
* No customer credit is touched here: a further sketch charged to the customer is slice 5 (funding.py).

The call never waits for the result: `request()` reserves and queues; `finalise()` reads the reservation's final state."""
from __future__ import annotations

import json
import logging
import os
from decimal import Decimal

from ..intake import budget as B
from . import store as S

_LOG = logging.getLogger(__name__)
TASK = 'direction_sketch'
SKETCH_MAX_USD = Decimal('0.10')      # the owner, 2026-11-26 ("מעולה על חשבוננו"): per call, and in all for a project's free sketch
FREE_ATTEMPTS = 3
MAX_TOKENS = 2000
# A safety bound for the scope of sketches the customer pays for in credits (slice 5): the credits are the customer's
# limit; this only keeps the loop bounded (CLAUDE.md section 3). At the measured $0.0017 a call it is about 590 calls.
SKETCH_PAID_PROJECT_USD = Decimal('1.00')
PROMPT_VERSION = 'direction-sketch/1'
OFFERED = {'hero': 'required', 'services': 'required'}

FREE_FUNDINGS = ('company_first', 'owner')


class SketchCopyRefused(RuntimeError):
    """The words cannot be requested; `reason` is what is recorded and what the customer's card says."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def prompt(direction) -> tuple[str, str]:
    """(system, user) for the model: the build's own copy writer's rules and payload shape, restricted to the hero and the
    services (site_content.agents._CONTENT_SYSTEM; the schema is schema.schema_for_model on two sections)."""
    from ..section_library import LAYOUTS
    from ..site_content import agents as A
    from ..site_content import schema as K
    sheet = direction.sheet
    body = {'request': sheet.for_model(), 'palette': direction.palette if direction.category else None,
            'direction': direction.art_direction, 'voice': (direction.voice or ''),
            'trade_words': list(direction.domain_words or []),
            'schema': K.schema_for_model(OFFERED, direction.titles, name_given=bool(sheet.name), layouts=LAYOUTS)}
    return A._CONTENT_SYSTEM, json.dumps(body, ensure_ascii=False)


def validate(doc, direction) -> tuple[bool, str | None]:
    """(True, None) when the words may be shown: the build's content validator, on the two sections, finds nothing that
    blocks (no phone, address or price in copy, no number or person the customer did not write)."""
    from ..site_content import agents as A
    from ..site_content import validate as V
    try:
        A.content_shape_guard(doc)
    except Exception as exc:                                       # ModelJSONRejected
        return False, f'shape: {str(exc)[:120]}'
    extra = sorted(set(doc['sections']) - set(OFFERED))
    if extra:
        return False, f'sections not asked for: {extra}'
    problems = V.blocking(V.validate(doc, direction.sheet, OFFERED, direction.titles))
    if problems:
        return False, 'validator: ' + ', '.join(sorted({f'{p.path} {p.code}' for p in problems})[:4])
    return True, None


def _funding(account_id: str, *, customer_pays: bool) -> str:
    from ..pricing import owner_account
    if owner_account(account_id):
        return 'owner'
    return 'customer' if customer_pays else 'company_first'


def model_allowed() -> str | None:
    """Why the model may not run now (the conversation's own switches), or None."""
    from ..model_policy import external_spend_enabled
    if os.getenv('OMNI_INTAKE_MODEL') != '1':
        return 'model switch off (OMNI_INTAKE_MODEL)'
    if os.getenv('OMNI_INTAKE_VIA_WORKER') != '1':
        return 'intake worker route is not enabled'
    if not external_spend_enabled():
        return 'external model spend is disabled'
    return None


def preflight(direction, *, venice_profile: dict | None = None):
    """(system, user, quote) of the words' call, or a SketchCopyRefused naming why no call may be made: the model's switches,
    no price, a quote above the owner's $0.10. Nothing is reserved, claimed or charged by this."""
    why_not = model_allowed()
    if why_not:
        raise SketchCopyRefused(why_not)
    system, user = prompt(direction)
    try:
        quote = B.quote(system=system, user=user, max_tokens=MAX_TOKENS, task=TASK, venice_profile=venice_profile)
    except B.QuoteUnavailable as exc:
        raise SketchCopyRefused(f'quote_unavailable: {str(exc)[:120]}') from exc
    if quote.amount_usd > SKETCH_MAX_USD:
        # a price or a prompt changed: an error, not a normal refusal (the owner's cap is per call)
        _LOG.error('SKETCH_OVER_CAP quote=%s cap=%s', quote.amount_usd, SKETCH_MAX_USD)
        raise SketchCopyRefused('sketch_over_cap')
    return system, user, quote


def request(store: S.SketchStore, reservations: B.ReservationService, enqueue, sketch: S.Sketch, direction, *,
            customer_pays: bool = False, claimed: bool = False, venice_profile: dict | None = None,
            caps: B.Caps | None = None) -> dict:
    """Reserve and queue the sketch's words, without waiting. {'state': 'pending' | 'failed' | 'refused', 'reason': ...,
    'reservation_id': ...}. Every refusal is named; the deterministic sketch is always still there.
    `claimed`: the caller (funding.py) already took the sketch for the customer's credits in its own transaction."""
    account_id, project_id = sketch.account_id, sketch.project_id
    funding = _funding(account_id, customer_pays=customer_pays)
    if funding == 'customer' and not claimed:
        raise SketchCopyRefused('customer-funded sketches are claimed by funding.py, with the customer\'s credits')
    try:
        system, user, quote = preflight(direction, venice_profile=venice_profile)
    except SketchCopyRefused as exc:
        return {'state': 'refused', 'reason': exc.reason}
    purpose = 'sketch-paid' if funding == 'customer' else 'sketch-free'
    if funding == 'company_first':
        used = store.attempts(project_id, account_id)
        if used >= FREE_ATTEMPTS:
            return {'state': 'refused', 'reason': f'free_attempts_used: {used} of {FREE_ATTEMPTS}'}
    if not claimed:
        taken = store.claim(sketch.id, project_id, account_id, funding)
        if taken != S.FREE:
            return {'state': 'refused', 'reason': {S.BUSY: 'free_sketch_busy', S.USED: 'free_sketch_used'}.get(taken, taken)}
    attempt = store.attempts(project_id, account_id, purpose)
    base = caps or B.caps_from_env()
    if funding == 'owner':
        scope_caps = B.Caps(project_usd=B.OWNER_INTAKE_SAFETY_USD,
                            daily_usd=B.OWNER_INTAKE_SAFETY_USD if base.daily_usd is not None else None)
    elif funding == 'customer':
        scope_caps = B.Caps(project_usd=SKETCH_PAID_PROJECT_USD, daily_usd=base.daily_usd)
    else:
        scope_caps = B.Caps(project_usd=SKETCH_MAX_USD, daily_usd=base.daily_usd)
    try:
        r = reservations.reserve(
            idempotency_key=f'sketch:{account_id}:{project_id}:{sketch.id}:{attempt}'[:300], account_id=account_id,
            project_id=project_id, quote_=quote, caps=scope_caps, purpose=purpose,
            payload={'system': system, 'user': user, 'max_tokens': MAX_TOKENS, 'task': TASK,
                     'prompt_version': PROMPT_VERSION})
    except B.LimitReached as exc:
        store.finish(sketch.id, 'failed', reason=f'limit: {exc.kind}')
        _LOG.info('SKETCH_LIMIT kind=%s scope=%s', exc.kind, getattr(exc, 'scope', '?').split(':')[0])
        return {'state': 'failed', 'reason': f'limit: {exc.kind}'}
    except Exception as exc:                      # BudgetError, DB errors: fail closed, no paid call
        store.finish(sketch.id, 'failed', reason=f'reserve_failed: {type(exc).__name__}')
        return {'state': 'failed', 'reason': f'reserve_failed: {type(exc).__name__}'}
    store.set_reservation(sketch.id, r.id)
    if r.state == B.RESERVED:
        try:
            try:
                enqueue(r.id)
            except Exception:                      # one retry on a fresh connection, as the conversation does
                enqueue(r.id)
            reservations.mark_enqueued(r.id)
        except Exception as exc:                   # nothing was sent: give the money and the slot back
            reservations.release(r.id, reason=f'enqueue failed: {type(exc).__name__}')
            store.finish(sketch.id, 'failed', reason='queue_unavailable')
            return {'state': 'failed', 'reason': 'queue_unavailable', 'reservation_id': r.id}
    return {'state': 'pending', 'reason': None, 'reservation_id': r.id}


def finalise(store: S.SketchStore, reservations: B.ReservationService, sketch: S.Sketch, direction) -> S.Sketch:
    """A pending sketch from its reservation's state, once. Still open: unchanged. RELEASED, UNKNOWN or a result that is
    not valid words: failed, with the reason (the slot is free again). SETTLED with words the validator passes: written.
    Never settles money and never touches credits: that is the reservation's own path (and funding.py's)."""
    if sketch.copy_state != 'pending' or not sketch.reservation_id:
        return sketch
    r = reservations.get(sketch.reservation_id, account_id=sketch.account_id)
    if r is None:
        return sketch
    if r.state in (B.RESERVED, B.CLAIMED, B.EXECUTING):
        return sketch
    if r.state == B.RELEASED:
        store.finish(sketch.id, 'failed', reason=f'released: {(r.failure_reason or "")[:120]}')
    elif r.state == B.UNKNOWN:
        store.finish(sketch.id, 'failed', reason='unknown: the call may have reached the provider; its quote stays held')
    else:
        result = r.result or {}
        doc = result.get('raw') if result.get('ok') else None
        if doc is None:
            store.finish(sketch.id, 'failed', reason=f'no words: {str(result.get("error") or "empty")[:120]}')
        else:
            ok, why = validate(doc, direction)
            if ok:
                store.finish(sketch.id, 'written', copy=doc)
            else:
                store.finish(sketch.id, 'failed', reason=f'not shown: {why}')
    return store.get(sketch.id, sketch.project_id, sketch.account_id) or sketch
