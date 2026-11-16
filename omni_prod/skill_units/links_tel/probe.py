"""skill.links.tel -- static: every phone link dials a valid Israeli number that the page shows, and every phone the
page shows has a link that dials it (a phone a customer cannot tap is a dead end on a phone)."""
import re

from omni_prod.skill_units import tags, text_nodes

_PHONE = re.compile(r'(?<!\d)(?:\+972[-\s]?|0)(?:[23489]|5\d|7\d)[-\s]?\d{3}[-\s]?\d{4}(?!\d)')


def _norm(raw: str) -> str:
    d = re.sub(r'\D', '', raw)
    return '0' + d[3:] if d.startswith('972') else d


def _valid(d: str) -> bool:
    return bool(re.fullmatch(r'0(?:[23489]\d{7}|5\d{8}|7\d{8})', d))


def probe(html):
    findings = []
    shown = {_norm(m.group()) for node in text_nodes(html) for m in _PHONE.finditer(node)}
    dialled = set()
    for _, tag, a in tags(html):
        href = a.get('href', '')
        if tag == 'a' and href.lower().startswith('tel:'):
            d = _norm(href[4:])
            dialled.add(d)
            if not _valid(d):
                findings.append({'where': href, 'why': 'not a valid Israeli phone number'})
            elif shown and d not in shown:
                findings.append({'where': href, 'why': f'dials {d}, which the page does not show ({sorted(shown)})'})
    for d in sorted(shown - dialled):
        findings.append({'where': d, 'why': 'a phone the page shows has no tel: link'})
    return {'status': 'fail', 'code': 'TEL_BROKEN', 'findings': findings} if findings else {'status': 'pass'}
