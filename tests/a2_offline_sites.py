"""Sites A2 collects from, offline (docs/spec/gemini-a2.md section 6): written here, copied from nowhere.

One local server answers every `https://<host>.a2.test/...` request the A2 session maps to it (header x-a2-host).
Each host is one negative control or one good page. Every request is logged, so a test can prove what was NOT
requested (robots) and that nothing left this machine.
"""
from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SLOW_SECONDS = 4.6           # above verify.MAX_LOAD_MS (4000)
HEAVY_BYTES = 7_000_000      # above verify.MAX_BYTES (6 MB)

_DIRECTIONS = (   # three different directions for one vertical (butcher): colour, font, rhythm, hero
    {'bg': '#fbf7f2', 'text': '#1c1917', 'accent': '#9a3412', 'font': 'Heebo', 'gap': 112, 'hero': 'split'},
    {'bg': '#f4f7f3', 'text': '#14231a', 'accent': '#14532d', 'font': 'Frank Ruhl Libre', 'gap': 72, 'hero': 'full'},
    {'bg': '#1c1917', 'text': '#fafaf9', 'accent': '#f59e0b', 'font': 'Assistant', 'gap': 128, 'hero': 'type'},
)


def good_page(n: int) -> str:
    d = _DIRECTIONS[n % 3]
    hero = {'split': '<div class="hero split"><h1>קצביית השכונה</h1><div class="ph"></div></div>',
            'full': '<div class="hero full"><div class="ph"></div><h1>קצביית השכונה</h1></div>',
            'type': '<div class="hero"><h1 class="big">קצביית השכונה</h1></div>'}[d['hero']]
    return f"""<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>דוגמה {n}</title>
<style>:root{{--bg:{d['bg']};--text:{d['text']};--accent:{d['accent']}}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:'{d['font']}',system-ui,sans-serif;font-size:18px}}
section,.hero{{padding:{d['gap']}px 24px}} h1{{font-size:56px;margin:0}} .big{{font-size:96px}}
.ph{{height:240px;background:var(--accent);opacity:.85}} .split{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
a.cta{{background:var(--accent);color:#fff;padding:14px 22px;display:inline-block}}</style></head>
<body>{hero}<section><h2>המוצרים</h2><ul><li>בקר</li><li>עוף</li><li>הודו</li></ul></section>
<section><h2>שעות פתיחה</h2><p>א׳–ה׳</p></section><section><a class="cta" href="#">להתקשר</a></section></body></html>"""


_LTR = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Butcher</title></head>'
        '<body><h1>The corner butcher</h1><section>Meat, poultry</section></body></html>')
_EXTERNAL = ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">'
             '<script src="https://cdn.example.com/tracker.js"></script></head><body><h1>קצב</h1>'
             '<img src="https://images.example.org/hero.jpg" alt=""></body></html>')
_TALL = ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"></head>'
         '<body><div style="height:25000px">ארוך מאוד</div></body></html>')
_SLOW = ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"></head>'
         '<body><h1>איטי</h1><img src="/slow.png" alt=""></body></html>')
_HEAVY = ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"></head>'
          '<body><h1>כבד</h1><img src="/big.bin" alt=""></body></html>')


class Sites:
    def __init__(self):
        self.requests: list[tuple[str, str]] = []
        sites = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                host = self.headers.get('x-a2-host', '')
                path = self.path.split('?', 1)[0]
                sites.requests.append((host, path))
                status, ctype, body = sites.answer(host, path)
                self.send_response(status)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.origin = f'http://127.0.0.1:{self.server.server_address[1]}'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def answer(self, host: str, path: str):
        html = 'text/html; charset=utf-8'
        name = host.split('.', 1)[0]
        if path == '/robots.txt':
            if name == 'blocked':
                return 200, 'text/plain', b'User-agent: *\nDisallow: /\n'
            return 404, 'text/plain', b'no robots'
        if name == 'dead':
            return 404, html, b'<h1>404</h1>'
        if name.startswith('good-') and path == '/':
            return 200, html, good_page(int(name[5:])).encode('utf-8')
        if name == 'slow':
            if path == '/slow.png':
                time.sleep(SLOW_SECONDS)
                return 200, 'image/png', b''
            return 200, html, _SLOW.encode()
        if name == 'heavy':
            if path == '/big.bin':
                return 200, 'application/octet-stream', b'\0' * HEAVY_BYTES
            return 200, html, _HEAVY.encode()
        pages = {'ltr': _LTR, 'external': _EXTERNAL, 'tall': _TALL, 'blocked': '<h1>never</h1>'}
        if name in pages and path == '/':
            return 200, html, pages[name].encode('utf-8')
        return 404, html, b'<h1>404</h1>'


def url(name: str) -> str:
    return f'https://{name}.a2.test/'
