"""Scripts and font pairs (warehouse 129, the script layer; warehouse 126, the font-pair library; the owner, 2026-11-22).

Until now the content route used Heebo everywhere: the brief's Design line names one font, its default is Heebo, and
the page used it for the body and for every heading. Here the unit is the script (scripts.json): Hebrew, Arabic and
Latin are supported -- each with its direction, its date, number and currency formats and its heading limits -- and
Cyrillic, Greek, CJK, Indic and Thai are declared but not supported. A page gets one pair of fonts from the library
(font_pairs.json): the business's category gives the art direction (its tone), the tone allows two of the script's
four pairs, and the business itself (its name) picks one of the two -- the same business always the same pair.

Nothing here falls back: a script not declared raises UnknownScript, a declared one without support raises
UnsupportedScript (never Latin), a font family that is not in the script's library raises FontNotInLibrary, a heading
longer than its script's limit raises HeadingTooLong, a currency the script does not list raises. The registry and
the library are checked when this module is imported; a malformed file fails the import.
"""
from __future__ import annotations

import datetime
import hashlib
import html as _html
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
_REGISTRY = json.loads((HERE / 'scripts.json').read_text(encoding='utf-8'))
_LIBRARY = json.loads((HERE / 'font_pairs.json').read_text(encoding='utf-8'))
DECLARED: dict = _REGISTRY['scripts']
TONES: tuple = tuple(_LIBRARY['tones'])
WEIGHTS = (400, 700)                       # the design contract's two weights (g_apple.contract.WEIGHTS)
GENERIC = frozenset({'serif', 'sans-serif', 'system-ui', 'monospace', 'cursive', 'fantasy', 'ui-serif',
                     'ui-sans-serif', 'ui-monospace', 'ui-rounded'})
_SUPPORTED_KEYS = {'supported', 'direction', 'lang', 'og_locale', 'languages', 'blocks', 'heading_max_chars', 'date',
                   'number', 'currency', 'sample'}
_DECLARED_KEYS = {'supported', 'direction', 'languages', 'blocks', 'why'}
HEADINGS = ('h1', 'h2', 'h3', 'h4')


class ScriptError(ValueError):
    """A script cannot be used as asked."""


class UnknownScript(ScriptError):
    """A script, or a language, the registry does not declare."""


class UnsupportedScript(ScriptError):
    """A script the registry declares but does not support yet: it never falls back to another script."""


class FontNotInLibrary(ValueError):
    """A font family, or a pair, that is not in the script's library."""


class HeadingTooLong(ValueError):
    """A heading longer than its script's limit."""


# ---- the registry and the library, checked on import --------------------------------------------------------------
def _ranges(blocks: list[str]) -> list[tuple[int, int]]:
    out = []
    for b in blocks:
        m = re.fullmatch(r'([0-9A-F]{4})-([0-9A-F]{4})', b)
        if not m or int(m.group(1), 16) > int(m.group(2), 16):
            raise ScriptError(f'not a code-point range: {b!r}')
        out.append((int(m.group(1), 16), int(m.group(2), 16)))
    return out


def _check() -> None:
    for name, s in DECLARED.items():
        keys = _SUPPORTED_KEYS if s.get('supported') is True else _DECLARED_KEYS
        if set(s) != keys:
            raise ScriptError(f'script {name!r}: keys {sorted(set(s) ^ keys)} differ from {sorted(keys)}')
        if s['direction'] not in ('rtl', 'ltr'):
            raise ScriptError(f'script {name!r}: direction {s["direction"]!r}')
        _ranges(s['blocks'])
        if s['supported'] is not True:
            continue
        if sorted(s['heading_max_chars']) != sorted(HEADINGS) or not all(
                isinstance(v, int) and v > 0 for v in s['heading_max_chars'].values()):
            raise ScriptError(f'script {name!r}: heading_max_chars needs a positive limit for each of {HEADINGS}')
        if sorted(re.findall(r'DD|MM|YYYY', s['date'])) != ['DD', 'MM', 'YYYY'] or \
                re.sub(r'DD|MM|YYYY', '', s['date']).strip('./-') != '':
            raise ScriptError(f'script {name!r}: date pattern {s["date"]!r} (DD, MM and YYYY once each, . / - between)')
        if set(s['number']) != {'group', 'decimal'} or s['number']['group'] == s['number']['decimal']:
            raise ScriptError(f'script {name!r}: number format {s["number"]!r}')
        c = s['currency']
        if set(c) != {'position', 'space', 'symbols'} or c['position'] not in ('before', 'after') or not c['symbols']:
            raise ScriptError(f'script {name!r}: currency format {c!r}')
    langs = [lang for s in DECLARED.values() for lang in s['languages']]
    if len(langs) != len(set(langs)):
        raise ScriptError('a language belongs to two scripts')
    if set(_LIBRARY['pairs']) != {n for n, s in DECLARED.items() if s['supported'] is True}:
        raise FontNotInLibrary('every supported script, and only those, has font pairs')
    owner: dict[str, str] = {}
    ids = set()
    for name, pairs in _LIBRARY['pairs'].items():
        for p in pairs:
            if set(p) != {'id', 'tones', 'display', 'body'} or p['id'] in ids:
                raise FontNotInLibrary(f'pair {p.get("id")!r}: malformed or repeated')
            ids.add(p['id'])
            if not p['tones'] or set(p['tones']) - set(TONES):
                raise FontNotInLibrary(f'pair {p["id"]!r}: tones {p["tones"]!r} not in {TONES}')
            for role in ('display', 'body'):
                f = p[role]
                if set(f) != {'family', 'fallback', 'weights'}:
                    raise FontNotInLibrary(f'pair {p["id"]!r} {role}: keys {sorted(f)}')
                allowed = ([400, 700],) if role == 'body' else ([400, 700], [400])
                if f['weights'] not in allowed:
                    raise FontNotInLibrary(f'pair {p["id"]!r} {role}: weights {f["weights"]} (the contract has {WEIGHTS})')
                if set(x.strip() for x in f['fallback'].split(',')) - GENERIC:
                    raise FontNotInLibrary(f'pair {p["id"]!r} {role}: a fallback names a font ({f["fallback"]!r})')
                if owner.setdefault(f['family'], name) != name:
                    raise FontNotInLibrary(f'{f["family"]!r} is in the {owner[f["family"]]} and the {name} library: '
                                           'a page of one script would share a font with a page of the other')
        for tone in TONES:
            if len([p for p in pairs if tone in p['tones']]) < 2:
                raise FontNotInLibrary(f'{name}: fewer than two pairs for the tone {tone!r} (the business could not '
                                       'change the pair)')


_check()
_SPANS = {name: _ranges(s['blocks']) for name, s in DECLARED.items()}


# ---- scripts ----------------------------------------------------------------------------------------------------------
def script(name: str) -> dict:
    """A supported script's entry. Not declared -> UnknownScript; declared but not supported -> UnsupportedScript."""
    if name not in DECLARED:
        raise UnknownScript(f'script {name!r} is not declared (declared: {sorted(DECLARED)})')
    s = DECLARED[name]
    if s['supported'] is not True:
        raise UnsupportedScript(f'script {name!r} is declared but not supported: {s["why"]}')
    return s


def script_for_language(lang: str) -> str:
    """The script a language is written in ('he' -> 'hebrew'). A language no script declares raises."""
    for name, s in DECLARED.items():
        if lang in s['languages']:
            return name
    raise UnknownScript(f'no declared script writes the language {lang!r}')


_ADDRESS = re.compile(r'\S+@\S+|https?://\S+|www\.\S+', re.I)


def detect_script(text: str) -> str:
    """The script most of the text's letters are written in, and only a supported one: a text mostly in a declared
    but unsupported script raises UnsupportedScript, mostly in letters of no declared script raises UnknownScript,
    with no letters or with two scripts tied it raises ScriptError. Never Latin by default. E-mail and web addresses
    are not counted: they are written in Latin letters whatever the customer's language."""
    counts: dict[str, int] = {}
    for ch in _ADDRESS.sub(' ', text or ''):
        if not ch.isalpha():
            continue
        cp = ord(ch)
        name = next((n for n, spans in _SPANS.items() if any(a <= cp <= b for a, b in spans)), None)
        counts[name] = counts.get(name, 0) + 1
    if not counts:
        raise ScriptError('the text has no letters: its script cannot be told')
    top = max(counts.values())
    leaders = sorted(str(n) for n, c in counts.items() if c == top)
    if len(leaders) > 1:
        raise ScriptError(f'the text is as much {leaders[0]} as {leaders[1]}: its script cannot be told')
    name = next(n for n, c in counts.items() if c == top)
    if name is None:
        raise UnknownScript('most of the text is in letters of no declared script')
    script(name)                                   # an unsupported script raises here, never a fallback
    return name


def html_attrs(name: str) -> str:
    """The <html> tag's language and direction for a page of this script: 'lang="he" dir="rtl"'."""
    s = script(name)
    return f'lang="{s["lang"]}" dir="{s["direction"]}"'


# ---- formats ----------------------------------------------------------------------------------------------------------
def format_date(name: str, day: datetime.date) -> str:
    """A date as this script's pages write it (Hebrew and Arabic: 05/11/2026)."""
    pattern = script(name)['date']
    return (pattern.replace('YYYY', f'{day.year:04d}').replace('MM', f'{day.month:02d}')
            .replace('DD', f'{day.day:02d}'))


def format_number(name: str, value, decimals: int = 0) -> str:
    """An int or a Decimal with the script's group and decimal marks (a float is refused: money is never binary)."""
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise TypeError(f'a number to format is an int or a Decimal, not {type(value).__name__}')
    if not isinstance(decimals, int) or not 0 <= decimals <= 4:
        raise ValueError(f'decimals {decimals!r}')
    marks = script(name)['number']
    q = Decimal(value).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    sign, whole, frac = ('-' if q < 0 else ''), *f'{abs(q):.{decimals}f}'.partition('.')[::2]
    grouped = re.sub(r'(?<=\d)(?=(\d{3})+$)', marks['group'], whole)
    return sign + grouped + (marks['decimal'] + frac if decimals else '')


def format_money(name: str, value, currency: str, decimals: int = 0) -> str:
    """An amount with its currency symbol where this script puts it ("250 ₪" with a no-break space; "$250")."""
    c = script(name)['currency']
    if currency not in c['symbols']:
        raise ScriptError(f'a {name} page does not show the currency {currency!r} (it shows {sorted(c["symbols"])})')
    number, symbol = format_number(name, value, decimals), c['symbols'][currency]
    gap = ' ' if c['space'] else ''
    return f'{number}{gap}{symbol}' if c['position'] == 'after' else f'{symbol}{gap}{number}'


# ---- headings ---------------------------------------------------------------------------------------------------------
_HEADING = re.compile(r'<(h[1-6])\b[^>]*>(.*?)</\1\s*>', re.S | re.I)


def visible(text: str) -> str:
    """A plain text as a visitor reads it: every run of white space one space, none at either end. A heading's limit is
    counted on this, in both places that count it: check_headings on the rendered heading, and the content route's
    validator on a field as the page will show it (site_content/validate.py, after each price reference is replaced
    by the customer's span) -- so what the validator accepts is what the render accepts (the release review of
    2026-11-25: a heading that passed validation failed the build)."""
    return ' '.join((text or '').split())


def check_headings(markup: str, name: str) -> None:
    """Every <h1>..<h4> of the markup within its script's limit (visible characters); a longer one, or a heading level
    the script sets no limit for, raises HeadingTooLong naming each one."""
    limits = script(name)['heading_max_chars']
    over = []
    for tag, inner in _HEADING.findall(markup or ''):
        tag = tag.lower()
        text = visible(_html.unescape(re.sub(r'<[^>]+>', '', inner)))
        if tag not in limits:
            over.append(f'{tag} has no {name} limit: {text[:40]!r}')
        elif len(text) > limits[tag]:
            over.append(f'{tag} of {len(text)} characters, the {name} limit is {limits[tag]}: {text[:40]!r}')
    if over:
        raise HeadingTooLong('; '.join(over))


# ---- font pairs -------------------------------------------------------------------------------------------------------
def pairs(name: str) -> list[dict]:
    """The script's pairs, each with its 'script' added."""
    script(name)
    return [dict(p, script=name) for p in _LIBRARY['pairs'][name]]


def pair(pair_id: str) -> dict:
    for name in _LIBRARY['pairs']:
        for p in pairs(name):
            if p['id'] == pair_id:
                return p
    raise FontNotInLibrary(f'no font pair {pair_id!r} in the library')


def families(name: str) -> set[str]:
    return {p[role]['family'] for p in pairs(name) for role in ('display', 'body')}


def pair_for(name: str, *, category: str, tone: str, business: str) -> dict:
    """The pair of one business: its tone (the art direction of its category's palette) allows two of the script's
    pairs, and the business key -- its name, spaces collapsed, case folded -- picks one, the same every time. The
    category is part of the key, so one name in two trades need not get the same pair."""
    if tone not in TONES:
        raise ValueError(f'tone {tone!r} is not one of {TONES}')
    if not (category or '').strip():
        raise ValueError('a pair is chosen for a category; none was given')
    key = ' '.join((business or '').split()).casefold()
    if not key:
        raise ValueError('a pair is chosen for a business; no business key was given')
    eligible = sorted((p for p in pairs(name) if tone in p['tones']), key=lambda p: p['id'])
    digest = hashlib.sha256('|'.join((name, category.strip(), key)).encode('utf-8')).digest()
    return eligible[int.from_bytes(digest[:8], 'big') % len(eligible)]


def stack(face: dict) -> str:
    """A face as a CSS font-family value: "'Frank Ruhl Libre', serif"."""
    return f"'{face['family']}', {face['fallback']}"


def contract_fonts(p: dict) -> dict:
    """What g_apple.contract.build takes to lock a pair into the design contract."""
    return {'pair': p['id'], 'script': p['script'], 'body': stack(p['body']), 'display': stack(p['display'])}


def check_stack(value: str, name: str) -> None:
    """A CSS font-family value of a page of this script: every name in it is a family of the script's library or a
    generic family; anything else raises FontNotInLibrary."""
    known = families(name)
    for part in (value or '').split(','):
        family = part.strip().strip('\'"').strip()
        if not family:
            raise FontNotInLibrary(f'an empty font name in {value!r}')
        if family not in known and family not in GENERIC:
            raise FontNotInLibrary(f'the font {family!r} is not in the {name} library ({sorted(known)})')


def font_link(p: dict) -> str:
    """The pair's Google Fonts stylesheet (body first, then the display face; each with exactly its weights,
    display=swap), after the two preconnects the perf gates ask for."""
    faces = [p['body']] + ([p['display']] if p['display']['family'] != p['body']['family'] else [])
    families_q = '&'.join('family=' + quote(f['family'], safe='').replace('%20', '+') + ':wght@'
                          + ';'.join(str(w) for w in f['weights']) for f in faces)
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{families_q}&display=swap">')
