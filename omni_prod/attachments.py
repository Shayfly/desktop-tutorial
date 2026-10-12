"""Conversation attachments: images and annotated screenshots (migration 038).

Founder directive 2026-10-11 ("Conversation UX + Visual Editing", task 2).

- Types: PNG, JPEG, WebP only. The type is decided from the file's own bytes
  (magic numbers), never from the declared MIME or file name; SVG/GIF/HTML are
  refused (SVG can carry script). Dimensions come from the image header.
- Size: at most 3 MiB per image after decoding (the workspace downsizes larger
  photos in the browser first; a Vercel function body is capped at 4.5 MB),
  at most 8000 px per side, at most 40 live attachments per project.
- Isolation: every read and delete filters on BOTH the project and the owning
  account; the API resolves project ownership first (403 otherwise). Objects
  live under attachments/<account>/<project>/<id>.<ext> in the project
  artifact bucket and are deleted with the attachment.
- Annotation: rectangles (image pixels) and the number of free-hand strokes the
  person drew; validated against the image size.
- Vision: nothing here calls a model. analysis_state stays NOT_ANALYZED until a
  vision-capable route is authorized with a budget (not enabled), and the
  workspace says so instead of pretending the image was understood.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import struct
import uuid

MAX_BYTES = 3 * 1024 * 1024
MAX_SIDE = 8000
MAX_LIVE_PER_PROJECT = 40
MAX_REGIONS = 20
KINDS = ('image', 'screenshot')
EXT = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp'}
VISION_NOTE = {
    'state': 'NOT_ANALYZED',
    'reason': 'image analysis needs a vision-capable model with an approved budget; it is not enabled',
}


class AttachmentError(ValueError):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.status = code, status


def sniff(data: bytes) -> str | None:
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if data[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return None


def dimensions(data: bytes, mime: str) -> tuple[int, int]:
    """(width, height) from the header; raises AttachmentError when unreadable."""
    try:
        if mime == 'image/png':
            if data[12:16] != b'IHDR':
                raise ValueError('no IHDR')
            w, h = struct.unpack('>II', data[16:24])
            return w, h
        if mime == 'image/jpeg':
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                seg = struct.unpack('>H', data[i + 2:i + 4])[0]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack('>HH', data[i + 5:i + 9])
                    return w, h
                i += 2 + seg
            raise ValueError('no SOF marker')
        if mime == 'image/webp':
            chunk = data[12:16]
            if chunk == b'VP8X':
                w = 1 + int.from_bytes(data[24:27], 'little')
                h = 1 + int.from_bytes(data[27:30], 'little')
                return w, h
            if chunk == b'VP8L':
                b = data[21:25]
                w = 1 + (((b[1] & 0x3F) << 8) | b[0])
                h = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
                return w, h
            if chunk == b'VP8 ':
                w, h = struct.unpack('<HH', data[26:30])
                return w & 0x3FFF, h & 0x3FFF
            raise ValueError('unknown WebP chunk')
    except (struct.error, IndexError, ValueError) as exc:
        raise AttachmentError('unreadable_image', f'the image header could not be read ({exc})') from exc
    raise AttachmentError('unsupported_type', 'only PNG, JPEG and WebP images are accepted')


def validate_image(data: bytes) -> tuple[str, int, int]:
    if not data:
        raise AttachmentError('empty', 'the file is empty')
    if len(data) > MAX_BYTES:
        raise AttachmentError('too_large', f'images are limited to {MAX_BYTES // (1024 * 1024)} MB', 413)
    mime = sniff(data)
    if mime is None:
        raise AttachmentError('unsupported_type', 'only PNG, JPEG and WebP images are accepted', 415)
    w, h = dimensions(data, mime)
    if not (0 < w <= MAX_SIDE and 0 < h <= MAX_SIDE):
        raise AttachmentError('bad_dimensions', f'image sides must be 1..{MAX_SIDE} px (got {w}x{h})')
    return mime, w, h


def decode_base64(text: str) -> bytes:
    if not isinstance(text, str) or len(text) > (MAX_BYTES * 4) // 3 + 8:
        raise AttachmentError('too_large', 'images are limited to 3 MB', 413)
    if text.startswith('data:'):
        text = text.split(',', 1)[-1]
    try:
        return base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AttachmentError('bad_encoding', 'the image is not valid base64') from exc


def validate_annotation(raw, width: int, height: int) -> dict:
    if raw in (None, {}):
        return {}
    if not isinstance(raw, dict):
        raise AttachmentError('bad_annotation', 'annotation must be an object')
    out: dict = {}
    regions = raw.get('regions') or []
    if not isinstance(regions, list) or len(regions) > MAX_REGIONS:
        raise AttachmentError('bad_annotation', f'at most {MAX_REGIONS} regions')
    clean = []
    for r in regions:
        try:
            x, y, w, h = (int(round(float(r[k]))) for k in ('x', 'y', 'w', 'h'))
        except (KeyError, TypeError, ValueError) as exc:
            raise AttachmentError('bad_annotation', 'a region needs numeric x, y, w, h') from exc
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > width or y + h > height:
            raise AttachmentError('bad_annotation', 'a region lies outside the image')
        clean.append({'x': x, 'y': y, 'w': w, 'h': h})
    if clean:
        out['regions'] = clean
    strokes = raw.get('strokes', 0)
    if not isinstance(strokes, int) or not 0 <= strokes <= 200:
        raise AttachmentError('bad_annotation', 'strokes must be 0..200')
    if strokes:
        out['strokes'] = strokes
    note = raw.get('note')
    if note is not None:
        if not isinstance(note, str) or len(note) > 500:
            raise AttachmentError('bad_annotation', 'note must be text up to 500 characters')
        out['note'] = note.strip()
    return out


def _delete_object(store, key: str) -> None:
    client = getattr(store, 'client', None)
    if client is not None and hasattr(client, 'delete_object'):
        client.delete_object(Bucket=store.bucket, Key=key)
    elif hasattr(store, 'delete'):
        store.delete(key)
    else:  # never pretend the bytes are gone
        raise AttachmentError('storage_cannot_delete', 'the storage backend cannot delete objects', 503)


_COLS = ('id, project_id, account_id, kind, mime, size_bytes, width, height, sha256, storage_key, annotation, '
         'analysis_state, created_at')


def public(row: dict) -> dict:
    return {'id': row['id'], 'kind': row['kind'], 'mime': row['mime'], 'size_bytes': row['size_bytes'],
            'width': row['width'], 'height': row['height'], 'annotation': row['annotation'] or {},
            'analysis': {**VISION_NOTE, 'state': row['analysis_state']},
            'created_at': str(row['created_at']), 'sha256': row['sha256']}


class AttachmentRepository:
    def __init__(self, pool, store):
        self.pool, self.store = pool, store

    def schema_ready(self) -> bool:
        with self.pool.connection() as conn:
            return conn.execute("SELECT to_regclass('public.conversation_attachments')").fetchone()[0] is not None

    def _row(self, r) -> dict:
        d = dict(zip([c.strip() for c in _COLS.split(',')], r))
        if isinstance(d.get('annotation'), str):
            d['annotation'] = json.loads(d['annotation'])
        return d

    def create(self, *, project_id: str, account_id: str, kind: str, data: bytes, annotation=None) -> dict:
        if kind not in KINDS:
            raise AttachmentError('bad_kind', f'kind must be one of {KINDS}')
        mime, w, h = validate_image(data)
        note = validate_annotation(annotation, w, h)
        with self.pool.connection() as conn:
            live = conn.execute('SELECT count(*) FROM conversation_attachments WHERE project_id = %s AND account_id = %s '
                                'AND deleted_at IS NULL', (project_id, account_id)).fetchone()[0]
        if live >= MAX_LIVE_PER_PROJECT:
            raise AttachmentError('too_many', f'a project keeps at most {MAX_LIVE_PER_PROJECT} images; delete some first', 409)
        att_id = f'att_{uuid.uuid4().hex}'
        key = f'attachments/{account_id}/{project_id}/{att_id}.{EXT[mime]}'
        stored = self.store.put_bytes(key, data)            # object first: a row never points at nothing
        digest = hashlib.sha256(data).hexdigest()
        if getattr(stored, 'sha256', digest) != digest:
            raise AttachmentError('integrity', 'storage digest mismatch', 502)
        try:
            with self.pool.connection() as conn:
                with conn.transaction():
                    r = conn.execute(
                        f'INSERT INTO conversation_attachments (id, project_id, account_id, kind, mime, size_bytes, width, '
                        f'height, sha256, storage_key, annotation) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb) '
                        f'RETURNING {_COLS}',
                        (att_id, project_id, account_id, kind, mime, len(data), w, h, digest, key, json.dumps(note))).fetchone()
        except Exception:
            try:
                _delete_object(self.store, key)
            except Exception:
                pass
            raise
        return self._row(r)

    def get(self, *, project_id: str, account_id: str, attachment_id: str) -> dict:
        with self.pool.connection() as conn:
            r = conn.execute(f'SELECT {_COLS} FROM conversation_attachments WHERE id = %s AND project_id = %s '
                             'AND account_id = %s AND deleted_at IS NULL', (attachment_id, project_id, account_id)).fetchone()
        if r is None:
            raise KeyError(attachment_id)
        return self._row(r)

    def read(self, row: dict) -> bytes:
        data = self.store.get_bytes(row['storage_key'])
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise AttachmentError('integrity', 'stored image does not match its checksum', 502)
        return data

    def list(self, *, project_id: str, account_id: str) -> list[dict]:
        with self.pool.connection() as conn:
            rows = conn.execute(f'SELECT {_COLS} FROM conversation_attachments WHERE project_id = %s AND account_id = %s '
                                'AND deleted_at IS NULL ORDER BY created_at', (project_id, account_id)).fetchall()
        return [self._row(r) for r in rows]

    def many(self, *, project_id: str, account_id: str, ids) -> list[dict]:
        ids = list(dict.fromkeys(ids or []))
        if len(ids) > 6:
            raise AttachmentError('too_many', 'at most 6 images per message')
        out = []
        for i in ids:
            try:
                out.append(self.get(project_id=project_id, account_id=account_id, attachment_id=str(i)))
            except KeyError:
                raise AttachmentError('unknown_attachment', f'attachment {i} not found', 404) from None
        return out

    def delete(self, *, project_id: str, account_id: str, attachment_id: str) -> dict:
        row = self.get(project_id=project_id, account_id=account_id, attachment_id=attachment_id)
        _delete_object(self.store, row['storage_key'])
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute('UPDATE conversation_attachments SET deleted_at = now() WHERE id = %s AND account_id = %s',
                             (attachment_id, account_id))
        return {'id': attachment_id, 'deleted': True}
