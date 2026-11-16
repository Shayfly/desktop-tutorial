"""A web-sized rendition of a customer's photo (warehouse 114, first half; the owner, 2026-11-16).

Production, 2026-11-14 (the butcher, bld_83529c13): the hero photo went into the page as 1,735,408 base64 characters,
so the whole picture downloaded with the HTML. A phone photo is 3-5 MB and 4000 px wide; no page shows it wider than
a screen. The rendition is what the page carries: the same picture, the same proportions, the right way up, at most
MAX_SIDE px on its long side, encoded so that it fits BUDGET_BYTES (under G4's inline limit).

The customer's file itself is never changed: the original stays in the attachment store under its own sha256, and
the build log records both digests. A photo that is already light is carried as is, byte for byte.

Serving the photo as a separate file (the second half of 114) needs the sandbox, the stored version and the preview
to carry binary files; that is a separate change.
"""
from __future__ import annotations

import hashlib
import io

BUDGET_BYTES = 360_000          # 480,000 base64 characters: under perf_inline_image_weight's 500,000
MAX_SIDE = 1600                 # px on the long side: enough for a full-width hero on a 2x phone or a desktop
# Each step is tried in order until one fits; a bounded list, never a loop that searches (side px, WebP quality).
STEPS = ((1600, 82), (1600, 72), (1280, 76), (1280, 66), (1024, 70), (800, 68))
MAX_PIXELS = 60_000_000         # a decompression bomb is refused, not opened


class RenditionError(ValueError):
    """The photo could not be made light enough, or could not be read. The build stops; nothing is guessed."""


def rendition(data: bytes, mime: str) -> dict:
    """{'data', 'mime', 'width', 'height', 'sha256', 'changed', 'original_sha256', 'original_bytes', 'step'}.
    `changed` False means the bytes are the customer's own, untouched."""
    original = {'original_sha256': hashlib.sha256(data).hexdigest(), 'original_bytes': len(data)}
    if len(data) <= BUDGET_BYTES:
        # already light: the customer's own bytes, untouched and not even decoded (a browser turns a phone photo
        # upright by its own rotation tag; the tag is only lost, and so applied here, when the photo is re-encoded)
        return {'data': data, 'mime': mime, 'width': None, 'height': None, 'changed': False,
                'sha256': original['original_sha256'], 'step': None, **original}
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:                              # the worker image must have it: said, never skipped
        raise RenditionError('Pillow is not installed: a photo cannot be prepared for the page') from exc
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise RenditionError(f'the photo could not be read as an image ({type(exc).__name__})') from exc
    if getattr(img, 'is_animated', False):
        raise RenditionError('an animated image cannot be used as a photo on the page')
    upright = ImageOps.exif_transpose(img)                  # a phone photo is stored sideways with a rotation tag
    has_alpha = upright.mode in ('RGBA', 'LA') or (upright.mode == 'P' and 'transparency' in upright.info)
    base = upright.convert('RGBA' if has_alpha else 'RGB')
    for side, quality in STEPS:
        candidate = base.copy()
        candidate.thumbnail((side, side), Image.Resampling.LANCZOS)   # keeps the proportions; never enlarges
        out = io.BytesIO()
        candidate.save(out, format='WEBP', quality=quality, method=4)
        if out.tell() <= BUDGET_BYTES:
            body = out.getvalue()
            return {'data': body, 'mime': 'image/webp', 'width': candidate.width, 'height': candidate.height,
                    'changed': True, 'sha256': hashlib.sha256(body).hexdigest(), 'step': [side, quality], **original}
    raise RenditionError(f'the photo is still over {BUDGET_BYTES:,} bytes at {STEPS[-1][0]} px; it cannot be carried '
                         'in the page')
