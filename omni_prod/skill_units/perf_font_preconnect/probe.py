"""skill.perf.font_preconnect -- static: Google Fonts CSS with no preconnect to fonts.gstatic.com."""
from omni_prod.skill_units import tags


def probe(html):
    links = [a for _, tag, a in tags(html) if tag == 'link']
    fonts = [a['href'] for a in links if 'fonts.googleapis.com/css' in a.get('href', '')]
    pre = any('preconnect' in a.get('rel', '').lower().split() and 'fonts.gstatic.com' in a.get('href', '') for a in links)
    if fonts and not pre:
        return {'status': 'fail', 'code': 'FONT_NO_PRECONNECT',
                'findings': [{'where': fonts[0], 'why': 'no <link rel="preconnect" href="https://fonts.gstatic.com">'}]}
    return {'status': 'pass'}
