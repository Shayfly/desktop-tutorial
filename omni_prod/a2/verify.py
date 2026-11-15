"""1.2 verify (docs/spec/gemini-a2.md 3.2): live, fast, light, readable direction, robots -- measured, not guessed.

Order (the first failure is the rejection; later checks do not run on a rejected page):
  robots.txt  -> robots_disallowed (and the page itself is never requested)
  HTTP status -> not_live          (200 only; a timeout or a refused connection is not live too)
  load at 390 -> too_slow          (navigation start to the load event, <= 4000 ms)
  bytes       -> too_heavy         (response bodies of every finished request, <= 6 MB)

Direction: `rtl` when <html> says Hebrew (dir="rtl" or lang="he*"); otherwise `neutral` -- whether a non-Hebrew
page's structure is bound to its reading direction is decided by the skeleton step (1.5), not here.
"""
from __future__ import annotations

import time
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import urlsplit

from .browser import USER_AGENT
from .contract import checked, now_z, rejection

MAX_LOAD_MS = 4000
MAX_BYTES = 6_000_000
NAV_TIMEOUT_MS = 15000


def robots_allows(url: str, session) -> bool:
    """robots.txt of the page's host. Missing (404/410) means allowed; unreachable means NOT allowed (fail closed)."""
    parts = urlsplit(url)
    robots_url = f'{parts.scheme}://{parts.netloc}/robots.txt'
    if not session.allowed(robots_url):
        return False
    local, headers = session.local(robots_url)
    try:
        with urllib.request.urlopen(urllib.request.Request(local, headers=headers), timeout=5) as r:
            body = r.read(200_000).decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:
        return exc.code in (404, 410)
    except (urllib.error.URLError, OSError):
        return False
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(body.splitlines())
    return rp.can_fetch(USER_AGENT, url)


def verify(session, candidate: dict, *, at: str | None = None) -> dict:
    at = at or now_z()
    url = candidate['url']
    out = {'kind': 'verify_result', 'candidate_id': candidate['candidate_id'], 'url': url, 'http_status': 0,
           'load_ms_390': None, 'transfer_bytes': None, 'direction': 'unknown', 'at': at}

    def reject(code, measured, threshold):
        return checked({**out, 'outcome': 'reject', 'rejection': rejection(code, 'verify', measured, threshold, at)})

    if not session.allowed(url):          # a host this session may not reach is never requested, not even robots
        session.blocked.append(urlsplit(url).hostname or '')
        return reject('not_live', 'blocked_offline', 200)
    allowed = robots_allows(url, session)
    out['robots_allowed'] = allowed
    if not allowed:
        return reject('robots_disallowed', False, True)
    with session.page(width=390, height=844) as page:
        started = time.monotonic()
        try:
            response = page.goto(url, wait_until='load', timeout=NAV_TIMEOUT_MS)
        except Exception as exc:          # refused, reset, timeout: not live
            name = type(exc).__name__
            return reject('not_live', 'timeout' if 'Timeout' in name else 'unreachable', 200)
        elapsed = int((time.monotonic() - started) * 1000)
        status = response.status if response is not None else 0
        out['http_status'] = status
        out['load_ms_390'] = _load_ms(page, elapsed)
        out['transfer_bytes'] = session.current_bytes['n']
        if response is not None and response.url != url and session.allowed(response.url):
            out['final_url'] = response.url
        out['direction'] = 'rtl' if page.evaluate(
            "() => { const h = document.documentElement; return h.dir.toLowerCase() === 'rtl' || "
            "(h.lang || '').toLowerCase().startsWith('he'); }") else 'neutral'
    if status != 200:
        return reject('not_live', status, 200)
    if out['load_ms_390'] > MAX_LOAD_MS:
        return reject('too_slow', out['load_ms_390'], MAX_LOAD_MS)
    if out['transfer_bytes'] > MAX_BYTES:
        return reject('too_heavy', out['transfer_bytes'], MAX_BYTES)
    return checked({**out, 'outcome': 'pass'})


def _load_ms(page, fallback: int) -> int:
    """The navigation timing of the page itself (start to loadEventEnd); the wall clock when it is unavailable."""
    try:
        ms = page.evaluate("() => { const n = performance.getEntriesByType('navigation')[0];"
                           " return n && n.loadEventEnd > 0 ? Math.round(n.loadEventEnd) : null; }")
    except Exception:
        ms = None
    return int(ms) if isinstance(ms, (int, float)) and ms >= 0 else fallback
