"""1.3 capture (docs/spec/gemini-a2.md 3.2): two full-page PNG screenshots, 390 and 1440, stored by sha256.

Both or nothing: a missing screenshot (the browser failed, the page is taller than 20000px) rejects the candidate with
`capture_missing`; a capture with one screenshot is never a pass. The bytes go to the object store under their own
digest; the document keeps the digest, so a later reader can check what it reads.
"""
from __future__ import annotations

import hashlib
import logging
import struct

from .contract import checked, now_z, rejection

VIEWPORTS = ((390, 844), (1440, 900))
MAX_HEIGHT = 20000


def png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG')
    return struct.unpack('>II', data[16:24])


_LOG = logging.getLogger(__name__)


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
                data = _shoot_bounded(shoot, page, width)
        except Exception as exc:
            # the owner, 2026-11-15 23:33 (step 1 of 3): the rejection carries the exception's own first line, not
            # only its class -- CI showed '390px: Error' twice and nothing more (job 132984165790)
            why = f'{width}px: {type(exc).__name__}: {(str(exc).splitlines() or [""])[0]}'
            return checked({**base, 'screenshots': shots, 'outcome': 'reject',
                            'rejection': rejection('capture_missing', 'capture', why[:80],
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


# The browser's own capture fails now and then with nothing wrong on the page: CI, 2026-11-17 (job on 148f0e4), three
# good sites out of 31 were rejected with "Page.screenshot: Protocol error (Page.captureScreenshot): Unable to capture
# screenshot", and the same run passes when repeated (#393, #403: the "a2 flake"). A good reference must not be lost to
# that. ONLY this error is tried again, at most MAX_SHOT_ATTEMPTS times in all, after a short pause; any other error,
# and this one when it persists, is still a rejection with its own words.
TRANSIENT_SHOT_ERROR = 'Unable to capture screenshot'
MAX_SHOT_ATTEMPTS = 3
SHOT_RETRY_PAUSE_MS = 250


def _shoot_bounded(shoot, page, width: int) -> bytes:
    for attempt in range(1, MAX_SHOT_ATTEMPTS + 1):
        try:
            return shoot(page, width)
        except Exception as exc:
            if TRANSIENT_SHOT_ERROR not in str(exc) or attempt == MAX_SHOT_ATTEMPTS:
                raise
            _LOG.warning('A2_SHOT_RETRY width=%s attempt=%s of %s: %s', width, attempt, MAX_SHOT_ATTEMPTS,
                         (str(exc).splitlines() or [''])[0][:160])
            page.wait_for_timeout(SHOT_RETRY_PAUSE_MS)
    raise AssertionError('unreachable')          # the loop returns or raises


def _shoot(page, width: int) -> bytes:
    return page.screenshot(full_page=True, type='png')
