"""skill.perf.inline_image_weight -- static: an image inlined in the page as a data: URI larger than LIMIT characters.

Warehouse 114 (2026-11-16): the butcher page (bld_83529c13...) carried its hero image inline as 1,735,408 base64
characters, so the whole picture downloads with the HTML and nothing can cache it. The threshold is high on purpose
(the owner: G4 warns with a high threshold until 114 is fixed): a small inline icon is fine, a photo is not."""
import re

LIMIT = 500_000
_DATA = re.compile(r'data:image/[\w.+-]+;base64,([A-Za-z0-9+/=]+)')


def probe(html):
    findings = [{'where': f'data:image ({len(m.group(1)):,} base64 characters)', 'why': f'over {LIMIT:,}'}
                for m in _DATA.finditer(html or '') if len(m.group(1)) > LIMIT]
    return {'status': 'fail', 'code': 'IMAGE_INLINED_HEAVY', 'findings': findings} if findings else {'status': 'pass'}
