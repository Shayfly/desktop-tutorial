"""Tiny stdlib web products used to prove the browser check both ways (local
tests and the deploy probe). `feedback_bug=True` reproduces the founder's
library defect: the status message is hidden after its first use and never
shown again. `dead_form=True` has a form whose submit does nothing.
`js_error=True` throws on load."""
from __future__ import annotations

import json

_APP = r'''
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
ITEMS = []
PAGE = """<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><title>Items</title>
<style>.banner{display:none;padding:8px}.banner.ok{display:block;background:#dfd}</style></head><body>
<div id="banner" class="banner"></div>
<form id="addForm"><label>שם <input id="name" name="name" required></label>
<label>כמות <input id="qty" name="qty" type="number" min="1" max="9" required></label>
<button type="submit">הוסף</button></form>
<ul id="list"></ul>
<script>
%(js_error)s
function show(msg){const b=document.getElementById('banner');%(reset)s b.textContent=msg;b.className='banner ok';
  setTimeout(()=>{b.style.display='none';b.className='banner';},3000);}
async function load(){const r=await fetch('/items');const items=await r.json();
  document.getElementById('list').innerHTML='';for(const it of items){const li=document.createElement('li');li.textContent=it.name+' '+it.qty;document.getElementById('list').append(li);}}
document.getElementById('addForm').addEventListener('submit',async e=>{e.preventDefault();%(dead)s
  const r=await fetch('/items',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name:document.getElementById('name').value,qty:Number(document.getElementById('qty').value)})});
  if(r.ok){show('נוסף');load();}});
load();
</script></body></html>"""
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype):
        b = body.encode("utf-8"); self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == "/items": return self._send(200, json.dumps(ITEMS), "application/json")
        return self._send(200, PAGE, "text/html; charset=utf-8")
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); d = json.loads(self.rfile.read(n) or b"{}")
        ITEMS.append({"name": str(d.get("name", "")), "qty": int(d.get("qty") or 0)})
        return self._send(201, json.dumps(ITEMS[-1]), "application/json")
HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), H).serve_forever()
'''


def fixture_repository(*, feedback_bug: bool = False, dead_form: bool = False, js_error: bool = False,
                       port: int = 8000) -> dict[str, str]:
    app = _APP % {
        'reset': '' if feedback_bug else "b.style.display='';",
        'dead': 'return;' if dead_form else '',
        'js_error': 'undefinedFunctionCall();' if js_error else '',
    }
    manifest = {'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'],
                'port': port, 'health_path': '/'}
    return {'app.py': app, '.omni/project.json': json.dumps(manifest)}
