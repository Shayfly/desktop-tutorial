"""skill.a11y.focus -- static: `outline: none|0` under a :focus selector without any :focus-visible rule in the page,
or a tabindex above 0."""
import re

from omni_prod.skill_units import tags

_RULE = re.compile(r'([^{}]+)\{([^{}]*)\}')


def probe(html):
    findings = []
    css = '\n'.join(m.group(1) for m in re.finditer(r'<style[^>]*>(.*?)</style>', html or '', re.S | re.I))
    has_visible = ':focus-visible' in css
    for r in _RULE.finditer(css):
        sel, decl = r.group(1), r.group(2).replace(' ', '')
        if ':focus' in sel and ':focus-visible' not in sel and re.search(r'outline:(none|0)(;|$)', decl) and not has_visible:
            findings.append({'where': sel.strip(), 'why': 'outline removed with no :focus-visible style'})
    for _, tag, a in tags(html):
        t = a.get('tabindex', '')
        if t.lstrip('-').isdigit() and int(t) > 0:
            findings.append({'where': f'<{tag} tabindex={t}>', 'why': 'tabindex above 0 breaks the reading order'})
    return {'status': 'fail', 'code': 'FOCUS_LOST', 'findings': findings} if findings else {'status': 'pass'}
