"""The owner's build bld_ab78f528 (2026-11-22, production UI, failed after 5 repair rounds, $1.53).

Its server served the generated image (preview smoke PASS) and two of our own checks still failed it in turns:
  * the consistency gate: 'acceptance step s4 calls /assets/148ai-image-1.webp but no server route handles it';
  * the image check: 'generated image ... is not on the page' whenever the page wrote '/assets/...'.
And the route: it went to the old path as 'approved_windows' without saying which window.

The fixtures are the build's own files, read back from production (build-evidence run 45014896178, read-only):
app.py is 3,803 characters, the length that run printed; project.json is the manifest it printed.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

from omni_prod.consistency_gate import scan
from omni_prod.generated_images import GeneratedImage, placement
from omni_prod.repository_assets import envelope

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'tests' / 'fixtures' / 'owner_build_ab78f528'
APP = (FIX / 'app.py').read_text(encoding='utf-8')
MANIFEST = (FIX / 'project.json').read_text(encoding='utf-8')
WEBP = b'RIFF\x24\x00\x00\x00WEBPVP8 \x18\x00\x00\x00' + b'\x30\x01\x00\x9d\x01\x2a\x01\x00\x01\x00' + b'\x00' * 14
S4 = 'acceptance step s4 calls /assets/148ai-image-1.webp but no server route handles it'


def repo(manifest: str = MANIFEST, **files) -> dict:
    out = {'app.py': APP, '.omni/project.json': manifest, 'assets/148ai-image-1.webp': envelope(WEBP, 'image/webp')}
    out.update(files)
    return {k: v for k, v in out.items() if v is not None}


def with_step(**step) -> str:
    plan = json.loads(MANIFEST)
    plan['web_saas_acceptance']['personas'][0]['steps'][3].update(step)
    return json.dumps(plan)


def routes(r: dict) -> list[str]:
    return [f.message for f in scan(r).blocking if f.check == 'routes']


class TheFixturesAreTheProductionFiles(unittest.TestCase):
    def test_lengths_and_digests(self):
        self.assertEqual(len(APP), 3803)          # the length build-evidence printed for app.py
        self.assertEqual(hashlib.sha256(APP.encode()).hexdigest()[:16], '7257d00c7337272a')
        self.assertEqual(hashlib.sha256(MANIFEST.encode()).hexdigest()[:16], '4b92baf83600ddec')


class TheConsistencyGate(unittest.TestCase):
    def test_a_step_that_gets_the_carried_image_is_not_a_missing_route(self):
        self.assertEqual(routes(repo()), [])

    def test_the_real_server_does_serve_it(self):
        """Run the build's own app.py with the carried file on disk: GET /assets/148ai-image-1.webp is 200 image/webp,
        so the gate's finding was false. (The run-time proof of every such step stays with the step itself and the
        preview smoke; the gate only stops blocking what it cannot read.)"""
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'app.py').write_text(APP, encoding='utf-8')
            Path(tmp, 'page.py').write_text('def render_page():\n    return "<html></html>"\n', encoding='utf-8')
            Path(tmp, 'assets').mkdir()
            Path(tmp, 'assets', '148ai-image-1.webp').write_bytes(WEBP)
            with socket.socket() as s:
                s.bind(('127.0.0.1', 0))
                port = s.getsockname()[1]
            proc = subprocess.Popen([sys.executable, 'app.py'], cwd=tmp, env={**os.environ, 'PORT': str(port)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(100):                   # bounded: at most 10 s for the server to listen
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{port}/assets/148ai-image-1.webp', timeout=2) as r:
                            self.assertEqual((r.status, r.headers['Content-Type'], r.read()), (200, 'image/webp', WEBP))
                            break
                    except (ConnectionError, OSError):
                        time.sleep(0.1)
                else:
                    self.fail('the build server never answered')
            finally:
                proc.terminate()
                proc.wait(timeout=10)

    def test_everything_else_is_still_judged(self):
        cases = {
            'the file is not in the repository': repo(**{'assets/148ai-image-1.webp': None}),
            'the file is text, not the carried envelope': repo(**{'assets/148ai-image-1.webp': 'not an image'}),
            'a POST': repo(with_step(method='POST')),
            'a HEAD': repo(with_step(method='HEAD')),
            'another directory': repo(with_step(path='/static/148ai-image-1.webp'),
                                      **{'static/148ai-image-1.webp': envelope(WEBP, 'image/webp')}),
            'a sub-directory': repo(with_step(path='/assets/x/148ai-image-1.webp'),
                                    **{'assets/x/148ai-image-1.webp': envelope(WEBP, 'image/webp')}),
            'a query': repo(with_step(path='/assets/148ai-image-1.webp?v=2')),
            'not an image suffix': repo(with_step(path='/assets/148ai-asset-manifest.json'),
                                        **{'assets/148ai-asset-manifest.json': envelope(WEBP, 'image/webp')}),
        }
        for why, r in cases.items():
            with self.subTest(why):
                self.assertTrue(routes(r), why)

    def test_the_exemption_itself_refuses_a_hidden_name(self):
        # '/assets/.webp' is then judged by the old reading (which happens to find "assets" and ".webp" quoted in this
        # server); the exemption must not be what lets it through.
        from omni_prod.consistency_gate import _carried_image
        r = repo(**{'assets/.webp': envelope(WEBP, 'image/webp')})
        self.assertFalse(_carried_image({'method': 'GET', 'path': '/assets/.webp'}, r))
        self.assertTrue(_carried_image({'method': 'GET', 'path': '/assets/148ai-image-1.webp'}, r))
        self.assertTrue(_carried_image({'path': '/assets/148ai-image-1.webp'}, r))      # no method means GET

    def test_a_missing_api_route_is_still_a_missing_route(self):
        r = repo(with_step(path='/api/bookings'))
        self.assertEqual(routes(r), ['acceptance step s4 calls /api/bookings but no server route handles it'])

    def test_on_main_this_was_the_production_failure(self):
        """The finding the build died on, word for word, is what the gate says when the step is not exempt."""
        r = repo(**{'assets/148ai-image-1.webp': 'plain text'})
        self.assertIn(S4, routes(r))


def image(index: int = 1) -> GeneratedImage:
    return GeneratedImage(index=index, requirement_id='asset-002', purpose='hero/brand visual', mime='image/webp',
                          width=1344, height=768, sha256='0' * 64, alt='מספרה מוארת עם כיסא עבודה ומראה גדולה',
                          data=WEBP)


def page(src: str, alt: str = 'מספרה מוארת') -> dict:
    return {'page.py': f'PAGE_HTML = """<!DOCTYPE html><html lang="he" dir="rtl"><body>'
                       f'<img src="{src}" width="1344" height="768" alt="{alt}"></body></html>"""\n'}


class TheImageCheck(unittest.TestCase):
    def test_the_forms_a_browser_reads_as_the_file(self):
        for src in ('assets/148ai-image-1.webp', '/assets/148ai-image-1.webp', './assets/148ai-image-1.webp',
                    '/assets/148ai-image-1.webp?v=2', 'assets/148ai-image-1.webp#top', '148ai-asset://image/1'):
            with self.subTest(src):
                self.assertEqual(placement(page(src), image()), 'ok')

    def test_never_another_file(self):
        for src in ('../assets/148ai-image-1.webp', '//assets/148ai-image-1.webp', '//cdn.example/assets/148ai-image-1.webp',
                    'https://example.com/assets/148ai-image-1.webp', '/he/assets/148ai-image-1.webp',
                    '148ai-image-1.webp', 'assets/148ai-image-11.webp', 'assets/148ai-image-2.webp',
                    '/static/148ai-image-1.webp', 'x/assets/148ai-image-1.webp', '148ai-asset://image/11'):
            with self.subTest(src):
                self.assertEqual(placement(page(src), image()), 'missing')

    def test_an_empty_alt_is_still_no_alt(self):
        self.assertEqual(placement(page('/assets/148ai-image-1.webp', alt=''), image()), 'no_alt')

    def test_the_two_checks_now_agree_on_one_page(self):
        """The seesaw of rounds 0-3: with the s4 step in the manifest, 'assets/x' in the page failed the routes check
        (the server text never held '/assets/x') and '/assets/x' failed the image check. Both forms now pass both."""
        for src in ('assets/148ai-image-1.webp', '/assets/148ai-image-1.webp'):
            with self.subTest(src):
                r = repo(**page(src))
                self.assertEqual(placement(r, image()), 'ok')
                self.assertEqual(routes(r), [])


class TheRouteNamesTheWindow(unittest.TestCase):
    def test_the_owners_two_windows_are_named(self):
        from unittest import mock
        from omni_prod import site_content
        from omni_prod.window_catalog import prompt_lines
        prompt = ('אתר תדמית למספרה "סטודיו נועה", רחוב הרצל 12, חולון. טלפון 03-5551234.\n'
                  '--- Approved project brief (binding; fingerprint 0123456789abcdef) ---\n'
                  'Sign-in: NONE. Do not add login.\nDo not store personal or contact details of people.\n'
                  'Product kind: CONTENT-ONLY website.\n' + '\n'.join(prompt_lines(['cookie_banner', 'question_widget'])))
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
            route = site_content.decide(prompt)
        self.assertEqual((route.route, route.reason), ('legacy', 'approved_windows: cookie_banner, question_widget'))


if __name__ == '__main__':
    unittest.main()
