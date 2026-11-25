"""Pin the versioned scope guidance at the call boundary of both alternate repair routes."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from omni_prod.autonomous_agents import RepairAgent
from omni_prod.worker_tasks import _install_agentic_repair
from tests.test_j1_real_agent_feature_flag import FakeGateway, FakeSpec, structured_reply, summary


class RepairRequestFidelityRoutes(unittest.TestCase):
    def assert_scope_guidance(self, prompt):
        self.assertIn('skill.request_fidelity@2', prompt)
        self.assertIn('Preserve confirmed requirements, exclusions and acceptance ids', prompt)
        self.assertIn('business facts, prices and testimonials need approved sources', prompt)

    def test_founder_worker_agentic_repair_sends_versioned_scope(self):
        gateway = FakeGateway({'action': 'submit', 'files': [{'path': 'app.py', 'content': 'x = 2\n'}]})
        engine = SimpleNamespace(repairer=RepairAgent(gateway))
        with patch.dict(os.environ, {'OMNI_AGENTIC_REPAIR': 'founder', 'OMNI_FOUNDER_ACCOUNT_IDS': 'fixture_founder'}):
            self.assertTrue(_install_agentic_repair(engine, {'user_id': 'fixture_founder'}))
            edits = engine.repairer.repair(spec=FakeSpec(), repo_summary={'_repository': {'app.py': 'x = 1\n'}},
                                           failures=[{'acceptance_id': 'A1', 'message': 'incorrect value'}])
        self.assertEqual([p.path for p in edits], ['app.py'])
        self.assertEqual(len(gateway.calls), 1)
        self.assert_scope_guidance(gateway.calls[0]['system'])

    def test_structured_repair_sends_versioned_scope_and_keeps_its_constraints(self):
        gateway = FakeGateway(structured_reply([{'path': 'src/site.py', 'operation': 'UPSERT', 'content': 'fixed'}]))
        with patch.dict(os.environ, {'OMNI_REPAIR_STRUCTURED_V1': '1'}):
            edits = RepairAgent(gateway).repair(spec=FakeSpec(), repo_summary=summary(), failures=[])
        self.assertEqual([p.path for p in edits], ['src/site.py'])
        self.assertEqual(len(gateway.calls), 1)
        prompt = gateway.calls[0]['system']
        self.assertIn('Never change tests, acceptance policy, secrets, manifests or lockfiles', prompt)
        self.assert_scope_guidance(prompt)
