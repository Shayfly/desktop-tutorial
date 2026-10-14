"""Attachments, Visual Edit locate/compose, and the preview inspector wrapper
(founder directive 2026-10-11: Conversation UX + Visual Editing).

Attachment storage tests use a REAL PostgreSQL (M4D2_DATABASE_URL, migration 038
applied by the test) with an in-process object store; they are skipped -- not
faked -- without PostgreSQL. No model is called anywhere.
"""
import base64
import gzip
import hashlib
import http.client
import io
import os
import struct
import threading
import unittest
import uuid
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

from omni_prod import attachments as A
from omni_prod import preview_inspector as PI
from omni_prod import visual_edit as V


def png(w=4, h=3) -> bytes:
    raw = b''.join(b'\x00' + b'\x10\x20\x30' * w for _ in range(h))
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def jpeg(w=640, h=480) -> bytes:
    sof = b'\xff\xc0' + struct.pack('>HBHHB', 17, 8, h, w, 3) + b'\x01\x11\x00\x02\x11\x00\x03\x11\x00'
    return b'\xff\xd8\xff\xe0' + struct.pack('>H', 16) + b'JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00' + sof + b'\xff\xd9'


def webp_vp8x(w=1200, h=900) -> bytes:
    body = b'VP8X' + struct.pack('<I', 10) + b'\x00\x00\x00\x00' + (w - 1).to_bytes(3, 'little') + (h - 1).to_bytes(3, 'little')
    return b'RIFF' + struct.pack('<I', 4 + len(body)) + b'WEBP' + body


class ImageValidationTests(unittest.TestCase):
    def test_types_are_decided_from_bytes(self):
        self.assertEqual(A.validate_image(png(5, 7)), ('image/png', 5, 7))
        self.assertEqual(A.validate_image(jpeg(640, 480)), ('image/jpeg', 640, 480))
        self.assertEqual(A.validate_image(webp_vp8x(1200, 900)), ('image/webp', 1200, 900))

    def test_refuses_svg_gif_html_and_oversize(self):
        for bad in (b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>', b'GIF89a....',
                    b'<html><script>1</script></html>', b''):
            with self.subTest(bad=bad[:10]):
                with self.assertRaises(A.AttachmentError):
                    A.validate_image(bad)
        with self.assertRaises(A.AttachmentError) as ctx:
            A.validate_image(png() + b'\x00' * A.MAX_BYTES)
        self.assertEqual(ctx.exception.code, 'too_large')
        with self.assertRaises(A.AttachmentError):
            A.validate_image(jpeg(9000, 10))

    def test_declared_type_is_ignored_and_base64_is_strict(self):
        data = png()
        self.assertEqual(A.decode_base64('data:image/svg+xml;base64,' + base64.b64encode(data).decode()), data)
        with self.assertRaises(A.AttachmentError):
            A.decode_base64('not base64 !!')

    def test_annotation_bounds(self):
        self.assertEqual(A.validate_annotation({'regions': [{'x': 1, 'y': 1, 'w': 2, 'h': 1}], 'strokes': 3, 'note': ' here '}, 4, 3),
                         {'regions': [{'x': 1, 'y': 1, 'w': 2, 'h': 1}], 'strokes': 3, 'note': 'here'})
        for bad in ({'regions': [{'x': 3, 'y': 0, 'w': 5, 'h': 1}]}, {'regions': 'x'}, {'strokes': -1}, {'note': 'x' * 501}, []):
            with self.subTest(bad=bad):
                with self.assertRaises(A.AttachmentError):
                    A.validate_annotation(bad, 4, 3)


class MemoryStore:
    def __init__(self):
        self.objects, self.bucket = {}, 'b'
        self.client = SimpleNamespace(delete_object=lambda Bucket, Key: self.objects.pop(Key))

    def put_bytes(self, key, data):
        self.objects[key] = bytes(data)
        return SimpleNamespace(key=key, sha256=hashlib.sha256(data).hexdigest(), size=len(data))

    def get_bytes(self, key):
        return self.objects[key]


DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '')


def _pg_skip():
    if not DATABASE_URL:
        return 'needs PostgreSQL (M4D2_DATABASE_URL)'
    try:
        import psycopg
        psycopg.connect(DATABASE_URL, connect_timeout=3).close()
    except Exception as exc:
        return f'no live Postgres: {exc}'
    return None


@unittest.skipIf(_pg_skip(), _pg_skip())
class AttachmentRepositoryTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.db import DatabasePool
        self.pool = DatabasePool(DATABASE_URL)
        sql = open(os.path.join(os.path.dirname(__file__), '..', 'infra', 'postgres', '038_conversation_attachments.sql')).read()
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute(sql)
        self.store = MemoryStore()
        self.repo = A.AttachmentRepository(self.pool, self.store)
        self.p, self.a, self.b = f'prj_{uuid.uuid4().hex[:8]}', f'acc_{uuid.uuid4().hex[:8]}', f'acc_{uuid.uuid4().hex[:8]}'

    def tearDown(self):
        getattr(self.pool, 'close', lambda: None)()

    def test_create_read_list_delete(self):
        row = self.repo.create(project_id=self.p, account_id=self.a, kind='screenshot', data=png(4, 3),
                               annotation={'regions': [{'x': 0, 'y': 0, 'w': 2, 'h': 2}]})
        self.assertRegex(row['id'], r'^att_[0-9a-f]{32}$')
        self.assertTrue(row['storage_key'].startswith(f'attachments/{self.a}/{self.p}/'))
        self.assertEqual(self.repo.read(row), png(4, 3))
        pub = A.public(row)
        self.assertEqual(pub['analysis']['state'], 'NOT_ANALYZED')            # honest: nothing analyzed it
        self.assertNotIn('storage_key', pub)
        self.assertEqual([r['id'] for r in self.repo.list(project_id=self.p, account_id=self.a)], [row['id']])
        self.repo.delete(project_id=self.p, account_id=self.a, attachment_id=row['id'])
        self.assertNotIn(row['storage_key'], self.store.objects)               # bytes really gone
        with self.assertRaises(KeyError):
            self.repo.get(project_id=self.p, account_id=self.a, attachment_id=row['id'])

    def test_other_accounts_and_projects_cannot_see_or_delete(self):
        row = self.repo.create(project_id=self.p, account_id=self.a, kind='image', data=jpeg())
        for project, account in ((self.p, self.b), (f'{self.p}x', self.a)):
            with self.assertRaises(KeyError):
                self.repo.get(project_id=project, account_id=account, attachment_id=row['id'])
            with self.assertRaises(KeyError):
                self.repo.delete(project_id=project, account_id=account, attachment_id=row['id'])
            self.assertEqual(self.repo.list(project_id=project, account_id=account), [])
        self.assertIn(row['storage_key'], self.store.objects)
        with self.assertRaises(A.AttachmentError):
            self.repo.many(project_id=self.p, account_id=self.b, ids=[row['id']])

    def test_tampered_object_is_refused(self):
        row = self.repo.create(project_id=self.p, account_id=self.a, kind='image', data=png())
        self.store.objects[row['storage_key']] = png(5, 5)
        with self.assertRaises(A.AttachmentError):
            self.repo.read(row)

    def test_per_project_limit(self):
        for _ in range(A.MAX_LIVE_PER_PROJECT):
            self.repo.create(project_id=self.p, account_id=self.a, kind='image', data=png())
        with self.assertRaises(A.AttachmentError) as ctx:
            self.repo.create(project_id=self.p, account_id=self.a, kind='image', data=png())
        self.assertEqual(ctx.exception.status, 409)

    def test_schema_refuses_bad_rows(self):
        import psycopg
        with self.assertRaises(psycopg.errors.CheckViolation):
            with self.pool.connection() as conn:
                with conn.transaction():
                    conn.execute("INSERT INTO conversation_attachments (id, project_id, account_id, kind, mime, size_bytes, width, "
                                 "height, sha256, storage_key) VALUES (%s, 'p', 'a', 'image', 'image/svg+xml', 1, 1, 1, %s, 'k')",
                                 (f'att_{uuid.uuid4().hex}', '0' * 64))


REPO = {
    'templates/index.html': '<html><head><title>Loans</title></head><body>\n'
                            '<h1 class="title big">Equipment loans</h1>\n'
                            '<button id="save-btn" class="btn primary">Save</button>\n'
                            '<button class="btn">Cancel</button>\n'
                            '<a href="/report" class="btn">Cancel</a>\n'
                            '<input name="borrower" placeholder="Who borrows?">\n</body></html>\n',
    'templates/edit.html': '<form><button class="btn">Cancel</button></form>\n',
    'static/app.js': 'document.title = "Loans";\n',
    'node_modules/x/index.html': '<button id="save-btn">Save</button>\n',
}


class LocateTests(unittest.TestCase):
    def test_id_is_unique(self):
        r = V.locate(REPO, {'tag': 'button', 'id': 'save-btn', 'classes': ['btn', 'primary'], 'text': 'Save'})
        self.assertEqual(r['status'], 'UNIQUE')
        self.assertEqual((r['candidates'][0]['file'], r['candidates'][0]['line']), ('templates/index.html', 3))
        self.assertTrue(r['anchor'].startswith('id'))                          # node_modules ignored

    def test_attribute_anchor(self):
        r = V.locate(REPO, {'tag': 'input', 'attrs': {'name': 'borrower', 'placeholder': 'Who borrows?'}})
        self.assertEqual(r['status'], 'UNIQUE')
        self.assertEqual(r['candidates'][0]['line'], 6)

    def test_same_text_in_several_places_is_ambiguous_and_lists_candidates(self):
        r = V.locate(REPO, {'tag': 'button', 'classes': ['btn'], 'text': 'Cancel'})
        self.assertEqual(r['status'], 'AMBIGUOUS')
        files = {(c['file'], c['line']) for c in r['candidates']}
        self.assertEqual(files, {('templates/index.html', 4), ('templates/edit.html', 1)})   # the <a> is filtered by tag
        with self.assertRaises(V.SelectionInvalid):
            V.choose(r, None)                                                   # never a guess
        self.assertEqual(V.choose(r, {'file': 'templates/edit.html', 'line': 1})['file'], 'templates/edit.html')
        with self.assertRaises(V.SelectionInvalid):
            V.choose(r, {'file': 'templates/other.html', 'line': 1})

    def test_not_found(self):
        self.assertEqual(V.locate(REPO, {'tag': 'div', 'text': 'Nothing like this'})['status'], 'NOT_FOUND')

    def test_selection_from_the_page_is_bounded(self):
        s = V.clean_selection({'tag': 'BUTTON', 'id': 'x" onclick="1', 'classes': ['ok', 'bad class', 7],
                               'attrs': {'onclick': 'evil()', 'name': 'n'}, 'text': 'a' * 999, 'html': 'h' * 999})
        self.assertEqual((s['tag'], s['id'], s['classes'], s['attrs']), ('button', '', ['ok'], {'name': 'n'}))
        self.assertLessEqual(len(s['text']), 160)
        with self.assertRaises(V.SelectionInvalid):
            V.clean_selection({'tag': '<script>'})

    def test_followup_names_the_target_and_the_scope(self):
        r = V.locate(REPO, {'tag': 'button', 'id': 'save-btn', 'text': 'Save'})
        f = V.compose_followup('make it green', target=V.choose(r, None), selection=r['selection'],
                               attachments=[{'id': 'att_1', 'kind': 'screenshot', 'width': 10, 'height': 10,
                                             'annotation': {'regions': [{'x': 1, 'y': 1, 'w': 2, 'h': 2}]}}])
        self.assertTrue(f.startswith('make it green'))
        self.assertIn('templates/index.html (around line 3)', f)
        self.assertIn('Keep every other part of the product unchanged', f)
        self.assertIn('not analyzed automatically', f)
        self.assertLessEqual(len(V.compose_followup('x' * 20000, target=None, selection=None)), 12000)


class InspectorTests(unittest.TestCase):
    def test_injection_points(self):
        tag = b'<script src="/__148ai/inspector.js" defer></script>'
        self.assertEqual(PI.inject(b'<html><head></head><body></body></html>'),
                         b'<html><head>' + tag + b'</head><body></body></html>')
        self.assertEqual(PI.inject(b'<p>x</p>'), b'<p>x</p>' + tag)
        self.assertEqual(PI.inject(PI.inject(b'<head></head>')).count(tag), 1)

    def test_rewrite_only_html_200_and_gzip_is_handled(self):
        def resp(status, ctype, body, extra=''):
            return (f'HTTP/1.1 {status}\r\nContent-Type: {ctype}\r\nContent-Length: {len(body)}\r\n{extra}\r\n').encode() + body
        out = PI.rewrite_response(resp('200 OK', 'text/html; charset=utf-8', b'<head></head>'))
        self.assertIn(b'inspector.js', out)
        self.assertIn(f'Content-Length: {len(PI.inject(b"<head></head>"))}'.encode(), out)
        for raw in (resp('200 OK', 'application/json', b'{}'), resp('404 Not Found', 'text/html', b'<head></head>'),
                    resp('200 OK', 'text/html', b'x', 'Content-Encoding: br\r\n')):
            self.assertEqual(PI.rewrite_response(raw), raw)
        gz = gzip.compress(b'<head></head>')
        out = PI.rewrite_response(resp('200 OK', 'text/html', gz, 'Content-Encoding: gzip\r\n'))
        self.assertIn(b'inspector.js', out)
        self.assertNotIn(b'Content-Encoding', out)

    def test_origins_are_strict(self):
        os.environ['OMNI_WORKSPACE_ORIGINS'] = 'https://app.148ai.com, http://evil.com, https://x.vercel.app/, javascript:1'
        try:
            self.assertEqual(PI.workspace_origins(), ['https://app.148ai.com', 'https://x.vercel.app'])
        finally:
            del os.environ['OMNI_WORKSPACE_ORIGINS']
        self.assertIn(b'["https://a.b"]', PI.inspector_script(['https://a.b']))

    def test_router_wrapper_end_to_end(self):
        """Real sockets: fake app upstream <- inspecting router <- client."""
        class App(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *a):
                pass

            def do_GET(self):
                body = b'<html><head><title>x</title></head><body>hi</body></html>' if self.path == '/' else b'{"a":1}'
                self.send_response(200)
                self.send_header('Content-Type', 'text/html' if self.path == '/' else 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        upstream = ThreadingHTTPServer(('127.0.0.1', 0), App)
        threading.Thread(target=upstream.serve_forever, daemon=True).start()
        port = upstream.server_address[1]
        pid = 'prv_' + 'a' * 32
        from omni_prod.preview_runtime import preview_id_from_host_label
        label = next(l for l in (pid, pid.replace('_', '-')) if preview_id_from_host_label(l) == pid)
        routes = SimpleNamespace(port_for=lambda p: port if p == pid else None)

        class Access:
            def allows(self, p, token):
                return token == 'owner'

            def record_denied(self, p):
                pass

        def run(enabled):
            h = PI.make_inspecting_handler(routes, 'prv.test', access=Access(), enabled=enabled, origins=['https://ws.test'])
            srv = ThreadingHTTPServer(('127.0.0.1', 0), h)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            return srv

        def get(srv, path, dest=None, cookie='owner'):
            c = http.client.HTTPConnection('127.0.0.1', srv.server_address[1], timeout=5)
            headers = {'Host': f'{label}.prv.test', 'X-148AI-Preview-Token': cookie}
            if dest:
                headers['Sec-Fetch-Dest'] = dest
            from omni_prod.preview_access import HEADER
            headers[HEADER] = headers.pop('X-148AI-Preview-Token')
            c.request('GET', path, headers=headers)
            r = c.getresponse()
            out = (r.status, r.read(), dict(r.getheaders()))
            c.close()
            return out

        on, off = run(True), run(False)
        try:
            st, body, hdr = get(on, '/', 'iframe')
            self.assertEqual(st, 200)
            self.assertIn(b'/__148ai/inspector.js', body)
            self.assertEqual(int(hdr['Content-Length']), len(body))
            self.assertNotIn(b'inspector.js', get(on, '/', 'document')[1])    # top-level visit: untouched
            self.assertNotIn(b'inspector.js', get(on, '/api', 'iframe')[1])   # not HTML: untouched
            self.assertNotIn(b'inspector.js', get(off, '/', 'iframe')[1])     # flag off: pass-through
            st, js, hdr = get(on, PI.INSPECTOR_PATH)
            self.assertEqual(st, 200)
            self.assertIn(b'https://ws.test', js)
            self.assertEqual(hdr['Content-Type'], 'text/javascript; charset=utf-8')
            self.assertEqual(get(on, PI.INSPECTOR_PATH, cookie='stranger')[0], 404)
            self.assertEqual(get(on, '/', 'iframe', cookie='stranger')[0], 401)   # access control unchanged
        finally:
            for s in (on, off, upstream):
                s.shutdown()


if __name__ == '__main__':
    unittest.main()
