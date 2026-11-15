"""One Chromium for a collect run, with the network decided by the session -- never assumed.

Offline (the only mode wired today, Shai 2026-11-15): candidate sites have https URLs on the reserved `.test`
top-level domain (RFC 6761: never resolvable), and every request to such a host is answered by a local server this
process names (`offline_origin`). A request to ANY other host is aborted and counted in `blocked` -- never fetched.
So "no network" is enforced by the browser for every page, image and script, not trusted to the fixtures.
"""
from __future__ import annotations

from contextlib import contextmanager
from urllib.parse import urlsplit

OFFLINE_SUFFIX = '.a2.test'
HOST_HEADER = 'x-a2-host'
USER_AGENT = '148AI-reference-collector/0.1'


class Session:
    def __init__(self, browser, *, offline_origin: str):
        if not offline_origin.startswith(('http://127.0.0.1:', 'http://localhost:')):
            raise ValueError('offline mode serves sites only from this machine')
        self.browser, self.offline_origin = browser, offline_origin.rstrip('/')
        self.blocked: list[str] = []          # hosts of requests that were aborted
        self.bytes_by_page: dict[int, int] = {}

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        return parts.scheme == 'https' and (parts.hostname or '').endswith(OFFLINE_SUFFIX)

    def local(self, url: str) -> tuple[str, dict]:
        """The local URL and headers that answer `url` (allowed hosts only)."""
        parts = urlsplit(url)
        path = parts.path or '/'
        return (f'{self.offline_origin}{path}' + (f'?{parts.query}' if parts.query else ''),
                {HOST_HEADER: parts.hostname or '', 'user-agent': USER_AGENT})

    @contextmanager
    def page(self, *, width: int, height: int = 900):
        context = self.browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1,
                                           user_agent=USER_AGENT, service_workers='block')
        page_bytes = {'n': 0}

        def _guard(route):
            url = route.request.url
            if url.startswith(('data:', 'blob:')):
                return route.continue_()
            if not self.allowed(url):
                self.blocked.append(urlsplit(url).hostname or url[:60])
                return route.abort('blockedbyclient')
            local, headers = self.local(url)
            try:
                response = route.fetch(url=local, headers={**route.request.headers, **headers}, timeout=15000)
                body = response.body()
            except Exception:
                return route.abort('connectionrefused')
            page_bytes['n'] += len(body)
            return route.fulfill(response=response, body=body)

        context.route('**/*', _guard)
        try:
            self.current_bytes = page_bytes      # bytes of every response of THIS page (verify reads it)
            yield context.new_page()
        finally:
            context.close()


@contextmanager
def session(*, offline_origin: str):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            yield Session(browser, offline_origin=offline_origin)
        finally:
            browser.close()
