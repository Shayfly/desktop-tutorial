"""The owner's law-firm brief, a production row read read-only (build bld_b0eb47a5, fingerprint asserted here), goes
through the fact sheet, a scripted content answer and the platform's render, and the page passes every gate that judges
a page: the 11 WORKER_GATES units, the G-APPLE static check against the route's contract, and the truth gate -- on the
page as the preview serves it (the generated hero's data URI inlined, cut at 45,000 characters) and on the whole page.
The render is deterministic, every fact on the page comes from the sheet, and the repository's own fixed tests pass
when they are run for real against the fixed server."""
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from html import unescape
from pathlib import Path
from types import SimpleNamespace

from omni_prod import fact_canon as F
from omni_prod import skill_units as U
from omni_prod.bidi_ranges import unwrapped_ranges
from omni_prod.g_apple import static
from omni_prod.generated_images import GeneratedImage, _Transform
from omni_prod.section_library import DIRECTIONS
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import render as R
from omni_prod.site_content import schema as K
from omni_prod.skill_units.gate import WORKER_GATES
from omni_prod.skill_units.gate import check as gate_check
from omni_prod.skills_runtime import _invented_contact

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))
PROMPT = FIXTURE['prompt']
TITLES = {'services': 'תחומי התמחות', 'about': 'על המשרד', 'process': 'איך זה עובד', 'faq': 'שאלות נפוצות',
          'contact': 'צור קשר'}
ORDER = ['hero', 'services', 'about', 'process', 'faq', 'contact']
CUT = 45_000
HERO = '148ai-asset://image/1'


def contract():
    from omni_prod import vertical_palettes as VP
    return R.render_contract(PROMPT, VP.palette_for('lawyers')[1])[0]


def render(doc=None, sheet=None, c=None):
    c = c or contract()
    return R.render(doc or FIXTURE['scripted_content'], sheet or Fx.fact_sheet(PROMPT), c, expect_fp=c['fingerprint'],
                    direction='formal', year='2026', outline_titles=TITLES, order=ORDER)


def visible(doc: str) -> str:
    return ' '.join(unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'(?s)<(script|style)\b.*?</\1>', ' ', doc))).split())


class TheProductionRow(unittest.TestCase):
    def test_the_fixture_is_the_production_prompt(self):
        self.assertEqual(hashlib.sha256(PROMPT.encode('utf-8')).hexdigest(), FIXTURE['prompt_sha256'])
        self.assertEqual(FIXTURE['prompt_sha256'], '41d10d6333900cf116de9da2e3ed38cffb58398fad8143132b4cab1d1eb5db61')
        self.assertEqual(FIXTURE['build_id'], 'bld_b0eb47a553c8442abdbc8ada7f2439dc')

    def test_the_sheet_is_the_truth_gates_canon(self):
        sheet = Fx.fact_sheet(PROMPT)
        self.assertEqual(sheet.canon_hash, F.build_canon(PROMPT).hash)
        self.assertEqual((sheet.phone, sheet.whatsapp, sheet.email, sheet.address, sheet.hours),
                         ('03-5551234', '050-5551234', 'office@cohen-law.co.il', 'דרך מנחם בגין 132, תל אביב',
                          ['א׳–ה׳ 09:00–18:00']))
        self.assertEqual([p['span'] for p in sheet.prices], ['250 ₪'])
        # 250 is the customer's price ("250 ₪"): reachable only as @price:1, never a number the copy may use
        self.assertEqual(sorted(sheet.allowed_numbers()), ['1500', '2008', '3'])
        self.assertEqual({(n['value'], n['noun'], n['kind']) for n in sheet.numbers},
                         {('2008', None, 'year'), ('3', 'עורכי דין', 'count'), ('1500', 'תיקים', 'count')})

    def test_the_model_never_sees_a_fact_value(self):
        seen = json.dumps(Fx.fact_sheet(PROMPT).for_model(), ensure_ascii=False)
        for value in ('5551234', 'office@cohen-law.co.il', 'מנחם בגין 132', '09:00', '250 ₪'):
            self.assertNotIn(value, seen)


class ThePage(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.contract = contract()
        cls.html, cls.skipped = render(c=cls.contract)

    def test_it_passes_every_worker_gate(self):
        failed = {g: gate_check(g, {R.PAGE: self.html}) for g in WORKER_GATES}
        self.assertEqual({g: r['failures'] for g, r in failed.items() if r['status'] != 'pass'}, {})

    def test_it_passes_the_design_contract_and_every_skill_unit(self):
        self.assertEqual(static.check(self.html, self.contract), [])
        self.assertEqual(unwrapped_ranges(self.html), [])
        self.assertEqual(U.run('design_minimum', self.html), {'status': 'pass'})

    def test_the_truth_gate_finds_nothing_on_the_whole_page(self):
        self.assertEqual(_invented_contact({R.PAGE: self.html}, {'request': PROMPT}), [])

    def test_the_customers_sections_in_order_under_the_customers_names(self):
        ids = re.findall(r'<section[^>]*\bid="(\w+)"', self.html)
        self.assertEqual(ids, ['top', 'services', 'about', 'process', 'faq', 'contact'])
        text = visible(self.html)
        at = [text.find(TITLES[k]) for k in ORDER[1:]]
        self.assertNotIn(-1, at)
        self.assertEqual(at, sorted(at))
        self.assertIn('cta: not in the customer\'s outline', [s for s in K.offered_sections(
            Fx.fact_sheet(PROMPT), DIRECTIONS['palettes']['counsel'], ORDER, TITLES)[1] for s in [f'{s[0]}: {s[1]}']])

    def test_whatsapp_goes_to_the_customers_whatsapp_number_and_the_landline_is_only_dialled(self):
        self.assertIn('https://wa.me/972505551234', self.html)
        self.assertNotIn('https://wa.me/97235551234', self.html)
        self.assertIn('href="tel:035551234"', self.html)

    def test_every_fact_on_the_page_comes_from_the_sheet(self):
        sheet = Fx.fact_sheet(PROMPT)
        phones, _ = F.page_phones(visible(self.html))
        self.assertEqual(phones, {F.parse_phone(sheet.phone).e164, F.parse_phone(sheet.whatsapp).e164})
        self.assertEqual(set(F._EMAIL.findall(self.html)), {sheet.email})
        for span in sheet.spans():
            self.assertIn(span, visible(self.html))
        # every number a visitor reads is one the customer wrote, a fact span's, a price span's, or the footer year
        allowed = sheet.allowed_numbers() | {Fx.norm_number(n) for s in sheet.spans() for n in re.findall(r'\d+', s)} \
            | {n for p in sheet.prices for n in re.findall(r'\d+', p['span'])} | {'2026'}
        shown = {Fx.norm_number(n) for n in re.findall(r'\d+(?:,\d{3})*', visible(self.html))}
        self.assertEqual(shown - allowed, set())

    def test_the_render_is_deterministic(self):
        again, skipped = render(c=self.contract)
        self.assertEqual(again, self.html)
        self.assertEqual(skipped, self.skipped)
        spec = SimpleNamespace(acceptance=[SimpleNamespace(id='accept-site-content'), SimpleNamespace(id='CUSTOMER-FACTS')])
        sheet = Fx.fact_sheet(PROMPT)
        bound = R.binds(sheet, self.contract, '2026')
        one = R.repository(FIXTURE['scripted_content'], sheet, self.html, spec=spec, contract=self.contract,
                           bound=bound, order_names=[TITLES[k] for k in ORDER[1:]])
        two = R.repository(copy.deepcopy(FIXTURE['scripted_content']), Fx.fact_sheet(PROMPT), again, spec=spec,
                           contract=self.contract, bound=R.binds(Fx.fact_sheet(PROMPT), self.contract, '2026'),
                           order_names=[TITLES[k] for k in ORDER[1:]])
        self.assertEqual(one, two)
        self.assertEqual((one['app.py'], one['tests/test_site.py']), (R.APP_PY, R.TEST_SITE))

    def test_a_contract_or_a_bind_that_does_not_match_is_refused(self):
        sheet = Fx.fact_sheet(PROMPT)
        with self.assertRaises(R.SiteRenderDefect):
            R.render(FIXTURE['scripted_content'], sheet, self.contract, expect_fp='0' * 16, direction='formal',
                     year='2026', outline_titles=TITLES, order=ORDER)
        bound = R.binds(sheet, self.contract, '2026')
        R.check_binds(dict(bound), bound)
        with self.assertRaises(R.SiteRenderDefect):
            R.check_binds({**bound, 'canon': 'another-brief'}, bound)


class TheServedCut(unittest.TestCase):
    """The truth gate reads preview_smoke's GET / cut at 45,000 characters. Images are delivered today as data URIs the
    engine's transform puts in place of the 148ai-asset:// marker (generated_images._Transform); a file server for the
    generated site is warehouse 118, so the route keeps that delivery. The largest generated hero the platform carries
    is web_rendition.BUDGET_BYTES (360,000 bytes, 480,000 base64 characters). With it inlined, every fact the truth gate
    requires and the hero's copy are inside the cut; the copy after the image is past it, and the route's pre-sandbox
    truth check reads the whole page as well (agents.prepass)."""

    @classmethod
    def setUpClass(cls):
        from omni_prod.web_rendition import BUDGET_BYTES
        sheet = Fx.fact_sheet(PROMPT, asset_plan=[{'place': 'hero', 'marker': HERO, 'alt': 'משרד עורכי דין בתל אביב',
                                                   'source': 'generated', 'index': 1}])
        cls.image = GeneratedImage(index=1, requirement_id='asset-002', purpose='hero/brand visual', mime='image/webp',
                                   width=1600, height=900, sha256='x', alt='משרד עורכי דין בתל אביב',
                                   data=b'\x00' * BUDGET_BYTES)
        cls.sheet = sheet
        cls.html, _ = render(sheet=sheet)
        cls.served = _Transform(None, [cls.image])({R.PAGE: cls.html})[R.PAGE]
        cls.cut = cls.served[:CUT]

    def test_the_image_is_inlined_and_the_page_is_past_the_cut(self):
        self.assertIn(HERO, self.html)
        self.assertGreater(len(self.served), CUT + 400_000)
        self.assertNotIn(HERO, self.served)

    def test_every_fact_the_truth_gate_requires_and_the_hero_copy_are_inside_the_cut(self):
        text = visible(self.cut)
        for span in ('03-5551234', 'דרך מנחם בגין 132, תל אביב', 'א׳–ה׳ 09:00–18:00'):
            self.assertIn(span, text)
        self.assertIn('wa.me/972505551234', self.cut)
        hero = FIXTURE['scripted_content']['sections']['hero']
        for key in ('title', 'lead', 'cta'):
            self.assertIn(hero[key], text)
        self.assertLess(self.cut.index('דרך מנחם בגין 132'), self.cut.index('data:image/webp'))

    def test_the_truth_gate_on_the_served_cut_finds_nothing(self):
        ctx = {'request': PROMPT, 'rendered_pages': {'/': self.cut}}
        self.assertEqual([f.to_dict() for f in _invented_contact({R.PAGE: self.served}, ctx)], [])

    def test_copy_past_the_cut_is_still_checked_on_the_whole_page(self):
        services = FIXTURE['scripted_content']['sections']['services']['title']
        self.assertNotIn(services, visible(self.cut))                  # said, not hidden: past the cut
        planted = self.served.replace(services, 'התקשרו 04-8123456', 1)
        whole = _invented_contact({R.PAGE: planted}, {'request': PROMPT})
        self.assertTrue(any('invented' in f.problem for f in whole))
        cut_only = _invented_contact({R.PAGE: planted}, {'request': PROMPT, 'rendered_pages': {'/': planted[:CUT]}})
        self.assertFalse(any('invented' in f.problem for f in cut_only))


class TheRepositoryRunsItsOwnTests(unittest.TestCase):
    def test_the_fixed_tests_pass_against_the_fixed_server(self):
        c = contract()
        html, _ = render(c=c)
        sheet = Fx.fact_sheet(PROMPT)
        spec = SimpleNamespace(acceptance=[SimpleNamespace(id=i) for i in ('accept-site-content', 'CUSTOMER-FACTS')])
        files = R.repository(FIXTURE['scripted_content'], sheet, html, spec=spec, contract=c,
                             bound=R.binds(sheet, c, '2026'), order_names=[TITLES[k] for k in ORDER[1:]])
        manifest = json.loads(files['.omni/project.json'])
        self.assertEqual(manifest['verify'][0]['acceptance_ids'], ['accept-site-content', 'CUSTOMER-FACTS'])
        with tempfile.TemporaryDirectory() as tmp:
            for path, text in files.items():
                target = Path(tmp) / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding='utf-8')
            run = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests'], cwd=tmp,
                                 capture_output=True, text=True, timeout=120)
        self.assertEqual(run.returncode, 0, run.stdout[-2000:] + run.stderr[-2000:])
        self.assertIn('5 passed', run.stdout)


if __name__ == '__main__':
    unittest.main()
