"""skill.brand.name -- static: the business name the page gives itself (the <title> before its separator, or the
whole title) is shown on the page, not only in the browser tab."""
import re

from omni_prod.skill_units import text_nodes

_TITLE = re.compile(r'<title[^>]*>(.*?)</title>', re.S | re.I)


def probe(html):
    m = _TITLE.search(html or '')
    if not m or not m.group(1).strip():
        return {'status': 'fail', 'code': 'BRAND_MISSING', 'findings': [{'where': '<title>', 'why': 'the page has no title'}]}
    name = re.split(r'\s[|\-–—·•]\s', m.group(1).strip())[0].strip()
    body = (html or '')[m.end():]
    if not any(name in node for node in text_nodes(body)):
        return {'status': 'fail', 'code': 'BRAND_MISSING',
                'findings': [{'where': name[:80], 'why': 'the business name in the title is not shown on the page'}]}
    return {'status': 'pass'}
