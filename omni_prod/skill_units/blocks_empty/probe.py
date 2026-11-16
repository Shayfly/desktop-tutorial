"""skill.blocks.empty -- static: a section (<section>, <article>) whose only visible text is its heading, or none at
all: a block promised and left empty."""
import re

from omni_prod.skill_units import tags, text_nodes

_BLOCK = re.compile(r'<(section|article)\b([^>]*)>(.*?)</\1\s*>', re.S | re.I)


def probe(html):
    findings = []
    for m in _BLOCK.finditer(html or ''):
        inner = m.group(3)
        nodes = text_nodes(inner)
        heading = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', inner, re.S | re.I)
        media = any(t in ('img', 'iframe', 'video', 'form', 'picture', 'svg') for _, t, _ in tags(inner))
        if not media and len(nodes) <= (1 if heading else 0):
            label = nodes[0] if nodes else (re.search(r'id="([^"]+)"', m.group(2)) or [None, m.group(1)])[1]
            findings.append({'where': str(label)[:80], 'why': 'the block has a heading and nothing under it'})
    return {'status': 'fail', 'code': 'EMPTY_BLOCK', 'findings': findings} if findings else {'status': 'pass'}
