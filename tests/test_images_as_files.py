"""Warehouse 118 (+114): the main image is a FILE the page references, carried by every point (the owner, 2026-11-20).

Production, 2026-11-14 (the butcher, bld_83529c13): the generated hero went into the page as 1,735,408 base64
characters. The page was heavy and the business facts fell past the 45,000 characters of GET / that the preview smoke
keeps for the truth gate. The five points of row 118 were text-only: the sandbox request, the saved version, the
preview, the export, and the generated site's server. Here each one runs for real (seam rule, AGENTS.md rule 2):

  * the D5 path: the plan's media.image.generate requirement -> generated_images.collect (the real web rendition) ->
    the real repository transform;
  * the sandbox: the REAL RemoteSandboxRepositoryExecutor._run (validate_snapshot, validate_command, the HMAC body),
    the runner writing the snapshot with repository_assets.file_bytes (what sandbox_service.run writes with; FastAPI is
    not installed in this container, so its HTTP layer is checked by source below), and the REAL preview smoke script
    run in a subprocess against a stdlib server written the way the generated sites write theirs;
  * the saved version: the REAL PostgresProjectWorkspace zip save and load (its SQL cursor scripted -- no Postgres here);
  * the preview: the REAL DockerPreviewProvider.start and its work directory; only `docker` itself is a double (no
    daemon in this container): the double runs the contract's start command from the very work directory start()
    wrote, so what is served is what the preview wrote;
  * the export: the REAL UnifiedOmniEngine.export_zip (every /api/v2x/.../export route calls it), unpacked and served.

The image: the platform ships no fixed D5 picture (D5 generates one per build), so a real image file the platform does
ship -- BRAND_PACK/148AI-logo-master-transparent.png, 726,326 bytes -- goes through the exact D5 path: the rendition
makes it a 114 KB WebP, i.e. 152,000 base64 characters, enough to push the butcher's facts past 45,000 when inlined.
The JPEG and the PNG cases use BRAND_PACK files too (re-encoded to JPEG; the 64 px logo as is).
"""
from __future__ import annotations

import ast
import base64
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from omni_prod import generated_images as G
from omni_prod import repository_assets as RA
from omni_prod.autonomous_core import ExecutionReport
from omni_prod.capabilities import CapabilityPlan
from omni_prod.media_pipeline import AssetKind, CreativeDirector
from omni_prod.preview_runtime import DockerPreviewProvider
from omni_prod.preview_smoke import PreviewReadyExecutor
from omni_prod.rehearsal import approved_prompt
from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor
from omni_prod.sandbox_request_policy import SandboxRequestRejected, validate_command, validate_snapshot
from omni_prod.unified_engine import UnifiedOmniEngine
from omni_prod.uploaded_assets import MARKER as LOGO_MARKER, logo_transform
from omni_prod.workspace import PostgresProjectWorkspace
from tests.test_generated_images_in_page import evidence_for, image_req
from tests.test_m495_capability_executor import MemoryStore

ROOT = Path(__file__).resolve().parent.parent
BUTCHER = json.loads((ROOT / 'tests/fixtures/butcher_served_page_2026_11_14.json').read_text(encoding='utf-8'))
PLACEHOLDER = 'data:image/gif;base64,R0lGODlhAQABAAAAACw='          # the fixture's 1x1 stand-in for the real hero
HERO_FILE = ROOT / 'BRAND_PACK/148AI-logo-master-transparent.png'
LOGO_FILE = ROOT / 'BRAND_PACK/148AI-logo-64.png'
FACTS = [f for f in BUTCHER['brief']['assets']['facts']['spans'] if f in BUTCHER['page']]
LATE_FACT = 'שבת סגור'                                              # written after the hero <img> on the butcher page
WINDOW = 45_000                                                     # preview_smoke keeps page[:45000]
REQUEST = 'אתר לאטליז "האטליז של סבא שמעון" ברחוב נתיב המזלות 22, ירושלים. טלפון 0504000162.'

# The generated sites serve their page from app.py with the standard library (preview_smoke.PREVIEW_SHAPE). This one
# serves /assets/<name> the way the shape now asks: the file's bytes, in binary, with its Content-Type.
APP = r'''import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
HTML_CONTENT = %(html)r
TYPES = {".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
SERVE_ASSETS = %(serve)r
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/assets/"):
            name = os.path.basename(path)
            full = os.path.join("assets", name)
            if not SERVE_ASSETS or not os.path.isfile(full):
                self.send_error(404)
                return
            with open(full, "rb") as fh:
                body = fh.read()
            ctype = TYPES.get(os.path.splitext(name)[1].lower(), "application/octet-stream")
        else:
            body, ctype = HTML_CONTENT.encode("utf-8"), "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass
ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), Handler).serve_forever()
'''


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def page_with(*imgs: str) -> str:
    """The butcher's production page; the hero placeholder becomes the first marker, other markers go after it."""
    page = BUTCHER['page']
    assert page.count(PLACEHOLDER) == 1
    page = page.replace(PLACEHOLDER, imgs[0])
    extra = ''.join(f'<img src="{m}" alt="לוגו האטליז" width="64" height="64">' for m in imgs[1:])
    return page.replace('</body>', extra + '</body>', 1)


def site(html: str, *, port: int, serve: bool = True) -> dict:
    return {'app.py': APP % {'html': html, 'serve': serve},
            '.omni/project.json': json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim',
                                              'start': ['python', 'app.py'], 'port': port, 'health_path': '/'})}


def d5_image():
    """The D5 default hero, through the real path: plan requirement -> collect (rendition) -> GeneratedImage."""
    store = MemoryStore()
    ev = evidence_for(store, [('cap-media-image-generate', 'VERIFIED', [HERO_FILE.read_bytes()])])
    prompt = approved_prompt(REQUEST, {'content_only': 'yes', 'personal_data': 'no', 'login': 'none'})
    engine = SimpleNamespace(core=SimpleNamespace(executor=None, repository_transform=None))
    G.install(engine, prompt=prompt, plan=CapabilityPlan((image_req(),), ()), evidence=ev, store=store)
    return engine.core.generated_images[0], engine.core.repository_transform, prompt


def logo_png():
    data = LOGO_FILE.read_bytes()
    return logo_transform(data, 'image/png', hashlib.sha256(data).hexdigest()), data


def jpeg_photo():
    out = io.BytesIO()
    Image.open(HERO_FILE).convert('RGB').resize((900, 900)).save(out, 'JPEG', quality=85)
    data = out.getvalue()
    return G.GeneratedImage(index=1, requirement_id='r1', purpose='hero', mime='image/jpeg', width=900, height=900,
                            sha256=hashlib.sha256(data).hexdigest(), alt='הדלפק', data=data)


def http(url: str, *, attempts: int = 40):
    """(status, content-type, body); bounded wait for a server that is starting."""
    last = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                return r.status, r.headers.get('Content-Type', ''), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get('Content-Type', ''), b''
        except OSError as e:
            last = e
            time.sleep(0.25)
    raise AssertionError(f'{url} never answered: {last}')


class Serve:
    """Runs app.py from a directory (the preview work directory, an unpacked export) on a free port."""

    def __init__(self, workdir):
        self.port = free_port()
        self.proc = subprocess.Popen([sys.executable, 'app.py'], cwd=workdir, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, env=dict(os.environ, PORT=str(self.port)))

    def get(self, path):
        return http(f'http://127.0.0.1:{self.port}{path}')

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


# ---------------------------------------------------------------- the sandbox: the real request path and runner write

class Runner:
    """The sandbox runner's HTTP endpoint: it validates the request again as sandbox_service.run does, writes the
    snapshot with the function sandbox_service writes with, and really runs the argv (the preview smoke)."""

    def __init__(self):
        self.payloads, self.stdouts = [], []

    def __call__(self, req, timeout=None):
        payload = json.loads(req.data.decode())
        validate_snapshot(payload['repository'])
        validate_command(payload['argv'], build_id=payload['build_id'], profile=payload.get('profile', 'default'),
                         repository=payload['repository'])
        self.payloads.append(payload)
        with tempfile.TemporaryDirectory() as root:
            RA.materialize(Path(root), payload['repository'])
            argv = payload['argv']
            p = subprocess.run([sys.executable if argv[0] == 'python' else argv[0], *argv[1:]], cwd=root,
                               capture_output=True, text=True, timeout=120)
        self.stdouts.append(p.stdout)
        body = json.dumps({'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}).encode()

        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False
        return Resp(body)


class _Inner:
    def __init__(self, runner):
        self._run = RemoteSandboxRepositoryExecutor(RemoteSandboxConfig('http://sandbox.invalid', 'x' * 40),
                                                    urlopen=runner)._run

    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'inner ok')


def smoke(repository):
    """The real preview smoke through the real request path. (report, smoke executor, runner)."""
    runner = Runner()
    ex = PreviewReadyExecutor(_Inner(runner))
    report = ex.execute(repository=repository, spec=SimpleNamespace(requirements=()))
    return report, ex, runner


def stdout_line(runner_payload_stdout: str, prefix: str):
    for line in runner_payload_stdout.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
    return None


class D5ContentSite(unittest.TestCase):
    """Acceptance 1 and 2 on the sandbox: no data:image in the page; the image served as its own file."""

    @classmethod
    def setUpClass(cls):
        cls.hero, transform, cls.prompt = d5_image()
        cls.logo, cls.logo_bytes = logo_png()
        from omni_prod.generated_images import _Transform
        cls.transform = _Transform(cls.logo, [cls.hero])                  # the worker's order: logo, then images
        cls.port = free_port()
        cls.repo = cls.transform(site(page_with(cls.hero.marker, LOGO_MARKER), port=cls.port))
        cls.report, cls.ex, cls.runner = smoke(cls.repo)

    def test_the_plan_of_a_content_site_asks_for_the_d5_default_hero(self):
        plan = [(r.kind, r.purpose, r.required) for r in CreativeDirector().plan(self.prompt).requests]
        self.assertIn((AssetKind.IMAGE, 'hero/brand visual', False), plan)
        self.assertEqual(self.hero.purpose, 'hero/brand visual')

    def test_the_real_image_went_through_the_rendition_and_is_a_file_of_its_own(self):
        self.assertEqual(self.hero.mime, 'image/webp')
        self.assertEqual(self.hero.uri, 'assets/148ai-image-1.webp')
        self.assertEqual(RA.file_bytes(self.hero.uri, self.repo[self.hero.uri]), self.hero.data)
        self.assertGreater(len(base64.b64encode(self.hero.data)), WINDOW)        # inlined, it would fill the window

    def test_the_page_has_no_data_image_uri(self):
        html = self.repo['app.py']
        self.assertNotIn('data:image', html)
        self.assertIn('src="assets/148ai-image-1.webp"', html)
        self.assertIn('src="assets/148ai-logo.png"', html)
        self.assertNotIn('148ai-asset://', html)

    def test_the_sandbox_got_the_image_as_a_file_and_served_it_with_its_type(self):
        self.assertTrue(self.report.passed, self.report.failures)
        self.assertEqual(self.ex.last_smoke, {'status': 'PASS'})
        [payload] = self.runner.payloads
        self.assertTrue(RA.is_envelope(payload['repository']['assets/148ai-image-1.webp']))
        served = json.loads(stdout_line(self.runner.stdouts[0], 'PREVIEW-ASSETS '))
        self.assertEqual(served, ['148ai-image-1.webp', '148ai-logo.png'])        # each checked: 200, type, bytes

    def test_the_business_facts_are_inside_the_45000_characters_the_truth_gate_reads(self):
        page = self.ex.last_pages['/']
        self.assertLessEqual(len(page), WINDOW)
        self.assertTrue(FACTS and LATE_FACT in FACTS, FACTS)
        for fact in FACTS:
            self.assertIn(fact, page, fact)

    def test_the_same_page_with_the_image_inlined_loses_the_late_fact(self):
        """The control on the same real path: inlined as before, the late fact is past the 45,000 characters."""
        inline = dict(self.repo)
        uri = f'data:{self.hero.mime};base64,' + base64.b64encode(self.hero.data).decode('ascii')
        inline['app.py'] = inline['app.py'].replace(self.hero.uri, uri)
        report, ex, _ = smoke(inline)
        self.assertTrue(report.passed, report.failures)
        self.assertNotIn(LATE_FACT, ex.last_pages['/'])


class TheGeneratedServer(unittest.TestCase):
    def test_a_server_that_does_not_serve_assets_fails_the_preview_loudly(self):
        hero, _, _ = d5_image()
        from omni_prod.generated_images import _Transform
        repo = _Transform(None, [hero])(site(page_with(hero.marker), port=free_port(), serve=False))
        report, ex, _ = smoke(repo)
        self.assertFalse(report.passed)
        self.assertEqual(ex.last_smoke, {'status': 'FAIL'})
        self.assertIn('GET /assets/148ai-image-1.webp answered HTTP 404', report.failures[0].message)

    def test_a_jpeg_is_served_as_image_jpeg(self):
        # image weight (2026-11-26): a photo is carried as a JPEG when the JPEG is its smaller conversion (a textured
        # photo); which format wins is the converter's own test (test_web_rendition). Here the carried file is a JPEG
        # made directly, because what is checked is how the server answers for one.
        photo = jpeg_photo()
        from omni_prod.generated_images import _Transform
        repo = _Transform(None, [photo])(site(page_with(photo.marker), port=free_port()))
        self.assertEqual(photo.uri, 'assets/148ai-image-1.jpg')
        report, ex, _ = smoke(repo)
        self.assertTrue(report.passed, report.failures)

    def test_the_sandbox_service_writes_the_image_bytes(self):
        """FastAPI is not installed here: the runner's write is checked in its source (one call, on every file)."""
        tree = ast.parse((ROOT / 'omni_prod/sandbox_service.py').read_text(encoding='utf-8'))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, 'attr', '') in
                 ('write_text', 'write_bytes')]
        self.assertEqual([c.func.attr for c in calls], ['write_bytes'])
        self.assertEqual(ast.unparse(calls[0].args[0]), 'file_bytes(rel, content)')

    def test_the_sandbox_service_endpoint_writes_the_image_bytes(self):
        """The real POST /run of sandbox_service (signature, RunRequest, validate_snapshot, the write). Only the docker
        run is a double: it reads the source directory the endpoint wrote. Skipped, and said so, without FastAPI."""
        try:
            from fastapi.testclient import TestClient
            from omni_prod import sandbox_service
        except ImportError as exc:                                   # the CLAUDE.md §2.8 container: CI runs it
            self.skipTest(f'FastAPI is not installed: {exc}')
        from unittest import mock
        from omni_prod.remote_sandbox import sign_body
        hero, transform, _ = d5_image()
        repo = transform(site(page_with(hero.marker), port=free_port()))
        seen = {}

        def docker(*, source_dir, **_):
            seen.update({p.relative_to(source_dir).as_posix(): p.read_bytes() for p in Path(source_dir).rglob('*') if p.is_file()})
            return mock.Mock(returncode=0, stdout='ok', stderr='')

        secret = 's' * 40
        body = json.dumps({'repository': repo, 'argv': ['python', 'app.py'], 'build_id': 'bld_118'}).encode('utf-8')
        with mock.patch.dict(os.environ, {'OMNI_SANDBOX_SHARED_SECRET': secret}), \
                mock.patch.object(sandbox_service, 'run_sandbox', docker):
            r = TestClient(sandbox_service.app).post('/run', content=body, headers={'x-omni-signature': sign_body(secret, body)})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(seen[hero.uri], hero.data)                   # the image's bytes, not the envelope text
        self.assertEqual(seen['app.py'], repo['app.py'].encode('utf-8'))
        # a tampered envelope never reaches the write (one base64 character changed: the conversion's WebP ends in zero
        # bytes, so writing 'AAAAAAAA' over its last eight characters, as this did before 2026-11-26, changed nothing)
        env = repo[hero.uri]
        at = len(env) - 20
        bad = dict(repo, **{hero.uri: env[:at] + ('B' if env[at] != 'B' else 'C') + env[at + 1:]})
        body = json.dumps({'repository': bad, 'argv': ['python', 'app.py'], 'build_id': 'bld_118'}).encode('utf-8')
        seen.clear()
        with mock.patch.dict(os.environ, {'OMNI_SANDBOX_SHARED_SECRET': secret}), \
                mock.patch.object(sandbox_service, 'run_sandbox', docker):
            r = TestClient(sandbox_service.app).post('/run', content=body, headers={'x-omni-signature': sign_body(secret, body)})
        self.assertEqual(r.status_code, 400, r.text)
        self.assertEqual(seen, {})


# ---------------------------------------------------------------- the saved version, the preview, the export

class _Cursor:
    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append(' '.join(sql.split()))

    def fetchone(self):
        return None


class EveryPointCarriesIt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hero, _, _ = d5_image()
        cls.logo, cls.logo_bytes = logo_png()
        from omni_prod.generated_images import _Transform
        cls.port = 8000
        cls.repo = _Transform(cls.logo, [cls.hero])(site(page_with(cls.hero.marker, LOGO_MARKER), port=cls.port))
        cls.expected = {'assets/148ai-image-1.webp': ('image/webp', cls.hero.data),
                        'assets/148ai-logo.png': ('image/png', cls.logo_bytes)}

    def check_served(self, workdir):
        server = Serve(workdir)
        try:
            status, ctype, html = server.get('/')
            self.assertEqual(status, 200)
            self.assertNotIn(b'data:image', html)
            for path, (mime, data) in self.expected.items():
                status, ctype, body = server.get('/' + path)
                self.assertEqual((status, ctype), (200, mime), path)
                self.assertEqual(body, data, path)
        finally:
            server.stop()

    def test_the_saved_version_keeps_the_image_file(self):
        store = MemoryStore()
        ws = PostgresProjectWorkspace(pool=None, artifact_store=store)
        cur = _Cursor()
        version = ws.commit(project_id='prj_118', repository=self.repo, message='build', cur=cur)
        self.assertTrue(any(s.startswith('INSERT INTO project_versions') for s in cur.executed))
        loaded = ws._get_loader(version.artifact_key)()                 # what preview and export load later
        self.assertEqual(loaded, self.repo)
        for path, (_, data) in self.expected.items():
            self.assertEqual(RA.file_bytes(path, loaded[path]), data)

    def test_the_preview_work_directory_serves_the_image_as_a_file(self):
        started = {}

        def docker(argv, **kw):                     # no Docker daemon in this container; everything else is real
            if argv[:2] == ['docker', 'run']:
                src = next(a for a in argv if a.startswith('type=bind,src=')).split('src=', 1)[1].split(',', 1)[0]
                started['dir'] = src
                return subprocess.CompletedProcess(argv, 0, 'cid118\n', '')
            if argv[:2] == ['docker', 'port']:
                return subprocess.CompletedProcess(argv, 0, '127.0.0.1:49999\n', '')
            return subprocess.CompletedProcess(argv, 0, 'true 0\n', '')

        provider = DockerPreviewProvider(workspace=None, runner=docker, data_root='')
        result = provider.start(preview_id='prv_' + 'a' * 16, project_id='prj_118', version_id='v1',
                                repository=self.repo, persistent=False)
        try:
            self.assertEqual(result.workdir, started['dir'])
            for path, (_, data) in self.expected.items():
                self.assertEqual((Path(result.workdir) / path).read_bytes(), data)
            self.check_served(result.workdir)
        finally:
            provider.remove_workdir(result.workdir)

    def test_the_export_holds_the_image_files_and_the_exported_site_serves_them(self):
        engine = UnifiedOmniEngine()
        engine.workspace.commit(project_id='prj_118', repository=self.repo, message='build')
        blob = engine.export_zip(project_id='prj_118')
        with zipfile.ZipFile(io.BytesIO(blob)) as zf, tempfile.TemporaryDirectory() as out:
            for path, (_, data) in self.expected.items():
                self.assertEqual(zf.read(path), data, path)
            self.assertNotIn(b'data:image', zf.read('app.py'))
            zf.extractall(out)
            self.check_served(out)


# ---------------------------------------------------------------- loud, never silent; the model never sees the bytes

class LoudAndRedacted(unittest.TestCase):
    def test_a_tampered_image_is_refused_by_the_request_policy(self):
        hero, _, _ = d5_image()
        env = hero.carried.envelope
        bad = env[:-8] + ('A' if env[-9] != 'A' else 'B') + env[-7:]
        with self.assertRaises(SandboxRequestRejected):
            validate_snapshot({'app.py': 'x', hero.uri: bad})
        with self.assertRaises(SandboxRequestRejected):                   # an image may not hide outside assets/
            validate_snapshot({'app.py': 'x', 'bin/tool.webp': env})
        with self.assertRaises(RA.AssetCarryError):
            RA.zip_bytes({hero.uri: bad})

    def test_an_image_that_cannot_be_carried_stops_the_install(self):
        with self.assertRaises(RA.AssetCarryError):
            RA.envelope(b'GIF89a not carried', 'image/gif')
        with self.assertRaises(RA.AssetCarryError):
            RA.envelope(b'\xff\xd8\xff jpeg bytes', 'image/png')            # the type is what the bytes are

    def test_the_model_never_sees_or_keeps_the_image(self):
        from tests.test_repair_stop_loss import _Executor, _Repairer, _engine
        hero, transform, _ = d5_image()
        repo = transform({'app.py': f'<img src="{hero.marker}" alt="x">'})
        engine = _engine(_Repairer([]), _Executor())
        engine.repository_transform = transform
        summary = engine._repair_summary(repo)
        self.assertEqual([f['path'] for f in summary['files']], ['app.py'])
        self.assertNotIn(hero.uri, summary['_repository'])
        self.assertIn(hero.marker, summary['files'][0]['content'])
        self.assertNotIn(hero.carried.encoded[:64], json.dumps(summary, default=str))
        # a repair that writes over the image file cannot change it: the transform puts the verified file back
        broken = dict(repo, **{hero.uri: 'not an image', 'app.py': f'<img src="{hero.marker}" alt="y">'})
        self.assertEqual(transform(broken)[hero.uri], hero.carried.envelope)
        # failure text that carries a cut piece of the bytes reaches the model without it
        cut = hero.carried.envelope[1000:5000]
        self.assertNotIn(cut[100:200], transform.redact_text('trace ' + cut))


class APageWithNoImageIsUnchanged(unittest.TestCase):
    """Byte for byte: no transform is installed, and every point writes exactly the old bytes."""

    REPO = {'app.py': 'print("שלום")\n', 'index.html': '<!doctype html><html lang="he"><body>דף</body></html>',
            '.omni/project.json': '{"schema_version": 2}'}

    def test_no_transform_is_installed_when_the_plan_has_no_image(self):
        engine = SimpleNamespace(core=SimpleNamespace(executor=None, repository_transform=None))
        self.assertEqual(G.install(engine, prompt='p', plan=CapabilityPlan((), ()), evidence=None, store=None), 'p')
        self.assertIsNone(engine.core.repository_transform)

    def test_the_work_directory_and_the_export_hold_the_same_bytes_as_before(self):
        with tempfile.TemporaryDirectory() as root:
            RA.materialize(Path(root), self.REPO)
            for path, text in self.REPO.items():
                self.assertEqual((Path(root) / path).read_bytes(), text.encode('utf-8'))
        old = io.BytesIO()
        with zipfile.ZipFile(old, 'w', zipfile.ZIP_DEFLATED) as zf:      # the export as it was written before 118
            for path, content in sorted(self.REPO.items()):
                zf.writestr(path, content)
        new_zip, old_zip = zipfile.ZipFile(io.BytesIO(RA.zip_bytes(self.REPO))), zipfile.ZipFile(old)
        self.assertEqual([(i.filename, i.CRC, i.file_size, i.compress_type, i.external_attr, i.flag_bits)
                          for i in new_zip.infolist()],
                         [(i.filename, i.CRC, i.file_size, i.compress_type, i.external_attr, i.flag_bits)
                          for i in old_zip.infolist()])
        for name in old_zip.namelist():
            self.assertEqual(new_zip.read(name), old_zip.read(name))

    def test_the_smoke_of_a_page_without_images_is_unchanged(self):
        repo = site('<!doctype html><html><body><h1>דף</h1>' + '<p>טקסט אמיתי של העסק. </p>' * 30 + '</body></html>',
                    port=free_port())
        report, ex, runner = smoke(repo)
        self.assertTrue(report.passed, report.failures)
        sent = runner.payloads[0]['repository']
        self.assertEqual({p: sent[p] for p in repo}, repo)                     # the request carries the files as is
        self.assertFalse(any(p.startswith('assets/') for p in sent))
        self.assertIsNone(stdout_line(runner.stdouts[0], 'PREVIEW-ASSETS '))  # the asset check had nothing to do


# ---------------------------------------------------------------- review 2026-11-21: the points the first pass missed

# A site whose stylesheet is its own file in a sub-directory, and whose page may live behind a redirect of GET /.
APP_STATIC = r"""import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
TYPES = {".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".css": "text/css"}
HOME = %(home)r
HTML_CONTENT = %(html)r
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/" and HOME != "/":
            self.send_response(302)
            self.send_header("Location", HOME)
            self.end_headers()
            return
        full = os.path.normpath(path.lstrip("/"))
        if path == HOME:
            body, ctype = HTML_CONTENT.encode("utf-8"), "text/html; charset=utf-8"
        elif full.startswith(("assets" + os.sep, "static" + os.sep)) and os.path.isfile(full):
            with open(full, "rb") as fh:
                body = fh.read()
            ctype = TYPES.get(os.path.splitext(full)[1].lower(), "application/octet-stream")
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass
ThreadingHTTPServer(("0.0.0.0", int(os.environ["PORT"])), Handler).serve_forever()
"""
TEXT = '<h1>האטליז של סבא שמעון</h1>' + '<p>בשר טרי כל יום, קצבים עם ניסיון של שלושים שנה. </p>' * 20


def static_site(html: str, *, port: int, home: str = '/', css: str | None = None) -> dict:
    repo = site(html, port=port)
    repo['app.py'] = APP_STATIC % {'html': html, 'home': home}
    if css is not None:
        repo['static/style.css'] = css
    return repo


class EveryReferenceResolves(unittest.TestCase):
    """The smoke fetches the URL the page or the stylesheet REFERENCES, resolved as a browser resolves it -- not only
    /assets/<name>. A data URI worked from anywhere; a relative path does not."""

    @classmethod
    def setUpClass(cls):
        cls.hero, cls.transform, _ = d5_image()

    def test_an_image_in_a_stylesheet_in_a_sub_directory_is_reached(self):
        html = ('<!doctype html><html lang="he"><head><link rel="stylesheet" href="static/style.css"></head><body>'
                f'<img src="{self.hero.marker}" alt="הדלפק">{TEXT}</body></html>')
        repo = self.transform(static_site(html, port=free_port(),
                                          css='.hero{background:url(' + self.hero.marker + ') center/cover}'))
        self.assertIn('url(../assets/148ai-image-1.webp)', repo['static/style.css'])
        self.assertIn('src="assets/148ai-image-1.webp"', repo['app.py'])           # the root page is as before
        report, ex, runner = smoke(repo)
        self.assertTrue(report.passed, report.failures)
        self.assertEqual(stdout_line(runner.stdouts[0], 'PREVIEW-ASSET-REFS '), '1')   # both resolve to one URL
        # what the model reads has the marker back in both files, and no image file
        seen = self.transform.redact(repo)
        self.assertEqual(seen['static/style.css'], '.hero{background:url(' + self.hero.marker + ') center/cover}')
        self.assertIn(f'src="{self.hero.marker}"', seen['app.py'])
        self.assertNotIn(self.hero.uri, seen)

    def test_a_reference_that_resolves_to_a_404_fails_the_preview_loudly(self):
        """GET / redirects to /he/, so `assets/<name>` in the page is /he/assets/<name>: a broken image for the
        visitor, while /assets/<name> itself answers 200."""
        html = f'<!doctype html><html lang="he"><body><img src="{self.hero.marker}" alt="הדלפק">{TEXT}</body></html>'
        repo = self.transform(static_site(html, port=free_port(), home='/he/'))
        report, ex, runner = smoke(repo)
        self.assertFalse(report.passed)
        self.assertEqual(ex.last_smoke, {'status': 'FAIL'})
        message = report.failures[0].message
        self.assertIn('/he/ references assets/148ai-image-1.webp, which resolves to', message)
        self.assertIn('/he/assets/148ai-image-1.webp and failed', message)
        self.assertIn('the visitor sees a broken image', message)
        # /assets/<name> itself answers: the old check alone would have passed this site
        fine = self.transform(static_site(html, port=free_port()))
        report, _, runner = smoke(fine)
        self.assertTrue(report.passed, report.failures)
        self.assertEqual(stdout_line(runner.stdouts[0], 'PREVIEW-ASSET-REFS '), '1')

    def test_a_reference_in_a_script_template_literal_or_after_a_semicolon_is_read_whole(self):
        """The reference is read back from the name to its delimiter. A JS template literal (`...`) or a CSS
        declaration list (`;`) must end it, else the delimiter becomes part of the URL and a working image fails."""
        html = ('<!doctype html><html lang="he"><body><img id="h" alt="הדלפק">'
                f'<script>document.getElementById("h").src = `{self.hero.marker}`;</script>'
                f'<div style="color:red;background-image:url({self.hero.marker})"></div>{TEXT}</body></html>')
        repo = self.transform(static_site(html, port=free_port()))
        self.assertIn('`assets/148ai-image-1.webp`', repo['app.py'])
        report, _, runner = smoke(repo)
        self.assertTrue(report.passed, report.failures)
        self.assertEqual(stdout_line(runner.stdouts[0], 'PREVIEW-ASSET-REFS '), '1')


class TheOtherWriters(unittest.TestCase):
    """Every place that writes a repository to disk or prints it handles the image file (review 2026-11-21)."""

    def test_the_gate_regression_serves_an_approved_build_that_carries_an_image(self):
        from omni_prod import gate_regression
        hero, transform, _ = d5_image()
        html = f'<!doctype html><html lang="he"><body><img src="{hero.marker}" alt="הדלפק">{TEXT}</body></html>'
        repo = transform(site(html, port=free_port()))
        # the workflow reads the saved version: the zip the workspace wrote, every entry decoded as text
        ws = PostgresProjectWorkspace(pool=None, artifact_store=MemoryStore())
        saved = ws._get_loader(ws.commit(project_id='prj_gr', repository=repo, message='build', cur=_Cursor()).artifact_key)()
        self.assertTrue(RA.is_envelope(saved[hero.uri]))
        pages, verdict = gate_regression.served_page(saved)
        self.assertEqual(verdict, 'PREVIEW-SMOKE OK')
        self.assertIn('assets/148ai-image-1.webp', pages['/'])
        result = gate_regression.run(saved, REQUEST)
        self.assertTrue(result['served'], result)

    def test_a_logo_the_upload_accepts_is_carried(self):
        """2,000,001 bytes to the upload limit: accepted at upload, so it must build. Over the limit: loud."""
        import struct
        import zlib
        from omni_prod.attachments import MAX_BYTES

        def png(size: int) -> bytes:                    # a valid stored (uncompressed) PNG of exactly `size` bytes
            def chunk(tag, data):
                return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
            head = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 64, 64, 8, 2, 0, 0, 0))
            body = chunk(b'IDAT', zlib.compress(b''.join(b'\x00' + bytes(64 * 3) for _ in range(64)), 9))
            pad = size - len(head) - len(body) - 12 - 12
            return head + body + chunk(b'tEXt', b'c\x00' + b'x' * (pad - 2)) + chunk(b'IEND', b'')

        self.assertEqual(RA.MAX_ASSET_BYTES, MAX_BYTES)
        for size in (2_000_001, MAX_BYTES):
            data = png(size)
            self.assertEqual(len(data), size)
            t = logo_transform(data, 'image/png', hashlib.sha256(data).hexdigest())
            repo = t({'app.py': f'<img src="{LOGO_MARKER}" alt="לוגו">'})
            validate_snapshot(repo)                                        # the sandbox request carries it
            self.assertEqual(RA.file_bytes(t.uri, repo[t.uri]), data)
        over = png(MAX_BYTES + 1)
        with self.assertRaises(RA.AssetCarryError):
            logo_transform(over, 'image/png', hashlib.sha256(over).hexdigest())

    def test_the_visual_edit_preview_host_writes_through_the_one_writer(self):
        source = (ROOT / 'tools/ui_visual_edit/preview_host.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        launcher = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'launcher')
        calls = [ast.unparse(n) for n in ast.walk(launcher) if isinstance(n, ast.Call)]
        self.assertIn('materialize(Path(d), files)', calls)
        self.assertFalse([c for c in calls if c.startswith('open(') or '.write(' in c or 'write_text' in c], calls)

    def test_the_round_artifacts_print_shortens_an_image_file(self):
        """inspect-round-artifacts.yml (files_mode=all) prints every file in 3,500-character notes. The workflow's own
        elision lines are run on a real image file: it must print as one short note, not as its base64."""
        import re
        import textwrap
        yml = (ROOT / '.github/workflows/inspect-round-artifacts.yml').read_text(encoding='utf-8')
        start, end = yml.index('                  import base64 as _b, hashlib as _h, re as _re'), yml.index('                  chunks = [text[i:i + size]')
        hero, _, _ = d5_image()
        scope = {'text': hero.carried.envelope}
        exec(textwrap.dedent(yml[start:end]), scope)
        self.assertLess(len(scope['text']), 300)
        self.assertIn(f'<{len(hero.carried.encoded)} base64 chars; decoded sha256 {hashlib.sha256(hero.data).hexdigest()}>',
                      scope['text'])
        inline = {'text': 'x <img src="data:image/webp;base64,' + hero.carried.encoded + '"> y'}
        exec(textwrap.dedent(yml[start:end]), inline)                        # the 2026-11-14 case still holds
        self.assertLess(len(inline['text']), 300)


if __name__ == '__main__':
    unittest.main()
