"""Visual plan S1: a hero led by its picture, with the facts in a strip under it.

Before: a page with a hero photo drew a boxed panel (the `split` or `banner` hero) that covered 11 to 16 percent of the
first desktop screen and 29 to 30 percent of a phone's, with the opening hours printed ON the photo. Now a page with a
hero image gets `photo` (the picture fills the end half of the first screen to the viewport edge) or `cover` (the
picture fills the first screen under a scrim made from the page's own text colour). The facts are a strip under the
hero, never on the picture. A page without a hero image is unchanged.

Real path: section_library.page() with a solid-colour photo, rendered in Chromium at visual_qa.VIEWPORTS, one page per
art direction and layout. The text-over-picture contrast is measured on pixels (the text made transparent, the pixels
under each text box sampled), against a white and a black picture, the worst case for light text on a scrim."""
import base64
import copy
import io
import re
import unittest

from omni_prod import section_library as L
from omni_prod import visual_qa as VQ
from omni_prod.g_apple import static
from omni_prod.section_library import demo_law_firm as D
from tests.test_section_library_conformance import contract_for

SAMPLE = {'formal': 'counsel', 'warm': 'hearth', 'bold': 'trade', 'elegant': 'blush'}
SHARE_MIN = {'desktop': 0.40, 'mobile': 0.35}          # visual plan S1: the picture's visible share of the viewport
FONTS = re.compile(r'<link[^>]+fonts\.g[^>]+>')


def solid(colour):
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (160, 90), colour).save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def photo_page(direction, palette, layout=None, colour=(120, 120, 120), merge=False):
    content = copy.deepcopy(D.CONTENT)
    content['direction'] = direction
    content['hero']['image'] = {'src': solid(colour), 'alt': 'תמונה', 'width': 1600, 'height': 900}
    if layout:
        content['layout'] = {'hero': layout}
    if merge:
        content['stats'] = [('3', 'עורכי דין'), ('4', 'תחומי ייצוג')]
    contract = contract_for(palette)
    doc, _ = L.page(content, contract)
    return FONTS.sub('', doc), contract


def context(browser, name):
    v = VQ.VIEWPORTS[name]
    return browser.new_context(viewport={'width': v['width'], 'height': v['height']}, is_mobile=v['mobile'],
                               has_touch=v['mobile'], device_scale_factor=1, locale='he-IL')


def playwright():
    try:
        from playwright.sync_api import sync_playwright
        from PIL import Image  # noqa: F401
    except ImportError:  # pragma: no cover
        raise unittest.SkipTest('playwright and pillow are required to render the page')
    return sync_playwright()


GEOMETRY = """() => {
  const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect(); return {l: r.left, t: r.top, r: r.right, b: r.bottom}; };
  const vw = innerWidth, vh = innerHeight, pic = box(document.querySelector('.hero-picture'));
  const vis = (b) => b ? Math.max(0, Math.min(b.r, vw) - Math.max(b.l, 0)) * Math.max(0, Math.min(b.b, vh) - Math.max(b.t, 0)) : 0;
  return {vw, vh, share: vis(pic) / (vw * vh), pic, h1: box(document.querySelector('.hero h1')),
          action: box(document.querySelector('.hero-words .btn-primary')), strip: box(document.querySelector('.hero-strip')),
          facts: [...document.querySelectorAll('.hero-strip dt, .hero-strip dd, .hero-strip .panel-figure')].map(box)};
}"""


def inside(b, vw, vh):
    return b is not None and b['l'] >= -0.5 and b['r'] <= vw + 0.5 and b['t'] >= -0.5 and b['b'] <= vh + 0.5


def overlap(a, b):
    return max(0, min(a['r'], b['r']) - max(a['l'], b['l'])) * max(0, min(a['b'], b['b']) - max(a['t'], b['t']))


class WhichHero(unittest.TestCase):
    def test_a_page_with_a_hero_picture_is_led_by_it_in_every_direction(self):
        for direction in ('formal', 'warm', 'bold', 'elegant'):
            for name in ('סטודיו אורן', 'כהן ושות׳', 'שקדייה', 'זרם אינסטלציה', 'מרפאת גפן', 'כוח'):
                got = L.layout_for({'name': name, 'direction': direction, 'hero': {'image': {'src': 'x', 'alt': 'a'}}})
                self.assertIn(got['hero'], L.PHOTO_HERO, f'{direction}/{name}')

    def test_both_photo_heroes_are_reached_by_the_business_name(self):
        seen = {L.layout_for({'name': n, 'direction': 'formal', 'hero': {'image': {'src': 'x', 'alt': 'a'}}})['hero']
                for n in ('סטודיו אורן', 'כהן ושות׳', 'שקדייה', 'זרם אינסטלציה', 'מרפאת גפן', 'כוח', 'בוטיק לילך', 'ענבר')}
        self.assertEqual(seen, set(L.PHOTO_HERO))

    def test_a_page_without_a_picture_keeps_its_hero(self):
        for direction in ('formal', 'warm', 'bold', 'elegant'):
            got = L.layout_for({'name': 'כהן ושות׳', 'direction': direction, 'hero': {'title': 't'}})['hero']
            self.assertIn(got, ('split', 'banner'))
            self.assertEqual(got, 'split' if direction == 'elegant' else got)

    def test_a_photo_hero_named_for_a_page_without_a_picture_raises(self):
        for name in L.PHOTO_HERO:
            with self.assertRaises(ValueError):
                L.layout_for({'name': 'x', 'direction': 'formal', 'hero': {'title': 't'}, 'layout': {'hero': name}})
            with self.assertRaises(ValueError):
                L.page(dict(copy.deepcopy(D.CONTENT), layout={'hero': name}), contract_for('counsel'))

    def test_the_content_model_is_not_offered_the_photo_heroes(self):
        self.assertEqual(L.LAYOUTS['hero'], ('split', 'banner'))
        self.assertEqual(L.PHOTO_HERO, ('photo', 'cover'))

    def test_a_named_boxed_hero_with_a_picture_is_still_the_boxed_panel(self):
        doc, _ = photo_page('formal', 'counsel', layout='banner')
        self.assertIn('hero--banner', doc)
        self.assertIn('panel--photo', doc)
        self.assertNotIn('hero-strip', doc)

    def test_the_marker_names_the_layout_and_the_library_version_moved(self):
        doc, _ = photo_page('formal', 'counsel', layout='cover')
        self.assertRegex(doc, r'data-layout="hero:cover ')
        self.assertIn('hero--cover', doc)
        self.assertEqual(L.LIBRARY_VERSION, '4')


class TheMarkup(unittest.TestCase):
    def test_the_facts_come_before_the_picture_in_the_markup(self):
        # the truth gate reads the first 45,000 characters of the page: an inlined picture must not push the facts out
        content = copy.deepcopy(D.CONTENT)
        content['hero']['image'] = {'src': 'data:image/webp;base64,' + 'A' * 60_000, 'alt': 'המשרד'}
        for layout in L.PHOTO_HERO:
            doc, _ = L.page(dict(content, layout={'hero': layout}), contract_for('counsel'))
            body = doc[doc.index('<body'):]
            self.assertLess(body.index('דרך מנחם בגין 132'), body.index('data:image/webp'), layout)
            self.assertLess(body.index('hero-strip'), body.index('hero-picture'), layout)

    def test_the_facts_are_in_a_strip_that_is_not_the_panel(self):
        doc, _ = photo_page('formal', 'counsel', layout='photo')
        strip = re.search(r'<div class="hero-strip">.*?</div></div>', doc, re.S).group(0)
        for fact in ('09:00–18:00', 'דרך מנחם בגין 132, תל אביב', '03-5551234', '+1,500'):
            self.assertIn(fact, strip)
        self.assertNotRegex(doc, r'class="panel[ "]')

    def test_one_h1_and_the_picture_has_its_alt(self):
        for layout in L.PHOTO_HERO:
            doc, _ = photo_page('warm', 'hearth', layout=layout)
            self.assertEqual(len(re.findall(r'<h1\b', doc)), 1)
            self.assertRegex(doc, r'<img class="hero-photo" src="data:image/png[^"]+" alt="תמונה"[^>]*loading="eager" fetchpriority="high"')

    def test_every_palette_and_hero_passes_the_g_apple_static_check(self):
        found = {}
        for palette in L.DIRECTIONS['palettes']:
            for layout in L.PHOTO_HERO:
                content = copy.deepcopy(D.CONTENT)
                content['direction'] = L.direction_for(palette)['direction']
                content['hero']['image'] = {'src': '/assets/hero.webp', 'alt': 'תמונה', 'width': 1600, 'height': 900}
                content['layout'] = {'hero': layout}
                contract = contract_for(palette)
                doc, _ = L.page(content, contract)
                bad = [f['code'] for f in static.check(doc, contract)]
                if bad:
                    found[f'{palette}/{layout}'] = bad
        self.assertEqual(found, {})


class TheFirstScreen(unittest.TestCase):
    def test_the_picture_is_at_least_40_percent_of_the_desktop_screen_and_35_of_the_phone(self):
        seen, bad = {}, []
        with playwright() as p:
            b = p.chromium.launch()
            for direction, palette in SAMPLE.items():
                for layout in L.PHOTO_HERO:
                    doc, _ = photo_page(direction, palette, layout)
                    for name in VQ.VIEWPORTS:
                        ctx = context(b, name)
                        pg = ctx.new_page()
                        pg.set_content(doc)
                        pg.wait_for_timeout(500)
                        g = pg.evaluate(GEOMETRY)
                        seen[f'{direction}/{layout}/{name}'] = round(g['share'], 3)
                        if g['share'] < SHARE_MIN[name]:
                            bad.append(f'{direction}/{layout}/{name}: {g["share"]:.3f} < {SHARE_MIN[name]}')
                        ctx.close()
            b.close()
        self.assertEqual(len(seen), len(SAMPLE) * len(L.PHOTO_HERO) * len(VQ.VIEWPORTS))
        self.assertEqual(bad, [], seen)

    def test_the_headline_and_the_main_action_are_wholly_on_the_first_screen(self):
        bad = []
        with playwright() as p:
            b = p.chromium.launch()
            for direction, palette in SAMPLE.items():
                for layout in L.PHOTO_HERO:
                    doc, _ = photo_page(direction, palette, layout)
                    for name in VQ.VIEWPORTS:
                        ctx = context(b, name)
                        pg = ctx.new_page()
                        pg.set_content(doc)
                        pg.wait_for_timeout(500)
                        g = pg.evaluate(GEOMETRY)
                        for what in ('h1', 'action'):
                            if not inside(g[what], g['vw'], g['vh']):
                                bad.append(f'{direction}/{layout}/{name}: {what} {g[what]} is not inside {g["vw"]}x{g["vh"]}')
                        ctx.close()
            b.close()
        self.assertEqual(bad, [])

    def test_the_facts_are_never_on_the_picture(self):
        bad = []
        with playwright() as p:
            b = p.chromium.launch()
            for direction, palette in SAMPLE.items():
                for layout in L.PHOTO_HERO:
                    doc, _ = photo_page(direction, palette, layout, merge=direction == 'elegant')
                    for name in VQ.VIEWPORTS:
                        ctx = context(b, name)
                        pg = ctx.new_page()
                        pg.set_content(doc)
                        pg.wait_for_timeout(500)
                        g = pg.evaluate(GEOMETRY)
                        self.assertTrue(g['facts'], f'{direction}/{layout}/{name}: the strip has no facts')
                        if overlap(g['pic'], g['strip']) > 1:
                            bad.append(f'{direction}/{layout}/{name}: the strip overlaps the picture')
                        for f in g['facts']:
                            if f and overlap(g['pic'], f) > 1:
                                bad.append(f'{direction}/{layout}/{name}: a fact lies on the picture {f}')
                        if g['strip']['t'] < g['pic']['b'] - 1:
                            bad.append(f'{direction}/{layout}/{name}: the strip is not under the picture')
                        ctx.close()
            b.close()
        self.assertEqual(bad, [])

    def test_on_a_phone_the_picture_comes_first(self):
        with playwright() as p:
            b = p.chromium.launch()
            doc, _ = photo_page('formal', 'counsel', 'photo')
            ctx = context(b, 'mobile')
            pg = ctx.new_page()
            pg.set_content(doc)
            pg.wait_for_timeout(400)
            g = pg.evaluate(GEOMETRY)
            b.close()
        self.assertLess(g['pic']['t'], g['h1']['t'])
        self.assertLess(g['pic']['b'], g['h1']['t'] + 1)


# the words of the cover hero sit on the picture: contrast measured on the pixels under each text box
TEXT_BOXES = """() => {
  const canvas = document.createElement('canvas').getContext('2d');
  const rgb = (c) => { canvas.fillStyle = '#000'; canvas.fillStyle = c; canvas.fillRect(0, 0, 1, 1);
    const d = canvas.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2]]; };
  const out = [];
  for (const el of document.querySelectorAll('.hero-words *')) {
    if (el.closest('.btn')) continue;                      // a button's text sits on the button's own fill
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    if (r.width < 1 || r.height < 1 || r.bottom > innerHeight || r.top < 0) continue;
    out.push({tag: el.tagName + '.' + el.className, l: r.left, t: r.top, r: r.right, b: r.bottom, colour: rgb(s.color)});
  }
  return out;
}"""


def luminance(rgb):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def worst_contrast_under_text(pg):
    """{tag: lowest contrast between the text colour and the lightest or the darkest pixel under its box}."""
    from PIL import Image
    boxes = pg.evaluate(TEXT_BOXES)
    pg.add_style_tag(content='.hero-words * { color: transparent !important; text-shadow: none !important; }')
    pg.wait_for_timeout(100)
    shot = Image.open(io.BytesIO(pg.screenshot())).convert('RGB')
    out = {}
    for bx in boxes:
        crop = shot.crop((max(0, int(bx['l'])), max(0, int(bx['t'])), min(shot.width, int(bx['r']) + 1),
                          min(shot.height, int(bx['b']) + 1)))
        px = list(crop.getdata())
        lo, hi = min(px, key=luminance), max(px, key=luminance)
        out[bx['tag']] = round(min(contrast(bx['colour'], lo), contrast(bx['colour'], hi)), 2)
    return out


class TextOverThePicture(unittest.TestCase):
    def test_the_cover_hero_text_reads_on_a_white_and_on_a_black_picture(self):
        low, measured = [], 0
        with playwright() as p:
            b = p.chromium.launch()
            for colour in ((255, 255, 255), (0, 0, 0)):
                for direction, palette in SAMPLE.items():
                    doc, _ = photo_page(direction, palette, 'cover', colour)
                    for name in VQ.VIEWPORTS:
                        ctx = context(b, name)
                        pg = ctx.new_page()
                        pg.set_content(doc)
                        pg.wait_for_timeout(500)
                        got = worst_contrast_under_text(pg)
                        self.assertTrue(got, f'{direction}/{name}: no hero text was measured')
                        measured += len(got)
                        low += [f'{direction}/{name}/{colour}: {tag} {c}:1' for tag, c in got.items() if c < 4.5]
                        ctx.close()
            b.close()
        self.assertGreater(measured, 40)
        self.assertEqual(low, [])

    def test_the_photo_hero_puts_no_text_on_the_picture(self):
        bad = []
        with playwright() as p:
            b = p.chromium.launch()
            for direction, palette in SAMPLE.items():
                doc, _ = photo_page(direction, palette, 'photo')
                for name in VQ.VIEWPORTS:
                    ctx = context(b, name)
                    pg = ctx.new_page()
                    pg.set_content(doc)
                    pg.wait_for_timeout(400)
                    g = pg.evaluate(GEOMETRY)
                    boxes = pg.evaluate(TEXT_BOXES)
                    bad += [f'{direction}/{name}: {x["tag"]}' for x in boxes if overlap(g['pic'], x) > 1]
                    ctx.close()
            b.close()
        self.assertEqual(bad, [])


class TheGatesStillPass(unittest.TestCase):
    def test_the_production_visual_check_finds_nothing_it_enforces(self):
        audit_js = re.search(r'AUDIT = r"""(.*?)"""', VQ.SCRIPT, re.S).group(1)       # the sandbox script's own audit
        found = {}
        with playwright() as p:
            b = p.chromium.launch()
            for direction, palette in SAMPLE.items():
                for layout in L.PHOTO_HERO:
                    doc, _ = photo_page(direction, palette, layout, merge=direction == 'elegant')
                    for name, v in VQ.VIEWPORTS.items():
                        ctx = context(b, name)
                        pg = ctx.new_page()
                        pg.set_content(doc)
                        pg.wait_for_timeout(1200)
                        audit = pg.evaluate(audit_js, v['mobile'])
                        found[f'{direction}/{layout}/{name}'] = [f"{f['kind']} {f['at']} {f['detail']}" for f in audit['findings']
                                                                  if f['kind'] in VQ.DEFAULT_ENFORCED]
                        ctx.close()
            b.close()
        self.assertEqual({k: v for k, v in found.items() if v}, {})
        self.assertEqual(len(found), len(SAMPLE) * len(L.PHOTO_HERO) * len(VQ.VIEWPORTS))

    def test_nothing_scrolls_sideways_at_320_390_and_1440(self):
        over = {}
        with playwright() as p:
            b = p.chromium.launch()
            for direction, palette in SAMPLE.items():
                for layout in L.PHOTO_HERO:
                    doc, _ = photo_page(direction, palette, layout, merge=direction == 'elegant')
                    for w in (320, 390, 1440):
                        pg = b.new_page(viewport={'width': w, 'height': 800})
                        pg.set_content(doc)
                        over[f'{direction}/{layout}/{w}'] = pg.evaluate('document.documentElement.scrollWidth - window.innerWidth')
                        pg.close()
            b.close()
        self.assertEqual({k: v for k, v in over.items() if v}, {})

    def test_the_render_check_sees_every_element_settled_after_300ms(self):
        # g_apple/render.py screenshots 300ms after load: the hero entrance must be over by then
        with playwright() as p:
            b = p.chromium.launch()
            faded = {}
            for layout in L.PHOTO_HERO:
                doc, _ = photo_page('formal', 'counsel', layout)
                pg = b.new_page(viewport={'width': 1440, 'height': 900})
                pg.set_content(doc)
                pg.wait_for_timeout(300)
                faded[layout] = pg.evaluate("""[...document.querySelectorAll('main *')].filter(el => {
                    const s = getComputedStyle(el); return parseFloat(s.opacity) < 0.99 && !el.closest('.panel-art'); })
                    .map(el => el.tagName + '.' + el.className).slice(0, 5)""")
                pg.close()
            b.close()
        self.assertEqual(faded, {'photo': [], 'cover': []})

    def test_the_purged_page_is_pixel_identical_to_the_full_stylesheet(self):
        differ = []
        with playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
            for direction, palette in SAMPLE.items():
                for layout in L.PHOTO_HERO:
                    shots = {}
                    for purged in (True, False):
                        L.PURGE = purged
                        try:
                            doc, _ = photo_page(direction, palette, layout, merge=direction == 'elegant')
                        finally:
                            L.PURGE = True
                        pg.set_content(doc)
                        for w in (390, 1440):
                            pg.set_viewport_size({'width': w, 'height': 900})
                            pg.wait_for_timeout(300)
                            shots[(purged, w)] = pg.screenshot(full_page=True)
                    for w in (390, 1440):
                        if shots[(True, w)] != shots[(False, w)]:
                            differ.append(f'{direction}/{layout}/{w}')
            b.close()
        self.assertEqual(differ, [])


class TheProductionRoute(unittest.TestCase):
    """The content route (site_content.render) is the real caller: a model that named `banner` for a page that then gets a
    hero picture must not keep the boxed panel, and a page with no picture keeps the model's choice."""

    def test_a_hero_picture_overrides_the_models_boxed_hero_and_no_picture_keeps_it(self):
        from tests import test_site_content_render as T
        from omni_prod.site_content import facts as Fx
        doc = copy.deepcopy(T.FIXTURE['scripted_content'])
        doc['layout'] = {'hero': 'banner'}
        plan = [{'place': 'hero', 'marker': T.HERO, 'alt': 'משרד עורכי דין בתל אביב', 'source': 'generated', 'index': 1}]
        with_picture, _ = T.render(doc=doc, sheet=Fx.fact_sheet(T.PROMPT, asset_plan=plan))
        without, _ = T.render(doc=doc, sheet=Fx.fact_sheet(T.PROMPT))
        self.assertRegex(with_picture, r'data-layout="hero:(photo|cover) ')
        self.assertIn('hero-strip', with_picture)
        self.assertNotIn('hero--banner', with_picture)
        self.assertRegex(without, r'data-layout="hero:banner ')
        self.assertNotIn('hero-strip', without)


if __name__ == '__main__':
    unittest.main()
