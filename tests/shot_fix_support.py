"""What the screenshot-fix tests share (warehouse 124): a small real site, the answer a vision model gives for it, a PNG/JPEG maker,
and the two stand-ins for storage and for the model. Nothing here is a test."""
from __future__ import annotations

import hashlib
import io
import json

from PIL import Image

from omni_prod import attachments as A

CSS = ('body{margin:0;font-family:Heebo,sans-serif;background:#fff;color:#222}\n'
       '.hero{padding:48px 24px;text-align:center}\n.hero h1{font-size:2rem;margin:0 0 12px}\n'
       '.booking{position:relative;height:120px}\n'
       '.cta{position:absolute;bottom:-40px;right:24px;padding:12px 20px;background:#0a5;color:#fff;border-radius:8px}\n'
       '.services{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;padding:24px}\n'
       '.services li{list-style:none;padding:16px;border:1px solid #ddd;border-radius:8px}\n'
       + ''.join(f'.pad{i}{{margin:{i}px;padding:{i}px;border:{i % 3}px solid #eee}}\n' for i in range(40)))
HTML = ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><link rel="stylesheet" href="style.css"></head>'
        '<body><section class="hero"><h1>סטודיו נועה</h1></section>'
        '<section class="booking"><a class="cta" href="#book">לקביעת תור</a></section>'
        '<ul class="services"><li>תספורת</li><li>צבע</li><li>החלקה</li></ul><script src="app.js"></script></body></html>')
JS = 'document.querySelectorAll(".services li").forEach(function (li) { li.tabIndex = 0; });\n'
WORK = {'index.html': HTML, 'style.css': CSS, 'app.js': JS, 'README.md': '# the site\n', 'logo.png': 'not text'}
FIX_ANSWER = {'finding': {'section': 'הכפתור לקביעת תור', 'component': 'הכפתור "לקביעת תור"',
                          'what': 'הכפתור יורד מתחת לקצה המסך בטלפון'},
              'edits': [{'path': 'style.css',
                         'old': '.cta{position:absolute;bottom:-40px;right:24px;',
                         'new': '.cta{position:absolute;bottom:8px;right:24px;'}],
              'reply': 'הזזתי את הכפתור למעלה.'}


def png(width, height, color=(200, 30, 30)) -> bytes:
    """A PNG with a gradient (something to compress, so a reduced copy is a different image), made fast and the same every time."""
    ramp = Image.linear_gradient('L').resize((width, height))
    img = Image.merge('RGB', (ramp.point(lambda v: (v + color[0]) % 256), ramp.point(lambda v: 255 - v),
                              Image.new('L', (width, height), color[2])))
    out = io.BytesIO()
    img.save(out, 'PNG')
    return out.getvalue()


def jpeg(width, height) -> bytes:
    out = io.BytesIO()
    Image.new('RGB', (width, height), (20, 90, 200)).save(out, 'JPEG', quality=90)
    return out.getvalue()


class MemoryAttachments:
    """The attachment store with the SQL and the object store replaced by a dict: validation and digests are the real ones."""

    def __init__(self):
        self.rows, self.blobs = {}, {}

    def create(self, *, project_id, account_id, kind, data, annotation=None):
        mime, w, h = A.validate_image(data)
        row = {'id': f'att_{len(self.rows):032x}', 'project_id': project_id, 'account_id': account_id, 'kind': kind, 'mime': mime,
               'size_bytes': len(data), 'width': w, 'height': h, 'sha256': hashlib.sha256(data).hexdigest(),
               'annotation': A.validate_annotation(annotation, w, h)}
        self.rows[row['id']], self.blobs[row['id']] = row, data
        return row


class Reader:
    """The vision model: records what it was given, answers what it is told to."""
    name = 'scripted'
    model = 'test-vision-model'
    cost_state = 'CONFIRMED'
    reservation_id = 'irs_test'

    def __init__(self, answer=None, error=None):
        self.answer, self.error, self.calls = answer, error, []

    def read(self, *, system, user, image, **_):
        self.calls.append({'system': system, 'user': json.loads(user), 'image': image})
        if self.error:
            raise self.error
        return json.loads(json.dumps(self.answer))
