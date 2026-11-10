"""Work order 001 (Michael 2026-11-10), mapped to 148AI: hardened sign-in in built products, behind site_auth_v2.

1. IDENTITY (blocking): with the flag off, every instruction, prompt, probe, sandbox script and arm-brief derivation
   hashes to the digest recorded at baseline 2c1d6cb. Model output is not hashed -- it is not deterministic.
2. The hardened acceptance against a REAL stdlib app: a correct sign-in passes; each broken variant fails exactly on
   its defect (cookie without HttpOnly, no rotation, different errors, no 429 on the 6th login).
3. The source probe: plain hashes, credentials in logs and in URLs block; scrypt passes.
"""
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASELINE_SHA = '2c1d6cb4cb0565df8f6fc0634218c1f98ea7fb49'
BASELINE_DIGEST = '728eb139efa6f3eab28ae603ede3b5b3fa9b78029642981dfdd169ba008b9a16'


def _digest(flag: str) -> str:
    env = dict(os.environ, OMNI_SITE_AUTH_V2=flag)
    out = subprocess.run([sys.executable, '-m', 'omni_prod.pipeline_identity'], env=env, capture_output=True,
                         text=True, check=True)
    return out.stdout.strip()


class Identity(unittest.TestCase):
    def test_flag_off_is_the_baseline_byte_for_byte(self):
        got = _digest('0')
        if os.getenv('GITHUB_ACTIONS'):
            print(f'::notice title=site_auth_v2 identity::flag off digest {got} (baseline {BASELINE_SHA[:7]}: '
                  f'{BASELINE_DIGEST})')
        self.assertEqual(got, BASELINE_DIGEST, 'with site_auth_v2 off the pipeline must be the baseline')

    def test_flag_on_changes_the_pipeline(self):
        self.assertNotEqual(_digest('1'), BASELINE_DIGEST)

    def test_default_is_off(self):
        env = {k: v for k, v in os.environ.items() if k != 'OMNI_SITE_AUTH_V2'}
        out = subprocess.run([sys.executable, '-c', 'from omni_prod import feature_flags as f; print(f.SITE_AUTH_V2)'],
                             env=env, capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout.strip(), 'False')

    def test_the_flag_is_read_in_one_place(self):
        hits = []
        for root, _, files in os.walk('omni_prod'):
            for f in files:
                if f.endswith('.py'):
                    p = os.path.join(root, f)
                    if 'OMNI_SITE_AUTH_V2' in open(p, encoding='utf-8').read():
                        hits.append(p)
        self.assertEqual(hits, [os.path.join('omni_prod', 'feature_flags.py')])


# ------------------------------------------------------------------ a real product with sign-in (stdlib only)
def make_app(*, httponly=True, rotate=True, uniform=True, rate_limit=True):
    users, sessions, hits = {}, {}, {}

    def kdf(pw, salt):
        return hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=5, dklen=32)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, status, body, cookie=None):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            if cookie:
                self.send_header('Set-Cookie', cookie)
            if status == 429:
                self.send_header('Retry-After', '60')
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            n = int(self.headers.get('Content-Length') or 0)
            return json.loads(self.rfile.read(n) or b'{}')

        def _limited(self):
            if not rate_limit:
                return False
            ip = self.client_address[0]
            now = time.time()
            hits[ip] = [t for t in hits.get(ip, []) if now - t < 60] + [now]
            return len(hits[ip]) > 5

        def _session(self, user):
            token = secrets.token_urlsafe(32) if rotate or user not in [u for u, _ in sessions.values()] else \
                next(t for t, (u, _) in sessions.items() if u == user)
            sessions[token] = (user, time.time())
            flags = '; HttpOnly' if httponly else ''
            return f'__Host-sid={token}; Path=/; Secure{flags}; SameSite=Lax; Max-Age=2592000'

        def do_POST(self):
            body = self._body()
            if self.path == '/auth/signup':
                email = str(body.get('email', '')).lower()
                if email in users:
                    return self._json(409, {'error': 'exists'})
                salt = os.urandom(16)
                users[email] = (salt, kdf(str(body.get('password', '')), salt))
                return self._json(201, {'ok': True}, self._session(email))
            if self.path == '/auth/login':
                if self._limited():
                    return self._json(429, {'error': 'יותר מדי ניסיונות'})
                email = str(body.get('email', '')).lower()
                rec = users.get(email)
                if rec is None:
                    return self._json(401, {'error': 'אימייל או סיסמה שגויים' if uniform else 'אין משתמש כזה'})
                if not hmac.compare_digest(kdf(str(body.get('password', '')), rec[0]), rec[1]):
                    return self._json(401, {'error': 'אימייל או סיסמה שגויים'})
                return self._json(200, {'ok': True}, self._session(email))
            self._json(404, {'error': 'not found'})

        def do_GET(self):
            sid = None
            for part in (self.headers.get('Cookie') or '').split(';'):
                k, _, v = part.strip().partition('=')
                if k == '__Host-sid':
                    sid = v
            if self.path == '/auth/me':
                return self._json(200, {'user': sessions[sid][0]}) if sid in sessions else self._json(401, {})
            self._json(200, {'ok': True})

    server = ThreadingHTTPServer(('127.0.0.1', 0), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


PLAN = [{'id': 'visitor', 'steps': [
    {'id': 's1', 'kind': 'auth', 'acceptance_ids': ['A1'], 'method': 'POST', 'path': '/auth/signup',
     'json': {'email': 'dana@example.com', 'password': 'Correct-Horse-9'}, 'expect_status': 201},
    {'id': 's2', 'kind': 'auth', 'acceptance_ids': ['A1'], 'method': 'POST', 'path': '/auth/login',
     'json': {'email': 'dana@example.com', 'password': 'Correct-Horse-9'}, 'expect_status': 200},
    {'id': 's3', 'kind': 'auth', 'acceptance_ids': ['A1'], 'method': 'GET', 'path': '/auth/me', 'expect_status': 200},
]}]
CONTRACT = {'acceptance': [{'id': 'A1', 'text': 'sign-in'}]}


def hardening(**app_kwargs) -> dict:
    from omni_prod.web_saas_auth_hardening import HardenedAcceptanceRunner
    server = make_app(**app_kwargs)
    try:
        runner = HardenedAcceptanceRunner(required_kinds=('auth',), build_contract=None)
        report = runner.verify({'preview_url': f'http://127.0.0.1:{server.server_port}'}, CONTRACT, PLAN)
    finally:
        server.shutdown()
    return {c.step_id: (c.passed, c.detail) for c in report.checks if c.kind == 'auth_hardening'} | \
        {'_status': report.status, '_summary': report.summary}


class HardenedAcceptance(unittest.TestCase):
    def test_a_correct_sign_in_passes_every_check(self):
        r = hardening()
        failed = {k: v for k, v in r.items() if not k.startswith('_') and not v[0]}
        self.assertEqual(failed, {})
        self.assertTrue({'auth_cookie_set', 'auth_cookie_flags', 'auth_token_rotation', 'auth_uniform_error',
                         'auth_rate_limit'} <= set(r))
        # (the rest of the floor -- data_create etc. -- is the base runner's business; this plan only signs in)
        self.assertNotIn('sign-in hardening failed', r['_summary'])

    def test_cookie_without_httponly_fails(self):
        r = hardening(httponly=False)
        self.assertFalse(r['auth_cookie_flags'][0])
        self.assertIn('httponly', r['auth_cookie_flags'][1])
        self.assertEqual(r['_status'], 'FAIL')
        self.assertIn('sign-in hardening failed', r['_summary'])

    def test_no_rotation_fails(self):
        r = hardening(rotate=False)
        self.assertFalse(r['auth_token_rotation'][0])

    def test_different_errors_for_unknown_email_fail(self):
        r = hardening(uniform=False)
        self.assertFalse(r['auth_uniform_error'][0])

    def test_no_rate_limit_fails(self):
        r = hardening(rate_limit=False)
        self.assertFalse(r['auth_rate_limit'][0])
        self.assertIn('no 429', r['auth_rate_limit'][1])

    def test_a_plan_without_a_login_step_cannot_pass(self):
        from omni_prod.web_saas_auth_hardening import HardenedAcceptanceRunner
        server = make_app()
        try:
            plan = [{'id': 'v', 'steps': [PLAN[0]['steps'][0]]}]
            report = HardenedAcceptanceRunner(required_kinds=('auth',)).verify(
                {'preview_url': f'http://127.0.0.1:{server.server_port}'}, CONTRACT, plan)
        finally:
            server.shutdown()
        self.assertEqual(report.status, 'FAIL')
        self.assertIn('auth_login_found', report.summary)

    def test_hardening_runs_inside_the_shipped_runner_source(self):
        # the sandbox execs web_saas_acceptance.py + this module as ONE source with no omni_prod imports
        import types
        src = open('omni_prod/web_saas_acceptance.py', encoding='utf-8').read() + '\n\n' + \
            open('omni_prod/web_saas_auth_hardening.py', encoding='utf-8').read()
        mod = types.ModuleType('wsa')
        mod.__dict__['__name__'] = 'wsa'
        sys.modules['wsa'] = mod
        exec(compile(src, 'web_saas_acceptance.py', 'exec'), mod.__dict__)
        server = make_app(rate_limit=False)
        try:
            report = mod.HardenedAcceptanceRunner(required_kinds=('auth',)).verify(
                {'preview_url': f'http://127.0.0.1:{server.server_port}'}, CONTRACT, PLAN)
        finally:
            server.shutdown()
        self.assertEqual(report.status, 'FAIL')
        self.assertIn('auth_rate_limit', report.summary)

    def test_content_only_products_are_not_attacked(self):
        from omni_prod.web_saas_auth_hardening import HardenedAcceptanceRunner
        runner = HardenedAcceptanceRunner(build_contract={'prompt': 'Sign-in: NONE', 'roles': ['user']})
        self.assertIn('auth', runner.not_required_kinds)


class SourceProbe(unittest.TestCase):
    APP = ('from http.server import BaseHTTPRequestHandler\nimport hashlib, os\n'
           'ROUTES = ["/auth/login", "/auth/signup"]\n')

    def found(self, code):
        from omni_prod.skills_runtime import _auth_source_rules
        return [f.problem for f in _auth_source_rules({'app.py': self.APP + code}, {})]

    def test_scrypt_passes(self):
        self.assertEqual(self.found('h = hashlib.scrypt(password.encode(), salt=s, n=2**14, r=8, p=5)\n'), [])

    def test_plain_hash_blocks(self):
        self.assertTrue(any('memory-hard' in p for p in self.found('h = hashlib.sha256(password.encode()).hexdigest()\n')))

    def test_credentials_in_logs_and_urls_block(self):
        found = self.found('h = hashlib.scrypt(password.encode(), salt=s, n=2**14, r=8, p=5)\n'
                           'print("login", email, password)\nurl = "/reset?token=" + t\n')
        self.assertTrue(any('log' in p for p in found))
        self.assertTrue(any('URL' in p for p in found))

    def test_products_without_sign_in_are_not_judged(self):
        from omni_prod.skills_runtime import _auth_source_rules
        self.assertEqual(_auth_source_rules({'app.py': 'print("hello")'}, {}), [])


class FormCheckUnits(unittest.TestCase):
    def test_parse_and_applicability(self):
        from omni_prod.auth_form_check import has_sign_in, parse
        self.assertTrue(has_sign_in({'page.py': '<input type="password" name="pw">'}))
        self.assertFalse(has_sign_in({'page.py': '<input type="email">'}))
        self.assertEqual(parse('x\nOMNI_AUTH_FORM {"page": "/login", "findings": []}')['page'], '/login')
        self.assertIsNone(parse('nothing'))


if __name__ == '__main__':
    unittest.main()
