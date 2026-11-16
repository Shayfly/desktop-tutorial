"""skill.links.anchor -- static: every in-page link (href="#section") points to an element with that id, so the
navigation goes where it says."""
from omni_prod.skill_units import tags


def probe(html):
    all_tags = list(tags(html))
    ids = {a['id'] for _, _, a in all_tags if a.get('id')} | {a['name'] for _, t, a in all_tags if t == 'a' and a.get('name')}
    findings = [{'where': a['href'], 'why': f'no element has id="{a["href"][1:]}"'}
                for _, tag, a in all_tags
                if tag == 'a' and a.get('href', '').startswith('#') and len(a['href']) > 1 and a['href'][1:] not in ids]
    return {'status': 'fail', 'code': 'ANCHOR_BROKEN', 'findings': findings} if findings else {'status': 'pass'}
