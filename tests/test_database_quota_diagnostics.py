"""Quota is a provider refusal, not a generic unreachable database."""
from contextlib import contextmanager
from unittest.mock import patch
import unittest

from psycopg import OperationalError
from psycopg_pool import PoolTimeout
from omni_prod.db import DatabasePool
from omni_prod.schema_manifest import database_failure


QUOTA = 'Your account or project has exceeded the quota. Upgrade your plan to increase limits.'


class DatabaseFailureTests(unittest.TestCase):
    def test_quota_and_timeout_are_different_and_secret_safe(self):
        quota = database_failure(OperationalError(QUOTA + ' postgresql://user:private@host/db'))
        self.assertEqual(quota['status'], 'QUOTA_EXCEEDED')
        self.assertEqual(quota['error_code'], 'DATABASE_QUOTA_EXCEEDED')
        self.assertEqual(quota['provider_status'], 402)
        self.assertNotIn('private', str(quota))
        timeout = database_failure(PoolTimeout('could not get connection'))
        self.assertEqual(timeout['status'], 'UNREACHABLE')
        self.assertEqual(timeout['error'], 'PoolTimeout')
        self.assertNotIn('provider_status', timeout)

    def test_http_402_and_chained_driver_quota(self):
        err = RuntimeError('provider refusal')
        err.status_code = 402
        self.assertEqual(database_failure(err)['status'], 'QUOTA_EXCEEDED')
        outer = PoolTimeout('pool exhausted')
        outer.__cause__ = OperationalError(QUOTA)
        self.assertEqual(database_failure(outer)['status'], 'QUOTA_EXCEEDED')

    def test_unknown_and_non_quota_operational_errors_remain_unreachable(self):
        for err in (OperationalError('connection refused'), OperationalError('remaining connection slots exhausted'),
                    RuntimeError('payment advice is not an HTTP error'), RuntimeError('quota is mentioned without refusal')):
            with self.subTest(err=err):
                self.assertEqual(database_failure(err)['status'], 'UNREACHABLE')


class SchemaQuotaTests(unittest.TestCase):
    def setUp(self):
        from omni_prod import investor_app
        self.app = investor_app
        self.previous = investor_app._v28_pool
        self.pool = DatabasePool('postgresql://synthetic:secret@host/db')
        class TimedOutDriver:
            @contextmanager
            def connection(self, **kwargs):
                raise PoolTimeout('pool timed out')
                yield
        self.pool._pool = TimedOutDriver()
        self.app._v28_pool = self.pool

    def tearDown(self):
        self.app._v28_pool = self.previous

    def test_pool_timeout_probes_once_and_surfaces_provider_quota(self):
        with patch('omni_prod.db.connect', side_effect=OperationalError(QUOTA)) as probe:
            out = self.app._schema_compatibility()
        self.assertEqual(out['status'], 'QUOTA_EXCEEDED')
        self.assertFalse(out['compatible'])
        self.assertEqual(out['provider_status'], 402)
        self.assertNotIn('secret', str(out))
        probe.assert_called_once_with(self.pool.database_url, connect_timeout_seconds=2)

    def test_failed_probe_without_quota_keeps_original_timeout(self):
        with patch('omni_prod.db.connect', side_effect=OperationalError('network unavailable')):
            out = self.app._schema_compatibility()
        self.assertEqual(out['status'], 'UNREACHABLE')
        self.assertEqual(out['error'], 'PoolTimeout')
        self.assertNotIn('provider_status', out)

    def test_successful_probe_does_not_hide_pool_timeout(self):
        @contextmanager
        def connected(*args, **kwargs):
            yield object()
        with patch('omni_prod.db.connect', side_effect=connected):
            out = self.app._schema_compatibility()
        self.assertEqual(out['status'], 'UNREACHABLE')
        self.assertEqual(out['error'], 'PoolTimeout')


class SchemaQuotaEvidenceTests(unittest.TestCase):
    def test_verifier_keeps_safe_category_and_drops_provider_text(self):
        from tests.test_deployment_verification import dv
        out = dv._schema_evidence({'status': 'QUOTA_EXCEEDED', 'compatible': False,
                                  'error': 'OperationalError', 'error_code': 'DATABASE_QUOTA_EXCEEDED',
                                  'provider_status': 402, 'provider_status_basis': 'provider_quota_message',
                                  'message': 'postgresql://user:private@host/db'})
        self.assertEqual(out['error_code'], 'DATABASE_QUOTA_EXCEEDED')
        self.assertEqual(out['provider_status'], 402)
        self.assertNotIn('private', str(out))

    def test_healthy_schema_does_not_probe_again(self):
        from tests.test_deployment_verification import _FakePool, EXPECTED_VERSIONS
        from omni_prod import investor_app
        previous = investor_app._v28_pool
        try:
            investor_app._v28_pool = _FakePool(list(EXPECTED_VERSIONS))
            with patch('omni_prod.db.connect') as probe:
                out = investor_app._schema_compatibility()
            self.assertEqual(out['status'], 'COMPATIBLE')
            probe.assert_not_called()
        finally:
            investor_app._v28_pool = previous
