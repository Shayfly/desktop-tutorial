"""Web skills that shape the build and the QA Verifier that enforces them
(Agent OS spec 2026-10-08; defects from the founder's task-list product)."""
import unittest
from decimal import Decimal

from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.product_review import REVIEW_FAILURE_ID, ProductReviewExecutor
from omni_prod.product_spec import ProductSpec
from omni_prod.skills_runtime import (WEB_SKILLS, applied_skills, checklist_for_review, guidance_for,
                                      static_findings)

CLEAN = {
    'app.py': 'import sqlite3\ncur.execute("INSERT INTO tasks (title) VALUES (?)", (title,))\n',
    'index.html': ('<html lang="he" dir="rtl"><head><style>:root{--primary:#0f766e;--bg:#f6f7f9;--radius:12px}'
                   + 'body{margin:0;padding:0;color:#1f2937;background:var(--bg);font-family:Assistant,system-ui;}' * 8
                   + '@media (max-width:640px){main{padding:12px;}}</style></head>'
                   '<body><form><input></form><script>el.textContent = t.title;</script></body></html>'),
}


def _spec():
    return ProductSpec.from_dict({'title': 'משימות', 'summary': 'ניהול משימות', 'stack': ['python'],
                                  'requirements': [{'id': 'R1', 'text': 'הוספת משימה'}],
                                  'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'POST /tasks'}]})


class VisualDesignTests(unittest.TestCase):
    """Founder 2026-10-09: generated sites had no colour or design."""

    def test_unstyled_page_is_a_blocking_finding(self):
        repo = {'index.html': '<html lang="he" dir="rtl"><body><form><input><button>הוסף</button></form></body></html>'}
        found = [f for f in static_findings(repo, {'request': 'אתר'}) if f.skill == 'skill.visual_design']
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, 'blocking')
        self.assertIn('browser default look', found[0].problem)

    def test_design_system_passes(self):
        self.assertEqual([f for f in static_findings(CLEAN, {'request': 'אתר'}) if f.skill == 'skill.visual_design'], [])

    def test_generator_and_reviewer_receive_the_design_skill(self):
        self.assertIn('skill.visual_design@1', guidance_for('generator'))
        self.assertIn('Visual design', guidance_for('repair'))
        self.assertTrue(any(c['skill'] == 'skill.visual_design' for c in checklist_for_review()))


class StaticChecks(unittest.TestCase):
    def test_clean_repository_has_no_findings(self):
        self.assertEqual(static_findings(CLEAN, {'request': 'אתר משימות'}), [])

    def test_founder_defects_are_found(self):
        repo = {
            'app.py': 'import html\nconn.execute("INSERT INTO tasks (title) VALUES (?)", (html.escape(t),))\n'
                      'PAGE = """<html><body><script>alert(\'תאריך לא תקין\'); tr.innerHTML = `<td>${t.title}</td>`;</script></body></html>"""\n',
            'tests/test_app.py': 'alert(',  # tests are not product code
        }
        found = {(f.skill, f.severity, f.problem.split(' ')[0]) for f in static_findings(repo, {'request': 'אתר בעברית'})}
        self.assertIn(('skill.form_validation', 'blocking', 'uses'), found)          # alert()
        self.assertIn(('skill.text_locale', 'blocking', 'escapes'), found)          # html.escape before INSERT
        self.assertIn(('skill.text_locale', 'blocking', 'Hebrew'), found)           # no dir="rtl"
        self.assertIn(('skill.text_locale', 'advisory', 'builds'), found)           # innerHTML ${}
        self.assertFalse(any(f.file.startswith('tests/') for f in static_findings(repo, {})))

    def test_rtl_only_required_for_hebrew_requests(self):
        repo = {'index.html': '<html><body><button>Add</button></body></html>'}
        rtl = [f for f in static_findings(repo, {'request': 'a todo site'}) if 'rtl' in f.problem.lower()]
        self.assertEqual(rtl, [])
        self.assertTrue([f for f in static_findings(repo, {'request': 'אתר משימות'}) if 'rtl' in f.problem.lower()])


class Guidance(unittest.TestCase):
    def test_agents_receive_their_skills(self):
        from omni_prod.autonomous_agents import _ARCHITECT_SYSTEM, _GENERATOR_SYSTEM, _REPAIR_SYSTEM
        from omni_prod.product_evolution import _EVOLUTION_SYSTEM
        self.assertIn('skill.request_fidelity@1', _ARCHITECT_SYSTEM)
        for prompt in (_GENERATOR_SYSTEM, _REPAIR_SYSTEM, _EVOLUTION_SYSTEM):
            self.assertIn('skill.form_validation@1', prompt)
            self.assertIn('never with alert()', prompt)
        # "without login" must not be overridden by a mandatory auth kind.
        self.assertIn('auth and role only when the product has sign-in or roles', _GENERATOR_SYSTEM)
        self.assertNotIn('covering auth, role, data_create', _GENERATOR_SYSTEM)

    def test_skill_contract_fields(self):
        for s in WEB_SKILLS:
            self.assertTrue(s.purpose and s.boundaries and s.roles and s.guidance and s.checklist and s.version)
        self.assertEqual(len(applied_skills()), len(WEB_SKILLS))
        self.assertTrue(all(c['checks'] for c in checklist_for_review()))
        self.assertEqual(guidance_for('nobody'), '')


class _Inner:
    def __init__(self, passed=True):
        self.passed = passed

    def execute(self, *, repository, spec):
        return ExecutionReport(self.passed, () if self.passed else (AcceptanceFailure('A1', 'x'),), 'log')


class _Reviewer:
    accepts_task_tag = True

    def __init__(self, findings=None, error=None):
        self.findings, self.error, self.calls = findings or [], error, []
        self.last_usage = None

    def complete_json(self, **kw):
        self.calls.append(kw.get('task'))
        if self.error:
            raise self.error
        return {'findings': self.findings}


BAD = {'index.html': '<html dir="rtl"><script>alert("x")</script></html>'}


class ReviewExecutor(unittest.TestCase):
    def test_failing_tests_are_not_reviewed(self):
        r = _Reviewer()
        ex = ProductReviewExecutor(_Inner(False), gateway=r)
        self.assertFalse(ex.execute(repository=BAD, spec=_spec()).passed)
        self.assertEqual((r.calls, ex.reviews), ([], []))

    def test_blocking_findings_go_to_repair_then_become_advisory(self):
        r = _Reviewer([{'skill': 'skill.ui_states', 'severity': 'blocking', 'file': 'app.py',
                        'problem': 'new task hidden by active filter', 'fix': 'clear the filter after add'}])
        ex = ProductReviewExecutor(_Inner(), gateway=r, max_reviews=2)
        first = ex.execute(repository=BAD, spec=_spec())
        self.assertFalse(first.passed)
        self.assertEqual({f.acceptance_id for f in first.failures}, {REVIEW_FAILURE_ID})
        self.assertTrue(any('filter' in f.message for f in first.failures))
        self.assertTrue(any('fix: clear the filter' in f.evidence for f in first.failures))
        self.assertEqual(r.calls, ['review'])
        ex.execute(repository=BAD, spec=_spec())
        third = ex.execute(repository=BAD, spec=_spec())  # cap reached: never stuck in review
        self.assertTrue(third.passed)
        self.assertEqual([x['enforced'] for x in ex.reviews], [True, True, False])
        self.assertEqual(ex.reviews[-1]['skills'], applied_skills())

    def test_advisory_only_passes_and_is_recorded(self):
        r = _Reviewer([{'skill': 'spec', 'severity': 'advisory', 'problem': 'README is short', 'fix': 'add usage'}])
        ex = ProductReviewExecutor(_Inner(), gateway=r)
        self.assertTrue(ex.execute(repository=CLEAN, spec=_spec()).passed)
        self.assertEqual(ex.reviews[0]['findings'][0]['source'], 'reviewer')

    def test_reviewer_outage_is_recorded_not_invented(self):
        ex = ProductReviewExecutor(_Inner(), gateway=_Reviewer(error=RuntimeError('all model routes failed')))
        self.assertTrue(ex.execute(repository=CLEAN, spec=_spec()).passed)
        self.assertEqual(ex.reviews[0]['reviewer'], 'unavailable')
        self.assertEqual(ex.reviews[0]['findings'], [])


class ReviewerRouting(unittest.TestCase):
    def test_reviewer_prefers_a_model_that_did_not_write_the_code(self):
        from omni_prod.model_catalog import CatalogModel
        from omni_prod.model_gateway import ModelEndpoint
        from omni_prod.model_policy import ModelUsePolicy
        from omni_prod.model_router import ModelOption, RoutingPolicy
        from omni_prod.routed_gateway import RoutedModelGateway

        def m(name, q, price):
            return CatalogModel(endpoint=ModelEndpoint(name=name, base_url='https://x.invalid', model=name, api_key='k', external=True),
                                option=ModelOption('p', name, q, 1000, Decimal(price), Decimal(price)), max_output_tokens=4000, api_key_env='K')
        gw = RoutedModelGateway(ranked=(m('cheap-strong', 90, '1'), m('dear-strong', 90, '5')),
                                routing_policy=RoutingPolicy(minimum_quality=0, prefer_cost=True),
                                policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                      external_budget_usd=Decimal('10'), max_external_calls_per_build=10))
        kw = {'system': 's', 'user': 'u', 'max_tokens': 100}
        self.assertEqual([r.endpoint.name for r, _, _ in gw.ranked_routes(kw, 'review')][0], 'cheap-strong')
        gw.models_by_task['codegen'] = {'cheap-strong'}
        self.assertEqual([r.endpoint.name for r, _, _ in gw.ranked_routes(kw, 'review')][0], 'dear-strong')
        self.assertEqual([r.endpoint.name for r, _, _ in gw.ranked_routes(kw, 'codegen')][0], 'cheap-strong')


if __name__ == '__main__':
    unittest.main()
