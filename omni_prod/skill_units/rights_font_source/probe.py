"""skill.rights.font_source -- static: every font reference of the page has a source listed in rights_sources.json."""
from omni_prod.rights_sources import unknown


def probe(html, path=None):
    findings = unknown(html, 'font', path)
    return {'status': 'fail', 'code': 'FONT_SOURCE_UNKNOWN', 'findings': findings} if findings else {'status': 'pass'}
