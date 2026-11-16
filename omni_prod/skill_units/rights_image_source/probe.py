"""skill.rights.image_source -- static: every image reference of the page has a source listed in rights_sources.json."""
from omni_prod.rights_sources import unknown


def probe(html, path=None):
    findings = unknown(html, 'image', path)
    return {'status': 'fail', 'code': 'IMAGE_SOURCE_UNKNOWN', 'findings': findings} if findings else {'status': 'pass'}
