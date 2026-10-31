import json
from pathlib import Path
import re
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
