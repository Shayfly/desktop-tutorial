import os
from http.server import BaseHTTPRequestHandler, HTTPServer
PAGE = """<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:sans-serif;margin:0;padding:16px;color:#1a1a1a;background:#fff}form{display:grid;gap:12px;max-width:480px}
input,button{font-size:16px;min-height:44px;padding:8px}button{background:#0b57d0;color:#fff;border:0;border-radius:8px}</style></head>
<body><h1>ניהול תורים</h1><form><label for="n">שם</label><input id="n" name="n"><label for="p">טלפון</label><input id="p" type="tel" name="p">
<button type="submit">קביעת תור</button></form><p>אין תורים עדיין.</p></body></html>"""
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        b = PAGE.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
HTTPServer(('127.0.0.1', int(os.environ['PORT'])), H).serve_forever()
