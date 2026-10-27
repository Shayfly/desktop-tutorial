"""Venice behind the intake conversation (C3, 2026-10-27).

`VeniceIntakeGateway` gives the reservation worker and `ModelInterpreter` the same surface the routed gateway gives
them -- `complete_json(system=, user=, max_tokens=, task=)` plus a `recorder.records` write-ahead ledger that
`reservation_worker.meter()` reads -- so the paid conversation path can run on Venice without touching the
reservation, budget or validation code:

  * selected only by `OMNI_INTAKE_PROVIDER=venice` on the worker; anything else keeps the routed gateway;
  * the key is `VENICE_API_KEY1`; a missing key fails when the gateway is BUILT, so the worker releases the
    reservation as "no model route" and the customer is never charged for a call that never happened;
  * the budget is the reservation's own quote (per call and aggregate), reserved at the worst case BEFORE contact:
    a call the quote cannot cover is refused without contacting Venice (no record -> CONFIRMED_ZERO);
  * no retries inside a reservation: a retry is a second paid call the quote did not price;
  * the answer must be ONE JSON object (a ```json fence is tolerated, any other text before or after is rejected),
    because `validate_model_output` and the evidence check are the only gate between the model and the brief;
  * every contact leaves a record: provider-reported cost.usd -> CONFIRMED; contact without usage -> COST_UNKNOWN,
    never silently free.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal

from .venice import VeniceBudget, VeniceBudgetExceeded, VeniceClient, VeniceError, VENICE_CONFIG

PROVIDER_ENV = 'OMNI_INTAKE_PROVIDER'


class VeniceOutputInvalid(VeniceError):
    pass


@dataclass
class Record:
    """One provider contact, in the fields reservation_worker.meter() reads."""
    provider: str
    model: str | None
    provider_reported_cost_usd: Decimal | None
    input_tokens: int | None
    output_tokens: int | None
    metered_cost_usd: Decimal | None
    outcome: str
    failure_reason: str | None
    provider_request_id: str
    kind: str = 'provider_call'


class Recorder:
    def __init__(self):
        self.records: list[Record] = []


_FENCE = re.compile(r'\A```(?:json)?\s*\n(?P<body>.*?)\n?```\Z', re.S)


def parse_json_object(text: str) -> dict:
    s = (text or '').strip()
    m = _FENCE.match(s)
    if m:
        s = m.group('body').strip()
    try:
        obj, end = json.JSONDecoder().raw_decode(s)
    except ValueError as exc:
        raise VeniceOutputInvalid(f'Venice answer is not JSON: {exc.msg}') from None
    if s[end:].strip():
        raise VeniceOutputInvalid('Venice answer has text after the JSON object')
    if not isinstance(obj, dict):
        raise VeniceOutputInvalid('Venice answer is JSON but not an object')
    return obj


class VeniceIntakeGateway:
    provider = 'venice'

    def __init__(self, quoted_usd: Decimal, *, env=None, transport=None, conversation: str | None = None):
        quoted = Decimal(str(quoted_usd))
        budget = VeniceBudget(per_conversation_usd=quoted, total_usd=quoted)
        from .venice import _urllib_transport
        inner = transport or _urllib_transport
        self._chat_sent = False

        def tracked(method, url, headers, body, timeout):
            if method == 'POST' and url.endswith('/chat/completions'):
                self._chat_sent = True       # from here on money may have been spent
            return inner(method, url, headers, body, timeout)
        self.client = VeniceClient(env if env is not None else os.environ, budget=budget, transport=tracked,
                                   retries=0)
        self.conversation = conversation or 'intake:' + uuid.uuid4().hex
        self.recorder = Recorder()
        self.last_usage = None

    def __repr__(self):
        return f'VeniceIntakeGateway(key_env={VENICE_CONFIG["key_env"]!r})'

    def complete_json(self, *, system: str, user: str, max_tokens: int, task: str = 'conversation') -> dict:
        self.recorder.records = []          # meter() prices THIS call only, also when one gateway serves many turns
        request_id = 'venice-' + uuid.uuid4().hex
        self._chat_sent = False
        try:
            out = self.client.chat(conversation=self.conversation, lang='same as the customer message',
                                   messages=[{'role': 'system', 'content': system},
                                             {'role': 'user', 'content': user}],
                                   max_tokens=int(max_tokens), idempotency_key=request_id,
                                   venice_parameters={'include_venice_system_prompt': False})
        except VeniceBudgetExceeded:
            raise                            # refused before contact: no record, nothing spent
        except Exception as exc:
            if not self._chat_sent:          # model list / key / budget failure: Venice never saw the prompt
                raise
            self.recorder.records.append(Record('venice', None, None, None, None, None, 'error',
                                                f'{type(exc).__name__}: {str(exc)[:200]}', request_id))
            raise
        usage = out.get('usage') or {}
        cost = out.get('cost_usd')
        self.last_usage = usage
        self.recorder.records.append(Record(
            'venice', out.get('model'), None if cost is None else Decimal(str(cost)),
            usage.get('prompt_tokens'), usage.get('completion_tokens'), None, 'ok', None, request_id))
        return parse_json_object(out['text'])


def selected(env=None) -> bool:
    return ((env if env is not None else os.environ).get(PROVIDER_ENV) or '').strip().lower() == 'venice'
