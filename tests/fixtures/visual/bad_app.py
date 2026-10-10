import os
from http.server import BaseHTTPRequestHandler, HTTPServer
PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="margin:0"><h1 style="color:#bbb;background:#fff">ניהול תורים למספרה קטנה בעיר הגדולה</h1>
<div style="width:1600px;background:#eee">שורה רחבה מאוד שגורמת לגלילה אופקית</div>
<input name="q"><button style="width:16px;height:16px;padding:0"></button>
<button style="position:absolute;top:60px;left:0;width:120px;height:40px">אחד</button><button style="position:absolute;top:70px;left:20px;width:120px;height:40px">שתיים</button>
<img src="/missing.png" alt="x" style="width:40px;height:40px"><a href="#" tabindex="3">קישור</a>
<script>console.error('boom')</script></body></html>"""
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/missing'):
            self.send_response(404); self.end_headers(); return
        b = PAGE.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
HTTPServer(('127.0.0.1', int(os.environ['PORT'])), H).serve_forever()
