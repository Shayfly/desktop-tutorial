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
