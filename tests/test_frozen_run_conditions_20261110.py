"""Michael 2026-11-10: conditions 1-5 that must be green before the frozen run's baseline SHA is handed over."""
import inspect
import json
import unittest

from omni_prod import product_review
from omni_prod.fact_canon import parse_phone
from omni_prod.probe_manifest import NOT_YET_PROBED, PROBES, critical_probes, is_critical
from omni_prod.skills_runtime import WEB_SKILLS, static_findings

from test_gate_mutations_20261110 import GOOD_PAGE, REQUEST


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
