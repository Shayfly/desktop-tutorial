"""Scripts and font pairs (warehouse 129, the script layer; warehouse 126, the font-pair library; the owner, 2026-11-22).

Until now the content route used Heebo everywhere: the brief's Design line names one font, its default is Heebo, and
the page used it for the body and for every heading. Here the unit is the script (scripts.json): Hebrew, Arabic and
Latin are supported -- each with its direction, its date, number and currency formats and its heading limits -- and
Cyrillic, Greek, CJK, Indic and Thai are declared but not supported. A page gets one pair of fonts from the library
(font_pairs.json): the business's category gives the art direction (its tone), the tone allows at least
MIN_PAIRS_PER_TONE of the script's pairs, and the business itself (its name) picks one of them -- the same business
always the same pair. The owner, 2026-11-25 ("א. צריך שיהיה את כל המגוון"): the library offers the full range, so
different businesses get different, fitting pairs; a content-only site's customer is not asked which font at all.
Every family a pair names is on the library's allowed list ('families'): its licence (OFL or Apache 2.0), the scripts
its Google Fonts subsets cover and the weights served were read live, and a body face is always a text face.

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
                   'number', 'currency', 'sample', 'spacing'}
_DECLARED_KEYS = {'supported', 'direction', 'languages', 'blocks', 'why'}
HEADINGS = ('h1', 'h2', 'h3', 'h4')
# The owner, 2026-11-25 ("את כל המגוון"): every tone of every supported script offers at least this many pairs.
MIN_PAIRS_PER_TONE = 3
# The allowed list (font_pairs.json 'families'). LICENCES as google/fonts METADATA.pb writes them: the SIL Open Font
# License and Apache 2.0. A text face (text_face) may set the body; any other face -- a display or handwriting face,
# or one served in a single weight -- may set headings only, so a pair never has two display faces.
LICENCES = ('OFL', 'APACHE2')
FAMILY_KEYS = {'licence', 'source', 'categories', 'classifications', 'scripts', 'weights', 'read_on'}
DISPLAY_ONLY = frozenset({'DISPLAY', 'HANDWRITING'})


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


SPACING_OVERRIDE = {'mode', 'connected', 'letter_spacing', 'word_spacing', 'body_line_height', 'heading_line_height'}


def _check_spacing(name: str, sp: dict) -> None:
    """A script's spacing: 'library' (the section library's own CSS suits it) or 'override' (the page gets the values
    named here). A script whose letters connect (`connected`) may carry no letter-spacing: the library's headings are
    tracked tighter than normal, which breaks the joins of Arabic -- so it must override, with letter_spacing '0'."""
    if not isinstance(sp, dict) or sp.get('mode') not in ('library', 'override') or not isinstance(sp.get('connected'), bool):
        raise ScriptError(f'script {name!r}: spacing {sp!r} needs a mode (library | override) and connected (true | false)')
    if sp['mode'] == 'library':
        if set(sp) != {'mode', 'connected'}:
            raise ScriptError(f'script {name!r}: spacing mode library carries nothing else, not {sorted(sp)}')
        if sp['connected']:
            raise ScriptError(f'script {name!r}: its letters connect, so it needs the override: the library tracks headings '
                              'tighter than normal, which breaks the joins')
        return
    if set(sp) != SPACING_OVERRIDE:
        raise ScriptError(f'script {name!r}: spacing override needs exactly {sorted(SPACING_OVERRIDE)}, not {sorted(sp)}')
    if not re.fullmatch(r'0|-?\d+(\.\d+)?(em|px|rem)', sp['letter_spacing']) or not re.fullmatch(
            r'0|\d+(\.\d+)?(em|px|rem)', sp['word_spacing']):
        raise ScriptError(f'script {name!r}: letter_spacing {sp["letter_spacing"]!r} or word_spacing '
                          f'{sp["word_spacing"]!r} is not a CSS length')
    if sp['connected'] and sp['letter_spacing'] != '0':
        raise ScriptError(f'script {name!r}: its letters connect, so letter_spacing is 0, not {sp["letter_spacing"]!r}')
    for key in ('body_line_height', 'heading_line_height'):
        if isinstance(sp[key], bool) or not isinstance(sp[key], (int, float)) or not 1 <= sp[key] <= 3:
            raise ScriptError(f'script {name!r}: {key} {sp[key]!r} is not a number from 1 to 3')


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
        _check_spacing(name, s['spacing'])
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
                _check_face(p['id'], role, f, name)
        for tone in TONES:
            if len([p for p in pairs if tone in p['tones']]) < MIN_PAIRS_PER_TONE:
                raise FontNotInLibrary(f'{name}: fewer than {MIN_PAIRS_PER_TONE} pairs for the tone {tone!r} -- not '
                                       'the full range the owner decided on 2026-11-25')
    unused = sorted(set(_LIBRARY['families']) - set(owner))
    if unused:
        raise FontNotInLibrary(f'the allowed list names families no pair uses: {unused}')


def text_face(entry: dict) -> bool:
    """A family the body text may be set in: Google Fonts gives it a text category (not only display or handwriting),
    no display or handwriting classification, and it is served in both of the contract's weights."""
    return (bool(set(entry['categories']) - DISPLAY_ONLY) and not set(entry['classifications']) & DISPLAY_ONLY
            and entry['weights'] == list(WEIGHTS))


def _check_face(pair_id: str, role: str, face: dict, name: str) -> None:
    """One face of a pair against the allowed list: listed, its licence OFL or Apache 2.0, its script covered, the
    weights it loads served, and a body face a text face. Anything else raises FontNotInLibrary."""
    entry = _LIBRARY['families'].get(face['family'])
    if entry is None:
        raise FontNotInLibrary(f'pair {pair_id!r} {role}: {face["family"]!r} is not on the allowed list (families)')
    if set(entry) != FAMILY_KEYS:
        raise FontNotInLibrary(f'{face["family"]!r}: keys {sorted(set(entry) ^ FAMILY_KEYS)} differ from '
                               f'{sorted(FAMILY_KEYS)}')
    if entry['licence'] not in LICENCES:
        raise FontNotInLibrary(f'{face["family"]!r}: licence {entry["licence"]!r} is not one of {LICENCES}')
    if name not in entry['scripts']:
        raise FontNotInLibrary(f'{face["family"]!r} does not cover the {name} script (it covers {entry["scripts"]})')
    if set(face['weights']) - set(entry['weights']):
        raise FontNotInLibrary(f'pair {pair_id!r} {role}: weights {face["weights"]}, but {face["family"]!r} is served in '
                               f'{entry["weights"]} only')
    if role == 'body' and not text_face(entry):
        raise FontNotInLibrary(f'pair {pair_id!r}: {face["family"]!r} is a display face, never body text')


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


def spacing_css(name: str) -> str:
    """The CSS a page of this script adds after the section library's own, minified; '' for a script the library's CSS
    suits (Hebrew, Latin): such a page stays byte for byte what it was. The override: the body's line height and word
    spacing, no letter-spacing anywhere (the joins of a connected script), and taller lines for the headings and the big
    figures, which the library sets at 1.05 to 1.3."""
    sp = script(name)['spacing']
    if sp['mode'] == 'library':
        return ''
    return (f'body{{line-height:{sp["body_line_height"]};word-spacing:{sp["word_spacing"]}}}'
            f'*,*::before,*::after{{letter-spacing:{sp["letter_spacing"]}!important}}'
            f'h1,h2,h3,h4,.title,.stat dd,.panel-figure,.panel-stats dd{{line-height:{sp["heading_line_height"]}!important}}')


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
    """The pair of one business: its tone (the art direction of its category's palette) allows the script's pairs of
    that tone (at least MIN_PAIRS_PER_TONE), and the business key -- its name, spaces collapsed, case folded -- picks
    one, the same every time. The category is part of the key, so one name in two trades need not get the same pair."""
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
