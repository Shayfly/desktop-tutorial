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


class _Site(BaseHTTPRequestHandler):
    """Answers like production (investor_app.py): register creates the account or, for an existing one with the right
    password, logs it in (existing_account); a wrong password is 409; /me needs the session; logout revokes it."""
    accounts = {}
    sessions = {}
    revoked = []

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
        token_in = self.headers.get('Cookie', '').partition('148ai_session=')[2]
        if self.path == '/api/v28/auth/register':
            email, password = body['email'], body['password']
            known = _Site.accounts.get(email)
            if known and known[0] != password:
                return self._send(409, {'detail': 'account already exists'})
            existing = known is not None
            if not existing:
                known = (password, FOUNDER if email.startswith('founder') else f'usr_{len(_Site.accounts) + 1}')
                _Site.accounts[email] = known
            token = f'tok-{len(_Site.sessions) + len(_Site.revoked) + 1}'
            _Site.sessions[token] = known[1]
            return self._send(200, {'token': token, **({'existing_account': True} if existing else {})})
        if self.path == '/api/v28/auth/logout':
            _Site.revoked.append(token_in)
            _Site.sessions.pop(token_in, None)
            return self._send(200, {'revoked': True})
        self._send(404, {})

    def do_GET(self):
        token = self.headers.get('Cookie', '').partition('148ai_session=')[2]
        account = _Site.sessions.get(token) if self.path == '/api/v28/me' else None
        self._send(*((200, {'id': account, 'email': 'shop@example.com'}) if account else (401, {'detail': 'invalid'})))

    def log_message(self, *a):
        pass


class LoggingInByItself(unittest.TestCase):
    """2026-11-21: with CUSTOMER_TEST_EMAIL and CUSTOMER_TEST_PASSWORD the check logs in fresh every run (a stored
    session expires after 7 days), through the real HTTP client against a server that answers like production."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), _Site)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        _Site.accounts.clear(), _Site.sessions.clear(), _Site.revoked.clear()

    def run_main(self, email=None, password=None, stored=None):
        env = {'BASE_URL': self.base}
        out = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=False), contextlib.redirect_stdout(out):
            for name, value in ((C.EMAIL_VAR, email), (C.PASSWORD_VAR, password), (C.STORED_SESSION_VAR, stored)):
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            code = C.main()
        return code, out.getvalue()

    def test_the_first_run_creates_the_account_and_revokes_its_session(self):
        code, out = self.run_main('shop+test@example.com', 'S3cret-only-for-tests')
        self.assertEqual(code, 0, out)
        self.assertIn('PASS account usr_1', out)
        self.assertIn('the account was created on this run', out)
        self.assertIn('the session was revoked', out)
        self.assertEqual(_Site.sessions, {})                       # nothing left open on production
        self.assertEqual(len(_Site.revoked), 1)

    def test_a_later_run_logs_in_to_the_same_account(self):
        _Site.accounts['shop+test@example.com'] = ('S3cret-only-for-tests', 'usr_existing')
        _Site.sessions['tok-old'] = 'usr_existing'                 # an earlier session of the same account
        code, out = self.run_main('shop+test@example.com', 'S3cret-only-for-tests')
        self.assertEqual(code, 0, out)
        self.assertIn('PASS account usr_existing', out)
        self.assertNotIn('created on this run', out)

    def test_a_wrong_password_fails_out_loud(self):
        _Site.accounts['shop+test@example.com'] = ('the-right-one', 'usr_existing')
        code, out = self.run_main('shop+test@example.com', 'a-wrong-one')
        self.assertEqual(code, 1)
        self.assertIn('::error title=customer session UNAUTHORIZED::the test customer already exists', out)
        self.assertIn('does not match', out)

    def test_the_founder_is_refused_and_its_session_still_revoked(self):
        code, out = self.run_main('founder@example.com', 'whatever-1')
        self.assertEqual(code, 1)
        self.assertIn('customer session FOUNDER', out)
        self.assertEqual(_Site.sessions, {})
        self.assertEqual(len(_Site.revoked), 1)

    def test_only_one_of_the_two_secrets_is_a_readable_failure(self):
        for email, password in (('shop+test@example.com', None), (None, 'S3cret-only-for-tests')):
            with self.subTest(email=bool(email)):
                code, out = self.run_main(email, password)
                self.assertEqual(code, 1)
                self.assertIn('customer session MISSING::only one of CUSTOMER_TEST_EMAIL and CUSTOMER_TEST_PASSWORD', out)

    def test_the_login_is_preferred_over_a_stored_session(self):
        code, out = self.run_main('shop+test@example.com', 'S3cret-only-for-tests', stored=state('tok-expired'))
        self.assertEqual(code, 0, out)
        self.assertIn('(logged in fresh', out)

    def test_nothing_set_says_how_to_fix_it_with_both_ways(self):
        code, out = self.run_main()
        self.assertEqual(code, 1)
        for name in ('CUSTOMER_TEST_EMAIL', 'CUSTOMER_TEST_PASSWORD', 'CUSTOMER_STORAGE_STATE', 'storage_state'):
            self.assertIn(name, out)

    def test_neither_the_address_nor_the_password_nor_the_token_is_printed(self):
        _, out = self.run_main('shop+test@example.com', 'S3cret-only-for-tests')
        for secret in ('shop+test', 'S3cret-only-for-tests', 'tok-1'):
            self.assertNotIn(secret, out)
        _Site.accounts['shop+test@example.com'] = ('the-right-one', 'usr_existing')
        _, out = self.run_main('shop+test@example.com', 'a-wrong-one')
        for secret in ('shop+test', 'a-wrong-one', 'the-right-one'):
            self.assertNotIn(secret, out)


class TheJob(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding='utf-8')

    def test_the_job_gives_the_secret_to_the_check_and_cannot_skip(self):
        self.assertIn('CUSTOMER_STORAGE_STATE: ${{ secrets.CUSTOMER_STORAGE_STATE }}', self.text)
        self.assertIn('run: python3 scripts/customer_session_check.py', self.text)
        self.assertIn('CUSTOMER_TEST_EMAIL: ${{ secrets.CUSTOMER_TEST_EMAIL }}', self.text)
        self.assertIn('CUSTOMER_TEST_PASSWORD: ${{ secrets.CUSTOMER_TEST_PASSWORD }}', self.text)
        for skip in ('continue-on-error', 'if:', '|| true', 'exit 0'):
            self.assertNotIn(skip, self.text)

    def test_the_job_runs_by_itself_every_day(self):
        self.assertRegex(self.text, r"schedule:\n\s+- cron: '\d+ \d+ \* \* \*'")
        self.assertIn('workflow_dispatch', self.text)
        self.assertTrue(re.search(r'BASE_URL: https://148aiv28\.vercel\.app', self.text))


if __name__ == '__main__':
    unittest.main()
