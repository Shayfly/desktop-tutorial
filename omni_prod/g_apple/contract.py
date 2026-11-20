"""The design contract (G-APPLE, part 1; the owner, 2026-11-17).

Locked BEFORE any code is written, from what the approved brief already decided (its Design line: primary colour,
background, text colour, font). The generator does not choose sizes, colours, weights or corners: it gets them as
CSS custom properties and may use nothing else. One contract, deterministic, no model:

  type scale      TYPE_PX, the only font sizes
  8-grid          SPACE_PX, the only margins, paddings and gaps (4 is the one half step)
  semantic palette  bg, surface, text, muted, border, primary, on-primary -- ONE accent (primary); every text pair's
                  contrast is COMPUTED here (WCAG 2.x), and a pair below its minimum is corrected, never shipped
  two weights     WEIGHTS
  one radius      RADIUS_PX
  motion tokens   two durations, one easing

`fingerprint` binds a build to the contract it was given: a page checked against another contract is a failure.
"""
from __future__ import annotations

import hashlib
import json
import re

VERSION = 1
TYPE_PX = (12, 14, 16, 20, 24, 32, 40, 56)
SPACE_PX = (0, 4, 8, 16, 24, 32, 48, 64, 96)
WEIGHTS = (400, 700)
RADIUS_PX = 8
HAIRLINE_PX = (1, 2)                       # borders and outlines
MOTION = {'--motion-fast': '150ms', '--motion-base': '250ms', '--motion-ease': 'cubic-bezier(0.2, 0, 0, 1)'}
MIN_TEXT_CONTRAST, MIN_UI_CONTRAST = 4.5, 3.0
_HEX = re.compile(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
# discovery.requirements_text: "Design: style clean; primary colour #9a3412; palette #9a3412, #a16207, #fffbeb, #1c1917
# (primary, accent, background, text: ...); font 'Heebo', system-ui, sans-serif (load it from Google Fonts ...)"
_DESIGN = re.compile(r'Design: style (?P<style>[\w-]+); (?P<colours>.*?); font (?P<font>[^;()]{1,200}?) \(')
_PALETTE = re.compile(r'palette ((?:#[0-9a-fA-F]{3,6}(?:, )?){4})')
# the owner 2026-11-20 (international level): a heading font of its own, e.g. a Hebrew serif for a law firm. Optional:
# "display font 'Frank Ruhl Libre', serif" on the Design line; without it, headings use the body font.
_DISPLAY = re.compile(r"display font (?P<display>[^;()\n]{1,200}?)(?=;|\s\(|$)", re.M)


class ContractError(ValueError):
    """The approved brief does not carry what a design contract needs. Nothing is defaulted."""


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    h = hex_colour.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    if not re.fullmatch(r'[0-9a-fA-F]{6}', h):
        raise ContractError(f'not a hex colour: {hex_colour!r}')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb) -> str:
    return '#' + ''.join(f'{max(0, min(255, round(c))):02x}' for c in rgb)


def luminance(hex_colour: str) -> float:
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _rgb(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def _mix(a: str, b: str, t: float) -> str:
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))


def _readable(fg: str, bg: str, minimum: float) -> str:
    """`fg` when it reads on `bg`; else the nearer of black/white steps toward the readable end. Bounded: 20 steps."""
    if contrast(fg, bg) >= minimum:
        return fg
    end = '#000000' if luminance(bg) > 0.4 else '#ffffff'
    for step in range(1, 21):
        candidate = _mix(fg, end, step / 20)
        if contrast(candidate, bg) >= minimum:
            return candidate
    return end


def build(prompt: str) -> dict:
    """The contract for this build, from the approved brief's Design line. Raises ContractError when the brief has
    no Design line with a four-colour palette (a raw request has none: there is nothing to lock)."""
    block = (prompt or '').rsplit('--- Approved project brief', 1)
    line = _DESIGN.search(block[1] if len(block) == 2 else '')
    if not line:
        raise ContractError('the approved brief has no Design line')
    palette = _PALETTE.search(line.group('colours'))
    if not palette:
        raise ContractError('the Design line has no four-colour palette (primary, accent, background, text)')
    primary, _accent, bg, text = [c.lower() for c in re.findall(r'#[0-9a-fA-F]{3,6}', palette.group(1))]
    text = _readable(text, bg, 7.0)                              # body text: AAA where the palette allows a step
    primary = _readable(primary, bg, MIN_UI_CONTRAST)            # a button must be seen against the page
    on_primary = '#ffffff' if contrast('#ffffff', primary) >= contrast('#000000', primary) else '#000000'
    surface = _mix(bg, text, 0.04)
    muted = _readable(_mix(text, bg, 0.35), bg, MIN_TEXT_CONTRAST)
    border = _mix(bg, text, 0.18)
    family = ' '.join(line.group('font').split())
    design_line = block[1][line.start():].split('\n', 1)[0]
    display_m = _DISPLAY.search(design_line)
    display = ' '.join(display_m.group('display').split()) if display_m else family
    tokens = {
        '--color-bg': bg, '--color-surface': surface, '--color-text': text, '--color-muted': muted,
        '--color-border': border, '--color-primary': primary, '--color-on-primary': on_primary,
        '--font-family': family, '--font-display': display,
        **{f'--text-{px}': f'{px}px' for px in TYPE_PX},
        **{f'--space-{px}': f'{px}px' for px in SPACE_PX if px},
        '--weight-regular': str(WEIGHTS[0]), '--weight-bold': str(WEIGHTS[1]),
        '--radius': f'{RADIUS_PX}px',
        **MOTION,
    }
    pairs = {'text on bg': (text, bg, MIN_TEXT_CONTRAST), 'muted on bg': (muted, bg, MIN_TEXT_CONTRAST),
             'text on surface': (text, surface, MIN_TEXT_CONTRAST),
             'on-primary on primary': (on_primary, primary, MIN_TEXT_CONTRAST),
             'primary on bg': (primary, bg, MIN_UI_CONTRAST)}
    measured = {name: contrast(a, b) for name, (a, b, _) in pairs.items()}
    low = {name: measured[name] for name, (_, _, minimum) in pairs.items() if measured[name] < minimum}
    if low:
        raise ContractError(f'the palette cannot be made readable: {low}')
    css = ':root {\n' + ''.join(f'  {k}: {v};\n' for k, v in tokens.items()) + '}'
    body = {'version': VERSION, 'style': line.group('style'), 'tokens': tokens, 'contrast': measured,
            'dropped': {'accent': _accent.lower(), 'why': 'one accent colour: the primary'}}
    return {**body, 'css': css,
            'fingerprint': hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]}


def rules(contract: dict) -> str:
    """The contract as the generator's instructions."""
    return '\n'.join([
        f"Design contract {contract['fingerprint']} (locked by 148AI; the finished page is checked against it):",
        'Put this block in the page <style>, EXACTLY as written, and use ONLY these custom properties:',
        contract['css'],
        '- Colours: only var(--color-...). No hex, rgb() or hsl() value anywhere outside this :root block. One accent: '
        '--color-primary. Text on the primary colour is --color-on-primary.',
        f"- Sizes: font-size only var(--text-...); margin, padding and gap only var(--space-...) or 0. No other px "
        f"value except {HAIRLINE_PX[0]}px/{HAIRLINE_PX[1]}px borders. Layout widths use %, rem, ch, fr or max-width.",
        '- Fonts: body text var(--font-family); headings may use var(--font-display). Load both from Google Fonts '
        'with display=swap when they differ.',
        '- Weights: only var(--weight-regular) and var(--weight-bold). No third weight.',
        '- Corners: only var(--radius) (or 50% for a circle). Motion: only var(--motion-fast|base) with var(--motion-ease).',
        '- Every button, link and field has five states: default, :hover, :focus-visible (a visible outline), :active, '
        'and :disabled where it can be disabled. At most two button styles (primary and secondary).',
        '- Not allowed: a gradient hero with outlined text; a row of three icon cards; a carousel or slider; a shadow on '
        'everything; everything centred; emoji as icons; placeholder text (lorem ipsum).',
        # calibration, rehearsal 44057019675 (2026-11-17): "about 52ch" gave Hebrew paragraphs 53 characters a line in
        # Heebo -- the rule itself made the page fail the check. ch follows the font's "0"; a fixed width does not.
        '- Body text lines are 55 to 75 characters long on a wide screen: give every paragraph max-width: 35rem (about '
        '65 characters of Hebrew or English at 16px; never a ch value); controls are at least 44px '
        'high; nothing scrolls sideways at 320px.',
        # calibration, rehearsal 44043708644: 24 OFF_GRID findings were headings and links left on the browser's own
        # margins (an h2's default is 0.83em: 19.92px at 24px), which no rule above mentions
        '- Start the stylesheet by setting margin: 0 and padding: 0 on h1, h2, h3, h4, p, ul, ol, li and figure, then '
        'give each its spacing from var(--space-...): a browser default margin is not on the grid.',
        # calibration, three builds of three (44048592665, 44049242034, 44050605137): the typography reviewer said the
        # hero's content sat in one half of a wide card and left the other half empty (P1 each time)
        '- The top area (hero): on a wide screen its content fills the width it is given -- either the text block is '
        'centred as a block with a max-width, or the second half holds real content (an image, the opening hours, '
        'the call button). Never text in one half and an empty half beside it.',
    ])
