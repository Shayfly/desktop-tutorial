"""Preview router: https://<prv-id>.<suffix> -> the preview container on this host.

Runs on the worker host behind Caddy (TLS). Standard library only.

- GET /_health                 -> 200 "ok"
- GET /_caddy_ask?domain=HOST  -> 200 only for a RUNNING, unexpired preview on
  this host (Caddy issues an on-demand certificate only then), else 404.
- anything else                -> reverse proxy to 127.0.0.1:<host_port> of the
  preview named by the Host header, via PostgresPreviewRepository.get_route(),
  only if the preview is PUBLIC or the request carries a valid access token
  (omni_prod.preview_access; autonomous completion directive §4). The token
  is stripped before proxying, so the generated app never sees it.

Environment: OMNI_DATABASE_URL, OMNI_PREVIEW_HOST_SUFFIX (e.g.
151-145-89-132.sslip.io), OMNI_PREVIEW_RUNTIME_HOST, OMNI_PREVIEW_ROUTER_PORT
(default 8088). Listens on 127.0.0.1 only.
"""
from __future__ import annotations

import http.client
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlencode, urlsplit

from .preview_access import COOKIE, HEADER, OWNER_TTL, QUERY_PARAM
from .preview_runtime import preview_id_from_host_label

_HOP_BY_HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers',
               'transfer-encoding', 'upgrade', 'host'}
_MAX_BODY = 10 * 1024 * 1024
_CACHE_SECONDS = 5.0


def preview_id_for_host(host: str, suffix: str) -> str | None:
    host = (host or '').split(':', 1)[0].strip().lower().rstrip('.')
    suffix = suffix.strip().lower().lstrip('.')
    if not suffix or not host.endswith('.' + suffix):
        return None
    label = host[:-(len(suffix) + 1)]
    if '.' in label:
        return None
    return preview_id_from_host_label(label)


class RouteTable:
    """get_route() with a short cache; only routes owned by this host."""

    def __init__(self, lookup, runtime_host: str, clock=time.monotonic):
        self._lookup, self._host, self._clock = lookup, runtime_host, clock
        self._cache: dict[str, tuple[float, int | None]] = {}
        self._lock = threading.Lock()

    def port_for(self, preview_id: str) -> int | None:
        now = self._clock()
        with self._lock:
            hit = self._cache.get(preview_id)
            if hit and now - hit[0] < _CACHE_SECONDS:
                return hit[1]
        route = self._lookup(preview_id)
        port = route[1] if route and route[0] == self._host else None
        with self._lock:
            self._cache[preview_id] = (now, port)
        return port


_PRIVATE_PAGE = (
    '<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" '
    'content="width=device-width,initial-scale=1"><title>תצוגה פרטית</title><style>body{font:16px/1.6 system-ui,'
    'sans-serif;margin:0;display:grid;place-items:center;min-height:100vh;background:#f4f6f8;color:#14202e}'
    'main{max-width:30rem;padding:2rem;background:#fff;border-radius:12px;border:1px solid #d6dde4}</style></head>'
    '<body><main><h1>התצוגה הזאת פרטית</h1><p>אפשר לפתוח אותה רק מתוך סביבת העבודה של 148AI, או בקישור '
    'שיתוף שבעל הפרויקט יצר.</p><p lang="en" dir="ltr">This preview is private. Open it from the 148AI workspace '
    'or with a share link from its owner.</p></main></body></html>')


def _token_from(handler) -> tuple[str | None, bool]:
    """(token, came_from_query)."""
    q = parse_qs(urlsplit(handler.path).query)
    if q.get(QUERY_PARAM):
        return q[QUERY_PARAM][0], True
    header = handler.headers.get(HEADER)
    if header:
        return header.strip(), False
    raw = handler.headers.get('Cookie')
    if raw:
        try:
            jar = SimpleCookie(raw)
            if COOKIE in jar:
                return jar[COOKIE].value, False
        except Exception:
            pass
    return None, False


def _strip_token(path: str) -> str:
    parts = urlsplit(path)
    q = [(k, v) for k, vs in parse_qs(parts.query, keep_blank_values=True).items() for v in vs if k != QUERY_PARAM]
    return parts.path + ('?' + urlencode(q) if q else '')


def _strip_cookie(raw: str | None) -> str | None:
    if not raw:
        return raw
    kept = [c for c in raw.split(';') if c.strip() and not c.strip().startswith(COOKIE + '=')]
    return '; '.join(c.strip() for c in kept) or None



def make_handler(routes: RouteTable, suffix: str, upstream_host: str = '127.0.0.1', access=None):
    class Handler(BaseHTTPRequestHandler):
        server_version = '148ai-preview-router'
        protocol_version = 'HTTP/1.1'

        def log_message(self, fmt, *args):  # one compact line per request, no query strings
            print(f'{self.command} {self.headers.get("Host", "-")} {self.path.split("?", 1)[0]} -> {args[1] if len(args) > 1 else ""}',
                  flush=True)

        def _plain(self, status: int, text: str):
            body = text.encode()
            self.send_response(status)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)

        def _route(self):
            path = urlsplit(self.path).path
            if path == '/_health':
                return self._plain(200, 'ok')
            if path == '/_caddy_ask':
                domain = (parse_qs(urlsplit(self.path).query).get('domain') or [''])[0]
                pid = preview_id_for_host(domain, suffix)
                return self._plain(200 if pid and routes.port_for(pid) else 404, 'ok' if pid else 'unknown')
            pid = preview_id_for_host(self.headers.get('Host', ''), suffix)
            port = routes.port_for(pid) if pid else None
            if not port:
                return self._plain(404, 'This preview is not running (stopped, expired or unknown).')
            if access is not None:
                token, from_query = _token_from(self)
                try:
                    allowed = access.allows(pid, token)
                except Exception:
                    allowed = False  # fail closed
                if not allowed:
                    access.record_denied(pid)
                    body = _PRIVATE_PAGE.encode()
                    self.send_response(401)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    if self.command != 'HEAD':
                        self.wfile.write(body)
                    return
                if from_query and self.command in ('GET', 'HEAD'):
                    # Exchange the link token for an HttpOnly cookie and drop it from the address bar.
                    self.send_response(302)
                    self.send_header('Location', _strip_token(self.path) or '/')
                    self.send_header('Set-Cookie', f'{COOKIE}={token}; Path=/; Max-Age={int(OWNER_TTL.total_seconds())}; '
                                                   'HttpOnly; Secure; SameSite=None; Partitioned')
                    self.send_header('Content-Length', '0')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Referrer-Policy', 'no-referrer')
                    self.end_headers()
                    return
            length = int(self.headers.get('Content-Length') or 0)
            if length > _MAX_BODY:
                return self._plain(413, 'request body too large')
            body = self.rfile.read(length) if length else None
            headers = {k: v for k, v in self.headers.items()
                       if k.lower() not in _HOP_BY_HOP and k.lower() not in (HEADER.lower(), 'cookie')}
            cookie = _strip_cookie(self.headers.get('Cookie'))
            if cookie:
                headers['Cookie'] = cookie
            headers['Host'] = f'{upstream_host}:{port}'
            headers['X-Forwarded-Host'] = self.headers.get('Host', '')
            headers['X-Forwarded-Proto'] = 'https'
            conn = http.client.HTTPConnection(upstream_host, port, timeout=30)
            try:
                conn.request(self.command, _strip_token(self.path) or '/', body=body, headers=headers)
                resp = conn.getresponse()
                data = resp.read()
            except OSError:
                return self._plain(502, 'The preview did not answer.')
            finally:
                conn.close()
            self.send_response(resp.status, resp.reason)
            for k, v in resp.getheaders():
                if k.lower() not in _HOP_BY_HOP and k.lower() != 'content-length':
                    self.send_header(k, v)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _route

    return Handler


def main():
    from .db import DatabasePool
    from .preview_repository import PostgresPreviewRepository
    suffix = os.environ['OMNI_PREVIEW_HOST_SUFFIX']
    runtime_host = os.environ['OMNI_PREVIEW_RUNTIME_HOST']
    port = int(os.getenv('OMNI_PREVIEW_ROUTER_PORT', '8088'))
    repo = PostgresPreviewRepository(DatabasePool(os.environ['OMNI_DATABASE_URL']))
    from .preview_access import PreviewAccess
    access = PreviewAccess(repo.pool) if os.getenv('OMNI_PREVIEW_ACCESS_CONTROL', '1') != '0' else None
    server = ThreadingHTTPServer(('127.0.0.1', port), make_handler(RouteTable(repo.get_route, runtime_host), suffix,
                                                                  access=access))
    print(f'preview router on 127.0.0.1:{port} for *.{suffix} (host {runtime_host})', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
