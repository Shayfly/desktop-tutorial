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
import hashlib
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
        self.assertIn('bytes embedded in the file that the platform did not supply', first[0]['message'])
        self.assertEqual((result.status, result.repair_rounds), ('ready', 1))

    def test_every_layer_the_worker_chains_gives_its_placeholder_back(self):
        """The logo, right-to-left, a generated image and the customer's photo, installed in the worker's order."""
        from omni_prod import page_locale, uploaded_assets as UA
        from omni_prod.generated_images import GeneratedImage, _Transform
        logo, made = b'\x89PNG logo ' * 60, b'\xff\xd8\xff generated ' * 90
        logo_sha, made_sha = hashlib.sha256(logo).hexdigest(), hashlib.sha256(made).hexdigest()
        prompt = (contract().prompt.replace(PROD_SHA, PHOTO_SHA)
                  + f' Uploaded logo attachment: att_{"c" * 32}; sha256={logo_sha}.')
        page = ('<!doctype html><html><body><img src="148ai-asset://logo" alt="לוגו">'
                f'<img id="hero-image" src="{MARKER}" alt="דלתות"><img src="148ai-asset://image/1" alt="חנות">'
                '<main>דלתות</main>EXTRA</body></html>')
        for extra, expect in (('', 'ready'), ('<img src="data:image/png;base64,' + 'Q' * 400 + '" alt="x">', 'failed')):
            with self.subTest(extra=bool(extra)):
                sandbox = _Recording()
                engine = engine_for(page.replace('EXTRA', extra), sandbox=sandbox, rounds=0)
                install_g5(engine)
                with mock.patch.object(UA, 'AttachmentRepository') as Repo:               # the logo, as the worker
                    Repo.return_value.get.return_value = {'sha256': logo_sha, 'mime': 'image/png'}
                    Repo.return_value.read.return_value = logo
                    UA.install(engine, prompt=prompt, pool=object(), store=object(), project_id='p', account_id='a')
                self.assertEqual(page_locale.install(engine, prompt), 'he')
                image = GeneratedImage(index=1, requirement_id='r', purpose='hero image', mime='image/jpeg', width=4,
                                       height=3, sha256=made_sha, alt='חנות', data=made)
                engine.repository_transform = _Transform(engine.repository_transform, [image])
                worker_install(engine, prompt)
                result = engine.build('x')
                seen = sandbox.seen[0]['index.html']
                self.assertNotIn('148ai-asset://', seen)                                   # the sandbox: bytes, three times
                self.assertEqual(seen.count('data:image/'), 3 + bool(extra))
                self.assertEqual(result.status, expect)
                gate = G.report(engine)['G5']
                self.assertEqual(gate['status'], 'pass' if expect == 'ready' else 'fail')
                self.assertEqual([f['unit'] for f in gate['failures']], [] if expect == 'ready' else ['rights_image_source'])

    def test_a_transform_that_invents_its_result_is_not_followed(self):
        engine = mock.MagicMock()
        install_g5(engine)
        gate = engine.core.executor                                     # a MagicMock engine: its core is a mock too
        self.assertIsInstance(gate, G.SkillGateExecutor)
        self.assertEqual(gate.view({'index.html': 'x'}), {'index.html': 'x'})


class EveryServedFileIsRead(unittest.TestCase):
    """An independent review (2026-11-16): the units read whole <html> documents only, so an asset loaded from a
    stylesheet, a script file or a fragment in a Python constant passed."""

    CLEAN = '<!doctype html><html><head><link rel="stylesheet" href="/static/site.css"></head><body><main>דף</main>' \
            '<script src="/static/app.js"></script></body></html>'

    def failures(self, repository):
        return {(f['unit'], f['page']) for f in G.check('G5', repository)['failures']}

    def test_a_stylesheet_a_script_file_and_a_fragment_constant(self):
        app = 'PAGE = """' + self.CLEAN + '"""\n'
        self.assertEqual(G.check('G5', {'app.py': app, 'static/site.css': 'body{margin:0}', 'static/app.js': 'let a=1;'})['status'], 'pass')
        self.assertEqual(self.failures({'app.py': app, 'static/site.css': '.hero{background:url(https://images.unsplash.com/photo-1)}'}),
                         {('rights_image_source', 'static/site.css')})
        self.assertEqual(self.failures({'app.py': app, 'static/site.css': '@font-face{font-family:G;src:url(//cdn.test/Gotham.woff2)}'}),
                         {('rights_font_source', 'static/site.css')})
        self.assertEqual(self.failures({'app.py': app, 'static/app.js':
                                        'const hero = document.querySelector("img"); hero.src = "https://picsum.photos/1200/800";'}),
                         {('rights_image_source', 'static/app.js')})
        fragment = app + 'GALLERY = \'<div><img src="https://images.unsplash.com/photo-2?w=600" alt="x"></div>\'\n'
        self.assertEqual(self.failures({'app.py': fragment}), {('rights_image_source', 'app.py')})
        self.assertEqual(self.failures({'app.py': app, 'static/app.js': 'new Audio("https://cdn.test/click.mp3").play();'}),
                         {('rights_media_source', 'static/app.js')})

    def test_a_page_that_takes_its_addresses_from_variables_has_its_constants_judged(self):
        page = 'HERO = "https://images.unsplash.com/photo-3"\nPAGE = f"""<html><body><img src="{HERO}" alt="x"></body></html>"""\n'
        self.assertEqual(self.failures({'app.py': page}), {('rights_image_source', 'app.py')})
        own = 'HERO = "148ai-asset://image/1"\nPAGE = f"""<html><body><img src="{HERO}" alt="x"></body></html>"""\n'
        self.assertEqual(G.check('G5', {'app.py': own})['status'], 'pass')
        # a page that names every address itself: an address constant has no way onto the page (a link target)
        link = 'WHATSAPP = "https://wa.me/972500000000"\nPAGE = """<html><body><a href="https://wa.me/972500000000">וואטסאפ</a></body></html>"""\n'
        self.assertEqual(G.check('G5', {'app.py': link})['status'], 'pass')

    def test_what_is_not_served_is_not_read_and_no_served_file_is_not_run(self):
        self.assertEqual(G.check('G5', {'README.md': '![x](https://images.unsplash.com/photo-1)', 'index.html': self.CLEAN})['status'], 'pass')
        self.assertEqual(G.check('G5', {'README.md': 'x'})['status'], 'NOT_RUN')

    def test_embedded_bytes_in_code_are_bytes_of_unknown_origin(self):
        app = 'import base64\nHERO = base64.b64decode("' + 'QUJD' * 400 + '")\nPAGE = """' + self.CLEAN + '"""\n'
        [failure] = G.check('G5', {'app.py': app})['failures']
        self.assertEqual((failure['unit'], failure['code']), ('rights_image_source', 'IMAGE_SOURCE_UNKNOWN'))
        self.assertIn('a base64 literal of 1600 characters', failure['findings'][0]['where'])
        self.assertLess(len(str(failure)), 600)


def refs(html, path=None, source='unknown'):
    """{reference} of one file whose source is unknown (or, with source=..., which have that source)."""
    want = None if source == 'unknown' else source
    return {a['ref'] for a in R.ledger(html, path) if a['source'] == want}


class TheInventory(unittest.TestCase):
    def test_every_way_a_page_carries_an_image(self):
        page = ('<link rel="icon" href="https://x.test/favicon.ico"><meta property="og:image" content="https://x.test/share.png">'
                '<meta property="og:image:secure_url" content="https://x.test/share2.png">'
                '<img src="148ai-asset://upload/2" srcset="https://cdn.test/a.webp 1x, https://cdn.test/a2 2x">'
                '<picture><source srcset="https://cdn.test/b.avif"></picture>'
                '<link rel="preload" as="image" imagesrcset="https://cdn.test/c 1x">'
                '<div style="background-image:url(\'https://cdn.test/bg.jpg\')"></div><body background="https://cdn.test/body">'
                '<video poster="https://cdn.test/poster"></video>'
                '<img class="lazy" data-src="https://images.unsplash.com/photo-9?w=600" alt="">'
                '<svg><image href="https://cdn.test/in-svg"/><use href="https://cdn.test/sprite.svg#i"/><use href="#local"/></svg>'
                '<object data="https://cdn.test/thing" type="image/png"></object>')
        self.assertEqual(refs(page), {
            'https://x.test/favicon.ico', 'https://x.test/share.png', 'https://x.test/share2.png', 'https://cdn.test/a.webp',
            'https://cdn.test/a2', 'https://cdn.test/b.avif', 'https://cdn.test/c', 'https://cdn.test/bg.jpg',
            'https://cdn.test/body', 'https://cdn.test/poster', 'https://images.unsplash.com/photo-9?w=600',
            'https://cdn.test/in-svg', 'https://cdn.test/sprite.svg#i', 'https://cdn.test/thing'})
        self.assertEqual(refs(page, source='customer_upload'), {'148ai-asset://upload/2'})

    def test_the_parser_is_not_fooled(self):
        self.assertEqual(refs('<img alt="a > b" title=\'x>y\' src="https://x.test/a">'), {'https://x.test/a'})
        self.assertEqual(refs('<style><!-- .h{background:url(https://x.test/bg)} --></style>'), {'https://x.test/bg'})
        self.assertEqual(refs('<script><!--\nel.src = "https://x.test/pic";\n//--></script>'), {'https://x.test/pic'})
        self.assertEqual(refs('<img src="https://x.test/a&amp;b.png">'), {'https://x.test/a&b.png'})
        self.assertEqual(refs('<IMG SRC="HTTPS://X.TEST/A.PNG">'), {'HTTPS://X.TEST/A.PNG'})
        self.assertEqual(refs('<!-- <img src="https://x.test/old.png"> --><p>https://x.test/in-the-copy.png</p>'), set())

    def test_css_in_every_form(self):
        css = ('@import"https://cdn.test/a.css";@import url(https://cdn.test/b.css);'
               '.a{background:image-set("https://cdn.test/one" 1x, "https://cdn.test/two" 2x)}'
               '.b{background:url("https://cdn.test/with(paren).jpg")}.c{background:\\75 rl(https://cdn.test/escaped)}'
               '.d{background:URL( https://cdn.test/spaced )}')
        want = {'https://cdn.test/a.css', 'https://cdn.test/b.css', 'https://cdn.test/one', 'https://cdn.test/two',
                'https://cdn.test/with(paren).jpg', 'https://cdn.test/escaped', 'https://cdn.test/spaced'}
        self.assertEqual(refs(f'<style>{css}</style>'), want)
        self.assertEqual(refs(css, 'static/site.css'), want)
        self.assertEqual({a['kind'] for a in R.ledger(css, 'site.css') if a['ref'].endswith('.css')}, {'font'})

    def test_google_fonts_in_every_form_is_known(self):
        for page in ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;700&display=swap">',
                     "<style>@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;700&display=swap');</style>",
                     '<style>@import "https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600&family=Rubik:wght@400;500";</style>',
                     '<link rel="preload" as="font" href="https://fonts.gstatic.com/s/heebo/v1/x.woff2" crossorigin>',
                     '<link rel="preconnect" href="https://fonts.gstatic.com"><link rel="dns-prefetch" href="//fonts.googleapis.com">'):
            with self.subTest(page=page[:50]):
                self.assertEqual(refs(page), set())
                self.assertEqual({a['kind'] for a in R.ledger(page)} - {'font'}, set())       # never read as an image
        self.assertEqual(U.run('rights_font_source', '<style>body{font-family:"Helvetica Neue",Gotham}</style>'), {'status': 'pass'})

    def test_a_script_that_puts_media_on_the_page_has_every_address_judged(self):
        gallery = ('<script>const PRODUCTS=[{name:"a",img:"https://images.unsplash.com/photo-1?w=600"},'
                   '{name:"b",img:"https://picsum.photos/600/400"}];'
                   'grid.innerHTML=PRODUCTS.map(p=>`<figure><img src="${p.img}" alt="${p.name}"></figure>`).join("")</script>')
        self.assertEqual(refs(gallery), {'https://images.unsplash.com/photo-1?w=600', 'https://picsum.photos/600/400'})
        self.assertEqual(refs('<script>["https://picsum.photos/1/2"].forEach(u=>{const i=document.createElement("img");i.src=u})</script>'),
                         {'https://picsum.photos/1/2'})
        self.assertEqual(refs('<script>img.src=`https://picsum.photos/${w}/600`</script>'), {'https://picsum.photos/${w}/600'})
        self.assertEqual(refs('<script>hero.style.backgroundImage="url(https://cdn.test/h)"</script>'), {'https://cdn.test/h'})
        self.assertEqual(refs('<button onclick="this.firstChild.src=\'https://cdn.test/swap\'">x</button>'), {'https://cdn.test/swap'})
        # its own drawing and its own placeholders stay known
        own = ('<script>const s=document.createElementNS("http://www.w3.org/2000/svg","svg");'
               'const pics=["148ai-asset://upload/1","148ai-asset://upload/2"];pics.forEach(u=>{const i=new Image();i.src=u})</script>')
        self.assertEqual(refs(own), set())

    def test_a_link_is_not_a_load(self):
        for page in ('<a href="https://wa.me/972500000000">וואטסאפ</a><a href="https://www.instagram.com/x">אינסטגרם</a>',
                     '<script>function wa(){window.open("https://wa.me/972500000000")}</script>',
                     '<script>btn.onclick=()=>{location.href="https://waze.com/ul?q=x"};img.src="148ai-asset://upload/1"</script>',
                     '<form action="https://formspree.io/f/x"></form><link rel="canonical" href="https://shop.example/">',
                     '<script src="https://cdn.tailwindcss.com"></script><script src="/static/app.js"></script>',
                     '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Store","url":"https://shop.example/",'
                     '"sameAs":["https://www.facebook.com/x"],"image":"148ai-asset://image/1"}</script>'):
            with self.subTest(page=page[:50]):
                self.assertEqual(refs(page), set())
        self.assertEqual(refs('<script type="application/ld+json">{"@type":"Store","image":["https://shop.example/a.jpg"],'
                              '"logo":{"@type":"ImageObject","url":"https://shop.example/logo"}}</script>'),
                         {'https://shop.example/a.jpg', 'https://shop.example/logo'})

    def test_what_the_build_draws_and_serves_itself(self):
        page = ('<svg viewBox="0 0 1 1"><path d="M0 0h1v1z" fill="url(#g)"/></svg><img src="icons/phone.svg" alt="">'
                '<img src="data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22/>" alt="">'
                '<img src="148ai-asset://logo" alt="logo"><img src="/static/hero.jpg" alt=""><link rel="icon" href="data:,">'
                '<link rel="stylesheet" href="/static/site.css">')
        self.assertEqual({a['source'] for a in R.ledger(page)}, {'authored_svg', 'customer_upload', 'build_served'})
        self.assertEqual(U.run('rights_image_source', page), {'status': 'pass'})

    def test_a_photograph_wrapped_in_an_svg_is_still_a_photograph(self):
        import base64
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://cdn.test/photo.jpg"/></svg>'
        for uri in ('data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode(),
                    'data:image/svg+xml,' + svg.replace('"', '%22').replace('<', '%3C').replace('>', '%3E').replace(' ', '%20')):
            with self.subTest(uri=uri[:40]):
                self.assertEqual(refs(f'<img src="{uri}" alt="">'), {'https://cdn.test/photo.jpg'})
        raster = '<svg xmlns="http://www.w3.org/2000/svg"><image href="data:image/png;base64,' + 'A' * 300 + '"/></svg>'
        [bad] = [a for a in R.ledger('<img src="data:image/svg+xml;base64,%s">' % base64.b64encode(raster.encode()).decode())
                 if a['source'] is None]
        self.assertIn('inside an SVG data: URI', bad['where'])
        self.assertEqual(len(refs('<img src="data:image/svg+xml;base64,!!!not-svg!!!">')), 1)       # does not decode: unknown

    def test_a_placeholder_must_be_exactly_one_the_platform_writes(self):
        self.assertEqual(refs('<img src="148ai-asset://upload/1"><img src="148ai-asset://image/12"><img src="148ai-asset://logo">'), set())
        self.assertEqual(refs('<img src="148ai-asset://upload/1AAAA"><img src="148ai-asset://logotype"><img src="148ai-asset://audio/1">'),
                         {'148ai-asset://upload/1AAAA', '148ai-asset://logotype', '148ai-asset://audio/1'})

    def test_audio_video_and_frames(self):
        for page in ('<audio controls><source src="https://cdn.test/song.mp3" type="audio/mpeg"></audio>',
                     '<video src="https://cdn.test/clip"></video>',
                     '<script>new Audio("https://cdn.test/click.wav").play()</script>',
                     '<script>const a = new Audio(sound); a.play()</script>',
                     '<audio src="data:audio/mpeg;base64,' + 'A' * 200 + '"></audio>',
                     '<iframe src="https://player.vimeo.com/video/1"></iframe>',
                     '<iframe src="https://www.youtube.com/embed/x"></iframe>',
                     '<iframe src="https://widgets.example.test/player"></iframe>',
                     '<embed src="https://cdn.test/intro" type="audio/ogg">',
                     '<meta property="og:video" content="https://cdn.test/v">'):
            with self.subTest(page=page[:45]):
                self.assertEqual(U.run('rights_media_source', page)['code'], 'MEDIA_SOURCE_UNKNOWN')
        for page in ('<iframe src="https://www.google.com/maps/embed?pb=1" title="מפה"></iframe>',     # the one known frame
                     '<iframe src="/terms.html"></iframe>', '<script>const a = new Audio();</script>',
                     '<audio src="/static/intro.mp3"></audio>'):
            with self.subTest(page=page[:45]):
                self.assertEqual(U.run('rights_media_source', page), {'status': 'pass'})
        self.assertEqual(U.run('rights_media_source', '<iframe src="https://www.google.com/search?q=x"></iframe>')['code'],
                         'MEDIA_SOURCE_UNKNOWN')                                    # the host alone is not the map

    def test_a_file_too_large_to_read_blocks_every_unit(self):
        page = ''.join(f'<img src="https://fonts.googleapis.com/i{n}" alt="">' for n in range(R.MAX_ASSETS + 5))
        page = page.replace('<img', '<link rel="stylesheet"').replace('src=', 'href=')
        for unit in RIGHTS:
            with self.subTest(unit):
                [finding] = U.run(unit, page)['findings']
                self.assertIn(f'more than {R.MAX_ASSETS} asset references and was not fully read', finding['why'])

    def test_an_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            R.unknown('<p></p>', 'icon')


class TheRegistry(unittest.TestCase):
    def test_every_source_states_its_basis(self):
        data = R.load()
        self.assertEqual(set(data['sources']), {'customer_upload', 'platform_generated', 'authored_svg', 'build_served',
                                                'google_fonts', 'google_maps_embed'})
        for sid, entry in data['sources'].items():
            with self.subTest(sid):
                self.assertTrue(all(entry[k] for k in R.ENTRY_KEYS))
                self.assertRegex(entry['read_on'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertIn('developers.google.com/fonts/faq', data['sources']['google_fonts']['basis'])
        self.assertIn('flux-schnell', data['sources']['platform_generated']['basis'])
        self.assertIn('developers.google.com/maps/documentation/embed', data['sources']['google_maps_embed']['basis'])
        # no source ON ANOTHER SITE is known for audio or video: only what the build serves itself
        self.assertEqual([sid for sid, e in data['sources'].items() if 'media' in e['kinds']], ['build_served'])

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
