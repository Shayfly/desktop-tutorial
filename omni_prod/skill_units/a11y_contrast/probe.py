"""skill.a11y.contrast -- static: every CSS rule or inline style that sets both a text colour and a background colour
must reach 4.5:1. Colours as #rgb, #rrggbb, white or black, written directly or through CSS custom properties
(`var(--name)`, resolved from the page's own declarations, with a var() fallback).

2026-11-16 (owner: "a gate that has not been shown to fail does not go in"): the generated pages set every colour
through custom properties (the butcher page: `color: var(--text-dark)` on `background-color: var(--bg-neutral)`), and
the first version read only literal hex -- it judged nothing on a real page and passed it. A pair it still cannot read
(rgb(), hsl(), a gradient, an undefined variable) is not judged; `judged()` counts only the pairs it read.
"""
import re

from omni_prod.design_palettes import contrast
from omni_prod.skill_units import tags

MIN = 4.5
_NAMED = {'white': '#ffffff', 'black': '#000000'}
_HEX = re.compile(r'#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
_COLOR = re.compile(r'(?<![-\w])color\s*:\s*([^;}]+)')
_BG = re.compile(r'(?<![-\w])background(?:-color)?\s*:\s*([^;}]+)')
_RULE = re.compile(r'([^{}]+)\{([^{}]*)\}')
_PROP = re.compile(r'(--[\w-]+)\s*:\s*([^;}]+)')
_VAR = re.compile(r'var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*))?\)')


def _full(h):
    h = h.lstrip('#')
    return '#' + (''.join(c * 2 for c in h) if len(h) == 3 else h).lower()


def _css(html):
    return '\n'.join(m.group(1) for m in re.finditer(r'<style[^>]*>(.*?)</style>', html or '', re.S | re.I))


def _props(html):
    """Every custom property the page declares (the last declaration wins, as in the cascade's simplest case)."""
    out = {}
    for m in _PROP.finditer(_css(html)):
        out[m.group(1)] = m.group(2).strip()
    for _, _, a in tags(html):
        for m in _PROP.finditer(a.get('style', '')):
            out[m.group(1)] = m.group(2).strip()
    return out


def _resolve(value, props, depth=0):
    """A CSS value with var() replaced from the page's properties; bounded (a cycle stops at depth 5)."""
    if depth > 5:
        return value
    def sub(m):
        got = props.get(m.group(1))
        if got is None:
            got = (m.group(2) or '').strip()
        return _resolve(got, props, depth + 1)
    return _VAR.sub(sub, value)


def _colour(value, props):
    v = _resolve(value or '', props).strip().lower()
    if v in _NAMED:
        return _NAMED[v]
    m = _HEX.fullmatch(v) or (_HEX.match(v) if ' ' not in v and '(' not in v else None)
    return _full(m.group()) if m else None


def _pairs(html):
    for r in _RULE.finditer(_css(html)):
        yield r.group(1).strip(), r.group(2)
    for _, tag, a in tags(html):
        if a.get('style'):
            yield f'<{tag} style>', a['style']


def probe(html):
    props, findings = _props(html), []
    for where, decl in _pairs(html):
        c, b = _COLOR.search(decl), _BG.search(decl)
        if not (c and b):
            continue
        fg, bg = _colour(c.group(1), props), _colour(b.group(1), props)
        if fg is None or bg is None:       # not read: not judged, and not counted by judged()
            continue
        ratio = contrast(fg, bg)
        if ratio < MIN:
            findings.append({'where': where, 'color': fg, 'background': bg, 'ratio': round(ratio, 2)})
    return {'status': 'fail', 'code': 'CONTRAST_LOW', 'findings': findings} if findings else {'status': 'pass'}


def judged(html):
    """How many colour pairs the probe could read on this page (the evidence that a pass judged something)."""
    props = _props(html)
    n = 0
    for _, decl in _pairs(html):
        c, b = _COLOR.search(decl), _BG.search(decl)
        if c and b and _colour(c.group(1), props) and _colour(b.group(1), props):
            n += 1
    return n
