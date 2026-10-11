"""Preview inspector: element picking for Visual Edit, added around the
existing preview router without changing it.

Founder directive 2026-10-11, task 3. The preview runs on its own origin
(https://<prv-id>.<suffix>), so the workspace cannot read the iframe's DOM.
When OMNI_PREVIEW_INSPECTOR=1 this wrapper:

- serves GET /__148ai/inspector.js from the preview host (same origin as the
  app, so the app's own `script-src 'self'` allows it), and
- adds <script src="/__148ai/inspector.js" defer> to HTML documents that are
  loaded INTO AN IFRAME (Sec-Fetch-Dest: iframe) by an authorized viewer.
  Top-level visits and share/public visitors opening the page directly get
  the app's HTML byte-for-byte.

The script is inert until the PARENT window, whose origin must be in
OMNI_WORKSPACE_ORIGINS, sends {type:'148ai:inspect', enabled:true}. It then
highlights the element under the pointer/finger and, on click/tap, posts a
bounded description (tag, id, classes, a few attributes, visible text, a CSS
path, the box) back to that origin only. It never reads cookies, storage,
form values or network data and changes nothing in the app.

Rollback: OMNI_PREVIEW_INSPECTOR unset (pass-through) or run
`python -m omni_prod.preview_router` again (compose).
"""
from __future__ import annotations

import gzip
import io
import json
import os
import re
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit

from .preview_router import RouteTable, _token_from, make_handler, preview_id_for_host

INSPECTOR_PATH = '/__148ai/inspector.js'
_MAX_HTML = 5 * 1024 * 1024

INSPECTOR_JS = r"""(function () {
  'use strict';
  if (window.__148aiInspector || window.parent === window) return;
  window.__148aiInspector = true;
  var ALLOWED = __ORIGINS__;
  var parentOrigin = null, enabled = false, box = null, hoverEl = null;
  function post(msg) { if (parentOrigin) window.parent.postMessage(msg, parentOrigin); }
  function cssPath(el) {
    var parts = [];
    while (el && el.nodeType === 1 && parts.length < 6 && el !== document.documentElement) {
      var p = el.tagName.toLowerCase();
      if (el.id) { parts.unshift(p + '#' + el.id); break; }
      var sib = el, n = 1; while ((sib = sib.previousElementSibling)) if (sib.tagName === el.tagName) n++;
      parts.unshift(p + ':nth-of-type(' + n + ')'); el = el.parentElement;
    }
    return parts.join(' > ');
  }
  function describe(el) {
    var attrs = {}, keys = ['name','type','href','src','placeholder','aria-label','data-testid','role','title','alt','for'];
    for (var i = 0; i < keys.length; i++) { var v = el.getAttribute(keys[i]); if (v) attrs[keys[i]] = String(v).slice(0, 200); }
    if (attrs.type === 'password') delete attrs.placeholder;
    var r = el.getBoundingClientRect();
    var text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 160);
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') text = '';  // never form values
    var htmlCopy = el.cloneNode(false).outerHTML.replace(/\svalue="[^"]*"/g, '').slice(0, 400);
    return { tag: el.tagName.toLowerCase(), id: el.id || '', classes: Array.prototype.slice.call(el.classList, 0, 8),
             attrs: attrs, text: text, path: cssPath(el), html: htmlCopy, page: location.pathname,
             rect: { x: r.left, y: r.top, w: r.width, h: r.height }, viewport: { w: innerWidth, h: innerHeight } };
  }
  function ensureBox() {
    if (box) return box;
    box = document.createElement('div');
    box.setAttribute('data-148ai-inspector', '');
    box.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483647;border:2px solid #0B7A75;' +
      'background:rgba(11,122,117,.12);border-radius:4px;transition:all .06s;display:none';
    document.documentElement.appendChild(box);
    return box;
  }
  function show(el) {
    var b = ensureBox(); if (!el) { b.style.display = 'none'; return; }
    var r = el.getBoundingClientRect();
    b.style.display = 'block'; b.style.left = r.left + 'px'; b.style.top = r.top + 'px';
    b.style.width = r.width + 'px'; b.style.height = r.height + 'px';
  }
  function target(ev) {
    var el = ev.target; if (!el || el.nodeType !== 1 || el === box) return null;
    if (el === document.body || el === document.documentElement) return null;
    return el;
  }
  function onMove(ev) { if (!enabled) return; hoverEl = target(ev); show(hoverEl); }
  function onPick(ev) {
    if (!enabled) return;
    var el = target(ev); if (!el) return;
    ev.preventDefault(); ev.stopPropagation(); if (ev.stopImmediatePropagation) ev.stopImmediatePropagation();
    show(el); post({ type: '148ai:selection', selection: describe(el) });
  }
  function onKey(ev) { if (enabled && ev.key === 'Escape') { post({ type: '148ai:cancel' }); } }
  document.addEventListener('mouseover', onMove, true);
  document.addEventListener('touchstart', function (ev) { if (enabled) { hoverEl = target(ev); show(hoverEl); } }, { capture: true, passive: true });
  document.addEventListener('click', onPick, true);
  document.addEventListener('submit', function (ev) { if (enabled) { ev.preventDefault(); ev.stopPropagation(); } }, true);
  document.addEventListener('keydown', onKey, true);
  window.addEventListener('message', function (ev) {
    if (ev.source !== window.parent || ALLOWED.indexOf(ev.origin) < 0) return;
    var d = ev.data || {};
    if (d.type === '148ai:hello') { parentOrigin = ev.origin; post({ type: '148ai:ready', page: location.pathname }); }
    if (d.type === '148ai:inspect') {
      parentOrigin = ev.origin; enabled = !!d.enabled;
      document.documentElement.style.cursor = enabled ? 'crosshair' : '';
      if (!enabled) show(null);
      post({ type: '148ai:inspecting', enabled: enabled });
    }
  });
})();
"""


def workspace_origins() -> list[str]:
    out = []
    for o in (os.getenv('OMNI_WORKSPACE_ORIGINS', '') or '').split(','):
        o = o.strip().rstrip('/')
        if re.fullmatch(r'https://[a-z0-9.-]+(:\d+)?', o) or re.fullmatch(r'http://(127\.0\.0\.1|localhost)(:\d+)?', o):
            out.append(o)
    return out


def inspector_script(origins: list[str]) -> bytes:
    return INSPECTOR_JS.replace('__ORIGINS__', json.dumps(origins)).encode()


def inject(html_bytes: bytes) -> bytes:
    tag = b'<script src="' + INSPECTOR_PATH.encode() + b'" defer></script>'
    if tag in html_bytes:
        return html_bytes
    m = re.search(rb'</head\s*>', html_bytes, re.I) or re.search(rb'</body\s*>', html_bytes, re.I)
    if m:
        return html_bytes[:m.start()] + tag + html_bytes[m.start():]
    return html_bytes + tag


def _split_response(raw: bytes):
    head, sep, body = raw.partition(b'\r\n\r\n')
    if not sep:
        return None
    lines = head.split(b'\r\n')
    status = lines[0]
    headers = []
    for line in lines[1:]:
        k, _, v = line.partition(b':')
        headers.append((k.decode('latin-1').strip(), v.decode('latin-1').strip()))
    return status, headers, body


def rewrite_response(raw: bytes) -> bytes:
    """Add the inspector tag to an HTML 200 response; anything else unchanged."""
    parts = _split_response(raw)
    if parts is None:
        return raw
    status, headers, body = parts
    if b' 200 ' not in status + b' ':
        return raw
    hmap = {k.lower(): v for k, v in headers}
    if 'text/html' not in hmap.get('content-type', '').lower() or len(body) > _MAX_HTML:
        return raw
    enc = hmap.get('content-encoding', '').lower()
    if enc not in ('', 'identity', 'gzip'):
        return raw
    try:
        plain = gzip.decompress(body) if enc == 'gzip' else body
    except OSError:
        return raw
    new = inject(plain)
    out_headers = [(k, v) for k, v in headers if k.lower() not in ('content-length', 'content-encoding', 'etag')]
    out_headers.append(('Content-Length', str(len(new))))
    head = status + b'\r\n' + b''.join(f'{k}: {v}\r\n'.encode('latin-1') for k, v in out_headers)
    return head + b'\r\n' + new


def make_inspecting_handler(routes: RouteTable, suffix: str, upstream_host: str = '127.0.0.1', access=None,
                            *, enabled: bool | None = None, origins: list[str] | None = None):
    Base = make_handler(routes, suffix, upstream_host, access)
    on = (os.getenv('OMNI_PREVIEW_INSPECTOR') == '1') if enabled is None else enabled
    allowed = workspace_origins() if origins is None else origins
    script = inspector_script(allowed)

    class Handler(Base):
        def _authorized(self) -> bool:
            pid = preview_id_for_host(self.headers.get('Host', ''), suffix)
            if not pid or not routes.port_for(pid):
                return False
            if access is None:
                return True
            token, _ = _token_from(self)
            try:
                return bool(access.allows(pid, token))
            except Exception:
                return False

        def _inspect_route(self):
            if not on or not allowed:
                return Base._route(self)
            path = urlsplit(self.path).path
            if path == INSPECTOR_PATH and self.command in ('GET', 'HEAD'):
                if not self._authorized():
                    return self._plain(404, 'not found')
                self.send_response(200)
                self.send_header('Content-Type', 'text/javascript; charset=utf-8')
                self.send_header('Content-Length', str(len(script)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                if self.command != 'HEAD':
                    self.wfile.write(script)
                return
            if self.command != 'GET' or self.headers.get('Sec-Fetch-Dest', '').lower() != 'iframe':
                return Base._route(self)
            real, buf = self.wfile, io.BytesIO()
            self.wfile = buf
            try:
                Base._route(self)
                if hasattr(self, '_headers_buffer') and self._headers_buffer:
                    self.flush_headers()
            finally:
                self.wfile = real
            real.write(rewrite_response(buf.getvalue()))

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _inspect_route

    return Handler


def main():
    from .db import DatabasePool
    from .preview_access import PreviewAccess
    from .preview_repository import PostgresPreviewRepository
    suffix = os.environ['OMNI_PREVIEW_HOST_SUFFIX']
    runtime_host = os.environ['OMNI_PREVIEW_RUNTIME_HOST']
    port = int(os.getenv('OMNI_PREVIEW_ROUTER_PORT', '8088'))
    repo = PostgresPreviewRepository(DatabasePool(os.environ['OMNI_DATABASE_URL']))
    access = PreviewAccess(repo.pool) if os.getenv('OMNI_PREVIEW_ACCESS_CONTROL', '1') != '0' else None
    handler = make_inspecting_handler(RouteTable(repo.get_route, runtime_host), suffix, access=access)
    server = ThreadingHTTPServer(('127.0.0.1', port), handler)
    print(f'preview router (inspector {"on" if os.getenv("OMNI_PREVIEW_INSPECTOR") == "1" else "off"}) on '
          f'127.0.0.1:{port} for *.{suffix}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
