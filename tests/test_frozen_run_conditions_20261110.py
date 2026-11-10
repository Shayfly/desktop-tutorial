"""Michael 2026-11-10: conditions 1-5 that must be green before the frozen run's baseline SHA is handed over."""
import inspect
import json
import unittest

from omni_prod import product_review
from omni_prod.fact_canon import parse_phone
from omni_prod.probe_manifest import NOT_YET_PROBED, PROBES, critical_probes, is_critical
from omni_prod.skills_runtime import WEB_SKILLS, static_findings

from tests.test_gate_mutations_20261110 import GOOD_PAGE, REQUEST


class PhoneBounds(unittest.TestCase):
    """No 0, no 972: < 7 SHORT, > 9 LONG, 7/8/9 AMBIGUOUS."""

    def test_bounds(self):
        for raw, reason in [('123456', 'SHORT'), ('1234567', 'AMBIGUOUS'), ('81234567', 'AMBIGUOUS'),
                            ('512345678', 'AMBIGUOUS'), ('5123456789', 'LONG')]:
            self.assertEqual(parse_phone(raw).reason, reason, raw)


class ManifestIsTheLaw(unittest.TestCase):
    """Conditions 1 and 2: every probe is in the manifest; reads_source and critical are declared, not inferred."""

    def checks(self):
        return {c.__name__: (c, s.key) for s in WEB_SKILLS for c in s.static_checks}

    def test_every_static_check_is_in_the_manifest_with_its_skill(self):
        for name, (_, skill) in self.checks().items():
            self.assertIn(name, PROBES, f'{name} is not declared in omni_prod/probe_manifest.py')
            self.assertEqual(PROBES[name]['skill'], skill, name)

    def test_source_readers_are_exactly_the_declared_six(self):
        readers = sorted(n for n, p in PROBES.items() if p['reads_source'])
        self.assertEqual(len(readers), 6, readers)              # 5 code checks + the quality gate's secret scan
        self.assertIn('quality_gate.secret_scan', readers)
        for name, (check, _) in self.checks().items():
            src = inspect.getsource(check)
            reads = '_text_files(' in src and '_pages(' not in src
            self.assertEqual(bool(PROBES[name]['reads_source']), reads, f'{name}: manifest and code disagree')
            self.assertEqual(bool(getattr(check, 'reads_source', None)), reads, f'{name}: @reads_source missing')
        # the quality gate really scans source for secrets (the sixth reader is real, not a placeholder)
        from omni_prod import quality_gate
        self.assertIn('hard-coded secret', inspect.getsource(quality_gate.assess_repository))

    def test_critical_set_is_declared_and_not_empty(self):
        crit = critical_probes()
        self.assertTrue(crit)
        self.assertTrue({'_rtl_for_hebrew', '_invented_contact', '_images_without_alt'} <= crit)
        self.assertIn('json_ld_schema', NOT_YET_PROBED)          # declared as missing, not silently absent
        self.assertFalse(is_critical('_styled_page'))

    def test_findings_carry_their_probe(self):
        found = static_findings({'index.html': GOOD_PAGE.replace(' dir="rtl"', '')}, {'request': REQUEST})
        self.assertIn('_rtl_for_hebrew', {f.probe for f in found})


class RepeatQuarantineEscalates(unittest.TestCase):
    """Condition 5: a probe quarantined again (an earlier build also quarantined it) stops the build for a human."""

    def setUp(self):
        self._saved = product_review._QUARANTINE_HISTORY

    def tearDown(self):
        product_review._QUARANTINE_HISTORY = self._saved

    def _three_rounds(self):
        from omni_prod.autonomous_core import ExecutionReport
        from omni_prod.product_review import ProductReviewExecutor

        class Inner:
            def execute(self, *, repository, spec):
                return ExecutionReport(True, (), '')

        spec = type('S', (), {'title': '', 'summary': '', 'requirements': (), 'acceptance': ()})()
        ex = ProductReviewExecutor(Inner(), gateway=None, max_reviews=6, request_text=REQUEST)
        repo = {'index.html': GOOD_PAGE.replace(' dir="rtl"', '')}
        ex.execute(repository=repo, spec=spec)
        ex.execute(repository=repo, spec=spec)
        return ex, (lambda: ex.execute(repository=repo, spec=spec))

    def test_first_quarantine_continues(self):
        product_review._QUARANTINE_HISTORY = lambda probe: None
        ex, third = self._three_rounds()
        self.assertTrue(third().passed)
        self.assertFalse(ex.quarantined[0]['repeat_quarantine'])

    def test_second_quarantine_stops(self):
        from omni_prod.build_control import BuildCancelled, GateEscalation
        product_review._QUARANTINE_HISTORY = lambda probe: 'bld_earlier' if probe == '_rtl_for_hebrew' else None
        ex, third = self._three_rounds()
        with self.assertRaises(GateEscalation) as ctx:
            third()
        self.assertIn('bld_earlier', str(ctx.exception))
        self.assertTrue(issubclass(GateEscalation, BuildCancelled))   # settles like a cancel, nothing half-done


class CanonNeedsAnExplicitTick(unittest.TestCase):
    """Condition 3: an incomplete canon is approved only with the box ticked."""

    def test_ui_renders_a_checkbox_and_sends_canon_ack(self):
        js = open('omni_prod/assets/app.js', encoding='utf-8').read()
        self.assertIn("a.canon.status === 'CANON_INCOMPLETE'", js)
        self.assertIn("type: 'checkbox', id: 'canonAck'", js)
        self.assertIn('canon_ack: incomplete ? Boolean(box && box.checked) : false', js)

    def test_api_model_and_supervisor_accept_the_tick(self):
        from omni_prod.conversation.supervisor import ConversationSupervisor as ChiefSupervisor
        from omni_prod.investor_app import V28SpecApproval
        self.assertFalse(V28SpecApproval(brief_fingerprint='a' * 64).canon_ack)
        self.assertIn('canon_ack', inspect.signature(ChiefSupervisor.approve_spec).parameters)


class GateRegressionTool(unittest.TestCase):
    """Condition 4: the tool the workflow runs on the approved builds."""

    def test_gates_on_a_served_page(self):
        from omni_prod.gate_regression import run
        ok = run({'page.py': 'x'}, REQUEST, pages={'/': GOOD_PAGE, 'assets': ''})
        self.assertTrue(ok['passed'], ok['blocking'])
        bad = run({'page.py': 'x'}, REQUEST, pages={'/': GOOD_PAGE.replace('050-1234567', '052-9876543'), 'assets': ''})
        self.assertFalse(bad['passed'])
        self.assertEqual(bad['blocking'][0]['probe'], '_invented_contact')

    def test_starts_a_real_product_like_the_preview_smoke(self):
        from omni_prod.gate_regression import run
        app = ('import os\nfrom http.server import BaseHTTPRequestHandler, HTTPServer\n'
               'PAGE = open("page.html", encoding="utf-8").read().encode("utf-8")\n'
               'class H(BaseHTTPRequestHandler):\n'
               '    def do_GET(self):\n'
               '        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")\n'
               '        self.end_headers(); self.wfile.write(PAGE)\n'
               '    def log_message(self, *a): pass\n'
               'HTTPServer(("0.0.0.0", int(os.environ["PORT"])), H).serve_forever()\n')
        repo = {'app.py': app, 'page.html': GOOD_PAGE,
                '.omni/project.json': json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim',
                                                  'start': ['python', 'app.py'], 'port': 8765, 'health_path': '/'})}
        r = run(repo, REQUEST)
        self.assertTrue(r['served'], r['smoke'])
        self.assertTrue(r['passed'], r['blocking'])


if __name__ == '__main__':
    unittest.main()


class ReportRow(unittest.TestCase):
    def test_row_from_evidence(self):
        from omni_prod.frozen_run_report import report_row
        job = {'id': 'bld_x', 'status': 'ready', 'repair_rounds': 2, 'actual_provider_cost_usd': '0.74',
               'started_at': '2026-11-09T23:36:56Z', 'finished_at': '2026-11-09T23:43:27Z'}
        ev = {'gate_waste': {'rounds': 2, 'measured_usd': '0.30', 'quarantined_gates': [
                  {'probe': '_rtl_for_hebrew', 'critical': True}]},
              'design_review': {'reviews': [{'score': 83}]},
              'product_review': [{'canon_hash': 'abc'}],
              'model_route_events': [{'model': 'claude-sonnet-5-5', 'outcome': 'ok'}]}
        row = report_row(arm='restaurant-a', job=job, evidence=ev, baseline_sha='sha', pinned_models={'claude-sonnet-5-5'})
        self.assertFalse(row['passed'])                  # 2 code-changing rounds = failure by the pre-registration
        self.assertTrue(row['degraded'])                 # a critical probe was quarantined
        self.assertEqual(row['timeToPreviewSec'], 391)
        self.assertEqual(row['gateWasteShare'], round(0.30 / 0.74, 4))
        self.assertEqual((row['designScore'], row['canonHash'], row['offPinModels']), (83, 'abc', []))


class RegressionFindings20261110(unittest.TestCase):
    """The first gate-regression run (2026-11-10) failed the approved cafe. Diagnosis: the workflow read an empty prompt
    (wrong table), and reviews the customer GAVE were not canon facts. Both are fixtures now."""

    CAFE = ('שם העסק: קפה "בוקר טוב" – בית קפה שכונתי כתובת: רחוב הנביאים 12, חיפה טלפון ו-WhatsApp: 050-1234567 '
            'שעות פתיחה: א׳–ה׳ 07:00–19:00, ו׳ 07:00–14:00 5. שלוש ביקורות של לקוחות: • "הקפה הכי טוב בחיפה" – דנה '
            '• "ארוחת בוקר מושלמת, נחזור" – יוסי ומיכל • "שירות חם ומחירים הוגנים" – אבי 6. שעות')
    FLORIST = ('תבנה לי דף לחנות הפרחים שלי, "שושנת העמקים", ברח\' נתיב המזלות 22, ירושלים.\n'
               'שיהיה כפתור להתקשר 052-1234567 וכפתור וואטסאפ לאותו מספר, עם הודעה מוכנה "היי, אשמח להזמין זר".\n'
               "אנחנו פתוחים א'–ה' 8:00–19:00, ו' 8:00–13:00, שבת סגור.\n"
               'שיהיה קטע עם מה שאומרים עלינו, ורשימה של זרים לחתונה, ליומולדת ולניחומים.')

    def page(self, reviews, contact):
        quotes = ''.join(f'<blockquote>“{q}” – {n}</blockquote>' for q, n in reviews)
        return (f'<html lang="he" dir="rtl"><body><h2>מה אומרים עלינו</h2>{quotes}{contact}</body></html>')

    def blocking(self, prompt, page):
        from omni_prod.fact_canon import build_canon
        ctx = {'request': prompt, 'canon': build_canon(prompt), 'rendered_pages': {'/': page, 'assets': ''}}
        return [(f.probe, f.problem) for f in static_findings({'a.py': 'x'}, ctx)
                if f.severity == 'blocking' and f.probe != '_styled_page']

    def test_canon_facts_of_both_briefs(self):
        from omni_prod.fact_canon import build_canon
        cafe = build_canon(self.CAFE)
        self.assertEqual(cafe.values('phone'), {'+972501234567'})
        self.assertEqual(cafe.values('address'), {'רחוב הנביאים 12 חיפה'})       # never "חיפה טלפון"
        self.assertEqual(len(cafe.values('review')), 3)                          # the business name is not a review
        self.assertEqual(cafe.values('name'), {'קפה "בוקר טוב"'})
        florist = build_canon(self.FLORIST)
        self.assertEqual(florist.values('phone'), {'+972521234567'})
        self.assertEqual(florist.values('address'), {'רחוב נתיב המזלות 22 ירושלים'})
        self.assertEqual(florist.values('hours'), {"א'–ה' 8:00–19:00", "ו' 8:00–13:00"})
        self.assertEqual(florist.values('review'), set())

    def test_cafe_with_its_given_reviews_passes(self):
        page = self.page([('הקפה הכי טוב בחיפה', 'דנה'), ('ארוחת בוקר מושלמת, נחזור!', 'יוסי ומיכל'),
                          ('שירות חם ומחירים הוגנים', 'אבי')],
                         '<p>רחוב הנביאים 12</p><a href="tel:050-1234567">050-1234567</a><a href="https://wa.me/972501234567">x</a>')
        self.assertEqual(self.blocking(self.CAFE, page), [])

    def test_cafe_with_one_invented_review_blocks(self):
        page = self.page([('הקפה הכי טוב בחיפה', 'דנה'), ('הכי טעים שיש, ממליצה בחום', 'רותי')], '')
        self.assertTrue(any('testimonials' in p for _, p in self.blocking(self.CAFE, page)))

    def test_florist_reviews_need_the_sample_label(self):
        contact = '<a href="tel:+972521234567">052-1234567</a><p>רח\' נתיב המזלות 22</p>'
        invented = self.page([('הזרים הכי יפים בעיר', 'שירה'), ('שירות מהיר ואדיב', 'דני')], contact)
        self.assertTrue(any('testimonials' in p for _, p in self.blocking(self.FLORIST, invented)))
        labelled = invented.replace('מה אומרים עלינו', 'מה אומרים עלינו (לדוגמה)')
        self.assertEqual(self.blocking(self.FLORIST, labelled), [])

    def test_workflow_reads_the_approved_prompt_and_refuses_an_empty_one(self):
        wf = open('.github/workflows/gate-regression.yml', encoding='utf-8').read()
        self.assertIn('JOIN build_requests r ON r.build_id = b.id', wf)
        self.assertIn('refusing an empty canon', wf)
        self.assertIn('SET TRANSACTION READ ONLY', wf)
        self.assertIn('--network none', wf)


class PreRegistration(unittest.TestCase):
    def test_document_has_the_rules(self):
        doc = open('docs/frozen-run-20261110.md', encoding='utf-8').read()
        for needle in ('noFixRule:', 'blindReview:', 'rollback:', 'manifestHash:', 'fixturesCommit:', 'knownGaps:',
                       'restaurant-a AND restaurant-b pass', '`informed`', '`warned`', 'verbatim',
                       'service:', 'measurement:', '`truth-inert`'):
            self.assertIn(needle, doc)

    def test_every_required_field_and_the_warned_rule(self):
        from omni_prod.frozen_run_report import REQUIRED_FIELDS, report_row
        job = {'id': 'b', 'status': 'ready', 'repair_rounds': 0, 'actual_provider_cost_usd': '0.4'}
        row = report_row(arm='florist-new', job=job, evidence={}, baseline_sha='s', informed=True,
                         warned={'shown': True, 'tick_required': True, 'refused_until_ticked': False})
        self.assertEqual([f for f in REQUIRED_FIELDS if f not in row], [])
        self.assertFalse(row['passed'])                  # the server accepted before the tick -> not a pass
        ok = report_row(arm='florist-new', job=job, evidence={}, baseline_sha='s', informed=True,
                        warned={'shown': True, 'tick_required': True, 'refused_until_ticked': True})
        self.assertTrue(ok['passed'] and ok['warned'] and ok['informed'])
        self.assertEqual(ok['knownGaps'], ['json_ld_schema'])


class LiteralReviewsAndAggregates(unittest.TestCase):
    """Michael 2026-11-10 items 1-2: a review matches only verbatim (after normalisation) with its author; a count is a
    separate claim that needs its number in the canon."""

    REQ = 'ביקורות: "הקפה הכי טוב בחיפה" – דנה • "שירות חם ומחירים הוגנים" – אבי • יש לנו מעל 50 ביקורות בגוגל'

    def blocking(self, body):
        from omni_prod.fact_canon import build_canon
        page = f'<html lang="he" dir="rtl"><body><h2>מה אומרים עלינו</h2>{body}<h2>תפריט</h2><ul><li>אספרסו 10</li><li>הפוך 14</li></ul></body></html>'
        ctx = {'request': self.REQ, 'canon': build_canon(self.REQ), 'rendered_pages': {'/': page, 'assets': ''}}
        return [f.problem for f in static_findings({'a.py': 'x'}, ctx) if f.severity == 'blocking' and f.probe == '_invented_contact']

    def test_verbatim_with_punctuation_and_niqqud_passes(self):
        body = ('<blockquote>“הקפה הכי טוב בחיפה!” – דנה</blockquote>'
                '<blockquote>"שֵׁירוּת חם, ומחירים הוגנים" – אבי</blockquote><p>מעל 50 ביקורות</p>')
        self.assertEqual(self.blocking(body), [])

    def test_html_entities_are_decoded(self):
        # the approved cafe writes its quotes as &ldquo;...&rdquo; (regression run 42821926825)
        body = ('<blockquote>&ldquo;הקפה הכי טוב בחיפה&rdquo; &ndash; דנה</blockquote>'
                '<blockquote>&quot;שירות חם ומחירים הוגנים&quot; – אבי</blockquote>')
        self.assertEqual(self.blocking(body), [])

    def test_paraphrase_blocks(self):
        body = '<blockquote>“הקפה הטוב ביותר בחיפה” – דנה</blockquote><blockquote>“שירות חם ומחירים הוגנים” – אבי</blockquote>'
        self.assertTrue(any('testimonials' in p for p in self.blocking(body)))

    def test_wrong_author_blocks(self):
        body = '<blockquote>“הקפה הכי טוב בחיפה” – רותי</blockquote><blockquote>“שירות חם ומחירים הוגנים” – אבי</blockquote>'
        self.assertTrue(any('testimonials' in p for p in self.blocking(body)))

    def test_invented_count_blocks_given_count_passes(self):
        given = '<blockquote>“הקפה הכי טוב בחיפה” – דנה</blockquote><blockquote>“שירות חם ומחירים הוגנים” – אבי</blockquote>'
        self.assertEqual(self.blocking(given + '<p>מעל 50 ביקורות</p>'), [])
        self.assertTrue(any('counts' in p for p in self.blocking(given + '<p>4.9 כוכבים מ-300 ביקורות</p>')))

    def test_menu_list_after_the_section_is_not_a_testimonial(self):
        given = '<blockquote>“הקפה הכי טוב בחיפה” – דנה</blockquote><blockquote>“שירות חם ומחירים הוגנים” – אבי</blockquote>'
        self.assertEqual(self.blocking(given), [])


class RegressionToolGolden(unittest.TestCase):
    """Michael 2026-11-10 item 3: the measuring tool has its own golden fixture with an EXACT fact count."""

    def test_golden_self_check(self):
        from omni_prod.gate_regression import GOLDEN_FACTS, self_check
        self.assertEqual(self_check(), GOLDEN_FACTS)

    def test_self_check_fails_on_a_wrong_count(self):
        from omni_prod import gate_regression
        saved = dict(gate_regression.GOLDEN_FACTS)
        try:
            gate_regression.GOLDEN_FACTS['phone'] = 2
            with self.assertRaises(AssertionError):
                gate_regression.self_check()
        finally:
            gate_regression.GOLDEN_FACTS.clear()
            gate_regression.GOLDEN_FACTS.update(saved)

    def test_identical_canons_for_different_prompts_are_an_error(self):
        from omni_prod.gate_regression import check_distinct
        with self.assertRaises(AssertionError):
            check_distinct([('a', 'prompt one', 'h1'), ('b', 'prompt two', 'h1')])
        check_distinct([('a', 'p1', 'h1'), ('b', 'p2', 'h2')])

    def test_zero_facts_is_truth_inert(self):
        from omni_prod.gate_regression import run
        r = run({'page.py': 'x'}, 'מערכת משימות לצוות', pages={'/': GOOD_PAGE.replace('050-1234567', ''), 'assets': ''})
        self.assertTrue(r['truth_inert'])
        self.assertFalse(run({'page.py': 'x'}, REQUEST, pages={'/': GOOD_PAGE, 'assets': ''})['truth_inert'])


class EntitiesAuthorsTypedCounts(unittest.TestCase):
    """Michael 2026-11-10 (merge conditions 1-3 for #291)."""

    REQ = ('ביקורות: "קפה & קרואסונים, הכי טוב" – דנה כהן • "שירות 5 כוכבים" – אבי • יש לנו מעל 50 ביקורות בגוגל '
           'ודירוג 4.8 • מגישים 120 מנות ביום')

    def blocking(self, body, req=None):
        from omni_prod.fact_canon import build_canon
        req = req or self.REQ
        page = f'<html lang="he" dir="rtl"><body><h2>מה אומרים עלינו</h2>{body}<h2>תפריט</h2></body></html>'
        ctx = {'request': req, 'canon': build_canon(req), 'rendered_pages': {'/': page, 'assets': ''}}
        return [f.problem for f in static_findings({'a.py': 'x'}, ctx) if f.severity == 'blocking' and f.probe == '_invented_contact']

    def test_every_entity_form_is_decoded_on_both_sides(self):
        second = '<blockquote>“שירות 5 כוכבים” – אבי</blockquote>'
        for first in ('&ldquo;קפה &amp; קרואסונים, הכי&nbsp;טוב&rdquo; – דנה כהן',
                      '&quot;קפה &#38; קרואסונים, הכי טוב&quot; – דנה כהן',
                      '&#8220;קפה &#x26; קרואסונים, הכי טוב&#8221; &#8211; דנה כהן',
                      '“קפה & קרואסונים, הכי טוב” &#39;–&#x27; דנה כהן'.replace("&#39;–&#x27;", '–')):
            self.assertEqual(self.blocking(f'<blockquote>{first}</blockquote>{second}'), [], first)
        encoded_req = self.REQ.replace('&', '&amp;').replace('"', '&quot;')
        self.assertEqual(self.blocking('<blockquote>“קפה & קרואסונים, הכי טוב” – דנה כהן</blockquote>' + second,
                                       req=encoded_req), [])

    def test_author_prefix_subset_and_city(self):
        second = '<blockquote>“שירות 5 כוכבים” – אבי</blockquote>'
        for author in ('דנה כהן', 'דנה', "דנה כ'", 'דנה, חיפה', 'דנה כהן, תל אביב'):
            body = f'<blockquote>“קפה & קרואסונים, הכי טוב” – {author}</blockquote>{second}'
            self.assertEqual(self.blocking(body), [], author)
        body = '<blockquote>“קפה & קרואסונים, הכי טוב” – דוד</blockquote>' + second
        self.assertTrue(any('testimonials' in p for p in self.blocking(body)))

    def test_counts_are_typed(self):
        from omni_prod.fact_canon import build_canon
        canon = build_canon(self.REQ)
        self.assertEqual(canon.values('reviewCount'), {'50'})
        self.assertIn('4.8', canon.values('rating'))
        self.assertEqual(self.blocking('<p>מעל 50 ביקורות, דירוג 4.8</p>'), [])
        self.assertTrue(any('counts' in p for p in self.blocking('<p>120 ביקורות</p>')))   # 120 is a dish count
        self.assertTrue(any('counts' in p for p in self.blocking('<p>50 לקוחות מרוצים</p>')))  # 50 is reviews, not customers
