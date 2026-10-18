"""Discovery/approval HTTP endpoints (directive 2026-10-09 §4-5). Needs
fastapi (CI); the repository itself is tested on real Postgres in
test_discovery_and_approval."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from omni_prod import discovery as d
from omni_prod.brief_repository import BriefRow, StaleBrief

try:
    from omni_prod import investor_app
except ModuleNotFoundError as exc:  # fastapi missing outside CI
    investor_app = None
    _WHY = str(exc)


class _MemRepo:
    def __init__(self):
        self.rows = []

    def latest(self, project_id, cur=None):
        return self.rows[-1] if self.rows else None

    def save(self, *, project_id, account_id, brief, expected_revision, request_key=None):
        if request_key:
            for r in self.rows:
                if getattr(r, 'key', None) == request_key:
                    return r
        current = self.rows[-1].revision if self.rows else 0
        if current != expected_revision:
            raise StaleBrief('stale')
        row = BriefRow(f'brf_{current + 1}', project_id, current + 1, brief, d.complete(brief), brief.fingerprint())
        object.__setattr__(row, 'key', request_key)
        self.rows.append(row)
        return row


@unittest.skipIf(investor_app is None, 'needs fastapi')
class DiscoveryEndpointTests(unittest.TestCase):
    def setUp(self):
        self.repo = _MemRepo()
        v28 = MagicMock()
        v28.resolve_project_key.return_value = (SimpleNamespace(id='usr_1'), 'tenant')
        # plan_for must return a real plan: build terms are derived from its code.
        from omni_prod.pricing import PLAN_CATALOG, PlanCode
        v28.subscriptions.plan_for.return_value = PLAN_CATALOG[PlanCode.PRO]
        self.patches = [patch.object(investor_app, '_v28', v28), patch.object(investor_app, '_v28_bearer', return_value='tok'),
                        patch.object(investor_app, '_brief_repo', return_value=self.repo)]
        for p in self.patches:
            p.start()
        self.req = MagicMock()
        self.req.query_params = {}

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_start_answer_and_stale_tab(self):
        view = investor_app.v28_discovery_start('prj_1', investor_app.V28DiscoveryStart(
            prompt='מערכת לניהול משימות לצוות בעברית'), self.req)
        self.assertEqual(view['brief']['revision'], 1)
        self.assertEqual(view['group'], 'purpose')
        self.assertTrue(all('why' in q for q in view['questions']))
        view = investor_app.v28_discovery_answer('prj_1', investor_app.V28DiscoveryAnswers(
            revision=1, answers={'audience': 'internal', 'goal': 'לנהל משימות'}), self.req)
        self.assertEqual(view['brief']['revision'], 2)
        with self.assertRaises(investor_app.HTTPException) as ctx:  # an old tab answering revision 1
            investor_app.v28_discovery_answer('prj_1', investor_app.V28DiscoveryAnswers(
                revision=1, answers={'color': 'green'}), self.req)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail['error'], 'brief_stale')

    def test_invalid_answer_is_422_and_recommend_mode_completes_with_summary(self):
        investor_app.v28_discovery_start('prj_1', investor_app.V28DiscoveryStart(prompt='מערכת לניהול משימות לצוות'), self.req)
        with self.assertRaises(investor_app.HTTPException) as ctx:
            investor_app.v28_discovery_answer('prj_1', investor_app.V28DiscoveryAnswers(revision=1, answers={'style': 'x'}), self.req)
        self.assertEqual(ctx.exception.status_code, 422)
        view = investor_app.v28_discovery_start('prj_1', investor_app.V28DiscoveryStart(
            prompt='מערכת לניהול משימות לצוות', mode='recommend'), self.req)
        self.assertTrue(view['complete'])
        self.assertTrue(view['summary']['assumptions'])

    def test_plan_from_a_stale_or_open_brief_is_refused(self):
        investor_app.v28_discovery_start('prj_1', investor_app.V28DiscoveryStart(prompt='מערכת לניהול משימות לצוות'), self.req)
        for revision, code in ((1, 'brief_incomplete'), (7, 'brief_stale')):
            with self.assertRaises(investor_app.HTTPException) as ctx:
                investor_app._brief_prompt('prj_1', revision)
            self.assertEqual(ctx.exception.detail['error'], code)

    def test_complete_brief_prompt_carries_the_fingerprint(self):
        investor_app.v28_discovery_start('prj_1', investor_app.V28DiscoveryStart(
            prompt='מערכת משימות בלי התחברות', mode='recommend'), self.req)
        prompt, row = investor_app._brief_prompt('prj_1', 1)
        self.assertIn(row.fingerprint[:16], prompt)
        self.assertIn('Sign-in: NONE', prompt)

    def test_quote_exposes_the_same_capability_block_as_build_admission(self):
        preview={'can_build':True,'blockers':[]}
        error=investor_app.HTTPException(409,detail={'error':'capability_not_feasible','findings':[{'item':'sign-in (roles)','outcome':'BLOCKED'}]})
        with patch.object(investor_app,'_bind_execution_plan',side_effect=error):
            investor_app._apply_execution_plan_gate(preview,'prj_1',SimpleNamespace(fingerprint='fp'))
        self.assertFalse(preview['can_build'])
        self.assertEqual(preview['blockers'][0]['code'],'capability_not_feasible')
        self.assertEqual(preview['blockers'][0]['findings'][0]['item'],'sign-in (roles)')

    def test_execution_gate_does_not_turn_server_errors_into_customer_blockers(self):
        with patch.object(investor_app,'_bind_execution_plan',side_effect=investor_app.HTTPException(503,'storage')):
            with self.assertRaises(investor_app.HTTPException) as ctx:
                investor_app._apply_execution_plan_gate({'can_build':True,'blockers':[]},'prj_1',SimpleNamespace(fingerprint='fp'))
        self.assertEqual(ctx.exception.status_code,503)

    def test_real_quote_endpoint_blocks_unsupported_execution_before_approval(self):
        investor_app.v28_discovery_start('prj_1',investor_app.V28DiscoveryStart(prompt='מערכת משימות',mode='recommend'),self.req)
        error=investor_app.HTTPException(409,detail={'error':'capability_not_feasible','findings':[{'item':'sign-in (roles)','outcome':'BLOCKED'}]})
        with patch.object(investor_app,'_bind_execution_plan',side_effect=error), \
             patch.object(investor_app,'_internal_qa_funding',return_value=(None,False)), \
             patch.object(investor_app,'build_plan_preview',return_value={'can_build':True,'blockers':[]}):
            view=investor_app.v28_build_contract_preview('prj_1',investor_app.V28PlanRequest(prompt='מערכת משימות',brief_revision=1),self.req)
        self.assertFalse(view['can_build'])
        self.assertEqual(view['blockers'][0]['code'],'capability_not_feasible')


if __name__ == '__main__':
    unittest.main()
