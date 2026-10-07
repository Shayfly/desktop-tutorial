"""The product must start for preview before a build is accepted.

Golden E2E #1 (2026-10-07): the football site passed tests/quality/review and
then failed preview with "preview contract requires schema_version 2, got
None". The smoke script is executed for real here (subprocess in a temp dir,
standing in for the sandbox's /run).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from omni_prod.autonomous_core import ExecutionReport
from omni_prod.preview_smoke import PREVIEW_FAILURE_ID, PreviewReadyExecutor

CONTRACT = {'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': [sys.executable, 'app.py'],
            'port': 0, 'health_path': '/', 'build': [], 'verify': [{'name': 't', 'argv': ['true'], 'acceptance_ids': ['A1']}]}
GOOD_APP = '''import os
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"league")
    def log_message(self, *a): pass
HTTPServer(("0.0.0.0", int(os.environ["PORT"])), H).serve_forever()
'''
CRASHING_APP = 'import sqlite3\nsqlite3.connect("league.db").execute("create table t(x)")\nraise SystemExit("cannot write")\n'


def _free_port():
    import socket
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


class _LocalSandbox:
    """execute() passes; _run() really runs argv in a temp copy of the repository."""
    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'tests ok')

    def _run(self, repository, argv, build_id):
        with tempfile.TemporaryDirectory() as d:
            for path, content in repository.items():
                full = os.path.join(d, path); os.makedirs(os.path.dirname(full), exist_ok=True)
                open(full, 'w').write(content)
            p = subprocess.run(list(argv), cwd=d, capture_output=True, text=True, timeout=60)
            return {'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def _repo(app, **contract):
    c = dict(CONTRACT, port=_free_port(), **contract)
    return {'.omni/project.json': json.dumps(c), 'app.py': app}


class PreviewSmokeTests(unittest.TestCase):
    def setUp(self):
        self.ex = PreviewReadyExecutor(_LocalSandbox())

    def test_app_that_starts_and_answers_passes(self):
        self.assertTrue(self.ex.execute(repository=_repo(GOOD_APP), spec=None).passed)

    def test_missing_contract_is_a_repairable_failure_with_the_shape(self):
        repo = {'.omni/project.json': json.dumps({'build': [], 'verify': CONTRACT['verify']}), 'app.py': GOOD_APP}
        report = self.ex.execute(repository=repo, spec=None)
        self.assertFalse(report.passed)
        f = report.failures[0]
        self.assertEqual(f.acceptance_id, PREVIEW_FAILURE_ID)
        self.assertIn('schema_version', f.message)
        self.assertIn('"start"', f.evidence)

    def test_app_that_crashes_reports_why(self):
        report = self.ex.execute(repository=_repo(CRASHING_APP), spec=None)
        self.assertFalse(report.passed)
        self.assertIn('server exited', report.failures[0].message)
        self.assertIn('cannot write', report.failures[0].evidence)


if __name__ == '__main__':
    unittest.main()
