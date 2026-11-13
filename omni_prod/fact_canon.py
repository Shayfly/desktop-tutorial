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


def fact_spans(text: str) -> list[str]:
    """#335 (Michael 2026-11-13): the customer's own spans for facts a page may show -- phone, e-mail, address,
    opening hours (a closed day included) -- verbatim, in order, without duplicates. Read from EVERY customer
    message, so a fact the brief's fields lose in the conversation still reaches the approved request and the canon."""
    from .opening_hours import spans as hour_spans
    clean = decode_entities(text or '')
    found = [m.group(0) for m in _PHONE.finditer(clean) if parse_phone(m.group(0)).ok]
    found += [m.group(0) for m in _EMAIL.finditer(clean)]
    found += [m.group(0) for m in _STREET.finditer(clean)]
    found += hour_spans(clean)
    out = []
    for span in (' '.join(f.split()).strip() for f in found):
        if span and span not in out:
            out.append(span)
    return out


def build_canon(request_text: str, *, source: str = 'brief') -> Canon:
    """Every phone, address, e-mail, opening-hours span and declared name in the approved request."""
    # Entities are decoded on BOTH sides before any comparison (Michael 2026-11-10): the request may carry &amp; or
    # &nbsp; just as the page does. source_ref keeps the decoded span; the hash keeps the raw text.
    raw = request_text or ''
    text = decode_entities(raw)
    canon = Canon(source_hash=hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16])
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
    # #335 (Michael 2026-11-13): hours per DAY, including a day the customer said is closed ("שבת סגור"), so the
    # truth gate can compare a page's hours with the customer's -- the raw 'hours' spans above never could.
    from .opening_hours import encode, parse, spans
    for span in spans(text):
        for value in sorted(encode(parse(span))):
            add('hours_day', value, span)
    for m in _NAME.finditer(text):
        add('name', m.group(1).strip(), m.group(0))
    # Reviews the customer GAVE: a quote followed by a dash and a name ("הקפה הכי טוב בחיפה" – דנה). The value is
    # "<normalised text>|<normalised author>"; a page review matches only when BOTH are identical after normalisation.
    for m in _QUOTE.finditer(text):
        add('review', norm_quote(m.group(1)) + '|' + norm_quote(m.group(2)), m.group(0))
    # Typed counts the customer gave ("מעל 50 ביקורות" -> reviewCount 50, "4.9 כוכבים" -> rating 4.9).
    for kind, value, ref in count_facts(text):
        add(kind, value, ref)
    return canon


# A review the customer gave: a quote, a dash and a short name (1-3 words), then a separator.
_QUOTE = re.compile(r'[“"„\u05F4]([^”"\u05F4\n]{8,200})[”"\u05F4]\s*[–—-]\s*'
                    r'((?:[\u0590-\u05FF\w\'\u05F3]+\s?){1,3}?)(?=\s*(?:[•\n"“]|\d+\.|$))')


# The number must stand alone: "14:00 ביקורות" (hours, then the word) is not "00 reviews" -- the golden fixture caught it.
# Typed count facts (Michael 2026-11-10): a claim is compared with a fact of the SAME type, never with "the number
# appears somewhere in the request" -- "50 מנות" in the request must not source "50 ביקורות" on the page.
_COUNT_TYPES = (
    ('reviewCount', r'ביקורות|חוות דעת|המלצות|reviews?'),
    ('rating', r'כוכבים|stars?|דירוג|rating'),
    ('customerCount', r'לקוחות מרוצים|לקוחות|happy customers|customers'),
)
# The number must stand alone: "14:00 ביקורות" (hours, then the word) is not "00 reviews" -- the golden fixture caught it.
_AGGREGATE = re.compile(r'(?<![\d:.,\-–])(\d+(?:[.,]\d+)?)\s*\+?\s*(' + '|'.join(p for _, p in _COUNT_TYPES) + r')', re.I)
_RATING_FIRST = re.compile(r'(?:דירוג|rating)\s*(?:של\s*)?(\d(?:[.,]\d)?)', re.I)


def count_type(noun: str) -> str:
    for kind, pattern in _COUNT_TYPES:
        if re.fullmatch(pattern, noun.strip(), re.I):
            return kind
    return 'count'


def aggregate_key(m) -> tuple[str, str]:
    """(fact type, value): ('reviewCount', '50'), ('rating', '4.9')."""
    return count_type(m.group(2)), m.group(1).replace(',', '.')


def count_facts(text: str) -> list[tuple[str, str, str]]:
    out = [(*aggregate_key(m), m.group(0)) for m in _AGGREGATE.finditer(text or '')]
    out += [('rating', m.group(1).replace(',', '.'), m.group(0)) for m in _RATING_FIRST.finditer(text or '')]
    return out


def decode_entities(text: str) -> str:
    """Every HTML entity (named, decimal, hex) to its character; non-breaking and other invisible spaces to a space."""
    import html
    return _INVISIBLE.sub(' ', html.unescape(text or ''))


def norm_quote(text: str) -> str:
    """Comparison form of a review quote: no punctuation, single spaces, final letters folded."""
    t = unicodedata.normalize('NFC', decode_entities(text))
    t = _HEBREW_MARKS.sub('', t)
    t = re.sub(r'[^\w\s\u0590-\u05FF]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip().lower().translate(_FINALS)


def page_phones(page_text: str) -> tuple[set[str], list[str]]:
    """(E.164 numbers the page shows, spans that looked like phones but did not parse: AMBIGUOUS, SERVICE, ...).

    Only parsed numbers are compared with the canon. A business that prints "1234567" with no prefix is AMBIGUOUS and
    must not block (Michael: blocking on that is exactly the waste we documented); it is reported, not enforced."""
    ok, odd = set(), []
    for m in _PHONE.finditer(page_text or ''):
        parsed = parse_phone(m.group(0))
        if not parsed.ok:
            # #335 (2026-11-13): a time just before a phone ("13:00    04-9999999") was read as one number that does
            # not parse, and the phone escaped the truth gate. Try what follows each gap inside the span.
            for gap in re.finditer(r'\s+', m.group(0)):
                tail = parse_phone(m.group(0)[gap.end():])
                if tail.ok:
                    parsed = tail
                    break
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
        if f.source == 'brief' and f.source_ref and f.source_ref not in decode_entities(request_text):
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
    # #335 (Michael 2026-11-13): the hours shown are the customer's own hours statements -- every one, a closed day
    # included. The 'hours' fact needs a time range, so "שבת סגור" was missing from the approval screen (production,
    # "מאפייה") while the truth gate already held it as an hours_day fact. One entry per statement, in order.
    stated = list(dict.fromkeys(f.source_ref for f in canon.facts if f.key == 'hours_day'))
    if stated:
        items = [f'{labels[f.key]}: {f.source_ref}' for f in shown if f.key != 'hours']
        items.append(f"{labels['hours']}: " + ', '.join(stated))
        lines[:1 if shown else 0] = [_TEXT[lang]['facts'].format(facts='; '.join(items))]
    status = 'OK'
    if family in (None, 'website', 'landing', 'content') and not (canon.values('phone') or canon.values('address')):
        status = 'CANON_INCOMPLETE'
        missing = f"{labels['phone']} {'או' if lang == 'he' else 'or'} {labels['address']}"
        lines.append(_TEXT[lang]['incomplete'].format(missing=missing))
    return {'status': status, 'hash': canon.hash, 'facts': [f.to_dict() for f in shown], 'lines': lines,
            'issues': validate_canon(canon, request_text)}


# ---- #335 part 2 (c), Michael 2026-11-13: a fact the PAGE NEEDS and the customer did not give ----------------------
# The customer asked for something that shows a fact -- a call / WhatsApp button needs a phone, an opening-hours
# section needs hours -- and the fact is missing. Gate 1 asks once (with the approval checkbox, as CANON_INCOMPLETE);
# approving without it omits that part of the page (requirements_text says so), never invents it.
_NEEDS = {
    'phone': re.compile(r'התקשרו|להתקשר|לחייג|מחייג|חיוג|וואטסאפ|ווטסאפ|whats\s*app|call\s+(?:us|button|now)|'
                        r'click[- ]to[- ]call', re.I),
    'hours': re.compile(r'שעות\s+(?:ה)?(?:פתיחה|פעילות)|opening\s+hours|business\s+hours', re.I),
}
_PROVIDES = {'phone': ('phone',), 'hours': ('hours', 'hours_day')}
OMIT = {'phone': 'phone -- show no call or WhatsApp button and no phone number anywhere',
        'hours': 'opening hours -- leave out the opening-hours section and any day or time'}
_NEEDED_TEXT = {
    'he': {'needed': 'ביקשתם {what}, אבל לא כתבתם {fact}. מה {fact}? אפשר לכתוב בהודעה, או לאשר בנייה בלעדיו — '
                     'ואז {omit} (לא נמציא).',
           'what': {'phone': 'כפתור חיוג או וואטסאפ', 'hours': 'אזור שעות פתיחה'},
           'fact': {'phone': 'מספר הטלפון', 'hours': 'שעות הפתיחה'},
           'omit': {'phone': 'הכפתור והמספר לא יופיעו', 'hours': 'אזור השעות יושמט'}},
    'en': {'needed': 'You asked for {what}, but did not give {fact}. What is it? Send it in a message, or approve '
                     'building without it -- then {omit} (we never invent it).',
           'what': {'phone': 'a call or WhatsApp button', 'hours': 'an opening-hours section'},
           'fact': {'phone': 'the phone number', 'hours': 'the opening hours'},
           'omit': {'phone': 'the button and the number are left out', 'hours': 'the hours section is left out'}},
}


def missing_needed(customer_text: str, canon: 'Canon') -> list[str]:
    """The facts the customer's own request needs on the page but never gave (order: phone, hours)."""
    return [k for k, rx in _NEEDS.items()
            if rx.search(customer_text or '') and not any(canon.values(f) for f in _PROVIDES[k])]


def gate_view(request_text: str, *, customer_text: str, family: str | None = None, lang: str = 'he') -> dict:
    """canon_view plus one question per missing needed fact. A missing needed fact makes the canon CANON_INCOMPLETE:
    approving needs the same explicit box, and the build omits that part."""
    view = canon_view(request_text, family=family, lang=lang)
    missing = missing_needed(customer_text, build_canon(request_text))
    t = _NEEDED_TEXT['he' if lang == 'he' else 'en']
    view['lines'] = list(view['lines']) + [t['needed'].format(what=t['what'][k], fact=t['fact'][k], omit=t['omit'][k])
                                           for k in missing]
    view['missing_needed'] = missing
    if missing:
        view['status'] = 'CANON_INCOMPLETE'
    return view


# ---- #335 part 2 (d), Michael 2026-11-13: a QA failure only the customer can fix stops the repair rounds ----------
# The page needs a fact (the customer asked for a call button / an hours section), the customer never gave it and did
# not approve building without it (a spec that did not pass gate 1's question: an older spec, a change request), and
# QA blocks the page for inventing it. A repair can only invent again or drop what was asked: stop and ask.
_INVENTED = {'phone': 'contact details not in the approved request (invented): +',
             'hours': 'opening hours the customer never gave (invented)'}
_OMITTED = {'phone': 'phone -- show no call', 'hours': 'opening hours -- leave out'}


def needs_customer_input(messages, prompt: str) -> list[str]:
    """The facts (phone, hours) a failing QA check needs from the customer: needed by the request, absent from the
    canon, not approved as omitted, and the failure is the truth gate refusing an invented one."""
    text = ' '.join(str(m) for m in messages or ())
    canon = build_canon(prompt or '')
    customer = (prompt or '').split('--- Approved project brief', 1)[0]
    return [k for k in missing_needed(customer, canon)
            if _INVENTED[k] in text and _OMITTED[k] not in (prompt or '')]
