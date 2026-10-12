"""A structurally valid DAG cannot authorize unavailable agents or skills."""
import dataclasses
import unittest
from decimal import Decimal
from unittest.mock import patch

from omni_prod import discovery
from omni_prod.intake.contract import from_brief
from omni_prod.planning import registry_view as R
from omni_prod.planning.architect import ChiefArchitect, web_graph
from omni_prod.planning.feasibility import CORE_CHECKS


class AssignmentGateTests(unittest.TestCase):
    def setUp(self):
        brief = discovery.start('Build a website for Test Travel', mode=discovery.RECOMMEND)
        self.contract = dataclasses.replace(from_brief(brief), unresolved_questions=[])
        tasks = web_graph(self.contract, budget_usd=Decimal('0.50')).tasks
        self.snapshot = {
            'loaded': True,
            'agents': {t.responsible_agent: {'status': 'IMPLEMENTED',
                       'allowed_skills': list(t.required_skills)} for t in tasks},
            'skills': {s: {'status': 'IMPLEMENTED'} for t in tasks for s in t.required_skills},
            'capabilities': {c: {'status': 'IMPLEMENTED'} for c in CORE_CHECKS},
            'models': [{'in_worker_catalog': True, 'availability': 'AVAILABLE',
                        'eligible_tasks': ['conversation', 'codegen', 'architecture', 'repair', 'review'],
                        'provider_model_id': 'fixture-only-no-provider-call'}],
            'gaps': {},
        }

    def plan(self, contract=None):
        with patch.object(R, 'snapshot', return_value=self.snapshot):
            return ChiefArchitect().plan(contract or self.contract)

    def test_available_assignments_can_execute(self):
        self.assertTrue(self.plan()['executable'])

    def test_unavailable_agent_blocks_plan(self):
        self.snapshot['agents']['architecture_agent']['status'] = 'NOT_IMPLEMENTED'
        plan = self.plan()
        self.assertFalse(plan['executable'])
        self.assertFalse(plan['feasibility']['buildable'])
        self.assertTrue(any('architecture_agent' in f['reason'] for f in plan['capability_gaps']))

    def test_unavailable_skill_blocks_plan(self):
        self.snapshot['skills']['data_model_design']['status'] = 'NOT_IMPLEMENTED'
        plan = self.plan()
        self.assertFalse(plan['executable'])
        task = next(a for a in plan['assignments'] if a['task_id'] == 'T03')
        self.assertFalse(task['executable'])

    def test_missing_architecture_model_blocks_plan(self):
        self.snapshot['models'][0]['eligible_tasks'].remove('architecture')
        self.assertFalse(self.plan()['executable'])

    def test_unresolved_customer_question_blocks_plan(self):
        contract = dataclasses.replace(self.contract, unresolved_questions=['contact handling is unconfirmed'])
        plan = self.plan(contract)
        self.assertFalse(plan['executable'])
        self.assertFalse(plan['feasibility']['buildable'])


if __name__ == '__main__':
    unittest.main()
