"""Golden E2E #1 build -> modify path against a REAL Postgres (migrations applied).

Skipped, not faked, without a reachable schema (same convention and env var as
test_m4d2_live_postgres: M4D2_DATABASE_URL). Covers the two defects found on
Preview on 2026-10-07:

1. A READY live build must store its ProductSpec with the version (the first
   modification failed with "predates spec tracking (M4B)").
2. An INTERNAL_QA account's modification must be admitted from the QA budget
   (it failed with "cost class not included in plan"), then settle through
   the same reservation.
"""
from __future__ import annotations

import os
import unittest
import uuid
from decimal import Decimal
from types import SimpleNamespace

DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')


def _skip_reason():
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            if conn.execute("SELECT to_regclass('public.internal_entitlements')").fetchone()[0] is None:
                return 'schema (through migration 029) not applied'
    except Exception as exc:
        return f'no live Postgres: {exc}'
    return None


_SKIP = _skip_reason()


class _MemoryStore:
    def __init__(self):
        self.objects = {}

    def put_bytes(self, key, data):
        self.objects[key] = bytes(data)
        return SimpleNamespace(key=key, sha256='', size=len(data))

    def get_bytes(self, key, *, verify=True):
        return self.objects[key]


@unittest.skipIf(_SKIP, _SKIP)
class GoldenModificationPathTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.creator_accounts import PostgresAccountService
        from omni_prod.db import DatabasePool
        from omni_prod.entitlements import grant
        from omni_prod.subscription_store import PostgresSubscriptionService
        self.pool = DatabasePool(DATABASE_URL)
        self.accounts = PostgresAccountService(token_secret='t' * 48, pool=self.pool)
        self.email = f'qa-{uuid.uuid4().hex[:8]}@example.com'
        self.account, _ = self.accounts.register(email=self.email, password='a-long-password-123')
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    grant(cur, email=self.email, reason='golden e2e', granted_by='test')
        self.subs = PostgresSubscriptionService(pool=self.pool)
        from omni_prod.qa_budget import QABudgetPolicy
        self.policy = QABudgetPolicy.from_env(
            {'OMNI_ENV': 'staging', 'OMNI_QA_BUILD_MAX_USD': '0.50', 'OMNI_QA_BUDGET_TOTAL_USD': '1000'})
        self.project = f'tenant_{uuid.uuid4().hex[:10]}'

    def tearDown(self):
        close = getattr(self.pool, 'close', None)
        if callable(close):
            close()

    def _spec(self):
        from omni_prod.product_spec import ProductSpec
        return ProductSpec.from_dict({
            'title': 'League', 'summary': 'league table', 'stack': ['python'],
            'requirements': [{'id': 'R1', 'text': 'teams'}],
            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'add a team'}]})

    def test_live_build_version_has_a_spec_and_qa_modification_is_admitted_and_settles(self):
        from omni_prod import worker_tasks
        from omni_prod.modification_admission import admit_modification
        from omni_prod.modification_repository import PostgresModificationRepository
        from omni_prod.spec_repository import PostgresSpecRepository
        from omni_prod.workspace import PostgresProjectWorkspace
        from tests.test_m3_preview_logic import BuildHarness

        workspace = PostgresProjectWorkspace(self.pool, _MemoryStore())
        spec_repo = PostgresSpecRepository(self.pool)
        spec = self._spec()

        # 1. The live build path commits version + spec in one transaction.
        h = BuildHarness()
        h.jobs.request['internal_project_id'] = self.project
        h.result.spec = spec
        status = worker_tasks._run_live_build_job(
            'bld_live', jobs=h.jobs, platform=h.platform, workspace=workspace,
            components_factory=h.factory, quality_fn=lambda **kw: h.quality,
            security_fn=lambda repo: h.security, spec_repo=spec_repo)
        self.assertEqual(status, 'ready')
        version_id = h.final['result_version_id']
        self.assertEqual(spec_repo.get(version_id, self.project).to_dict(), spec.to_dict())

        # 2. The QA-entitled account's modification is admitted from the QA budget.
        mods = PostgresModificationRepository(self.pool)
        mod_id = f'mod_{uuid.uuid4().hex}'
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    admission = admit_modification(
                        cur, subscriptions=self.subs, modification_id=mod_id, account_id=self.account.id,
                        project_id=self.project, cost_class='standard', credits=30,
                        internal_qa=True, qa_policy=self.policy)
                    self.assertTrue(admission.allowed, admission.reason)
                    mods.create(cur, modification_id=mod_id, project_id=self.project, user_id=self.account.id,
                                source_version_id=version_id, followup='add delete team')
                    mods.create_outbox(cur, modification_id=mod_id)
        with self.pool.connection() as conn:
            row = conn.execute('SELECT funding_source, status, estimated_provider_cost_usd FROM credit_reservations '
                               'WHERE build_id = %s', (mod_id,)).fetchone()
        self.assertEqual((row[0], row[1]), ('internal_qa', 'RESERVED'))
        self.assertEqual(Decimal(str(row[2])), Decimal('0.50'))

        # 3. The worker can read the request and the source spec it needs.
        req = mods.get_request(mod_id)
        self.assertEqual(req['source_version_id'], version_id)
        self.assertEqual(spec_repo.get(req['source_version_id'], self.project).to_dict(), spec.to_dict())

        # 4. Settlement of a QA-funded modification reservation.
        self.subs.settle(build_id=mod_id, actual_provider_cost_usd=Decimal('0.01'))
        with self.pool.connection() as conn:
            status = conn.execute('SELECT status FROM credit_reservations WHERE build_id = %s',
                                  (mod_id,)).fetchone()[0]
        self.assertEqual(status, 'SETTLED')

    def test_non_entitled_account_still_uses_its_plan(self):
        from omni_prod.modification_admission import admit_modification
        self.subs.plan_for(self.account.id)  # creates the default (free) subscription row
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    admission = admit_modification(
                        cur, subscriptions=self.subs, modification_id=f'mod_{uuid.uuid4().hex}',
                        account_id=self.account.id, project_id=self.project, cost_class='standard',
                        credits=30, internal_qa=False, qa_policy=self.policy)
        self.assertFalse(admission.allowed)
        self.assertEqual(admission.reason, 'cost class not included in plan')


if __name__ == '__main__':
    unittest.main()
