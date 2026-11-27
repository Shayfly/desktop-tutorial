"""Warehouse 105 (owner 2026-11-16; was 80): a site's colours when its customer stated none come from its business
category, read from a data file -- not the one default blue every site got before (WAREHOUSE.md 105).

`vertical_palettes.json` holds the palettes and, for each of the 32 categories of reference_catalog.CATEGORIES, its
palette and the words that identify it in a brief. Loading checks the file against the catalogue: a category without a
palette, a palette that does not exist, a category outside the catalogue, or a colour that is not #rrggbb raises
PaletteError -- loudly, at import, never a silent fallback.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).with_name('vertical_palettes.json')
ROLES = ('primary', 'accent', 'background', 'ink')
VARIANTS = ('dark', 'light')       # warehouse 125 (the owner 2026-11-27, "4א"): every palette declares both
AA_TEXT = 4.5                      # WCAG 2.x AA, normal text: ink, and the primary and accent that carry text or controls
_HEX = re.compile(r'#[0-9a-f]{6}')
# a Hebrew word may carry up to two one-letter prefixes (ה, ו, ב, ש, ל, מ, כ): "והאטליז", "במספרה"
_PRE = r'(?:(?<=^)|(?<=[^\w֐-׿]))[הובשלמכ]{0,2}'
_END = r'(?![\w֐-׿])'


class PaletteError(ValueError):
    pass


def check(data: dict, categories) -> None:
    """Raise PaletteError when the data does not cover exactly the catalogue's categories with existing palettes."""
    palettes, mapped = data.get('palettes') or {}, data.get('categories') or {}
    for name, p in palettes.items():
        for role in ROLES:
            if not _HEX.fullmatch(str(p.get(role, ''))):
                raise PaletteError(f'palette {name!r}: {role} must be #rrggbb, not {p.get(role)!r}')
        for variant in VARIANTS:
            v = p.get(variant)
            if not isinstance(v, dict):
                raise PaletteError(f'palette {name!r}: no declared {variant} variant')
            for role in ROLES:
                if not _HEX.fullmatch(str(v.get(role, ''))):
                    raise PaletteError(f'palette {name!r} {variant}: {role} must be #rrggbb, not {v.get(role)!r}')
        low = contrast_findings(name, p)
        if low:
            raise PaletteError(f'palette {name!r} is below WCAG AA ({AA_TEXT}): {low}')
    missing = sorted(set(categories) - set(mapped))
    if missing:
        raise PaletteError(f'categories without a palette: {missing}')
    extra = sorted(set(mapped) - set(categories))
    if extra:
        raise PaletteError(f'categories not in the catalogue: {extra}')
    stray = sorted(set(data.get('near') or {}) - set(categories))
    if stray:
        raise PaletteError(f'near words for categories not in the catalogue: {stray}')
    for slug, entry in mapped.items():
        if entry.get('palette') not in palettes:
            raise PaletteError(f'category {slug!r}: no palette named {entry.get("palette")!r}')
        if not entry.get('words'):
            raise PaletteError(f'category {slug!r}: no words to recognise it by')


def contrast_findings(name: str, palette: dict) -> dict:
    """{'<palette or variant>: <pair>': ratio} for each pair below WCAG AA (4.5:1) in the palette itself and in its
    dark and light variants: ink, primary and accent on the page, and the better of white and black on the primary (the
    colour of a button's text, which the contract computes). Empty when every pair reads."""
    from .g_apple import contract as C
    low = {}
    for label, p in [(name, palette)] + [(f'{name}.{v}', palette[v]) for v in VARIANTS if isinstance(palette.get(v), dict)]:
        on_primary = max(C.contrast('#ffffff', p['primary']), C.contrast('#000000', p['primary']))
        for pair, ratio in {'ink on background': C.contrast(p['ink'], p['background']),
                            'primary on background': C.contrast(p['primary'], p['background']),
                            'accent on background': C.contrast(p['accent'], p['background']),
                            'text on primary': on_primary}.items():
            if ratio < AA_TEXT:
                low[f'{label}: {pair}'] = ratio
    return low


@lru_cache(maxsize=1)
def load() -> dict:
    from .reference_catalog import CATEGORIES
    data = json.loads(DATA.read_text(encoding='utf-8'))
    check(data, CATEGORIES)
    return data


def category_of(text: str) -> str | None:
    """The catalogue category a brief names, by the first category word in it (longest word first at a tie); None
    when it names none -- never a guess."""
    t = (text or '').lower()
    hits = []
    for slug, entry in load()['categories'].items():
        for word in entry['words']:
            m = re.search(_PRE + re.escape(word.lower()) + _END, t)
            if m:
                hits.append((m.start(), -len(word), slug))
    return min(hits)[2] if hits else None


_WORD = re.compile(r'[a-z\u05d0-\u05ea"\u05f4]{3,}')
# with no shared word at all there is nothing to be near: a professional, high-contrast palette (DECISIONS 7)
NO_SIGNAL = 'lawyers'


def _grams(word: str) -> set:
    w = f' {word} '
    return {w[i:i + 3] for i in range(len(w) - 2)}


def nearest_category(text: str) -> tuple[str, float]:
    """DECISIONS 7 (the owner 2026-11-17): a brief whose category is not recognised and whose customer did not answer
    the colour question takes the palette of the NEAREST category: first a related word the data file lists under
    "near" (a pizzeria is near restaurants), then an inflection of a category word by letter trigrams (one-letter
    Hebrew prefixes stripped; the threshold keeps a shared generic noun -- "מכון", "חנות" -- from counting). Returns (category, score 0..1); with no shared
    trigram at all, (NO_SIGNAL, 0.0). Deterministic: the same text, the same category."""
    exact = category_of(text)
    if exact:
        return exact, 1.0
    t = (text or '').lower()
    hits = [(m.start(), -len(word), slug) for slug, related in sorted((load().get('near') or {}).items())
            for word in related for m in [re.search(_PRE + re.escape(word.lower()) + _END, t)] if m]
    if hits:                                       # a related word the data file names: near by declaration
        return min(hits)[2], 0.9
    words = set()
    for w in _WORD.findall((text or '').lower()):
        words.add(w)
        if w[0] in 'הובשלמכ' and len(w) > 4:
            words.add(w[1:])
    best = (0.0, NO_SIGNAL)
    for slug, entry in sorted(load()['categories'].items()):
        for cw in entry['words']:
            g = _grams(cw.lower())
            for w in words:
                h = _grams(w)
                score = len(g & h) / len(g | h)
                if score > best[0]:
                    best = (score, slug)
    return (best[1], round(best[0], 3)) if best[0] >= 0.55 else (NO_SIGNAL, 0.0)


def identify(text: str) -> dict:
    """The business and the palette of a brief, kept apart (route-honesty; the owner's build bld_3938e570, 2026-11-25):

      category          the catalogue category the brief NAMES (category_of), or None -- the business
      palette_category  the category whose palette, art direction and fonts the page takes: the named one, else the
                        nearest (nearest_category), else NO_SIGNAL
      found             'named' | 'nearest' | 'none' (no signal at all)
      score             1.0 named; nearest_category's score otherwise (0.0: none)

    NO_SIGNAL names a palette, never a business: a smoke shop that nothing was near took 'lawyers' as its business,
    read the lawyer domain and was written as a law firm (an invented fee in a 'how it works' section the lawyer
    palette required). A near word is a declaration of COLOUR nearness ("near" in the data file: a tattoo studio is
    near photographers, an insurance agent near accountants, a greengrocer near delis) and a trigram match is a guess
    at an inflection: both lend the palette only, never the business."""
    named = category_of(text)
    if named:
        return {'category': named, 'palette_category': named, 'found': 'named', 'score': 1.0}
    near, score = nearest_category(text)
    return {'category': None, 'palette_category': near, 'found': 'nearest' if score else 'none', 'score': score}


def palette_for(category: str) -> tuple[str, dict]:
    """(palette name, {primary, accent, background, ink}) of a catalogue category. An unknown category raises."""
    data = load()
    if category not in data['categories']:
        raise PaletteError(f'{category!r} is not a catalogue category')
    name = data['categories'][category]['palette']
    return name, {role: data['palettes'][name][role] for role in ROLES}


def variants_for(palette: str) -> dict:
    """{'dark': {...}, 'light': {...}}: the two variants a palette declares, each {primary, accent, background, ink}.
    An unknown palette raises. colour_roles takes them when a customer says "dark" or "light" (warehouse 125)."""
    data = load()['palettes']
    if palette not in data:
        raise PaletteError(f'{palette!r} is not a palette')
    return {v: {role: data[palette][v][role] for role in ROLES} for v in VARIANTS}


def design_colours(text: str) -> str:
    """The colour clause of the build prompt for a brief whose customer stated no colour."""
    category = category_of(text)
    if category is None:
        # DECISIONS 7: never "choose something" -- the nearest category's palette, said as such (G-APPLE then runs)
        near, score = nearest_category(text)
        if not score:
            # the owner, 2026-11-22: for a business we do not know, the customer is asked (conversation_agent
            # COLOUR_QUESTION); when they leave it to us, the palette is always one we have -- with nothing near, the
            # neutral one (NO_SIGNAL). "Choose a palette" left the contract without colours and the build fell to the
            # old path (no_design_contract).
            name, p = palette_for(NO_SIGNAL)
            return (f'primary colour {p["primary"]}; palette {p["primary"]}, {p["accent"]}, {p["background"]}, '
                    f'{p["ink"]} (primary, accent, background, text: the neutral "{name}" palette -- the customer '
                    f'stated no colour and no category is near this business)')
        name, p = palette_for(near)
        return (f'primary colour {p["primary"]}; palette {p["primary"]}, {p["accent"]}, {p["background"]}, {p["ink"]} '
                f'(primary, accent, background, text: the "{name}" palette of the nearest category, {near}, '
                f'similarity {score} -- the customer stated no colour and the business category is not recognised)')
    name, p = palette_for(category)
    return (f'primary colour {p["primary"]}; palette {p["primary"]}, {p["accent"]}, {p["background"]}, {p["ink"]} '
            f'(primary, accent, background, text: the "{name}" palette of the {category} category -- the customer '
            f'stated no colour)')
