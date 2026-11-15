"""Colour palettes by global category -- tier 3 only (Michael 2026-11-15, final: not by vertical, not by mood).

Ten categories, three palettes each (conservative, warm, bold); the default is conservative. Every palette is
60/30/10 (background / text / accent). A palette is used only at tier 3: when the customer gave no colours (tier 1)
and the library has no approved examples for the vertical (tier 2).

Contrast: text on background >= 7:1 (body text, WCAG AAA); the label on the accent >= 4.5:1. A tone that fails is
REPLACED automatically (Michael: "גוון שלא עובר ניגוד -- מחליף לבד, בלי לחזור אלי"): the text is moved toward
black or white, the accent darkened or lightened, in small steps, until it passes. Every replacement is returned in
`adjusted`, so it is visible in the evidence -- never a silent change.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SHARES = (60, 30, 10)
BODY_CONTRAST = 7.0
ACCENT_LABEL_CONTRAST = 4.5
STYLES = ('conservative', 'warm', 'bold')
DEFAULT_STYLE = 'conservative'

CATEGORIES: dict[str, str] = {
    'restaurants': 'מסעדנות', 'nightlife': 'מועדונים ולילה', 'tech': 'הייטק וסטארטאפים', 'retail': 'קמעונאות',
    'beauty': 'יופי וטיפוח', 'health': 'בריאות', 'education': 'חינוך', 'real_estate': 'נדל״ן', 'events': 'אירועים',
    'tourism': 'תיירות',
}

# (background, text, accent) per category and style -- a starting set; contrast is enforced in palette(), not trusted
_RAW: dict[str, dict[str, tuple[str, str, str]]] = {
    'restaurants': {'conservative': ('#F7F3EE', '#2A2420', '#7A2E22'), 'warm': ('#FBF1E4', '#3A2618', '#C2552B'),
                    'bold': ('#1E1A17', '#F6EFE6', '#E0702F')},
    'nightlife': {'conservative': ('#14141A', '#ECEAF2', '#6C5CE0'), 'warm': ('#1A1214', '#F4E9EC', '#D9466F'),
                  'bold': ('#0B0B10', '#F2F2F7', '#E5FF3D')},
    'tech': {'conservative': ('#F7F9FC', '#16202E', '#2457C5'), 'warm': ('#FBF8F5', '#1F1A17', '#E35D2F'),
             'bold': ('#0E1220', '#EEF2FF', '#3DD6A3')},
    'retail': {'conservative': ('#FAFAF8', '#1D1D1B', '#1F5F8B'), 'warm': ('#FBF4EC', '#2B211A', '#B4582A'),
               'bold': ('#FFFFFF', '#141414', '#E0283C')},
    'beauty': {'conservative': ('#FAF7F5', '#2A2326', '#8C5A6A'), 'warm': ('#FBF1EE', '#3A2428', '#C76E7E'),
               'bold': ('#1E161A', '#F7ECEF', '#E85B8A')},
    'health': {'conservative': ('#F6FAFA', '#14272A', '#1F6F78'), 'warm': ('#F8F6F1', '#22302B', '#3E8E6E'),
               'bold': ('#FFFFFF', '#0F1F2E', '#0077C8')},
    'education': {'conservative': ('#F8F9FB', '#1A2233', '#2D4E9A'), 'warm': ('#FBF7EE', '#2A2418', '#D08A1E'),
                  'bold': ('#FFFFFF', '#161B26', '#7B3FE4')},
    'real_estate': {'conservative': ('#F7F7F5', '#1E2124', '#2F4A5C'), 'warm': ('#F7F2EB', '#2A241D', '#9C6B3C'),
                    'bold': ('#121518', '#F1F3F5', '#C9A45C')},
    'events': {'conservative': ('#FBFAF8', '#232027', '#6B4E9B'), 'warm': ('#FCF3EC', '#2E1F1A', '#D9643A'),
               'bold': ('#16111C', '#F7F0FA', '#FF5FA2')},
    'tourism': {'conservative': ('#F5F9FA', '#16262E', '#1E6A8C'), 'warm': ('#FBF5EA', '#2B2418', '#D4862A'),
                'bold': ('#FFFFFF', '#10202A', '#00A3A3')},
}


def _rgb(hex_: str) -> tuple[int, int, int]:
    h = hex_.lstrip('#')
    if len(h) != 6 or any(c not in '0123456789abcdefABCDEF' for c in h):
        raise ValueError(f'not a #RRGGBB colour: {hex_!r}')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb: tuple[float, float, float]) -> str:
    return '#' + ''.join(f'{max(0, min(255, round(c))):02X}' for c in rgb)


def luminance(hex_: str) -> float:
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(hex_)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _toward(hex_: str, target: tuple[int, int, int], step: float) -> str:
    r, g, b = _rgb(hex_)
    return _hex((r + (target[0] - r) * step, g + (target[1] - g) * step, b + (target[2] - b) * step))


def _fix(colour: str, against: str, minimum: float) -> str:
    """Move `colour` toward black or white (whichever side of `against` it is on) until the contrast passes.
    Bounded: 40 steps reach the extreme, and pure black/white on any background reaches at least 1.0 -- a value that
    still fails after that raises (it cannot happen with a light or dark background, but it is never silent)."""
    target = (0, 0, 0) if luminance(against) > luminance(colour) or luminance(against) > 0.18 else (255, 255, 255)
    out = colour.upper()
    for i in range(1, 41):
        if contrast(out, against) >= minimum:
            return out
        out = _toward(colour, target, i / 40)
    if contrast(out, against) >= minimum:
        return out
    raise ValueError(f'{colour} cannot reach {minimum}:1 against {against}')


@dataclass(frozen=True)
class Palette:
    category: str
    style: str
    background: str
    text: str
    accent: str
    on_accent: str
    shares: tuple[int, int, int] = SHARES
    adjusted: tuple[str, ...] = field(default=())

    def to_dict(self) -> dict:
        return {'category': self.category, 'style': self.style, 'background': self.background, 'text': self.text,
                'accent': self.accent, 'on_accent': self.on_accent, 'shares': list(self.shares),
                'contrast_body': round(contrast(self.text, self.background), 2),
                'contrast_accent_label': round(contrast(self.on_accent, self.accent), 2),
                'adjusted': list(self.adjusted)}


def build(category: str, style: str, background: str, text: str, accent: str) -> Palette:
    """A palette with the contrast rules enforced; every replaced tone is listed in `adjusted`."""
    adjusted = []
    fixed_text = _fix(text, background, BODY_CONTRAST)
    if fixed_text != text.upper():
        adjusted.append(f'text {text} -> {fixed_text} (body {contrast(text, background):.2f}:1 < {BODY_CONTRAST}:1)')
    white, black = '#FFFFFF', '#141414'
    on = white if contrast(white, accent) >= contrast(black, accent) else black
    fixed_accent = accent.upper()
    if contrast(on, accent) < ACCENT_LABEL_CONTRAST:
        fixed_accent = _fix(accent, on, ACCENT_LABEL_CONTRAST)
        adjusted.append(f'accent {accent} -> {fixed_accent} (label {contrast(on, accent):.2f}:1 < {ACCENT_LABEL_CONTRAST}:1)')
    return Palette(category, style, background.upper(), fixed_text, fixed_accent, on, SHARES, tuple(adjusted))


def palette(category: str, style: str = DEFAULT_STYLE) -> Palette:
    if category not in CATEGORIES:
        raise KeyError(f'unknown category {category!r}; one of {sorted(CATEGORIES)}')
    if style not in STYLES:
        raise KeyError(f'unknown style {style!r}; one of {STYLES}')
    return build(category, style, *_RAW[category][style])


def resolve(*, customer_colours: list[str] | None, example_palette: dict | None, category: str | None,
            style: str = DEFAULT_STYLE) -> dict:
    """Which colours a card shows. Tier 1: the customer's own colours. Tier 2: the palette of approved examples for
    the vertical. Tier 3: this module's category palette. No category at tier 3 -> no palette (the card asks)."""
    if customer_colours:
        return {'tier': 1, 'source': 'customer', 'colours': list(customer_colours)}
    if example_palette:
        return {'tier': 2, 'source': 'library', 'palette': dict(example_palette)}
    if category is None:
        return {'tier': 3, 'source': 'none', 'palette': None, 'reason': 'no category yet: the card asks the vertical'}
    return {'tier': 3, 'source': 'category', 'palette': palette(category, style).to_dict()}
