"""The persistence decision (R1, docs/design/r1-r2-persistence.md, signed by Michael 2026-11-11).

One authority for "does this product store records". Run 10b: a static florist page was contracted with
customers/availability/bookings because the word "הזמנה" appeared (inside a WhatsApp template) and the customer's
explicit "static page" never reached the contract. Precedence, enforced in ONE place (`resolve`):

  1. a customer decision bound into the approved brief      -> it decides; keywords are not read for the requirement
  2. no decision                                             -> STRONG cues (or sign-in) decide; WEAK cues never do

`artifact_class` is derived here from persistence + storing capabilities, never from the family classifier.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .intent_terms import has_term

NONE, RECORDS, STALE = 'none', 'records', 'stale'
PAGE, APP = 'page', 'app'
CUSTOMER, KEYWORD = 'customer', 'keyword'

# 8.1 -- STRONG: alone enough for "records". A product with one of these keeps data by its nature.
STRONG_TERMS = (
    'הרשמה', 'נרשמים', 'להירשם', 'הירשמו', 'התחברות', 'להתחבר', 'אזור אישי', 'החשבון שלי', 'משתמשים רשומים',
    'סל קניות', 'עגלת קניות', 'תשלום באתר', 'לשלם באתר', 'סליקה', 'רשימת הזמנות', 'ניהול הזמנות', 'מערכת הזמנות',
    'קביעת תור', 'קביעת תורים', 'לקבוע תור', 'ניהול תורים', 'יומן תורים', 'טופס שנשמר', 'נשמרת', 'נשמרים', 'נשמר',
    'השארת פרטים', 'להשאיר פרטים', 'השאירו פרטים', 'מעקב', 'מלאי', 'דשבורד', 'ניהול לקוחות',
    # the product itself is a system: a management tool keeps records by definition ("אפליקציה לניהול משימות")
    'מערכת', 'אפליקציה', 'אפליקציית', 'פלטפורמה', 'כלי', 'ניהול', 'לנהל', 'CRM',
    'app', 'system', 'platform', 'tool', 'manage', 'management', 'tracker',
    # the visitor changes things: add / mark / delete / edit is a record by definition (shopping list, to-do)
    'הוספת', 'להוסיף', 'מוסיפים', 'מחיקה', 'למחוק', 'מוחקים', 'עריכה', 'לערוך', 'סימון', 'לסמן', 'מסמנים',
    'add item', 'delete', 'edit', 'mark as',
    'sign up', 'signup', 'sign-up', 'register', 'registration', 'log in', 'login', 'sign in', 'my account',
    'user accounts', 'shopping cart', 'checkout', 'pay online', 'order history', 'booking system', 'book an appointment',
    'appointment booking', 'saved form', 'stores submissions', 'inventory', 'dashboard', 'track',
)
# WEAK: present in almost every business brief; NEVER enough alone (they may only name records once a strong cue
# exists): phone, e-mail, WhatsApp, "להזמין", "הזמנה", "לקוחות". Kept here so the split is explicit and reviewable.
WEAK_TERMS = ('טלפון', 'מייל', 'וואטסאפ', 'whatsapp', 'להזמין', 'הזמנה', 'הזמנות', 'לקוחות', 'phone', 'email', 'order')

# Roles beyond the single visitor, infrastructure and integrations that by themselves store records (8.5).
_STORING_INFRA = ('auth_session',)
_STORING_INTEGRATIONS = ('payments',)

_DECISION_LINE = re.compile(r'Product decisions v1:\s*(\{[^{}]*\})')
_MARKER = re.compile(r'--- Approved project brief \(binding; fingerprint [a-f0-9]{16}\) ---')


@dataclass(frozen=True)
class Decision:
    persistence: str | None      # NONE | RECORDS | None (no customer decision)
    source: str | None           # CUSTOMER or None


@dataclass(frozen=True)
class Resolved:
    persistence: str             # NONE | RECORDS | STALE
    source: str                  # CUSTOMER | KEYWORD
    artifact_class: str          # PAGE | APP
    data_requirements: tuple[str, ...]
    storing_capabilities: tuple[str, ...]
    strong_cues: tuple[str, ...]

    @property
    def persistence_source(self) -> str:
        return self.source


def strong_cues(customer_text: str) -> tuple[str, ...]:
    """The strong cues in what the CUSTOMER wrote (the caller strips negations and the generated brief first)."""
    return tuple(t for t in STRONG_TERMS if has_term(customer_text or '', t))


def read_decision(full_prompt: str, *, legacy_content_only: bool = False) -> Decision:
    """The customer decision, read ONLY from the last server-generated approved-brief block -- never from text the
    customer typed (which may imitate a block). `legacy_content_only`: a brief approved before this field existed
    with the old CONTENT-ONLY line counts as a customer `none`."""
    flat = ' '.join((full_prompt or '').split())
    markers = list(_MARKER.finditer(flat))
    if markers:
        block = flat[markers[-1].end():]
        m = _DECISION_LINE.search(block)
        if m:
            try:
                data = json.loads(m.group(1))
            except ValueError:
                data = {}
            value = data.get('persistence')
            if value in (NONE, RECORDS):
                return Decision(value, CUSTOMER)
    if legacy_content_only:
        return Decision(NONE, CUSTOMER)
    return Decision(None, None)


def decision_line(persistence: str) -> str:
    """What discovery.requirements_text writes into the approved brief block for a confirmed customer answer."""
    if persistence not in (NONE, RECORDS):
        raise ValueError(f'not a persistence decision: {persistence!r}')
    return 'Product decisions v1: ' + json.dumps(
        {'version': 1, 'persistence': persistence, 'source': CUSTOMER}, separators=(',', ':'))


def storing_capabilities(*, roles, infrastructure_kinds, integrations, strong) -> tuple[str, ...]:
    out = [f'role:{r}' for r in roles if r not in ('user',)]
    out += [f'infra:{k}' for k in infrastructure_kinds if k in _STORING_INFRA]
    out += [f'integration:{i}' for i in integrations if i in _STORING_INTEGRATIONS]
    out += [f'cue:{c}' for c in strong]
    return tuple(dict.fromkeys(out))


def resolve(decision: Decision, *, strong: tuple[str, ...], keyword_requirements: tuple[str, ...],
            capabilities: tuple[str, ...]) -> Resolved:
    """THE precedence point (R1). `keyword_requirements` = what the old vocabulary/modules would name."""
    if decision.source == CUSTOMER and decision.persistence == NONE:
        if capabilities:                      # 8.4: the brief now asks for something that stores -> stale
            return Resolved(STALE, CUSTOMER, APP, (), capabilities, strong)
        return Resolved(NONE, CUSTOMER, PAGE, (), (), strong)
    if decision.source == CUSTOMER and decision.persistence == RECORDS:
        return Resolved(RECORDS, CUSTOMER, APP, keyword_requirements or ('records',), capabilities, strong)
    if capabilities:                           # no decision: a strong cue or a storing capability decides
        return Resolved(RECORDS, KEYWORD, APP, keyword_requirements or ('records',), capabilities, strong)
    return Resolved(NONE, KEYWORD, PAGE, (), (), strong)  # weak cues alone never create a requirement
