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


# ------------------------------------------------------------------ the page (release review of 550320c, S2)
# a4.PAGE_IMAGE_BUDGET_BYTES used to be checked AFTER the pictures were paid for, as a raise that surfaced as
# worker_exception ("משהו השתבש אצלנו"), and a retry paid again for the same failure. The owner, 2026-11-26: no image
# cap at all, and every image reduced to the smallest size at the best quality. So the page's images are re-encoded to
# fit the budget together; what still does not fit is carried and said (a4.install), never a failure.
# The interface mirrors fit_page of branch claude/practical-hopper-oi3qj2-image-weight (web_rendition.fit_page there),
# so the two can be unified: images with marker/data/mime and refit(r); `places` accepted and checked.
PAGE_FIT_STEPS = ((1.0, 86), (1.0, 78), (0.85, 76), (0.75, 72), (0.62, 68), (0.5, 64), (0.4, 60))   # (scale, quality)
PAGE_FIT_QUALITY_FLOOR = 60      # never below: the last step's quality
PAGE_FIT_PLACES = ('icon', 'hero', 'story', 'products', 'gallery')    # a4.PLACES
_PAGE_FIT_FORMAT = {'image/webp': 'WEBP', 'image/jpeg': 'JPEG', 'image/png': 'PNG'}


def _reencode(data: bytes, mime: str, scale: float, quality: int) -> tuple[bytes, int, int]:
    """One encode of `data` in its own type at `scale` of its size and `quality` (PNG is lossless: size only)."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise RenditionError(f'an image of the page could not be read ({type(exc).__name__})') from exc
    fmt = _PAGE_FIT_FORMAT[mime]
    if fmt == 'JPEG' and img.mode != 'RGB':
        img = img.convert('RGB')
    elif fmt != 'JPEG' and img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGBA' if 'transparency' in img.info or img.mode in ('LA', 'PA') else 'RGB')
    if scale < 1:
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                         Image.Resampling.LANCZOS)
    out = io.BytesIO()
    if fmt == 'WEBP':
        img.save(out, format='WEBP', quality=quality, method=4)
    elif fmt == 'JPEG':
        img.save(out, format='JPEG', quality=quality, optimize=True, progressive=True)
    else:
        img.save(out, format='PNG', optimize=True)
    return out.getvalue(), img.width, img.height


def fit_page(images, *, budget: int, places: dict | None = None) -> dict:
    """Make ONE page's images fit `budget` bytes together (a4.PAGE_IMAGE_BUDGET_BYTES), each in its own type so its
    file and path do not change. Each image over its share (budget * its bytes / all the bytes) is encoded again from
    its current bytes by PAGE_FIT_STEPS -- descending quality and width, never below PAGE_FIT_QUALITY_FLOOR, at most
    len(PAGE_FIT_STEPS) encodes -- and takes the first step that fits its share, else the smallest it reached; an encode
    that is not smaller is never taken. The new bytes go into the image and its carried file (refit). Returns
    {'budget', 'bytes_before', 'bytes_after', 'fits', 'count', 'images'}: `fits` False when even the last steps do
    not fit -- said by the caller, never a refusal. Raises ValueError on a bad argument, RenditionError on an image
    that cannot be read."""
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1:
        raise ValueError(f'budget must be a positive int, not {budget!r}')
    images = list(images)
    places = dict(places or {})
    unknown = sorted(set(places) - {img.marker for img in images})
    if unknown:
        raise ValueError(f'places names images that are not on the page: {unknown}')
    bad = sorted(f'{m}: {p!r}' for m, p in places.items() if p not in PAGE_FIT_PLACES)
    if bad:
        raise ValueError(f'unknown place(s) {bad}: one of {list(PAGE_FIT_PLACES)}')
    unsupported = sorted(f'{img.marker}: {img.mime}' for img in images if img.mime not in _PAGE_FIT_FORMAT)
    if unsupported:
        raise ValueError(f'an image type the page fit cannot encode: {unsupported}')
    before = {img.marker: len(img.data) for img in images}
    total, done = sum(before.values()), []
    if total > budget:
        for img in images:
            share = max(1, budget * before[img.marker] // total)
            if before[img.marker] <= share:
                continue
            fitting, smallest = None, None
            for scale, quality in PAGE_FIT_STEPS:                   # bounded: one encode per step
                body, width, height = _reencode(img.data, img.mime, scale, quality)
                candidate = (body, width, height, [scale, quality])
                if smallest is None or len(body) < len(smallest[0]):
                    smallest = candidate
                if len(body) <= share:
                    fitting = candidate
                    break
            body, width, height, step = fitting or smallest
            if len(body) >= before[img.marker]:
                continue                                            # never a heavier or equal file
            from_sha = hashlib.sha256(img.data).hexdigest()
            img.refit({'data': body, 'mime': img.mime, 'width': width, 'height': height})
            done.append({'marker': img.marker, 'place': places.get(img.marker), 'mime': img.mime,
                         'bytes_before': before[img.marker], 'bytes': len(body), 'share': share,
                         'from_sha256': from_sha, 'sha256': hashlib.sha256(body).hexdigest(),
                         'size': [width, height], 'step': step, 'fits_share': fitting is not None})
    after = sum(len(img.data) for img in images)
    return {'budget': budget, 'bytes_before': total, 'bytes_after': after, 'fits': after <= budget,
            'count': len(images), 'images': done}
