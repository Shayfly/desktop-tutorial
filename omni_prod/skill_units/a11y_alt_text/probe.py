"""skill.a11y.alt_text -- static: <img> without alt fails; alt="" only with role="presentation" or aria-hidden="true"."""
from omni_prod.skill_units import tags


def probe(html):
    findings = []
    for _, tag, a in tags(html):
        if tag != 'img':
            continue
        decorative = a.get('role') == 'presentation' or a.get('aria-hidden') == 'true'
        if 'alt' not in a:
            findings.append({'where': a.get('src', '?'), 'why': 'no alt attribute'})
        elif not a['alt'].strip() and not decorative:
            findings.append({'where': a.get('src', '?'), 'why': 'empty alt on an image that is not marked decorative'})
    return {'status': 'fail', 'code': 'ALT_MISSING', 'findings': findings} if findings else {'status': 'pass'}
