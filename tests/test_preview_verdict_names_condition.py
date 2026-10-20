"""The preview verdict names WHICH condition failed (paid run 39473090833, 2026-10-20).

A 738-char page failed condition (b) -- no interactive control -- but the message showed only character counts, so
the repairer (and we) read it as "too short". The smoke script runs for real here: the real
RemoteSandboxRepositoryExecutor._run, the stub runner from test_sandbox_callers_real_policy executing it in a
subprocess against a tiny app that serves PAGE.
"""
import json
import os
import sys
import unittest
from types import SimpleNamespace

from omni_prod.preview_smoke import PreviewReadyExecutor
from tests.test_sandbox_callers_real_policy import Inner, StubRunner

APP = r'''
import http.server, os
PAGE = %r
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b = PAGE.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), H).serve_forever()
'''
SPEC = SimpleNamespace(acceptance=[SimpleNamespace(id='A1')], requirements=[])
HEAD = '<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="UTF-8"><title>תורים</title></head><body>'


def repo(page):
    manifest = {"schema_version": 2, "runtime": "python:3.11-slim", "start": [sys.executable, "app.py"],
                "port": 19000 + os.getpid() % 900, "health_path": "/"}
    return {'app.py': APP % page, '.omni/project.json': json.dumps(manifest)}


def verdict(page):
    ex = PreviewReadyExecutor(Inner(StubRunner()))
    report = ex.execute(repository=repo(page), spec=SPEC)
    return report, ' '.join(f.message + ' ' + (f.evidence or '') for f in report.failures)


class PreviewVerdictNamesTheCondition(unittest.TestCase):
    def test_a_long_page_without_controls_fails_b_only(self):          # the shape of run 39473090833
        report, text = verdict(HEAD + '<h1>תורים למספרה</h1>' + '<p>ברוכים הבאים למערכת התורים.</p>' * 20 + '</body></html>')
        self.assertFalse(report.passed)
        self.assertIn('(b) no interactive control', text)
        self.assertNotIn('(a) too short', text)

    def test_a_short_page_with_a_button_fails_a_only(self):
        report, text = verdict(HEAD + '<button>הוסף</button></body></html>')
        self.assertFalse(report.passed)
        self.assertIn('(a) too short', text)
        self.assertNotIn('(b) no interactive control', text)

    def test_both_are_named_when_both_fail(self):
        report, text = verdict(HEAD + '<h1>OK</h1></body></html>')
        self.assertIn('(a) too short', text)
        self.assertIn('(b) no interactive control', text)

    def test_a_real_interface_still_passes(self):
        rows = ''.join(f'<tr><td>תור {i}</td><td><button>ביטול</button></td></tr>' for i in range(12))
        report, _ = verdict(HEAD + '<form><input name="n"><button>קבע תור</button></form><table>' + rows + '</table></body></html>')
        self.assertTrue(report.passed)


if __name__ == '__main__':
    unittest.main()
