"""1.3 capture (docs/spec/gemini-a2.md 3.2): two full-page PNG screenshots, 390 and 1440, stored by sha256.

Both or nothing: a missing screenshot (the browser failed, the page is taller than 20000px) rejects the candidate with
`capture_missing`; a capture with one screenshot is never a pass. The bytes go to the object store under their own
digest; the document keeps the digest, so a later reader can check what it reads.
"""
from __future__ import annotations

import hashlib
import struct

from .contract import checked, now_z, rejection

VIEWPORTS = ((390, 844), (1440, 900))
MAX_HEIGHT = 20000


def png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG')
    return struct.unpack('>II', data[16:24])


def capture(session, candidate: dict, store, *, at: str | None = None, shoot=None) -> dict:
    """`shoot(page, width)` takes one screenshot (injectable for the missing-screenshot control)."""
    at = at or now_z()
    shoot = shoot or _shoot
    base = {'kind': 'capture_result', 'candidate_id': candidate['candidate_id'], 'url': candidate['url'],
            'captured_at': at}
    shots = []
    for width, height in VIEWPORTS:
        try:
            with session.page(width=width, height=height) as page:
                page.goto(candidate['url'], wait_until='load', timeout=15000)
                tall = page.evaluate('() => document.documentElement.scrollHeight')
                if tall > MAX_HEIGHT:
                    raise ValueError(f'page height {tall}px is above {MAX_HEIGHT}px')
                data = shoot(page, width)
        except Exception as exc:
            return checked({**base, 'screenshots': shots, 'outcome': 'reject',
                            'rejection': rejection('capture_missing', 'capture', f'{width}px: {type(exc).__name__}'[:80],
                                                   'both 390 and 1440', at)})
        w, h = png_size(data)
        digest = hashlib.sha256(data).hexdigest()
        key = f'a2/captures/{candidate["candidate_id"]}/{width}-{digest}.png'
        try:
            store.put_bytes(key, data)
        except KeyError:                  # the same bytes were already stored under this digest
            pass
        shots.append({'viewport_px': width, 'full_page': True, 'sha256': digest, 'height_px': h, 'mime': 'image/png'})
    return checked({**base, 'screenshots': shots, 'outcome': 'pass'})


def _shoot(page, width: int) -> bytes:
    return page.screenshot(full_page=True, type='png')
