import json
import os
import threading
import unittest
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from omni_prod.autonomous_core import AutonomousProductEngine, ExecutionReport, AcceptanceFailure
from omni_prod.change_policy import ChangeAssessment
from omni_prod.model_gateway import ModelEndpoint, OpenAICompatibleGateway
from omni_prod.model_policy import ModelUsePolicy, ModelUseState, authorize_model_call, ModelPolicyViolation
from omni_prod.model_runtime_config import ModelRuntimeConfig
from omni_prod.product_spec import ProductSpec
from omni_prod.repository_patch import apply_patch, parse_patch, PatchValidationError

SPEC = {
    'title': 'Todo',
    'summary': 'Todo app',
    'stack': ['python'],
    'requirements': [
        {'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True}
    ],
    'acceptance': [
        {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}
    ],
}

class Architect:
    def create_spec(self, prompt):
        return ProductSpec.from_dict(SPEC)

class Generator:
    def generate(self, spec):
        return parse_patch({'files': [{'path': 'app.py', 'content': 'BROKEN'}]})

class Repairer:
    def repair(self, **kwargs):
        return parse_patch({'files': [{'path': 'app.py', 'content': 'WORKING'}]})

class Executor:
    def execute(self, *, repository, spec):
        if repository['app.py'] == 'WORKING':
            return ExecutionReport(True)
        return ExecutionReport(
            False,
            (AcceptanceFailure('A1', 'not working', 'app.py'),),
            'failed',
        )

class ProductSpecTests(unittest.TestCase):
    def test_mandatory_requirement_must_have_acceptance(self):
        bad = dict(SPEC)
        bad['acceptance'] = []
        with self.assertRaises(ValueError):
            ProductSpec.from_dict(bad)

class PatchTests(unittest.TestCase):
    def test_path_traversal_rejected(self):
        with self.assertRaises(PatchValidationError):
            parse_patch({'files': [{'path': '../x', 'content': 'x'}]})
    def test_patch_delete(self):
        repo = apply_patch(
            {'a': '1'},
            parse_patch({'files': [{'path': 'a', 'content': None}]}),
        )
        self.assertEqual(repo, {})

class AutonomousLoopTests(unittest.TestCase):
    def test_generate_fail_repair_pass(self):
        result = AutonomousProductEngine(
            architect=Architect(),
            generator=Generator(),
            repairer=Repairer(),
            executor=Executor(),
            max_repair_rounds=2,
        ).build('todo')
        self.assertEqual(result.status, 'ready')
        self.assertEqual(result.repair_rounds, 1)
        self.assertEqual(result.repository['app.py'], 'WORKING')

class ChangePolicyTests(unittest.TestCase):
    def test_omni_fault_is_not_billable(self):
        spec = ProductSpec.from_dict(SPEC)
        a = ChangeAssessment.from_dict(
            {'category': 'missing_requirement', 'reason': 'R1 missing', 'acceptance_ids': ['A1']},
            spec=spec,
        )
        self.assertFalse(a.billable)
    def test_user_new_feature_is_billable(self):
        spec = ProductSpec.from_dict(SPEC)
        a = ChangeAssessment.from_dict(
            {'category': 'change_request', 'reason': 'new calendar', 'acceptance_ids': []},
            spec=spec,
        )
        self.assertTrue(a.billable)
    def test_free_repair_without_contract_evidence_rejected(self):
        spec = ProductSpec.from_dict(SPEC)
        with self.assertRaises(ValueError):
            ChangeAssessment.from_dict(
                {'category': 'system_bug', 'reason': 'broken', 'acceptance_ids': []},
                spec=spec,
            )

class ModelPolicyTests(unittest.TestCase):
    def test_local_model_allowed_in_zero_cost_mode(self):
        ep = ModelEndpoint('local', 'http://127.0.0.1:1/v1', 'qwen', external=False)
        authorize_model_call(endpoint=ep, policy=ModelUsePolicy(), state=ModelUseState())
    def test_external_model_blocked_in_zero_cost_mode(self):
        ep = ModelEndpoint('remote', 'https://example.com/v1', 'x', api_key='secret', external=True)
        with self.assertRaises(ModelPolicyViolation):
            authorize_model_call(
                endpoint=ep,
                policy=ModelUsePolicy(),
                state=ModelUseState(),
                estimated_cost_usd=Decimal('0.01'),
            )
    def test_external_budget_enforced(self):
        ep = ModelEndpoint('remote', 'https://example.com/v1', 'x', api_key='secret', external=True)
        pol = ModelUsePolicy(False, True, Decimal('0.10'), 1)
        state = ModelUseState()
        authorize_model_call(
            endpoint=ep, policy=pol, state=state, estimated_cost_usd=Decimal('0.05')
        )
        with self.assertRaises(ModelPolicyViolation):
            authorize_model_call(
                endpoint=ep, policy=pol, state=state, estimated_cost_usd=Decimal('0.01')
            )

class RuntimeConfigTests(unittest.TestCase):
    def test_default_is_local_zero_cost(self):
        env = {
            'OMNI_LOCAL_MODEL_URL': 'http://127.0.0.1:9000/v1',
            'OMNI_LOCAL_MODEL_ID': 'local-coder',
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = ModelRuntimeConfig.from_env()
        self.assertFalse(cfg.primary.external)
        self.assertTrue(cfg.policy.zero_cost_mode)
        self.assertEqual(cfg.fallback, ())

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        body = json.loads(self.rfile.read(length))
        self.server.seen = body
        payload = {'choices': [{'message': {'content': '{"ok":true}'}}]}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *args):
        pass

class GatewayHTTPTests(unittest.TestCase):
    def test_real_http_openai_compatible_local_endpoint(self):
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            ep = ModelEndpoint(
                'local',
                f'http://127.0.0.1:{server.server_port}/v1',
                'local-coder',
            )
            out = OpenAICompatibleGateway(ep).complete_json(system='s', user='u')
            self.assertEqual(out, {'ok': True})
            self.assertEqual(server.seen['model'], 'local-coder')
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

if __name__ == '__main__':
    unittest.main()
