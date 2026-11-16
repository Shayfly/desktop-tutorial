"""skill.perf.hero_eager -- static: the first <img> must not carry loading="lazy"."""
from omni_prod.skill_units import tags


def probe(html):
    imgs = [a for _, tag, a in tags(html) if tag == 'img']
    if imgs and imgs[0].get('loading', '').lower() == 'lazy':
        return {'status': 'fail', 'code': 'HERO_LAZY',
                'findings': [{'where': imgs[0].get('src', '?')[:80], 'why': 'the first image is loading="lazy"'}]}
    return {'status': 'pass'}
