"""Warehouse 126.4: a pair really loads in a browser, not only declared in CSS.

Chromium opens a page carrying the stylesheet link the section library writes for a pair (typography.font_link) and
text of the pair's script in each face and weight, waits for document.fonts.ready and reads document.fonts: for every
face and weight there must be a FontFace of that family whose status is 'loaded' and whose unicode-range covers the
script's letters. A face that did not load -- the page silently fell back to a system font -- fails, by name. The
same is read on the content route's page for the owner's brief (a production row read read-only), rendered by the
platform. Every pair of the library is loaded, Hebrew, Arabic and Latin.

This needs fonts.googleapis.com and fonts.gstatic.com. When they cannot be reached the test FAILS and says so; it
never passes on a fallback font."""
import json
import os
import re
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import site_content as SC
from omni_prod import typography as T
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import render as R

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))
PROMPT = FIXTURE['prompt']

FACES_JS = '''async () => {
  await document.fonts.ready;
  await new Promise(r => setTimeout(r, 50));
  await document.fonts.ready;
  return Array.from(document.fonts).map(f => ({family: f.family.replace(/^["']|["']$/g, ''), weight: String(f.weight),
                                              status: f.status, range: f.unicodeRange}));
}'''


def _ranges(unicode_range: str) -> list[tuple[int, int]]:
    out = []
    for part in unicode_range.split(','):
        m = re.fullmatch(r'\s*U\+([0-9A-Fa-f?]+)(?:-([0-9A-Fa-f]+))?\s*', part)
        if not m:
            continue
        lo = int(m.group(1).replace('?', '0'), 16)
        hi = int(m.group(2), 16) if m.group(2) else int(m.group(1).replace('?', 'F'), 16)
        out.append((lo, hi))
    return out


def missing(faces: list[dict], wanted: list[tuple[str, int]], sample: str) -> list[str]:
    """Each (family, weight) with no loaded FontFace covering every letter of the sample."""
    letters = {ord(c) for c in sample if c.isalpha()}
    out = []
    for family, weight in wanted:
        ok = [f for f in faces if f['family'] == family and f['weight'] == str(weight) and f['status'] == 'loaded']
        covered = set()
        for f in ok:
            covered |= {cp for cp in letters if any(a <= cp <= b for a, b in _ranges(f['range']))}
        if covered != letters:
            out.append(f'{family} {weight}')
    return out


def sample_page(p: dict) -> tuple[str, list[tuple[str, int]], str]:
    s = T.script(p['script'])
    wanted = [(p[role]['family'], w) for role in ('body', 'display') for w in p[role]['weights']]
    rows = ''.join(f'<p style="font-family: {T.stack(p[role])}; font-weight: {w}">{s["sample"]}</p>'
                   for role in ('body', 'display') for w in p[role]['weights'])
    doc = (f'<!doctype html><html {T.html_attrs(p["script"])}><head><meta charset="utf-8">{T.font_link(p)}</head>'
           f'<body>{rows}</body></html>')
    return doc, wanted, s['sample']


class EveryPairLoads(unittest.TestCase):
    def test_every_pair_of_the_library_loads_its_faces_for_its_script(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:  # pragma: no cover
            self.skipTest('playwright is required to load the fonts')
        failed, seen = {}, 0
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name in ('hebrew', 'arabic', 'latin'):
                    for p in T.pairs(name):
                        doc, wanted, sample = sample_page(p)
                        page = browser.new_page()
                        page.set_default_timeout(30_000)
                        page.set_content(doc, wait_until='load')
                        faces = page.evaluate(FACES_JS)
                        page.close()
                        seen += len(faces)
                        lost = missing(faces, wanted, sample)
                        if lost:
                            failed[p['id']] = lost
            finally:
                browser.close()
        self.assertGreater(seen, 0, 'no font face reached the page: fonts.googleapis.com could not be reached, so it '
                                    'is NOT shown that the pairs load')
        self.assertEqual(failed, {}, 'these faces did not load: the page would fall back to a system font')

    def test_the_routes_page_for_the_owners_brief_loads_its_pair(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:  # pragma: no cover
            self.skipTest('playwright is required to load the fonts')
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on'}):
            route = SC.decide(PROMPT, {'user_id': 'usr_owner_test'}, year='2026')
        doc, _ = R.render(FIXTURE['scripted_content'], Fx.fact_sheet(PROMPT), route.contract,
                          expect_fp=route.contract_fp, direction=route.direction, year='2026',
                          outline_titles=route.outline_titles, order=route.order, windows=route.windows)
        p = T.pair(route.font_pair)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page(viewport={'width': 1280, 'height': 900})
                page.set_default_timeout(30_000)
                page.set_content(doc, wait_until='load')
                faces = page.evaluate(FACES_JS)
                used = page.evaluate('''() => {
                  const h1 = document.querySelector("h1"), p = document.querySelector("main p");
                  const cs = e => getComputedStyle(e);
                  return {h1: [cs(h1).fontFamily, cs(h1).fontWeight, h1.textContent],
                          p: [cs(p).fontFamily, cs(p).fontWeight, p.textContent]};
                }''')
            finally:
                browser.close()
        first = lambda value: value.split(',')[0].strip().strip('\'"')     # Chromium quotes only a name with a space
        self.assertEqual((first(used['h1'][0]), first(used['p'][0])), (p['display']['family'], p['body']['family']))
        self.assertGreater(len(faces), 0, 'no font face reached the page: fonts.googleapis.com could not be reached')
        self.assertEqual(missing(faces, [(p['display']['family'], int(used['h1'][1]))], used['h1'][2])
                         + missing(faces, [(p['body']['family'], int(used['p'][1]))], used['p'][2]), [])


if __name__ == '__main__':
    unittest.main()
