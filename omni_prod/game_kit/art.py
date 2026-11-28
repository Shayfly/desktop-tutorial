"""The art layer of a 2D game (the owner, 2026-11-27, answer 11; warehouse 134 widened to generated art; plan S12.3-S12.4).

A game is the definition the model writes (schema 148ai.game/1) plus, optionally, images for five roles
(`schema.ART_ROLES`: background, player, enemy, item, ground). `attach` returns the definition as 148ai.game/2 with an
`art` block, and a report that says, per role, where each image came from and why any was dropped.

Two sources, one layer:
  procedural  deterministic pixel art drawn from the definition's seed and palette, in this file, with no network and no
              model. The same definition gives the same bytes. It is the FALLBACK and, with no provider configured, the art.
  provider    the existing image provider (`providers.image_provider`, the same journal, idempotency key, kill switch and
              safe fetch every generated image of the platform already goes through), one image per role.

Art never fails a build (plan S12.4). An image that does not pass its checks, or a provider that errors, is DROPPED, the
reason is in the report (and so in the build's evidence), and that role is drawn procedurally; the game always plays.
The checks (`check_image`): the bytes are the type they claim; the size is within the schema's bound; the dimensions are
within 16 to 2048 px; a sprite (not the background) must be a PNG with an alpha channel, otherwise it would draw as an
opaque box. What is not checked, said: whether the picture shows what was asked (no vision call here), and a provider
image over the size bound is dropped, not shrunk (no image library in the worker).

Spend. The provider path is OFF unless a caller passes a source: the worker builds one only with OMNI_GAME_ART=provider
(omni_prod/game_kit/builder.py), and the provider itself refuses when the external-spend kill switch is closed. Its cost is
metered by the provider's own journal, not (yet) in the build's economics quote: see STATUS.md.
"""
from __future__ import annotations

import hashlib
import math
import random
import struct
import time
import zlib
from dataclasses import dataclass, field

from .schema import ART_MAX_BYTES, ART_ROLES, ART_TOTAL_MAX_BYTES, SCHEMA, SCHEMA_V2, validate

MIN_SIDE, MAX_SIDE = 16, 2048
SPRITE_ROLES = ('player', 'enemy', 'item', 'ground')


# ---- PNG, written here: no image library -------------------------------------------------------------------------
def _chunk(tag: bytes, body: bytes) -> bytes:
    return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body) & 0xFFFFFFFF)


def encode_png(width: int, height: int, rows: list[bytes], *, alpha: bool) -> bytes:
    """rows: `height` byte strings of width*4 (RGBA) or width*3 (RGB) bytes."""
    channels = 4 if alpha else 3
    if len(rows) != height or any(len(r) != width * channels for r in rows):
        raise ValueError('png rows do not match the size')
    raw = b''.join(b'\x00' + r for r in rows)
    return (b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6 if alpha else 2, 0, 0, 0))
            + _chunk(b'IDAT', zlib.compress(raw, 9)) + _chunk(b'IEND', b''))


def png_info(data: bytes) -> tuple[int, int, bool] | None:
    """(width, height, has_alpha) of a PNG, or None when the bytes are not one."""
    if len(data) < 33 or not data.startswith(b'\x89PNG\r\n\x1a\n') or data[12:16] != b'IHDR':
        return None
    width, height = struct.unpack('>II', data[16:24])
    return width, height, data[25] in (4, 6)


# ---- the deterministic fallback ----------------------------------------------------------------------------------
def _rgb(hex_color: str) -> tuple[int, int, int]:
    n = int(hex_color[1:], 16)
    return n >> 16, (n >> 8) & 255, n & 255


def _mix(c, f: float) -> tuple[int, int, int]:
    """f > 0 toward white, f < 0 toward black."""
    return tuple(int(round(v + (255 - v) * f)) if f > 0 else int(round(v * (1 + f))) for v in c)


def _rng(seed: int, role: str) -> random.Random:
    return random.Random(int(hashlib.sha256(f'{seed}:{role}'.encode()).hexdigest()[:16], 16))


def _grid_png(grid: list[list], scale: int, *, alpha: bool = True) -> bytes:
    height, width = len(grid) * scale, len(grid[0]) * scale
    rows = []
    for gr in grid:
        row = b''.join((bytes(px) if alpha else bytes(px[:3])) * scale for px in gr)
        rows += [row] * scale
    return encode_png(width, height, rows, alpha=alpha)


CLEAR = (0, 0, 0, 0)


def _creature(rng: random.Random, color, *, eyes: bool) -> bytes:
    n = 12
    body = [[False] * n for _ in range(n)]
    for r in range(1, n - 1):
        for c in range(n // 2):
            body[r][c] = body[r][n - 1 - c] = rng.random() < (0.9 if c > 1 else 0.55) and (r > 1 or c > 2)
    for r in range(3, n - 2):            # a solid core, so the sprite is never a few specks
        for c in range(3, n // 2):
            body[r][c] = body[r][n - 1 - c] = True
    edge, light = _mix(color, -0.45), _mix(color, 0.35)
    grid = [[CLEAR] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            if not body[r][c]:
                continue
            border = any(not (0 <= r + dr < n and 0 <= c + dc < n and body[r + dr][c + dc]) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            grid[r][c] = (*(edge if border else light if r < 4 else color), 255)
    if eyes:
        for c in (n // 2 - 3, n // 2 + 2):
            grid[4][c], grid[5][c] = (255, 255, 255, 255), (20, 20, 30, 255)
    return _grid_png(grid, 4)


def _coin(color) -> bytes:
    n, c0 = 12, 5.5
    edge, light = _mix(color, -0.4), _mix(color, 0.5)
    grid = [[CLEAR] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            d = math.hypot(r - c0, c - c0)
            if d <= 5.4:
                grid[r][c] = (*(edge if d > 4.2 else light if (r + c) < 9 and d < 3 else color), 255)
    return _grid_png(grid, 4)


def _ground(rng: random.Random, color) -> bytes:
    n = 12
    top, dark, mid = _mix(color, 0.45), _mix(color, -0.3), color
    grid = [[(*(top if r < 2 else mid), 255) for _ in range(n)] for r in range(n)]
    for r in range(2, n):
        for c in range(n):
            if rng.random() < 0.16:
                grid[r][c] = (*dark, 255)
    for c in range(n):
        grid[2][c] = (*_mix(top, -0.2), 255)
    return _grid_png(grid, 4)


def _background(rng: random.Random, kind: str, bg) -> bytes:
    w, h = 192, 108
    top, bottom = _mix(bg, 0.25), _mix(bg, -0.35)
    layers = [(_mix(bg, -0.18), 0.55, 9), (_mix(bg, -0.30), 0.72, 14), (_mix(bg, -0.42), 0.86, 20)]
    phases = [(rng.random() * 6.28, rng.random() * 6.28) for _ in layers]
    stars = {(rng.randrange(w), rng.randrange(int(h * 0.7))) for _ in range(70)} if kind == 'shooter' else set()
    rows = []
    for y in range(h):
        t = y / (h - 1)
        base = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        row = bytearray()
        for x in range(w):
            px = base
            if (x, y) in stars:
                px = (235, 235, 245)
            if kind != 'shooter':
                for (col, level, amp), (p1, p2) in zip(layers, phases):
                    ridge = h * level + amp * (math.sin(x / 17 + p1) * 0.6 + math.sin(x / 7 + p2) * 0.4)
                    if y >= ridge:
                        px = col
            row += bytes(px)
        rows.append(bytes(row))
    return encode_png(w, h, rows, alpha=False)


def procedural(defn: dict) -> dict[str, bytes]:
    """Every role, as PNG bytes. Deterministic: the same seed, kind and palette give the same bytes."""
    p, seed = defn['palette'], defn['seed']
    return {
        'background': _background(_rng(seed, 'background'), defn['kind'], _rgb(p['bg'])),
        'player': _creature(_rng(seed, 'player'), _rgb(p['player']), eyes=True),
        'enemy': _creature(_rng(seed, 'enemy'), _rgb(p['enemy']), eyes=True),
        'item': _coin(_rgb(p['item'])),
        'ground': _ground(_rng(seed, 'ground'), _rgb(p['ground'])),
    }


# ---- the checks every image passes, whoever made it --------------------------------------------------------------
def check_image(role: str, data: bytes, mime: str) -> str | None:
    """None when the image may be used for this role; otherwise the reason it is dropped."""
    if role not in ART_ROLES:
        return f'unknown role {role!r}'
    if not data:
        return 'empty'
    if len(data) > ART_MAX_BYTES:
        return f'{len(data):,} bytes is over the size bound ({ART_MAX_BYTES:,})'
    if mime == 'image/png':
        info = png_info(data)
        if info is None:
            return 'the bytes are not a PNG'
        width, height, has_alpha = info
        if role in SPRITE_ROLES and role != 'ground' and not has_alpha:
            return 'a sprite must be a PNG with transparency (this one would draw as a box)'
    elif mime in ('image/jpeg', 'image/webp'):
        magic = b'\xff\xd8\xff' if mime == 'image/jpeg' else b'RIFF'
        if not data.startswith(magic) or (mime == 'image/webp' and data[8:12] != b'WEBP'):
            return f'the bytes are not {mime}'
        if role in SPRITE_ROLES and role != 'ground':
            return 'a sprite must be a PNG with transparency'
        width = height = None
        if mime == 'image/webp' or mime == 'image/jpeg':
            from ..providers.image_provider import sniff_image
            try:
                _m, width, height = sniff_image(data)
            except ValueError:
                return f'the bytes are not {mime}'
    else:
        return f'type {mime!r} is not used for art'
    if width is not None and not (MIN_SIDE <= width <= MAX_SIDE and MIN_SIDE <= height <= MAX_SIDE):
        return f'{width}x{height} px is outside {MIN_SIDE} to {MAX_SIDE}'
    return None


# ---- the provider source -----------------------------------------------------------------------------------------
_PROMPTS = {
    'background': 'wide scenic game background, soft parallax-friendly landscape, no characters, {theme}',
    'player': 'single game character sprite, side view, centred, plain transparent background, {theme}',
    'enemy': 'single game enemy sprite, side view, centred, plain transparent background, {theme}',
    'item': 'single collectible item sprite, centred, plain transparent background, {theme}',
    'ground': 'seamless square ground tile texture, top-down flat, {theme}',
}
_NEGATIVE = 'No text, no letters, no logos, no watermark, no user interface elements.'


def prompt_for(role: str, theme: str) -> str:
    return f'{_PROMPTS[role].format(theme=theme.strip()[:200] or "bright friendly 2D game art")}. {_NEGATIVE}'


class ProviderImageSource:
    """The existing image provider (submit / poll / collect, journal, kill switch) asked for one image per role.
    Every wait is bounded: at most `max_polls` polls per image (the provider sleeps its own interval between them)."""

    def __init__(self, provider, *, build_id: str, max_polls: int = 40) -> None:
        if max_polls < 1:
            raise ValueError('max_polls must be at least 1')
        self.provider, self.build_id, self.max_polls = provider, build_id, max_polls

    def image(self, role: str, theme: str) -> tuple[bytes, str]:
        from ..capabilities import CapabilityRequirement
        from ..image_prompt import IMAGE_CAPABILITY
        req = CapabilityRequirement(
            id=f'game-art-{role}', key=IMAGE_CAPABILITY, purpose=f'2D game {role} art', required=False,
            constraints={'prompt': prompt_for(role, theme), 'aspect_ratio': '16:9' if role == 'background' else '1:1'})
        handle = self.provider.submit(req, idempotency_key=f'{self.build_id}:game-art:{role}')
        for _ in range(self.max_polls):
            state = self.provider.poll(handle)
            if state.status == 'SUCCEEDED':
                result = self.provider.collect(handle)
                if not result.payloads:
                    raise RuntimeError('the provider returned no image')
                return result.payloads[0].data, result.payloads[0].mime_type
            if state.status in ('FAILED', 'CANCELLED'):
                raise RuntimeError(f'the provider ended the image as {state.status}')
        raise TimeoutError(f'the image was not ready after {self.max_polls} polls')


# ---- the layer ---------------------------------------------------------------------------------------------------
@dataclass
class ArtReport:
    sources: dict = field(default_factory=dict)         # role -> 'provider' | 'procedural'
    dropped: list = field(default_factory=list)         # {'role', 'reason'}: an image that was asked for and not used
    bytes: dict = field(default_factory=dict)           # role -> size of the image in the page
    sha256: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {'sources': dict(self.sources), 'dropped': list(self.dropped), 'bytes': dict(self.bytes),
                'sha256': dict(self.sha256), 'provider_images': sum(1 for s in self.sources.values() if s == 'provider')}


def attach(defn: dict, *, source=None, theme: str = '', roles=ART_ROLES) -> tuple[dict, dict, ArtReport]:
    """(the definition as 148ai.game/2, the image files, what happened to each role). The files are {path: (bytes, mime)}
    under assets/, named by role (repository_assets.asset_path); the definition only names them. `defn` must be a valid
    version 1 definition (the model's); `source` (ProviderImageSource or anything with .image(role, theme) -> (bytes,
    mime)) is optional; with none, every role is procedural. Never raises for an image: a bad one is dropped and said."""
    from ..repository_assets import MIME_EXT, asset_path
    if defn.get('schema') != SCHEMA or 'art' in defn:
        raise ValueError('art is attached to a version 1 definition that has none')
    validate(defn)
    fallback = procedural(defn)
    report, art, files, used = ArtReport(), {}, {}, 0
    for role in roles:
        data, mime, origin = fallback[role], 'image/png', 'procedural'
        if source is not None:
            try:
                got, got_mime = source.image(role, theme)
                why = check_image(role, got, got_mime)
                if why is None and used + len(got) > ART_TOTAL_MAX_BYTES:
                    why = f'the images of the game would be over {ART_TOTAL_MAX_BYTES:,} bytes'
                if why is None and got_mime not in MIME_EXT:
                    why = f'{got_mime} cannot be carried as a file'
                if why is None:
                    data, mime, origin = got, got_mime, 'provider'
                else:
                    report.dropped.append({'role': role, 'reason': why})
            except Exception as exc:       # noqa: BLE001 -- art never fails a build; the reason is recorded, not hidden
                report.dropped.append({'role': role, 'reason': f'{type(exc).__name__}: {str(exc)[:200]}'})
        path = asset_path(role, '', mime)
        art[role], files[path] = path, (data, mime)
        used += len(data)
        report.sources[role], report.bytes[role] = origin, len(data)
        report.sha256[role] = hashlib.sha256(data).hexdigest()
    out = {**defn, 'schema': SCHEMA_V2, 'art': art}
    validate(out)
    return out, files, report
