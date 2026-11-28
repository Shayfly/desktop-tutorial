"""Warehouse 127, acceptance 6 (the owner's answer to DECISIONS.md question 13, 2026-11-22; the standing release of
2026-11-27): every business that reads a domain file gets a legal page derived from section 7 of that file, and the build
fails when it is missing. The page holds only what the platform knows, says in plain Hebrew that it is not legal advice,
shows the domain's questions for a lawyer (copyable), and invents no company number, regulator or terms."""
import copy
import http.client
import importlib.util
import json
import os
import re
import tempfile
import threading
import unittest
from pathlib import Path

from omni_prod import domain_registry as D
from omni_prod import part_ledger as PL
from omni_prod import section_library as L
from omni_prod import skill_units as U
from omni_prod.section_library import demo_law_firm as DEMO
from omni_prod.site_content import legal as LG
from omni_prod.site_content import render as R

ROOT = Path(__file__).resolve().parent.parent
DOMAINS = D.load()['domains']
GOOD = Path(D.DOCS, 'restaurant.md').read_text(encoding='utf-8')
FORM_PAGE = '<html><body><form data-wa="https://wa.me/1"></form></body></html>'
COOKIE_PAGE = '<html><body><div data-148-window="cookie_banner"></div></body></html>'
BARE_PAGE = '<html><body><p>hello</p></body></html>'


def _contract_and_content():
    _, contract, _ = DEMO.build()
    return contract, copy.deepcopy(DEMO.CONTENT)


class TheDomainFilesCarryTheirLegalSection(unittest.TestCase):
    def test_every_domain_has_the_two_required_groups_with_questions(self):
        self.assertEqual(len(DOMAINS), 30)
        for slug, d in DOMAINS.items():
            with self.subTest(slug):
                heads = {g['heading']: g['items'] for g in d['legal']['groups']}
                self.assertTrue(heads[D.LEGAL_EVERYWHERE])
                self.assertTrue(heads[D.LEGAL_ISRAEL])

    def test_the_platforms_own_rules_are_kept_apart_and_never_a_group(self):
        for slug, d in D.build()['domains'].items():                  # parsed now, not read from the committed file
            with self.subTest(slug):
                self.assertTrue(d['legal']['platform_rules'])
                self.assertNotIn(D.LEGAL_PLATFORM, [g['heading'] for g in d['legal']['groups']])

    def test_a_domain_without_the_israel_group_fails_naming_the_domain_and_the_group(self):
        text = GOOD.replace('### Israel\n', '### Elsewhere\n', 1)
        with self.assertRaises(D.DomainError) as ctx:
            D.parse(text, 'restaurant')
        self.assertIn('restaurant', str(ctx.exception))
        self.assertIn('Israel', str(ctx.exception))

    def test_a_domain_without_the_everywhere_group_fails_naming_it(self):
        text = GOOD.replace('### Applies almost everywhere\n', '### Applies sometimes\n', 1)
        with self.assertRaises(D.DomainError) as ctx:
            D.parse(text, 'restaurant')
        self.assertIn('Applies almost everywhere', str(ctx.exception))

    def test_a_group_with_no_items_fails_too(self):
        body = D._sections(GOOD)['7. Legal']
        start = body.index('### Israel')
        end = body.index('### European Union')
        text = GOOD.replace(body[start:end], '### Israel\n\n', 1)
        with self.assertRaises(D.DomainError) as ctx:
            D.parse(text, 'restaurant')
        self.assertIn('Israel', str(ctx.exception))

    def test_domain_by_slug_never_guesses(self):
        self.assertIsNone(D.domain_by_slug(None))
        self.assertEqual(D.domain_by_slug('restaurant')['slug'], 'restaurant')
        with self.assertRaises(D.DomainError):
            D.domain_by_slug('restaraunt')


class TheLegalDocument(unittest.TestCase):
    def setUp(self):
        _, self.c = _contract_and_content()

    def doc(self, slug='restaurant', html=FORM_PAGE):
        return LG.document(DOMAINS[slug], self.c, html)

    def test_it_says_in_plain_hebrew_that_it_is_not_legal_advice_and_says_it_first(self):
        for slug in DOMAINS:
            with self.subTest(slug):
                self.assertTrue(self.doc(slug)['notice'].startswith('זה לא ייעוץ משפטי.'))

    def test_the_questions_are_the_domains_two_groups_as_written_and_nothing_else(self):
        for slug, d in DOMAINS.items():
            with self.subTest(slug):
                q = self.doc(slug)['questions']
                by = {g['heading']: g['items'] for g in d['legal']['groups']}
                self.assertEqual([(g['heading'], g['items']) for g in q['groups']],
                                 [(h, by[h]) for h in (D.LEGAL_EVERYWHERE, D.LEGAL_ISRAEL)])
                for g in q['groups']:
                    for item in g['items']:
                        self.assertIn('- ' + item, q['copy_text'])

    def test_what_the_site_collects_is_read_from_the_page_not_assumed(self):
        form = ' '.join(self.doc(html=FORM_PAGE)['sections'][0]['paragraphs'])
        bare = ' '.join(self.doc(html=BARE_PAGE)['sections'][0]['paragraphs'])
        cookie = ' '.join(self.doc(html=COOKIE_PAGE)['sections'][0]['paragraphs'])
        self.assertIn('באתר יש טופס יצירת קשר', form)
        self.assertIn('לא נשמר באתר', form)
        self.assertIn('באתר אין טופס', bare)
        self.assertNotIn('טופס יצירת קשר', bare.replace('באתר אין טופס ששומר פרטים', ''))
        self.assertIn('הודעת עוגיות', cookie)
        self.assertNotIn('הודעת עוגיות', form)
        self.assertEqual(LG.collects(FORM_PAGE), {'form': True, 'cookie_window': False})
        self.assertEqual(LG.collects(BARE_PAGE), {'form': False, 'cookie_window': False})

    def test_it_invents_no_company_number_regulator_licence_or_terms(self):
        d = self.doc()
        own = json.dumps([d['title'], d['lead'], d['notice'], d['sections']], ensure_ascii=False)
        self.assertNotRegex(own, r'\d{5,}')                         # no registration number of any kind
        for word in ('ח.פ', 'ח״פ', 'רשם החברות', 'רישיון מספר', 'מורשה', 'תנאי השימוש הם', 'מאושר על ידי'):
            self.assertNotIn(word, own)
        self.assertIn('לא נמסר לנו', own)                            # a fact not given is said as not given

    def test_the_accessibility_claims_are_the_g3_units_that_exist(self):
        from omni_prod.skill_units import manifest, units
        self.assertEqual({u for u in units() if manifest(u)['gate'] == 'G3' and u.startswith('a11y_')},
                         set(LG.ACCESSIBILITY_CHECKS))
        text = ' '.join(self.doc()['sections'][2]['items'])
        for said in LG.ACCESSIBILITY_CHECKS.values():
            self.assertIn(said, text)
        self.assertIn('לא נבדק: שימוש בקורא מסך', text)             # and what was not checked

    def test_the_servers_log_claim_is_true_of_the_fixed_server(self):
        self.assertIn('self.address_string()', R.APP_PY)
        self.assertIn('ביומן טכני', ' '.join(self.doc()['sections'][0]['paragraphs']))

    def test_another_script_raises_and_never_falls_back_to_hebrew(self):
        with self.assertRaises(LG.LegalNotBuilt):
            LG.document(DOMAINS['restaurant'], self.c, FORM_PAGE, script='arabic')


class TheLegalPageRendered(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract, cls.c = _contract_and_content()
        cls.pages = {slug: LG.files(d, cls.c, FORM_PAGE, cls.contract)[LG.LEGAL_PAGE] for slug, d in DOMAINS.items()}

    def test_a_page_for_every_domain_right_to_left_with_one_h1_and_the_notice_in_the_visible_text(self):
        for slug, page in self.pages.items():
            with self.subTest(slug):
                self.assertIn('<html lang="he" dir="rtl">', page)
                self.assertEqual(len(re.findall(r'<h1\b', page)), 1)
                self.assertIn('זה לא ייעוץ משפטי', page)
                self.assertEqual(LG.findings({LG.LEGAL_PAGE: page, LG.LEGAL_JSON: json.dumps({'domain': slug})},
                                             DOMAINS[slug]), [])

    def test_every_question_of_the_domain_is_on_the_page_twice_as_a_list_and_in_the_copy_block(self):
        for slug in ('restaurant', 'clinic', 'lawyer'):
            for g in LG._groups(DOMAINS[slug], 'hebrew'):
                for item in g['items']:
                    with self.subTest(slug=slug, item=item[:40]):
                        self.assertEqual(self.pages[slug].count(L.e(item)), 2)

    def test_the_questions_are_marked_english_and_left_to_right_inside_the_hebrew_page(self):
        page = self.pages['restaurant']
        self.assertIn('<ul lang="en" dir="ltr">', page)
        self.assertIn('<textarea class="legal-copy" id="legal-copy" readonly', page)

    def test_the_page_passes_every_skill_unit_that_judges_a_page(self):
        names = [d for d in os.listdir(os.path.dirname(U.__file__))
                 if os.path.isdir(os.path.join(os.path.dirname(U.__file__), d)) and not d.startswith('_')]
        for slug in ('restaurant', 'clinic', 'lawyer'):
            failed = {u: U.run(u, self.pages[slug]) for u in names if U.run(u, self.pages[slug]).get('status') != 'pass'}
            self.assertEqual(failed, {}, slug)

    def test_it_carries_no_script_no_form_no_image_and_no_contact_link_of_its_own(self):
        page = self.pages['restaurant']
        self.assertNotRegex(page, r'<script\b(?!\s+type="application/ld\+json")|<form\b|<img\b|href="(tel:|mailto:|https://wa\.me)')

    def test_it_links_back_to_the_home_page(self):
        self.assertGreaterEqual(self.pages['restaurant'].count('href="index.html"'), 2)

    def test_the_footer_links_to_it_only_when_the_content_names_one(self):
        contract, c = _contract_and_content()
        without, _ = L.page(c, contract)
        self.assertNotIn(LG.HREF, without)
        c['legal_href'] = LG.HREF
        with_link, _ = L.page(c, contract)
        self.assertIn(f'<a href="{LG.HREF}">{L.LEGAL_LINK_TEXT}</a>', with_link)
        self.assertEqual(with_link.replace(f' · <a href="{LG.HREF}">{L.LEGAL_LINK_TEXT}</a>', ''), without)

    def test_a_business_without_a_domain_gets_no_page_and_the_evidence_says_so(self):
        contract, c = _contract_and_content()
        self.assertEqual(LG.files(None, c, FORM_PAGE, contract), {})
        self.assertEqual(LG.summary(None, {}), {'page': None, 'why': 'no domain file for this business'})
        self.assertIsNone(D.domain_for('alcohol'))                 # a category with no domain file yet
        self.assertEqual(LG.findings({}, None), [])
        self.assertTrue(LG.findings({LG.LEGAL_PAGE: 'x'}, None))   # a stray page of a business with no domain


class TheGateFailsWhenThePageIsMissingOrWrong(unittest.TestCase):
    def setUp(self):
        self.contract, self.c = _contract_and_content()
        self.d = DOMAINS['restaurant']
        files = LG.files(self.d, self.c, FORM_PAGE, self.contract)
        self.repo = {'public/index.html': f'<a href="{LG.HREF}">x</a>', **files}

    def test_a_whole_repository_passes(self):
        self.assertEqual(LG.findings(self.repo, self.d), [])

    def test_a_missing_page_is_found(self):
        del self.repo[LG.LEGAL_PAGE]
        self.assertTrue(any('is missing' in f for f in LG.findings(self.repo, self.d)))

    def test_a_missing_data_file_is_found(self):
        del self.repo[LG.LEGAL_JSON]
        self.assertTrue(any(LG.LEGAL_JSON in f for f in LG.findings(self.repo, self.d)))

    def test_a_home_page_that_does_not_link_to_it_is_found(self):
        self.repo['public/index.html'] = '<a href="#top">x</a>'
        self.assertTrue(any('does not link' in f for f in LG.findings(self.repo, self.d)))

    def test_a_page_without_the_not_legal_advice_line_is_found(self):
        self.repo[LG.LEGAL_PAGE] = self.repo[LG.LEGAL_PAGE].replace('זה לא ייעוץ משפטי', 'ייעוץ')
        self.assertTrue(any('not legal advice' in f or 'לא ייעוץ' in f for f in LG.findings(self.repo, self.d)))

    def test_a_page_missing_one_question_is_found(self):
        item = self.d['legal']['groups'][0]['items'][0]
        self.repo[LG.LEGAL_PAGE] = self.repo[LG.LEGAL_PAGE].replace(L.e(item), 'x')
        self.assertTrue(any('lacks the question' in f for f in LG.findings(self.repo, self.d)))

    def test_data_of_another_domain_is_found(self):
        self.repo[LG.LEGAL_JSON] = json.dumps({'domain': 'clinic'})
        self.assertTrue(any("names the domain 'clinic'" in f for f in LG.findings(self.repo, self.d)))

    def test_the_parity_executor_fails_the_build_on_it_in_every_mode(self):
        from omni_prod.autonomous_core import ExecutionReport
        from omni_prod.site_content import agents as A
        from omni_prod.site_content import Route

        class Inner:
            def execute(self, *, repository, spec):
                return ExecutionReport(True, (), '')

        class Core:
            site_route = Route('section_library', 'x', domain='restaurant')
            site_report = {}

        for mode in ('block', 'warn'):
            with self.subTest(mode):
                good = A.SiteParityExecutor(Inner(), Core, mode).execute(repository=self.repo, spec=None)
                self.assertTrue(good.passed)
                broken = {k: v for k, v in self.repo.items() if k != LG.LEGAL_PAGE}
                report = A.SiteParityExecutor(Inner(), Core, mode).execute(repository=broken, spec=None)
                self.assertFalse(report.passed)
                self.assertEqual([f.acceptance_id for f in report.failures], ['gate-SITE_LEGAL'])


class TheFixedServerServesIt(unittest.TestCase):
    def serve(self, with_legal: bool):
        tmp = tempfile.mkdtemp()
        Path(tmp, 'public').mkdir()
        Path(tmp, 'app.py').write_text(R.APP_PY, encoding='utf-8')
        Path(tmp, 'public', 'index.html').write_text('<html>home</html>', encoding='utf-8')
        if with_legal:
            Path(tmp, 'public', 'legal.html').write_text('<html>legal</html>', encoding='utf-8')
        spec = importlib.util.spec_from_file_location('site_app', Path(tmp, 'app.py'))
        app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app)
        server = app.make_server(0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_address[1]

        def get(path):
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
            conn.request('GET', path)
            r = conn.getresponse()
            return r.status, r.read().decode('utf-8')
        return get

    def test_legal_html_is_served_when_the_build_has_it(self):
        get = self.serve(True)
        self.assertEqual(get('/legal.html'), (200, '<html>legal</html>'))
        self.assertEqual(get('/'), (200, '<html>home</html>'))
        self.assertEqual(get('/api/records')[0], 404)

    def test_legal_html_is_404_when_it_does_not_exist(self):
        get = self.serve(False)
        self.assertEqual(get('/legal.html')[0], 404)
        self.assertEqual(get('/')[0], 200)


class TheRoutesFilesAreOneThing(unittest.TestCase):
    def test_the_part_ledger_knows_the_legal_files_by_the_same_names(self):
        self.assertEqual((PL.LEGAL_PAGE, PL.LEGAL_JSON), (LG.LEGAL_PAGE, LG.LEGAL_JSON))

    def test_the_reviews_page_fallback_leaves_the_legal_page_out_and_names_the_same_path(self):
        from omni_prod import skills_runtime as SR
        self.assertEqual(SR.LEGAL_PAGE_PATH, LG.LEGAL_PAGE)
        repo = {'public/index.html': '<html>home</html>', LG.LEGAL_PAGE: '<html>legal</html>'}
        self.assertEqual(sorted(SR._pages(repo, {})), ['public/index.html'])

    def test_the_renderer_version_covers_the_legal_text(self):
        import hashlib
        h = hashlib.sha256()
        for name in R._LIBRARY_FILES:
            h.update((Path(L.__file__).resolve().parent / name).read_bytes())
        for name in R._TYPOGRAPHY_FILES:
            h.update((Path(R.T.__file__).resolve().parent / name).read_bytes())
        h.update((R.HERE / 'render.py').read_bytes())
        self.assertNotEqual(h.hexdigest()[:16], R.RENDERER_VERSION)     # without legal.py it is another version

    def test_the_ledger_claims_the_files_of_a_build_with_a_domain(self):
        contract, c = _contract_and_content()
        files = LG.files(DOMAINS['restaurant'], c, FORM_PAGE, contract)
        claimed = {}
        L_ = PL._Ledger({**files, PL.PAGE: 'x'})
        PL._section_files(L_)
        claimed = {p: part for p, part in L_.claims.items()}
        self.assertEqual(claimed[LG.LEGAL_PAGE], 'page')
        self.assertEqual(claimed[LG.LEGAL_JSON], 'copy')


if __name__ == '__main__':
    unittest.main()
