"""Bind the approved, owner-checked raster logo into generated text sources.

No vision call and no base64 sent to a model. Existing text-only repository
storage is preserved: the image is embedded as a data URI before verification.
"""
import base64
import hashlib
import re
import io
import tokenize
from .attachments import AttachmentRepository, EXT
from .autonomous_core import AcceptanceFailure, ExecutionReport

MARKER = '148ai-asset://logo'
_BINDING = re.compile(r'Uploaded logo attachment: (att_[a-f0-9]{32}); sha256=([a-f0-9]{64})\.')


def logo_transform(data: bytes, mime: str, digest: str):
    if mime not in EXT or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('approved logo integrity mismatch')
    encoded = base64.b64encode(data).decode('ascii')
    uri = f'data:{mime};base64,' + encoded
    def transform(repository):
        return {p:c.replace(MARKER,uri) for p,c in repository.items()}
    transform.uri = uri
    def redact_text(text):
        text = text.replace(uri, MARKER)
        # Sandbox evidence can be truncated in the middle of the URI. Remove
        # long fragments of this known image too, without stripping code.
        return re.sub(r'[A-Za-z0-9+/]{32,}={0,2}',
                      lambda m: MARKER if m.group(0) in encoded else m.group(0), text)
    transform.redact_text = redact_text
    transform.redact = lambda repository: {p:c.replace(uri,MARKER) for p,c in repository.items()}
    return transform


class LogoExecutor:
    def __init__(self, inner, uri):
        self._inner, self.uri = inner, uri

    def __getattr__(self, name):
        return getattr(self._inner,name)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository,spec=spec)
        # A reference in a comment or unrelated constant cannot satisfy this
        # source-level gate. Actual visibility still needs browser acceptance.
        if any(self._image_reference(p, c) for p, c in repository.items()):
            return report
        return ExecutionReport(False, report.failures + (AcceptanceFailure('uploaded-logo',
            f'The approved uploaded logo is missing. Add a visible img with src="{MARKER}"; do not invent a new logo.'),),
            report.build_log)

    def _image_reference(self, path, source):
        if not path.endswith(('.html', '.js', '.jsx', '.tsx', '.py')):
            return False
        if path.endswith('.py'):
            try:
                source = tokenize.untokenize(t for t in tokenize.generate_tokens(io.StringIO(source).readline)
                                            if t.type != tokenize.COMMENT)
            except (tokenize.TokenError, IndentationError):
                return False
        source = re.sub(r'<!--.*?-->|/\*.*?\*/|^\s*//[^\n]*', '', source, flags=re.S | re.M)
        return bool(re.search(r'<img\b[^>]*\bsrc\s*=\s*\{?\s*[\"\x27]' + re.escape(self.uri) +
                              r'[\"\x27]', source, re.I))


def install(engine, *, prompt, pool, store, project_id, account_id):
    match = _BINDING.search(prompt)
    if not match:
        return
    if pool is None or store is None:
        raise ValueError('approved logo requires durable attachment storage')
    repo=AttachmentRepository(pool,store)
    row=repo.get(project_id=project_id,account_id=account_id,attachment_id=match[1])
    if row['sha256'] != match[2]:
        raise ValueError('approved logo digest changed')
    transform=logo_transform(repo.read(row),row['mime'],match[2])
    core=getattr(engine,'core',engine)
    core.repository_transform=transform
    core.executor=LogoExecutor(core.executor,transform.uri)


# ---------------------------------------------------------------------------------------------------------------------
# The customer's own photo as the main image, AS IS (production 2026-11-15, "סבא שמעון": the uploaded photo was dropped
# and a different man was generated). Same marker mechanism as the logo and the generated images, plus the blocking
# check: the build is not accepted until the photo is in a visible <img> with a non-empty alt. No generation, no vision.

MAIN_ACCEPTANCE_ID = 'uploaded-main-image'
# one line per placed image (discovery.requirements_text): its attachment, digest, marker, place and the role words
_IMAGE_BINDING = re.compile(r'^Uploaded image (\d{1,2}) attachment: (att_[a-f0-9]{32}); sha256=([a-f0-9]{64}); '
                            r'src="(148ai-asset://upload/\1)"; placement: (hero|story|products|gallery); '
                            r'role (person|product|place|other): "([^"\n]{1,160})"\.', re.M)


class _MainImage:
    """One of the customer's own photos. Duck-types generated_images.GeneratedImage for its transform and check."""

    def __init__(self, data: bytes, mime: str, digest: str, alt: str, width=None, height=None, *, index: int = 1,
                 place: str = 'hero'):
        if mime not in EXT or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('uploaded image integrity mismatch')
        from .discovery import UPLOAD_MARKER
        self.data, self.mime, self.sha256, self.alt, self.index, self.place = data, mime, digest, alt, index, place
        self.width, self.height, self.marker = width, height, f'{UPLOAD_MARKER}{index}'
        self.purpose = f"the customer's own photo, as is ({place})"
        self.uri = f'data:{mime};base64,' + base64.b64encode(data).decode('ascii')


# The owner, 2026-11-16 00:18 / 00:49: a photo placed in "the story" must sit INSIDE a story section, not anywhere on
# the page. Sections are recognised by the same words the reference extractor uses (a2.extract._SECTION_WORDS),
# read from the section's opening tag (id/class) and its first heading. The hero has no section word: it is first.
_PLACE_HE = {'story': 'הסיפור שלנו', 'products': 'המוצרים שלנו', 'gallery': 'גלריה'}
_SECTION_BLOCK = re.compile(r'<section\b([^>]*)>(.*?)</section\s*>', re.S | re.I)
_HEADING = re.compile(r'<h[1-4]\b[^>]*>(.*?)</h[1-4]\s*>', re.S | re.I)


def place_state(repository: dict, img) -> str:
    """'ok' | 'no_section' (the page has no section for this place) | 'wrong_section' (it has one; the photo is
    outside it). Only for story / products / gallery; every other place is 'ok' here."""
    if img.place not in _PLACE_HE:
        return 'ok'
    from .a2.extract import _SECTION_WORDS
    words = re.compile(_SECTION_WORDS[img.place], re.I)
    found = False
    for path, source in repository.items():
        if not isinstance(source, str):
            continue
        for attrs, body in _SECTION_BLOCK.findall(source):
            heading = _HEADING.search(body)
            label = attrs + ' ' + re.sub(r'<[^>]+>', ' ', heading.group(1) if heading else '')
            if not words.search(label):
                continue
            found = True
            if img.marker in body or img.uri in body:
                return 'ok'
    return 'wrong_section' if found else 'no_section'


class MainImageExecutor:
    """The build is not accepted until EVERY placed photo is in a visible <img> with its alt."""

    def __init__(self, inner, images):
        self._inner = inner
        self.images = list(images) if isinstance(images, (list, tuple)) else [images]

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def execute(self, *, repository, spec):
        from .generated_images import placement
        report = self._inner.execute(repository=repository, spec=spec)
        problems = []
        for img in self.images:
            state = placement(repository, img)
            if state == 'missing':
                problems.append(AcceptanceFailure(MAIN_ACCEPTANCE_ID, (
                    f"The customer's uploaded image {img.index} ({img.place}) is not on the page. Add a visible "
                    f'<img src="{img.marker}" alt="{img.alt}"> there; do not generate, draw or replace it.')))
            elif state == 'no_alt':
                problems.append(AcceptanceFailure(MAIN_ACCEPTANCE_ID, (
                    f"The customer's uploaded image {img.index} has an empty or missing alt. Use alt=\"{img.alt}\".")))
            if state != 'missing' and img.place in _PLACE_HE:
                where = place_state(repository, img)
                he = _PLACE_HE[img.place]
                if where == 'no_section':
                    problems.append(AcceptanceFailure(MAIN_ACCEPTANCE_ID, (
                        f"The customer's uploaded image {img.index} belongs in the {img.place} section, and the page "
                        f'has no such section. Add <section> with the heading "{he}" and put '
                        f'<img src="{img.marker}" alt="{img.alt}"> inside it.')))
                elif where == 'wrong_section':
                    problems.append(AcceptanceFailure(MAIN_ACCEPTANCE_ID, (
                        f"The customer's uploaded image {img.index} is on the page but not inside the {img.place} "
                        f'section ("{he}"). Move <img src="{img.marker}" alt="{img.alt}"> into that <section>.')))
        if not problems:
            return report
        return ExecutionReport(False, tuple(report.failures) + tuple(problems), report.build_log)


def install_main_image(engine, *, prompt, pool, store, project_id, account_id):
    """Bind every photo the customer placed as is. Returns the prompt the engine builds from (with each photo's real
    size and place); unchanged when the brief places none. Any integrity problem fails the build loudly."""
    found = list(_IMAGE_BINDING.finditer(prompt or ''))
    if not found:
        return prompt
    if [int(m[1]) for m in found] != list(range(1, len(found) + 1)):
        raise ValueError('uploaded image lines are not numbered 1..n')
    if pool is None or store is None:
        raise ValueError('uploaded images require durable attachment storage')
    repo = AttachmentRepository(pool, store)
    images = []
    for m in found:
        row = repo.get(project_id=project_id, account_id=account_id, attachment_id=m[2])
        if row['sha256'] != m[3]:
            raise ValueError(f'uploaded image {m[1]}: digest changed')
        images.append(_MainImage(repo.read(row), row['mime'], m[3], m[7], row.get('width'), row.get('height'),
                                 index=int(m[1]), place=m[5]))
    from .generated_images import _Transform
    core = getattr(engine, 'core', engine)
    core.repository_transform = _Transform(getattr(core, 'repository_transform', None), images)
    core.executor = MainImageExecutor(core.executor, images)
    core.uploaded_images = images
    lines = ["Uploaded images (verified by 148AI): use each one, in its place, with its exact src and alt. Size each "
             'element to its proportions; it must stay responsive (max-width: 100%; height: auto).']
    for img in images:
        size = f'{img.width}x{img.height} px' if img.width and img.height else 'size unknown'
        lines.append(f'- image {img.index}: src="{img.marker}"; place: {img.place}; {size}; {img.mime}; alt="{img.alt}"')
    return prompt + '\n\n' + '\n'.join(lines)
