"""M7: every requirement carries the words it came from (founder 2026-10-24).

A requirement is one of three things, and only the first one binds:

  stated      the customer's own words: a span (message index, start, end) whose text is re-read from the
              conversation and must equal the recorded quote. Binding; may drive a gate.
  assumed     a default 148AI chose and SHOWS ("הנחנו"). Never binding, never drives a gate.
  unsourced   a claim with no valid span (a model guess, a fabricated or stale quote). Not thrown away:
              kept, flagged, and forbidden to drive a gate.

USBR (unsourced binding requirement rate) = binding requirements whose span does not verify against the
conversation / all binding requirements. It must be 0. `Ledger.verify()` recomputes it from the messages
themselves, so a requirement cannot be binding just because something says it is.
"""
from __future__ import annotations

from dataclasses import dataclass, field

STATED, ASSUMED, UNSOURCED = 'stated', 'assumed', 'unsourced'


class GateRefused(ValueError):
    """A requirement without a verified source of the customer's words tried to drive a gate."""


@dataclass(frozen=True)
class Span:
    message: int          # index in the customer's messages (0 = first contact)
    start: int
    end: int
    quote: str

    def verifies(self, messages: list[str]) -> bool:
        if not (0 <= self.message < len(messages)) or not (0 <= self.start < self.end <= len(messages[self.message])):
            return False
        return messages[self.message][self.start:self.end] == self.quote and bool(self.quote.strip())

    def to_dict(self) -> dict:
        return {'message': self.message, 'start': self.start, 'end': self.end, 'quote': self.quote}


@dataclass
class Requirement:
    key: str                         # e.g. 'product_kind', 'behavior.data_create', 'login'
    value: object
    status: str                      # stated | assumed | unsourced
    span: Span | None = None
    why: str = ''                    # for an assumption: why 148AI chose it; for unsourced: where the claim came from
    superseded_by: int | None = None  # message index of the customer's later correction

    @property
    def binding(self) -> bool:
        return self.status == STATED and self.superseded_by is None

    def to_dict(self) -> dict:
        return {'key': self.key, 'value': self.value, 'status': self.status, 'binding': self.binding,
                'source': self.span.to_dict() if self.span else None, 'why': self.why,
                'superseded_by': self.superseded_by}


@dataclass
class Ledger:
    messages: list[str]
    items: list[Requirement] = field(default_factory=list)

    def add(self, req: Requirement) -> Requirement:
        if req.status == STATED and (req.span is None or not req.span.verifies(self.messages)):
            # A "stated" claim whose words are not in the conversation is not stated: keep it, flag it.
            req = Requirement(req.key, req.value, UNSOURCED, req.span,
                              why=req.why or 'claimed as stated but the quoted words are not in the conversation')
        for old in self.items:
            if old.key == req.key and old.superseded_by is None and req.status == STATED and old.status != ASSUMED:
                old.superseded_by = req.span.message
        if req.status == STATED:
            # a stated value replaces any assumption for the same key (the customer corrected us)
            self.items = [i for i in self.items if not (i.key == req.key and i.status == ASSUMED)]
        elif req.status == ASSUMED and any(i.key == req.key and i.binding for i in self.items):
            return req                       # never assume over what the customer said
        self.items.append(req)
        return req

    def current(self, key: str) -> Requirement | None:
        live = [i for i in self.items if i.key == key and i.superseded_by is None]
        bound = [i for i in live if i.binding]
        return (bound or live)[-1] if live else None

    def binding(self) -> list[Requirement]:
        return [i for i in self.items if i.binding]

    def assumed(self) -> list[Requirement]:
        return [i for i in self.items if i.status == ASSUMED and i.superseded_by is None]

    def unsourced(self) -> list[Requirement]:
        return [i for i in self.items if i.status == UNSOURCED and i.superseded_by is None]

    def verify(self) -> dict:
        """Recompute from the messages. USBR must be 0."""
        claimed = [i for i in self.items if i.binding]
        bad = [i for i in claimed if i.span is None or not i.span.verifies(self.messages)]
        return {'binding': len(claimed), 'unsourced_binding': len(bad),
                'usbr': (len(bad) / len(claimed)) if claimed else 0.0,
                'unsourced_binding_keys': [i.key for i in bad]}

    def gate_value(self, key: str):
        """The only way a gate may read a requirement: binding and verified, or GateRefused."""
        req = self.current(key)
        if req is None:
            raise GateRefused(f'{key}: no requirement')
        if req.status == ASSUMED:
            raise GateRefused(f'{key}: an assumption ("הנחנו") never drives a gate')
        if req.status == UNSOURCED or not req.binding or req.span is None or not req.span.verifies(self.messages):
            raise GateRefused(f'{key}: no verified source in the customer\'s words')
        return req.value
