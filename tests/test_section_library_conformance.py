"""The section library's conformance matrix (the judges of the wiring design, 2026-11-20: "this is what lets slice 1 grow
past 'counsel' quickly and safely"). Every palette the library knows x four content shapes -- every section and fact;
the bare minimum (no panel, no WhatsApp, no e-mail, no hours); no WhatsApp and no e-mail; a photo hero -- must pass every
gate that judges a page, link only to what it rendered, show no channel the customer did not give, invent no number,
and fit inside the 45,000 characters the truth gate reads (preview_smoke). Then one page per art direction and shape is
rendered at 320 and 1440px: nothing scrolls sideways.

The content here is synthetic test data for an unnamed generic business, not any real customer."""
import copy
import json
import os
import re
import unittest
from html import unescape

from omni_prod import section_library as L
from omni_prod import skill_units as U
from omni_prod.bidi_ranges import unwrapped_ranges
from omni_prod.g_apple import contract as C
from omni_prod.g_apple import static

HERE = os.path.dirname(os.path.abspath(__file__))
PALETTES = json.load(open(os.path.join(HERE, '..', 'omni_prod', 'vertical_palettes.json'), encoding='utf-8'))['palettes']
UNITS = sorted(d for d in os.listdir(os.path.dirname(U.__file__))
               if os.path.isdir(os.path.join(os.path.dirname(U.__file__), d)) and not d.startswith('_'))
PREVIEW_CUT = 45_000          # preview_smoke keeps the first 45,000 characters of GET / for the truth gate


def contract_for(palette: str) -> dict:
    p, d = PALETTES[palette], L.direction_for(palette)
    return C.build(f"\n--- Approved project brief\nDesign: style clean; primary colour {p['primary']}; palette {p['primary']}, "
                   f"{p['accent']}, {p['background']}, {p['ink']} (primary, accent, background, text: test); font 'Heebo', "
                   f"system-ui, sans-serif (load it from Google Fonts); display font {d['display']}")


FULL = {
    'title': 'סטודיו אורן – עיצוב ושיפוץ | רחובות', 'description': 'תכנון ושיפוץ דירות ברחובות והסביבה. 08-9312456.',
    'name': 'סטודיו אורן', 'tagline': 'עיצוב ושיפוץ · רחובות', 'year': '2026', 'schema_type': 'HomeAndConstructionBusiness',
    'phone': '08-9312456', 'whatsapp': '052-7314489', 'email': 'studio@oren-design.co.il',
    'address': 'הרצל 120, רחובות', 'hours': 'א׳–ה׳ 08:00–17:00',
    'nav': [('services', 'שירותים'), ('pricelist', 'מחירון'), ('gallery', 'עבודות'), ('about', 'עלינו'), ('team', 'צוות'),
            ('process', 'תהליך'), ('faq', 'שאלות'), ('contact', 'יצירת קשר')],
    'hero': {'eyebrow': 'עיצוב ושיפוץ דירות', 'title': 'מתכננים איתכם, משפצים בשבילכם', 'lead': 'תכנון, ליווי וביצוע של שיפוץ דירה.',
             'cta': 'לתיאום פגישה', 'note': 'פגישת היכרות ללא תשלום', 'panel_label': 'הסטודיו בקצרה',
             'panel_figure': '19', 'panel_caption': 'שנות עבודה',
             'panel_facts': [('שעות', 'א׳–ה׳ 08:00–17:00'), ('כתובת', 'הרצל 120, רחובות'), ('טלפון', '08-9312456', 'tel:089312456')]},
    'stats': [('19', 'שנות עבודה'), ('340', 'דירות ששופצו'), ('6', 'אנשי צוות')],
    'services': {'eyebrow': 'שירותים', 'title': 'מה אנחנו עושים',
                 'items': [('תכנון', 'תוכנית עבודה ומפרט.'), ('שיפוץ', 'ביצוע מלא.'), ('ליווי', 'פיקוח באתר.'), ('מטבחים', 'תכנון מטבח.')]},
    'pricelist': {'eyebrow': 'מחירון', 'title': 'מחירים', 'groups': [
        {'title': 'תכנון', 'items': [{'name': 'פגישת תכנון', 'price': '450 ₪', 'desc': 'שעתיים בדירה.'}, {'name': 'מפרט', 'price': '1,200 ₪'}]},
        {'title': 'ליווי', 'items': [{'name': 'ביקור פיקוח', 'price': '380 ₪'}, {'name': 'ליווי חודשי'}]}]},
    'gallery': {'eyebrow': 'עבודות', 'title': 'מהשנה האחרונה', 'images': [
        {'src': '/assets/g1.webp', 'alt': 'מטבח אחרי שיפוץ', 'caption': 'מטבח ברחובות'}, {'src': '/assets/g2.webp', 'alt': 'סלון'}]},
    'about': {'eyebrow': 'עלינו', 'title': 'סטודיו קטן, עבודה מסודרת', 'paragraphs': ['אנחנו מתכננים ומשפצים דירות.'],
              'image': {'src': '/assets/about.webp', 'alt': 'הסטודיו', 'width': 1200, 'height': 900}},
    'team': {'eyebrow': 'צוות', 'title': 'מי עובד איתכם', 'members': [
        {'name': 'אדר׳ נועה אורן', 'role': 'מתכננת'}, {'name': 'יואב לוי', 'role': 'מנהל עבודה'},
        {'name': 'רוני בר', 'role': 'מעצבת', 'photo': {'src': '/assets/r.webp', 'alt': 'רוני בר'}}]},
    'process': {'eyebrow': 'תהליך', 'title': 'איך עובדים', 'steps': [('פגישה', 'מכירים.'), ('תכנון', 'מתכננים.'), ('ביצוע', 'בונים.')]},
    'cta': {'title': 'מתכננים שיפוץ?', 'text': 'התקשרו או כתבו לנו.'},
    'testimonials': {'eyebrow': 'לקוחות', 'title': 'מה אמרו', 'items': [{'text': 'עבודה מסודרת.', 'name': 'דנה'}, {'text': 'עמדו בזמנים.', 'name': 'אבי'}]},
    'faq': {'eyebrow': 'שאלות', 'title': 'שאלות נפוצות', 'items': [('כמה זמן לוקח שיפוץ?', 'תלוי בהיקף.'), ('האם יש אחריות?', 'כן, בכתב.')]},
    'contact': {'eyebrow': 'יצירת קשר', 'title': 'דברו איתנו', 'topics': ['תכנון', 'שיפוץ', 'אחר']},
}


def shapes():
    full = copy.deepcopy(FULL)
    minimal = {k: copy.deepcopy(FULL[k]) for k in ('title', 'description', 'name', 'phone', 'services', 'about', 'contact')}
    minimal['hero'] = {k: FULL['hero'][k] for k in ('title', 'lead', 'cta')}
    minimal['about'].pop('image')
    minimal['nav'] = [('services', 'שירותים'), ('faq', 'שאלות'), ('contact', 'יצירת קשר')]   # faq is not given: no link
    no_wa = copy.deepcopy(FULL)
    del no_wa['whatsapp'], no_wa['email']
    photo = copy.deepcopy(FULL)
    photo['hero']['image'] = {'src': '/assets/hero.webp', 'alt': 'דירה אחרי שיפוץ', 'width': 1600, 'height': 1200}
    del photo['stats']
    return {'full': full, 'minimal': minimal, 'no_whatsapp': no_wa, 'photo_hero': photo}


def visible_text(doc: str) -> str:
    body = re.sub(r'<(script|style)\b.*?</\1>', ' ', doc, flags=re.S)
    return unescape(re.sub(r'<[^>]+>', ' ', body))


def numbers(s: str) -> set:
    return {re.sub(r'[,.]', '', n) for n in re.findall(r'\d[\d,.]*\d|\d', s)}


class Conformance(unittest.TestCase):
    maxDiff = None

    def test_every_palette_and_shape_passes_every_gate_and_invents_nothing(self):
        problems = {}
        for palette in L.DIRECTIONS['palettes']:
            contract = contract_for(palette)
            for name, content in shapes().items():
                content['direction'] = L.direction_for(palette)['direction']
                doc, skipped = L.page(content, contract)
                key, found = f'{palette}/{name}', []
                found += [f"g_apple {f['code']}" for f in static.check(doc, contract)]
                found += [f'unit {u}: {r}' for u in UNITS for r in [U.run(u, doc)] if r.get('status') != 'pass']
                if unwrapped_ranges(doc):
                    found.append(f'unwrapped ranges {unwrapped_ranges(doc)}')
                if len(re.findall(r'<h1\b', doc)) != 1:
                    found.append('not exactly one h1')
                if len(doc) >= PREVIEW_CUT:
                    found.append(f'{len(doc)} characters: past the truth gate cut')
                ids = set(re.findall(r'\bid="([^"]+)"', doc))
                found += [f'link to missing #{h}' for h in re.findall(r'href="#([^"]+)"', doc) if h not in ids]
                if not content.get('whatsapp') and 'wa.me' in doc:
                    found.append('a WhatsApp link the customer did not give')
                if not content.get('email') and 'mailto:' in doc:
                    found.append('an e-mail link the customer did not give')
                given = numbers(json.dumps(content, ensure_ascii=False))
                invented = numbers(visible_text(doc)) - given
                if invented:
                    found.append(f'numbers on the page that the content never gave: {sorted(invented)}')
                if found:
                    problems[key] = found
        self.assertEqual(problems, {})

    def test_the_minimal_shape_says_what_it_left_out(self):
        doc, skipped = L.page(dict(shapes()['minimal'], direction='formal'), contract_for('counsel'))
        self.assertEqual(skipped, ['stats', 'pricelist', 'gallery', 'team', 'process', 'cta', 'testimonials', 'faq'])
        self.assertNotIn('<form', doc)                  # no WhatsApp number: the form has nowhere to go
        self.assertNotIn('class="panel', doc)           # no panel content: the hero is one column
        self.assertIn('hero--solo', doc)

    def test_a_missing_required_fact_raises_instead_of_being_filled_in(self):
        for key in ('name', 'phone', 'title', 'description', 'direction', 'hero'):
            content = dict(shapes()['full'], direction='formal')
            del content[key]
            with self.assertRaises(ValueError, msg=key):
                L.page(content, contract_for('counsel'))
        content = dict(shapes()['full'], direction='formal')
        content['services'] = {'items': FULL['services']['items']}          # a section without its title
        with self.assertRaises(ValueError):
            L.page(content, contract_for('counsel'))
        with self.assertRaises(ValueError):
            L.page(dict(shapes()['full'], direction='baroque'), contract_for('counsel'))

    def test_nothing_scrolls_sideways_in_any_direction_or_shape(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:  # pragma: no cover
            self.skipTest('playwright is required to render the page')
        sample = {'formal': 'counsel', 'warm': 'hearth', 'bold': 'trade', 'elegant': 'blush'}
        over = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={'width': 320, 'height': 800})
            for direction, palette in sample.items():
                for name in ('full', 'minimal'):
                    doc, _ = L.page(dict(shapes()[name], direction=direction), contract_for(palette))
                    pg.set_content(re.sub(r'<link[^>]+fonts\.g[^>]+>', '', doc))
                    for w in (320, 1440):
                        pg.set_viewport_size({'width': w, 'height': 800})
                        o = pg.evaluate('document.documentElement.scrollWidth - window.innerWidth')
                        if o:
                            over[f'{direction}/{name}/{w}'] = o
            b.close()
        self.assertEqual(over, {})


MEASURE = """() => {
  const lum = c => { const m = c.match(/[\\d.]+/g).slice(0, 3).map(Number).map(v => v / 255)
    .map(v => v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)); return 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]; };
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const bg = el => { for (; el; el = el.parentElement) { const c = getComputedStyle(el).backgroundColor;
    if (c && !c.endsWith(', 0)') && c !== 'transparent') return c; } return 'rgb(255, 255, 255)'; };
  const px = el => el ? parseFloat(getComputedStyle(el).fontSize) : 0;
  const out = {};
  const sec = document.querySelector('.band .btn-secondary');
  if (sec) out.bandSecondary = ratio(getComputedStyle(sec).color, bg(sec));
  out.flush = [...document.querySelectorAll('.section--flush')].map(s => parseFloat(getComputedStyle(s).paddingTop));
  const h1 = px(document.querySelector('h1'));
  out.hierarchy = [...document.querySelectorAll('section[id]')].flatMap(s => { const h2 = s.querySelector('h2');
    if (!h2) return []; const bad = []; if (px(h2) >= h1) bad.push(s.id + ': h2 >= h1');
    s.querySelectorAll('h3').forEach(h3 => { if (px(h3) >= px(h2)) bad.push(s.id + ': h3 >= h2'); }); return bad; });
  const rows = {}; document.querySelectorAll('.stat dd').forEach(dd => { const r = dd.closest('.stat').getBoundingClientRect();
    const k = Math.round(r.top); (rows[k] = rows[k] || []).push(Math.round(dd.getBoundingClientRect().top)); });
  out.statRowsUneven = Object.values(rows).filter(t => Math.max(...t) - Math.min(...t) > 1).length;
  const legal = document.querySelector('.site-footer .legal'), wrap = document.querySelector('.site-footer .wrap');
  out.legalShort = legal ? Math.round(wrap.getBoundingClientRect().width - legal.getBoundingClientRect().width) : 0;
  return out; }"""


class RoundTwoMeasured(unittest.TestCase):
    """Round 2's measured fixes, measured again in the browser on every palette (the design editor, 2026-11-21)."""
    maxDiff = None

    def test_round_two_holds_on_every_palette_at_phone_and_desktop_width(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:  # pragma: no cover
            self.skipTest('playwright is required to render the page')
        problems = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={'width': 390, 'height': 844})
            for palette in L.DIRECTIONS['palettes']:
                content = dict(shapes()['full'], direction=L.direction_for(palette)['direction'])
                doc, _ = L.page(content, contract_for(palette))
                pg.set_content(re.sub(r'<link[^>]+fonts\.g[^>]+>', '', doc))
                for w in (390, 1440):
                    pg.set_viewport_size({'width': w, 'height': 900})
                    m, found = pg.evaluate(MEASURE), []
                    if m.get('bandSecondary', 99) < 4.5:
                        found.append(f"band outline button {m['bandSecondary']:.2f}:1 < 4.5")
                    if any(m['flush']):
                        found.append(f"flush padding {m['flush']}")
                    found += m['hierarchy']
                    if m['statRowsUneven']:
                        found.append(f"{m['statRowsUneven']} numbers row(s) not on one line")
                    if m['legalShort'] > 1:
                        found.append(f"legal line {m['legalShort']}px short of the footer")
                    if found:
                        problems[f'{palette}/{w}'] = found
            b.close()
        self.assertEqual(problems, {})


SETTLE = ('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 0))))')


class PurgingChangesNothingVisible(unittest.TestCase):
    """The page ships only the rules it can use (section_library.purge). The proof that nothing that can match was
    removed: every direction, the richest and the barest shape, and every layout variant render pixel-identical with
    the full stylesheet and with the purged one, on a phone and on a wide screen (motion reduced, so no frame of the
    entrance animation is compared)."""

    def test_the_purged_page_is_pixel_identical_to_the_full_stylesheet(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:  # pragma: no cover
            self.skipTest('playwright is required to render the page')
        sample = {'formal': 'counsel', 'warm': 'hearth', 'bold': 'trade', 'elegant': 'blush'}
        variants = [dict(zip(L.LAYOUTS, combo)) for combo in zip(*[opts for opts in L.LAYOUTS.values()])] + \
                   [dict(zip(L.LAYOUTS, combo)) for combo in zip(*[opts[::-1] for opts in L.LAYOUTS.values()])]
        differ = []
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
            for direction, palette in sample.items():
                for name in ('full', 'minimal'):
                    for layout in variants:
                        content = dict(shapes()[name], direction=direction, layout=layout)
                        shots = {}
                        for purged in (True, False):
                            L.PURGE = purged
                            try:
                                doc, _ = L.page(content, contract_for(palette))
                            finally:
                                L.PURGE = True
                            pg.set_content(re.sub(r'<link[^>]+fonts\.g[^>]+>', '', doc))
                            for w in (390, 1440):
                                pg.set_viewport_size({'width': w, 'height': 900})
                                # the action bar's IntersectionObserver delivers after a render, as a task: two frames
                                # and a task let it decide `is-away` before the shot (seen once under load, 2026-11-21)
                                pg.evaluate(SETTLE)
                                shots[(purged, w)] = pg.screenshot(full_page=True)
                        for w in (390, 1440):
                            if shots[(True, w)] != shots[(False, w)]:
                                differ.append(f'{direction}/{name}/{layout}/{w}')
            b.close()
        self.assertEqual(differ, [])

    def test_the_richest_page_leaves_room_under_the_truth_gate_window(self):
        biggest = max(len(L.page(dict(c, direction=L.direction_for(pal)['direction']), contract_for(pal))[0])
                      for pal in L.DIRECTIONS['palettes'] for c in shapes().values())
        self.assertLess(biggest, PREVIEW_CUT - 5_000)          # 5,000 characters of headroom for longer copy


class Variety(unittest.TestCase):
    """The owner, 2026-11-20: "מגוון בהכול ברמה הכי גבוהה". Each section with more than one designed layout; a business
    gets its own combination, stable across builds; every combination passes every gate."""
    maxDiff = None

    def test_a_business_keeps_its_layout_and_businesses_on_one_palette_differ(self):
        names = ['סטודיו אורן', 'כהן ושות׳', 'שקדייה', 'זרם אינסטלציה', 'מרפאת גפן', 'סטודיו ענבר', 'כוח', 'בוטיק לילך']
        combos = [L.layout_for({'name': n, 'direction': 'formal'}) for n in names]
        self.assertEqual(combos, [L.layout_for({'name': n, 'direction': 'formal'}) for n in names])
        self.assertGreaterEqual(len({tuple(x.values()) for x in combos}), 4)

    def test_a_layout_the_library_does_not_have_raises(self):
        for bad in ({'hero': 'carousel'}, {'sidebar': 'left'}):
            with self.assertRaises(ValueError):
                L.layout_for({'name': 'x', 'direction': 'formal', 'layout': bad})

    def test_the_content_can_name_its_layout_and_the_page_says_which_it_used(self):
        content = dict(shapes()['full'], direction='bold', layout={'services': 'list', 'faq': 'stacked'})
        doc, _ = L.page(content, contract_for('trade'))
        self.assertIn('<ol class="svc-list">', doc)
        self.assertIn('faq faq--stacked', doc)
        self.assertRegex(doc, r'data-layout="[^"]*services:list[^"]*faq:stacked')

    def test_every_variant_in_every_direction_passes_every_gate_and_never_scrolls_sideways(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:  # pragma: no cover
            self.skipTest('playwright is required to render the page')
        sample = {'formal': 'counsel', 'warm': 'hearth', 'bold': 'trade', 'elegant': 'blush'}
        problems = {}
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={'width': 320, 'height': 800})
            for direction, palette in sample.items():
                contract = contract_for(palette)
                for axis, opts in L.LAYOUTS.items():
                    for opt in opts:
                        content = dict(shapes()['full'], direction=direction, layout={axis: opt})
                        doc, _ = L.page(content, contract)
                        key, found = f'{direction}/{axis}:{opt}', []
                        found += [f"g_apple {f['code']}" for f in static.check(doc, contract)]
                        found += [f'unit {u}' for u in UNITS if U.run(u, doc).get('status') != 'pass']
                        pg.set_content(re.sub(r'<link[^>]+fonts\.g[^>]+>', '', doc))
                        for w in (320, 820, 1440):
                            pg.set_viewport_size({'width': w, 'height': 800})
                            o = pg.evaluate('document.documentElement.scrollWidth - window.innerWidth')
                            if o:
                                found.append(f'{w}px overflow {o}')
                        if found:
                            problems[key] = found
            b.close()
        self.assertEqual(problems, {})


if __name__ == '__main__':
    unittest.main()
