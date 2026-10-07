"""Preview router: https://<prv-id>.<suffix> -> the preview container on this host.

Runs on the worker host behind Caddy (TLS). Standard library only.

- GET /_health                 -> 200 "ok"
- GET /_caddy_ask?domain=HOST  -> 200 only for a RUNNING, unexpired preview on
  this host (Caddy issues an on-demand certificate only then), else 404.
- anything else                -> reverse proxy to 127.0.0.1:<host_port> of the
  preview named by the Host header, via PostgresPreviewRepository.get_route().

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
from urllib.parse import parse_qs, urlsplit

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


def make_handler(routes: RouteTable, suffix: str, upstream_host: str = '127.0.0.1'):
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
            length = int(self.headers.get('Content-Length') or 0)
            if length > _MAX_BODY:
                return self._plain(413, 'request body too large')
            body = self.rfile.read(length) if length else None
            headers = {k: v for k, v in self.headers.items() if k.lower() not in _HOP_BY_HOP}
            headers['Host'] = f'{upstream_host}:{port}'
            headers['X-Forwarded-Host'] = self.headers.get('Host', '')
            headers['X-Forwarded-Proto'] = 'https'
            conn = http.client.HTTPConnection(upstream_host, port, timeout=30)
            try:
                conn.request(self.command, self.path, body=body, headers=headers)
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
    server = ThreadingHTTPServer(('127.0.0.1', port), make_handler(RouteTable(repo.get_route, runtime_host), suffix))
    print(f'preview router on 127.0.0.1:{port} for *.{suffix} (host {runtime_host})', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
