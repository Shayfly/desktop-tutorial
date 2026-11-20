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


if __name__ == '__main__':
    unittest.main()
