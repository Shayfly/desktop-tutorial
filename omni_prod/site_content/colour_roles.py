"""The roles of the colours a customer stated, when they are not the four a design contract needs.

The conversation model records the customer's colour answer in their own words: a pair of names ("שחור, זהב"), a
description ("כהה", "dark", "משטח חול בהיר, טקסט פחם"), or words no table knows ("צבעים בהשראת בוב מארלי").
G-APPLE's contract (g_apple/contract.py) needs primary, accent, background and text. Before this module a
description gave the Design line no primary colour at all -- the contract failed and the build fell to the legacy path
(site_content.decide 'no_design_contract') -- and a named pair set only the primary colour, so a barber that asked
for black and gold got black on the blush palette's pink.

`roles(clause, palette)` fills the four roles, deterministically, from the stated colours and the business category's
palette (a dict of primary, accent, background, ink):
  * a stated colour that is nearly black or nearly white is the page's background when at least one more colour is
    stated (a pair "black, gold": black is the page, gold the primary); the remaining colours are primary, then accent;
  * a description word ("כהה"/"dark", "בהיר"/"light") picks the palette's dark or light variant when no stated colour is
    a background; colour names that contain such a word ("כחול כהה" = navy) are colours, not descriptions;
  * a role nobody stated comes from the palette; text is chosen to read on the background.
It never raises for a colour answer: words it does not know leave the category's palette as it is (basis says so).
"""
from __future__ import annotations

import re

from ..g_apple import contract as C

_HEX = re.compile(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b')
_DESCRIPTION = re.compile(r"requested colour description (?:'([^']*)'|\"([^\"]*)\")")
_DARK = re.compile(r'(?<![\w֐-׿])[הובלכ]?(?:כהה|כהים|כהות|חשוך|חשוכה|dark)(?![\w֐-׿])', re.I)
_LIGHT = re.compile(r'(?<![\w֐-׿])[הובלכ]?(?:בהיר|בהירה|בהירים|בהירות|light)(?![\w֐-׿])', re.I)
BACKGROUND_DARK = 0.02      # relative luminance at or below: a page background ("black")
BACKGROUND_LIGHT = 0.75     # at or above: a page background ("white", "cream", "beige")
DARK_INK, LIGHT_INK = '#f5f5f4', '#111111'
DARK_MIX = 0.9              # a dark page: the hue colour mixed this far toward black


def _long(colour: str) -> str:
    colour = colour.lower()
    return '#' + ''.join(c * 2 for c in colour[1:]) if len(colour) == 4 else colour


def description_of(clause: str) -> str:
    m = _DESCRIPTION.search(clause or '')
    return (m.group(1) if m and m.group(1) is not None else (m.group(2) if m else '')) or ''


def stated_hexes(clause: str) -> list[str]:
    """The colours the Design line already resolved (the part before the description), in order, without repeats."""
    head = (clause or '').split('requested colour description', 1)[0]
    out: list[str] = []
    for found in _HEX.findall(head):
        found = _long(found)
        if found not in out:
            out.append(found)
    return out


def words_of(description: str) -> str | None:
    """'dark', 'light' or None. A colour name that carries the word ("כחול כהה", "light blue") is a colour, not a
    description; both words, or neither, say nothing."""
    from ..discovery import _COLOUR_ALIASES
    names = '|'.join(re.escape(w) for w in sorted(_COLOUR_ALIASES, key=len, reverse=True))
    rest = re.sub(r'(?<!\w)(?:וב|ו|ב)?(?:' + names + r')(?!\w)', ' ', description or '', flags=re.I)
    dark, light = bool(_DARK.search(rest)), bool(_LIGHT.search(rest))
    return 'dark' if dark and not light else 'light' if light and not dark else None


def _ink_for(background: str, palette_ink: str) -> str:
    if C.luminance(background) < 0.3:
        return DARK_INK
    return palette_ink if C.contrast(palette_ink, background) >= 7.0 else LIGHT_INK


def roles(clause: str, palette: dict) -> dict:
    """{primary, accent, background, ink, basis, source} for the Design line's colour clause."""
    stated = stated_hexes(clause)
    word = words_of(description_of(clause))
    background = None
    rest = list(stated)
    if len(stated) >= 2:
        for colour in stated:
            lum = C.luminance(colour)
            if lum <= BACKGROUND_DARK or lum >= BACKGROUND_LIGHT:
                background = colour
                rest.remove(colour)
                break
    basis = []
    if background:
        basis.append('the stated colour %s is the page' % background)
        ink = _ink_for(background, palette['ink'])
    elif word == 'dark':
        hue = stated[0] if stated else palette['primary']
        background = C._mix(hue, '#000000', DARK_MIX)
        ink = DARK_INK
        basis.append('"dark": the palette\'s dark variant')
    else:
        background = palette['background']
        ink = palette['ink']
        basis.append('"light": the palette\'s light variant' if word == 'light'
                     else 'no role word: the category\'s palette')
    primary = rest[0] if rest else palette['primary']
    accent = rest[1] if len(rest) > 1 else palette['accent']
    if stated:
        basis.append('primary and accent from the stated colours' if len(rest) > 1 else 'primary from the stated colours')
    source = 'brief-primary+category' if stated else ('category+' + word if word else 'category')
    return {'primary': primary, 'accent': accent, 'background': background, 'ink': ink,
            'basis': '; '.join(basis), 'source': source}
