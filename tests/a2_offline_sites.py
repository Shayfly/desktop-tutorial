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
             '<script src="https://cdn.example.invalid/tracker.js"></script></head><body><h1>קצב</h1>'
             '<img src="https://images.example.invalid/hero.jpg" alt=""></body></html>')
_TALL = ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"></head>'
         '<body><div style="height:25000px">ארוך מאוד</div></body></html>')
_SLOW = ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"></head>'
         '<body><h1>איטי</h1><img src="/slow.png" alt=""></body></html>')
_HEAVY = ('<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"></head>'
          '<body><h1>כבד</h1><img src="/big.bin" alt=""></body></html>')


_RICH_BUTCHER = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>rich</title>
<style>body{margin:0;background:#fbf7f2;color:#1c1917;font-family:Heebo,sans-serif;font-size:18px}
nav{display:flex;gap:24px;padding:16px 24px;border-bottom:1px solid #e7ded3}
section{padding:96px 24px}h1{font-size:64px;line-height:72px;margin:0}h2{font-size:30px;margin:0 0 16px}
.hero{display:flex;gap:24px;align-items:center}.hero img{width:640px;height:480px}
a.cta{background:#9a3412;color:#ffffff;padding:14px 22px;border-radius:8px;display:inline-block}
ul.products{display:flex;gap:24px;list-style:none;padding:0}ul.products li{background:#ffffff;padding:16px;font-size:16px}
small{font-size:13px;color:#57534e}
.tel{position:fixed;bottom:16px;left:16px;width:56px;height:56px}
.cookies{position:fixed;bottom:0;right:0;width:40%;height:56px;background:#ffffff;font-size:14px}
footer{padding:48px 24px;font-size:14px;color:#57534e}</style></head><body>
<nav><a href="#">בית</a><a href="#products">מוצרים</a></nav>
<section class="hero"><div><h1>קצביית השכונה</h1><p>בשר טרי</p><a class="cta" href="tel:+97250000000">להתקשר</a></div>
<img src="/photo.png" alt="דלפק"></section>
<section id="products"><h2>המוצרים</h2><ul class="products"><li>בקר</li><li>עוף</li><li>הודו</li><li>קציצות</li></ul></section>
<section><h2>שעות פתיחה</h2><table><tr><th>א׳–ה׳</th><td>07:00–19:00</td></tr></table><small>שבת סגור</small></section>
<section><h2>איך מגיעים</h2><iframe src="https://maps.example.invalid/embed" class="map" width="400" height="200"></iframe></section>
<section><h2>צור קשר</h2><form><input type="text" name="n"><input type="tel" name="t"><button style="background:#9a3412;color:#fff">שליחה</button></form></section>
<footer>פרטי העסק</footer>
<a class="tel" href="tel:+97250000000">חיוג</a><div class="cookies">האתר משתמש בעוגיות</div>
</body></html>"""

_WINE_BAR = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>wine</title>
<style>body{margin:0;background:#1c1917;color:#fafaf9;font-family:Assistant,sans-serif;font-size:18px}
.promo{position:fixed;top:0;left:0;right:0;height:36px;background:#7f1d1d;font-size:14px}
.gate{position:fixed;inset:0;background:#0c0a09;display:flex;align-items:center;justify-content:center}
.hero{padding:160px 24px;background-image:linear-gradient(#000,#333);background-color:#1c1917}
h1{font-size:80px;line-height:88px;margin:0;text-align:center}h2{font-size:40px}p{font-size:18px}
section{padding:128px 24px}small{font-size:13px;color:#a8a29e}</style></head><body>
<header class="hero"><h1>בר היין</h1></header>
<section><h2>תפריט יינות</h2><p>יינות מקומיים</p><small>לגימה אחראית</small></section>
<footer>כתובת</footer>
<div class="promo">מבצע השבוע</div>
<div class="gate" role="dialog"><p>האם מלאו לך 18?</p></div>
</body></html>"""

# a 640x480 PNG of one colour, made here (zlib), so the rich page has a real image
def _png(w=640, h=480):
    import struct
    import zlib
    raw = b''.join(b'\0' + b'\x9a\x34\x12' * w for _ in range(h))
    chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


PNG = _png()


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
        if path == '/photo.png':
            return 200, 'image/png', PNG
        pages = {'ltr': _LTR, 'external': _EXTERNAL, 'tall': _TALL, 'blocked': '<h1>never</h1>'}
        pages.update({'rich-butcher': _RICH_BUTCHER, 'wine-bar': _WINE_BAR})
        if name in pages and path == '/':
            return 200, html, pages[name].encode('utf-8')
        return 404, html, b'<h1>404</h1>'


def url(name: str) -> str:
    return f'https://{name}.a2.test/'
