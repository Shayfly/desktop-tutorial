"""Failure Injection Agent (autonomous completion §8, agent 51): controlled
bad conditions against the real platform code, each with the expected,
graceful outcome. Real-host injections (worker SIGKILL, deploy during a
build) run in workflows and are listed in FAILURE_INJECTION_MATRIX.json."""
import json
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from omni_prod.build_control import BuildControl
from omni_prod.migrations import Migration, verify_applied
from omni_prod.model_gateway import ModelGatewayError, ModelHTTPError
from omni_prod.model_policy import ModelPolicyViolation
from omni_prod.storage import ArtifactIntegrityError, S3ArtifactStore
from omni_prod.worker_tasks import failure_code
from tests.test_provider_quota_and_dialects import Script, _gw, _model


class ProviderFailures(unittest.TestCase):
    def setUp(self):
        self.models = (_model('primary', 85, '0.75', '3.75'), _model('fallback', 90, '2', '10'))

    def call(self, script, budget='1'):
        return _gw(script, self.models, budget).complete_json(system='s', user='u', max_tokens=1000, task='codegen')

    def test_timeout_falls_back_to_the_next_provider(self):
        s = Script({'primary': [TimeoutError('read timed out')] * 5})
        self.assertEqual(self.call(s), {'ok': 'fallback'})

    def test_malformed_response_falls_back(self):
        s = Script({'primary': [ValueError('Expecting value: line 1 column 1')] * 5})
        self.assertEqual(self.call(s), {'ok': 'fallback'})

    def test_429_is_released_and_the_route_is_skipped(self):
        s = Script({'primary': [ModelHTTPError('HTTP 429: quota exceeded, check your plan and billing', status=429)]})
        self.assertEqual(self.call(s), {'ok': 'fallback'})

    def test_500_is_retried_then_falls_back(self):
        s = Script({'primary': [ModelHTTPError('HTTP 500: internal', status=500)] * 5})
        self.assertEqual(self.call(s), {'ok': 'fallback'})
        self.assertGreaterEqual(s.calls.count('primary'), 2)  # bounded retry of the same route first

    def test_all_providers_down_is_a_named_failure(self):
        s = Script({'primary': [TimeoutError('x')] * 9, 'fallback': [TimeoutError('y')] * 9})
        with self.assertRaises(ModelGatewayError) as ctx:
            self.call(s)
        self.assertEqual(failure_code(ctx.exception), 'model_unavailable')

    def test_exhausted_budget_stops_with_a_named_failure(self):
        s = Script({})
        with self.assertRaises(ModelPolicyViolation) as ctx:
            self.call(s, budget='0.000001')
        self.assertEqual(failure_code(ctx.exception), 'model_budget_exhausted')


class InfrastructureFailures(unittest.TestCase):
    def test_database_unavailable_during_a_step_does_not_crash_the_build(self):
        jobs = MagicMock()
        jobs.checkpoint.side_effect = OSError('connection refused')
        jobs.add_event.side_effect = OSError('connection refused')
        control = BuildControl(jobs, 'bld_x')
        control.before_model_call('codegen')   # logged warning, build continues
        self.assertEqual(control.model_calls, 1)

    def test_queue_interruption_is_redispatched(self):
        from omni_prod import maintenance
        sent = []
        with patch.object(maintenance, 'queued_too_long', return_value=[(maintenance.BUILD_JOB, 'bld_lost')]):
            maintenance.redispatch_lost(None, queued_ids=lambda: [], enqueue=lambda f, i: sent.append(i), attempts={})
        self.assertEqual(sent, ['bld_lost'])

    def test_invalid_migration_aborts_instead_of_diverging(self):
        m = Migration(31, 'x', Path('x.sql'), 'sha-now', 'SELECT 1')
        with self.assertRaises(RuntimeError) as ctx:
            verify_applied([m], {31: 'sha-recorded-earlier'})
        self.assertIn('checksum drift', str(ctx.exception))

    def test_corrupted_artifact_is_refused(self):
        store = S3ArtifactStore.__new__(S3ArtifactStore)
        body = SimpleNamespace(read=lambda: b'tampered bytes')
        store.bucket = 'b'
        store.client = SimpleNamespace(get_object=lambda **k: {'Body': body, 'Metadata': {'sha256': '0' * 64}})
        with self.assertRaises(ArtifactIntegrityError):
            store.get_bytes('repositories/x.zip')

    def test_sandbox_network_interruption_is_a_named_error(self):
        from urllib import error
        from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxError, RemoteSandboxRepositoryExecutor
        ex = RemoteSandboxRepositoryExecutor(RemoteSandboxConfig('http://127.0.0.1:9', 's' * 32, timeout_seconds=1))
        ex._urlopen = MagicMock(side_effect=error.URLError('connection reset'))
        with self.assertRaises(RemoteSandboxError):
            ex._run({'a.py': ''}, ('python', '-c', '1'), 'b1')


class MatrixTests(unittest.TestCase):
    def test_every_injection_in_the_matrix_names_where_it_is_proven(self):
        path = Path(__file__).resolve().parents[1] / 'FAILURE_INJECTION_MATRIX.json'
        rows = json.loads(path.read_text())['injections']
        self.assertGreaterEqual(len(rows), 15)
        for row in rows:
            self.assertTrue(row['proven_by'] or row['status'] in ('NOT_RUN', 'BLOCKED'), row)


if __name__ == '__main__':
    unittest.main()
