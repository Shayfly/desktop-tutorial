"""skill.copy.placeholder -- static, page text and links: text that was meant to be replaced and was not ("lorem
ipsum", "[שם העסק]", "{business_name}", "טקסט לדוגמה", "TODO", a 123-456-7890 phone, an example.com address)."""
import re

from omni_prod.skill_units import tags, text_nodes

_TEXT = re.compile(r'lorem ipsum|dolor sit amet|\[\s*(?:שם|כתובת|טלפון|business|company|your)[^\]]{0,30}\]|\{\{?\s*\w+\s*\}?\}'
                   r'|טקסט לדוגמה|טקסט לדוגמא|כאן יופיע|כאן יבוא|\bTODO\b|\bTBD\b|\bXXX\b|your company|company name'
                   r'|123-456-7890|050-?0000000|example\.com', re.I)


def probe(html):
    findings = [{'where': node[:80], 'why': f'placeholder "{m.group()}" left in the page'}
                for node in text_nodes(html) for m in [_TEXT.search(node)] if m]
    for _, tag, a in tags(html):
        href = a.get('href', '')
        if tag == 'a' and _TEXT.search(href):
            findings.append({'where': href[:80], 'why': 'a link to a placeholder address'})
    return {'status': 'fail', 'code': 'COPY_PLACEHOLDER', 'findings': findings} if findings else {'status': 'pass'}
