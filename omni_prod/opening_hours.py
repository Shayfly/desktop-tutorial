"""Opening hours as facts (#335, Michael 2026-11-13).

Build bld_cf406df6 ("בית קפה", 2026-11-12): the customer wrote "א׳–ה׳ 07:00–19:00, ו׳ 07:00–14:00, שבת סגור". The
values were lost in the conversation, and the page said "שבת 08:00–16:00" -- invented, and contradicting an explicit
request. The truth gate compared phones, addresses and reviews; it never looked at hours.

`parse` reads day specs followed by a time range or "closed", in Hebrew and English:
  "א׳–ה׳ 07:00–19:00", "ראשון - חמישי 07:30 - 18:00", "יום ו' 7:00-14:00", "שבת סגור", "Sun-Thu 8:00-17:00", "Saturday closed"
into {day: (open_minutes, close_minutes) | CLOSED}, Sunday = 0 ... Saturday = 6.
`compare(page, canon)` returns what the page shows that the customer did not say:
  invented     -- the page shows hours for a day the customer gave nothing for (or the customer gave no hours at all)
  contradicted -- the page's hours for a day differ from the customer's, or the customer said that day is closed.
"""
from __future__ import annotations

import re

CLOSED = 'closed'

_DAY_WORDS = {
    0: ('ראשון', "א'", 'א׳', 'sunday', 'sun'),
    1: ('שני', "ב'", 'ב׳', 'monday', 'mon'),
    2: ('שלישי', "ג'", 'ג׳', 'tuesday', 'tue', 'tues'),
    3: ('רביעי', "ד'", 'ד׳', 'wednesday', 'wed'),
    4: ('חמישי', "ה'", 'ה׳', 'thursday', 'thu', 'thur', 'thurs'),
    5: ('שישי', "ו'", 'ו׳', 'friday', 'fri'),
    6: ('שבת', "ש'", 'ש׳', 'saturday', 'sat'),
}
_LOOKUP = {w: d for d, words in _DAY_WORDS.items() for w in words}
_DAY_ALT = '|'.join(sorted((re.escape(w) for w in _LOOKUP), key=len, reverse=True))
_DAY = rf"(?:יום\s+|ימי\s+)?(?P<{{n}}>{_DAY_ALT})(?![֐-׿a-z])"
_SEP = r'\s*(?:[-–—]|עד|to|through)\s*'
_TIME = r'(\d{1,2})(?::|\.)(\d{2})'
_SPEC = re.compile(
    _DAY.format(n='d1') + rf'(?:{_SEP}' + _DAY.format(n='d2') + r')?'
    + r'[\s:,]*(?:' + rf'(?P<t>{_TIME}{_SEP}{_TIME})' + r'|(?P<closed>סגור(?:ה|ים)?|closed))',
    re.I)


def _minutes(h: str, m: str) -> int:
    return int(h) * 60 + int(m)


def _day(word: str) -> int:
    word = word.lower()
    return _LOOKUP[word] if word in _LOOKUP else _LOOKUP[word + "'"]      # a bare letter of a range ("א-ה")


def _days(first: str, last: str | None) -> list[int]:
    a = _day(first)
    if last is None:
        return [a]
    b = _day(last)
    return list(range(a, b + 1)) if a <= b else list(range(a, 7)) + list(range(0, b + 1))


# "א-ה 07:00-14:00": a bare letter RANGE (very common); a single bare letter is never read as a day
_BARE = re.compile(r"(?<![\u0590-\u05FF])(?P<d1>[אבגדהוש])\s*[-–—]\s*(?P<d2>[אבגדהוש])(?![\u0590-\u05FF׳'])"
                   + r'[\s:,]*(?:' + rf'(?P<t>{_TIME}{_SEP}{_TIME})' + r'|(?P<closed>סגור(?:ה|ים)?|closed))', re.I)


def _matches(text: str):
    """Every hours statement, on the ORIGINAL text (spans stay verbatim), in order, without overlaps."""
    found = sorted([m for rx in (_SPEC, _BARE) for m in rx.finditer(text or '')], key=lambda m: (m.start(), -m.end()))
    out, last = [], -1
    for m in found:
        if m.start() >= last:
            out.append(m)
            last = m.end()
    return out


def spans(text: str) -> list[str]:
    """The raw spans that state hours -- substrings of the text, the customer's own words."""
    return [m.group(0).strip() for m in _matches(text)]


def parse(text: str) -> dict[int, object]:
    out: dict[int, object] = {}
    for m in _matches(text):
        value: object = CLOSED
        if m.group('t'):
            times = re.findall(_TIME, m.group('t'))
            value = (_minutes(*times[0]), _minutes(*times[1]))
        for day in _days(m.group('d1'), m.group('d2')):
            out[day] = value
    return out


def encode(hours: dict[int, object]) -> set[str]:
    """Canon values: "0:420-1140", "6:closed"."""
    return {f'{d}:{CLOSED}' if v == CLOSED else f'{d}:{v[0]}-{v[1]}' for d, v in hours.items()}


def decode(values) -> dict[int, object]:
    out = {}
    for v in values or ():
        day, _, rest = str(v).partition(':')
        if rest == CLOSED:
            out[int(day)] = CLOSED
        else:
            a, _, b = rest.partition('-')
            out[int(day)] = (int(a), int(b))
    return out


_NAMES = ('ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת')


def _show(v) -> str:
    return 'סגור' if v == CLOSED else f'{v[0] // 60:02d}:{v[0] % 60:02d}-{v[1] // 60:02d}:{v[1] % 60:02d}'


def compare(page: dict[int, object], canon: dict[int, object]) -> tuple[list[str], list[str]]:
    """(invented, contradicted) as readable lines; both empty when every day on the page is the customer's."""
    invented, contradicted = [], []
    # a day the customer said is CLOSED comes first: opening it is the most serious contradiction
    for day in sorted(page, key=lambda d: (canon.get(d) != CLOSED, d)):
        shown = page[day]
        if day not in canon:
            invented.append(f'{_NAMES[day]} {_show(shown)}')
        elif shown != canon[day]:
            contradicted.append(f'{_NAMES[day]}: הדף {_show(shown)}, הלקוח {_show(canon[day])}')
    return invented, contradicted
