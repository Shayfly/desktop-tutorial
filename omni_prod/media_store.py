"""S13.1/S13.2 (the owner, 2026-11-27, answer 6): where a large generated file (an image set, a song, a clip, a model) lives.

One class, TenantMediaStore, on top of the object store that already exists (omni_prod/storage.S3ArtifactStore on
Cloudflare R2; the key function is omni_prod/artifact_keys.build_media_key). Nothing here calls a provider.

  put      the bytes are sniffed and must be the type they claim, bounded per kind, stored under
           tenants/<account>/projects/<project>/media/<sha256>.<ext>, and the sha256 is the name.
  read     a reference is honoured only when its key is under THIS account's prefix and agrees with its own sha256 and
           type; the bytes are streamed with a size bound and checked against the sha256. A key of another account, a key
           that does not exist and a key that is malformed all raise the same MediaNotFound: no existence oracle.
  deliver  read + the rights gate (omni_prod/asset_rights.py): a file with no rights record, or one that may not be sold,
           is not delivered. This is the one door a customer's download goes through.
  link     a signed link of our own bucket, at most MAX_LINK_SECONDS (five minutes), behind the same gate.

A reference (MediaRef) is the key, the sha256, the size and the type. It is what travels in a build's record instead of
the bytes; the existing base64 envelope of repository_assets stays for images up to 3 MB and is not touched.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .artifact_keys import MEDIA_EXTENSIONS, build_media_key, media_key_prefix

MAX_LINK_SECONDS = 300
CHUNK = 1024 * 1024
MiB = 1024 * 1024
# mime -> (extension, kind, byte limit). Bounded per kind: an unlimited upload is an unbounded wait and an unbounded bill.
TYPES: dict[str, tuple[str, str, int]] = {
    'image/png': ('png', 'image', 20 * MiB), 'image/jpeg': ('jpg', 'image', 20 * MiB), 'image/webp': ('webp', 'image', 20 * MiB),
    'audio/mpeg': ('mp3', 'audio', 100 * MiB), 'audio/wav': ('wav', 'audio', 100 * MiB),
    'video/mp4': ('mp4', 'video', 512 * MiB), 'video/webm': ('webm', 'video', 512 * MiB),
    'model/gltf-binary': ('glb', 'model', 100 * MiB),
}
EXT_MIME = {ext: mime for mime, (ext, _k, _l) in TYPES.items()}
assert set(EXT_MIME) == set(MEDIA_EXTENSIONS)
_KEY = re.compile(r'tenants/([A-Za-z0-9._-]{1,120})/projects/([A-Za-z0-9._-]{1,120})/media/([0-9a-f]{64})\.([a-z0-9]{2,4})')


class MediaError(ValueError):
    """The file cannot be stored: wrong type, wrong size, empty."""


class MediaNotFound(LookupError):
    """The one answer for a reference that is not this account's, does not exist or does not agree with itself."""


@dataclass(frozen=True)
class MediaRef:
    key: str
    sha256: str
    size: int
    mime: str

    def parts(self) -> tuple[str, str]:
        """(account, project) the key names; MediaNotFound when the key is not a media key or disagrees with the ref."""
        m = _KEY.fullmatch(self.key or '')
        if not m or m.group(3) != self.sha256 or EXT_MIME.get(m.group(4)) != self.mime:
            raise MediaNotFound('unknown media')
        return m.group(1), m.group(2)


def sniff(data: bytes) -> str:
    """The mime type of a media file from its magic bytes; MediaError when it is none of TYPES."""
    from .providers.image_provider import sniff_image
    if data[:4] == b'glTF':
        return 'model/gltf-binary'
    if data[:4] == b'\x1aE\xdf\xa3':
        return 'video/webm'
    if len(data) >= 12 and data[4:8] == b'ftyp':
        return 'video/mp4'
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WAVE':
        return 'audio/wav'
    if data[:3] == b'ID3' or (len(data) > 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0 and data[:3] != b'\xff\xd8\xff'):
        return 'audio/mpeg'
    try:
        return sniff_image(data[:65536] if data[:3] != b'\xff\xd8\xff' else data)[0]
    except ValueError:
        raise MediaError('the file is not a PNG, JPEG, WebP, MP3, WAV, MP4, WebM or GLB file') from None


def _absent(exc: Exception) -> bool:
    code = ((getattr(exc, 'response', None) or {}).get('Error') or {}).get('Code')
    return isinstance(exc, (KeyError, FileNotFoundError)) or code in {'NoSuchKey', '404', 'NotFound'}


class TenantMediaStore:
    def __init__(self, store, account_id: str, *, rights=None) -> None:
        self._store, self.account_id, self._rights = store, account_id, rights
        self._prefix = media_key_prefix(account_id)             # raises on an unsafe account id

    def put(self, project_id: str, data: bytes, mime: str) -> MediaRef:
        if mime not in TYPES:
            raise MediaError(f'a file of type {mime!r} is not stored (only {sorted(TYPES)})')
        payload = bytes(data)
        if not payload:
            raise MediaError('a file with no bytes is not stored')
        limit = TYPES[mime][2]
        if len(payload) > limit:
            raise MediaError(f'a {TYPES[mime][1]} of {len(payload):,} bytes is over its limit of {limit:,}')
        if sniff(payload) != mime:
            raise MediaError(f'the bytes are not {mime}')
        digest = hashlib.sha256(payload).hexdigest()
        key = build_media_key(account_id=self.account_id, project_id=project_id, sha256=digest, ext=TYPES[mime][0])
        stored = self._store.put_bytes(key, payload)
        if stored is not None and (stored.sha256 != digest or stored.size != len(payload) or stored.key != key):
            raise MediaError('the object store did not keep what was sent')
        return MediaRef(key=key, sha256=digest, size=len(payload), mime=mime)

    def _own(self, ref: MediaRef) -> tuple[str, str]:
        account, project = ref.parts()
        if account != self.account_id or not ref.key.startswith(self._prefix):
            raise MediaNotFound('unknown media')
        if not isinstance(ref.size, int) or not 0 < ref.size <= TYPES[ref.mime][2]:
            raise MediaNotFound('unknown media')
        return account, project

    def read(self, ref: MediaRef) -> bytes:
        self._own(ref)
        digest, chunks, size = hashlib.sha256(), [], 0
        try:
            for chunk in self._store.iter_bytes(ref.key, chunk_size=CHUNK, verify=True, max_size_bytes=ref.size):
                digest.update(chunk)
                chunks.append(chunk)
                size += len(chunk)
        except Exception as exc:
            if _absent(exc):
                raise MediaNotFound('unknown media') from None
            raise
        if size != ref.size or digest.hexdigest() != ref.sha256:
            raise MediaNotFound('unknown media')
        return b''.join(chunks)

    def deliver(self, ref: MediaRef) -> bytes:
        """The bytes for the customer, only with a rights record that allows it (omni_prod/asset_rights.py)."""
        account, project = self._own(ref)
        if self._rights is None:
            raise RuntimeError('a media store without a rights gate cannot deliver')
        self._rights.require(account_id=account, project_id=project, sha256=ref.sha256)
        return self.read(ref)

    def link(self, ref: MediaRef, *, expires_seconds: int = MAX_LINK_SECONDS) -> str:
        """A signed link of our own bucket, for this account's own file and for at most five minutes."""
        if not 1 <= int(expires_seconds) <= MAX_LINK_SECONDS:
            raise ValueError(f'a media link lives at most {MAX_LINK_SECONDS} seconds')
        account, project = self._own(ref)
        if self._rights is None:
            raise RuntimeError('a media store without a rights gate cannot link')
        self._rights.require(account_id=account, project_id=project, sha256=ref.sha256)
        return self._store.presign_get(ref.key, expires_seconds=int(expires_seconds))
