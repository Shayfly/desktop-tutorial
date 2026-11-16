"""skill.share.meta -- static: a page shared in WhatsApp or Facebook shows a title and a description (og:title and
og:description, not empty). og:image is not required yet: the hero is inlined as base64 (warehouse 114), so there is no
image URL to give."""
from omni_prod.skill_units import tags


def probe(html):
    og = {a.get('property', '').lower(): a.get('content', '').strip() for _, t, a in tags(html) if t == 'meta'}
    missing = [p for p in ('og:title', 'og:description') if not og.get(p)]
    if missing:
        return {'status': 'fail', 'code': 'SHARE_META_MISSING',
                'findings': [{'where': p, 'why': 'missing or empty: a shared link shows no preview'} for p in missing]}
    return {'status': 'pass'}
