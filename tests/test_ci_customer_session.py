"""Warehouse 107 (owner 2026-11-16): a CI job loads the stored customer session and fails loudly on 401.

Acceptance: a missing secret is a readable failure, not a skip. Real path: scripts/customer_session_check.py's real HTTP
client against a local HTTP server that answers like /api/v28/me (200 with an account, or 401), and the real main()
exit code and ::error line. The workflow file is read as it is committed. Runs in ci-fast (test_ci_*)."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('customer_session_check', ROOT / 'scripts' / 'customer_session_check.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
WORKFLOW = ROOT / '.github' / 'workflows' / 'customer-session.yml'
CUSTOMER, FOUNDER = 'usr_customer_test', 'usr_GCWlMxENgr9vpwph'


def state(value='tok-live', name='148ai_session', domain='127.0.0.1'):
    return json.dumps({'cookies': [{'name': name, 'value': value, 'domain': domain, 'path': '/'}], 'origins': []})


class _Me(BaseHTTPRequestHandler):
    sessions = {'tok-live': CUSTOMER, 'tok-founder': FOUNDER}
    seen: list = []

    def do_GET(self):
        cookie = self.headers.get('Cookie', '')
        _Me.seen.append((self.path, cookie))
        token = cookie.partition('148ai_session=')[2]
        account = self.sessions.get(token) if self.path == '/api/v28/me' else None
        code, body = (200, {'id': account, 'email': 'shop@example.com'}) if account else (401, {'detail': 'invalid session'})
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


class AgainstALiveServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), _Me)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def run_main(self, secret):
        env = {'BASE_URL': self.base}
        if secret is not None:
            env[C.STORED_SESSION_VAR] = secret
        out = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=False), contextlib.redirect_stdout(out):
            if secret is None:
                os.environ.pop(C.STORED_SESSION_VAR, None)
            code = C.main()
        return code, out.getvalue()

    def test_a_live_customer_session_passes(self):
        code, out = self.run_main(state())
        self.assertEqual(code, 0, out)
        self.assertIn(f'PASS account {CUSTOMER}', out)
        self.assertIn(('/api/v28/me', '148ai_session=tok-live'), _Me.seen)

    def test_a_missing_secret_is_a_readable_failure_not_a_skip(self):
        for secret in (None, '', '   '):
            with self.subTest(repr(secret)):
                code, out = self.run_main(secret)
                self.assertEqual(code, 1)
                self.assertRegex(out, r'::error title=customer session MISSING::the secret CUSTOMER_STORAGE_STATE is not set')
                self.assertIn('storage_state', out)               # says how to fix it

    def test_a_401_fails_out_loud(self):
        code, out = self.run_main(state('tok-revoked'))
        self.assertEqual(code, 1)
        self.assertIn('::error title=customer session UNAUTHORIZED::production answered 401', out)

    def test_the_founders_session_is_not_a_customer(self):
        code, out = self.run_main(state('tok-founder'))
        self.assertEqual(code, 1)
        self.assertIn('customer session FOUNDER', out)

    def test_a_secret_that_is_not_a_session_says_so(self):
        for secret, why in (('{not json', 'is not JSON'), ('{"origins": []}', 'no "cookies" list'),
                            (state(name='other'), 'no 148ai_session cookie'),
                            (state(domain='148aiv28.vercel.app'), 'no 148ai_session cookie for 127.0.0.1')):
            with self.subTest(why):
                code, out = self.run_main(secret)
                self.assertEqual(code, 1)
                self.assertIn('customer session MALFORMED', out)
                self.assertIn(why, out)

    def test_the_cookie_value_is_never_printed(self):
        for token in ('tok-live', 'tok-revoked', 'tok-founder'):
            _, out = self.run_main(state(token))
            self.assertNotIn(token, out)

    def test_no_answer_is_a_failure(self):
        with mock.patch.object(C, '_get', side_effect=OSError('refused')):
            with self.assertRaises(C.SessionProblem) as ctx:
                C.check(state(), self.base, get=C._get)
        self.assertEqual(ctx.exception.code, 'UNEXPECTED')


class TheJob(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding='utf-8')

    def test_the_job_gives_the_secret_to_the_check_and_cannot_skip(self):
        self.assertIn('CUSTOMER_STORAGE_STATE: ${{ secrets.CUSTOMER_STORAGE_STATE }}', self.text)
        self.assertIn('run: python3 scripts/customer_session_check.py', self.text)
        for skip in ('continue-on-error', 'if:', '|| true', 'exit 0'):
            self.assertNotIn(skip, self.text)

    def test_the_job_runs_by_itself_every_day(self):
        self.assertRegex(self.text, r"schedule:\n\s+- cron: '\d+ \d+ \* \* \*'")
        self.assertIn('workflow_dispatch', self.text)
        self.assertTrue(re.search(r'BASE_URL: https://148aiv28\.vercel\.app', self.text))


if __name__ == '__main__':
    unittest.main()
