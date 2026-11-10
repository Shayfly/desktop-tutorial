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
def make_app(*, httponly=True, rotate=True, uniform=True, rate_limit=True, trust_xff=True, server_logout=True):
    users, sessions, hits = {}, {}, {}
    trusted = {'127.0.0.1', '::1'}

    def hash_password(pw):
        salt = os.urandom(16)
        h = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 16, r=8, p=1, dklen=64, maxmem=128 * 1024 * 1024)
        return f'scrypt$65536$8$1${salt.hex()}${h.hex()}'

    def verify(pw, stored):
        # the parameters are read FROM the stored string, never from the code (Michael fix 5)
        algo, n, r, p, salt, h = stored.split('$')
        got = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
                             dklen=len(bytes.fromhex(h)), maxmem=128 * 1024 * 1024)
        return algo == 'scrypt' and hmac.compare_digest(got, bytes.fromhex(h))

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

        def _client(self):
            peer = self.client_address[0]
            fwd = (self.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
            return fwd if (trust_xff and fwd and peer in trusted) else peer

        def _limited(self):
            if not rate_limit:
                return False
            ip = self._client()
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
                users[email] = hash_password(str(body.get('password', '')))
                return self._json(201, {'ok': True}, self._session(email))
            if self.path == '/auth/login':
                if self._limited():
                    return self._json(429, {'error': 'יותר מדי ניסיונות'})
                email = str(body.get('email', '')).lower()
                rec = users.get(email)
                if rec is None:
                    return self._json(401, {'error': 'אימייל או סיסמה שגויים' if uniform else 'אין משתמש כזה'})
                if not verify(str(body.get('password', '')), rec):
                    return self._json(401, {'error': 'אימייל או סיסמה שגויים'})
                return self._json(200, {'ok': True}, self._session(email))
            if self.path == '/auth/logout':
                sid = self._sid()
                if server_logout:
                    sessions.pop(sid, None)
                self.send_response(204)
                self.send_header('Set-Cookie', '__Host-sid=; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=0')
                self.end_headers()
                return
            self._json(404, {'error': 'not found'})

        def _sid(self):
            for part in (self.headers.get('Cookie') or '').split(';'):
                k, _, v = part.strip().partition('=')
                if k == '__Host-sid':
                    return v
            return None

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
    server.users, server.verify = users, verify
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

    def test_logout_that_only_clears_the_cookie_fails(self):
        r = hardening(server_logout=False)
        self.assertFalse(r['auth_logout_server_side'][0])
        self.assertIn('401', r['auth_logout_server_side'][1])

    def test_counting_the_proxy_instead_of_the_client_fails(self):
        r = hardening(trust_xff=False)
        self.assertFalse(r['auth_rate_limit_per_client'][0])

    def test_the_stored_password_string_carries_its_parameters(self):
        import re as _re
        app = make_app()
        try:
            from omni_prod.web_saas_auth_hardening import HardenedSessionTransport
            HardenedSessionTransport().request(method='POST', url=f'http://127.0.0.1:{app.server_port}/auth/signup',
                                               json_body={'email': 'x@example.com', 'password': 'Correct-Horse-9'})
            stored = app.users['x@example.com']
            self.assertRegex(stored, r'^scrypt\$65536\$8\$1\$[0-9a-f]{32}\$[0-9a-f]{128}$')
            self.assertTrue(app.verify('Correct-Horse-9', stored))
            # verification follows the string: an older, weaker record still verifies with ITS parameters
            salt = os.urandom(16)
            old = 'scrypt$16384$8$1$' + salt.hex() + '$' + hashlib.scrypt(b'pw', salt=salt, n=16384, r=8, p=1, dklen=32).hex()
            self.assertTrue(app.verify('pw', old))
            self.assertFalse(app.verify('wrong', old))
        finally:
            app.shutdown()
        from omni_prod.skills_runtime import SITE_AUTH
        self.assertIn('scrypt$65536$8$1$<salt hex>$<hash hex>', SITE_AUTH.guidance)
        self.assertTrue(_re.search(r'n=2\*\*16, r=8, p=1, dklen=64', SITE_AUTH.guidance))

    def test_the_hardened_runner_keeps_the_base_floor(self):
        """Michael fix 6: hardening adds checks, it never replaces the base runner's floor."""
        from omni_prod.web_saas_acceptance import WebSaaSAcceptanceRunner
        from omni_prod.web_saas_auth_hardening import HardenedAcceptanceRunner
        contract = {'prompt': 'מערכת תורים עם התחברות ללקוחות ולמנהלת, לקוחה מבטלת ומעדכנת תור', 'roles': ['user', 'admin'],
                    'infrastructure': []}
        server = make_app()
        try:
            url = {'preview_url': f'http://127.0.0.1:{server.server_port}'}
            base = WebSaaSAcceptanceRunner(build_contract=contract).verify(url, CONTRACT, PLAN)
            hard = HardenedAcceptanceRunner(build_contract=contract).verify(url, CONTRACT, PLAN)
        finally:
            server.shutdown()
        self.assertEqual(hard.missing_kinds, base.missing_kinds)
        self.assertTrue(base.missing_kinds)                 # this plan only signs in: the floor still asks for more
        self.assertEqual(hard.status, 'FAIL')
        self.assertTrue(set(c.step_id for c in base.checks) <= set(c.step_id for c in hard.checks))

    def test_secure_host_cookie_is_returned_on_loopback(self):
        """__Host-/Secure on http://127.0.0.1: browsers treat loopback as secure; the checker does the same, so a
        correct product does not fail on environment."""
        app = make_app()
        try:
            from omni_prod.web_saas_auth_hardening import HardenedSessionTransport
            t = HardenedSessionTransport()
            base = f'http://127.0.0.1:{app.server_port}'
            t.request(method='POST', url=base + '/auth/signup', json_body={'email': 'l@example.com', 'password': 'Pw-123456'})
            self.assertEqual(t.request(method='GET', url=base + '/auth/me').status, 200)
        finally:
            app.shutdown()

    def test_no_rate_limit_fails(self):
        r = hardening(rate_limit=False)
        self.assertFalse(r['auth_rate_limit'][0])
        self.assertIn('the 6th must answer 429', r['auth_rate_limit'][1])

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


class SourceIdentity(unittest.TestCase):
    """Michael 2026-11-10 fix 1: the RUNNER and GATE CODE, not only what the pipeline says. The whole import closure of
    the gates, as ASTs, equals the baseline after removing only declared flag additions.

    The baseline manifest is computed by the SAME interpreter from a worktree of 2c1d6cb (.github/workflows/
    identity.yml passes it in BASELINE_SOURCE_MANIFEST): an AST dump differs between Python versions, so a stored hash
    from another machine would compare interpreters, not code (first CI run: all 205 files "differed" on 3.12 vs 3.13).
    The mutation tests below compare the tool with itself on one interpreter."""

    @unittest.skipUnless(os.getenv('BASELINE_SOURCE_MANIFEST'), 'runs in the identity workflow against a baseline worktree')
    def test_the_gate_code_is_the_baseline_with_the_flag_off(self):
        from omni_prod.pipeline_identity import source_manifest
        base = json.load(open(os.environ['BASELINE_SOURCE_MANIFEST'], encoding='utf-8'))
        got = source_manifest()
        self.assertEqual(got['leaked_flag_only'], [], 'a flag-only name is used outside a flag block')
        self.assertEqual(set(got['files']), set(base['files']), 'the gate import closure changed')
        self.assertEqual(set(got['data']), set(base['data']), 'the set of non-Python gate inputs changed')
        changed = sorted(p for p in got['files'] if got['files'][p] != base['files'][p])
        changed_data = sorted(p for p in got['data'] if got['data'][p] != base['data'][p])
        t = got['stripped_total']
        print(f"::notice title=source identity::{len(got['files'])} Python files (AST) + {len(got['data'])} data inputs "
              f"(bytes); changed vs {BASELINE_SHA[:7]} with the flag off: {len(changed)} + {len(changed_data)}")
        print(f"::{'warning' if t['needs_human_review'] else 'notice'} title=stripped for the flag::{t['names']} "
              f"flag-only names, {t['blocks']} blocks, {t['lines']} lines in {t['files']} files"
              + (' -- large: review the flag-only code by eye' if t['needs_human_review'] else ''))
        self.assertEqual(changed, [], 'gate code differs from the baseline with the flag off')
        self.assertEqual(changed_data, [], 'a non-Python gate input differs from the baseline')

    def test_the_closure_is_computed_not_listed(self):
        from omni_prod.pipeline_identity import closure
        files = closure()
        self.assertIn('omni_prod/web_saas_acceptance.py', files)
        self.assertIn('omni_prod/fact_canon.py', files)              # imported by the gates, not listed anywhere
        self.assertGreater(len(files), 20)

    # ---- the tool catches what it must (mutations of the identity check itself, one interpreter)
    @classmethod
    def setUpClass(cls):
        from omni_prod.pipeline_identity import source_manifest
        cls.BASE = source_manifest()

    def test_no_flag_only_name_leaks_today(self):
        self.assertEqual(self.BASE['leaked_flag_only'], [])

    def test_the_two_checks_cover_every_gate_input(self):
        """Michael fix 1: the union of the AST identity and the byte identity covers every input of the gates."""
        import ast as _ast
        from omni_prod.pipeline_identity import ROOT, _DATA_EXT, _flag_only, _Strip
        covered = set(self.BASE['files']) | set(self.BASE['data'])
        uncovered = set()
        for p in self.BASE['files']:
            tree = _ast.parse((ROOT / p).read_text(encoding='utf-8'))
            for node in _ast.walk(_Strip(_flag_only(tree)).visit(tree)):     # flag-off inputs
                v = node.value if isinstance(node, _ast.Constant) else None
                if isinstance(v, str) and v.endswith(_DATA_EXT + ('.py',)) and len(v) < 160 and '\n' not in v:
                    for cand in (ROOT / v, ROOT / 'omni_prod' / v, (ROOT / p).parent / v):
                        if cand.is_file():
                            rel = str(cand.resolve().relative_to(ROOT))
                            if rel.startswith(('omni_prod/', '.github/', 'docs/', 'infra/')) and rel not in covered:
                                uncovered.add(rel)
                            break
        self.assertEqual(sorted(uncovered), [], 'a gate input is covered by neither identity check')
        self.assertIn('omni_prod/assets/app.js', self.BASE['data'])
        self.assertIn('.github/workflows/gate-regression.yml', self.BASE['data'])

    def test_flag_only_modules_are_outside_the_flag_off_closure(self):
        # 2026-11-10: a file NAME inside a flag block pulled the flag-only module into the closure; it must not.
        for module in ('omni_prod/web_saas_auth_hardening.py', 'omni_prod/auth_form_check.py', 'omni_prod/feature_flags.py'):
            self.assertNotIn(module, self.BASE['files'])

    def test_stripping_is_reported(self):
        t = self.BASE['stripped_total']
        self.assertEqual((t['names'], t['needs_human_review']), (2, False))
        self.assertIn('omni_prod/skills_runtime.py', self.BASE['stripped'])
        self.assertGreater(t['blocks'], 0)

    def test_a_large_flag_only_rewrite_asks_for_a_human(self):
        from omni_prod import pipeline_identity as pi
        saved = pi.REVIEW_LINES
        try:
            pi.REVIEW_LINES = 10
            self.assertTrue(pi.source_manifest()['stripped_total']['needs_human_review'])
        finally:
            pi.REVIEW_LINES = saved

    def test_a_data_input_change_is_caught(self):
        from omni_prod.pipeline_identity import ROOT, source_manifest
        got = source_manifest(read_bytes=lambda p: (ROOT / p).read_bytes() + (b'x' if p.endswith('app.js') else b''))
        self.assertNotEqual(got['data']['omni_prod/assets/app.js'], self.BASE['data']['omni_prod/assets/app.js'])

    def mutated(self, path, change):
        from omni_prod.pipeline_identity import ROOT, source_manifest

        def read(p):
            text = (ROOT / p).read_text(encoding='utf-8')
            return change(text) if p == path else text
        return source_manifest(read)

    def test_a_live_change_outside_a_flag_is_caught(self):
        got = self.mutated('omni_prod/web_saas_acceptance.py',
                           lambda t: t.replace("float(timeout_seconds)", "float(timeout_seconds) * 2", 1))
        self.assertNotEqual(got['files']['omni_prod/web_saas_acceptance.py'],
                            self.BASE['files']['omni_prod/web_saas_acceptance.py'])

    def test_a_change_inside_a_flag_block_is_not_counted(self):
        got = self.mutated('omni_prod/skills_runtime.py',
                           lambda t: t.replace("    WEB_SKILLS = WEB_SKILLS + (SITE_AUTH,)",
                                               "    WEB_SKILLS = WEB_SKILLS + (SITE_AUTH, SITE_AUTH)", 1))
        self.assertEqual(got['files']['omni_prod/skills_runtime.py'], self.BASE['files']['omni_prod/skills_runtime.py'])

    def test_comments_and_formatting_do_not_count(self):
        got = self.mutated('omni_prod/fact_canon.py', lambda t: t.replace('\n\n\ndef ', '\n\n\n# note\ndef ', 1))
        self.assertEqual(got['files']['omni_prod/fact_canon.py'], self.BASE['files']['omni_prod/fact_canon.py'])

    def test_a_flag_only_name_used_outside_a_flag_block_is_caught(self):
        got = self.mutated('omni_prod/skills_runtime.py',
                           lambda t: t.replace("def guidance_for(role: str) -> str:\n",
                                               "def guidance_for(role: str) -> str:\n    _ = SITE_AUTH\n", 1))
        self.assertIn('SITE_AUTH', got['leaked_flag_only'])

    def test_declaring_a_live_name_flag_only_does_not_hide_its_change(self):
        # hiding web_saas_acceptance's runner behind _FLAG_ONLY: its uses elsewhere expose it
        got = self.mutated('omni_prod/web_saas_acceptance.py',
                           lambda t: t + "\n_FLAG_ONLY = {'site_auth_v2': ('acceptance_scope',)}\n")
        self.assertIn('acceptance_scope', got['leaked_flag_only'])
