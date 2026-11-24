"""The content route's agents and executors, case by case, with no browser (these run in CI's test job).

The real section library, the real validator, the real gate executors and the real worker functions; only the model
gateway is scripted (AGENTS.md rule 2). The brief is the owner's production row (bld_b0eb47a5, read-only; its
fingerprint is asserted in test_site_content_render.py).

  the generator: a document still invalid after its one correction fails loudly, its problems in the evidence;
                 every section the page does not show is said with its reason, and an unexplained gap raises
  the repairer:  after a verified round, a refused rewrite ends the loop on its best version (never an exception that
                 throws the verified work away); a rewrite of a path it was not given is refused; a finding the
                 customer owns asks the customer
  the pre-pass:  the truth gate reads the page as served (data URIs in, cut at 45,000) and the whole page, each
                 named exactly; a gate in warn mode never blocks
  parity:        a served page that is not the rendered one, or a second HTML document, fails SITE_PARITY
  the worker:    the failure codes, the release message of a declined round, the 'site_route' evidence
"""
import copy
import json
import os
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tests.test_site_content_engine import BAD_PATH, BAD_TEXT, CONTENT, GOOD_TEXT, PROMPT, ScriptedGateway

from omni_prod import site_content
from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport, RepairDeclined
from omni_prod.site_content import agents as A
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import render as R

ROOT = Path(__file__).resolve().parent.parent
OWNER = {'user_id': 'usr_owner_test'}
NO_OUTLINE = PROMPT.replace('מבנה הדף:', 'מה חשוב לי:')          # the same brief, its sections not listed


class Passing:
    def __init__(self, tests=5):
        self.tests = tests

    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'ok', tests_executed=self.tests)


def routed(gw, *, prompt=PROMPT, executor=None, **env):
    """An engine with the route installed (OMNI_SITE_LIBRARY=on) and the given executor chain."""
    from omni_prod.autonomous_agents import ArchitectAgent, GeneratorAgent, RepairAgent
    from omni_prod.autonomous_core import AutonomousProductEngine
    engine = AutonomousProductEngine(architect=ArchitectAgent(gw), generator=GeneratorAgent(gw),
                                     repairer=RepairAgent(gw), executor=executor or Passing(),
                                     max_repair_rounds=3, repair_ceiling=3)
    with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on', **env}):
        route = site_content.install(engine, prompt=prompt, gateway=gw, request=OWNER, year='2026')
    assert route.route == 'section_library', route.reason
    return engine


def with_bad_copy():
    content = json.loads(json.dumps(CONTENT))
    return A.set_path(content, BAD_PATH, BAD_TEXT)


class TheGenerator(unittest.TestCase):
    def test_a_document_still_invalid_after_its_one_correction_fails_loudly(self):
        content = A.set_path(json.loads(json.dumps(CONTENT)), 'sections.services.items[1].desc',
                             'התקשרו אלינו 03-5551234 לייעוץ.')
        gw = ScriptedGateway(content=content)                  # the correction returns the same document
        engine = routed(gw)
        spec = engine.architect.create_spec(PROMPT)
        with self.assertRaises(A.SiteContentInvalid) as caught:
            engine.generator.generate(spec)
        self.assertEqual(gw.roles().count('content'), 2)       # the call and its one correction, no more
        self.assertIn(('sections.services.items[1].desc', 'FACT_IN_COPY'),
                      {(p['path'], p['code']) for p in engine.site_report['problems']})
        self.assertIn('FACT_IN_COPY', str(caught.exception))

    def test_every_section_the_page_does_not_show_is_said_with_its_reason(self):
        content = json.loads(json.dumps(CONTENT))
        for key, nav in (('services', 'תחומי התמחות'), ('about', 'על המשרד'), ('process', 'איך זה עובד'),
                         ('faq', 'שאלות נפוצות'), ('contact', 'צור קשר')):
            content['sections'][key]['nav'] = nav
        content['sections']['cta'] = {'title': 'נשמח לעזור בדיני עבודה'}   # stats and the price list left out
        gw = ScriptedGateway(content=content)
        engine = routed(gw, prompt=NO_OUTLINE)
        self.assertIsNone(engine.site_route.order)
        engine.generator.generate(engine.architect.create_spec(NO_OUTLINE))
        skipped = engine.site_report['skipped']
        self.assertIn('stats: offered, the model left it out', skipped)
        self.assertIn('pricelist: offered, the model left it out', skipped)
        self.assertIn('testimonials: no review the customer gave', skipped)
        self.assertEqual([s for s in skipped if ':' not in s], [])

    def test_a_section_the_library_leaves_out_with_no_known_reason_raises(self):
        with self.assertRaises(A.SiteRenderDefect):
            A.skipped_report([], ['faq'], {'faq': 'required'}, {'sections': {'faq': {}}})
        self.assertEqual(A.skipped_report([('cta', "not in the customer's outline")], ['cta'], {}, {'sections': {}}),
                         ["cta: not in the customer's outline"])


class TheRepairer(unittest.TestCase):
    """After a verified round (the real HE gate, at block, fails the copy), the route's repairer."""

    def build(self, rewrite):
        from omni_prod.skill_units.gate import SkillGateExecutor
        gw = ScriptedGateway(content=with_bad_copy(), rewrites=[rewrite])
        with mock.patch.dict(os.environ, {'OMNI_GATE_HE': 'warn'}):        # the pre-pass records it, the chain blocks
            engine = routed(gw, executor=SkillGateExecutor(Passing(), 'HE', 'block'))
            result = engine.build(PROMPT)
        return gw, engine, result

    def test_a_good_rewrite_is_ready_after_one_round(self):
        gw, engine, result = self.build({BAD_PATH: GOOD_TEXT})
        self.assertEqual((result.status, result.repair_rounds), ('ready', 1))
        self.assertEqual(json.loads(result.repository[R.SITE_JSON])['document'],
                         A.set_path(with_bad_copy(), BAD_PATH, GOOD_TEXT))

    def test_a_refused_rewrite_ends_the_loop_on_its_best_version(self):
        cases = {
            'a path it was not given': {BAD_PATH: GOOD_TEXT, 'sections.hero.title': 'כותרת אחרת לגמרי'},
            'a value that is not text': {BAD_PATH: 5},
            'a number the customer never wrote': {BAD_PATH: 'ליווי מקצועי בתלונה, ב-7 שלבים.'},
        }
        for label, rewrite in cases.items():
            with self.subTest(label):
                gw, engine, result = self.build(rewrite)
                self.assertEqual((result.status, result.stop_reason), ('failed', 'site_content_invalid'))
                # the verified round 0 is kept: its repository, its real failure
                self.assertEqual(json.loads(result.repository[R.SITE_JSON])['document'], with_bad_copy())
                self.assertEqual([f.acceptance_id for f in result.report.failures], ['gate-HE-he_gender'])
                self.assertEqual(engine.trace[-1]['repair_declined'], 'site_content_invalid')
                self.assertEqual(result.repair_rounds, 1)                 # the rewrite was a paid call
                self.assertEqual(gw.roles().count('rewrite'), 1)

    def test_a_rewrite_of_a_path_it_was_not_given_is_refused(self):
        sheet = Fx.fact_sheet(PROMPT)
        gw = ScriptedGateway(rewrites=[{BAD_PATH: GOOD_TEXT, 'sections.hero.lead': 'אחר'}])
        agent = A.ContentRepairAgent(gw)
        with self.assertRaises(A.SiteContentInvalid) as caught:
            agent.rewrite(CONTENT, {BAD_PATH: 'x'}, ['finding'], sheet)
        self.assertIn('sections.hero.lead', str(caught.exception))

    def test_a_finding_the_customer_owns_asks_the_customer(self):
        from omni_prod.fact_canon import MISSING_PREFIX
        from omni_prod.product_review import ProductReviewExecutor

        class Inner:
            def execute(self, *, repository, spec):
                raise AssertionError('not reached')
        review = ProductReviewExecutor(Inner(), gateway=None, max_reviews=1)
        problem = 'opening hours the customer never gave (invented): ו׳ 08:00–12:00'
        review.reviews.append({'round': 1, 'blocking': 1, 'findings': [
            {'skill': 'skill.copy_quality', 'problem': problem, 'source': 'static', 'severity': 'blocking'}]})
        prompt = PROMPT + '\n' + MISSING_PREFIX + 'hours.'
        engine = routed(ScriptedGateway(), prompt=prompt, executor=review)
        with self.assertRaises(RepairDeclined) as caught:
            engine.repairer.repair(spec=None, repo_summary={}, failures=[
                {'acceptance_id': 'REVIEW', 'message': f'QA review (skill.copy_quality): {problem}', 'evidence': ''}])
        self.assertEqual(caught.exception.stop_reason, 'needs_customer_input')
        self.assertEqual(engine.needs_input, ['hours'])


class ThePrepass(unittest.TestCase):
    """agents.prepass: the gates and the truth gate on the rendered page, before any sandbox time."""

    @classmethod
    def setUpClass(cls):
        from tests.test_site_content_render import contract
        cls.route = SimpleNamespace(prompt=PROMPT, contract=contract())
        cls.sheet = Fx.fact_sheet(PROMPT)

    def render(self, doc=None, sheet=None):
        c = self.route.contract
        return R.render(doc or CONTENT, sheet or self.sheet, c, expect_fp=c['fingerprint'], direction='formal',
                        year='2026', outline_titles={'services': 'תחומי התמחות', 'about': 'על המשרד',
                                                     'process': 'איך זה עובד', 'faq': 'שאלות נפוצות',
                                                     'contact': 'צור קשר'},
                        order=['hero', 'services', 'about', 'process', 'faq', 'contact'], windows=())[0]

    def review(self, found):
        return [f for f in found['block'] if f['acceptance_id'] == 'REVIEW']

    def test_the_truth_gate_reads_the_page_as_served_cut_at_45000(self):
        html = self.render()
        self.assertEqual(self.review(A.prepass(SimpleNamespace(repository_transform=None), self.route, html,
                                               self.sheet)), [])
        image = 'data:image/webp;base64,' + 'A' * 480_000

        def ahead_of_the_facts(repository):          # a served page whose image comes before every fact
            page = repository[R.PAGE]
            at = page.index('>', page.index('<body')) + 1
            return {**repository, R.PAGE: page[:at] + f'<img src="{image}" alt="x">' + page[at:]}
        found = self.review(A.prepass(SimpleNamespace(repository_transform=ahead_of_the_facts), self.route, html,
                                      self.sheet))
        self.assertTrue(found)
        self.assertEqual({f['evidence'] for f in found}, {'truth gate on the served cut'})
        self.assertTrue(all('facts the customer gave are missing' in f['message'] for f in found))

    def test_an_invented_fact_past_the_cut_is_caught_on_the_whole_page(self):
        # Since warehouse 118 the hero is a file and a typical page fits the cut; a page that does run past it (here
        # the served page is padded ahead of the services title) is still checked whole by the pre-pass.
        planted = 'התקשרו 04-8123456 לייעוץ'
        doc = A.set_path(json.loads(json.dumps(CONTENT)), 'sections.services.title', planted)
        html = self.render(doc, self.sheet)

        def past_the_cut(repository):
            page = repository[R.PAGE]
            return {**repository, R.PAGE: page.replace(planted, '<!--' + ' ' * A.PREVIEW_CUT + '-->' + planted, 1)}
        found = self.review(A.prepass(SimpleNamespace(repository_transform=past_the_cut), self.route, html, self.sheet))
        invented = [f for f in found if 'invented' in f['message']]
        self.assertTrue(invented)
        self.assertEqual({f['evidence'] for f in invented}, {'truth gate on the whole page'})
        self.assertFalse(any(f['evidence'] == 'truth gate on the served cut' for f in invented))

    def test_a_gate_in_warn_mode_never_blocks(self):
        html = self.render(with_bad_copy())
        with mock.patch.dict(os.environ, {'OMNI_GATE_HE': 'warn'}):
            found = A.prepass(SimpleNamespace(repository_transform=None), self.route, html, self.sheet)
        self.assertIn('gate-HE-he_gender', [f['acceptance_id'] for f in found['warn']])
        self.assertNotIn('gate-HE-he_gender', [f['acceptance_id'] for f in found['block']])
        with mock.patch.dict(os.environ, {'OMNI_GATE_HE': 'block'}):
            found = A.prepass(SimpleNamespace(repository_transform=None), self.route, html, self.sheet)
        self.assertIn('gate-HE-he_gender', [f['acceptance_id'] for f in found['block']])
        self.assertNotIn('gate-HE-he_gender', [f['acceptance_id'] for f in found['warn']])


class TheParityCheck(unittest.TestCase):
    def parity(self, served, repository, mode='warn'):
        from omni_prod.preview_smoke import PreviewReadyExecutor
        preview = object.__new__(PreviewReadyExecutor)
        preview.last_pages = {'/': served}

        class Inner:
            def __init__(self):
                self._inner = preview                       # chain walkers read the instance's _inner

            def execute(self, *, repository, spec):
                return ExecutionReport(True, (), 'ok', tests_executed=5)
        core = SimpleNamespace(site_report={})
        executor = A.SiteParityExecutor(Inner(), core, mode)
        return executor.execute(repository=repository, spec=None), core.site_report['parity']

    def test_the_served_page_is_the_rendered_page_and_the_only_page(self):
        page = '<!doctype html><html lang="he" dir="rtl"><body><p>שלום</p></body></html>'
        report, parity = self.parity(page, {R.PAGE: page, 'app.py': 'x'})
        self.assertEqual((report.passed, parity['status'], parity['findings']), (True, 'pass', []))
        report, parity = self.parity('<p>another page</p>', {R.PAGE: page})
        self.assertEqual(parity['status'], 'fail')
        self.assertIn('the served GET / is not the rendered public/index.html', parity['findings'])
        self.assertTrue(report.passed)                                 # warn: recorded, not blocking
        report, parity = self.parity(page, {R.PAGE: page, 'public/other.html': page})
        self.assertEqual(parity['status'], 'fail')
        self.assertIn("other HTML documents in the repository: ['public/other.html']", parity['findings'])
        report, _ = self.parity('<p>another page</p>', {R.PAGE: page}, mode='block')
        self.assertEqual((report.passed, [f.acceptance_id for f in report.failures]), (False, ['gate-SITE_PARITY']))


class TheWorker(unittest.TestCase):
    def test_the_failure_codes(self):
        from omni_prod.worker_tasks import failure_code
        self.assertEqual(failure_code(A.SiteContentInvalid('x')), 'site_content_invalid')
        self.assertEqual(failure_code(A.SiteRenderDefect('x')), 'site_render_defect')

    def test_the_release_message_of_a_declined_round(self):
        from omni_prod.worker_tasks import evaluate_release_gates
        ok = SimpleNamespace(passed=True, score=90, minimum_score=80, blockers=(), publish_allowed=True)

        def message(stop_reason, rounds=0):
            result = SimpleNamespace(status='failed', stop_reason=stop_reason, repair_rounds=rounds, repository={},
                                     report=ExecutionReport(False, (AcceptanceFailure('gate-G3-a11y_alt_text', 'no alt'),)))
            return evaluate_release_gates(result=result, quality=ok, security=ok, rights=ok)
        for reason in ('platform_render_defect', 'unowned_finding'):
            passed, code, text = message(reason)
            self.assertEqual((passed, code), (False, 'verification_failed'))
            self.assertIn("platform's own page renderer", text)
            self.assertIn('after 0 repair round(s)', text)
        passed, code, text = message('site_content_invalid', 1)
        self.assertIn("the repair model's rewrite of the copy was refused", text)

    def test_the_site_route_evidence_on_both_paths(self):
        from omni_prod import worker_tasks as W
        self.assertIsNone(W._site_route_evidence(None))
        with mock.patch.object(site_content, 'report', side_effect=RuntimeError('boom')):
            self.assertIsNone(W._site_route_evidence(SimpleNamespace()))
        source = (ROOT / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        self.assertEqual(len(re.findall(r"'site_route': site_content\.report\(engine\)", source)), 1)     # success
        self.assertEqual(len(re.findall(r"'site_route': _site_route_evidence\(engine\)", source)), 1)     # failure
        engine = SimpleNamespace()
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'off'}):
            site_content.install(engine, prompt=PROMPT, gateway=None, request=OWNER)
        self.assertEqual(W._site_route_evidence(engine)['reason'], 'flag_off')


class TheAdvisoryFilter(unittest.TestCase):
    """The model reviewer's blocking finding is advisory on the route: the round passes with the threshold's own test
    count, and the review record counts it as advisory, so the release policy reads the tests and the review as they
    are (the real VerificationGroup, ProductReviewExecutor and QualityAwareExecutor; the sandbox is a passing
    threshold here -- the Chromium engine test runs the full chain and the worker's release report)."""

    def test_a_reviewer_finding_never_fails_the_release(self):
        from omni_prod.product_review import ProductReviewExecutor
        from omni_prod.quality_gate import QualityAwareExecutor
        from omni_prod.release_policy import build_report  # noqa: F401  (the policy the worker runs)
        from omni_prod.verification_group import VerificationGroup
        review = {'findings': [{'skill': 'spec', 'severity': 'blocking', 'file': 'public/index.html',
                                'problem': 'The hero does not name the city in its title', 'fix': 'add the city'}]}
        gw = ScriptedGateway(review=review)
        threshold = Passing(tests=5)
        stage = ProductReviewExecutor(threshold, gateway=gw, max_reviews=2)
        assessed = []
        chain = QualityAwareExecutor(VerificationGroup(threshold, (stage,)), quality_fn=lambda **_: (
            assessed.append(1), SimpleNamespace(passed=True))[1])
        engine = routed(gw, executor=chain)
        result = engine.build(PROMPT)
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0))
        self.assertEqual(assessed, [1])            # the round the filter passed still met the quality assessment
        self.assertEqual(result.report.tests_executed, 5)          # the threshold's count, not None (UNKNOWN)
        last = stage.reviews[-1]
        self.assertEqual((last['blocking'], last['advisory']), (0, 1))
        self.assertEqual([f.get('route_owner') for f in last['findings'] if f['source'] == 'reviewer'], ['advisory'])
        feedback = site_content.report(engine)['library_feedback']
        self.assertTrue(any(f['acceptance_id'] == 'REVIEW' and 'city' in f['message'] for f in feedback), feedback)
        self.assertNotIn('rewrite', gw.roles())


if __name__ == '__main__':
    unittest.main()
