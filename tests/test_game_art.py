"""The art layer of a 2D game (the owner, 2026-11-27, answer 11; warehouse 134 widened to generated art; plan S12.3-S12.4).

No browser needed: the schema (version 1 files play as before; version 2 adds the optional `art`), the deterministic fallback, the
checks every image passes, the provider source (the REAL PredictionImageProvider with only the HTTP call replaced), and what
the builder's executor does with a page that was edited by hand or cannot be played.

The browser tests (a game is PLAYED with its art, every role drawn, at a computer's width and a phone's) run where Chromium is:
browser-python's game-kit job (a skip fails there, tests/test_game_kit_in_ci.py) and here with OMNI_CHROMIUM.
"""
from __future__ import annotations

import copy
import functools
import hashlib
import http.server
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from omni_prod.game_kit import InvalidGame, KINDS, art as ART, build_html, validate
from omni_prod.game_kit.builder import DEFINITION_FILE, PAGE_FILE, GameProbeExecutor, game_engine
from omni_prod.game_kit.schema import ART_MAX_BYTES, SCHEMA, SCHEMA_V2
from omni_prod.repository_assets import envelope

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = {k: json.loads((ROOT / 'omni_prod/game_kit/samples' / f'{k}.json').read_text(encoding='utf-8')) for k in KINDS}

try:
    import playwright  # noqa: F401
    HAVE_BROWSER = True
except ImportError:          # pragma: no cover - v24-ci installs no Python playwright; browser-python does
    HAVE_BROWSER = False


def with_art(kind='platformer', source=None, theme=''):
    defn, files, report = ART.attach(copy.deepcopy(SAMPLES[kind]), source=source, theme=theme)
    return defn, files, report


class TheSchema(unittest.TestCase):
    def test_a_version_1_file_still_plays_as_it_did(self):
        for kind, d in SAMPLES.items():
            self.assertEqual(d['schema'], SCHEMA)
            self.assertIs(validate(d), d, kind)

    def test_a_version_2_file_is_version_1_plus_art(self):
        d, _, _ = with_art()
        self.assertEqual(d['schema'], SCHEMA_V2)
        self.assertIs(validate(d), d)

    def test_a_version_2_key_in_a_version_1_file_is_refused_not_ignored(self):
        d, _, _ = with_art()
        d['schema'] = SCHEMA
        with self.assertRaises(InvalidGame) as e:
            validate(d)
        self.assertIn("unknown key 'art'", ' | '.join(e.exception.problems))

    def test_version_2_still_checks_everything_version_1_checks(self):
        d, _, _ = with_art()
        d['palette']['bg'] = 'red'
        with self.assertRaises(InvalidGame) as e:
            validate(d)
        self.assertIn('palette.bg must be a colour', ' | '.join(e.exception.problems))

    def test_art_names_only_files_of_the_roles_under_assets(self):
        d, _, _ = with_art()
        for bad in ({'player': 'assets/148ai-enemy.png'}, {'player': 'https://x.example/p.png'}, {'player': '../p.png'},
                    {'player': 'data:image/png;base64,iVBORw0KGgo='}, {'boss': 'assets/148ai-boss.png'}, {'player': 3}):
            e = copy.deepcopy(d)
            e['art'].update(bad)
            with self.subTest(bad), self.assertRaises(InvalidGame):
                validate(e)
        e = copy.deepcopy(d)
        e['art'] = {}
        with self.assertRaises(InvalidGame):
            validate(e)


class TheFallback(unittest.TestCase):
    def test_the_same_definition_gives_the_same_bytes_and_another_seed_another_look(self):
        for kind, d in SAMPLES.items():
            self.assertEqual(ART.procedural(d), ART.procedural(copy.deepcopy(d)), kind)
        other = copy.deepcopy(SAMPLES['platformer'])
        other['seed'] += 1
        a, b = ART.procedural(SAMPLES['platformer']), ART.procedural(other)
        self.assertNotEqual(a['player'], b['player'])

    def test_every_role_is_a_real_image_and_sprites_have_transparency(self):
        for kind, d in SAMPLES.items():
            images = ART.procedural(d)
            self.assertEqual(set(images), set(ART.ART_ROLES))
            for role, data in images.items():
                width, height, alpha = ART.png_info(data)
                self.assertEqual(alpha, role not in ('background',), (kind, role))
                self.assertIsNone(ART.check_image(role, data, 'image/png'), (kind, role))
                self.assertLessEqual(len(data), ART_MAX_BYTES)

    def test_the_images_follow_the_palette(self):
        d = copy.deepcopy(SAMPLES['platformer'])
        a = ART.procedural(d)['player']
        d['palette']['player'] = '#00ff00'
        self.assertNotEqual(a, ART.procedural(d)['player'])

    def test_attach_with_no_source_is_all_procedural_and_says_so(self):
        d, files, report = with_art()
        self.assertEqual(set(report.sources.values()), {'procedural'})
        self.assertEqual(report.dropped, [])
        self.assertEqual(set(files), set(d['art'].values()))
        for path, (data, mime) in files.items():
            self.assertEqual(mime, 'image/png')
            self.assertEqual(hashlib.sha256(data).hexdigest(), next(h for r, h in report.sha256.items() if d['art'][r] == path))
            self.assertTrue(envelope(data, mime).startswith('148ai-binary:v1;mime=image/png;sha256='))

    def test_attach_refuses_a_definition_that_is_not_a_valid_version_1(self):
        d = copy.deepcopy(SAMPLES['runner'])
        d['kind'] = 'rpg'
        with self.assertRaises(InvalidGame):
            ART.attach(d)
        with self.assertRaises(ValueError):
            ART.attach(with_art()[0])


class TheChecks(unittest.TestCase):
    def png(self, w, h, alpha):
        return ART.encode_png(w, h, [bytes([200, 30, 30, 255] if alpha else [200, 30, 30]) * w] * h, alpha=alpha)

    def test_what_passes_and_what_is_dropped_and_why(self):
        ok = lambda role, data, mime='image/png': ART.check_image(role, data, mime)         # noqa: E731
        self.assertIsNone(ok('player', self.png(64, 64, True)))
        self.assertIsNone(ok('background', self.png(64, 64, False)))
        self.assertIsNone(ok('ground', self.png(64, 64, False)))                               # a tile may be opaque
        self.assertIn('transparency', ok('player', self.png(64, 64, False)))                   # it would draw as a box
        self.assertIn('transparency', ok('enemy', self.png(64, 64, False)))
        self.assertIn('outside', ok('player', self.png(8, 8, True)))
        self.assertIn('outside', ok('background', self.png(4000, 20, False)))
        self.assertIn('not a PNG', ok('player', b'GIF89a' + b'\0' * 100))
        self.assertIn('empty', ok('player', b''))
        self.assertIn('size bound', ok('background', b'\x89PNG\r\n\x1a\n' + b'\0' * ART_MAX_BYTES))
        self.assertIn('not used for art', ok('player', b'x', 'image/gif'))
        self.assertIn('unknown role', ok('boss', self.png(64, 64, True)))


class _Source:
    def __init__(self, images=None, errors=None):
        self.images, self.errors, self.asked = images or {}, errors or {}, []

    def image(self, role, theme):
        self.asked.append((role, theme))
        if role in self.errors:
            raise self.errors[role]
        return self.images[role]


class TheProviderLayer(unittest.TestCase):
    png = TheChecks.png

    def test_a_good_image_replaces_the_fallback_and_a_bad_one_is_dropped_with_its_reason(self):
        good = self.png(64, 64, True)
        source = _Source({'background': (self.png(96, 54, False), 'image/png'), 'player': (good, 'image/png'),
                          'enemy': (self.png(64, 64, False), 'image/png'),            # no transparency: dropped
                          'item': (b'not an image', 'image/png'), 'ground': (self.png(64, 64, False), 'image/png')},
                         errors={})
        d, files, report = with_art(source=source, theme='sunny meadow')
        self.assertEqual(report.sources, {'background': 'provider', 'player': 'provider', 'enemy': 'procedural',
                                          'item': 'procedural', 'ground': 'provider'})
        self.assertEqual({x['role'] for x in report.dropped}, {'enemy', 'item'})
        self.assertEqual(files[d['art']['player']][0], good)
        self.assertEqual({t for _, t in source.asked}, {'sunny meadow'})

    def test_a_provider_that_errors_never_fails_the_build_and_the_game_plays_procedurally(self):
        source = _Source(errors={r: RuntimeError('the provider said no') for r in ART.ART_ROLES})
        d, files, report = with_art(source=source)
        self.assertEqual(set(report.sources.values()), {'procedural'})
        self.assertEqual(len(report.dropped), len(ART.ART_ROLES))
        self.assertIn('the provider said no', report.dropped[0]['reason'])
        self.assertIs(validate(d), d)

    def test_the_images_of_one_game_stay_under_the_total_bound(self):
        big = ART.encode_png(256, 256, [os.urandom(256 * 4) for _ in range(256)], alpha=True)      # incompressible, over ART_MAX_BYTES?
        if len(big) > ART_MAX_BYTES:
            source = _Source({r: (big, 'image/png') for r in ART.ART_ROLES})
            _, _, report = with_art(source=source)
            self.assertEqual(set(report.sources.values()), {'procedural'})
            self.assertTrue(all('size bound' in x['reason'] for x in report.dropped))

    def test_the_real_provider_adapter_is_asked_once_per_role_with_a_journal_key_and_polled_a_bounded_number_of_times(self):
        from omni_prod.providers.image_provider import MemorySubmissionJournal
        from tests.test_m5_media_provider_adapters import ENV, FakePredictionAPI, _fetcher
        from omni_prod.providers.image_provider import ImageProviderConfig, PredictionImageProvider
        api = FakePredictionAPI(image=self.png(64, 64, True))
        journal = MemorySubmissionJournal()
        provider = PredictionImageProvider(
            config=ImageProviderConfig.from_env(dict(ENV)), resolve_reference=lambda ref: dict(ENV)[ref.split(':', 1)[1]],
            journal=journal, urlopen=api, sleep=lambda s: None, poll_interval_seconds=0.1, fetcher=_fetcher(api), spend_env=dict(ENV))
        source = ART.ProviderImageSource(provider, build_id='bld_art1', max_polls=5)
        d, files, report = with_art(source=source, theme='cartoon forest')
        self.assertEqual(len(api.created), 5, 'one prediction per role')
        prompts = [c['body']['input']['prompt'] for c in api.created]
        self.assertTrue(all('cartoon forest' in p and 'No text' in p for p in prompts))
        self.assertEqual(set(report.sources.values()), {'provider'})
        self.assertEqual(files[d['art']['player']][0], api.image)
        self.assertEqual(sorted(journal._rows), sorted(f'bld_art1:game-art:{r}' for r in ART.ART_ROLES))

    def test_a_provider_that_never_finishes_is_given_up_on_after_max_polls(self):
        class Never:
            def submit(self, requirement, *, idempotency_key):
                return object()

            def poll(self, handle):
                from omni_prod.provider_contracts import ProviderTaskState
                self.polls = getattr(self, 'polls', 0) + 1
                return ProviderTaskState('RUNNING', None)
        never = Never()
        _, _, report = with_art(source=ART.ProviderImageSource(never, build_id='bld_art2', max_polls=3), theme='x')
        self.assertEqual(never.polls, 3 * len(ART.ART_ROLES))
        self.assertTrue(all('after 3 polls' in x['reason'] for x in report.dropped))
        self.assertEqual(set(report.sources.values()), {'procedural'})

    def test_with_the_spend_switch_closed_the_real_provider_refuses_and_the_game_still_plays(self):
        from omni_prod.providers.image_provider import ImageProviderConfig, MemorySubmissionJournal, PredictionImageProvider
        from tests.test_m5_media_provider_adapters import ENV, FakePredictionAPI, _fetcher
        closed = dict(ENV, OMNI_ZERO_COST_MODE='1')
        api = FakePredictionAPI(image=self.png(64, 64, True))
        provider = PredictionImageProvider(
            config=ImageProviderConfig.from_env(dict(ENV)), resolve_reference=lambda ref: dict(ENV)[ref.split(':', 1)[1]],
            journal=MemorySubmissionJournal(), urlopen=api, sleep=lambda s: None, fetcher=_fetcher(api), spend_env=closed)
        _, _, report = with_art(source=ART.ProviderImageSource(provider, build_id='bld_art3'))
        self.assertEqual(api.created, [], 'nothing was sent to the provider')
        self.assertEqual(set(report.sources.values()), {'procedural'})
        self.assertEqual(len(report.dropped), 5)


class TheExecutor(unittest.TestCase):
    """GameProbeExecutor without a browser: what it refuses before it plays."""

    def repo(self):
        d, files, report = with_art()
        from omni_prod.game_kit.builder import _files
        return d, _files(d, files, report)

    def run_it(self, repo, probe):
        return GameProbeExecutor(probe).execute(repository=repo, spec=None)

    def test_a_page_that_is_what_the_assembler_makes_is_played_with_its_art_files(self):
        d, repo = self.repo()
        seen = {}

        def probe(html, defn, *, files=None):
            seen.update(files=files, defn=defn)
            return {'ok': True, 'findings': [], 'measures': {'computer': {}, 'phone': {}}}
        report = self.run_it(repo, probe)
        self.assertTrue(report.passed)
        self.assertEqual(set(seen['files']), set(d['art'].values()))
        self.assertTrue(all(isinstance(b, bytes) and b.startswith(b'\x89PNG') for b in seen['files'].values()))

    def test_a_platform_addition_to_the_page_is_fine_but_a_changed_game_is_not(self):
        d, repo = self.repo()
        probe = lambda html, defn, *, files=None: {'ok': True, 'findings': [], 'measures': {}}          # noqa: E731
        added = dict(repo, **{PAGE_FILE: repo[PAGE_FILE].replace('<title>', '<meta property="og:title" content="x"><title>')})
        self.assertTrue(self.run_it(added, probe).passed)
        edited = dict(repo, **{PAGE_FILE: repo[PAGE_FILE].replace('"time_limit_s": 90', '"time_limit_s": 9999')})
        self.assertNotEqual(edited[PAGE_FILE], repo[PAGE_FILE])
        report = self.run_it(edited, probe)
        self.assertFalse(report.passed)
        self.assertIn('edited by hand', report.failures[0].message)
        stripped = dict(repo, **{PAGE_FILE: repo[PAGE_FILE].replace('(function () {', '(function () { /* tampered */', 1)})
        self.assertFalse(self.run_it(stripped, probe).passed)

    def test_an_invalid_definition_a_missing_image_and_a_wrong_image_fail_before_any_play(self):
        d, repo = self.repo()
        called = []
        probe = lambda *a, **k: called.append(1) or {'ok': True, 'findings': [], 'measures': {}}        # noqa: E731
        bad_def = dict(repo, **{DEFINITION_FILE: json.dumps({**d, 'kind': 'rpg'})})
        missing = {k: v for k, v in repo.items() if k != d['art']['player']}
        wrong = dict(repo, **{d['art']['player']: envelope(ART.procedural(d)['item'], 'image/png').replace('sha256=', 'sha256=0')})
        for name, r in (('invalid', bad_def), ('missing', missing), ('wrong', wrong), ('no definition', {PAGE_FILE: 'x'})):
            with self.subTest(name):
                report = self.run_it(r, probe)
                self.assertFalse(report.passed)
        self.assertEqual(called, [])

    def test_the_probes_findings_become_failures_and_a_probe_that_cannot_run_is_a_failure_not_a_pass(self):
        d, repo = self.repo()
        findings = {'ok': False, 'measures': {}, 'findings': [{'kind': 'no_touch_controls', 'where': 'phone', 'message': 'a'},
                                                               {'kind': 'score_never_rose', 'where': 'computer', 'message': 'b'}]}
        report = self.run_it(repo, lambda html, defn, *, files=None: findings)
        self.assertEqual([(f.acceptance_id, f.message.split(' ')[0]) for f in report.failures],
                         [('A2', 'no_touch_controls'), ('A1', 'score_never_rose')])

        def boom(html, defn, *, files=None):
            raise OSError('chromium crashed')
        report = self.run_it(repo, boom)
        self.assertFalse(report.passed)
        self.assertIn('NOT_RUN', report.failures[0].message)

    def test_without_a_browser_on_this_machine_the_game_is_not_ready(self):
        import builtins
        d, repo = self.repo()
        real = builtins.__import__

        def no_playwright(name, *a, **k):
            if name == 'playwright' or name.startswith('playwright.'):
                raise ImportError('no playwright')
            return real(name, *a, **k)
        builtins.__import__ = no_playwright
        try:
            report = GameProbeExecutor().execute(repository=repo, spec=None)
        finally:
            builtins.__import__ = real
        self.assertFalse(report.passed)
        self.assertIn('NOT_RUN', report.failures[0].message)


class TheSystemPrompt(unittest.TestCase):
    def test_what_the_model_is_told_matches_what_the_schema_checks(self):
        from omni_prod.game_kit import schema
        from omni_prod.game_kit.builder import _SYSTEM
        for kind in schema.KINDS:
            self.assertIn(kind, _SYSTEM)
        told = _SYSTEM.split('using only the tiles ')[1].split(']')[0].split()
        self.assertEqual(set(told), schema.PLATFORM_TILES, 'the tiles the model is told about are the tiles the schema allows')
        for key in schema.TOP_KEYS - {'levels', 'schema', 'kind'}:
            self.assertIn(key, _SYSTEM)
        self.assertIn(schema.SCHEMA, _SYSTEM)


# ---- played in a real Chromium --------------------------------------------------------------------------------------
@unittest.skipUnless(HAVE_BROWSER, 'NOT_RUN: needs Python playwright (runs in browser-python game-kit)')
class ThePlayedGame(unittest.TestCase):
    """Every kind is played with art, at a computer's width and a phone's: the probe's own verdict, and the runtime's
    window `__game.art()` says every role the kind draws was drawn from a loaded image (not the flat shape)."""
    DRAWN = {'platformer': ('background', 'player', 'enemy', 'item', 'ground'), 'shooter': ('background', 'player', 'enemy'),
             'runner': ('background', 'player', 'item'), 'match': ('background',)}

    def serve(self, defn, files):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        Path(d.name, 'index.html').write_text(build_html(defn), encoding='utf-8')
        for path, (data, _mime) in files.items():
            Path(d.name, path).parent.mkdir(parents=True, exist_ok=True)
            Path(d.name, path).write_bytes(data)

        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path == '/favicon.ico':
                    self.send_response(204)
                    self.end_headers()
                else:
                    super().do_GET()
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=d.name))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        return f'http://127.0.0.1:{server.server_port}/index.html'

    def play(self, defn, files, *, phone):
        from omni_prod.game_kit.probe import PHONE, DESKTOP, _launch
        from playwright.sync_api import sync_playwright
        url = self.serve(defn, files)
        with sync_playwright() as p:
            browser = _launch(p)
            try:
                opts = {'viewport': PHONE if phone else DESKTOP}
                if phone:
                    opts.update(has_touch=True, is_mobile=True)
                page = browser.new_context(**opts).new_page()
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
                page.goto(url)
                page.wait_for_function('() => window.__game && window.__game.state().frames > 3', timeout=10000)
                page.wait_for_function(f'() => window.__game.art().loaded.length === {len(defn["art"])}', timeout=10000)
                page.keyboard.press('Enter') if not phone else page.locator('#screen-btn').tap()
                page.wait_for_timeout(200)
                page.evaluate('() => window.__game.fastForward(2)')
                page.wait_for_timeout(250)                       # a few frames render after the fast-forward
                art = page.evaluate('() => window.__game.art()')
                shot = page.screenshot()
                return art, errors, shot
            finally:
                browser.close()

    def test_every_kind_is_played_with_its_art_and_every_role_it_draws_is_drawn_from_an_image(self):
        shots = os.environ.get('OMNI_GAME_SHOTS')
        for kind in KINDS:
            defn, files, report = with_art(kind)
            for phone in (False, True):
                with self.subTest(kind=kind, phone=phone):
                    art, errors, shot = self.play(defn, files, phone=phone)
                    self.assertEqual(errors, [])
                    self.assertEqual(sorted(art['declared']), sorted(defn['art']))
                    self.assertEqual(sorted(art['loaded']), sorted(defn['art']), 'every image loaded')
                    for role in self.DRAWN[kind]:
                        self.assertGreater(art['drawn'][role], 0, f'{kind}: {role} was never drawn from its image')
                    if shots:
                        Path(shots, f'{kind}-{"phone" if phone else "computer"}.png').write_bytes(shot)

    def test_a_version_1_game_draws_no_image_and_plays_exactly_as_before(self):
        defn = copy.deepcopy(SAMPLES['platformer'])
        from omni_prod.game_kit.probe import _launch
        from playwright.sync_api import sync_playwright
        url = self.serve(defn, {})
        with sync_playwright() as p:
            browser = _launch(p)
            try:
                page = browser.new_context().new_page()
                page.goto(url)
                page.wait_for_function('() => window.__game && window.__game.state().frames > 3', timeout=10000)
                page.keyboard.press('Enter')
                page.evaluate('() => window.__game.fastForward(1)')
                self.assertEqual(page.evaluate('() => window.__game.art()'), {'declared': [], 'loaded': [], 'drawn': {}})
            finally:
                browser.close()

    def test_the_probe_plays_a_game_with_art_and_passes_it(self):
        from omni_prod.game_kit.probe import probe_html
        for kind in ('platformer', 'runner'):
            defn, files, _ = with_art(kind)
            result = probe_html(build_html(defn), defn, files={p: d for p, (d, _m) in files.items()})
            self.assertTrue(result['ok'], (kind, result['findings']))
            self.assertGreaterEqual(result['measures']['computer']['fps'], 30)

    def test_the_probe_still_reports_a_blank_game_when_the_art_is_missing_files(self):
        """A page that names images that do not exist must not pass as if it had them: the browser reports the 404s."""
        from omni_prod.game_kit.probe import probe_html
        defn, files, _ = with_art('runner')
        result = probe_html(build_html(defn), defn, files={'assets/unrelated.png': b'x'})
        self.assertFalse(result['ok'])
        self.assertIn('page_error', {f['kind'] for f in result['findings']})


class TheProbesServer(unittest.TestCase):
    """The server the probe serves a game with art from (no browser needed). A browser asks for /favicon.ico by itself and
    the game has none: the 404 would be a console error that is not the game's. Whether a given Chromium asks is its own
    business (the headless shell of CI does not), so what is tested is the server: the answer is 204, the page is served."""

    def test_the_favicon_a_browser_asks_for_is_answered_empty_not_with_a_404(self):
        import urllib.request
        from omni_prod.game_kit.probe import serve_game
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'index.html').write_text('<!doctype html><title>g</title>', encoding='utf-8')
            server, url = serve_game(d)
            self.addCleanup(lambda: (server.shutdown(), server.server_close()))
            with urllib.request.urlopen(url.replace('index.html', 'favicon.ico'), timeout=10) as r:
                self.assertEqual((r.status, r.read()), (204, b''))
            with urllib.request.urlopen(url, timeout=10) as r:
                self.assertEqual((r.status, b'<title>g</title>' in r.read()), (200, True))


if __name__ == '__main__':
    unittest.main()
