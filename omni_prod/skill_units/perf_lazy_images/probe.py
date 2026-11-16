"""skill.perf.lazy_images -- static: every <img> after the first carries loading="lazy"."""
from omni_prod.skill_units import tags


def probe(html):
    imgs = [a for _, tag, a in tags(html) if tag == 'img']
    findings = [{'where': a.get('src', '?')[:80], 'why': 'not loading="lazy"'} for a in imgs[1:]
                if a.get('loading', '').lower() != 'lazy']
    return {'status': 'fail', 'code': 'IMG_NOT_LAZY', 'findings': findings} if findings else {'status': 'pass'}
