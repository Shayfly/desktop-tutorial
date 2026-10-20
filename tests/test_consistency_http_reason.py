"""Consistency gate: an http.server reason phrase that latin-1 cannot encode (paid run 39473090833, 2026-10-20).

`self.send_error(404, "לא נמצא")` crashed the handler (UnicodeEncodeError), the connection closed without a response,
and the behaviour check saw RemoteDisconnected on POST and DELETE for three repair rounds. The first test proves the
crash on the real http.server; the rest prove the gate reports it before any sandbox runs.
"""
import http.client
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

from omni_prod.autonomous_core import ExecutionReport
from omni_prod.consistency_gate import CONSISTENCY_FAILURE_ID, ConsistencyGateExecutor, scan

APP = '''import http.server, os
class H(http.server.BaseHTTPRequestHandler):
    def do_DELETE(self):
        self.send_error(404, %s)
    def log_message(self, *a): pass
if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", int(os.environ["PORT"])), H).serve_forever()
'''


def app(message_src):
    return {'app.py': APP % message_src, '.omni/project.json': json.dumps({})}


def findings(repo):
    return [f for f in scan(repo).findings if f.check == 'http_reason']


class TheCrashIsReal(unittest.TestCase):
    def test_hebrew_reason_closes_the_connection_without_a_response(self):
        port = 20000 + os.getpid() % 900
        with tempfile.TemporaryDirectory() as root:
            open(os.path.join(root, 'app.py'), 'w', encoding='utf-8').write(APP % '"לא נמצא"')
            proc = subprocess.Popen([sys.executable, 'app.py'], cwd=root, env=dict(os.environ, PORT=str(port)),
                                    stderr=subprocess.PIPE)
            try:
                for _ in range(50):
                    try:
                        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
                        conn.request('DELETE', '/api/appointments/1')
                        break
                    except ConnectionRefusedError:
                        time.sleep(0.1)
                with self.assertRaises((http.client.RemoteDisconnected, ConnectionResetError)):
                    conn.getresponse()
            finally:
                proc.terminate()
                err = proc.communicate(timeout=5)[1].decode('utf-8', 'replace')
        self.assertIn("UnicodeEncodeError: 'latin-1' codec can't encode", err)


class GateReportsItBeforeTheSandbox(unittest.TestCase):
    def test_hebrew_reason_phrase_is_a_blocking_finding_with_file_and_line(self):
        [f] = findings(app('"לא נמצא"'))
        self.assertTrue(f.blocking)
        self.assertEqual((f.path, f.line), ('app.py', 4))
        self.assertIn("explain='לא נמצא'", f.fix)

    def test_keyword_message_and_fstring_literal_parts(self):
        self.assertEqual(len(findings(app('message="שגיאה"'))), 1)
        self.assertEqual(len(findings(app('f"תור {1} לא נמצא"'))), 1)
        r = {'app.py': APP % '"x"' + '\n    # also\nclass G(http.server.BaseHTTPRequestHandler):\n'
                                       '    def do_GET(self):\n        self.send_response(400, "קלט שגוי")\n'}
        line = next(i for i, l in enumerate(r['app.py'].splitlines(), 1) if 'קלט שגוי' in l)
        self.assertEqual([f.line for f in findings(r)], [line])

    def test_what_is_fine_is_not_reported(self):
        for src in ('"Not Found"', 'None', 'explain="לא נמצא"', 'msg', 'f"Not found: {name}"'):
            self.assertEqual(findings(app(src)), [], src)       # ascii, body text, or computed (never guessed)
        self.assertEqual(findings({'tests/test_app.py': APP % '"לא נמצא"'}), [])

    def test_the_executor_returns_the_failure_without_running_the_sandbox(self):
        class Sandbox:
            ran = False

            def execute(self, *, repository, spec):
                Sandbox.ran = True
                return ExecutionReport(True, (), 'ok')
        report = ConsistencyGateExecutor(Sandbox()).execute(repository=app('"לא נמצא"'), spec=None)
        self.assertFalse(report.passed)
        self.assertFalse(Sandbox.ran)
        self.assertEqual(report.failures[0].acceptance_id, CONSISTENCY_FAILURE_ID)
        self.assertIn('consistency (http_reason): app.py:4', report.failures[0].message)


if __name__ == '__main__':
    unittest.main()
