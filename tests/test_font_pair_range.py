"""The owner, 2026-11-25, on the font question: "א. צריך שיהיה את כל המגוון" -- the font-pair library offers the full
range, so different businesses get different, fitting pairs and their sites do not look alike (DECISIONS.md). On the
real path: the library as omni_prod/typography loads and checks it, and pair_for as the content route calls it.

* every pair is valid: each face's family is on the library's allowed list ('families'), under the SIL Open Font
  License or Apache 2.0, covers the pair's script and is served in the weights the page loads, and the body is a text
  face (a pair never has two display faces); every family on the list is used;
* every pair is reachable: pair_for chooses it for some business;
* the distribution: in every category of the business catalogue (vertical_palettes.json) and every supported script,
  thirty fixed business names use every pair of the category's tone -- more than one pair per tone, always;
* the library's own check (run when the module is imported) refuses each kind of invalid pair;
* every Hebrew pair, locked into the design contract, renders the section library's page in every direction it serves
  and every content shape of the library's conformance matrix, and passes the G-APPLE static check and every skill
  unit, with one h1, inside the truth gate's 45,000 characters, loading exactly its own faces.
That the licences and the weights are what Google Fonts states today, and that every Hebrew pair fits and loads on the
section library's page in Chromium, is tests/test_font_pair_range_live.py (it needs the network and a browser)."""
import copy
import re
import unittest
from collections import Counter
from unittest import mock

from omni_prod import section_library as L
from omni_prod import skill_units as U
from omni_prod import typography as T
from omni_prod import vertical_palettes as VP
from omni_prod.g_apple import contract as C
from omni_prod.g_apple import static
from omni_prod.section_library import DIRECTIONS
from tests.test_section_library_conformance import PALETTES, PREVIEW_CUT, UNITS, picture_less_only, shapes

SCRIPTS = ('hebrew', 'arabic', 'latin')
# Thirty business names per script, fixed: the distribution is measured on these, never on random ones.
NAMES = {
    'hebrew': ('כהן ושות׳', 'לוי ובניו', 'מספרת דני', 'מאפיית אורן', 'קפה נחמה', 'סטודיו מיכל', 'מרפאת השרון',
               'אטליז שמעון', 'גלריה רונית', 'יוסי חשמל', 'אינסטלציה אבי', 'הובלות משה', 'פיזיותרפיה גליה', 'משרד ברק',
               'צלמת נועה', 'מסעדת הגפן', 'קייטרינג עדן', 'צימר בגליל', 'וטרינר ד״ר שי', 'תכשיטי ליה', 'רהיטי הדר',
               'שיפוצי יעקב', 'מנעולן 24', 'נדל״ן אופק', 'אופנת טל', 'קוסמטיקה דנה', 'ציפורניים מאיה', 'כושר עם עידו',
               'מעדניית רחל', 'יין הכרמל'),
    'arabic': ('بيت الزيتون', 'مخبز الأمل', 'صالون نور', 'مقهى الياسمين', 'عيادة الشفاء', 'مطعم الأصيل', 'مكتب العدالة',
               'استوديو ريم', 'حلويات سلمى', 'ملحمة أبو خليل', 'كهرباء سامر', 'سباكة يوسف', 'نقل الأمانة', 'معرض فادي',
               'مصور كريم', 'تموين الضيافة', 'شاليهات الجليل', 'بيطري الرحمة', 'مجوهرات ليلى', 'أثاث الهدى',
               'ترميم البيت', 'أقفال سريعة', 'عقارات الأفق', 'أزياء رنا', 'تجميل دانة', 'أظافر مايا', 'نادي القوة',
               'بقالة رحاب', 'نبيذ الكرمل', 'تصميم هالة'),
    'latin': ('Cohen & Co', 'Levi and Sons', 'Danny Cuts', 'Oren Bakery', 'Cafe Nechama', 'Studio Michal', 'Sharon Clinic',
              'Simon Butchers', 'Gallery Ronit', 'Yossi Electric', 'Avi Plumbing', 'Moshe Movers', 'Galia Physio',
              'Barak Accounting', 'Noa Photography', 'The Vine', 'Eden Catering', 'Galilee Cabins', 'Dr Shai Vets',
              'Lia Jewels', 'Hadar Furniture', 'Jacob Renovations', 'Lock 24', 'Horizon Realty', 'Tal Fashion',
              'Dana Cosmetics', 'Maya Nails', 'Fit with Ido', 'Rachel Deli', 'Carmel Wines'),
}


def tone_of(category: str) -> str:
    """The tone the content route gives a category: its palette's art direction (site_content.decide)."""
    return DIRECTIONS['palettes'][VP.palette_for(category)[0]]['direction']


def distribution() -> dict:
    """{(script, category): Counter of the pair ids the thirty names get}, through pair_for itself."""
    out = {}
    for script in SCRIPTS:
        for category in sorted(VP.load()['categories']):
            out[(script, category)] = Counter(T.pair_for(script, category=category, tone=tone_of(category),
                                                         business=name)['id'] for name in NAMES[script])
    return out


class TheRange(unittest.TestCase):
    def test_every_tone_of_every_script_offers_at_least_three_pairs(self):
        counts = {(s, tone): len([p for p in T.pairs(s) if tone in p['tones']]) for s in SCRIPTS for tone in T.TONES}
        self.assertEqual({k: n for k, n in counts.items() if n < 3}, {}, counts)
        self.assertGreaterEqual(T.MIN_PAIRS_PER_TONE, 3)
        self.assertEqual(set(T._LIBRARY['pairs']), set(SCRIPTS))          # every supported script has its range

    def test_the_fixed_names_are_thirty_different_businesses_per_script(self):
        for script, names in NAMES.items():
            self.assertEqual((len(names), len(set(' '.join(n.split()).casefold() for n in names))), (30, 30), script)

    def test_thirty_businesses_of_every_category_use_every_pair_of_their_tone(self):
        found, short = distribution(), {}
        for (script, category), used in found.items():
            eligible = {p['id'] for p in T.pairs(script) if tone_of(category) in p['tones']}
            self.assertLessEqual(set(used), eligible, (script, category))
            if len(used) < 2 or set(used) != eligible:
                short[(script, category)] = dict(used)
        self.assertEqual(short, {}, 'a category whose thirty businesses do not use every pair of its tone')
        reached = {pid for used in found.values() for pid in used}
        self.assertEqual(reached, {p['id'] for s in SCRIPTS for p in T.pairs(s)}, 'a pair pair_for never chooses')

    def test_no_pair_takes_most_of_a_category(self):
        # measured 2026-11-25 on these names: at most 14 of 30 (Latin), 12 of 30 (Hebrew and Arabic)
        top = {k: max(used.values()) for k, used in distribution().items()}
        self.assertEqual({k: n for k, n in top.items() if n > 15}, {}, 'one pair takes more than half of a category')



SAMPLE_PALETTE = {'formal': 'counsel', 'warm': 'hearth', 'bold': 'trade', 'elegant': 'blush'}


def contract_for(palette: str, p: dict) -> dict:
    q = PALETTES[palette]
    return C.build(f"\n--- Approved project brief\nDesign: style clean; primary colour {q['primary']}; palette {q['primary']}, "
                   f"{q['accent']}, {q['background']}, {q['ink']} (primary, accent, background, text: test); font 'Heebo', "
                   'system-ui, sans-serif (load it from Google Fonts)', T.contract_fonts(p))


class EveryHebrewPairOnTheLibraryPage(unittest.TestCase):
    def test_every_hebrew_pair_passes_the_librarys_gates_in_every_direction_and_shape(self):
        problems, rendered = {}, 0
        for p in T.pairs('hebrew'):
            for direction in p['tones']:
                contract = contract_for(SAMPLE_PALETTE[direction], p)
                self.assertEqual(L.page_fonts(contract), ('hebrew', p), p['id'])
                for name, content in shapes().items():
                    content['direction'] = direction
                    doc, _ = L.page(content, contract)
                    rendered += 1
                    found = [f"g_apple {f['code']}" for f in static.check(doc, contract)]
                    found += [f'unit {u}: {r}' for u in UNITS for r in [U.run(u, doc)] if r.get('status') != 'pass'
                              and not (u == 'design_minimum' and name == 'minimal' and picture_less_only(r))]
                    if len(re.findall(r'<h1\b', doc)) != 1:
                        found.append('not exactly one h1')
                    if len(doc) >= PREVIEW_CUT:
                        found.append(f'{len(doc)} characters: past the truth gate cut')
                    if re.findall(r'<link rel="stylesheet" href="([^"]+)"', doc) != [
                            re.search(r'href="([^"]+)">$', T.font_link(p)).group(1)]:
                        found.append('the page does not load exactly its pair')
                    if found:
                        problems[f"{p['id']}/{direction}/{name}"] = found
        self.assertEqual(rendered, 4 * sum(len(p['tones']) for p in T.pairs('hebrew')))
        self.assertEqual(problems, {})

class TheAllowedList(unittest.TestCase):
    def test_every_face_is_listed_with_an_open_licence_its_script_and_its_weights(self):
        families, used = T._LIBRARY['families'], set()
        for script in SCRIPTS:
            for p in T.pairs(script):
                with self.subTest(pair=p['id']):
                    self.assertNotEqual(p['display']['family'], p['body']['family'])
                    for role in ('display', 'body'):
                        face = p[role]
                        entry = families[face['family']]
                        used.add(face['family'])
                        self.assertIn(entry['licence'], ('OFL', 'APACHE2'))
                        self.assertIn(script, entry['scripts'])
                        self.assertLessEqual(set(face['weights']), set(entry['weights']))
                        self.assertRegex(entry['source'], r'^google/fonts (ofl|apache)/[a-z0-9]+/METADATA\.pb$')
                    self.assertTrue(T.text_face(families[p['body']['family']]), 'a display face set as body text')
        self.assertEqual(set(families), used, 'the allowed list names a family no pair uses')

    def test_a_display_face_is_never_the_body(self):
        f = T._LIBRARY['families']
        self.assertEqual({n for n in ('Karantina', 'Playpen Sans Hebrew', 'Suez One', 'Bellefair', 'Secular One',
                                      'Varela Round', 'Lalezar', 'Rakkas', 'Lemonada', 'Baloo Bhaijaan 2', 'Changa',
                                      'Anton', 'Baloo 2', 'DM Serif Display', 'Playfair Display') if T.text_face(f[n])}, set())
        self.assertTrue(all(T.text_face(f[n]) for n in ('Heebo', 'Assistant', 'Alef', 'Cairo', 'Inter')))

    def test_the_library_check_refuses_each_kind_of_invalid_pair(self):
        T._check()                                                  # the library as committed passes

        def broken(change):
            lib = copy.deepcopy(T._LIBRARY)
            change(lib)
            return lib

        def pair(lib, pid):
            return next(p for s in lib['pairs'].values() for p in s if p['id'] == pid)

        def two_left(lib):                                          # 'bold' in Hebrew down to exactly two pairs
            bold = [p for p in lib['pairs']['hebrew'] if 'bold' in p['tones']]
            for p in bold[2:]:
                p['tones'] = [t for t in p['tones'] if t != 'bold'] or ['warm']

        cases = {
            # (Alef stays in use by he-bona-alef: only the unlisted family is wrong here)
            'a family not on the list': lambda lib: pair(lib, 'he-varela-alef')['body'].update(family='Comic Neue'),
            'a licence that is not OFL or Apache': lambda lib: lib['families']['Heebo'].update(licence='GPL-3.0'),
            'a family without the script': lambda lib: lib['families']['Alef'].update(scripts=['latin']),
            'a weight the family is not served in': lambda lib: pair(lib, 'he-bellefair-assistant')['display'].update(
                weights=[400, 700]),
            'a display face as body text': lambda lib: pair(lib, 'he-karantina-rubik').update(
                display=dict(pair(lib, 'he-karantina-rubik')['body']), body=dict(pair(lib, 'he-karantina-rubik')['display'],
                                                                                    fallback='system-ui, sans-serif')),
            'a tone left with two pairs': two_left,
            'a listed family no pair uses': lambda lib: lib['families'].update(
                {'Open Sans': dict(lib['families']['Heebo'], source='google/fonts ofl/opensans/METADATA.pb')}),
            'a family entry without its date': lambda lib: lib['families']['Rubik'].pop('read_on'),
        }
        for what, change in cases.items():
            with self.subTest(what), mock.patch.object(T, '_LIBRARY', broken(change)), \
                    self.assertRaises(T.FontNotInLibrary):
                T._check()


if __name__ == '__main__':
    unittest.main()
