"""skill.a11y.contrast -- static: every CSS rule or inline style that sets both a text colour and a background colour
must reach 4.5:1. Colours as #rgb or #rrggbb; a pair it cannot read is not judged (and not claimed)."""
import re

from omni_prod.design_palettes import contrast
from omni_prod.skill_units import tags

MIN = 4.5
_HEX = r'#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b'
_COLOR = re.compile(r'(?<![-\w])color\s*:\s*(' + _HEX + ')')
_BG = re.compile(r'background(?:-color)?\s*:\s*(' + _HEX + ')')
_RULE = re.compile(r'([^{}]+)\{([^{}]*)\}')


def _full(h):
    h = h.lstrip('#')
    return '#' + (''.join(c * 2 for c in h) if len(h) == 3 else h)


def _pairs(html):
    for m in re.finditer(r'<style[^>]*>(.*?)</style>', html or '', re.S | re.I):
        for r in _RULE.finditer(m.group(1)):
            yield r.group(1).strip(), r.group(2)
    for _, tag, a in tags(html):
        if a.get('style'):
            yield f'<{tag} style>', a['style']


def probe(html):
    findings = []
    for where, decl in _pairs(html):
        c, b = _COLOR.search(decl), _BG.search(decl)
        if c and b:
            ratio = contrast(_full(c.group(1)), _full(b.group(1)))
            if ratio < MIN:
                findings.append({'where': where, 'color': c.group(1), 'background': b.group(1), 'ratio': round(ratio, 2)})
    return {'status': 'fail', 'code': 'CONTRAST_LOW', 'findings': findings} if findings else {'status': 'pass'}
