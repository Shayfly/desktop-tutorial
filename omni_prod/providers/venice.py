"""Venice -- the model provider behind agent.venice (owner brief 2026-10-26).

OpenAI-compatible API at VENICE_CONFIG['base_url']. The key is CONFIGURATION: its variable name lives here
(VENICE_CONFIG['key_env'] = 'VENICE_API_KEY1', as it is stored in Vercel), never the key itself. A missing or empty
key is a loud error that names that exact variable; there is no second name and no fallback.

Model choice is by TRAIT from the provider's own /models answer, never by a model name in code:
  * only models whose model_spec.privacy == "private";
  * when the call needs no tools, prefer capabilities.supportsE2EE (the raw idea is the most sensitive input);
    with tools, only models that support function calling;
  * then the cheapest by the provider's own pricing (USD per 1M tokens), so prices are never hard-coded.
The truth tag reports the SELECTED model's traits. It never claims more: `end_to_end_encrypted` is False because this
client does not perform Venice's client-side E2EE handshake -- an E2EE-capable model reached over plain TLS is not an
end-to-end encrypted conversation, and the tag says so.

Every call: bounded retries (429/5xx/timeouts only), an idempotency key, a cancellation event, a timeout, and a
budget reserved at the worst case before the call and settled to the provider-reported cost.usd after it. 401, 402,
an exhausted budget or a provider that stays down is an explicit error -- never a silent demo answer labelled as AI.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

VENICE_CONFIG = {'provider': 'venice', 'base_url': 'https://api.venice.ai/api/v1', 'key_env': 'VENICE_API_KEY1'}


class VeniceError(RuntimeError):
    """Base: every Venice failure is explicit."""


class VeniceKeyMissing(VeniceError):
    pass


class VeniceAuthError(VeniceError):       # 401
    pass


class VeniceInsufficientCredit(VeniceError):   # 402
    pass


class VeniceUnavailable(VeniceError):     # 5xx / 429 / timeouts after the bounded retries
    pass


class VeniceBudgetExceeded(VeniceError):
    pass


class VeniceCancelled(VeniceError):
    pass


class NoPrivateModel(VeniceError):
    pass


def api_key(env) -> str:
    name = VENICE_CONFIG['key_env']
    value = (env.get(name) or '').strip()
    if not value:
        raise VeniceKeyMissing(f'{name} is missing or empty: set it in the deployment environment '
                               f'(see SECRETS_AND_ENVIRONMENT.md); there is no fallback')
    return value


# ---------------------------------------------------------------- models by trait

@dataclass(frozen=True)
class VeniceModel:
    id: str
    privacy: str
    e2ee: bool
    tools: bool
    input_usd_per_m: Decimal | None
    output_usd_per_m: Decimal | None

    @classmethod
    def from_api(cls, item: dict) -> 'VeniceModel':
        spec = item.get('model_spec') or {}
        caps = spec.get('capabilities') or item.get('capabilities') or {}
        price = spec.get('pricing') or item.get('pricing') or {}

        def usd(side):
            v = (price.get(side) or {}).get('usd')
            return None if v is None else Decimal(str(v))
        return cls(str(item.get('id')), str(spec.get('privacy') or item.get('privacy') or ''),
                   bool(caps.get('supportsE2EE')), bool(caps.get('supportsFunctionCalling')), usd('input'), usd('output'))


def select_model(models: list[VeniceModel], *, needs_tools: bool = False, prefer_e2ee: bool = True) -> VeniceModel:
    private = [m for m in models if m.privacy == 'private' and m.input_usd_per_m is not None
               and m.output_usd_per_m is not None]
    if needs_tools:
        private = [m for m in private if m.tools]
    if not private:
        raise NoPrivateModel('no private Venice model (with prices' + (' and tools' if needs_tools else '') + ') is offered')
    pool = [m for m in private if m.e2ee] if (prefer_e2ee and not needs_tools) else []
    pool = pool or private
    return min(pool, key=lambda m: (m.input_usd_per_m + m.output_usd_per_m, m.id))


def truth_tag(model: VeniceModel) -> dict:
    """What the customer-facing label may say, derived from the selected model only."""
    return {'provider': 'venice', 'model_private': model.privacy == 'private', 'privacy': model.privacy or 'unknown',
            'model_supports_e2ee': model.e2ee, 'end_to_end_encrypted': False}


def text_direction(lang: str) -> str:
    return 'rtl' if lang in ('he', 'ar', 'fa', 'ur') else 'ltr'


# ---------------------------------------------------------------- budget

@dataclass
class VeniceBudget:
    """Per-conversation and aggregate caps (USD). Reserve the worst case, settle to the reported cost."""
    per_conversation_usd: Decimal
    total_usd: Decimal
    spent: dict = field(default_factory=dict)
    reserved: dict = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def _total(self):
        return sum(self.spent.values(), Decimal('0')) + sum(self.reserved.values(), Decimal('0'))

    def reserve(self, conversation: str, worst: Decimal) -> None:
        with self.lock:
            mine = self.spent.get(conversation, Decimal('0')) + self.reserved.get(conversation, Decimal('0'))
            if mine + worst > self.per_conversation_usd:
                raise VeniceBudgetExceeded(f'conversation cap {self.per_conversation_usd} USD reached')
            if self._total() + worst > self.total_usd:
                raise VeniceBudgetExceeded(f'aggregate cap {self.total_usd} USD reached')
            self.reserved[conversation] = self.reserved.get(conversation, Decimal('0')) + worst

    def settle(self, conversation: str, worst: Decimal, actual: Decimal | None) -> None:
        with self.lock:
            self.reserved[conversation] = self.reserved.get(conversation, Decimal('0')) - worst
            # unknown actual cost stays at the worst case: never counted as free
            self.spent[conversation] = self.spent.get(conversation, Decimal('0')) + (worst if actual is None else actual)


# ---------------------------------------------------------------- client

def _urllib_transport(method, url, headers, body, timeout):
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen
    req = Request(url, data=None if body is None else json.dumps(body).encode(), method=method, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {}


class VeniceClient:
    RETRYABLE = (429, 500, 502, 503, 504)

    def __init__(self, env, *, budget: VeniceBudget, transport=None, timeout: float = 60.0, retries: int = 2,
                 sleep=time.sleep):
        self._key = api_key(env)                      # loud now, not at the first customer message
        self.budget, self.timeout, self.retries, self.sleep = budget, timeout, retries, sleep
        self.transport = transport or _urllib_transport

    def __repr__(self):                                # the key never appears in a repr, a log line or an export
        return f'VeniceClient(base_url={VENICE_CONFIG["base_url"]!r}, key_env={VENICE_CONFIG["key_env"]!r})'

    def _headers(self, idem: str | None = None):
        h = {'Authorization': 'Bearer ' + self._key, 'Content-Type': 'application/json', 'Accept': 'application/json'}
        if idem:
            h['Idempotency-Key'] = idem
        return h

    def _request(self, method, path, body=None, *, idem=None, cancel: threading.Event | None = None):
        last = None
        for attempt in range(self.retries + 1):
            if cancel is not None and cancel.is_set():
                raise VeniceCancelled('cancelled before the provider was contacted' if attempt == 0 else 'cancelled')
            try:
                status, data = self.transport(method, VENICE_CONFIG['base_url'] + path, self._headers(idem), body, self.timeout)
            except (TimeoutError, OSError) as exc:
                status, data, last = None, {}, type(exc).__name__
            if status == 401:
                raise VeniceAuthError(f'Venice refused the key in {VENICE_CONFIG["key_env"]} (401)')
            if status == 402:
                raise VeniceInsufficientCredit('Venice: insufficient credit (402)')
            if status is not None and status < 400:
                return data
            if status is not None and status not in self.RETRYABLE:
                raise VeniceError(f'Venice answered HTTP {status}')
            last = last or f'HTTP {status}'
            if attempt < self.retries:
                self.sleep(min(2 ** attempt, 8))
        raise VeniceUnavailable(f'Venice unavailable after {self.retries + 1} attempts ({last})')

    def models(self) -> list[VeniceModel]:
        data = self._request('GET', '/models?type=text')
        return [VeniceModel.from_api(m) for m in (data.get('data') or []) if isinstance(m, dict)]

    def chat(self, *, conversation: str, messages: list[dict], lang: str, max_tokens: int = 800,
             needs_tools: bool = False, cancel: threading.Event | None = None, idempotency_key: str | None = None,
             venice_parameters: dict | None = None) -> dict:
        model = select_model(self.models(), needs_tools=needs_tools)
        prompt_chars = sum(len(str(m.get('content', ''))) for m in messages)
        worst = (model.input_usd_per_m * Decimal(prompt_chars + 64) + model.output_usd_per_m * Decimal(max_tokens)) / Decimal(1_000_000)
        self.budget.reserve(conversation, worst)
        actual = None
        try:
            system = {'role': 'system', 'content': f'Reply in the customer\'s language ({lang}).'}
            body = {'model': model.id, 'messages': [system] + messages, 'max_tokens': max_tokens}
            if venice_parameters:
                body['venice_parameters'] = dict(venice_parameters)
            data = self._request('POST', '/chat/completions', body, idem=idempotency_key or uuid.uuid4().hex, cancel=cancel)
            cost = (data.get('cost') or {}).get('usd')
            actual = None if cost is None else Decimal(str(cost))
            text = (((data.get('choices') or [{}])[0].get('message') or {}).get('content') or '')
            if not text.strip():
                raise VeniceError('Venice returned an empty answer')
            return {'text': text, 'dir': text_direction(lang), 'model': model.id, 'tag': truth_tag(model),
                    'usage': data.get('usage'), 'cost_usd': None if actual is None else str(actual)}
        finally:
            self.budget.settle(conversation, worst, actual)
