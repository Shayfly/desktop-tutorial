"""skill.rights.media_source -- static: every media reference of the page has a source listed in rights_sources.json."""
from omni_prod.rights_sources import unknown


def probe(html, path=None):
    findings = unknown(html, ('media', 'embed'), path)
    return {'status': 'fail', 'code': 'MEDIA_SOURCE_UNKNOWN', 'findings': findings} if findings else {'status': 'pass'}
