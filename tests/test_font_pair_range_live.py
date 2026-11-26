"""The owner, 2026-11-25 ("א. צריך שיהיה את כל המגוון"): the font-pair library offers the full range (DECISIONS.md).
What only the network and a browser can show, on the real path:

* the allowed list is what Google Fonts states today: for every family, google/fonts' METADATA.pb names the licence,
  the categories, the classifications and the script subsets the library records, fonts.googleapis.com/css2 serves
  exactly the recorded weights in the family's script subset, and it serves every weight a pair loads for the script's
  sample letters (text=);
* every Hebrew pair, locked into the design contract (typography.contract_fonts) and rendered by the section library
  with the richest content and its headings near the script's length limits, in every art direction the pair serves:
  at 320, 390, 768 and 1440 px the page does not scroll sideways, no heading is wider than its box or runs off the
  screen, the h1-h3 are set in the pair's display face and the text in its body face, no text is set in another face,
  and every face the text uses really loaded (for each family and weight in use, a FontFace of that family and weight,
  status 'loaded', covering the letters set in it) -- never a silent system font.
Arabic and Latin pairs are not rendered on the library's page (it writes its own words in Hebrew only, warehouse 129);
that every one of their faces loads for its script is tests/test_font_pairs_load.py.

These tests need fonts.googleapis.com, fonts.gstatic.com and raw.githubusercontent.com. When one cannot be reached they
FAIL and say so; they never pass on a fallback. CI runs them in browser-python's font-range job."""
import copy
import re
import unittest
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from omni_prod import section_library as L
from omni_prod import typography as T
from omni_prod.g_apple import contract as C
from tests.test_font_pairs_load import FACES_JS, missing
from tests.test_section_library_conformance import FULL, PALETTES

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
METADATA = 'https://raw.githubusercontent.com/google/fonts/main/{}/METADATA.pb'
SAMPLE_PALETTE = {'formal': 'counsel', 'warm': 'hearth', 'bold': 'trade', 'elegant': 'blush'}
WIDTHS = (320, 390, 768, 1440)
LIBRARY_SCRIPTS = ('hebrew', 'arabic', 'latin')
# Headings near the Hebrew limits (scripts.json heading_max_chars: h1 and h2 70, h3 and h4 40), long words included.
H1 = 'מתכננים איתכם ומשפצים בשבילכם דירות ובתים פרטיים בירושלים ובסביבתה'
H2 = 'השירותים המקצועיים שלנו לתכנון, לעיצוב ולשיפוץ של דירות ובתים פרטיים'
CTA = 'מתכננים שיפוץ? דברו איתנו עוד היום ונבנה יחד תוכנית עבודה מסודרת'
H3 = ('תכנון אדריכלי ופיקוח הנדסי צמוד באתר', 'שיפוצים כלליים והתחדשות מטבחים ישנים',
      'ליווי מקצועי מול הרשויות והקבלנים', 'עיצוב פנים והתאמה אישית של חללים')
H4 = 'פגישת תכנון ראשונית בדירה עם האדריכלית'


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode('utf-8', 'replace')
    except (urllib.error.URLError, OSError) as exc:
        raise AssertionError(f'{url} could not be read ({exc}): it is NOT shown that the allowed list holds') from exc


def served(family: str, script: str, text: str | None = None) -> list[int]:
    """The weights (of 400 and 700) fonts.googleapis.com serves: in the script's subset, or for these letters."""
    q = f"family={urllib.parse.quote(family).replace('%20', '+')}:wght@400;700&display=swap"
    body = fetch('https://fonts.googleapis.com/css2?' + q + (f'&text={urllib.parse.quote(text)}' if text else ''))
    if text:
        return sorted({int(w) for w in re.findall(r'font-weight: (\d+);', body)})
    return sorted({int(w) for s, w in re.findall(r'/\* ([\w-]+) \*/\s*@font-face \{[^}]*?font-weight: (\d+);', body)
                   if s == script})


def long_content(direction: str) -> dict:
    c = copy.deepcopy(FULL)
    c['direction'] = direction
    c['hero']['title'] = H1
    c['services']['title'] = H2
    c['services']['items'] = [(t, d) for t, (_, d) in zip(H3, c['services']['items'])]
    c['cta']['title'] = CTA
    c['process']['steps'] = [(H3[i], d) for i, (_, d) in enumerate(c['process']['steps'])]
    c['pricelist']['groups'][0]['items'][0]['name'] = H4
    return c


def contract_for(palette: str, p: dict) -> dict:
    q = PALETTES[palette]
    return C.build(f"\n--- Approved project brief\nDesign: style clean; primary colour {q['primary']}; palette {q['primary']}, "
                   f"{q['accent']}, {q['background']}, {q['ink']} (primary, accent, background, text: test); font 'Heebo', "
                   'system-ui, sans-serif (load it from Google Fonts)', T.contract_fonts(p))


MEASURE = r'''() => {
  const doc = document.documentElement, vw = doc.clientWidth, out = {scroll: doc.scrollWidth - vw, over: []};
  const first = v => v.split(',')[0].trim().replace(/^["']|["']$/g, '');
  for (const el of document.querySelectorAll('h1, h2, h3, h4')) {
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    if (s.display === 'none' || s.visibility === 'hidden' || !r.width) continue;
    if (el.scrollWidth > el.clientWidth + 1 || r.left < -1 || r.right > vw + 1)
      out.over.push(`${el.tagName.toLowerCase()} ${Math.round(r.left)}..${Math.round(r.right)} of ${vw}, content ` +
                    `${el.scrollWidth} in ${el.clientWidth}: ${el.textContent.trim().slice(0, 30)}`);
  }
  out.display = [...new Set([...document.querySelectorAll('h1, h2, h3')].map(e => first(getComputedStyle(e).fontFamily)))];
  // the text: every paragraph and h4 but the hero panel's big number and a quote, which the library sets as display
  const text = [...document.querySelectorAll('main p, h4')].filter(e => !e.matches('.panel-figure') && !e.closest('blockquote'));
  out.body = [...new Set(text.map(e => first(getComputedStyle(e).fontFamily)))];
  // every face the visible text is set in (family, weight) with the letters it must cover
  const used = {};
  for (const el of document.querySelectorAll('h1, h2, h3, h4, main p, main li, .btn, .brand b')) {
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    if (s.display === 'none' || s.visibility === 'hidden' || !r.width) continue;
    const key = first(s.fontFamily) + '|' + s.fontWeight;
    used[key] = ((used[key] || '') + ' ' + el.textContent).slice(0, 600);
  }
  out.used = Object.entries(used).map(([k, t]) => [...k.split('|'), t]);
  return out; }'''


def have_browser() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:  # pragma: no cover
        return False
    return True


@unittest.skipUnless(have_browser(), 'playwright is required (CI: browser-python, font-range job, where a skip fails)')
class TheAllowedListLive(unittest.TestCase):
    def test_the_allowed_list_is_what_google_fonts_states_today(self):
        wrong, families = {}, T._LIBRARY['families']
        used = {}
        for script in LIBRARY_SCRIPTS:
            for p in T.pairs(script):
                for role in ('display', 'body'):
                    used.setdefault(p[role]['family'], (script, set()))[1].update(p[role]['weights'])
        def observe(family):
            entry, (script, weights) = families[family], used[family]
            meta = fetch(METADATA.format(entry['source'].split(' ', 1)[1].rsplit('/', 1)[0]))
            live = {'name': re.search(r'^name: "([^"]+)"', meta, re.M).group(1),
                    'licence': re.search(r'^license: "([^"]+)"', meta, re.M).group(1),
                    'categories': re.findall(r'^category: "([^"]+)"', meta, re.M),
                    'classifications': re.findall(r'^classifications: "([^"]+)"', meta, re.M),
                    'scripts': [s for s in LIBRARY_SCRIPTS if s in re.findall(r'^subsets: "([^"]+)"', meta, re.M)],
                    'weights': served(family, script)}
            recorded = {'name': family, **{k: entry[k] for k in ('licence', 'categories', 'classifications', 'scripts',
                                                                 'weights')}}
            letters = served(family, script, T.script(script)['sample'])
            return family, live, recorded, letters, weights

        # three requests a family, 62 families: eight at a time (measured locally: 21 s to 106 s one after another)
        with ThreadPoolExecutor(max_workers=8) as pool:
            for family, live, recorded, letters, weights in pool.map(observe, sorted(families)):
                if live != recorded or not weights <= set(letters):
                    wrong[family] = {'recorded': recorded, 'live': live, 'served_for_the_sample': letters}
        self.assertEqual(wrong, {})
        self.assertEqual(sorted({e['licence'] for e in families.values()} - set(T.LICENCES)), [])


@unittest.skipUnless(have_browser(), 'playwright is required (CI: browser-python, font-range job, where a skip fails)')
class EveryHebrewPairOnTheLibraryPage(unittest.TestCase):
    def test_every_hebrew_pair_fits_and_loads_in_every_direction_it_serves(self):
        from playwright.sync_api import sync_playwright
        problems, seen = {}, 0
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                ctx = browser.new_context(viewport={'width': 1440, 'height': 900}, reduced_motion='reduce')
                for p in T.pairs('hebrew'):
                    for direction in p['tones']:
                        key, found = f"{p['id']}/{direction}", []
                        doc, _ = L.page(long_content(direction), contract_for(SAMPLE_PALETTE[direction], p))
                        self.assertIn(T.font_link(p), doc, key)
                        page = ctx.new_page()
                        page.set_default_timeout(30_000)
                        page.set_content(doc, wait_until='load')
                        faces = page.evaluate(FACES_JS)
                        seen += len(faces)
                        for width in WIDTHS:
                            page.set_viewport_size({'width': width, 'height': 900})
                            m = page.evaluate(MEASURE)
                            if m['scroll'] > 1:
                                found.append(f'{width}px: the page scrolls sideways by {m["scroll"]}px')
                            found += [f'{width}px: {o}' for o in m['over']]
                        if m['display'] != [p['display']['family']] or m['body'] != [p['body']['family']]:
                            found.append(f"faces in use: headings {m['display']}, text {m['body']}")
                        pair_faces = {p['display']['family'], p['body']['family']}
                        outside = sorted({family for family, _, _ in m['used']} - pair_faces)
                        if outside:
                            found.append(f'text set in a face outside the pair: {outside}')
                        lost = [x for family, weight, text in m['used'] if family in pair_faces
                                for x in missing(faces, [(family, int(weight))], text)]
                        if lost:
                            found.append(f'not loaded: {lost}')
                        page.close()
                        if found:
                            problems[key] = found
            finally:
                browser.close()
        self.assertGreater(seen, 0, 'no font face reached the page: fonts.googleapis.com could not be reached, so it is '
                                    'NOT shown that the pairs load')
        self.assertEqual(problems, {})


if __name__ == '__main__':
    unittest.main()
