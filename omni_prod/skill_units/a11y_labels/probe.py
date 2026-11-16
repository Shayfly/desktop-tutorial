"""skill.a11y.labels -- static: input (not hidden/submit/button/reset/image), select and textarea need an accessible
name: label[for=id], a wrapping <label>, aria-label or aria-labelledby."""
import re

from omni_prod.skill_units import attrs

_FIELD = re.compile(r'<(input|select|textarea)\b([^>]*)>', re.I)
_SKIP = {'hidden', 'submit', 'button', 'reset', 'image'}


def probe(html):
    html = html or ''
    fors = set(re.findall(r'<label\b[^>]*\bfor\s*=\s*["\']([^"\']+)["\']', html, re.I))
    findings = []
    for m in _FIELD.finditer(html):
        tag, a = m.group(1).lower(), attrs(m.group(2))
        if tag == 'input' and a.get('type', 'text').lower() in _SKIP:
            continue
        if a.get('aria-label', '').strip() or a.get('aria-labelledby', '').strip() or (a.get('id') and a['id'] in fors):
            continue
        before = html[:m.start()]
        if before.lower().rfind('<label') > before.lower().rfind('</label>'):
            continue                                    # wrapped in an open <label>
        findings.append({'where': f'<{tag} name={a.get("name", "?")}>', 'why': 'no accessible name'})
    return {'status': 'fail', 'code': 'LABEL_MISSING', 'findings': findings} if findings else {'status': 'pass'}
