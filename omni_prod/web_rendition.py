"""The page's copy of an image: the lowest bytes at the best quality (image weight; the owner, 2026-11-26).

The owner, 2026-11-26: "every image the customer uploads, the system brings down from its size to the lowest size at
the best quality". Before this (warehouse 114, 2026-11-16) a file of 360,000 bytes or less was carried byte for byte --
with its EXIF, so a phone photo published its GPS position and the phone's make and model inside the customer's site
and its export zip (a privacy defect, measured on main fa41a5d: the GPS block, make and model were read back from the
page's file and from the zip) -- and a heavier one went through six fixed steps, past which the BUILD STOPPED.

Now every image the platform puts in a page -- the customer's photos (uploaded_assets._MainImage) and the generated
images (generated_images.collect) -- is converted; none of them is carried as uploaded. (The uploaded LOGO is not
one of them: uploaded_assets.logo_transform still carries it as uploaded, metadata included -- open.)

1. Read. A file that is not an image, an animated image or a decompression bomb is refused by name (RenditionError).
   A phone JPEG with a second picture in it (MPO: a depth map, a gain map) is a still photo: its first picture is used.
2. Upright and clean. The rotation tag is applied; the colours are converted to sRGB from the embedded ICC profile; and
   nothing else of the file reaches the page -- no EXIF (GPS, make, model, time), no XMP, no ICC profile, no text chunk.
3. Sized for its place. The long side is at most PLACE_SIDE[place]: the largest the page shows that place at, a phone
   counted at 2x (section_library/library.css: content 72rem = 1152 CSS px; the hero panel is object-fit: cover at
   min-height 26rem, so a landscape photo on a 382 px wide phone panel is drawn about 740 CSS px wide = 1,480 device px;
   a story photo is 4:3 cover in up to 912 CSS px; a gallery tile is 4:3 cover, one column on a phone = 382 CSS px; an
   icon sits in the header). Never enlarged; the proportions are kept.
4. The lowest bytes that still look the same. Each candidate format is searched for the LOWEST quality whose SSIM to the
   sized source is at least THRESHOLD (ssim() below: luma, 8x8 windows at stride 4, on Pillow alone; it matches a numpy
   implementation of the same definition to 4e-6 and the 11x11 Gaussian SSIM of Wang et al. to 0.002). A binary search
   over [QUALITY_FLOOR, 100]: at most MAX_SEARCH_ENCODES encodes per format. The floor is there because SSIM does not see
   blotches in a flat gradient: WebP q20 scores 0.9975 on a sky with visible blotches, JPEG q30 0.996 with visible 8x8
   blocks; from q50 on neither is visible at 2x zoom, so the floor is 60 (with a margin). Candidates:
     - WebP, lossy: always (alpha is kept, losslessly: alpha_quality 100);
     - JPEG: for a JPEG original without alpha -- the clean re-encode of the original in its own format;
     - WebP, lossless: for an image of at most LOSSLESS_COLOURS colours (a logo, a flat drawing, a screenshot), which a
       lossless file can beat; a photo has far more colours and its lossless file is 10 to 20 times the lossy one.
   The smallest candidate that passes is kept; if none passes, the most similar one, and the record says so.
   The format, by numbers (2026-11-26: threshold 0.98, floor 60, the 45 distinct PNGs of the repository and two 12 MP
   photo-like images, at 1600 px): WebP lossy was the smallest in 44 of 47 and WebP lossless in 3 (UI screenshots); a
   JPEG or a re-encoded PNG in none. On a textured 12 MP phone JPEG the JPEG re-encode can win (177,565 bytes against
   190,502 for WebP, both at 0.98), so it stays a candidate for a JPEG original. AVIF was smaller on 45 of 47 (median
   23%), but it is not used: its search took a median 8.5 times as long as WebP's (about 5 s, up to 8.7 s, for one
   picture), a single <img src> has no fallback, and a browser without AVIF shows a broken picture (caniuse.com, read
   2026-11-26: AVIF from iOS Safari 16, macOS Safari 16.4, Edge 121, Firefox 93, never Opera Mini or KaiOS; WebP from
   iOS 14, Safari 14 on macOS 11, Edge 18, Firefox 65); and the carried-file contract (repository_assets.MIME_EXT, the
   preview smoke, the server instruction ASSET_SERVING) knows only WebP, JPEG and PNG.
5. Weight is never a refusal. A result over `max_bytes` (one image: BUDGET_BYTES) steps down the bounded list STEPS
   until it fits. If even the last step does not fit, the last step is carried and the record and the log say so
   (IMAGE_WEIGHT_OVER_BUDGET) -- the build goes on. G4's perf_inline_image_weight reads only data: URIs in the page
   (skill_units/perf_inline_image_weight/probe.py), and since warehouse 118 a carried image is a file, so G4 cannot
   see it: this log line and the build evidence (report()) are where it is said.
6. The page. fit_page() shrinks the renditions of one page proportionally so that together they fit a byte budget
   (a4.PAGE_IMAGE_BUDGET_BYTES), re-encoding each from its original, in the same format and file.

The customer's file itself is never changed: the original stays in the attachment store under its own sha256, and the
record of every image (the build log and the build evidence) holds both digests.
"""
from __future__ import annotations

import hashlib
import io
import logging
import math
import numbers
import time

BUDGET_BYTES = 360_000          # one image, as carried: 480,000 base64 characters, under perf_inline_image_weight's 500,000
THRESHOLD = 0.98                # SSIM on luma that the converted image must keep against the sized source
# The largest the page shows each place at, long side in px, a phone counted at 2x (the docstring, point 3).
PLACE_SIDE = {'hero': 1600, 'story': 1280, 'products': 1024, 'gallery': 1024, 'icon': 512}
MAX_SIDE = PLACE_SIDE['hero']
QUALITY_FLOOR = 60              # the lowest quality a search may choose (SSIM is blind below it: the docstring, point 4)
MAX_SEARCH_ENCODES = 7          # per format: a binary search over [QUALITY_FLOOR, 100] needs 6
LOSSLESS_COLOURS = 16_384       # at most this many colours: a lossless WebP is a candidate too
# Over the byte budget: tried in order until one fits (scale of the place side, WebP or JPEG quality); bounded.
STEPS = ((1.0, 80), (1.0, 70), (0.8, 75), (0.8, 65), (0.64, 70), (0.5, 65), (0.4, 60))
MAX_PIXELS = 60_000_000         # a decompression bomb is refused, not decoded
SSIM_MAX_SIDE = MAX_SIDE        # the similarity is measured at the carried size, never above this side
OUTPUT_MIMES = ('image/webp', 'image/jpeg')
_FORMAT_MIME = {'JPEG': 'image/jpeg', 'MPO': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp',
                'GIF': 'image/gif'}
_C1, _C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
_LOG = logging.getLogger(__name__)


class RenditionError(ValueError):
    """The file cannot be put in the page: not an image, an animated image, or a decompression bomb. Never its weight."""


def _pil():
    try:
        from PIL import Image
    except ImportError as exc:                              # the worker image must have it: said, never skipped
        raise RenditionError('Pillow is not installed: an image cannot be prepared for the page') from exc
    return Image


# ------------------------------------------------------------------ similarity

def _luma(img, background=None):
    Image = _pil()
    if img.mode == 'RGBA':
        img = Image.alpha_composite(Image.new('RGBA', img.size, background), img)
    return img.convert('L')


def _window_ssim(x, y) -> float:
    """Mean SSIM of two same-size 'L' images: 8x8 windows at stride 4 (4x4 block means, two by two), population
    moments, C1 = (0.01 * 255)^2, C2 = (0.03 * 255)^2. Every per-pixel step runs in Pillow's C code (ImageMath on 'F'
    images, BOX resampling for the means); nothing loops over pixels in Python."""
    Image = _pil()
    from PIL import ImageMath
    if max(x.size) > SSIM_MAX_SIDE:                         # bounded: never measured above SSIM_MAX_SIDE
        factor = math.ceil(max(x.size) / SSIM_MAX_SIDE)
        x, y = x.reduce(factor), y.reduce(factor)
    x, y = x.convert('F'), y.convert('F')
    box = Image.Resampling.BOX

    def mul(p, q):
        return ImageMath.lambda_eval(lambda v: v['p'] * v['q'], p=p, q=q)

    def mean(im):
        return im.resize((1, 1), box).getpixel((0, 0))

    w, h = (x.width // 4) * 4, (x.height // 4) * 4
    if w < 8 or h < 8:                                      # too small for one 8x8 window: the whole image is one
        mx, my = mean(x), mean(y)
        vx, vy, cxy = mean(mul(x, x)) - mx * mx, mean(mul(y, y)) - my * my, mean(mul(x, y)) - mx * my
        return ((2 * mx * my + _C1) * (2 * cxy + _C2)) / ((mx * mx + my * my + _C1) * (vx + vy + _C2))
    x, y = x.crop((0, 0, w, h)), y.crop((0, 0, w, h))
    bw, bh = w // 4, h // 4
    blocks = [im.resize((bw, bh), box) for im in (x, y, mul(x, x), mul(y, y), mul(x, y))]

    def windows(im):                                        # the mean of 2x2 neighbouring blocks = one 8x8 window
        return ImageMath.lambda_eval(lambda v: (v['a'] + v['b'] + v['c'] + v['d']) / 4,
                                     a=im.crop((0, 0, bw - 1, bh - 1)), b=im.crop((1, 0, bw, bh - 1)),
                                     c=im.crop((0, 1, bw - 1, bh)), d=im.crop((1, 1, bw, bh)))
    ux, uy, uxx, uyy, uxy = (windows(b) for b in blocks)
    smap = ImageMath.lambda_eval(
        lambda v: ((v['ux'] * v['uy'] * 2 + _C1) * ((v['uxy'] - v['ux'] * v['uy']) * 2 + _C2))
        / ((v['ux'] * v['ux'] + v['uy'] * v['uy'] + _C1)
           * ((v['uxx'] - v['ux'] * v['ux']) + (v['uyy'] - v['uy'] * v['uy']) + _C2)),
        ux=ux, uy=uy, uxx=uxx, uyy=uyy, uxy=uxy)
    return mean(smap)


def ssim(a, b) -> float:
    """Similarity of two same-size images (RGB or RGBA), 1.0 when identical. On luma; for an image with transparency,
    the lower of its composites on black and on white, so a change hidden by one background is seen on the other."""
    if a.size != b.size:
        raise ValueError(f'ssim of different sizes: {a.size} and {b.size}')
    if 'A' in a.mode or 'A' in b.mode:
        a, b = a.convert('RGBA'), b.convert('RGBA')
        return min(_window_ssim(_luma(a, bg), _luma(b, bg)) for bg in ((0, 0, 0, 255), (255, 255, 255, 255)))
    return _window_ssim(_luma(a), _luma(b))


# ------------------------------------------------------------------ reading

def _open(data: bytes, mime: str):
    Image = _pil()
    try:
        img = Image.open(io.BytesIO(data))
    except Image.DecompressionBombError as exc:
        raise RenditionError(f'a decompression bomb is refused: {exc}') from exc
    except Exception as exc:
        raise RenditionError(f'the image could not be read as an image ({type(exc).__name__})') from exc
    if img.width * img.height > MAX_PIXELS:
        raise RenditionError(f'a decompression bomb is refused: {img.width}x{img.height} is '
                             f'{img.width * img.height:,} pixels, over {MAX_PIXELS:,}')
    if getattr(img, 'is_animated', False) and img.format != 'MPO':
        raise RenditionError('an animated image cannot be used as a picture on the page')
    found = _FORMAT_MIME.get(img.format)
    if found is None:
        raise RenditionError(f'the image could not be read as an image (a {img.format} file is not a PNG, JPEG, '
                             'WebP or GIF)')
    if found != mime:
        raise RenditionError(f'the file says {mime} but its bytes are {found}')
    return img


def _orientation(value) -> int | None:
    """The rotation tag as the record keeps it: an int, or None. A file may store the tag as UNDEFINED (bytes) or
    RATIONAL (an IFDRational); either would make the build evidence unserialisable (json.dumps fails, and
    dumps_evidence_for_terminal_state then replaces ALL the evidence with an error marker -- review 2026-11-26)."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        return None
    number = float(value)
    return int(number) if number.is_integer() else None


def _facts(img) -> dict:
    """What the original carried that the page does not: said in the record. Reading the metadata may decode the file
    (a PNG's eXIf chunk) or parse a broken EXIF block: any failure there is a named RenditionError."""
    try:
        exif = img.getexif()
        gps = bool(exif.get_ifd(0x8825))
    except Exception as exc:
        raise RenditionError(f'the image could not be read as an image ({type(exc).__name__} in its metadata)') from exc
    return {'exif': len(exif) > 0, 'gps': gps, 'orientation': _orientation(exif.get(0x0112)),
            'xmp': any(k in img.info for k in ('xmp', 'XML:com.adobe.xmp')), 'icc': bool(img.info.get('icc_profile')),
            'comment': 'comment' in img.info,
            'text': sorted(k for k in img.info if isinstance(img.info.get(k), str)
                           and k not in ('xmp', 'XML:com.adobe.xmp'))}


def _scaled(size, side):
    w, h = size
    scale = min(1.0, side / max(w, h))
    return max(1, round(w * scale)), max(1, round(h * scale))


def _source(img, side: int):
    """(the sized, upright, sRGB, metadata-free image, the ICC note). Never enlarged; proportions kept."""
    Image = _pil()
    from PIL import ImageCms, ImageOps
    need = _scaled(img.size, side)
    if img.format in ('JPEG', 'MPO') and need[0] * 4 <= img.width:   # a JPEG 4x the size or more: decoded at 1/2 or
        img.draft(None, (need[0] * 2, need[1] * 2))                  # 1/4 directly, still 2x the size it is made at
    try:
        img.load()
    except Exception as exc:
        raise RenditionError(f'the image could not be read as an image ({type(exc).__name__})') from exc
    icc = img.info.get('icc_profile')
    try:
        upright = ImageOps.exif_transpose(img)              # a phone photo is stored sideways with a rotation tag
    except Exception as exc:
        raise RenditionError(f'the image could not be read as an image ({type(exc).__name__} in its metadata)') from exc
    if upright.mode == 'F' or upright.mode == 'I' or upright.mode.startswith('I;16'):   # 16-bit grey: to 8 bits
        upright = upright if upright.mode == 'F' else upright.convert('I')
        top = upright.getextrema()[1]
        factor = 255 / top if top > 255 or (upright.mode == 'F' and 0 < top <= 1) else 1
        upright = upright.point(lambda v: v * factor).convert('L')
    has_alpha = upright.mode in ('RGBA', 'LA', 'PA', 'RGBa', 'La') or 'transparency' in upright.info
    if upright.mode not in ('RGB', 'L', 'CMYK') or has_alpha:
        upright = upright.convert('RGBA' if has_alpha else 'RGB')
    upright.thumbnail((side, side), Image.Resampling.LANCZOS)        # keeps the proportions; never enlarges
    alpha = upright.getchannel('A') if upright.mode == 'RGBA' else None
    note = 'none: sRGB assumed (a browser assumes it too)'
    out = None
    if icc:
        try:
            profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            space = profile.profile.xcolor_space.strip()
            src = {'RGB': lambda: upright.convert('RGB'), 'GRAY': lambda: upright.convert('L'),
                   'CMYK': lambda: upright if upright.mode == 'CMYK' else None}.get(space, lambda: None)()
            if src is None:
                raise ValueError(f'a {space} profile on a {upright.mode} image')
            out = ImageCms.profileToProfile(src, profile, ImageCms.createProfile('sRGB'), outputMode='RGB')
            note = 'converted to sRGB'
        except Exception as exc:        # a profile that cannot be read: dropped, said in the record and the log
            note = f'unreadable ({type(exc).__name__}): left out, colours as stored'
            _LOG.warning('IMAGE_ICC_UNREADABLE %s', exc)
    if out is None:
        out = upright.convert('RGB')
        if upright.mode == 'CMYK' and not icc:
            note = 'none: a CMYK image converted without a profile'
    if alpha is not None and alpha.getextrema() != (255, 255):
        out.putalpha(alpha)                                  # transparency is kept; an all-opaque alpha is dropped
    clean = Image.new(out.mode, out.size)                    # a new image: no info, no EXIF, no XMP, no ICC
    clean.paste(out)
    return clean, note


# ------------------------------------------------------------------ encoding

def _encode(img, fmt: str, quality: int | None) -> bytes:
    out = io.BytesIO()
    if fmt == 'webp':
        img.save(out, 'WEBP', quality=quality, method=4)
    elif fmt == 'webp-lossless':
        img.save(out, 'WEBP', lossless=True, method=4)
    elif fmt == 'jpeg':
        img.save(out, 'JPEG', quality=quality, optimize=True, progressive=True)
    else:
        raise ValueError(f'unknown output format {fmt!r}')
    return out.getvalue()


def _mime(fmt: str) -> str:
    return 'image/jpeg' if fmt == 'jpeg' else 'image/webp'


class _Tried:
    def __init__(self):
        self.encodes, self.rows = 0, []

    def candidate(self, img, fmt, quality):
        data = _encode(img, fmt, quality)
        self.encodes += 1
        decoded = _pil().open(io.BytesIO(data))
        decoded.load()
        score = ssim(img, decoded.convert(img.mode))
        row = {'format': fmt, 'quality': quality, 'bytes': len(data), 'similarity': round(score, 5),
               'passed': score >= THRESHOLD, 'size': list(img.size)}
        self.rows.append(row)
        return {'data': data, 'score': score, **row}


def _search(img, fmt: str, tried: _Tried):
    """(the smallest candidate at or above THRESHOLD or None, the most similar candidate). A binary search for the lowest
    quality that passes; at most MAX_SEARCH_ENCODES encodes."""
    lo, hi, best, top, n = QUALITY_FLOOR, 100, None, None, 0
    while lo <= hi and n < MAX_SEARCH_ENCODES:
        q = (lo + hi) // 2
        c = tried.candidate(img, fmt, q)
        n += 1
        if top is None or c['score'] > top['score']:
            top = c
        if c['score'] >= THRESHOLD:
            if best is None or c['bytes'] < best['bytes']:
                best = c
            hi = q - 1
        else:
            lo = q + 1
    return best, top


def rendition(data: bytes, mime: str, *, place: str = 'hero', max_bytes: int = BUDGET_BYTES,
              keep_mime: str | None = None, search: bool = True, label: str = 'image') -> dict:
    """The page's copy of one image. {'data', 'mime', 'width', 'height', 'sha256', 'changed' (always True: nothing is
    carried as uploaded), 'original_sha256', 'original_bytes', 'original_mime', 'original_size', 'place', 'side',
    'format', 'quality', 'similarity', 'threshold', 'threshold_met', 'max_bytes', 'over_budget', 'step' (None, or
    [side, quality] of STEPS when the budget needed one), 'removed', 'icc', 'candidates', 'encodes', 'ms', 'bytes'}.
    `keep_mime` keeps the output type (the page fit: the same file). `search` False goes straight to STEPS (the page
    fit, which already knows the threshold result is over its share). Raises RenditionError, never for weight."""
    if place not in PLACE_SIDE:
        raise ValueError(f'unknown place {place!r}: one of {sorted(PLACE_SIDE)}')
    if keep_mime is not None and keep_mime not in OUTPUT_MIMES:
        raise ValueError(f'keep_mime must be one of {OUTPUT_MIMES}, not {keep_mime!r}')
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        raise ValueError(f'max_bytes must be a positive int, not {max_bytes!r}')
    if not search and keep_mime is None:
        raise ValueError('search=False is the page fit: it needs keep_mime (the format of the file it remakes)')
    started = time.perf_counter()
    img = _open(data, mime)
    original_size, facts = list(img.size), _facts(img)
    side = PLACE_SIDE[place]
    sized, icc_note = _source(img, side)
    tried = _Tried()
    lossy = 'jpeg' if keep_mime == 'image/jpeg' else 'webp'
    chosen = None                    # search False: the page fit, whose threshold result is known to be over its share
    if search:
        passing, tops = [], []
        formats = [lossy]
        if keep_mime is None and img.format in ('JPEG', 'MPO') and sized.mode == 'RGB':
            formats.append('jpeg')   # the clean re-encode of a JPEG original, in its own format
        for fmt in formats:
            best, top = _search(sized, fmt, tried)
            passing += [best] if best else []
            tops.append(top)
        if lossy == 'webp' and sized.getcolors(maxcolors=LOSSLESS_COLOURS) is not None:
            c = tried.candidate(sized, 'webp-lossless', None)
            (passing if c['score'] >= THRESHOLD else tops).append(c)
        chosen = min(passing, key=lambda c: c['bytes']) if passing else max(tops, key=lambda c: c['score'])
    carried, step = sized, None
    if chosen is None or chosen['bytes'] > max_bytes:
        fmt = 'jpeg' if (chosen['format'] if chosen else lossy) == 'jpeg' else 'webp'
        last = None
        for scale, q in STEPS:
            smaller = sized.copy()
            smaller.thumbnail(_scaled(sized.size, max(1, round(max(sized.size) * scale))),
                              _pil().Resampling.LANCZOS)
            last = (smaller, tried.candidate(smaller, fmt, q), [max(smaller.size), q])
            if last[1]['bytes'] <= max_bytes:
                break
        carried, chosen, step = last
    body = chosen['data']
    r = {'data': body, 'mime': _mime(chosen['format']), 'width': carried.width, 'height': carried.height,
         'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body), 'changed': True,
         'original_sha256': hashlib.sha256(data).hexdigest(), 'original_bytes': len(data), 'original_mime': mime,
         'original_size': original_size, 'place': place, 'side': side, 'format': chosen['format'],
         'quality': chosen['quality'], 'similarity': chosen['similarity'], 'threshold': THRESHOLD,
         'threshold_met': chosen['score'] >= THRESHOLD, 'max_bytes': max_bytes, 'over_budget': len(body) > max_bytes,
         'step': step, 'removed': facts, 'icc': icc_note, 'candidates': tried.rows, 'encodes': tried.encodes,
         'ms': round((time.perf_counter() - started) * 1000)}
    _LOG.info('IMAGE_WEIGHT %s place=%s original_bytes=%s original_sha256=%s bytes=%s sha256=%s format=%s size=%sx%s '
              'quality=%s similarity=%s threshold=%s step=%s removed_gps=%s encodes=%s ms=%s', label, place,
              r['original_bytes'], r['original_sha256'], r['bytes'], r['sha256'], r['format'], r['width'], r['height'],
              r['quality'], r['similarity'], THRESHOLD, step, facts['gps'], r['encodes'], r['ms'])
    if not r['threshold_met']:
        _LOG.warning('IMAGE_SIMILARITY_BELOW_THRESHOLD %s similarity=%s threshold=%s', label, r['similarity'],
                     THRESHOLD)
    if r['over_budget']:
        _LOG.warning('IMAGE_WEIGHT_OVER_BUDGET %s bytes=%s max_bytes=%s: carried at the last step; G4 cannot see a '
                     'carried file, so it is said here and in the build evidence', label, r['bytes'], max_bytes)
    return r


FIT_KEYS = ('data', 'mime', 'format', 'width', 'height', 'quality', 'similarity', 'bytes', 'sha256', 'over_budget')


def fit_bytes(data: bytes, mime: str, max_bytes: int, *, place: str = 'hero') -> dict:
    """The small, stable entry point (for any caller that only has bytes and a byte target, e.g. a generated picture
    that must fit a page budget): {'data', 'mime', 'format', 'width', 'height', 'quality', 'similarity', 'bytes',
    'sha256', 'over_budget'}. The same conversion as rendition(): upright, no metadata, sized for `place`, the lowest
    bytes at THRESHOLD, then STEPS down to `max_bytes`; past the last step it is returned with over_budget True --
    never an exception for weight. RenditionError for an unreadable, animated or bomb file."""
    r = rendition(data, mime, place=place, max_bytes=max_bytes, label='fit_bytes')
    return {k: r[k] for k in FIT_KEYS}


def record(r: dict) -> dict:
    """A rendition as the build evidence keeps it: everything but the bytes."""
    return {k: v for k, v in r.items() if k != 'data'}


# ------------------------------------------------------------------ the page

def fit_page(images, *, budget: int, places: dict | None = None) -> dict:
    """Make the renditions of ONE page fit `budget` bytes together, proportionally (a4.PAGE_IMAGE_BUDGET_BYTES).

    `images`: the page's bound images (uploaded_assets._MainImage, generated_images.GeneratedImage): each has `marker`,
    `data`, `mime`, `source` (its original bytes and type), `rendition` (its record) and `refit(r)`. `places`, when
    given, is marker -> the place the asset plan gave it: an image made for a larger place is first made again for its
    own (never larger). Then, if the images still weigh more than `budget`, each is made again from its ORIGINAL with
    a byte target of its share -- budget * its bytes / all the bytes -- in the same format, so its file and path do not
    change (rendition(max_bytes=..., keep_mime=...)). Every new rendition goes into the image and its carried file
    (refit), so the transforms installed before carry the new bytes. Returns the record of what was done; `fits` False
    when even the last steps do not fit -- said, never a refusal."""
    if not isinstance(budget, int) or budget < 1:
        raise ValueError(f'budget must be a positive int, not {budget!r}')
    images = list(images)
    places = dict(places or {})
    unknown = sorted(set(places) - {img.marker for img in images})
    if unknown:
        raise ValueError(f'places names images that are not on the page: {unknown}')
    bad = sorted(f'{m}: {p!r}' for m, p in places.items() if p not in PLACE_SIDE)
    if bad:
        raise ValueError(f'unknown place(s) {bad}: one of {sorted(PLACE_SIDE)}')
    before = {img.marker: len(img.data) for img in images}
    done = []

    def made_for(img):
        """The place an image was made for; an image this module did not make cannot be made again: said, never
        guessed (checked only for an image that has to be made again)."""
        was = (getattr(img, 'rendition', None) or {}).get('place')
        if len(getattr(img, 'source', ()) or ()) != 2 or was not in PLACE_SIDE:
            raise ValueError(f'{img.marker}: no original or no conversion record to make it again from')
        return was

    def redo(img, place, max_bytes, why, search):
        made_for(img)
        data, mime = img.source
        r = rendition(data, mime, place=place, max_bytes=max_bytes, keep_mime=img.mime, search=search,
                      label=f'{img.marker} ({why})')
        img.refit(r)
        done.append({'marker': img.marker, 'why': why, 'place': place, 'bytes_before': before[img.marker],
                     'bytes': r['bytes'], 'sha256': r['sha256'], 'size': [r['width'], r['height']],
                     'quality': r['quality'], 'similarity': r['similarity'], 'step': r['step']})

    for img in images:
        place = places.get(img.marker)
        if place is not None and PLACE_SIDE[place] < PLACE_SIDE[made_for(img)]:
            redo(img, place, BUDGET_BYTES, f'made for {made_for(img)}, shown as {place}', True)
    total = sum(len(img.data) for img in images)
    if total > budget:
        for img in images:
            share = max(1, budget * len(img.data) // total)
            redo(img, made_for(img), share, f'page over {budget:,} bytes: its share is {share:,}', False)
    after = sum(len(img.data) for img in images)
    out = {'budget': budget, 'bytes_before': sum(before.values()), 'bytes_after': after, 'fits': after <= budget,
           'images': done}
    _LOG.log(logging.INFO if out['fits'] else logging.WARNING, 'IMAGE_PAGE_FIT budget=%s bytes_before=%s '
             'bytes_after=%s fits=%s remade=%s', budget, out['bytes_before'], after, out['fits'], len(done))
    return out


def report(engine) -> dict:
    """For the build evidence: every image's conversion (no bytes) and the page fit, if one ran."""
    core = getattr(engine, 'core', engine)
    rows = []
    for kind, attr in (('upload', 'uploaded_images'), ('generated', 'generated_images')):
        images = getattr(core, attr, None)
        for img in images if isinstance(images, (list, tuple)) else ():
            rec = getattr(img, 'rendition', None)
            if isinstance(rec, dict):
                rows.append({'kind': kind, 'index': img.index, 'file': img.uri, **rec})
    fit = getattr(core, 'image_fit', None)
    return {'threshold': THRESHOLD, 'budget_bytes': BUDGET_BYTES, 'images': rows,
            'page_fit': fit if isinstance(fit, dict) else None}
