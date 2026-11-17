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


def palette_for(category: str) -> tuple[str, dict]:
    """(palette name, {primary, accent, background, ink}) of a catalogue category. An unknown category raises."""
    data = load()
    if category not in data['categories']:
        raise PaletteError(f'{category!r} is not a catalogue category')
    name = data['categories'][category]['palette']
    return name, {role: data['palettes'][name][role] for role in ROLES}


def design_colours(text: str) -> str:
    """The colour clause of the build prompt for a brief whose customer stated no colour."""
    category = category_of(text)
    if category is None:
        # DECISIONS 7: never "choose something" -- the nearest category's palette, said as such (G-APPLE then runs)
        near, score = nearest_category(text)
        if not score:   # nothing near at all: the colour question (DECISIONS 7, part 2) is the only honest source
            return ('colours: the customer stated none and the business category is not recognised; choose a palette '
                    'that fits this business, with text at least 4.5:1 against its background, and name it in the '
                    'page CSS')
        name, p = palette_for(near)
        return (f'primary colour {p["primary"]}; palette {p["primary"]}, {p["accent"]}, {p["background"]}, {p["ink"]} '
                f'(primary, accent, background, text: the "{name}" palette of the nearest category, {near}, '
                f'similarity {score} -- the customer stated no colour and the business category is not recognised)')
    name, p = palette_for(category)
    return (f'primary colour {p["primary"]}; palette {p["primary"]}, {p["accent"]}, {p["background"]}, {p["ink"]} '
            f'(primary, accent, background, text: the "{name}" palette of the {category} category -- the customer '
            f'stated no colour)')
