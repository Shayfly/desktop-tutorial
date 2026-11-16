"""The rights gate, G5 (the owner, 2026-11-16): the source of every asset -- font, image, audio -- is known, and an
unknown right blocks; it is never assumed. The gate comes before the agent (A7) that will use it.

Each unit's broken fixture is the real production page of the butcher build, as the model wrote it, changed in one
place; G5, in its default mode, fails the build on it, and a repair to the unchanged page passes.

Real path: the units' probes on the recorded page, gate.install on the real AutonomousProductEngine, and -- for the
as-written view -- the worker's own install_main_image on the production contract row of "148 דלתות", whose transform
puts the photo's bytes in before the sandbox and whose redaction gives the gate the page as written.
"""
from __future__ import annotations

import copy
import inspect
import json
import os
import unittest
from unittest import mock

from omni_prod import rights_sources as R
from omni_prod import skill_units as U
from omni_prod.autonomous_core import AutonomousProductEngine
from omni_prod.skill_units import gate as G
from tests.test_contract_prompt_readers import (MARKER, PHOTO_SHA, PHOTO_URI, PROD_SHA, _Recording, contract,
                                                engine_for, hero, worker_install)
from tests.test_skill_gates import BUTCHER, _Arch, _Files, _Sandbox, as_app_py

RIGHTS = ['rights_font_source', 'rights_image_source', 'rights_media_source']
PLACEHOLDER = 'data:image/gif;base64,R0lGODlhAQABAAAAACw='         # stands for the generated hero in the recorded page
AS_WRITTEN = BUTCHER['page'].replace(PLACEHOLDER, '148ai-asset://image/1')


def install_g5(engine):
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop('OMNI_GATE_G5', None)
        return G.install(engine, 'G5')


def build(page):
    rep = _Files({'app.py': as_app_py(AS_WRITTEN)})
    e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'app.py': as_app_py(page)}), repairer=rep,
                                executor=_Sandbox(), max_repair_rounds=2)
    install_g5(e)
    return e.build('a page'), rep


class TheRightsGate(unittest.TestCase):
    def test_the_gate_is_three_units_and_blocks_by_default(self):
        self.assertEqual(G.gate_units('G5'), RIGHTS)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_GATE_G5', None)
            self.assertEqual(G.mode('G5'), 'block')

    def test_the_recorded_page_is_the_production_page_as_written(self):
        self.assertIn('bld_83529c132a864075945080e9390484cb', BUTCHER['_source'])
        self.assertEqual(BUTCHER['page'].count(PLACEHOLDER), 1)
        for unit in RIGHTS:
            [(_, page, _)] = [f for f in U.fixtures(unit, 'ok') if f[0] == 'butcher_as_written.html']
            self.assertEqual(page, AS_WRITTEN)

    def test_each_unit_falls_on_the_real_page_changed_in_one_place(self):
        for unit in RIGHTS:
            broken = U.fixtures(unit, 'broken')
            self.assertGreaterEqual(len(broken), 2)
            for name, page, expected in broken:
                with self.subTest(unit=unit, fixture=name):
                    result, rep = build(page)
                    msgs = {f['acceptance_id']: f['message'] for f in rep.failures[0]}
                    self.assertEqual(list(msgs), [f'gate-G5-{unit}'])            # that unit, and no other
                    self.assertTrue(msgs[f'gate-G5-{unit}'].startswith(expected['code']), msgs)
                    self.assertEqual((result.status, result.repair_rounds), ('ready', 1))

    def test_the_unchanged_page_passes_with_its_two_assets_known(self):
        result = G.check('G5', {'app.py': as_app_py(AS_WRITTEN)})
        self.assertEqual(result['status'], 'pass', result['failures'])
        self.assertEqual([(a['kind'], a['source']) for a in R.ledger(AS_WRITTEN)],
                         [('font', 'google_fonts'), ('image', 'platform_generated')])

    def test_a_finding_never_carries_the_bytes(self):
        big = hero('data:image/png;base64,' + 'A' * 50000)
        [finding] = U.run('rights_image_source', big)['findings']
        self.assertLess(len(str(finding)), 300)
        self.assertIn('(50022 characters)', finding['where'])


class ThePageAsWritten(unittest.TestCase):
    """The platform's own photo reaches the sandbox as bytes, and the gate knows where those bytes came from."""

    def _engine(self, sandbox):
        engine = engine_for(hero(MARKER), sandbox=sandbox)
        install_g5(engine)                                              # inside, as the worker installs it
        worker_install(engine, contract().prompt.replace(PROD_SHA, PHOTO_SHA))
        return engine

    def test_the_customers_photo_passes_and_the_sandbox_got_its_bytes(self):
        sandbox = _Recording()
        engine = self._engine(sandbox)
        result = engine.build('x')
        self.assertIn(f'src="{PHOTO_URI}"', sandbox.seen[0]['index.html'])     # the sandbox: the bytes
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0))
        self.assertEqual(G.report(engine)['G5'], {'mode': 'block', 'status': 'pass', 'failures': []})

    def test_the_same_bytes_with_no_record_of_their_source_block(self):
        # no photo was bound: the page carries a raster the platform did not supply
        engine = engine_for(hero(PHOTO_URI), hero('148ai-asset://image/1'))
        install_g5(engine)
        result = engine.build('x')
        first = engine.repairer.failures[0]
        self.assertEqual([f['acceptance_id'] for f in first], ['gate-G5-rights_image_source'])
        self.assertIn('bytes embedded in the page that the platform did not supply', first[0]['message'])
        self.assertEqual((result.status, result.repair_rounds), ('ready', 1))

    def test_a_transform_that_invents_its_result_is_not_followed(self):
        engine = mock.MagicMock()
        install_g5(engine)
        gate = engine.core.executor                                     # a MagicMock engine: its core is a mock too
        self.assertIsInstance(gate, G.SkillGateExecutor)
        self.assertEqual(gate.view({'index.html': 'x'}), {'index.html': 'x'})


class TheInventory(unittest.TestCase):
    def kinds(self, html):
        return [(a['kind'], a['ref'], a['source']) for a in R.ledger(html)]

    def test_every_way_a_page_carries_an_image(self):
        page = ('<link rel="icon" href="/favicon.ico"><meta property="og:image" content="https://x.test/share.png">'
                '<img src="148ai-asset://upload/2" srcset="https://cdn.test/a.webp 1x, pic@2x.jpg 2x">'
                '<picture><source srcset="https://cdn.test/b.avif"></picture>'
                '<div style="background-image:url(\'https://cdn.test/bg.jpg\')"></div>'
                '<video poster="poster.png"></video>'
                '<script>const gallery = ["https://cdn.test/g1.jpeg"];</script>')
        refs = {r for k, r, s in self.kinds(page) if k == 'image' and s is None}
        self.assertEqual(refs, {'/favicon.ico', 'https://x.test/share.png', 'https://cdn.test/a.webp', 'pic@2x.jpg',
                                'https://cdn.test/b.avif', 'https://cdn.test/bg.jpg', 'poster.png',
                                'https://cdn.test/g1.jpeg'})
        self.assertIn(('image', '148ai-asset://upload/2', 'customer_upload'), self.kinds(page))

    def test_what_the_build_draws_itself_is_known(self):
        page = ('<svg viewBox="0 0 1 1"><path d="M0 0h1v1z" fill="url(#g)"/></svg><img src="icons/phone.svg" alt="">'
                '<img src="data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22/>" alt="">'
                '<img src="148ai-asset://logo" alt="logo">')
        self.assertEqual({s for _, _, s in self.kinds(page)}, {'authored_svg', 'customer_upload'})
        self.assertEqual(U.run('rights_image_source', page), {'status': 'pass'})

    def test_fonts(self):
        loaded = ('<link rel="preload" as="font" href="https://fonts.gstatic.com/s/heebo/v1/x.woff2">'
                  '<style>@import url("https://fonts.googleapis.com/css2?family=Rubik");'
                  '@font-face{font-family:X;src:url(data:font/woff2;base64,AAAA) format("woff2")}'
                  'body{font-family:"Helvetica Neue",Gotham,Arial}</style>'
                  '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">'
                  '<link rel="stylesheet" href="/static/site.css"><link rel="preconnect" href="https://fonts.gstatic.com">')
        got = [(r[:40], s) for k, r, s in self.kinds(loaded) if k == 'font']
        self.assertEqual(got, [('https://fonts.gstatic.com/s/heebo/v1/x.w', 'google_fonts'),
                               ('https://cdnjs.cloudflare.com/ajax/libs/f', None),
                               ('data:font/woff2;base64,… (27 characters)', None),
                               ('https://fonts.googleapis.com/css2?family', 'google_fonts')])
        # a font only NAMED is a system font: nothing is loaded, nothing is judged; a local stylesheet is the build's
        self.assertEqual(U.run('rights_font_source', '<style>body{font-family:"Helvetica Neue",Gotham}</style>'
                                                     '<link rel="stylesheet" href="/static/site.css">'), {'status': 'pass'})

    def test_audio_and_video_have_no_known_source_yet(self):
        for page in ('<audio controls><source src="song.mp3" type="audio/mpeg"></audio>',
                     '<video src="https://cdn.test/clip.mp4"></video>',
                     '<script>new Audio("click.wav").play()</script>',
                     '<script>const a = new Audio(); a.src = sound;</script>',
                     '<iframe src="https://player.vimeo.com/video/1"></iframe>',
                     '<embed src="intro.ogg">'):
            with self.subTest(page=page[:40]):
                self.assertEqual(U.run('rights_media_source', page)['code'], 'MEDIA_SOURCE_UNKNOWN')
        self.assertEqual(U.run('rights_media_source', '<iframe src="https://www.google.com/maps/embed?pb=1"></iframe>'),
                         {'status': 'pass'})                                        # a map is not media

    def test_what_is_not_read_is_skipped_not_guessed(self):
        page = ('<!-- <img src="https://cdn.test/old.png"> --><img src="${item.src}" alt=""><img src="{{ photo }}" alt="">'
                '<a href="#top">top</a><a href="mailto:a@b.test">mail</a>')
        self.assertEqual(R.inventory(page), [])

    def test_an_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            R.unknown('<p></p>', 'icon')


class TheRegistry(unittest.TestCase):
    def test_every_source_states_its_basis(self):
        data = R.load()
        self.assertEqual(set(data['sources']), {'customer_upload', 'platform_generated', 'authored_svg', 'google_fonts'})
        for sid, entry in data['sources'].items():
            with self.subTest(sid):
                self.assertTrue(all(entry[k] for k in R.ENTRY_KEYS))
                self.assertRegex(entry['read_on'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertIn('developers.google.com/fonts/faq', data['sources']['google_fonts']['basis'])
        self.assertIn('flux-schnell', data['sources']['platform_generated']['basis'])
        self.assertNotIn('media', {k for e in data['sources'].values() for k in e['kinds']})   # no audio source yet

    def test_a_source_without_its_basis_is_refused(self):
        data = json.loads(R.DATA.read_text(encoding='utf-8'))
        broken = copy.deepcopy(data)
        broken['sources']['pixabay'] = {'kinds': ['media'], 'match': {'hosts': ['cdn.pixabay.com']}, 'right': 'free'}
        with self.assertRaisesRegex(R.RightsSourceError, r"'pixabay' lacks \['basis', 'read_on', 'legal_review'\]"):
            R.check(broken)
        broken = copy.deepcopy(data)
        broken['sources']['google_fonts']['kinds'] = ['typeface']
        with self.assertRaisesRegex(R.RightsSourceError, 'unknown kind'):
            R.check(broken)
        broken = copy.deepcopy(data)
        broken['sources']['google_fonts']['match'] = {'domain': ['fonts.googleapis.com']}
        with self.assertRaisesRegex(R.RightsSourceError, 'match must use'):
            R.check(broken)
        with self.assertRaisesRegex(R.RightsSourceError, 'no sources'):
            R.check({'sources': {}})


class TheWorker(unittest.TestCase):
    def test_the_worker_installs_the_gate_before_the_photo(self):
        from omni_prod import worker_tasks
        src = inspect.getsource(worker_tasks._run_live_build_job)
        self.assertIn("install_skill_gate(engine, 'G5')", src)
        self.assertLess(src.index("install_skill_gate(engine, 'G5')"), src.index('build_prompt = install_main_image('))

    def test_the_mode_is_said_on_every_build_off_included(self):
        e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'index.html': AS_WRITTEN}),
                                    repairer=_Files({'index.html': AS_WRITTEN}), executor=_Sandbox())
        with mock.patch.dict(os.environ, {'OMNI_GATE_G5': 'off'}), self.assertLogs('omni_prod.skill_units.gate', 'WARNING'):
            self.assertEqual(G.install(e, 'G5'), [])
        self.assertEqual(G.report(e), {'G5': {'mode': 'off'}})


if __name__ == '__main__':
    unittest.main()
