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
        return ('colours: the customer stated none and the business category is not recognised; choose a palette that '
                'fits this business, with text at least 4.5:1 against its background, and name it in the page CSS')
    name, p = palette_for(category)
    return (f'primary colour {p["primary"]}; palette {p["primary"]}, {p["accent"]}, {p["background"]}, {p["ink"]} '
            f'(primary, accent, background, text: the "{name}" palette of the {category} category -- the customer '
            f'stated no colour)')
