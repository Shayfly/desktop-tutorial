"""Fact canon: the business facts a product may show, taken from the approved request (CEO/Michael 2026-11-10).

The truth gate used to "guess": it searched the request text for a phone number that looked like the one on the
page. The canon makes it a comparison. Each fact carries its key, the normalised value, the raw span it came from
(`source_ref`) and the source kind ("brief" today; "upload" and "manual" when those exist). The canon's hash is
part of the build evidence, so a page is judged against the same facts in every round.

Normalisation (first version; Michael's toE164/normAddr with Hebrew/Arabic edge cases replace these when they land):
  phone   -> E.164 for Israel: 050-123-4567, 050 1234567, +972-50-123-4567, 972501234567 are one value
  address -> "רח'" / "רח׳" / "שד'" expanded, punctuation and spaces collapsed, final letters kept
  email   -> lower-cased
  hours   -> the raw span ("א-ה 07:00-14:00"), digits kept as written
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

_PHONE = re.compile(r'(?<![\d])(?:\+?972[\s\-.]?|0)(?:5\d|7\d|[2-489])[\s\-.]?\d{3}[\s\-.]?\d{4}(?![\d])')
_EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+', re.I)
_STREET = re.compile(r"(?:רחוב|רח['׳]|שדרות|שד['׳]|דרך|סמטת|כיכר)\s+(?:[֐-׿\"'׳״-]+\s+){0,3}?\d{1,4}"
                     r"(?:\s*[,/]?\s*[֐-׿]{2,}(?:\s[֐-׿]{2,})?)?")
_HOURS = re.compile(r"(?:[א-ת]['׳]?\s*[-–]\s*[א-ת]['׳]?\s*)?\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}")
_NAME = re.compile(r"(?:^|\n)\s*(?:שם(?: העסק| המקום)?|business name|name)\s*[:\-]\s*([^\n,.]{2,60})", re.I)


def phone_e164(text: str) -> str | None:
    digits = re.sub(r'\D', '', text or '')
    if digits.startswith('972'):
        digits = digits[3:]
    elif digits.startswith('0'):
        digits = digits[1:]
    else:
        return None
    return '+972' + digits if 8 <= len(digits) <= 9 else None


def norm_address(text: str) -> str:
    t = (text or '').strip()
    t = re.sub(r"רח['׳]\s*", 'רחוב ', t)
    t = re.sub(r"שד['׳]\s*", 'שדרות ', t)
    t = re.sub(r'[,.;:/]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


@dataclass(frozen=True)
class Fact:
    key: str            # phone | address | email | hours | name
    value: str          # normalised
    source: str         # brief | upload | manual
    source_ref: str     # the raw span

    def to_dict(self) -> dict:
        return {'key': self.key, 'value': self.value, 'source': self.source, 'source_ref': self.source_ref}


@dataclass
class Canon:
    facts: list[Fact] = field(default_factory=list)
    source_hash: str = ''

    @property
    def hash(self) -> str:
        body = json.dumps([f.to_dict() for f in self.facts], ensure_ascii=False, sort_keys=True)
        return hashlib.sha256((self.source_hash + body).encode('utf-8')).hexdigest()[:16]

    def values(self, key: str) -> set[str]:
        return {f.value for f in self.facts if f.key == key}

    def to_dict(self) -> dict:
        return {'hash': self.hash, 'facts': [f.to_dict() for f in self.facts]}

    @classmethod
    def from_dict(cls, data) -> 'Canon':
        c = cls()
        for f in (data or {}).get('facts', []) if isinstance(data, dict) else []:
            if isinstance(f, dict) and all(isinstance(f.get(k), str) for k in ('key', 'value', 'source', 'source_ref')):
                c.facts.append(Fact(f['key'], f['value'], f['source'], f['source_ref']))
        return c


def build_canon(request_text: str, *, source: str = 'brief') -> Canon:
    """Every phone, address, e-mail, opening-hours span and declared name in the approved request."""
    text = request_text or ''
    canon = Canon(source_hash=hashlib.sha256(text.encode('utf-8')).hexdigest()[:16])
    seen: set[tuple[str, str]] = set()

    def add(key, value, ref):
        if value and (key, value) not in seen:
            seen.add((key, value))
            canon.facts.append(Fact(key, value, source, ref.strip()))

    for m in _PHONE.finditer(text):
        add('phone', phone_e164(m.group(0)), m.group(0))
    for m in _EMAIL.finditer(text):
        add('email', m.group(0).lower(), m.group(0))
    for m in _STREET.finditer(text):
        add('address', norm_address(m.group(0)), m.group(0))
    for m in _HOURS.finditer(text):
        add('hours', re.sub(r'\s+', ' ', m.group(0)).strip(), m.group(0))
    for m in _NAME.finditer(text):
        add('name', m.group(1).strip(), m.group(0))
    return canon


def validate_canon(canon: Canon, request_text: str) -> list[dict]:
    """Michael's validator, first version: every brief fact must still be in the request; phones must parse."""
    issues = []
    seen = set()
    for f in canon.facts:
        if not f.source_ref:
            issues.append({'code': 'FACT_NO_SOURCE', 'fatal': True, 'at': f.key})
        if f.source == 'brief' and f.source_ref and f.source_ref not in (request_text or ''):
            issues.append({'code': 'FACT_NOT_IN_BRIEF', 'fatal': True, 'at': f.source_ref})
        if f.key == 'phone' and not f.value.startswith('+972'):
            issues.append({'code': 'PHONE_UNPARSEABLE', 'fatal': True, 'at': f.source_ref})
        k = (f.key, f.value)
        if k in seen:
            issues.append({'code': 'FACT_DUPLICATE', 'fatal': True, 'at': f'{f.key}:{f.value}'})
        seen.add(k)
    return issues
