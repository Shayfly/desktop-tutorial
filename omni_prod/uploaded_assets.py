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
_MAIN_BINDING = re.compile(r'^Uploaded main image attachment: (att_[a-f0-9]{32}); sha256=([a-f0-9]{64})\.', re.M)


class _MainImage:
    """Duck-types generated_images.GeneratedImage for its transform and placement check."""
    index = 1
    purpose = 'main image (the customer\'s own photo, as is)'

    def __init__(self, data: bytes, mime: str, digest: str, alt: str, width=None, height=None):
        if mime not in EXT or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('uploaded main image integrity mismatch')
        from .discovery import MAIN_IMAGE_MARKER
        self.data, self.mime, self.sha256, self.alt = data, mime, digest, alt
        self.width, self.height, self.marker = width, height, MAIN_IMAGE_MARKER
        self.uri = f'data:{mime};base64,' + base64.b64encode(data).decode('ascii')


class MainImageExecutor:
    def __init__(self, inner, image: _MainImage):
        self._inner, self.image = inner, image

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def execute(self, *, repository, spec):
        from .generated_images import placement
        report = self._inner.execute(repository=repository, spec=spec)
        state = placement(repository, self.image)
        if state == 'ok':
            return report
        img = self.image
        why = ('is not on the page. Add a visible <img src="%s" alt="%s">; do not generate, draw or replace it.'
               if state == 'missing' else 'has an empty or missing alt. Use alt="%s".')
        msg = "The customer's uploaded main image " + (why % (img.marker, img.alt) if state == 'missing' else why % img.alt)
        return ExecutionReport(False, tuple(report.failures) + (AcceptanceFailure(MAIN_ACCEPTANCE_ID, msg),),
                               report.build_log)


def main_image_alt(prompt: str) -> str:
    from .generated_images import describe
    return describe(prompt, 'hero') or 'התמונה הראשית של העסק'


def install_main_image(engine, *, prompt, pool, store, project_id, account_id):
    """Bind the photo the customer chose to show as is. Returns the prompt the engine builds from (with the photo's
    real size); unchanged when the brief has no such photo. Any integrity problem fails the build loudly."""
    match = _MAIN_BINDING.search(prompt or '')
    if not match:
        return prompt
    if pool is None or store is None:
        raise ValueError('the uploaded main image requires durable attachment storage')
    repo = AttachmentRepository(pool, store)
    row = repo.get(project_id=project_id, account_id=account_id, attachment_id=match[1])
    if row['sha256'] != match[2]:
        raise ValueError('uploaded main image digest changed')
    image = _MainImage(repo.read(row), row['mime'], match[2], main_image_alt(prompt), row.get('width'), row.get('height'))
    from .generated_images import _Transform
    core = getattr(engine, 'core', engine)
    core.repository_transform = _Transform(getattr(core, 'repository_transform', None), [image])
    core.executor = MainImageExecutor(core.executor, image)
    core.uploaded_main_image = image
    size = f'{image.width}x{image.height} px' if image.width and image.height else 'size unknown'
    return (f'{prompt}\n\nUploaded main image (verified by 148AI): src="{image.marker}"; {size}; {image.mime}; '
            f'alt="{image.alt}". Size the element to these proportions; it must stay responsive '
            '(max-width: 100%; height: auto).')
