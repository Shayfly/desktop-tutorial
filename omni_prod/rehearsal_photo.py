"""The golden rehearsal's customer photo, and the account it runs as (warehouse 117, 71 and 118; owner's order 2026-11-27).

Until now the rehearsal took text only, so a build with a customer's photo could be proven in production by the
owner alone (warehouse 117). This gives the rehearsal ONE committed fixture image and the same path a customer's photo
takes: the brief's image role questions, `uploaded_assets.install_main_image` (the real `AttachmentRepository.get` and
`read`, with its checksum), the real transform, the real executor and the real preview smoke. What is NOT the customer's
path is said, never hidden: the attachment row and its bytes come from the fixture, not from the database and the
object store (a rehearsal writes nothing and has no account's attachments).

The report answers two questions in the run's own words: did the photo reach the page as a FILE (`assets/...`, never
`data:image` base64), and was the hero kept (the photo is in a visible <img> with its alt, in the hero's place).
"""
from __future__ import annotations

import hashlib
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# name -> the customer's own answers about the picture (what is in it, in the customer's words, and where it goes).
# The picture is a synthetic gradient: the alt says what the customer would say, the build never judges the content.
FIXTURES = {
    'customer_photo': {
        'path': 'tests/fixtures/rehearsal/customer_photo.jpg',
        'kind': 'place', 'alt': 'חזית העסק', 'use': 'as_is', 'place': 'hero',
    },
}

# An account that is NOT the founder's: the worker gives a founder's build extra (agentic repair, the design critic,
# the image match by default). The id is invented for the rehearsal; it must never be in OMNI_FOUNDER_ACCOUNT_IDS.
NON_FOUNDER_ID = 'usr_rehearsal_non_founder'
ACCOUNT_MODES = ('non_founder',)

PROJECT_ID = 'rehearsal'
_DATA_URI = re.compile(r'data:image/(?:png|jpe?g|webp|gif|avif)[^,]{0,40},', re.I)   # a raster picture in the text; an inline svg icon is not a photo


@dataclass(frozen=True)
class Fixture:
    name: str
    data: bytes
    mime: str
    width: int
    height: int
    sha256: str
    attachment_id: str
    kind: str
    alt: str
    use: str
    place: str

    @property
    def meta(self) -> dict:
        """What the conversation stores on the brief when a customer uploads (supervisor: the same five keys)."""
        return {'id': self.attachment_id, 'sha256': self.sha256, 'mime': self.mime, 'size_bytes': len(self.data),
                'width': self.width, 'height': self.height}

    @property
    def answers(self) -> dict:
        """The brief's image questions, by id (discovery.IMAGE_QUESTIONS), answered as the customer would."""
        return {'image_kind': self.kind, f'image_who_{self.kind}': self.alt, 'image_use': self.use,
                f'image_place_{self.kind}': self.place}


def load(name: str) -> Fixture:
    spec = FIXTURES.get(name)
    if spec is None:
        raise ValueError(f'unknown rehearsal image {name!r}; one of {sorted(FIXTURES)} or empty')
    from .attachments import validate_image
    data = (ROOT / spec['path']).read_bytes()
    mime, width, height = validate_image(data)             # the same check an upload gets: type, size, sides
    digest = hashlib.sha256(data).hexdigest()
    return Fixture(name, data, mime, width, height, digest, 'att_' + digest[:32], spec['kind'], spec['alt'],
                   spec['use'], spec['place'])


def check_account(mode: str) -> str:
    """The account id the rehearsal runs as. An unknown mode raises; so does an id the founder list contains."""
    if mode not in ACCOUNT_MODES:
        raise ValueError(f'account must be empty or one of {list(ACCOUNT_MODES)}, not {mode!r}')
    from .pricing import m5_founder_account
    if m5_founder_account(NON_FOUNDER_ID):
        raise ValueError(f'{NON_FOUNDER_ID} is in OMNI_FOUNDER_ACCOUNT_IDS: this would not be a non-founder run')
    return NON_FOUNDER_ID


# ----------------------------------------------------------------------------------------------------------------------
# The attachment store of the rehearsal. `AttachmentRepository` is the real one: its `get` runs one SELECT and `read`
# fetches the bytes and verifies their sha256. Only the two things behind it are the fixture's: the pool answers that
# one SELECT with the fixture's row, and the store returns the fixture's bytes.

class _Cursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _Connection:
    def __init__(self, fixture: Fixture, account_id: str):
        self._fx, self._account = fixture, account_id

    def execute(self, sql, params=()):
        if 'FROM conversation_attachments WHERE id = %s' not in sql:
            raise AssertionError(f'the rehearsal pool answers only AttachmentRepository.get, not: {sql[:80]}')
        att, project, account = params
        fx = self._fx
        if (att, project, account) != (fx.attachment_id, PROJECT_ID, self._account):
            return _Cursor(None)                              # the real "not found": KeyError in the repository
        return _Cursor((fx.attachment_id, PROJECT_ID, account, 'image', fx.mime, len(fx.data), fx.width, fx.height,
                        fx.sha256, f'rehearsal/{fx.name}', '{}', 'none', None))


class FixturePool:
    def __init__(self, fixture: Fixture, account_id: str):
        self._fx, self._account = fixture, account_id

    @contextmanager
    def connection(self):
        yield _Connection(self._fx, self._account)


class FixtureStore:
    def __init__(self, fixture: Fixture):
        self._fx = fixture

    def get_bytes(self, key: str) -> bytes:
        if key != f'rehearsal/{self._fx.name}':
            raise KeyError(key)
        return self._fx.data


# ----------------------------------------------------------------------------------------------------------------------
def photo_report(repository: dict, images) -> dict:
    """What the finished repository did with the customer's photo(s). Pure: the repository and the placed images.
    `as_file`: every photo is a verified file at its own path under assets/ AND no page, style or script carries
    `data:image` (base64). `hero_kept`: the hero photo is in a visible <img> with a non-empty alt (the same
    `generated_images.placement` the build's own gate uses) and its marker is gone. `ok` needs both."""
    from .generated_images import placement
    from .repository_assets import decode, is_envelope, names_file
    text_sources = {p: s for p, s in repository.items() if isinstance(s, str) and not is_envelope(s)}
    inline = sorted(p for p, s in text_sources.items() if _DATA_URI.search(s))
    rows = []
    for img in images:
        path = img.uri
        content = repository.get(path)
        carried, reason = False, None
        if content is None:
            reason = f'no file at {path}'
        elif not is_envelope(content):
            reason = f'{path} is text, not the image file'
        else:
            try:
                carried = hashlib.sha256(decode(path, content)).hexdigest() == hashlib.sha256(img.data).hexdigest()
                reason = None if carried else f'{path} holds other bytes than the photo the page was fitted to'
            except ValueError as exc:
                reason = f'{path}: {exc}'[:200]
        referenced = any(
            names_file(m.group(2), path)
            for s in text_sources.values()
            for m in re.finditer(r'\bsrc\s*=\s*\{?\s*(["\'`])(.*?)\1', s, re.I | re.S))
        rows.append({
            'index': img.index, 'place': img.place, 'path': path, 'mime': img.mime, 'bytes': len(img.data),
            'file_carried': carried, 'referenced_as_file': referenced,
            'marker_left': any(img.marker in s for s in text_sources.values()),
            'placement': placement(repository, img), 'reason': reason})
    as_file = bool(rows) and not inline and all(r['file_carried'] and r['referenced_as_file'] and not r['marker_left']
                                                for r in rows)
    hero = [r for r in rows if r['place'] == 'hero']
    hero_kept = bool(hero) and all(r['placement'] == 'ok' for r in hero)
    return {'images': rows, 'inline_data_uri_in': inline, 'as_file': as_file, 'hero_kept': hero_kept,
            'ok': as_file and (hero_kept or not hero)}


def photo_lines(photo: dict) -> list[str]:
    """The two answers, as GitHub annotations: an error when either is no."""
    def one(r):
        return (f"image {r['index']} ({r['place']}) path={r['path']} {r['mime']} {r['bytes']} bytes "
                f"file_carried={r['file_carried']} referenced_as_file={r['referenced_as_file']} "
                f"marker_left={r['marker_left']} placement={r['placement']}" + (f" reason={r['reason']}" if r['reason'] else ''))
    body = (f"photo_as_file={photo['as_file']} (not base64: inline data:image in {photo['inline_data_uri_in'] or 'none'}) "
            f"hero_kept={photo['hero_kept']}\n" + '\n'.join(one(r) for r in photo['images']))
    body = body.replace('%', '%25').replace('\r', '').replace('\n', '%0A')
    kind = 'notice' if photo['ok'] else 'error'
    return [f'::{kind} title=customer photo::{body[:3400]}']
