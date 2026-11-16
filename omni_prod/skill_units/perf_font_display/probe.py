"""skill.perf.font_display -- static: Google Fonts CSS without display=swap, or an @font-face without font-display."""
import re

from omni_prod.skill_units import tags

_FACE = re.compile(r'@font-face\s*\{([^}]*)\}', re.I)


def probe(html):
    findings = []
    for _, tag, a in tags(html):
        href = a.get('href', '')
        if tag == 'link' and 'fonts.googleapis.com/css' in href and 'display=' not in href:
            findings.append({'where': href, 'why': 'Google Fonts without display=swap'})
    for m in _FACE.finditer(html or ''):
        if 'font-display' not in m.group(1).lower():
            findings.append({'where': '@font-face', 'why': 'no font-display'})
    return {'status': 'fail', 'code': 'FONT_NO_SWAP', 'findings': findings} if findings else {'status': 'pass'}
