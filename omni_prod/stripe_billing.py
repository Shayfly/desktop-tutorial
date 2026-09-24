from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
import os
import threading
import time
import urllib.parse
import urllib.request

from .pricing import PlanCode


class StripeBillingError(RuntimeError):
    pass


_PRICE_ENV = {
    PlanCode.BASIC: 'STRIPE_PRICE_BASIC',
    PlanCode.PRO: 'STRIPE_PRICE_PRO',
    PlanCode.BUSINESS: 'STRIPE_PRICE_BUSINESS',
}


@dataclass(frozen=True)
class CheckoutSession:
    id: str
    url: str
    plan: str


class StripeCheckoutClient:
    """Minimal Stripe Checkout REST adapter with no SDK dependency.

    It never stores card data. Stripe-hosted Checkout handles payment details.
    """
    endpoint = 'https://api.stripe.com/v1/checkout/sessions'

    def __init__(self, *, secret_key: str | None = None, base_url: str | None = None, timeout_seconds: int = 20, opener=None):
        self.secret_key = (secret_key or os.getenv('STRIPE_SECRET_KEY', '')).strip()
        self.base_url = (base_url or os.getenv('OMNI_PUBLIC_BASE_URL', '')).rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.opener = opener or urllib.request.urlopen

    def create_subscription(self, *, user_id: str, email: str, plan: str | PlanCode) -> CheckoutSession:
        code = plan if isinstance(plan, PlanCode) else PlanCode(plan)
        if code not in _PRICE_ENV:
            raise ValueError('checkout is available for basic/pro/business plans only')
        if not self.secret_key:
            raise StripeBillingError('STRIPE_SECRET_KEY is not configured')
        if not self.base_url:
            raise StripeBillingError('OMNI_PUBLIC_BASE_URL is not configured')
        price_id = os.getenv(_PRICE_ENV[code], '').strip()
        if not price_id:
            raise StripeBillingError(f'{_PRICE_ENV[code]} is not configured')
        form = urllib.parse.urlencode({
            'mode': 'subscription',
            'line_items[0][price]': price_id,
            'line_items[0][quantity]': '1',
            'client_reference_id': user_id,
            'customer_email': email,
            'success_url': self.base_url + '/?billing=success&session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': self.base_url + '/?billing=cancelled',
            'metadata[user_id]': user_id,
            'metadata[plan_code]': code.value,
            'subscription_data[metadata][user_id]': user_id,
            'subscription_data[metadata][plan_code]': code.value,
        }).encode()
        req = urllib.request.Request(self.endpoint, data=form, method='POST', headers={
            'Authorization': 'Bearer ' + self.secret_key,
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        try:
            with self.opener(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode('utf-8'))
        except Exception as exc:
            raise StripeBillingError('Stripe checkout creation failed') from exc
        session_id = str(body.get('id', ''))
        url = str(body.get('url', ''))
        if not session_id or not url.startswith('https://'):
            raise StripeBillingError('invalid Stripe checkout response')
        return CheckoutSession(session_id, url, code.value)


def verify_stripe_signature(payload: bytes, signature_header: str, secret: str, *, now: int | None = None, tolerance_seconds: int = 300) -> dict:
    if not secret:
        raise StripeBillingError('STRIPE_WEBHOOK_SECRET is not configured')
    pieces: dict[str, list[str]] = {}
    for item in signature_header.split(','):
        if '=' not in item:
            continue
        k, v = item.split('=', 1)
        pieces.setdefault(k.strip(), []).append(v.strip())
    try:
        timestamp = int(pieces['t'][0])
        signatures = pieces['v1']
    except Exception as exc:
        raise StripeBillingError('invalid Stripe-Signature header') from exc
    current = int(time.time()) if now is None else int(now)
    if abs(current - timestamp) > tolerance_seconds:
        raise StripeBillingError('stale Stripe webhook signature')
    signed = str(timestamp).encode() + b'.' + payload
    expected = hmac.new(secret.encode(), signed, sha256).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in signatures):
        raise StripeBillingError('invalid Stripe webhook signature')
    try:
        event = json.loads(payload.decode('utf-8'))
    except Exception as exc:
        raise StripeBillingError('invalid Stripe webhook JSON') from exc
    if not isinstance(event, dict) or not event.get('id') or not event.get('type'):
        raise StripeBillingError('invalid Stripe event')
    return event


class StripeSubscriptionWebhookProcessor:
    """Idempotent reviewer/runtime processor for verified subscription events.

    Production scale should persist processed event IDs, but duplicate delivery is
    already safe within a running process and plan changes are deterministic.
    """
    SUPPORTED = {'checkout.session.completed', 'customer.subscription.created', 'customer.subscription.updated', 'customer.subscription.deleted'}

    def __init__(self, subscription_service):
        self.subscriptions = subscription_service
        self._seen: set[str] = set()
        self._lock = threading.RLock()

    def process(self, event: dict) -> dict:
        event_id = str(event.get('id', ''))
        event_type = str(event.get('type', ''))
        with self._lock:
            if event_id in self._seen:
                return {'processed': False, 'duplicate': True, 'event_id': event_id}
            if event_type not in self.SUPPORTED:
                self._seen.add(event_id)
                return {'processed': False, 'ignored': True, 'event_id': event_id, 'type': event_type}
            obj = dict(((event.get('data') or {}).get('object') or {}))
            meta = dict(obj.get('metadata') or {})
            user_id = str(meta.get('user_id') or obj.get('client_reference_id') or '')
            if not user_id:
                raise StripeBillingError('verified event missing user_id metadata')
            if event_type == 'customer.subscription.deleted':
                plan = PlanCode.FREE
            else:
                raw_plan = str(meta.get('plan_code') or '')
                try:
                    plan = PlanCode(raw_plan)
                except Exception as exc:
                    raise StripeBillingError('verified event missing/invalid plan_code metadata') from exc
                if plan not in {PlanCode.BASIC, PlanCode.PRO, PlanCode.BUSINESS}:
                    raise StripeBillingError('unsupported paid plan in Stripe event')
            self.subscriptions.assign_plan(user_id, plan)
            self._seen.add(event_id)
            return {'processed': True, 'event_id': event_id, 'type': event_type, 'user_id': user_id, 'plan': plan.value}
