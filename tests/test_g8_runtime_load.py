"""G8, the runtime and load gate (the owner, 2026-11-16, stage F).

Real servers run here: each case is a small product (app.py + .omni/project.json) that is written to a temporary
directory and started by the gate's own script, exactly as the sandbox would; the request goes through the real
sandbox request policy (validate_snapshot, validate_command) before it runs. Only the transport to the remote
sandbox is replaced by a local process."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import runtime_load as R
from omni_prod.autonomous_core import ExecutionReport
from omni_prod.sandbox_request_policy import validate_command, validate_snapshot
from omni_prod.skill_units import gate as G

PORT = 18473
MANIFEST = json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'],
                       'port': PORT, 'health_path': '/'})
_HEAD = '''
import os, sys, time
from http.server import BaseHTTPRequestHandler, %(server)s
PAGE = ("<!doctype html><html lang='he' dir='rtl'><body><h1>אטליז</h1>" + "<p>בשר טרי</p>" * 40 + "</body></html>").encode()
COUNT = [0]
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        COUNT[0] += 1
%(body)s
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE))); self.end_headers(); self.wfile.write(PAGE)
%(server)s(("0.0.0.0", int(os.environ["PORT"])), H).serve_forever()
'''


def app(body='        pass', server='ThreadingHTTPServer'):
    return {'app.py': _HEAD % {'body': body, 'server': server}, '.omni/project.json': MANIFEST}


GOOD = app()
CRASHES = app('        if COUNT[0] > 20: os._exit(3)')                     # dies in the middle of the load
ERRORS = app('        if COUNT[0] % 4 == 0:\n            self.send_error(500); return')
SLOW = app(f'        time.sleep({R.P95_LIMIT_MS / 1000 + 0.6})')            # every answer over the limit
ONE_AT_A_TIME = app('        time.sleep(0.4)', server='HTTPServer')     # fine alone, queues when six ask at once
NEVER_STARTS = {'app.py': 'import sys; sys.exit(2)\n', '.omni/project.json': MANIFEST}


class LocalSandbox:
    """The inner executor: passes, and runs a staged script in a temporary copy of the repository."""
    def __init__(self):
        self.runs = []

    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'ok')

    def _run(self, repository, argv, build_id, profile='default'):
        validate_snapshot(repository)                                       # the real request policy, unchanged
        validate_command(argv, build_id=build_id, profile=profile, repository=repository)
        self.runs.append(argv)
        with tempfile.TemporaryDirectory() as root:
            for path, text in repository.items():
                target = Path(root) / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding='utf-8')
            done = subprocess.run([sys.executable, *argv[1:]], cwd=root, capture_output=True, text=True,
                                  timeout=R.WALL_SECONDS + 30)
        return {'returncode': done.returncode, 'stdout': done.stdout, 'stderr': done.stderr}


def run(repo, mode='warn'):
    gate = R.RuntimeLoadExecutor(LocalSandbox(), mode)
    return gate, gate.execute(repository=repo, spec=None)


NESTED = os.environ.get('OMNI_M4_ACCEPTANCE_W_NESTED') == '1'   # tests/test_m4_acceptance.py re-runs the suite in 300 s


@unittest.skipIf(NESTED, 'real servers: run once in the main suite, not again in the time-bounded nested run')
class OnRealServers(unittest.TestCase):
    def test_a_healthy_product_answers_every_request_and_passes(self):
        gate, report = run(GOOD, 'block')
        self.assertTrue(report.passed)
        last = gate.last_load
        self.assertEqual((last['status'], last['findings']), ('pass', []))
        m = last['measured']
        self.assertEqual((m['requests'], m['errors'], m['alive'], m['started']), (R.REQUESTS, 0, True, True))
        self.assertLessEqual(m['p95_ms'], R.P95_LIMIT_MS)
        if m['rss_kb'] is None:
            self.assertIn('NOT_RUN', last['memory'])
        else:
            self.assertLess(m['rss_kb'], R.RSS_LIMIT_KB)

    def test_a_server_that_dies_under_load_is_found(self):
        gate, report = run(CRASHES, 'block')
        self.assertFalse(report.passed)
        codes = {f['code'] for f in gate.last_load['findings']}
        self.assertIn('RUNTIME_CRASHED', codes)
        self.assertIn('LOAD_ERRORS', codes)
        self.assertTrue(all(f.acceptance_id == R.ACCEPTANCE_ID for f in report.failures))
        self.assertIn('never exit the process', ' '.join(f.message for f in report.failures))

    def test_failed_answers_are_found(self):
        gate, report = run(ERRORS, 'block')
        self.assertEqual({f['code'] for f in gate.last_load['findings']}, {'LOAD_ERRORS'})
        self.assertGreater(gate.last_load['measured']['errors'], 5)

    def test_a_server_that_never_starts_is_said(self):
        gate, report = run(NEVER_STARTS, 'block')
        self.assertFalse(report.passed)
        self.assertEqual([f['code'] for f in gate.last_load['findings']], ['LOAD_NOT_STARTED'])

    def test_in_warn_mode_the_build_goes_on_and_the_finding_is_recorded(self):
        with self.assertLogs(R.__name__, level='INFO') as logs:
            gate, report = run(ERRORS, 'warn')
        self.assertTrue(report.passed)
        self.assertEqual((gate.last_load['status'], gate.last_load['mode']), ('fail', 'warn'))
        self.assertTrue(any('G8_LOAD mode=warn status=fail' in line for line in logs.output))

    def test_the_script_travels_as_a_file_through_the_real_request_policy(self):
        gate, _ = run(GOOD)
        (argv,) = gate._inner.runs
        self.assertEqual(argv, ('python', '.omni/_sandbox/runtime_load.py'))


@unittest.skipIf(NESTED, 'real servers: run once in the main suite, not again in the time-bounded nested run')
class SlowAndQueued(unittest.TestCase):
    def test_a_slow_product_is_found_by_the_real_measurement(self):
        gate, report = run(SLOW, 'block')
        codes = {f['code'] for f in gate.last_load['findings']}
        self.assertIn('LOAD_SLOW', codes)
        self.assertGreater(gate.last_load['measured']['p95_ms'], R.P95_LIMIT_MS)


    def test_a_server_that_answers_one_visitor_at_a_time_is_found_because_six_ask_at_once(self):
        gate, report = run(ONE_AT_A_TIME, 'block')
        m = gate.last_load['measured']
        self.assertIn('LOAD_SLOW', {f['code'] for f in gate.last_load['findings']}, m)
        self.assertGreater(m['p95_ms'], R.P95_LIMIT_MS)                    # each answer takes 0.4 s; the queue makes it 2 s+
        self.assertIn('concurrently', ' '.join(f.message for f in report.failures) + R._FIX['LOAD_ERRORS'])



if __name__ == '__main__':
    unittest.main()
