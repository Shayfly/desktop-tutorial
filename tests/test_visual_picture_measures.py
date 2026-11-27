"""Visual plan S2: how much picture a page has, measured inside the visual QA run that already opens it, and four advisory
rules (no_picture, small_hero_picture, text_on_picture, long_run_without_picture) that read the measures against one
thresholds table.

Real path: the whole in-sandbox SCRIPT of omni_prod.visual_qa runs against a page served by a local server, exactly as
tests/test_visual_qa.py does (not a copy of its audit), with the thresholds file staged the way the executor stages it.
The exact numbers come from hand-made pages whose boxes have fixed sizes, so they do not depend on the machine's fonts;
the library pages are judged by whether a rule fires, and by the numbers that do not depend on a font (a picture's box)."""
import base64
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from omni_prod import section_library as L
from omni_prod import visual_qa as VQ
from omni_prod.autonomous_core import ExecutionReport
from tests.test_hero_photo_led import FONTS, photo_page
from tests.test_section_library_conformance import FULL, contract_for
from tests.test_visual_qa import CHROMIUM, FIXTURES, HAVE_BROWSER, _free_port

PICTURE_KINDS = set(VQ.PICTURE_RULES)


def png(colour, size=(8, 8)):
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', size, colour).save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def run_script(page_html: str, viewport: str) -> dict:
    """The report the real in-sandbox script prints for this page at this viewport."""
    port = _free_port()
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(FIXTURES / 'offscreen_app.py', Path(d) / 'app.py')
        (Path(d) / 'page.html').write_text(page_html, encoding='utf-8')
        (Path(d) / '.omni').mkdir()
        (Path(d) / '.omni' / 'project.json').write_text(json.dumps(
            {'port': port, 'start': [sys.executable, 'app.py'], 'health_path': '/'}))
        (Path(d) / VQ.THRESHOLDS_PATH).parent.mkdir(parents=True, exist_ok=True)
        (Path(d) / VQ.THRESHOLDS_PATH).write_text(VQ.threshold_file_text(VQ.visual_thresholds()))
        proc = subprocess.run([sys.executable, '-c', VQ.SCRIPT, viewport], cwd=d, capture_output=True, text=True,
                              timeout=120, env=dict(os.environ, OMNI_CHROMIUM=CHROMIUM))
    report, _ = VQ.parse(proc.stdout)
    assert report is not None, proc.stderr[-1200:]
    return report


def rules_of(report: dict, viewport: str) -> dict:
    """{rule: finding} of the picture rules for one script report, judged by the platform's own picture_rules."""
    return {f['kind']: f for f in VQ.picture_rules(report['measures'], viewport, VQ.visual_thresholds())}


# ---- hand-made pages: every box has a fixed size, so the numbers are exact on any machine ----------------------------
BLUE = png((30, 60, 120))


def sized_page(*, contact=True, icon_only=False, background=False, hero_px=None) -> str:
    """Four sections. s1: two columns (700px | 692px) with a picture in the second; s2 and s4: text only; s3: a full-width
    picture. On a phone s1 is one column (200px of words, a 300px picture). Heights are fixed."""
    s1_img = f'<img src="{BLUE}" alt="" style="width:{hero_px[0]}px;height:{hero_px[1]}px">' if hero_px else f'<img src="{BLUE}" alt="">'
    if icon_only:
        s1_img = f'<img src="{BLUE}" alt="" style="width:100px;height:100px">'
    bg = f'<div class="bg" style="background-image:url({BLUE});width:400px;height:300px"></div>' if background else ''
    tel = '<a href="tel:0300000000">03-0000000</a>' if contact else ''
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>fixture</title><style>
body{{margin:0;font:16px/1.4 sans-serif;color:#111;background:#fff}} section{{box-sizing:border-box;overflow:hidden}}
.s1{{height:700px;display:grid;grid-template-columns:700px 692px;column-gap:48px}} .s1 img{{width:692px;height:700px;display:block}}
.s2{{height:900px}} .s3{{height:400px}} .s3 img{{width:100%;height:400px;display:block}} .s4{{height:300px}}
@media (max-width:640px){{.s1{{display:block;height:500px}} .s1 .copy{{height:200px;display:flow-root}} .s1 img{{width:100%;height:300px}}}}
</style></head><body><main>
<section class="s1"><div class="copy"><h1>Fixture</h1><p>First section.</p></div><div>{s1_img}</div></section>
<section class="s2"><h2>Text only</h2><p>No picture here.</p>{bg}</section>
<section class="s3"><img src="{BLUE}" alt=""></section>
<section class="s4"><h2>Contact</h2><p>{tel}</p></section>
</main></body></html>"""


def two_tone():
    """A picture whose left half is black and whose right half is white."""
    from PIL import Image
    im = Image.new('RGB', (160, 90), (255, 255, 255))
    im.paste((0, 0, 0), (0, 0, 80, 90))
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def text_page(picture_rgb, text_colour, size_px, contact=True, image=None) -> str:
    """One picture (a solid colour, 1440x500 or full width) with a line of text over it."""
    tel = '<a href="tel:0300000000">call</a>' if contact else ''
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>fixture</title><style>body{{margin:0;font:16px/1.4 sans-serif;background:#fff;color:#111}}
.hero{{position:relative;height:500px;overflow:hidden}} .hero img{{position:absolute;inset:0;width:100%;height:100%}}
.hero h1{{position:relative;margin:0;padding:80px 24px;text-align:center;font-size:{size_px}px;font-weight:400;color:{text_colour}}}
</style></head><body><main><section class="hero"><img src="{image or png(picture_rgb)}" alt=""><h1>Text over the picture</h1></section>
<section><p>{tel}</p></section></main></body></html>"""


@unittest.skipUnless(HAVE_BROWSER, 'playwright + chromium not available')
class TheMeasures(unittest.TestCase):
    """The numbers, on pages whose boxes are fixed."""

    def test_the_numbers_of_a_page_with_two_pictures_on_a_desktop(self):
        m = run_script(sized_page(), 'desktop')['measures']
        self.assertEqual(m['pictures'], 2)
        self.assertAlmostEqual(m['first_screen_picture_share'], 692 * 700 / (1440 * 900), places=3)
        self.assertAlmostEqual(m['hero_picture_share'], 692 * 700 / (1440 * 900), places=3)
        self.assertAlmostEqual(m['page_picture_share'], (692 * 700 + 1440 * 400) / (1440 * 2300), places=3)
        self.assertAlmostEqual(m['longest_run_without_picture'], 900 / 900, places=2)
        self.assertEqual(m['page_height'], 2300)
        # four sections, three kinds: two columns with a picture at the edge, one column of text (twice), a full-width picture
        self.assertEqual(m['composition_sections'], 4)
        self.assertEqual(m['compositions'], 3)
        self.assertEqual(m['composition_signatures'], ['1|pic|bleed', '1|text|boxed', '2|pic|bleed'])
        self.assertEqual(m['scope'], {'kit': False, 'contact': True})

    def test_the_numbers_of_the_same_page_on_a_phone(self):
        m = run_script(sized_page(), 'mobile')['measures']
        self.assertEqual(m['pictures'], 2)
        self.assertAlmostEqual(m['first_screen_picture_share'], 390 * 300 / (390 * 844), places=3)
        self.assertAlmostEqual(m['hero_picture_share'], 390 * 300 / (390 * 844), places=3)
        self.assertEqual(m['page_height'], 2100)
        self.assertAlmostEqual(m['longest_run_without_picture'], 900 / 844, places=2)

    def test_an_icon_sized_image_is_not_a_picture(self):
        m = run_script(sized_page(icon_only=True), 'desktop')['measures']
        self.assertEqual(m['pictures'], 1)                       # the full-width one; the 100x100 image is an icon

    def test_a_css_background_picture_is_a_picture(self):
        with_bg = run_script(sized_page(background=True), 'desktop')['measures']
        without = run_script(sized_page(), 'desktop')['measures']
        self.assertEqual(with_bg['pictures'], without['pictures'] + 1)

    def test_a_page_without_pictures_measures_zero_and_one_long_run(self):
        page = sized_page().replace(f'<img src="{BLUE}" alt="">', '').replace(f'<img src="{BLUE}" alt="" style="width:692px;height:700px">', '')
        m = run_script(page, 'desktop')['measures']
        self.assertEqual((m['pictures'], m['first_screen_picture_share'], m['page_picture_share'], m['hero_picture_share']), (0, 0, 0, 0))
        self.assertAlmostEqual(m['longest_run_without_picture'], 2300 / 900, places=2)

    def test_the_script_needs_its_thresholds_file(self):
        port = _free_port()
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(FIXTURES / 'offscreen_app.py', Path(d) / 'app.py')
            (Path(d) / 'page.html').write_text(sized_page(), encoding='utf-8')
            (Path(d) / '.omni').mkdir()
            (Path(d) / '.omni' / 'project.json').write_text(json.dumps(
                {'port': port, 'start': [sys.executable, 'app.py'], 'health_path': '/'}))
            proc = subprocess.run([sys.executable, '-c', VQ.SCRIPT, 'desktop'], cwd=d, capture_output=True, text=True,
                                  timeout=60, env=dict(os.environ, OMNI_CHROMIUM=CHROMIUM))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('visual_thresholds.json', proc.stderr)


@unittest.skipUnless(HAVE_BROWSER, 'playwright + chromium not available')
class TheRulesOnRealPages(unittest.TestCase):
    def test_a_business_page_with_pictures_but_no_hero_picture_is_small_hero(self):
        r = rules_of(run_script(sized_page(hero_px=(720, 450)), 'desktop'), 'desktop')          # 25 percent of the screen
        self.assertEqual(set(r) & PICTURE_KINDS, {'small_hero_picture'})

    def test_a_business_page_with_no_picture_has_no_picture(self):
        page = sized_page(icon_only=True).replace(f'<img src="{BLUE}" alt="">', '')
        for vp in VQ.VIEWPORTS:
            self.assertIn('no_picture', rules_of(run_script(page, vp), vp), vp)

    def test_an_app_page_is_not_judged_by_the_layout_rules(self):
        page = sized_page(contact=False, icon_only=True).replace(f'<img src="{BLUE}" alt="">', '')
        for vp in VQ.VIEWPORTS:
            self.assertEqual(set(rules_of(run_script(page, vp), vp)) & PICTURE_KINDS, set(), vp)

    def test_text_over_a_picture_is_judged_on_the_pixels_under_it(self):
        dark, light = (40, 40, 40), (255, 255, 255)
        low = rules_of(run_script(text_page(dark, '#222222', 40), 'desktop'), 'desktop')
        self.assertIn('text_on_picture', low)
        high = rules_of(run_script(text_page(dark, '#ffffff', 40), 'desktop'), 'desktop')
        self.assertNotIn('text_on_picture', high)
        # the text colour against a light picture, and the page's own screenshot is untouched: the measure reads a copy
        self.assertIn('text_on_picture', rules_of(run_script(text_page(light, '#ffffff', 40), 'desktop'), 'desktop'))

    def test_text_across_a_dark_and_a_light_part_of_a_picture_is_judged_on_the_worst_pixel(self):
        # dark text reads on the white half and not on the black half; white text the other way round: both fail
        for colour in ('#222222', '#ffffff'):
            r = rules_of(run_script(text_page(None, colour, 40, image=two_tone()), 'desktop'), 'desktop')
            self.assertIn('text_on_picture', r, colour)

    def test_large_text_needs_3_and_normal_text_needs_4_and_a_half(self):
        grey = (140, 140, 140)                       # white on it is 3.37:1
        big = run_script(text_page(grey, '#ffffff', 40), 'desktop')['measures']['text_on_picture']
        small = run_script(text_page(grey, '#ffffff', 16), 'desktop')['measures']['text_on_picture']
        self.assertTrue(big[0]['large'] and not small[0]['large'])
        self.assertAlmostEqual(big[0]['ratio'], 3.37, delta=0.1)
        table = VQ.visual_thresholds()
        self.assertEqual([f['kind'] for f in VQ.picture_rules({'text_on_picture': big, 'scope': {}}, 'desktop', table)], [])
        self.assertEqual([f['kind'] for f in VQ.picture_rules({'text_on_picture': small, 'scope': {}}, 'desktop', table)],
                         ['text_on_picture'])


def library_page(palette, *, picture=False, layout=None):
    """A library page for a business with every section and fact, and no picture unless asked."""
    content = copy.deepcopy(FULL)
    content['direction'] = L.direction_for(palette)['direction']
    content['about'].pop('image')
    content.pop('gallery')
    if picture:
        content['hero']['image'] = {'src': png((120, 120, 120), (160, 90)), 'alt': 'תמונה', 'width': 1600, 'height': 900}
    if layout:
        content['layout'] = {'hero': layout}
    doc, _ = L.page(content, contract_for(palette))
    return FONTS.sub('', doc)


REFERENCE_PALETTES = ('counsel', 'clinic', 'hearth', 'retreat', 'trade', 'energy', 'blush', 'studio')   # eight verticals
# the numbers of the visual plan's section 1.1 that do not depend on a font: a picture-less library page has none
PICTURELESS = {'pictures': 0, 'first_screen_picture_share': 0, 'page_picture_share': 0, 'hero_picture_share': 0}
# the S1 pages: the picture's box is the grid's (6/11 of 1440 by the hero's height; 390 by 5:4), so these are exact too
PHOTO_HERO_SHARE = {'desktop': 0.458, 'mobile': 0.37}


@unittest.skipUnless(HAVE_BROWSER, 'playwright + chromium not available')
class TheLibraryPages(unittest.TestCase):
    def test_every_picture_less_library_page_has_no_picture_and_says_so_on_both_viewports(self):
        seen = {}
        for palette in REFERENCE_PALETTES:
            doc = library_page(palette)
            for vp in VQ.VIEWPORTS:
                report = run_script(doc, vp)
                m = report['measures']
                seen[f'{palette}/{vp}'] = {k: m[k] for k in PICTURELESS}
                self.assertEqual(m['scope']['kit'], True, f'{palette}/{vp}')
                self.assertIn('no_picture', rules_of(report, vp), f'{palette}/{vp}')
                if vp == 'desktop':          # on a phone almost every section is one column of text
                    self.assertGreaterEqual(m['compositions'], 2, f'{palette}/{vp}')
                else:
                    self.assertIn('1|text|boxed', m['composition_signatures'], f'{palette}/{vp}')
        self.assertEqual(seen, {f'{p}/{v}': PICTURELESS for p in REFERENCE_PALETTES for v in VQ.VIEWPORTS})

    def test_a_photo_led_page_trips_none_of_the_four_rules(self):
        bad = {}
        for palette, layout in (('counsel', 'photo'), ('hearth', 'cover'), ('trade', 'photo'), ('blush', 'cover')):
            doc = library_page(palette, picture=True, layout=layout)
            for vp in VQ.VIEWPORTS:
                report = run_script(doc, vp)
                m = report['measures']
                fired = set(rules_of(report, vp)) & PICTURE_KINDS
                if fired:
                    bad[f'{palette}/{layout}/{vp}'] = (sorted(fired), m)
                self.assertEqual(m['pictures'], 1, f'{palette}/{layout}/{vp}')
                if layout == 'photo':
                    self.assertAlmostEqual(m['hero_picture_share'], PHOTO_HERO_SHARE[vp], places=2, msg=f'{palette}/{vp}')
        self.assertEqual(bad, {})

    def test_the_pre_s0_photo_page_trips_text_on_picture(self):
        # visual plan S0 (a): the colour overlay was painted under the photo, so the facts sat on the raw photo. A bright
        # picture under the white facts of the boxed panel is the page the reviewers saw; the rule must see it.
        doc = library_page('counsel', picture=True, layout='split').replace(
            png((120, 120, 120), (160, 90)), png((0, 255, 0), (160, 90)))
        doc = doc.replace('.panel--photo::before{content:"";position:absolute;inset:0;z-index:1;',
                          '.panel--photo::before{content:"";position:absolute;inset:0;z-index:0;')
        doc = doc.replace('.panel-photo{position:absolute;inset:0;z-index:0;', '.panel-photo{position:absolute;inset:0;')
        self.assertIn('z-index:0;', doc)
        report = run_script(doc, 'desktop')
        self.assertIn('text_on_picture', rules_of(report, 'desktop'))
        fixed = library_page('counsel', picture=True, layout='split').replace(png((120, 120, 120), (160, 90)), png((0, 255, 0), (160, 90)))
        # after S0 the same bright picture reads better under the overlay (the caption higher up the fade still reads 4.1:1,
        # a real advisory finding of a pure green photo, which is why this compares the two and does not demand silence)
        worst = lambda r: min(t['ratio'] for t in r['measures']['text_on_picture'])
        self.assertLess(worst(report), 2.0)
        self.assertGreater(worst(run_script(fixed, "desktop")), worst(report) + 0.3)


class TheTable(unittest.TestCase):
    def table(self):
        return json.loads(VQ.THRESHOLDS_FILE.read_text(encoding='utf-8'))

    def load(self, data):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'directions.json'
            p.write_text(json.dumps(data), encoding='utf-8')
            return VQ.visual_thresholds(p)

    def test_the_table_is_read_from_the_platform_not_from_the_repository_under_test(self):
        self.assertEqual(VQ.THRESHOLDS_FILE.resolve().parent.name, 'section_library')
        self.assertTrue(str(VQ.THRESHOLDS_FILE.resolve()).startswith(str(Path(VQ.__file__).resolve().parent)))
        self.assertEqual(VQ.visual_thresholds()['measure']['min_picture_px'], 120)

    def test_a_missing_key_raises_and_is_never_defaulted(self):
        for rule in ('measure', 'no_picture', 'small_hero_picture', 'text_on_picture', 'long_run_without_picture'):
            data = self.table()
            del data['visual_thresholds'][rule]
            with self.assertRaises(ValueError, msg=rule):
                self.load(data)
        data = self.table()
        del data['visual_thresholds']['text_on_picture']['large']
        with self.assertRaises(ValueError):
            self.load(data)
        data = self.table()
        del data['visual_thresholds']
        with self.assertRaises(ValueError):
            self.load(data)

    def test_an_unknown_rule_raises(self):
        data = self.table()
        data['visual_thresholds']['looks_generic'] = {'score': 3}
        with self.assertRaises(ValueError):
            self.load(data)

    def test_a_value_that_is_not_a_positive_number_raises(self):
        for path, bad in ((('measure', 'min_picture_px'), 0), (('measure', 'min_picture_px'), '120'),
                          (('text_on_picture', 'normal'), -1), (('text_on_picture', 'large'), True),
                          (('small_hero_picture', 'hero_picture_share_min', 'desktop'), None)):
            data = self.table()
            node = data['visual_thresholds']
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = bad
            with self.assertRaises(ValueError, msg=str(path)):
                self.load(data)

    def test_a_viewport_the_check_does_not_have_raises(self):
        data = self.table()
        data['visual_thresholds']['small_hero_picture']['hero_picture_share_min']['tablet'] = 0.4
        with self.assertRaises(ValueError):
            self.load(data)
        data = self.table()
        del data['visual_thresholds']['long_run_without_picture']['max_viewport_heights']['mobile']
        with self.assertRaises(ValueError):
            self.load(data)


class TheRules(unittest.TestCase):
    """picture_rules on given measures: which rule fires for whom."""
    GOOD = {'pictures': 4, 'hero_picture_share': 0.5, 'longest_run_without_picture': 1.2, 'text_on_picture': [],
            'scope': {'kit': True, 'contact': True}}

    def judge(self, vp='desktop', **change):
        m = dict(self.GOOD, **change)
        return [f['kind'] for f in VQ.picture_rules(m, vp, VQ.visual_thresholds())]

    def test_a_good_page_trips_nothing(self):
        self.assertEqual(self.judge(), [])

    def test_each_rule_fires_alone(self):
        self.assertEqual(self.judge(pictures=0, hero_picture_share=0, longest_run_without_picture=9), ['no_picture'])
        self.assertEqual(self.judge(hero_picture_share=0.2), ['small_hero_picture'])
        self.assertEqual(self.judge(longest_run_without_picture=2.6), ['long_run_without_picture'])
        self.assertEqual(self.judge(text_on_picture=[{'at': 'h1', 'ratio': 2.0, 'large': True}]), ['text_on_picture'])

    def test_the_hero_share_is_per_viewport(self):
        self.assertEqual(self.judge('desktop', hero_picture_share=0.37), ['small_hero_picture'])
        self.assertEqual(self.judge('mobile', hero_picture_share=0.37), [])

    def test_a_long_run_is_only_judged_when_the_page_has_pictures_to_space(self):
        self.assertEqual(self.judge(pictures=2, longest_run_without_picture=5), [])
        self.assertEqual(self.judge(pictures=3, longest_run_without_picture=5), ['long_run_without_picture'])

    def test_only_a_business_page_is_judged_by_the_layout_rules_but_every_page_by_text_on_picture(self):
        app = {'scope': {'kit': False, 'contact': False}}
        self.assertEqual(self.judge(pictures=0, hero_picture_share=0, **app), [])
        self.assertEqual(self.judge(text_on_picture=[{'at': 'p', 'ratio': 1.1, 'large': False}], **app), ['text_on_picture'])

    def test_the_four_rules_are_advisory_until_the_owner_enforces_them(self):
        self.assertTrue(PICTURE_KINDS <= set(VQ.RULES))
        self.assertEqual(PICTURE_KINDS & set(VQ.DEFAULT_ENFORCED), set())
        with patch.dict(os.environ, {'OMNI_VISUAL_QA_ENFORCE': 'no_picture,looks_generic'}):
            self.assertEqual(VQ.enforced_rules(), {'no_picture'})


def report_stdout(measures, findings=()):
    return ('OMNI_VISUAL_SHOT ' + base64.b64encode(b'\xff\xd8jpeg').decode() + '\nOMNI_VISUAL_QA ' + json.dumps(
        {'viewport': 'x', 'findings': list(findings), 'controls': 3, 'text_elements': 5, 'measures': measures}))


class TheExecutor(unittest.TestCase):
    """The executor: records the measures, adds the rules' findings, stages the thresholds file, changes no outcome."""
    PICTURELESS = {'pictures': 0, 'hero_picture_share': 0, 'first_screen_picture_share': 0, 'page_picture_share': 0,
                   'longest_run_without_picture': 2.4, 'text_on_picture': [], 'scope': {'kit': True, 'contact': True}}

    class Inner:
        def __init__(self, measures):
            self.measures, self.staged = measures, []

        def execute(self, **k):
            return ExecutionReport(True, (), '')

        def _run(self, repo, argv, tag, profile=None):
            self.staged.append(json.loads(repo[VQ.THRESHOLDS_PATH]))
            return {'returncode': 0, 'stdout': report_stdout(self.measures), 'stderr': ''}

    def run_check(self, enforce=None):
        inner = self.Inner(self.PICTURELESS)
        ex = VQ.VisualQAExecutor(inner)
        env = {k: v for k, v in os.environ.items() if k != 'OMNI_VISUAL_QA_ENFORCE'}
        if enforce is not None:
            env['OMNI_VISUAL_QA_ENFORCE'] = enforce
        with patch.dict(os.environ, env, clear=True):
            report = ex.execute(repository={}, spec=SimpleNamespace())
        return report, ex, inner

    def test_the_measures_and_the_rules_are_recorded_and_nothing_blocks_by_default(self):
        report, ex, inner = self.run_check()
        self.assertTrue(report.passed)
        for vp, entry in ex.last_visual['viewports'].items():
            self.assertEqual(entry['measures'], self.PICTURELESS, vp)
            self.assertEqual(entry['counts'], {'no_picture': 1}, vp)
        self.assertEqual(ex.last_visual['enforced_rules'], sorted(VQ.DEFAULT_ENFORCED))

    def test_the_script_is_given_its_threshold_in_the_snapshot_it_runs_in(self):
        _, _, inner = self.run_check()
        self.assertEqual(inner.staged, [{'min_picture_px': 120}] * 2)

    def test_the_owner_can_enforce_a_rule_and_then_it_blocks(self):
        report, _, _ = self.run_check(enforce='no_picture')
        self.assertFalse(report.passed)
        self.assertIn('no_picture', report.failures[0].message)

    def test_a_script_report_without_measures_is_recorded_as_such(self):
        class NoMeasures(self.Inner):
            def _run(self, repo, argv, tag, profile=None):
                return {'returncode': 0, 'stdout': report_stdout(None), 'stderr': ''}
        ex = VQ.VisualQAExecutor(NoMeasures(None))
        self.assertTrue(ex.execute(repository={}, spec=SimpleNamespace()).passed)
        self.assertEqual({e['measures'] for e in ex.last_visual['viewports'].values()}, {None})


if __name__ == '__main__':
    unittest.main()
