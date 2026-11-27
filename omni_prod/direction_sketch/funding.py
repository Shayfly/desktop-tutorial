"""A further sketch from the customer's balance (S6.3, slice 5).

The owner's answers (2026-11-27, 1א 2א, recorded in PR #550, inbox/003):
  * a further sketch is charged ONLY FOR NEW WORDING. Re-drawing with another colour, font, order or layout costs the company
    nothing, so it is never charged (service.create reuses the words of an earlier sketch of the same customer words);
  * a further sketch costs ONE credit (PRICE_CREDITS).
The first sketch of a project is on the company (copy.py: $0.10 at most); this module is what happens after it.

How it is charged (the mechanism that exists: credit_reservations, keyed here by the sketch id, as modifications are by theirs):
  1. the customer's request carries `price_ack` = the price they were shown; the server compares it with its own and refuses a
     mismatch (PriceChanged, nothing spent). That is the spend approval: a separate action, bound to the amount;
  2. ONE transaction: the sketch moves to pending with funding 'customer' and `subscriptions.reserve` holds the credit. A refusal
     ("monthly credits exhausted", "paid-provider budget exhausted") rolls both back (CreditsRefused, 402);
  3. the words' model call is reserved on the scope `sketch-paid:{account}:{project}` and queued (copy.request, claimed=True);
     if that cannot be done, the credit is released at once;
  4. when the call is settled: words written and shown -> `subscriptions.settle` (the credit is charged, the provider cost is the
     reservation's actual); anything else -> `subscriptions.release` (the credit returns). The customer pays only for a sketch
     they received;
  5. reconcile() closes what a crash left open (a pending customer sketch older than five minutes).

The owner's own account is never charged (copy.py funds it); an internal-QA account is not handled here (customer plan only).
CLAUDE.md section 5 holds: the sum of settled credit_reservations equals creator_subscriptions.provider_spend_usd."""
from __future__ import annotations

import logging
from decimal import Decimal

from ..intake import budget as B
from . import copy as C
from . import store as S

_LOG = logging.getLogger(__name__)
PRICE_CREDITS = 1                # the owner, 2026-11-27: "2א" -- a further sketch costs one credit
CATEGORY = 'direction_sketch'
STALE_MINUTES = 5


class PriceChanged(RuntimeError):
    """The price the customer acknowledged is not the price now. Nothing was spent."""

    def __init__(self, acknowledged):
        super().__init__(f'acknowledged {acknowledged!r}, price {PRICE_CREDITS}')
        self.acknowledged = acknowledged


class CreditsRefused(RuntimeError):
    """The customer's plan refused the credit (402). `reason` is the subscription's own."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def price() -> dict:
    return {'credits': PRICE_CREDITS}


def require_price(price_ack) -> None:
    """The acknowledged price is the price, or PriceChanged (nothing is spent either way)."""
    if isinstance(price_ack, bool) or price_ack != PRICE_CREDITS:
        raise PriceChanged(price_ack)


def needs_payment(reason: str | None) -> bool:
    """The free sketch is gone (written, or its attempts are used up): new words are the customer's to pay for."""
    return bool(reason) and (reason == 'free_sketch_used' or reason.startswith('free_attempts_used'))


def credit_key(pool, sketch_id: str, *, new: bool = False) -> str:
    """The credit reservation's key for this sketch: the sketch id for the first, `id:n` for a later one (a released
    reservation is resolved for good, so a retry needs a key of its own). With new=False, the latest key."""
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT build_id FROM credit_reservations WHERE build_id = %s OR build_id LIKE %s "
                    'ORDER BY created_at, build_id', (sketch_id, sketch_id + ':%'))
        keys = [r[0] for r in cur.fetchall()]
    if not new:
        return keys[-1] if keys else sketch_id
    return sketch_id if not keys else f'{sketch_id}:{len(keys)}'


class _Refused(Exception):
    def __init__(self, reason):
        self.reason = reason


def _claim_and_hold(pool, subscriptions, sketch: S.Sketch, key: str, quote_usd: Decimal) -> str:
    """One transaction: the sketch to pending as the customer's, and the credit held. Returns FREE or NOT_CLAIMABLE; raises
    CreditsRefused (the plan refused: the claim is rolled back with it)."""
    try:
        with pool.connection() as conn:
            with conn.transaction(), conn.cursor() as cur:
                cur.execute("UPDATE direction_sketches SET funding = 'customer', copy_state = 'pending', copy_reason = NULL, "
                            'credits = %s WHERE id = %s AND project_id = %s AND account_id = %s '
                            "AND copy_state IN ('none', 'failed') RETURNING id",
                            (PRICE_CREDITS, sketch.id, sketch.project_id, sketch.account_id))
                if cur.fetchone() is None:
                    return S.NOT_CLAIMABLE
                decision = subscriptions.reserve(cur, build_id=key, user_id=sketch.account_id, project_id=sketch.project_id,
                                                 cost_class='zero', credits=PRICE_CREDITS, category=CATEGORY,
                                                 estimated_provider_cost_usd=quote_usd)
                if not decision.allowed:
                    raise _Refused(decision.reason)
    except _Refused as exc:
        raise CreditsRefused(exc.reason) from exc
    return S.FREE


def request_paid(store: S.SketchStore, reservations: B.ReservationService, enqueue, subscriptions, pool,
                 sketch: S.Sketch, direction, *, price_ack, venice_profile: dict | None = None) -> dict:
    """Charge one credit for new words and queue them. {'state': 'pending'|'failed'|'refused', 'reason': ...}.
    Raises PriceChanged (the acknowledged price is not the price) and CreditsRefused (the plan said no)."""
    require_price(price_ack)
    try:
        _system, _user, quote = C.preflight(direction, venice_profile=venice_profile)
    except C.SketchCopyRefused as exc:
        return {'state': 'refused', 'reason': exc.reason}              # no model may run now: no credit is held
    key = credit_key(pool, sketch.id, new=True)
    taken = _claim_and_hold(pool, subscriptions, sketch, key, quote.amount_usd)
    if taken != S.FREE:
        return {'state': 'refused', 'reason': 'sketch_busy' if sketch.copy_state == 'pending' else taken}
    fresh = store.get(sketch.id, sketch.project_id, sketch.account_id)
    try:
        out = C.request(store, reservations, enqueue, fresh, direction, customer_pays=True, claimed=True,
                        venice_profile=venice_profile)
    except Exception:                                                   # never leave a credit held for a call never made
        subscriptions.release(build_id=key)
        store.finish(sketch.id, 'failed', reason='request_failed')
        raise
    if out['state'] != 'pending':
        subscriptions.release(build_id=key)
        store.finish(sketch.id, 'failed', reason=str(out.get('reason') or out['state'])[:120])
        _LOG.info('SKETCH_CREDIT_RELEASED key=%s reason=%s', key, out.get('reason'))
    return out


def settle_or_release(store: S.SketchStore, reservations: B.ReservationService, subscriptions, pool, sketch: S.Sketch) -> None:
    """After finalise: a written sketch charges its credit (settled with the call's actual cost), a failed one gives it back.
    Idempotent: settle and release both do nothing on a reservation that is no longer RESERVED."""
    if sketch.funding != 'customer' or sketch.copy_state not in ('written', 'failed'):
        return
    key = credit_key(pool, sketch.id)
    if sketch.copy_state == 'written':
        r = reservations.get(sketch.reservation_id, account_id=sketch.account_id) if sketch.reservation_id else None
        subscriptions.settle(build_id=key, actual_provider_cost_usd=None if r is None else r.actual_usd)
    else:
        subscriptions.release(build_id=key)


def reconcile(store: S.SketchStore, reservations: B.ReservationService, subscriptions, pool, *, limit: int = 50) -> list[dict]:
    """The customer's sketches a crash left pending: older than STALE_MINUTES. With no model call reserved the sketch fails and
    the credit returns; with one, the sketch is finalised from the call's final state and the credit settled or released.
    Bounded by `limit`, and each sketch is read once."""
    from . import service as SK
    def find():
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT id, project_id, account_id FROM direction_sketches WHERE funding = 'customer' "
                        "AND copy_state = 'pending' AND created_at < now() - make_interval(mins => %s) "
                        'ORDER BY created_at LIMIT %s', (STALE_MINUTES, int(limit)))
            return cur.fetchall()
    stale = store._run(find)                      # without migration 049: SketchStoreMissing, never a half answer
    done = []
    for sid, project_id, account_id in stale:
        row = store.get(sid, project_id, account_id)
        if row is None or row.copy_state != 'pending':
            continue
        if not row.reservation_id:
            store.finish(sid, 'failed', reason='crash before the words were reserved')
        else:
            C.finalise(store, reservations, row, SK._direction_of(row))
        after = store.get(sid, project_id, account_id)
        if after is not None and after.copy_state in ('written', 'failed'):
            settle_or_release(store, reservations, subscriptions, pool, after)
            done.append({'sketch': sid, 'state': after.copy_state})
    return done
