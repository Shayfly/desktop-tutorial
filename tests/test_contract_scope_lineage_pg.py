"""The contract behind a version is found through the workspace's own versions too, on real PostgreSQL.

Production, read-only, 2026-11-25 (verify-replay run 45607249874). The content site bld_c35b8332 (READY) produced
v_089840b5472d4323; the workspace then made
  v_d7cfba9f4a7c4160  "accepted in workspace"   (a promoted change: modification_requests)
  v_8fd6c2ad3b174200  "undo visual edit"        (parent_id only)
  v_88812e8a4066448e  "rollback from workspace" (parent_id only)
The lineage followed modification_requests alone, so the last two had no contract and were judged on the strict
floor (auth, role, data_create, data_update, data_delete, integration). The same lookup feeds a customer's change
request (worker_tasks.execute_modification), so a change made after an undo or a rollback was judged the same way.

Runs in intake-budget-pg (skipped elsewhere without M4D2_DATABASE_URL). Foreign keys are switched off for the
seeded rows only (session_replication_role), because the contract's own tables (credit_reservations,
creator_projects) play no part in the lookup.
"""
from __future__ import annotations

import json
import os
import pathlib
import unittest
import uuid

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
FIXTURE = json.loads((pathlib.Path(__file__).parent / 'fixtures' / 'replay_content_site_contract.json').read_text('utf-8'))
TENANT, PUBLIC = 'tenant_ee88bb0812cd6882655ed5b0', 'prj_m38cCNxifG74Pw'
BUILD, CONTRACT = 'bld_c35b8332175c4ebd9f416049d3da6792', 'bc_c3e6aa413faabff9b469f1df'
BUILT, ACCEPTED, UNDONE, ROLLED_BACK = ('v_089840b5472d4323', 'v_d7cfba9f4a7c4160', 'v_8fd6c2ad3b174200',
                                        'v_88812e8a4066448e')


class ContractScopeLineage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        root = pathlib.Path(__file__).resolve().parents[1]
        cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        cls.dbname = f'csl_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(root / 'infra' / 'postgres'))
            cls._seed(conn)
        cls.pool = DatabasePool(cls.url)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    @classmethod
    def _seed(cls, conn):
        infra, integrations, roles, defaults, prompt = FIXTURE['row']
        contract = {'infrastructure': infra, 'required_integrations': integrations, 'user_roles': roles,
                    'defaults_applied': defaults, 'prompt': prompt}
        conn.execute('SET session_replication_role = replica')
        conn.execute("INSERT INTO m5_build_contracts(id, project_id, contract_version, status, capability_plan_fingerprint,"
                     " contract_fingerprint, contract_json, created_at) VALUES (%s,%s,1,'READY','f','f',%s::jsonb, now())",
                     (CONTRACT, PUBLIC, json.dumps(contract, ensure_ascii=False)))
        for vid, parent, message in ((BUILT, None, 'build'), (ACCEPTED, BUILT, 'accepted in workspace'),
                                     (UNDONE, ACCEPTED, 'undo visual edit'),
                                     (ROLLED_BACK, UNDONE, 'rollback from workspace'),
                                     ('v_other_project', None, 'build')):
            conn.execute('INSERT INTO project_versions(id, project_id, parent_id, repository_sha256, message) '
                         'VALUES (%s,%s,%s,%s,%s)', (vid, TENANT if vid != 'v_other_project' else 'tenant_other',
                                                     parent, 'sha', message))
        conn.execute("INSERT INTO build_jobs(id, project_id, status, result_version_id) VALUES (%s,%s,'ready',%s)",
                     (BUILD, TENANT, BUILT))
        conn.execute('INSERT INTO build_requests(build_id, user_id, internal_project_id, public_project_id, prompt, '
                     'build_contract_id) VALUES (%s,%s,%s,%s,%s,%s)', (BUILD, 'usr_x', TENANT, PUBLIC, 'p', CONTRACT))
        conn.execute("INSERT INTO modification_requests(id, project_id, user_id, source_version_id, source_spec_version_id,"
                     " followup, status, promoted_version_id) VALUES ('mod_1',%s,'usr_x',%s,%s,'f','ACCEPTED',%s)",
                     (TENANT, BUILT, BUILT, ACCEPTED))
        conn.commit()

    def scope(self, version_id, project_id=TENANT):
        from omni_prod.worker_tasks import contract_scope_for_version
        return contract_scope_for_version(self.pool, project_id=project_id, version_id=version_id)

    def test_every_workspace_version_finds_the_approved_contract(self):
        for vid in (BUILT, ACCEPTED, UNDONE, ROLLED_BACK):
            with self.subTest(vid=vid):
                scope = self.scope(vid)
                self.assertIsNotNone(scope)
                self.assertIn('static_content_site', scope['defaults'])

    def test_a_rolled_back_content_site_is_judged_as_a_content_site(self):
        from omni_prod.web_saas_acceptance import acceptance_scope
        required, waived = acceptance_scope(self.scope(ROLLED_BACK))
        self.assertNotIn('data_create', required)
        self.assertIn('auth', waived)

    def test_another_projects_version_has_no_contract(self):
        self.assertIsNone(self.scope('v_other_project', project_id='tenant_other'))
        self.assertIsNone(self.scope(ROLLED_BACK, project_id='tenant_other'))


if __name__ == '__main__':
    unittest.main()
