"""An image is a file the page references, not base64 inside the page (warehouse 118 + 114; the owner, 2026-11-20).

Production, 2026-11-14 (the butcher, bld_83529c13): the hero image was embedded in the page as 1,735,408 base64
characters. The page was heavy, nothing could cache the picture, and the business facts fell past the 45,000
characters of GET / that the preview smoke keeps for the truth gate.

The design (option b of warehouse 118): the pipeline stays text-only. A repository is still {path: str} everywhere --
the sandbox request (validate_snapshot, the HMAC body), the saved version (the zip in the artifact store), the
fingerprint and the repair loop are unchanged. An image the platform carries is ONE repository entry at its real path,
e.g. `assets/148ai-image-1.webp`, whose text is an envelope:

    148ai-binary:v1;mime=image/webp;sha256=<64 hex>;base64,<the bytes>

The page references that path (`<img src="assets/148ai-image-1.webp">`). Every point where files leave the pipeline
-- the sandbox runner writing the snapshot to disk, the local sandbox, the preview container's work directory, the
export zip and the version download -- writes the DECODED bytes, so the generated server serves a real image file
and a downloaded project holds a real .webp. Why not real bytes in the repository (option a): `dict[str, str]` is the
contract of every one of those points and of everything between them (the pydantic RunRequest is strict str, the
snapshot policy rejects NUL, the version zip decodes UTF-8, the fingerprint json-dumps the values); turning values
into bytes would touch all of them at once, and a missed one fails at run time. The envelope changes only the points
that write files, and each of them goes through `file_bytes` here.

Loud, never silent: an envelope whose bytes do not match its sha256, whose bytes are not the image its mime says, or
that sits at a path whose extension says another type, raises `AssetCarryError` at the point that writes it. An
envelope is decoded only under `assets/` with an image extension: it cannot smuggle an arbitrary binary file.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import re
import zipfile
from pathlib import Path, PurePosixPath

PREFIX = '148ai-binary:v1;'
ASSET_DIR = 'assets'
MIME_EXT = {'image/webp': '.webp', 'image/jpeg': '.jpg', 'image/png': '.png'}
EXT_MIME = {'.webp': 'image/webp', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}
_HEAD = re.compile(r'148ai-binary:v1;mime=(image/(?:webp|jpeg|png));sha256=([0-9a-f]{64});base64,')
# One image. The web rendition keeps a photo under 360,000 bytes; a logo is carried as uploaded, so the bound is the
# upload limit itself (review 2026-11-21: a 2.4 MB logo the upload accepted failed the build under a 2,000,000 bound).
from .attachments import MAX_BYTES as MAX_ASSET_BYTES   # noqa: E402


class AssetCarryError(ValueError):
    """An image the platform carries could not be carried as a file. The build or the export stops; never re-inlined."""


def is_envelope(content) -> bool:
    return isinstance(content, str) and content.startswith(PREFIX)


def names_file(src: str, path: str) -> bool:
    """True when an <img src> names the carried file at `path` ('assets/x.webp'), written as a page may write it:
    'assets/x.webp', './assets/x.webp' or '/assets/x.webp', with or without a ?query or #fragment. The browser, the
    preview smoke and the static check all read these as the same file. Never a parent path, a scheme, a host ('//'),
    another directory or a bare file name. One rule for every carried image (generated, uploaded, the logo): the
    owner's build bld_ab78f528 (2026-11-22) failed 'not on the page' while its page showed the image as '/assets/...'."""
    p = re.split(r'[?#]', src or '', maxsplit=1)[0]
    if p.startswith('./'):
        p = p[2:]
    elif p.startswith('/') and not p.startswith('//'):
        p = p[1:]
    return p == path


def envelope(data: bytes, mime: str) -> str:
    """The repository text of one image file."""
    if mime not in MIME_EXT:
        raise AssetCarryError(f'an image of type {mime!r} cannot be carried as a file (only {sorted(MIME_EXT)})')
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise AssetCarryError('an image with no bytes cannot be carried as a file')
    if len(data) > MAX_ASSET_BYTES:
        raise AssetCarryError(f'an image of {len(data):,} bytes is over {MAX_ASSET_BYTES:,}; it cannot be carried')
    _check_kind(bytes(data), mime, 'the image')
    return (f'{PREFIX}mime={mime};sha256={hashlib.sha256(data).hexdigest()};base64,'
            + base64.b64encode(bytes(data)).decode('ascii'))


def asset_path(kind: str, index, mime: str) -> str:
    """`assets/148ai-<kind>-<index><ext>`: one fixed name per carried image, so the transform can always put it back."""
    if not re.fullmatch(r'[a-z]{2,12}', kind) or not re.fullmatch(r'[0-9]{0,3}', str(index)):
        raise AssetCarryError(f'invalid asset name parts {kind!r} {index!r}')
    if mime not in MIME_EXT:
        raise AssetCarryError(f'an image of type {mime!r} cannot be carried as a file (only {sorted(MIME_EXT)})')
    return f'{ASSET_DIR}/148ai-{kind}{"-" + str(index) if str(index) else ""}{MIME_EXT[mime]}'


def _check_kind(data: bytes, mime: str, what: str) -> None:
    from .providers.image_provider import sniff_image
    try:
        found = sniff_image(data[:65536] if mime != 'image/jpeg' else data)[0]
    except ValueError as exc:
        raise AssetCarryError(f'{what} is not a PNG, JPEG or WebP image') from exc
    if found != mime:
        raise AssetCarryError(f'{what} says {mime} but its bytes are {found}')


def decode(path: str, content: str) -> bytes:
    """The bytes of one envelope, checked: its place, its type, its digest. Raises AssetCarryError."""
    m = _HEAD.match(content or '')
    if not m:
        raise AssetCarryError(f'{path}: a 148ai-binary entry with an unreadable header')
    mime, digest = m.group(1), m.group(2)
    p = PurePosixPath(path)
    if p.parts[:1] != (ASSET_DIR,) or EXT_MIME.get(p.suffix.lower()) != mime:
        raise AssetCarryError(f'{path}: a {mime} image may only be carried under {ASSET_DIR}/ with its own extension')
    try:
        data = base64.b64decode(content[m.end():], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AssetCarryError(f'{path}: the image bytes are not valid base64') from exc
    if hashlib.sha256(data).hexdigest() != digest:
        raise AssetCarryError(f'{path}: the image bytes do not match their sha256')
    _check_kind(data, mime, path)
    return data


def file_bytes(path: str, content: str) -> bytes:
    """What is written to disk (or into a zip) for one repository entry: an envelope's image bytes, else the text."""
    if is_envelope(content):
        return decode(path, content)
    return content.encode('utf-8')


def materialize(root: Path, repository: dict[str, str]) -> None:
    """Write a repository to `root`: the one function every sandbox and preview work directory is written with."""
    from .repository_patch import normalize_repo_path
    for rel, content in repository.items():
        safe = normalize_repo_path(rel)
        target = Path(root) / safe
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(file_bytes(safe, content))


def zip_bytes(repository: dict[str, str], *, ordered: bool = True) -> bytes:
    """An export zip of a repository, images as real files."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path, content in (sorted(repository.items()) if ordered else repository.items()):
            zf.writestr(path, file_bytes(path, content))
    return out.getvalue()


def without_assets(repository: dict) -> dict:
    """The repository as a model may read it: no image bytes at all."""
    return {p: c for p, c in repository.items() if not is_envelope(c)}


def strip_fragments(text: str, encoded: str, marker: str) -> str:
    """Sandbox evidence can be cut in the middle of the bytes: a long base64 run that is part of `encoded` becomes
    `marker`; any other text, code included, is left as it is."""
    return re.sub(r'[A-Za-z0-9+/]{32,}={0,2}', lambda m: marker if m.group(0) in encoded else m.group(0), text)


class CarriedImage:
    """One image the platform puts in the page as a file: its marker (what the model writes), its path (what the page
    references after the transform) and its envelope (the repository entry at that path)."""

    def __init__(self, marker: str, path: str, data: bytes, mime: str):
        self.marker, self.path, self.mime = marker, path, mime
        self.envelope = envelope(data, mime)
        self.encoded = self.envelope.split(',', 1)[1]

    def rebind(self, data: bytes) -> None:
        """New bytes for the same file (the page fit, web_rendition.fit_page): the type, and so the path, stay. The
        transforms installed before hold this object, so they carry the new bytes from the next round on."""
        self.envelope = envelope(data, self.mime)
        self.encoded = self.envelope.split(',', 1)[1]

    def _reference(self, holder: str) -> str:
        """What a file at `holder` writes to reach the image. Only a STYLESHEET resolves its url(...) against its own
        URL: one in a sub-directory (static/style.css) gets one `../` per directory, else the plain relative path is
        /static/assets/<name> there, a 404 (review 2026-11-21); a URL cannot climb above the root, so the extra `../`
        is harmless when the stylesheet is served elsewhere. Every other file (a page, a template, JSX, a script, the
        server's HTML string) is read against the DOCUMENT's URL, so it keeps `assets/<name>` as before, wherever the
        file itself lives (src/App.jsx: the image checks compare the src with the path). The preview smoke fetches
        every reference as a browser resolves it, so a page whose URL breaks the relative path fails loudly."""
        if PurePosixPath(holder).suffix.lower() != '.css':
            return self.path
        return '../' * (len(PurePosixPath(holder).parts) - 1) + self.path

    def place(self, repo: dict) -> dict:
        """Marker -> path in every text file, and the file itself at its path (always rewritten: a repair cannot drop
        or change it)."""
        rx = re.compile(re.escape(self.marker) + r'(?![0-9])')
        out = {}
        for path, text in repo.items():
            out[path] = rx.sub(self._reference(path), text) if isinstance(text, str) and not is_envelope(text) else text
        out[self.path] = self.envelope
        return out

    def unplace(self, repo: dict) -> dict:
        """The reverse, for what a model reads: path -> marker, and no image file."""
        out = {}
        for path, text in repo.items():
            if path == self.path:
                continue
            if isinstance(text, str) and not is_envelope(text):
                text = text.replace(self._reference(path), self.marker).replace(self.path, self.marker)
            out[path] = text
        return out

    def redact_text(self, text: str) -> str:
        text = text.replace(self.envelope, self.marker)
        return strip_fragments(text, self.encoded, self.marker)
