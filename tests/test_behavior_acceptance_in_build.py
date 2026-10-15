"""Behavioural acceptance runs inside the build and feeds repair
(autonomous completion directive §1, real-server finding 2026-10-09)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

from omni_prod.autonomous_core import ExecutionReport
from omni_prod.behavior_acceptance import BEHAVIOR_FAILURE_ID, BehaviorAcceptanceExecutor, find_in_chain

APP = r'''
import json, os, tempfile, http.server
from datetime import date
DATA = os.path.join(os.environ.get("DATA_DIR") or os.environ.get("OMNI_SCRATCH_DIR") or tempfile.gettempdir(), "items.json")
def load():
    try:
        return json.load(open(DATA))
    except Exception:
        return []
class H(http.server.BaseHTTPRequestHandler):
    def _j(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == "/api/items": return self._j(200, load())
        b = b"<!doctype html><html><body><h1>Bookings</h1><form><input name=n><button>Add</button></form></body></html>"
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if BUG and body.get("date", "") >= date.today().isoformat():
            return self._j(400, {"error": "date must be in the past"})   # the injected bug
        items = load(); item = {"id": len(items) + 1, "name": body.get("name")}
        items.append(item); json.dump(items, open(DATA, "w")); self._j(201, item)
    def do_DELETE(self):
        items = [i for i in load() if str(i["id"]) != self.path.rsplit("/", 1)[-1]]
        json.dump(items, open(DATA, "w")); self._j(200, {"ok": True})
    def log_message(self, *a): print("request", *a, flush=True)
BUG = %s
http.server.ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), H).serve_forever()
'''


def repository(bug: bool, plan_steps=None) -> dict:
    steps = plan_steps or [
        {"id": "s1", "kind": "api_smoke", "acceptance_ids": ["A1"], "method": "GET", "path": "/", "expect_status": 200},
        {"id": "s2", "kind": "responsive", "acceptance_ids": ["A1"], "method": "GET", "path": "/", "expect_status": 200},
        {"id": "s3", "kind": "data_create", "acceptance_ids": ["A2"], "method": "POST", "path": "/api/items",
         "json": {"name": "יוסי", "date": "2099-01-01"}, "expect_status": 201, "capture": {"created_id": "id"}},
        {"id": "s4", "kind": "data_read", "acceptance_ids": ["A2"], "method": "GET", "path": "/api/items",
         "expect_status": 200, "expect_json_contains": [{"name": "יוסי"}]},
        {"id": "s5", "kind": "data_delete", "acceptance_ids": ["A3"], "method": "DELETE",
         "path": "/api/items/${created_id}", "expect_status": 200},
    ]
    manifest = {"schema_version": 2, "runtime": "python:3.11-slim", "start": [sys.executable, "app.py"],
                "port": 18000 + os.getpid() % 1000, "health_path": "/",
                "web_saas_acceptance": {"product_family": "managed_web_saas_v1",
                                        "required_kinds": ["api_smoke", "data_create", "data_read", "data_delete"],
                                        "personas": [{"id": "visitor", "steps": steps}]}}
    return {"app.py": APP % ("True" if bug else "False"), ".omni/project.json": json.dumps(manifest)}


class LocalSandbox:
    """Runs the in-sandbox script the way the sandbox runner does: the
    repository as the working directory, a writable /tmp."""
    def __init__(self):
        self.runs = []

    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'tests ok')

    def _run(self, repository, argv, name, profile='default'):
        self.runs.append(name)
        with tempfile.TemporaryDirectory() as root:
            for path, text in repository.items():
                full = os.path.join(root, path)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                open(full, "w", encoding="utf-8").write(text)
            p = subprocess.run(list(argv), cwd=root, capture_output=True, text=True, timeout=90)
            return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


SPEC = SimpleNamespace(acceptance=[SimpleNamespace(id="A1"), SimpleNamespace(id="A2"), SimpleNamespace(id="A3")],
                       requirements=[])
NO_LOGIN_SCOPE = {"infrastructure": [], "required_integrations": [], "user_roles": ["user"],
                  "defaults_applied": ["no_login_single_user"],
                  "prompt": "booking: add, list and cancel. Sign-in: NONE. Do not add login."}


class BehaviorAcceptanceInBuildTests(unittest.TestCase):
    def run_exec(self, repo, scope=NO_LOGIN_SCOPE):
        ex = BehaviorAcceptanceExecutor(LocalSandbox())
        ex.scope = scope
        return ex, ex.execute(repository=repo, spec=SPEC)

    def test_working_product_passes_without_auth_checks_for_a_no_login_contract(self):
        ex, report = self.run_exec(repository(bug=False))
        self.assertTrue(report.passed, ex.last_report)
        self.assertEqual(ex.last_report["status"], "PASS")
        self.assertIn("auth", ex.last_report["not_required_kinds"])

    def test_a_real_400_becomes_a_repairable_failure_with_evidence(self):
        ex, report = self.run_exec(repository(bug=True))
        self.assertFalse(report.passed)
        failure = report.failures[0]
        self.assertEqual(failure.acceptance_id, BEHAVIOR_FAILURE_ID)
        self.assertIn("POST /api/items", failure.evidence)          # what was sent
        self.assertIn("HTTP 400", failure.evidence)                  # what came back
        self.assertIn("date must be in the past", failure.evidence)  # the answer
        self.assertIn("request", failure.evidence)                   # server log tail

    def test_dropping_a_criterion_from_the_plan_does_not_pass(self):
        steps = [{"id": "s1", "kind": "api_smoke", "acceptance_ids": ["A1"], "method": "GET", "path": "/",
                  "expect_status": 200}]
        ex, report = self.run_exec(repository(bug=False, plan_steps=steps))
        self.assertFalse(report.passed)
        self.assertIn("A2", report.failures[0].evidence)

    def test_without_a_contract_the_strict_floor_applies(self):
        ex, report = self.run_exec(repository(bug=False), scope=None)
        self.assertFalse(report.passed)   # auth/role/update/integration demanded
        self.assertIn("auth", ex.last_report["missing_kinds"])

    def test_found_through_wrapper_chain(self):
        inner = BehaviorAcceptanceExecutor(LocalSandbox())

        class Wrap:
            def __init__(self, i): self._inner = i
        self.assertIs(find_in_chain(Wrap(Wrap(inner)), BehaviorAcceptanceExecutor), inner)


if __name__ == "__main__":
    unittest.main()
