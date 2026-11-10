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
import unicodedata
from dataclasses import dataclass, field

# Candidate spans: anything that looks like a phone, in any digit script; parse_phone decides what it is.
_PHONE = re.compile(r'(?<![\d\u0660-\u0669\u06F0-\u06F9])(?:\+|00)?[\d\u0660-\u0669\u06F0-\u06F9][\d\u0660-\u0669\u06F0-\u06F9()\s\-.\u2010-\u2015]{5,16}[\d\u0660-\u0669\u06F0-\u06F9](?![\d\u0660-\u0669\u06F0-\u06F9])')
_EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+', re.I)
# City: one word after a comma, or a known two-word city ("תל אביב"); never the next unrelated word ("חיפה טלפון").
_CITY2 = r"(?:תל|באר|ראש|כפר|בית|קריית|קרית|נווה|רמת|גבעת|מעלה|אור|בני|נס|מגדל|נצרת|יבנה|זכרון)\s[\u0590-\u05FF]{2,}"
_STREET = re.compile(r"(?:רחוב|רח['\u05F3]|ר[\"\u05F4]ח|שדרות|שד['\u05F3]|דרך|סמטת|כיכר)\s+(?:[\u0590-\u05FF\"'\u05F3\u05F4-]+\s+){0,3}?\d{1,4}"
                     r"(?:\s*,\s*(?:" + _CITY2 + r"|[\u0590-\u05FF]{2,})"
                     r"|\s+(?:" + _CITY2 + r"|[\u0590-\u05FF]{2,})(?=\s*[,.;\n]|$))?")
_HOURS = re.compile(r"(?:[א-ת]['\u05F3]?\s*(?:[-–]\s*[א-ת]['\u05F3]?\s*)?)?\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}")
_NAME = re.compile(r"(?:^|\n|\s)(?:שם העסק|שם המקום|business name)\s*:\s*([^\n,.–—:]{2,40}?)(?=\s*(?:[–—,.\n]|כתובת|טלפון|$))", re.I)


# ---- normalisation (Michael 2026-11-10: pure functions, a reason on failure, Hebrew/Arabic edge cases) ----
_INVISIBLE = re.compile('[\u00A0\u2007\u202F\u200B-\u200F\u202A-\u202E\u2066-\u2069\u061C\u0640\uFEFF]')
_DASHES = re.compile('[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D]')
_EXT_MARK = re.compile(r'(?:שלוחה|פנימי|ת\.ד\.?|ext\.?|\bx\b|#)', re.I)
_SERVICE = re.compile(r'^(?:\*|1[-\s]?(?:800|700|900|80|90))')
_SPLIT_SECOND = re.compile(r'[/,;]|\sאו\s')
_HEBREW_MARKS = re.compile('[\u05B0-\u05BD\u05BF\u05C1\u05C2\u05C7]')
_ARABIC_MARKS = re.compile('[\u064B-\u0652\u0670\u0640]')
_QUOTES = re.compile('["\'`\u05F3\u05F4]')
_PUNCT = re.compile(r'[.,;:!?()\[\]{}]')
_FINALS = str.maketrans('ךםןףץ', 'כמנפצ')
_HE_PREFIX = {'רח': 'רחוב', 'רח׳': 'רחוב', "רח'": 'רחוב', 'ר"ח': 'רחוב', 'שד': 'שדרות', "שד'": 'שדרות', 'שד׳': 'שדרות'}
_HE_STREET_WORDS = {'רחוב', 'שדרות', 'דרך', 'סמטת', 'כיכר', 'מבוא', 'מעלה', 'מדרגות', 'פארק', 'קניון', 'בניין', 'בית', 'אזור'}
_AR_PREFIX = {'ش': 'شارع', 'ش.': 'شارع'}
_HE_NUM = {'אחד': '1', 'אחת': '1', 'שניים': '2', 'שתיים': '2', 'שלושה': '3', 'שלוש': '3', 'ארבעה': '4', 'ארבע': '4',
           'חמישה': '5', 'חמש': '5', 'שישה': '6', 'שש': '6', 'שבעה': '7', 'שבע': '7', 'שמונה': '8', 'תשעה': '9',
           'תשע': '9', 'עשרה': '10', 'עשר': '10'}
_AR_NUM = {'واحد': '1', 'اثنان': '2', 'ثلاثة': '3', 'اربعة': '4', 'خمسة': '5', 'ستة': '6', 'سبعة': '7', 'ثمانية': '8',
           'تسعة': '9', 'عشرة': '10'}


def fold_digits(text: str) -> str:
    """Arabic-Indic, Persian and full-width digits -> ASCII."""
    out = []
    for ch in text:
        cp = ord(ch)
        if 0x0660 <= cp <= 0x0669:
            out.append(str(cp - 0x0660))
        elif 0x06F0 <= cp <= 0x06F9:
            out.append(str(cp - 0x06F0))
        elif 0xFF10 <= cp <= 0xFF19:
            out.append(str(cp - 0xFF10))
        else:
            out.append(ch)
    return ''.join(out)


@dataclass(frozen=True)
class PhoneResult:
    ok: bool
    e164: str | None = None
    kind: str | None = None          # mobile | landline | voip
    reason: str | None = None        # EMPTY SERVICE NON_IL SHORT LONG BAD_PREFIX DUMMY AMBIGUOUS


def parse_phone(raw: str, cc: str = 'IL') -> PhoneResult:
    """toE164 for Israel: one value for every way a number is written, a reason when it is not a number."""
    if not raw or not raw.strip():
        return PhoneResult(False, reason='EMPTY')
    s = unicodedata.normalize('NFC', raw)
    s = _INVISIBLE.sub(' ', s)
    s = _DASHES.sub('-', s)
    s = fold_digits(s)
    s = _EXT_MARK.split(s)[0]                      # "03-1234567 שלוחה 4" -> "03-1234567 "
    s = _SPLIT_SECOND.split(s)[0]                  # two numbers -> the first
    if _SERVICE.match(s.strip()):
        return PhoneResult(False, reason='SERVICE')
    s = re.sub(r'[^\d+]', '', s)
    if not s:
        return PhoneResult(False, reason='EMPTY')
    if s.count('+') > 1:
        return PhoneResult(False, reason='NON_IL')
    if re.fullmatch(r'0+', s):                      # "000-0000000" is a dummy, not a "00" international prefix
        return PhoneResult(False, reason='DUMMY')
    s = re.sub(r'^00', '+', s)
    if s.startswith('+'):
        s = re.sub(r'^\+9720', '+972', s)
        if not s.startswith('+972'):
            return PhoneResult(False, reason='NON_IL')
        s = s[4:]
    elif s.startswith('972') and len(s) >= 11:
        s = s[3:]
    elif not s.startswith('0'):
        # No 0 and no 972 (Michael 2026-11-10 bounds): < 7 digits SHORT, > 9 LONG, 7/8/9 a subscriber number without
        # its area code -> AMBIGUOUS, never a guess.
        if len(s) < 7:
            return PhoneResult(False, reason='SHORT')
        if len(s) > 9:
            return PhoneResult(False, reason='LONG')
        return PhoneResult(False, reason='AMBIGUOUS')
    if s.startswith('0'):
        s = s[1:]
    if re.fullmatch(r'0+', s) or re.fullmatch(r'(\d)\1+', s) or s in ('12345678', '123456789'):
        return PhoneResult(False, reason='DUMMY')
    if len(s) == 9 and re.match(r'5\d', s):
        kind = 'mobile'
    elif len(s) == 9 and re.match(r'7[2-9]', s):
        kind = 'voip'
    elif len(s) == 8 and re.match(r'[2-489]', s):
        kind = 'landline'
    elif s[:1] in '23489' and len(s) > 8 or len(s) > 9:
        return PhoneResult(False, reason='LONG')
    else:
        return PhoneResult(False, reason='SHORT' if len(s) < 8 else 'BAD_PREFIX')
    return PhoneResult(True, e164='+972' + s, kind=kind)


def phone_e164(text: str) -> str | None:
    return parse_phone(text).e164


def norm_address(text: str, locale: str = 'he') -> str:
    s = unicodedata.normalize('NFC', text or '')
    s = _INVISIBLE.sub(' ', s)
    s = _DASHES.sub('-', s)
    s = fold_digits(s)
    s = _HEBREW_MARKS.sub('', s)
    s = _ARABIC_MARKS.sub('', s)
    # Keep "רח'" and 'ר"ח' recognisable before quotes are stripped.
    s = re.sub(r"\bר[\"\u05F4]ח\b", 'רחוב', s)
    s = re.sub(r"\bרח['\u05F3]", 'רחוב', s)
    s = re.sub(r"\bשד['\u05F3]", 'שדרות', s)
    s = _QUOTES.sub('', s)
    s = re.sub('[أإآ]', 'ا', s)
    s = re.sub('[ىئ]', 'ي', s)
    s = s.replace('ة', 'ه')
    s = s.lower()
    s = _PUNCT.sub(' ', s)
    tokens = []
    for tok in s.split():
        if tok in _HE_NUM:
            tokens.append(_HE_NUM[tok])
        elif tok in _AR_NUM:
            tokens.append(_AR_NUM[tok])
        elif tok in _HE_PREFIX:
            tokens.append(_HE_PREFIX[tok])
        elif tok in _AR_PREFIX:
            tokens.append(_AR_PREFIX[tok])
        else:
            m = re.match(r'^[בלמה](.+)$', tok)          # "ברחוב" / "לדרך": prefix letter + street word
            if m and (m.group(1) in _HE_STREET_WORDS or m.group(1) in _HE_PREFIX):
                tokens.append(_HE_PREFIX.get(m.group(1), m.group(1)))
            else:
                tokens.append(tok)
    return ' '.join(tokens).strip()


def addr_key(text: str, locale: str = 'he') -> str:
    """Comparison key: the readable normalised form with Hebrew final letters folded (ם/מ, ן/נ ...)."""
    return norm_address(text, locale).translate(_FINALS)


def addr_matches(a: str, b: str, locale: str = 'he') -> bool:
    na, nb = addr_key(a, locale), addr_key(b, locale)
    if not na or not nb:
        return False
    if na == nb:
        return True
    return sorted(na.split()) == sorted(nb.split())      # "יפו 5 רחוב" == "רחוב יפו 5"


def addr_contains(page_text: str, canon_addr: str) -> bool:
    """A page mentions the canon address when its normalised tokens appear together (city may be absent on page)."""
    page = addr_key(page_text)
    want = addr_key(canon_addr).split()
    if not want:
        return False
    # Require street word(s) + number; the city, when the canon has one, is optional on the page.
    core = [t for t in want if not (t.isalpha() and len(want) > 3 and t == want[-1])]
    return all(t in page.split() for t in core)


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
        parsed = parse_phone(m.group(0))
        if parsed.ok:
            add('phone', parsed.e164, m.group(0))
    for m in _EMAIL.finditer(text):
        add('email', m.group(0).lower(), m.group(0))
    for m in _STREET.finditer(text):
        add('address', norm_address(m.group(0)), m.group(0))
    for m in _HOURS.finditer(text):
        add('hours', re.sub(r'\s+', ' ', m.group(0)).strip(), m.group(0))
    for m in _NAME.finditer(text):
        add('name', m.group(1).strip(), m.group(0))
    # Reviews the customer GAVE: a quote followed by a dash and a name ("הקפה הכי טוב בחיפה" – דנה).
    for m in _QUOTE.finditer(text):
        add('review', norm_quote(m.group(1)), m.group(0))
    return canon


# A review the customer gave: a quote, a dash and a short name (1-3 words), then a separator.
_QUOTE = re.compile(r'[“"„\u05F4]([^”"\u05F4\n]{8,200})[”"\u05F4]\s*[–—-]\s*'
                    r'((?:[\u0590-\u05FF\w\'\u05F3]+\s?){1,3}?)(?=\s*(?:[•\n"“]|\d+\.|$))')


def norm_quote(text: str) -> str:
    """Comparison form of a review quote: no punctuation, single spaces, final letters folded."""
    t = re.sub(r'[^\w\s\u0590-\u05FF]', ' ', text or '')
    return re.sub(r'\s+', ' ', t).strip().lower().translate(_FINALS)


def page_phones(page_text: str) -> tuple[set[str], list[str]]:
    """(E.164 numbers the page shows, spans that looked like phones but did not parse: AMBIGUOUS, SERVICE, ...).

    Only parsed numbers are compared with the canon. A business that prints "1234567" with no prefix is AMBIGUOUS and
    must not block (Michael: blocking on that is exactly the waste we documented); it is reported, not enforced."""
    ok, odd = set(), []
    for m in _PHONE.finditer(page_text or ''):
        parsed = parse_phone(m.group(0))
        if parsed.ok:
            ok.add(parsed.e164)
        elif parsed.reason in ('AMBIGUOUS', 'LONG', 'BAD_PREFIX'):
            odd.append(f'{m.group(0).strip()} ({parsed.reason})')
    return ok, odd


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


# ---- the canon on the approval screen (Michael 2026-11-10 condition 2) ----
_LABELS = {'he': {'phone': 'טלפון', 'address': 'כתובת', 'email': 'מייל', 'hours': 'שעות', 'name': 'שם'},
           'en': {'phone': 'phone', 'address': 'address', 'email': 'e-mail', 'hours': 'hours', 'name': 'name'}}
_TEXT = {
    'he': {'facts': 'פרטי העסק שיופיעו באתר (מתוך מה שכתבתם): {facts}.',
           'incomplete': 'אזהרה: לא כתבתם {missing}. בלי זה הם לא יופיעו באתר (לא נמציא אותם). '
                         'אפשר להוסיף עכשיו בהודעה, או לאשר בלעדיהם.'},
    'en': {'facts': 'Business details that will appear on the site (from what you wrote): {facts}.',
           'incomplete': 'Warning: you did not give {missing}. They will not appear on the site (we never invent them). '
                         'Add them now in a message, or approve without them.'},
}


def canon_view(request_text: str, *, family: str | None = None, lang: str = 'he') -> dict:
    """What the brief approval screen shows: every fact with its source span, approved together with the brief.

    For a business website an empty phone AND address is CANON_INCOMPLETE -- a warning the customer sees, never a
    silent pass (a canon with nothing in it makes the truth gate pass "happily")."""
    lang = lang if lang in _TEXT else 'en'
    canon = build_canon(request_text)
    shown = [f for f in canon.facts if f.key in ('phone', 'address', 'email', 'hours')]
    labels = _LABELS.get(lang, _LABELS['en'])
    lines = []
    if shown:
        lines.append(_TEXT[lang]['facts'].format(
            facts='; '.join(f'{labels[f.key]}: {f.source_ref}' for f in shown)))
    status = 'OK'
    if family in (None, 'website', 'landing', 'content') and not (canon.values('phone') or canon.values('address')):
        status = 'CANON_INCOMPLETE'
        missing = f"{labels['phone']} {'או' if lang == 'he' else 'or'} {labels['address']}"
        lines.append(_TEXT[lang]['incomplete'].format(missing=missing))
    return {'status': status, 'hash': canon.hash, 'facts': [f.to_dict() for f in shown], 'lines': lines,
            'issues': validate_canon(canon, request_text)}
