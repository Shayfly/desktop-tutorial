import json
import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient

from omni_prod.benchmark_suite import CASES
from omni_prod.demo_project import demo_spec, create_demo_repository, StaticDemoVerifier
from omni_prod.investor_app import app
from omni_prod.model_gateway import ModelEndpoint, ModelGatewayError
from omni_prod.model_policy import ModelUsePolicy, ModelUseState, ModelPolicyViolation
from omni_prod.routed_gateway import ProviderRoute, RoutedModelGateway


class FakeGateway:
    calls = []
    def __init__(self, endpoint):
        self.endpoint = endpoint
    def complete_json(self, **kwargs):
        FakeGateway.calls.append(self.endpoint.name)
        if self.endpoint.name == 'broken-local':
            raise ModelGatewayError('down')
        return {'provider': self.endpoint.name}
    def complete(self, **kwargs):
        FakeGateway.calls.append(self.endpoint.name)
        if self.endpoint.name == 'broken-local':
            raise ModelGatewayError('down')
        return self.endpoint.name


class RoutedGatewayTests(unittest.TestCase):
    def setUp(self):
        FakeGateway.calls = []

    def test_local_primary_used_first(self):
        local = ModelEndpoint('local', 'http://local/v1', 'qwen')
        remote = ModelEndpoint('remote', 'https://remote/v1', 'x', api_key='secret', external=True)
        gw = RoutedModelGateway(
            primary=ProviderRoute(local),
            fallback=(ProviderRoute(remote, Decimal('0.02')),),
            policy=ModelUsePolicy(False, True, Decimal('0.10'), 2),
            gateway_factory=FakeGateway,
        )
        self.assertEqual(gw.complete_json(system='s', user='u'), {'provider': 'local'})
        self.assertEqual(FakeGateway.calls, ['local'])

    def test_external_fallback_blocked_by_zero_cost_mode(self):
        local = ModelEndpoint('broken-local', 'http://local/v1', 'qwen')
        remote = ModelEndpoint('remote', 'https://remote/v1', 'x', api_key='secret', external=True)
        gw = RoutedModelGateway(
            primary=ProviderRoute(local),
            fallback=(ProviderRoute(remote, Decimal('0.02')),),
            policy=ModelUsePolicy(),
            gateway_factory=FakeGateway,
        )
        with self.assertRaises(ModelPolicyViolation):
            gw.complete_json(system='s', user='u')
        self.assertEqual(FakeGateway.calls, ['broken-local'])

    def test_external_fallback_within_budget(self):
        local = ModelEndpoint('broken-local', 'http://local/v1', 'qwen')
        remote = ModelEndpoint('remote', 'https://remote/v1', 'x', api_key='secret', external=True)
        state = ModelUseState()
        gw = RoutedModelGateway(
            primary=ProviderRoute(local),
            fallback=(ProviderRoute(remote, Decimal('0.03')),),
            policy=ModelUsePolicy(False, True, Decimal('0.05'), 1),
            state=state,
            gateway_factory=FakeGateway,
        )
        self.assertEqual(gw.complete_json(system='s', user='u'), {'provider': 'remote'})
        self.assertEqual(state.external_calls, 1)
        self.assertEqual(state.external_spend_usd, Decimal('0.03'))


class DemoProjectTests(unittest.TestCase):
    def test_demo_repo_is_traceable_and_verifies(self):
        prompt = 'Build a CRM with customers and jobs'
        spec = demo_spec(prompt)
        repo = create_demo_repository(prompt, spec)
        self.assertIn('.omni/project.json', repo)
        self.assertEqual(json.loads(repo['request.json'])['prompt'], prompt)
        report = StaticDemoVerifier().execute(repository=repo, spec=spec)
        self.assertTrue(report.passed)

    def test_empty_prompt_rejected(self):
        with self.assertRaises(ValueError):
            demo_spec('   ')


class BenchmarkCatalogTests(unittest.TestCase):
    def test_catalog_is_broad_and_unique(self):
        self.assertGreaterEqual(len(CASES), 30)
        self.assertEqual(len({x.id for x in CASES}), len(CASES))
        self.assertGreaterEqual(len({x.category for x in CASES}), 10)


class InvestorAppTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_home_renders(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Omni Creator', r.text)

    def test_status_truthfully_exposes_readiness(self):
        with patch.dict(os.environ, {}, clear=True):
            r = self.client.get('/api/status')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['version'], 'V23 Investor-Grade Prelaunch')
        self.assertIn('live_ready', data['readiness'])
        self.assertEqual(data['benchmark_catalog_cases'], len(CASES))

    def test_offline_demo_build(self):
        r = self.client.post('/api/demo/build', json={'prompt':'Build a booking app for technicians'})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['mode'], 'offline-deterministic-demo')
        self.assertEqual(data['status'], 'ready')
        self.assertTrue(data['verification']['passed'])
        self.assertGreaterEqual(data['repository']['file_count'], 5)

    def test_live_build_is_fail_closed_when_disabled(self):
        with patch.dict(os.environ, {'OMNI_ENABLE_LIVE_BUILD':'0'}, clear=True):
            r = self.client.post('/api/live/build', json={'prompt':'Build a CRM'})
        self.assertEqual(r.status_code, 503)
        self.assertIn('OMNI_ENABLE_LIVE_BUILD', r.json()['detail'])


if __name__ == '__main__':
    unittest.main()
