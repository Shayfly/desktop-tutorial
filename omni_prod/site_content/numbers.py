"""Numbers as a reader reads them: digit runs AND Hebrew number words, each with what it counts.

A number on the page is a fact the customer gave, so it is checked twice (validate.INVENTED_NUMBER): its VALUE must be
one the customer wrote, and it must count the SAME THING the customer's number counted -- "3 עורכי דין" may become
"שלושה עורכי דין", never "3 עשורים"; a year ("מאז 2008") stays a year. `mentions(text)` finds every number in a text:
digit runs (Arabic-Indic digits folded, thousands separators normalised) and Hebrew cardinal words ("שלושה",
"עשרים ושלוש", "שלוש מאות", "אלפיים"), with the words right after it (what it counts) and right before it (a year's
"מאז"). Vague magnitudes ("מאות לקוחות", "אלפי תיקים", "עשרות", "עשורים") are mentions of kind 'vague': a size no
number of the customer's supports unless the customer used that word.

Words that are a number only sometimes are left out on purpose: "אחד/אחת" (one, a) and "ראשון" (first) are ordinary
words, and "שני/שתי" counts only before a noun and never after "יום" (Monday).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .. import fact_canon as F

UNITS = {'שניים': 2, 'שתיים': 2, 'שני': 2, 'שתי': 2, 'שלושה': 3, 'שלוש': 3, 'שלושת': 3, 'ארבעה': 4, 'ארבע': 4,
         'ארבעת': 4, 'חמישה': 5, 'חמש': 5, 'חמשת': 5, 'שישה': 6, 'שש': 6, 'ששת': 6, 'שבעה': 7, 'שבע': 7, 'שבעת': 7,
         'שמונה': 8, 'שמונת': 8, 'תשעה': 9, 'תשע': 9, 'תשעת': 9, 'עשרה': 10, 'עשר': 10, 'עשרת': 10}
TENS = {'עשרים': 20, 'שלושים': 30, 'ארבעים': 40, 'חמישים': 50, 'שישים': 60, 'שבעים': 70, 'שמונים': 80, 'תשעים': 90}
HUNDREDS = {'מאה': 100, 'מאתיים': 200}
THOUSANDS = {'אלף': 1000, 'אלפיים': 2000}
VAGUE = ('עשרות', 'מאות', 'אלפי', 'אלפים', 'רבבות', 'עשור', 'עשורים', 'מיליון', 'מיליוני', 'מליון', 'אינספור')
YEAR_WORDS = ('מאז', 'משנת', 'בשנת', 'שנת', 'נוסד', 'נוסדה', 'נוסדנו', 'הוקם', 'הוקמה', 'הקמה', 'פועל', 'פועלת',
              'פועלים', 'since', 'founded', 'est')
PREFIXES = 'ובלמהשכ'
_FINALS = str.maketrans('םןץףך', 'מנצפכ')
_TOKEN = re.compile(r"[א-ת]+(?:[\"'׳״][א-ת]+)?|\d[\d,.]*\d|\d|[A-Za-z]+|[,.;:!?\n()]")
_CLAUSE_END = set(',.;:!?\n()')


@dataclass(frozen=True)
class Mention:
    value: str | None          # '3', '1500', '2008'; None for a vague magnitude
    kind: str                  # 'digits' | 'word' | 'vague'
    text: str                  # as written
    start: int
    end: int
    after: tuple[str, ...]     # up to two words after it, inside its clause
    before: tuple[str, ...]    # up to two words before it, inside its clause


def norm_number(raw: str) -> str:
    """A digit run as a reader compares it: digits folded, thousands separators and a trailing full stop dropped."""
    s = F.fold_digits(raw).rstrip('.')
    return re.sub(r'(?<=\d),(?=\d{3}\b)', '', s)


def forms(word: str) -> set[str]:
    """A Hebrew word with its final letters normalised, with and without one or two prefix letters (ו, ה, ב, ל, מ,
    ש, כ): what two spellings of the same noun share."""
    w = word.strip('"\'׳״-').translate(_FINALS).lower()
    out = {w}
    if len(w) > 3 and w[0] in PREFIXES:
        out.add(w[1:])
        if len(w) > 4 and w[1] in PREFIXES:
            out.add(w[2:])
    return out


def same_noun(a: str, b: str) -> bool:
    """True when two words are the same noun (the first four letters of some form agree, at least three)."""
    for x in forms(a):
        for y in forms(b):
            k = min(4, len(x), len(y))
            if k >= 3 and x[:k] == y[:k]:
                return True
    return False


def is_year(value: str | None) -> bool:
    return bool(value) and len(value) == 4 and value.isdigit() and 1900 <= int(value) <= 2099


_NUM_PREFIXES = 'ובלמכש'           # never ה: "המאה" is a century, "השני" is "the second"


def _nforms(token: str) -> list[str]:
    w = token.translate(_FINALS)
    out = [w]
    if len(w) > 2 and w[0] in _NUM_PREFIXES:
        out.append(w[1:])
        if len(w) > 3 and w[1] in _NUM_PREFIXES:
            out.append(w[2:])
    return out


def _word(token: str, table: dict) -> int | None:
    for w in _nforms(token):
        if w in table:
            return table[w]
    return None


def _plain(token: str) -> str:
    return token.translate(_FINALS)


def _tables():
    fin = lambda t: {k.translate(_FINALS): v for k, v in t.items()}          # noqa: E731
    return fin(UNITS), fin(TENS), fin(HUNDREDS), fin(THOUSANDS)


_UNITS, _TENS, _HUNDREDS, _THOUSANDS = _tables()
_VAGUE = {v.translate(_FINALS) for v in VAGUE}


def _parse_words(tokens: list, i: int) -> tuple[int | None, int]:
    """(value, tokens used) of a Hebrew cardinal starting at tokens[i]; (None, 0) when it is not one."""
    t = tokens[i].group(0)
    nxt = tokens[i + 1].group(0) if i + 1 < len(tokens) else ''
    u = _word(t, _UNITS)
    if u is not None:
        prev = tokens[i - 1].group(0) if i else ''
        if u == 2 and t not in ('שניים', 'שתיים', 'ושניים', 'ושתיים'):
            # "שני/שתי" counts only as written, before a noun, and never in "יום שני" (Monday)
            if t not in ('שני', 'שתי', 'ושני', 'ושתי') or not re.fullmatch('[א-ת]+', nxt or '-') \
                    or _plain(prev) in ('יומ', 'ביומ', 'מיומ'):
                return None, 0
        if u == 7 and 'באר' in forms(prev):                         # באר שבע is a city
            return None, 0
        if _plain(nxt) in ('עשר', 'עשרה') and u < 10:
            return u + 10, 2
        if _plain(nxt) == 'מאות':
            return u * 100, 2
        if _plain(nxt) in ('אלפימ', 'אלפ'):
            return u * 1000, 2
        return u, 1
    for table in (_TENS, _HUNDREDS, _THOUSANDS):
        v = _word(t, table)
        if v is not None:
            used = 1
            if nxt.startswith('ו') and len(nxt) > 2:
                rest = nxt[1:]
                extra = _word(rest, _UNITS) or _word(rest, _TENS) or _word(rest, _HUNDREDS)
                if extra is not None and extra < v:
                    return v + extra, 2
            return v, used
    return None, 0


def _around(tokens: list, i: int, j: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    after, before = [], []
    for t in tokens[j:j + 3]:
        if t.group(0) in _CLAUSE_END:
            break
        if re.fullmatch(r'[א-תA-Za-z"\'׳״]{2,}', t.group(0)):
            after.append(t.group(0))
        if len(after) == 2:
            break
    for t in reversed(tokens[max(0, i - 3):i]):
        if t.group(0) in _CLAUSE_END:
            break
        if re.fullmatch(r'[א-תA-Za-z"\'׳״]{2,}', t.group(0)):
            before.append(t.group(0))
        if len(before) == 2:
            break
    return tuple(after), tuple(reversed(before))


def mentions(text: str) -> list[Mention]:
    """Every number in a text, digit runs and Hebrew words, in order."""
    folded = F.fold_digits(text or '')
    tokens = list(_TOKEN.finditer(folded))
    out: list[Mention] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        raw = tok.group(0)
        if raw[0].isdigit():
            after, before = _around(tokens, i, i + 1)
            out.append(Mention(norm_number(raw), 'digits', raw, tok.start(), tok.end(), after, before))
            i += 1
            continue
        if re.fullmatch('[א-ת]+', raw):
            value, used = _parse_words(tokens, i)
            if value is not None:
                after, before = _around(tokens, i, i + used)
                end = tokens[i + used - 1].end()
                out.append(Mention(str(value), 'word', folded[tok.start():end], tok.start(), end, after, before))
                i += used
                continue
            if any(w in _VAGUE for w in _nforms(raw)):
                after, before = _around(tokens, i, i + 1)
                out.append(Mention(None, 'vague', raw, tok.start(), tok.end(), after, before))
        i += 1
    return out


def year_word_near(m: Mention) -> bool:
    return any(any(f.startswith(y) for y in YEAR_WORDS for f in forms(w)) for w in m.before + m.after)
