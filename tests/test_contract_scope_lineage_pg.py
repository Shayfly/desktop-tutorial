"""The contract behind a version is found by where the version's CONTENT came from, on real PostgreSQL.

Production, read-only, 2026-11-25 (verify-replay run 45607249874). The content site bld_c35b8332 (READY) produced
v_089840b5472d4323; the workspace then made
  v_d7cfba9f4a7c4160  "accepted in workspace"   a promoted change (modification_requests), new content
  v_8fd6c2ad3b174200  "undo visual edit"        no build, not promoted; the content of the build again
  v_88812e8a4066448e  "rollback from workspace" no build, not promoted; the content of the accepted version again
  v_88bf6deea2a64908  a later build of the same project
The lineage followed modification_requests alone, so the undo and the rollback had no contract and were judged on the
strict floor (auth, role, data_create, data_update, data_delete, integration). The same lookup feeds a customer's
change request (worker_tasks.execute_modification) and the preview's acceptance (execute_preview_launch).

The first fix followed project_versions.parent_id for every version. Review of #530 (2026-11-25, reproduced): parent_id
is the project's head at commit time, not the version the content came from. A project can be built again under
another contract (7 projects in production have more than one build), so a data app restored after a later
content-site build took the content site's contract -- auth, role and data checks waived -- and the reverse gave a
false FAIL. A change accepted with force had two edges at the same depth and LIMIT 1 picked one arbitrarily.

Now every version has ONE origin (worker_tasks._CONTRACT_SCOPE_FOR_VERSION_SQL): a promoted change -> the version it
was made on; otherwise the earliest earlier version of the same project with the same repository_sha256 (a restore,
a rollback, an undo); otherwise parent_id. The nearest build on that chain answers.

Runs in intake-budget-pg (skipped elsewhere without M4D2_DATABASE_URL). In ContractScopeLineage foreign keys are
switched off for the seeded rows only (session_replication_role), because the contract's own tables
(credit_reservations, creator_projects) play no part in the lookup. RealWorkspaceLineage writes its versions with the
production code itself (PostgresProjectWorkspace.commit / restore, PostgresModificationRepository.accept / rollback),
so parent_id and repository_sha256 are what production writes, not what this file assumes.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import unittest
import uuid

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
FIXTURE = json.loads((pathlib.Path(__file__).parent / 'fixtures' / 'replay_content_site_contract.json').read_text('utf-8'))
TENANT, PUBLIC = 'tenant_ee88bb0812cd6882655ed5b0', 'prj_m38cCNxifG74Pw'
BUILD, CONTRACT = 'bld_c35b8332175c4ebd9f416049d3da6792', 'bc_c3e6aa413faabff9b469f1df'
BUILT, ACCEPTED, UNDONE, ROLLED_BACK, LATER_BUILD = ('v_089840b5472d4323', 'v_d7cfba9f4a7c4160', 'v_8fd6c2ad3b174200',
                                                     'v_88812e8a4066448e', 'v_88bf6deea2a64908')
# The first eight characters of the two production checksums: the undo holds the build's, the rollback the accepted one's.
SHA_BUILT, SHA_ACCEPTED = 'fa7e1cdf', '4d31782e'

_INFRA, _INTEGRATIONS, _ROLES, _DEFAULTS, _PROMPT = FIXTURE['row']
# The production content site: no sign-in, nothing stored (auth, role and data_create/update/delete are waived).
CONTENT = {'infrastructure': _INFRA, 'required_integrations': _INTEGRATIONS, 'user_roles': _ROLES,
           'defaults_applied': _DEFAULTS, 'prompt': _PROMPT}
# A later revision of the same content site (synthetic: the text of the real later contract was not fetched).
CONTENT_NEXT = dict(CONTENT, prompt=_PROMPT + '\nRevision 2.')
# A data app with sign-in and roles (synthetic): auth, role and every data kind are required.
DATA = {'infrastructure': _INFRA, 'required_integrations': [], 'user_roles': ['admin', 'member'],
        'defaults_applied': ['self_contained_web_v1'],
        'prompt': 'Order desk for a shop. Staff sign in; an admin creates, edits and deletes orders; a member reads them.'}
T0 = dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc)
STEPS = 64          # worker_tasks: "WHERE l.depth < 64"


def _ids(name: str) -> tuple[str, str]:
    """(internal project id, public project id) of one seeded scenario."""
    return f'tenant_{name}', f'prj_{name}'


class _Seed:
    """Rows as production writes them. Every version gets a later created_at than the one before it."""

    def __init__(self, conn):
        self.conn, self.minute, self.revisions = conn, 0, {}

    def version(self, vid, tenant, parent, sha, message='edit'):
        self.minute += 1
        self.conn.execute('INSERT INTO project_versions(id, project_id, parent_id, repository_sha256, message, created_at)'
                          ' VALUES (%s,%s,%s,%s,%s,%s)',
                          (vid, tenant, parent, sha, message, T0 + dt.timedelta(minutes=self.minute)))
        return vid

    def build(self, vid, tenant, public, contract, *, build_id=None, contract_id=None):
        """A build whose result is `vid`, under its own contract revision of the public project."""
        build_id, contract_id = build_id or f'bld_{vid}', contract_id or f'bc_{vid}'
        revision = self.revisions[public] = self.revisions.get(public, 0) + 1
        self.conn.execute(
            'INSERT INTO m5_build_contracts(id, project_id, contract_version, status, capability_plan_fingerprint,'
            " contract_fingerprint, contract_json, created_at) VALUES (%s,%s,%s,'READY','f',%s,%s::jsonb, now())",
            (contract_id, public, revision, contract_id, json.dumps(contract, ensure_ascii=False)))
        self.conn.execute("INSERT INTO build_jobs(id, project_id, status, result_version_id) VALUES (%s,%s,'ready',%s)",
                          (build_id, tenant, vid))
        self.conn.execute('INSERT INTO build_requests(build_id, user_id, internal_project_id, public_project_id, prompt, '
                          'build_contract_id) VALUES (%s,%s,%s,%s,%s,%s)',
                          (build_id, 'usr_x', tenant, public, 'p', contract_id))

    def built(self, vid, name, parent, sha, contract):
        tenant, public = _ids(name)
        self.version(vid, tenant, parent, sha, 'build')
        self.build(vid, tenant, public, contract)

    def change(self, promoted, source, tenant):
        """An accepted change: `promoted` is the version accept() committed, `source` the one it was proposed on."""
        self.conn.execute(
            'INSERT INTO modification_requests(id, project_id, user_id, source_version_id, source_spec_version_id,'
            " followup, status, promoted_version_id) VALUES (%s,%s,'usr_x',%s,%s,'f','ACCEPTED',%s)",
            (f'mod_{promoted}', tenant, source, source, promoted))


class _Database(unittest.TestCase):
    """A fresh database with the repository's migrations, dropped afterwards."""

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
            conn.commit()
        cls.pool = DatabasePool(cls.url)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def scope(self, version_id, project_id):
        """The lookup, with proof that it ran: contract_scope_for_version answers None for a failed query too (it logs
        the error and keeps the strict floor), so a None is only "no contract" when nothing was logged."""
        from omni_prod.worker_tasks import contract_scope_for_version
        with self.assertNoLogs('omni_prod.worker_tasks', level='ERROR'):
            return contract_scope_for_version(self.pool, project_id=project_id, version_id=version_id)

    def assertContract(self, scope, contract):
        """`scope` is the scope of exactly this contract, and it is judged like it."""
        from omni_prod.web_saas_acceptance import acceptance_scope
        self.assertIsNotNone(scope, 'no contract found: the strict floor would apply')
        self.assertEqual(scope['prompt'], contract['prompt'])
        self.assertEqual(scope['defaults'], contract['defaults_applied'])
        self.assertEqual(scope['user_roles'], contract['user_roles'])
        required, waived = acceptance_scope(scope)
        if contract is DATA:
            for kind in ('auth', 'role', 'data_create', 'data_update', 'data_delete'):
                self.assertIn(kind, required)
        else:
            self.assertNotIn('data_create', required)
            for kind in ('auth', 'role', 'data_create'):
                self.assertIn(kind, waived)


class ContractScopeLineage(_Database):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import psycopg
        with psycopg.connect(cls.url) as conn:
            conn.execute('SET session_replication_role = replica')
            cls._seed(_Seed(conn))
            conn.commit()

    @classmethod
    def _seed(cls, s):
        # The production project, in production's order.
        s.version(BUILT, TENANT, None, SHA_BUILT, 'build')
        s.build(BUILT, TENANT, PUBLIC, CONTENT, build_id=BUILD, contract_id=CONTRACT)
        s.version(ACCEPTED, TENANT, BUILT, SHA_ACCEPTED, 'accepted in workspace')
        s.change(ACCEPTED, BUILT, TENANT)
        s.version(UNDONE, TENANT, ACCEPTED, SHA_BUILT, 'undo visual edit')
        s.version(ROLLED_BACK, TENANT, UNDONE, SHA_ACCEPTED, 'rollback from workspace')
        s.version(LATER_BUILD, TENANT, ROLLED_BACK, 'later-build', 'build')
        s.build(LATER_BUILD, TENANT, PUBLIC, CONTENT_NEXT)
        s.version('v_other_project', 'tenant_other', None, 'other', 'build')

        # A data app, then a content-site build of the same project, then the data app restored (parent = the head).
        t = _ids('restore_data')[0]
        s.built('rd_data', 'restore_data', None, 'rd-data', DATA)
        s.built('rd_content', 'restore_data', 'rd_data', 'rd-content', CONTENT)
        s.version('rd_restored', t, 'rd_content', 'rd-data', 'rollback from workspace')
        s.version('rd_edit_on_restored', t, 'rd_restored', 'rd-edit')
        # The reverse: a content site, then a data-app build, then the content site restored.
        t = _ids('restore_content')[0]
        s.built('rc_content', 'restore_content', None, 'rc-content', CONTENT)
        s.built('rc_data', 'restore_content', 'rc_content', 'rc-data', DATA)
        s.version('rc_restored', t, 'rc_data', 'rc-content', 'undo visual edit')

        # accept(force=True): the change was made on the first build; the head it was committed on is the second.
        for name, first, second in (('forced_data', DATA, CONTENT), ('forced_content', CONTENT, DATA)):
            t = _ids(name)[0]
            s.built(f'{name}_source', name, None, f'{name}-1', first)
            s.built(f'{name}_head', name, f'{name}_source', f'{name}-2', second)
            s.version(f'{name}_accepted', t, f'{name}_head', f'{name}-3', 'accepted in workspace')
            s.change(f'{name}_accepted', f'{name}_source', t)

        # One rule alone reaches the build (the other two lead nowhere).
        t = _ids('only_change')[0]
        s.built('oc_build', 'only_change', None, 'oc-1', CONTENT)
        s.version('oc_promoted', t, None, 'oc-2', 'accepted in workspace')
        s.change('oc_promoted', 'oc_build', t)
        t = _ids('only_content')[0]
        s.built('os_build', 'only_content', None, 'os-1', CONTENT)
        s.version('os_restored', t, None, 'os-1', 'rollback from workspace')
        t = _ids('only_parent')[0]
        s.built('op_build', 'only_parent', None, 'op-1', CONTENT)
        s.version('op_edit', t, 'op_build', 'op-2')

        # An older build further down the chain of a newer one.
        t = _ids('nearest')[0]
        s.built('n_old', 'nearest', None, 'n-1', DATA)
        s.built('n_new', 'nearest', 'n_old', 'n-2', CONTENT)
        s.version('n_edit', t, 'n_new', 'n-3')
        s.version('n_promoted', t, 'n_edit', 'n-4', 'accepted in workspace')
        s.change('n_promoted', 'n_edit', t)

        # Identical content in another project, written earlier.
        s.built('twin_a_build', 'twin_a', None, 'twin', DATA)
        s.built('twin_b_build', 'twin_b', None, 'twin-b-own', CONTENT)
        s.version('twin_b_same', _ids('twin_b')[0], 'twin_b_build', 'twin')
        s.version('twin_c_same', _ids('twin_c')[0], None, 'twin')

        # Cycles: through parent_id, through changes, and one that passes a build.
        t = _ids('cycle')[0]
        s.version('cy_p1', t, 'cy_p2', 'cy-1')
        s.version('cy_p2', t, 'cy_p1', 'cy-2')
        s.version('cy_m1', t, None, 'cy-3')
        s.version('cy_m2', t, None, 'cy-4')
        s.change('cy_m1', 'cy_m2', t)
        s.change('cy_m2', 'cy_m1', t)
        s.built('cy_build', 'cycle', 'cy_after', 'cy-5', CONTENT)
        s.version('cy_after', t, 'cy_build', 'cy-6')

        # A chain of edits longer than the bound: long_0 is the build, long_N is N steps away from it.
        t = _ids('long')[0]
        s.built('long_0', 'long', None, 'long-0', CONTENT)
        for n in range(1, STEPS + 7):
            s.version(f'long_{n}', t, f'long_{n - 1}', f'long-{n}')

        # The same content built twice under two contracts, then restored: the earliest holder is the origin.
        t = _ids('twice')[0]
        s.built('tw_first', 'twice', None, 'tw-same', DATA)
        s.built('tw_second', 'twice', 'tw_first', 'tw-same', CONTENT)
        s.version('tw_edit', t, 'tw_second', 'tw-edit')
        s.version('tw_restored', t, 'tw_edit', 'tw-same', 'rollback from workspace')
        # A LATER build with the content of an earlier edit never becomes that edit's origin.
        t = _ids('later_twin')[0]
        s.built('lt_build', 'later_twin', None, 'lt-1', CONTENT)
        s.version('lt_edit', t, 'lt_build', 'lt-same')
        s.built('lt_later', 'later_twin', 'lt_edit', 'lt-same', DATA)

        # A promoted change whose content equals an earlier version of another build: the change's source decides.
        t = _ids('change_same')[0]
        s.built('cs_data', 'change_same', None, 'cs-data', DATA)
        s.built('cs_content', 'change_same', 'cs_data', 'cs-content', CONTENT)
        s.version('cs_promoted', t, 'cs_content', 'cs-data', 'accepted in workspace')
        s.change('cs_promoted', 'cs_content', t)

        # Two build rows on one version, inserted in opposite orders in two projects: the answer is the same.
        for name, order in (('tie_ab', ('a', 'b')), ('tie_ba', ('b', 'a'))):
            tenant, public = _ids(name)
            s.version(f'{name}_v', tenant, None, f'{name}-1', 'build')
            for letter in order:
                s.build(f'{name}_v', tenant, public, DATA if letter == 'a' else CONTENT,
                        build_id=f'bld_{name}_{letter}', contract_id=f'bc_{name}_{letter}')

    # ---- the production project -------------------------------------------------------------------------------
    def test_every_workspace_version_finds_the_approved_contract(self):
        for vid in (BUILT, ACCEPTED, UNDONE, ROLLED_BACK):
            with self.subTest(vid=vid):
                self.assertContract(self.scope(vid, TENANT), CONTENT)
        self.assertContract(self.scope(LATER_BUILD, TENANT), CONTENT_NEXT)

    def test_a_rolled_back_content_site_is_judged_as_a_content_site(self):
        from omni_prod.web_saas_acceptance import acceptance_scope
        required, waived = acceptance_scope(self.scope(ROLLED_BACK, TENANT))
        self.assertNotIn('data_create', required)
        self.assertIn('auth', waived)

    def test_another_projects_version_has_no_contract(self):
        self.assertIsNone(self.scope('v_other_project', 'tenant_other'))
        self.assertIsNone(self.scope(ROLLED_BACK, 'tenant_other'))

    # ---- a project built more than once -----------------------------------------------------------------------
    def test_a_data_app_restored_after_a_content_site_build_keeps_the_data_contract(self):
        tenant = _ids('restore_data')[0]
        self.assertContract(self.scope('rd_content', tenant), CONTENT)      # the head the restore was committed on
        self.assertContract(self.scope('rd_restored', tenant), DATA)
        self.assertContract(self.scope('rd_edit_on_restored', tenant), DATA)

    def test_a_content_site_restored_after_a_data_app_build_keeps_the_content_contract(self):
        tenant = _ids('restore_content')[0]
        self.assertContract(self.scope('rc_data', tenant), DATA)
        self.assertContract(self.scope('rc_restored', tenant), CONTENT)

    def test_a_forced_accept_takes_the_contract_of_the_version_the_change_was_made_on(self):
        self.assertContract(self.scope('forced_data_accepted', _ids('forced_data')[0]), DATA)
        self.assertContract(self.scope('forced_content_accepted', _ids('forced_content')[0]), CONTENT)

    def test_the_nearest_build_on_the_chain_wins(self):
        tenant = _ids('nearest')[0]
        for vid in ('n_new', 'n_edit', 'n_promoted'):
            with self.subTest(vid=vid):
                self.assertContract(self.scope(vid, tenant), CONTENT)
        self.assertContract(self.scope('n_old', tenant), DATA)

    # ---- each rule alone --------------------------------------------------------------------------------------
    def test_only_the_change_reaches_the_build(self):
        self.assertContract(self.scope('oc_promoted', _ids('only_change')[0]), CONTENT)

    def test_only_the_same_content_reaches_the_build(self):
        self.assertContract(self.scope('os_restored', _ids('only_content')[0]), CONTENT)

    def test_only_the_parent_reaches_the_build(self):
        self.assertContract(self.scope('op_edit', _ids('only_parent')[0]), CONTENT)

    # ---- what must never lend a contract ----------------------------------------------------------------------
    def test_identical_content_in_another_project_lends_nothing(self):
        self.assertContract(self.scope('twin_a_build', _ids('twin_a')[0]), DATA)
        # its own project's build through parent_id, not the earlier identical content of project twin_a
        self.assertContract(self.scope('twin_b_same', _ids('twin_b')[0]), CONTENT)
        self.assertIsNone(self.scope('twin_c_same', _ids('twin_c')[0]))      # a project with no build at all
        self.assertIsNone(self.scope('twin_c_same', _ids('twin_a')[0]))

    def test_same_content_built_twice_is_traced_to_its_first_holder_and_never_to_a_later_one(self):
        self.assertContract(self.scope('tw_restored', _ids('twice')[0]), DATA)
        self.assertContract(self.scope('lt_edit', _ids('later_twin')[0]), CONTENT)
        self.assertContract(self.scope('lt_later', _ids('later_twin')[0]), DATA)

    def test_a_change_with_the_content_of_an_older_build_follows_the_version_it_was_made_on(self):
        self.assertContract(self.scope('cs_promoted', _ids('change_same')[0]), CONTENT)

    def test_two_builds_on_one_version_answer_the_same_whatever_the_insert_order(self):
        self.assertContract(self.scope('tie_ab_v', _ids('tie_ab')[0]), DATA)
        self.assertContract(self.scope('tie_ba_v', _ids('tie_ba')[0]), DATA)

    # ---- the walk ends ----------------------------------------------------------------------------------------
    def test_a_cycle_ends_without_an_error(self):
        tenant = _ids('cycle')[0]
        for vid in ('cy_p1', 'cy_p2', 'cy_m1', 'cy_m2'):
            with self.subTest(vid=vid):
                self.assertIsNone(self.scope(vid, tenant))
        self.assertContract(self.scope('cy_after', tenant), CONTENT)
        self.assertContract(self.scope('cy_build', tenant), CONTENT)

    def test_the_walk_stops_after_64_steps(self):
        tenant = _ids('long')[0]
        self.assertContract(self.scope(f'long_{STEPS}', tenant), CONTENT)     # the last step the bound allows
        self.assertIsNone(self.scope(f'long_{STEPS + 1}', tenant))            # one past it: the strict floor
        self.assertIsNone(self.scope(f'long_{STEPS + 6}', tenant))


class _Store:
    """Object storage in memory (the boundary); the interface of omni_prod.storage.S3ArtifactStore."""

    def __init__(self):
        self.objects = {}

    def put_bytes(self, key, data):
        self.objects[key] = bytes(data)

    def get_bytes(self, key, *, verify=True):
        return self.objects[key]


class RealWorkspaceLineage(_Database):
    """The same two defects, with the versions written by the production code."""
    SPEC = {'title': 'Shop', 'summary': 'A shop', 'stack': ['python'],
            'requirements': [{'id': 'R1', 'text': 'show the shop', 'kind': 'functional', 'mandatory': True}],
            'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'the page opens'}]}

    def _build(self, repository, contract, name):
        """What a build leaves behind: its result version (the real commit) and the rows that bind it to a contract."""
        import psycopg
        tenant, public = _ids('real')
        version = self.workspace.commit(project_id=tenant, repository=repository, message=f'build {name}')
        self.specs.save(version_id=version.id, project_id=tenant, spec=self.spec)
        with psycopg.connect(self.url) as conn:
            conn.execute('SET session_replication_role = replica')
            self.seed.conn = conn
            self.seed.build(version.id, tenant, public, contract)
            conn.commit()
        return version

    def test_real_restore_and_forced_accept_keep_the_contract_of_their_content(self):
        from omni_prod.modification_repository import PostgresModificationRepository
        from omni_prod.product_spec import ProductSpec
        from omni_prod.spec_repository import PostgresSpecRepository
        from omni_prod.workspace import PostgresProjectWorkspace
        tenant = _ids('real')[0]
        self.workspace = PostgresProjectWorkspace(self.pool, _Store())
        self.specs, self.spec, self.seed = PostgresSpecRepository(self.pool), ProductSpec.from_dict(self.SPEC), _Seed(None)
        mods = PostgresModificationRepository(self.pool)
        data_app = {'app.py': 'print("orders")\n', 'templates/login.html': '<form>sign in</form>'}
        content_site = {'app.py': 'print("catalogue")\n', 'index.html': '<h1>GOA</h1>'}

        v_data = self._build(data_app, DATA, 'data app')
        # A change is proposed on the data app and waits for review...
        mod = f'mod_{uuid.uuid4().hex}'
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    mods.create(cur, modification_id=mod, project_id=tenant, user_id='usr_x',
                                source_version_id=v_data.id, followup='add a notes field')
        self.assertTrue(mods.transition_running(mod))
        self.assertTrue(mods.complete(mod, project_id=tenant, status='READY_FOR_REVIEW', classification='change_request',
                                      classification_reason='test', billable=True,
                                      candidate_repository=dict(data_app, **{'notes.py': 'NOTES = []\n'}),
                                      candidate_spec=self.spec))
        # ...while the project is built again as a content site.
        v_content = self._build(content_site, CONTENT, 'content site')
        self.assertEqual(v_content.parent_id, v_data.id)

        # accept(force=True): committed on the content site, made on the data app.
        accepted = mods.accept(mod, tenant, workspace=self.workspace, spec_repo=self.specs,
                               message='accepted in workspace', force=True)
        self.assertEqual((accepted['accepted'], accepted['forced']), (True, True))
        v_forced = self.workspace.get(project_id=tenant, version_id=accepted['new_version_id'])
        self.assertEqual(v_forced.parent_id, v_content.id)
        self.assertContract(self.scope(v_forced.id, tenant), DATA)

        # Restore the data app: the new version's parent is the head, its checksum is the data app's.
        restored = mods.rollback(tenant, target_version_id=v_data.id, workspace=self.workspace, spec_repo=self.specs,
                                 message='rollback from workspace')
        v_restored = self.workspace.get(project_id=tenant, version_id=restored['version_id'])
        self.assertEqual(v_restored.parent_id, v_forced.id)
        self.assertEqual(v_restored.checksum, v_data.checksum)
        self.assertContract(self.scope(v_restored.id, tenant), DATA)

        # And the reverse: restore the content site on top of the restored data app.
        back = mods.rollback(tenant, target_version_id=v_content.id, workspace=self.workspace, spec_repo=self.specs,
                             message='undo visual edit')
        v_back = self.workspace.get(project_id=tenant, version_id=back['version_id'])
        self.assertEqual(v_back.parent_id, v_restored.id)
        self.assertEqual(v_back.checksum, v_content.checksum)
        self.assertContract(self.scope(v_back.id, tenant), CONTENT)


if __name__ == '__main__':
    unittest.main()
