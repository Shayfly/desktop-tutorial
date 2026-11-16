"""skill.a11y.heading_order -- static: exactly one h1, first; going down, no level is skipped (h2 -> h4)."""
import re


def probe(html):
    levels = [int(m.group(1)) for m in re.finditer(r'<h([1-6])\b', html or '', re.I)]
    findings = []
    if levels.count(1) != 1:
        findings.append({'why': f'{levels.count(1)} h1 elements (exactly one is needed)'})
    if levels and levels[0] != 1:
        findings.append({'why': f'the first heading is h{levels[0]}, not h1'})
    for a, b in zip(levels, levels[1:]):
        if b > a + 1:
            findings.append({'why': f'h{a} is followed by h{b}: a level is skipped'})
    return {'status': 'fail', 'code': 'HEADING_ORDER', 'findings': findings} if findings else {'status': 'pass'}
