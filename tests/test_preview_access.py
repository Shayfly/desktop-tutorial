"""Private previews (autonomous completion directive §4)."""
import os
import threading
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, request

from omni_prod import preview_router
from omni_prod.preview_access import COOKIE, HEADER, PreviewAccess, QUERY_PARAM

DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')


def _skip():
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as c:
            if c.execute("SELECT to_regclass('public.preview_access_tokens')").fetchone()[0] is None:
                return 'schema through 032 not applied'
    except Exception as exc:
        return f'no live Postgres: {exc}'
    return None


class _App(BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        _App.seen.append((self.path, self.headers.get('Cookie'), self.headers.get(HEADER)))
        b = b'generated app'
        self.send_response(200); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    do_POST = do_GET

    def log_message(self, *a):
        pass


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


@unittest.skipIf(_skip(), _skip())
class PreviewAccessTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.db import DatabasePool
        self.pool = DatabasePool(DATABASE_URL)
        self.pid = f'prv_{uuid.uuid4().hex}'
        with self.pool.connection() as c:
            with c.transaction():
                c.execute("INSERT INTO project_previews(id, project_id, version_id, status, expires_at) "
                          "VALUES (%s, 'k', 'v', 'RUNNING', now() + interval '1 hour')", (self.pid,))
        self.access = PreviewAccess(self.pool)
        self.app = ThreadingHTTPServer(('127.0.0.1', 0), _App)
        threading.Thread(target=self.app.serve_forever, daemon=True).start()
        app_port = self.app.server_address[1]

        class Routes:
            def port_for(_, pid):
                return app_port if pid == self.pid else None
        self.router = ThreadingHTTPServer(('127.0.0.1', 0), preview_router.make_handler(Routes(), 'ex.test',
                                                                                         access=self.access))
        threading.Thread(target=self.router.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.router.server_address[1]}'
        self.host = self.pid.replace('_', '-') + '.ex.test'
        _App.seen = []

    def tearDown(self):
        self.app.shutdown(); self.router.shutdown()

    def get(self, path='/', headers=None, follow=False):
        req = request.Request(self.base + path, headers={'Host': self.host, **(headers or {})})
        opener = request.build_opener() if follow else request.build_opener(_NoRedirect)
        try:
            with opener.open(req, timeout=5) as r:
                return r.status, dict(r.headers), r.read().decode()
        except error.HTTPError as e:
            return e.code, dict(e.headers), e.read().decode()

    def test_private_by_default_refuses_anonymous_requests(self):
        status, _, body = self.get('/')
        self.assertEqual(status, 401)
        self.assertIn('פרטית', body)
        self.assertEqual(_App.seen, [])  # never reached the app
        with self.pool.connection() as c:
            n = c.execute("SELECT count(*) FROM preview_access_audit WHERE preview_id=%s AND event='denied'",
                          (self.pid,)).fetchone()[0]
        self.assertEqual(n, 1)

    def test_owner_link_becomes_a_cookie_and_the_token_never_reaches_the_app(self):
        token, _ = self.access.issue(self.pid, kind='owner', issued_to='u1')
        status, headers, _ = self.get(f'/?{QUERY_PARAM}={token}')
        self.assertEqual(status, 302)
        self.assertEqual(headers['Location'], '/')
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        status, _, body = self.get('/page?x=1', headers={'Cookie': f'{COOKIE}={token}; other=1'})
        self.assertEqual((status, body), (200, 'generated app'))
        path, cookie, header = _App.seen[-1]
        self.assertEqual(path, '/page?x=1')
        self.assertEqual(cookie, 'other=1')
        self.assertIsNone(header)

    def test_header_token_for_api_clients(self):
        token, _ = self.access.issue(self.pid, kind='owner')
        self.assertEqual(self.get('/', headers={HEADER: token})[0], 200)
        self.assertEqual(self.get('/', headers={HEADER: 'wrong'})[0], 401)

    def test_share_link_works_only_while_shared_and_is_revoked_by_private(self):
        token, _ = self.access.issue(self.pid, kind='share')
        self.assertEqual(self.get('/', headers={HEADER: token})[0], 401)   # PRIVATE ignores share links
        self.access.set_mode(self.pid, 'SHARED')   # no cache clearing: works at once
        self.assertEqual(self.get('/', headers={HEADER: token})[0], 200)
        self.access.set_mode(self.pid, 'PRIVATE')
        self.access._cache.clear()
        self.access.set_mode(self.pid, 'SHARED')   # revoked tokens stay revoked
        self.access._cache.clear()
        self.assertEqual(self.get('/', headers={HEADER: token})[0], 401)

    def test_public_needs_no_token_and_expired_tokens_fail(self):
        token, _ = self.access.issue(self.pid, kind='owner')
        with self.pool.connection() as c:
            with c.transaction():
                c.execute("UPDATE preview_access_tokens SET expires_at = now() - interval '1 minute' WHERE preview_id=%s",
                          (self.pid,))
        self.assertEqual(self.get('/', headers={HEADER: token})[0], 401)
        self.access.set_mode(self.pid, 'PUBLIC')
        self.access._cache.clear()
        self.assertEqual(self.get('/')[0], 200)


if __name__ == '__main__':
    unittest.main()
