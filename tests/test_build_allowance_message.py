import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import tests.test_m5_build_economics as economics

from tests.test_m5_build_economics import DurableBuildRouteReservationTests


class BuildAllowanceMessageTests(unittest.TestCase):
    def test_plan_eligibility_is_not_reported_as_exhausted_allowance(self):
        def namespace(**kw):
            if kw.get('allowed') is False and 'reason' in kw:
                kw['reason'] = 'cost class not included in plan'
            return SimpleNamespace(**kw)
        with patch.object(economics, 'SimpleNamespace', side_effect=namespace):
            _, _, enqueue, _, exc = DurableBuildRouteReservationTests()._run(reserve_allowed=False)
        self.assertEqual(exc.status_code, 402)
        self.assertEqual(exc.detail['error'], 'plan_cannot_authorize_cost')
        self.assertIn('not included', exc.detail['message'])
        self.assertIn('Upgrade', exc.detail['message'])
        self.assertNotIn('Add credits', exc.detail['message'])
        enqueue.assert_not_called()

    def test_qa_budget_and_plan_preview_blockers_stay_distinct(self):
        from tests.test_m5_creator_workspace import PlanPreviewTests
        from omni_prod.qa_budget import QABudgetDenied
        for exception, expected in ((QABudgetDenied('QA cap reached'), 'qa_budget_denied'),
                                    (PermissionError('plan limit'), 'plan_cannot_authorize_cost')):
            def denied():
                raise exception
            _, preview = PlanPreviewTests()._preview(quote=denied)
            self.assertIn(expected, [b['code'] for b in preview['blockers']])
            self.assertFalse(preview['can_build'])
    def test_refusal_is_structured_and_does_not_expose_provider_reason(self):
        _, _, enqueue, _, exc = DurableBuildRouteReservationTests()._run(reserve_allowed=False)
        self.assertEqual(exc.status_code, 402)
        self.assertIsInstance(exc.detail, dict)
        self.assertEqual(exc.detail['error'], 'build_allowance_exhausted')
        self.assertNotIn('paid-provider', json.dumps(exc.detail))
        self.assertIn('budget or credits', exc.detail['message'])
        enqueue.assert_not_called()

    # pg-tests has no node: a skip there is honest; the test runs wherever node exists (test, customer-ui jobs).
    @unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js explain()')
    def test_real_ui_explains_allowance_in_hebrew_and_english(self):
        source = (Path(__file__).resolve().parents[1] / 'omni_prod/assets/app.js').read_text()
        translations = source[source.index('const T ='):source.index('const S =')]
        explain = re.search(r'function explain\(err\) \{.*?\n\}', source, re.S).group()
        error = re.search(r'class ApiError extends Error \{.*?\n\}', source, re.S).group()
        js = translations + '\nconst S={lang:"he",signedIn:true};\nfunction t(k){return T[S.lang][k];}\n' + error + '\n' + explain
        js += '\nconst e=new ApiError(402,{error:"build_allowance_exhausted",message:"INTERNAL_SENTINEL"}); console.log(JSON.stringify([explain(e),(S.lang="en",explain(e))]));'
        p = subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True)
        he, en = json.loads(p.stdout)
        self.assertIn('נגמר התקציב או הקרדיטים', he)
        self.assertIn('budget or credits', en)
        for message in (he, en):
            self.assertNotIn('paid-provider', message)
            self.assertNotIn('INTERNAL_SENTINEL', message)
        js += '\nS.lang="he";const plan=new ApiError(402,{error:"plan_cannot_authorize_cost"}); console.log(JSON.stringify([explain(plan),(S.lang="en",explain(plan))]));'
        p = subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True)
        he, en = json.loads(p.stdout.splitlines()[-1])
        self.assertIn('לא כלולה במסלול', he)
        self.assertIn('לשדרג', he)
        self.assertIn('not included', en)
        self.assertIn('Upgrade', en)

    def test_the_approval_route_refuses_with_the_same_code_as_the_build_route(self):
        """One code for one meaning: POST .../approvals used plan_cannot_authorize_build, which explain() did not
        know, so a customer refused at approval saw the generic 402 prefix."""
        try:
            from omni_prod import investor_app as IA
        except ImportError as exc:                                         # v24-ci has fastapi
            raise unittest.SkipTest(f'fastapi not installed here ({exc})')
        from fastapi import HTTPException
        from omni_prod.pricing import PLAN_CATALOG, PlanCode
        row = SimpleNamespace(fingerprint='f' * 64)
        contract = SimpleNamespace(id='bc_1', prompt='Approved brief ' + 'f' * 16, contract_fingerprint='sha256:x')

        def denied(*a, **kw):
            raise PermissionError('zero/unknown revenue plan cannot authorize paid variable build cost')
        with patch.object(IA, '_discovery_account', lambda request, pid: SimpleNamespace(id='u1')), \
                patch.object(IA, '_brief_prompt', lambda pid, rev: ('prompt', row)), \
                patch.object(IA, '_bind_execution_plan', lambda pid, fp: None), \
                patch.object(IA, 'PostgresBuildContractRepository', lambda pool: SimpleNamespace(get=lambda *a, **kw: contract)), \
                patch.object(IA._v28.subscriptions, 'plan_for', lambda uid: PLAN_CATALOG[PlanCode.FREE]), \
                patch.object(IA, '_internal_qa_funding', lambda aid: (None, False)), \
                patch.object(IA, '_m5_cost_inputs', lambda *a, **kw: ()), \
                patch.object(IA, '_m5_build_economics_quote', denied):
            with self.assertRaises(HTTPException) as caught:
                IA.v28_build_approval('p', SimpleNamespace(build_contract_id='bc_1', brief_revision=1), request=None)
        self.assertEqual(caught.exception.status_code, 402)
        self.assertEqual(caught.exception.detail['error'], 'plan_cannot_authorize_cost')
        self.assertIn('Upgrade', caught.exception.detail['message'])
        self.assertNotIn('revenue', json.dumps(caught.exception.detail))

    def test_no_route_emits_the_retired_code(self):
        source = (Path(__file__).resolve().parents[1] / 'omni_prod/investor_app.py').read_text()
        self.assertNotIn('plan_cannot_authorize_build', source)

    def test_the_explain_strings_live_in_t(self):
        source = (Path(__file__).resolve().parents[1] / 'omni_prod/assets/app.js').read_text()
        explain = re.search(r'function explain\(err\) \{.*?\n\}', source, re.S).group()
        self.assertIn("t('errPlanNotIncluded')", explain)
        self.assertIn("t('errAllowanceExhausted')", explain)
        self.assertNotIn('לשדרג', explain)
        self.assertEqual(source.count('errPlanNotIncluded:'), 2)
        self.assertEqual(source.count('errAllowanceExhausted:'), 2)
