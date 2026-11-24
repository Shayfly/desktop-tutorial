"""Generated images go INTO the page (#324, Michael 2026-11-13).

Production build bld_cf406df6 (2026-11-12): the capability stage generated the hero image, verified it and stored it
(media.image.generate VERIFIED), but nothing handed it to code generation. The page showed an illustration the code
model drew itself; the paid, verified image was never used.

Michael's four conditions, each enforced here:
  1. An image is inserted ONLY when the plan asked for it: only media.image.generate requirements of the bound
     capability plan, only VERIFIED ones, only artifacts whose bytes match their recorded sha256.
  2. Dimensions and purpose go to the model: each image is described with its purpose and its real width x height.
  3. alt is mandatory and comes from the brief: the clause of the approved request that describes the image, or the
     product line of the request when the request has no such clause. Never empty.
  4. The blocking check stays, with a non-empty alt on top: until every image is used in a visible <img> with a
     non-empty alt, the build's acceptance fails (repair rounds, then a failed build -- never a silent pass).
Several images are handled, not only one hero: every artifact of every requested image requirement gets its own
marker, 148ai-asset://image/1, /2, ...

Same mechanism as the approved uploaded logo (uploaded_assets.py): the model writes a marker, the worker replaces it
before tests and puts the marker back in anything the model reads again (repair summaries, failure text).
Warehouse 118 (the owner, 2026-11-20): the marker becomes a FILE path, `assets/148ai-image-<n>.<ext>`, and the image
is that file in the repository (repository_assets: a text envelope every point that writes files decodes) -- no longer
a data URI inside the page. The model never sees the image bytes: the file is left out of what it reads.
"""
from __future__ import annotations

import base64
import hashlib
import io
import logging
import re
import tokenize
from dataclasses import dataclass
from functools import cached_property

from .autonomous_core import AcceptanceFailure, ExecutionReport

IMAGE_CAPABILITY = 'media.image.generate'
MARKER_PREFIX = '148ai-asset://image/'
ACCEPTANCE_ID = 'generated-image'

# The request's own words for each kind of image (media_pipeline's triggers): the alt is the clause that holds them.
_HERO_TERMS = ('תמונה ראשית', 'תמונת הירו', 'תמונת רקע', 'באנר', 'איור', 'פוסטר', 'hero image', 'hero visual',
               'hero banner', 'cover image', 'illustration', 'banner', 'poster', 'artwork', 'key art')
_ICON_TERMS = ('לוגו', 'סמליל', 'אייקון', 'logo', 'app icon', 'favicon', 'mascot')
_PURPOSE_HE = {'hero': 'תמונה ראשית', 'icon': 'סמל המוצר'}
_PURPOSE_EN = {'hero': 'Main image', 'icon': 'Product icon'}
_BRIEF_SPLIT = '--- Approved project brief'
_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedImage:
    index: int
    requirement_id: str
    purpose: str
    mime: str
    width: int | None
    height: int | None
    sha256: str
    alt: str
    data: bytes

    @property
    def marker(self) -> str:
        return f'{MARKER_PREFIX}{self.index}'

    @cached_property
    def carried(self):
        """The image as a file the page references (warehouse 118). Raises AssetCarryError if it cannot be carried."""
        from .repository_assets import CarriedImage, asset_path
        return CarriedImage(self.marker, asset_path('image', self.index, self.mime), self.data, self.mime)

    @property
    def uri(self) -> str:
        """What the page's <img src> holds after the transform: the image's file path, never its bytes."""
        return self.carried.path


# ------------------------------------------------------------------ condition 3: alt from the brief

def _kind(purpose: str) -> str:
    return 'icon' if re.search(r'\bicon\b|logo', purpose or '', re.I) else 'hero'


def aspect_ratio(purpose: str) -> str:
    """The proportions the image is generated in (an icon is square; a main image is wide)."""
    return '1:1' if _kind(purpose) == 'icon' else '16:9'


def _request_text(prompt: str) -> str:
    """The customer's request: the text before the approved-brief block (the block repeats it in English)."""
    return (prompt or '').split(_BRIEF_SPLIT, 1)[0].strip()


def describe(prompt: str, purpose: str) -> str | None:
    """The clause of the approved request that describes this image, e.g. 'תמונה ראשית גדולה של כוס קפה על שולחן
    עץ ליד חלון'. None when the request has no such clause.

    A heading followed by a colon is a label, and the description is what comes after it (production 2026-11-13,
    "מאפייה": "תמונה ראשית גדולה בראש הדף: כיכרות לחם מחמצת טריות על מדף עץ במאפייה, אור בוקר חם" was cut at the
    colon, FLUX got "A large main image at the top of the page." and drew mountains). After a colon the description
    runs to the end of its sentence or line -- commas belong to it."""
    terms = _ICON_TERMS if _kind(purpose) == 'icon' else _HERO_TERMS
    for line in _request_text(prompt).splitlines():           # a line break always ends a description
        text = ' '.join(line.split())
        low = text.lower()
        hits = [low.find(t.lower()) for t in terms if t.lower() in low]
        if not hits:
            continue
        start = min(hits)
        end = re.search(r'[,.;:!?]|\s-\s|\s—\s', text[start:])
        clause = text[start:start + end.start()] if end else text[start:]
        if end and end.group(0) == ':':
            after = text[start + end.end():]
            stop = re.search(r'[.;!?](\s|$)', after)
            described = (after[:stop.start()] if stop else after).strip(' "\'')
            if described:
                return described
        clause = clause.strip(' "\'')
        if clause:
            return clause
    return None


# The customer's own style and colour words (production 2026-11-13: "סגנון חמים וכפרי, צבעים: חום קרמל, שמנת ולבן"
# never reached the image because the plan's "Design:" line was not in the planner's prompt).
_STYLE_RX = re.compile(r'(?:^|[\s.,;])(?:סגנון|style)\s*:?\s*([^.;:\n,]+)', re.I)
_COLOURS_RX = re.compile(r'(?:^|[\s.,;])(?:צבעים|צבע|colou?rs?)\s*:\s*([^.;\n]+)', re.I)


def stated_style(prompt: str) -> tuple[str | None, str | None]:
    """(style, colours) in the customer's own words, from the request; None where the request says nothing."""
    text = _request_text(prompt)
    style, colours = _STYLE_RX.search(text), _COLOURS_RX.search(text)
    return (style.group(1).strip(' "\'') if style else None), (colours.group(1).strip(' "\'') if colours else None)


def alt_text(prompt: str, purpose: str, *, number: int = 1, of: int = 1, subject: str | None = None) -> str:
    """The alt for one image, from the brief only. Never empty (a request always has a product line).
    `subject` is the clause the image was GENERATED from (the plan's constraint): when present the alt is exactly it,
    so what the image shows and what its alt says come from one source."""
    request = ' '.join(_request_text(prompt).split())
    hebrew = bool(re.search(r'[֐-׿]', request))
    clause = (subject or '').strip() or describe(prompt, purpose)
    if clause is None:
        product = re.split(r'[,.;:!?]', request, maxsplit=1)[0].strip(' "\'')
        if not product:      # nothing in the brief to take an alt from: refuse rather than invent one
            raise ValueError('a generated image needs an alt from the brief, and the brief is empty')
        clause = f'{(_PURPOSE_HE if hebrew else _PURPOSE_EN)[_kind(purpose)]} — {product}'
    if of > 1:
        clause = f'{clause} ({number}/{of})'
    return clause[:300]


# ------------------------------------------------------------------ condition 1: only what the plan asked for

def _requested_ids(plan) -> set[str]:
    return {r.id for r in getattr(plan, 'requirements', ()) or () if r.key == IMAGE_CAPABILITY}


def _purposes(plan) -> dict[str, str]:
    return {r.id: r.purpose for r in getattr(plan, 'requirements', ()) or () if r.key == IMAGE_CAPABILITY}


def _required_ids(plan) -> set:
    """The image requirements the customer actually asked for. The default hero (DECISIONS 5) is required=False."""
    return {r.id for r in getattr(plan, 'requirements', ()) or ()
            if r.key == IMAGE_CAPABILITY and getattr(r, 'required', True)}


def _subjects(plan) -> dict[str, str]:
    return {r.id: str((r.constraints or {}).get('subject') or '') for r in getattr(plan, 'requirements', ()) or ()
            if r.key == IMAGE_CAPABILITY}


def collect(*, plan, evidence: dict | None, store, prompt: str) -> list[GeneratedImage]:
    """The verified images of the plan's image requirements, in order, with their bytes checked again."""
    from .providers.image_provider import sniff_image
    requested, purposes, subjects = _requested_ids(plan), _purposes(plan), _subjects(plan)
    if not requested or not evidence:
        return []
    found: list[tuple[str, str, dict]] = []
    for row in evidence.get('requirements') or ():
        rid = str(row.get('requirement_id'))
        if row.get('capability_key') != IMAGE_CAPABILITY or rid not in requested or row.get('status') != 'VERIFIED':
            continue
        artifacts = list((row.get('verification') or {}).get('artifacts') or ())
        for position, art in enumerate(artifacts):
            key = art.get('artifact_key') or (row.get('artifact_key') if position == 0 else None)
            if key and art.get('verified', True):
                found.append((rid, key, art))
        if not artifacts and row.get('artifact_key'):
            found.append((rid, row['artifact_key'], {}))
    if not found:
        return []
    if store is None:
        raise ValueError('generated images were verified but no artifact store is available to read them')
    per_requirement: dict[str, int] = {}
    for rid, _, _ in found:
        per_requirement[rid] = per_requirement.get(rid, 0) + 1
    seen: dict[str, int] = {}
    images = []
    for index, (rid, key, art) in enumerate(found, start=1):
        data = bytes(store.get_bytes(key))
        digest = hashlib.sha256(data).hexdigest()
        if art.get('sha256') and art['sha256'] != digest:
            raise ValueError(f'generated image {key} does not match its verified sha256')
        mime, width, height = sniff_image(data)
        # warehouse 114 (the butcher, bld_83529c13: the generated hero went into the page as 1,735,408 base64
        # characters): the page carries a web-sized rendition; `sha256` stays the digest of the verified artifact.
        from .web_rendition import rendition
        light = rendition(data, mime)
        if light['changed']:
            data, mime, width, height = light['data'], light['mime'], light['width'], light['height']
        _LOG.info('GENERATED_IMAGE index=%s changed=%s bytes=%s original_bytes=%s size=%sx%s step=%s', index,
                  light['changed'], len(data), light['original_bytes'], width, height, light['step'])
        seen[rid] = seen.get(rid, 0) + 1
        images.append(GeneratedImage(
            index=index, requirement_id=rid, purpose=purposes.get(rid, 'image'), mime=mime, width=width,
            height=height, sha256=digest, data=data,
            alt=alt_text(prompt, purposes.get(rid, 'image'), number=seen[rid], of=per_requirement[rid],
                         subject=subjects.get(rid))))
    return images


# ------------------------------------------------------------------ condition 2: what the model is told

# Warehouse 118: the generated server serves the image files. The preview smoke checks it (preview_smoke._SMOKE).
ASSET_SERVING = ('The images are files under assets/ in the repository. The server must answer GET /assets/<name> '
                 'with the file\'s bytes (open it in binary mode) and its Content-Type (image/webp, image/jpeg or '
                 'image/png), e.g. mimetypes.guess_type; never inline an image as base64 in the page.')

def prompt_block(images: list[GeneratedImage]) -> str:
    if not images:
        return ''
    lines = ['Generated images (verified by 148AI; already paid for). Use EVERY one of them, each in a visible <img> '
             'element with its exact src marker and its exact alt text. The worker replaces each marker with the '
             'path of the image file (shown below) and puts that file in the repository before tests. Do NOT draw a '
             'replacement for these images (no SVG, canvas or CSS drawing of the subject) and do not use another '
             'image in their place. Size the element to the image proportions given; it must stay responsive '
             '(max-width: 100%; height: auto).', ASSET_SERVING]
    for img in images:
        size = f'{img.width}x{img.height} px' if img.width and img.height else 'size unknown'
        lines.append(f'- image {img.index}: src="{img.marker}"; purpose: {img.purpose}; {size}; {img.mime}; '
                     f'alt="{img.alt}"; file: {img.uri}')
    return '\n'.join(lines)


# ------------------------------------------------------------------ marker <-> bytes

class _Transform:
    """Markers -> image files after generation and after every repair; the reverse for anything the model reads.
    Wraps the transform already installed (uploaded logo, right-to-left) and keeps its redaction too.
    Warehouse 118: each marker becomes `assets/148ai-image-<n>.<ext>` and that file is (re)written into the repository;
    the page carries no image bytes. An image that cannot be carried raises AssetCarryError here, at install."""

    def __init__(self, inner, images: list[GeneratedImage]):
        self._inner, self._images = inner, images
        self._carried = [img.carried for img in images]       # built now: a failure is loud before any build round

    def __call__(self, repo):
        repo = self._inner(repo) if self._inner is not None else repo
        for carried in self._carried:
            repo = carried.place(repo)
        return repo

    def redact(self, repo):
        out = dict(repo)
        for carried in self._carried:
            out = carried.unplace(out)
        inner = getattr(self._inner, 'redact', None)
        return inner(out) if inner else out

    def redact_text(self, text):
        for carried in self._carried:
            text = carried.redact_text(text)
        inner = getattr(self._inner, 'redact_text', None)
        return inner(text) if inner else text

    def __getattr__(self, name):
        if self._inner is None:
            raise AttributeError(name)
        return getattr(self._inner, name)


# ------------------------------------------------------------------ condition 4: the blocking check (+ non-empty alt)

_SOURCES = ('.html', '.htm', '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.py')
_IMG_TAG = re.compile(r'<img\b[^>]*>', re.I | re.S)
_ALT = re.compile(r'\balt\s*=\s*(?:\{\s*)?(["\'`])(.*?)\1', re.I | re.S)


def _strip_comments(path: str, source: str) -> str:
    if path.endswith('.py'):
        try:
            source = tokenize.untokenize(t for t in tokenize.generate_tokens(io.StringIO(source).readline)
                                         if t.type != tokenize.COMMENT)
        except (tokenize.TokenError, IndentationError):
            return ''
    return re.sub(r'<!--.*?-->|/\*.*?\*/|^\s*//[^\n]*', '', source, flags=re.S | re.M)


def _names_the_image(src: str, img: GeneratedImage) -> bool:
    """True when an <img src> names this image: its marker, or its file path in any form repository_assets.names_file
    accepts ('assets/x', './assets/x', '/assets/x', with or without a query or fragment)."""
    from .repository_assets import names_file
    return src == img.marker or names_file(src, img.uri)


def placement(repo: dict, img: GeneratedImage) -> str:
    """'ok', 'missing' (no visible <img> with this image) or 'no_alt' (used, but every use has an empty alt)."""
    used = False
    for path, source in repo.items():
        if not isinstance(source, str) or not path.lower().endswith(_SOURCES):
            continue
        for tag in _IMG_TAG.findall(_strip_comments(path, source)):
            src = re.search(r'\bsrc\s*=\s*(?:\{\s*)?(["\'`])(.*?)\1', tag, re.I | re.S)
            if not src or not _names_the_image(src.group(2), img):
                continue
            used = True
            alt = _ALT.search(tag)
            if alt and alt.group(2).strip():
                return 'ok'
    return 'no_alt' if used else 'missing'


class GeneratedImagesExecutor:
    def __init__(self, inner, images: list[GeneratedImage]):
        self._inner, self.images = inner, images

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        problems = []
        for img in self.images:
            state = placement(repository, img)
            if state == 'missing':
                problems.append(AcceptanceFailure(ACCEPTANCE_ID, (
                    f'Generated image {img.index} ({img.purpose}) is not on the page. Add a visible <img '
                    f'src="{img.marker}" alt="{img.alt}">; do not draw a replacement.')))
            elif state == 'no_alt':
                problems.append(AcceptanceFailure(ACCEPTANCE_ID, (
                    f'Generated image {img.index} ({img.purpose}) has an empty or missing alt. Use '
                    f'alt="{img.alt}".')))
        if not problems:
            return report
        return ExecutionReport(False, tuple(report.failures) + tuple(problems), report.build_log)


def install(engine, *, prompt: str, plan, evidence: dict | None, store, vision=None) -> str:
    """Bind the plan's verified images into the build. Returns the prompt the engine builds from (unchanged when
    the plan asked for no image).

    Lens 11 / I-01 (Michael 2026-11-14): with a `vision` gateway, every image is first checked against the subject
    the customer asked for (image_match.verify) -- BEFORE any code is generated, so a wrong picture costs one vision
    call, not a build. A mismatch, or a check that cannot run, raises image_match.ImageDoesNotMatch."""
    images = collect(plan=plan, evidence=evidence, store=store, prompt=prompt)
    if not images:
        return prompt
    if vision is not None:
        from .image_match import check_optional, verify
        core = getattr(engine, 'core', engine)
        # A picture the customer asked for is judged as before: a mismatch, or a check that cannot run, stops the
        # build. The default hero nobody asked for (DECISIONS 5) is optional by the owner's decision, so it is never
        # a reason to fail: it is kept only if it was checked and matches, and otherwise dropped from the build.
        wanted = _required_ids(plan)
        asked_for = [i for i in images if i.requirement_id in wanted]
        by_default = [i for i in images if i.requirement_id not in wanted]
        verdicts = verify(vision, asked_for, _subjects(plan))
        kept, optional_verdicts = check_optional(vision, by_default, _subjects(plan))
        core.image_match = verdicts + optional_verdicts
        dropped = [v for v in optional_verdicts if v['status'] == 'DROPPED']
        if dropped:
            _LOG.info('IMAGE_DROPPED_NOT_SHOWN count=%s reasons=%s', len(dropped),
                      '; '.join(str(v.get('reason'))[:80] for v in dropped))
        images = [i for i in images if i in asked_for or i in kept]
        if not images:
            return prompt
    core = getattr(engine, 'core', engine)
    core.repository_transform = _Transform(getattr(core, 'repository_transform', None), images)
    core.executor = GeneratedImagesExecutor(core.executor, images)
    core.generated_images = images
    return f'{prompt}\n\n{prompt_block(images)}'
