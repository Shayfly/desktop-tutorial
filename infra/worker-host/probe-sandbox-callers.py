"""Real-sandbox probe of the four in-sandbox scripts (2026-10-19). Run INSIDE a worker image on the worker host:

    docker compose run --rm --no-deps -T worker python - < infra/worker-host/probe-sandbox-callers.py

Each caller runs exactly as in a build -- its executor's execute() with the real RemoteSandboxRepositoryExecutor
(J2 request policy, HMAC, the sandbox runner on this host). No model call, no database, no spend. Prints one
`::notice`/`::warning` line per caller and exits 1 unless all four pass.
"""
import json
import os
import sys

from omni_prod.autonomous_core import ExecutionReport
from omni_prod.behavior_acceptance import BehaviorAcceptanceExecutor
from omni_prod.browser_fixtures import fixture_repository
from omni_prod.browser_probe import BrowserFlowExecutor
from omni_prod.preview_smoke import PreviewReadyExecutor
from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor
from omni_prod.visual_qa import VisualQAExecutor

APP = r'''
import json, os, http.server
DATA = os.path.join("/tmp", "items.json")
def load():
    try: return json.load(open(DATA))
    except Exception: return []
PAGE = ("<!doctype html><html lang=he dir=rtl><head><meta charset=utf-8><meta name=viewport content='width=device-width'>"
        "<title>Bookings</title></head><body><h1>הזמנות</h1><form id=f><label>שם <input name=name required></label>"
        "<button type=submit>הוסף</button></form><p id=msg role=status></p><table id=t><tr><th>שם</th><th></th></tr></table>"
        "<script>const f=document.getElementById('f'),m=document.getElementById('msg');"
        "async function r(){const d=await (await fetch('/api/items')).json();const t=document.getElementById('t');"
        "t.innerHTML='<tr><th>שם</th><th></th></tr>'+d.map(i=>'<tr><td>'+i.name.replace(/</g,'&lt;')+'</td><td><button onclick=del('+i.id+')>מחק</button></td></tr>').join('')}"
        "async function del(id){await fetch('/api/items/'+id,{method:'DELETE'});m.textContent='נמחק';r()}"
        "f.onsubmit=async e=>{e.preventDefault();const n=new FormData(f).get('name');"
        "const x=await fetch('/api/items',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({name:n})});"
        "m.textContent=x.ok?'נוסף':'שגיאה';r()};r()</script></body></html>").encode()
class H(http.server.BaseHTTPRequestHandler):
    def _j(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == "/api/items": return self._j(200, load())
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE))); self.end_headers(); self.wfile.write(PAGE)
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        items = load(); item = {"id": len(items) + 1, "name": body.get("name")}; items.append(item)
        json.dump(items, open(DATA, "w")); self._j(201, item)
    def do_DELETE(self):
        json.dump([i for i in load() if str(i["id"]) != self.path.rsplit("/", 1)[-1]], open(DATA, "w")); self._j(200, {"ok": True})
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), H).serve_forever()
'''
STEPS = [
    {"id": "s1", "kind": "api_smoke", "acceptance_ids": ["A1"], "method": "GET", "path": "/", "expect_status": 200},
    {"id": "s2", "kind": "data_create", "acceptance_ids": ["A2"], "method": "POST", "path": "/api/items",
     "json": {"name": "יוסי"}, "expect_status": 201, "capture": {"created_id": "id"}},
    {"id": "s3", "kind": "data_read", "acceptance_ids": ["A2"], "method": "GET", "path": "/api/items",
     "expect_status": 200, "expect_json_contains": [{"name": "יוסי"}]},
    {"id": "s4", "kind": "data_delete", "acceptance_ids": ["A3"], "method": "DELETE", "path": "/api/items/${created_id}",
     "expect_status": 200},
]
MANIFEST = {"schema_version": 2, "runtime": "python:3.11-slim", "start": ["python", "app.py"], "port": 8000,
            "health_path": "/", "web_saas_acceptance": {"product_family": "managed_web_saas_v1",
                                                         "required_kinds": ["api_smoke", "data_create", "data_read", "data_delete"],
                                                         "personas": [{"id": "visitor", "steps": STEPS}]}}
REPO = {"app.py": APP, ".omni/project.json": json.dumps(MANIFEST, ensure_ascii=False)}


class _A:
    def __init__(self, i): self.id = i


class _Spec:
    acceptance = [_A("A1"), _A("A2"), _A("A3")]
    requirements = []


SCOPE = {"infrastructure": [], "required_integrations": [], "user_roles": ["user"],
         "defaults_applied": ["no_login_single_user"], "prompt": "bookings: add, list, delete. No login."}


class Inner:
    def __init__(self):
        self._remote = RemoteSandboxRepositoryExecutor(RemoteSandboxConfig(
            os.environ["OMNI_SANDBOX_RUNNER_URL"], os.environ["OMNI_SANDBOX_SHARED_SECRET"], timeout_seconds=200))
        self._run = self._remote._run

    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), "inner ok")


def emit(name, ok, detail):
    text = json.dumps(detail, ensure_ascii=False, default=str)[:1500].replace("%", "%25").replace("\n", "%0A")
    print(f"::{'notice' if ok else 'warning'} title=sandbox-caller {name}::{'PASS' if ok else 'FAIL'} {text}", flush=True)
    return ok


results = []
ex = PreviewReadyExecutor(Inner())
rep = ex.execute(repository=REPO, spec=_Spec())
results.append(emit("preview_smoke", ex.last_smoke == {"status": "PASS"},
                    {"last_smoke": ex.last_smoke, "failures": [f.message[:300] for f in rep.failures]}))

seen = {}
for label, repo in (("working", fixture_repository()), ("message-bug", fixture_repository(feedback_bug=True))):
    ex = BrowserFlowExecutor(Inner())
    ex.execute(repository=repo, spec=_Spec())
    seen[label] = ex.last_probe
kinds = {k: sorted({f.get("kind") for f in (v or {}).get("findings", [])}) for k, v in seen.items()}
results.append(emit("browser_probe", (seen["working"] or {}).get("status") == "passed"
                    and kinds["message-bug"] == ["feedback_disappears"], {"kinds": kinds, "status": {k: (v or {}).get("status") for k, v in seen.items()},
                                                                           "reason": {k: (v or {}).get("reason") for k, v in seen.items()}}))

ex = BehaviorAcceptanceExecutor(Inner())
ex.scope = SCOPE
rep = ex.execute(repository=REPO, spec=_Spec())
lr = ex.last_report or {}
results.append(emit("behavior_acceptance", lr.get("status") == "PASS",
                    {"status": lr.get("status"), "summary": lr.get("summary"),
                     "failed": [c for c in (lr.get("checks") or []) if not c.get("passed")][:3],
                     "failures": [f.message[:300] for f in rep.failures]}))

ex = VisualQAExecutor(Inner())
ex.execute(repository=REPO, spec=_Spec())
lv = ex.last_visual or {}
vps = {k: {"status": v.get("status"), "reason": v.get("reason"), "counts": v.get("counts"),
           "screenshot_bytes": v.get("screenshot_bytes")} for k, v in (lv.get("viewports") or {}).items()}
results.append(emit("visual_qa", sorted(vps) == ["desktop", "mobile"] and all(v["status"] in ("PASS", "FINDINGS") for v in vps.values()),
                    {"status": lv.get("status"), "mode": lv.get("mode"), "viewports": vps}))

sys.exit(0 if all(results) else 1)
