"""Read-only evidence export of one build: redacts secrets, binds the approved brief/contract, shows per-round
behaviour, and writes nothing. Needs the local PostgreSQL (M4D2_DATABASE_URL); skipped, not faked, without one."""
import json
import os
import unittest
import uuid

from omni_prod import evidence_export as X

URL = os.environ.get('M4D2_DATABASE_URL')


class PureTests(unittest.TestCase):
    def test_redaction_and_flag_allow_list(self):
        t = X.redact('postgresql://u:p@h/db key=abcdef AIzaSyAAAAAAAAAAAAAAAAAAAAAAAAAA')
        self.assertNotIn('u:p@h', t)
        self.assertNotIn('abcdef', t)
        self.assertIn('[redacted-google-key]', t)
        rt = X.runtime({'OMNI_PLAN_DRIVEN': '1', 'OMNI_DATABASE_URL': 'postgres://secret', 'OMNI_SOURCE_COMMIT': 'abc'})
        self.assertEqual(rt['flags']['OMNI_PLAN_DRIVEN'], '1')
        self.assertNotIn('OMNI_DATABASE_URL', rt['flags'])
        self.assertEqual(rt['source_commit'], 'abc')
        self.assertIn('OMNI_PREVIEW_INSPECTOR', rt['flags_unset'])

    def test_round_summary_shows_whether_the_failure_set_moved(self):
        beh = {'rounds': [{'summary': 'x', 'checks': [{'step_id': 's1', 'kind': 'data_create', 'passed': False}],
                           'missing_acceptance_ids': ['A2'], 'missing_kinds': ['responsive']},
                          {'summary': 'x', 'checks': [{'step_id': 's1', 'kind': 'data_create', 'passed': False}],
                           'missing_acceptance_ids': ['A2'], 'missing_kinds': ['responsive']}]}
        r = X.summarise_rounds(beh)
        self.assertEqual(r[0]['failed_steps'], r[1]['failed_steps'])      # stagnation is visible


@unittest.skipUnless(URL, 'needs M4D2_DATABASE_URL')
class LiveSchemaTests(unittest.TestCase):
    def test_export_against_the_real_schema_is_read_only_and_complete(self):
        import psycopg
        from omni_prod.product_architect import ProductArchitect
        from tests.test_content_only_site import approved_brief, compile_contract
        u = uuid.uuid4().hex[:10]
        pid, acc, bid, brief_id, cid, vid = (f'{p}_{u}' for p in ('prj', 'acc', 'bld', 'brf', 'cnt', 'ver'))
        contract = compile_contract(approved_brief())
        with psycopg.connect(URL) as conn:
            try:
                conn.execute('INSERT INTO creator_accounts (id, email, password_hash, salt_b64) VALUES (%s,%s,%s,%s)',
                             (acc, f'{u}@example.test', 'x', 'x'))
                conn.execute('INSERT INTO creator_projects (id, owner_id, title) VALUES (%s,%s,%s)', (pid, acc, 'חגית'))
                brief = approved_brief()
                conn.execute('INSERT INTO project_briefs (id, project_id, revision, account_id, mode, complete, brief_json, fingerprint) '
                             'VALUES (%s,%s,1,%s,%s,true,%s,%s)',
                             (brief_id, pid, acc, 'guided', json.dumps(brief.to_dict()), brief.fingerprint()))
                conn.execute('INSERT INTO m5_build_contracts (id, project_id, contract_version, status, capability_plan_fingerprint, '
                             'contract_fingerprint, contract_json, created_at) VALUES (%s,%s,1,%s,%s,%s,%s, now())',
                             (cid, pid, 'READY', 'cpf', 'cf', json.dumps(contract)))
                conn.execute("INSERT INTO build_approvals (id, project_id, account_id, brief_id, brief_revision, brief_fingerprint, "
                             "build_contract_id, contract_fingerprint, budget_fingerprint, status, expires_at, used_by_build_id) "
                             "VALUES (%s,%s,%s,%s,1,%s,%s,'cf','bf','USED', now() + interval '1 day', %s)",
                             (f'apr_{u}', pid, acc, brief_id, brief.fingerprint(), cid, bid))
                ev = {'repair_stop_reason': 'rounds_exhausted', 'provider_spend_usd': '0.42',
                      'behavior_acceptance': {'last': {'summary': 'password=hunter2xx'},
                                              'rounds': [{'summary': 'r0', 'checks': [{'step_id': 'c', 'kind': 'data_create', 'passed': False}],
                                                          'missing_acceptance_ids': ['A2']}]}}
                conn.execute('INSERT INTO project_versions (id, project_id, repository_sha256, message) VALUES (%s,%s,%s,%s)', (vid, pid, 'x', 'm'))
                conn.execute("INSERT INTO build_jobs (id, project_id, status, repair_rounds, evidence_json, version_id) VALUES (%s,%s,'FAILED',5,%s,%s)",
                             (bid, pid, json.dumps(ev), vid))
                conn.execute('INSERT INTO project_version_specs (version_id, project_id, spec_json) VALUES (%s,%s,%s)',
                             (vid, pid, json.dumps({'acceptance': [{'id': 'A2', 'requirement_id': 'R1', 'text': 'x'}]})))
                out = X.export(conn, bid, {'OMNI_PLAN_DRIVEN': '1'})
                self.assertEqual(out['build']['status'], 'FAILED')
                self.assertEqual(out['approved_contract']['acceptance_scope_by_deployed_code']['required'], ['data_read', 'responsive', 'api_smoke'])
                self.assertEqual(out['approved_brief']['fields']['content_only']['value'], 'yes')
                self.assertEqual(out['product_spec_acceptance'][0]['id'], 'A2')
                self.assertEqual(out['behavior_acceptance']['per_round'][0]['missing_acceptance_ids'], ['A2'])
                self.assertNotIn('hunter2xx', json.dumps(out))
                self.assertTrue(out['schema_versions'])
                with self.assertRaises(psycopg.errors.ReadOnlySqlTransaction):
                    conn.execute("UPDATE build_jobs SET status='X' WHERE id=%s", (bid,))
            finally:
                conn.rollback()


    def _seed(self, conn, u, tag, approval_for):
        """A project with a build whose approval is `approval_for` ('self' | 'other' | None)."""
        from tests.test_content_only_site import approved_brief, compile_contract
        pid, acc, bid, other = (f'{p}_{tag}{u}' for p in ('prj', 'acc', 'bld', 'bld2'))
        brief, contract = approved_brief(), compile_contract(approved_brief())
        conn.execute('INSERT INTO creator_accounts (id, email, password_hash, salt_b64) VALUES (%s,%s,%s,%s)', (acc, f'{tag}{u}@example.test', 'x', 'x'))
        conn.execute('INSERT INTO creator_projects (id, owner_id, title) VALUES (%s,%s,%s)', (pid, acc, 'p'))
        conn.execute('INSERT INTO project_briefs (id, project_id, revision, account_id, mode, complete, brief_json, fingerprint) '
                     "VALUES (%s,%s,1,%s,'guided',true,%s,%s)", (f'brf_{tag}{u}', pid, acc, json.dumps(brief.to_dict()), brief.fingerprint()))
        conn.execute('INSERT INTO m5_build_contracts (id, project_id, contract_version, status, capability_plan_fingerprint, contract_fingerprint, '
                     "contract_json, created_at) VALUES (%s,%s,1,'READY','c','cf',%s,now())", (f'cnt_{tag}{u}', pid, json.dumps(contract)))
        for b in (bid, other):
            conn.execute("INSERT INTO build_jobs (id, project_id, status, evidence_json) VALUES (%s,%s,'FAILED','{}')", (b, pid))
        if approval_for:
            conn.execute("INSERT INTO build_approvals (id, project_id, account_id, brief_id, brief_revision, brief_fingerprint, build_contract_id, "
                         "contract_fingerprint, budget_fingerprint, status, expires_at, used_by_build_id) "
                         "VALUES (%s,%s,%s,%s,1,%s,%s,'cf','bf',%s, now() + interval '1 day', %s)",
                         (f'apr_{tag}{u}', pid, acc, f'brf_{tag}{u}', brief.fingerprint(), f'cnt_{tag}{u}', 'ACTIVE' if approval_for == 'unused' else 'USED', bid if approval_for == 'self' else (None if approval_for == 'unused' else other)))
        return bid

    def test_only_the_approval_of_this_exact_build_is_used_and_a_missing_one_is_reported(self):
        import psycopg
        u = uuid.uuid4().hex[:8]
        with psycopg.connect(URL) as conn:
            try:
                exact = X.export(conn, self._seed(conn, u, 'a', 'self'))
                self.assertEqual(exact['approval_status'], 'EXACT')
                self.assertIn('approved_contract', exact)
                conn.rollback()
                # the ONLY approval of the project belongs to another build: it must NOT be substituted
                missing = X.export(conn, self._seed(conn, u, 'b', 'other'))
                self.assertTrue(missing['approval_status'].startswith('MISSING'))
                self.assertNotIn('approved_brief', missing)
                self.assertNotIn('approved_contract', missing)
                self.assertEqual(missing['approvals'], [])
                self.assertEqual(len(missing['other_project_approvals_not_used']), 1)    # reported, not used
                conn.rollback()
                none = X.export(conn, self._seed(conn, u, 'c', None))
                self.assertTrue(none['approval_status'].startswith('MISSING'))
                conn.rollback()
                # an approval nobody used yet (used_by_build_id NULL) is not this build's approval either
                unused = X.export(conn, self._seed(conn, u, 'e', 'unused'))
                self.assertTrue(unused['approval_status'].startswith('MISSING'))
                self.assertNotIn('approved_contract', unused)
            finally:
                conn.rollback()

    def test_a_contract_whose_fingerprint_differs_from_the_approval_is_reported_missing(self):
        import psycopg
        u = uuid.uuid4().hex[:8]
        with psycopg.connect(URL) as conn:
            try:
                bid = self._seed(conn, u, 'd', 'self')
                conn.execute("UPDATE build_approvals SET contract_fingerprint='different' WHERE used_by_build_id=%s", (bid,))
                out = X.export(conn, bid)
                self.assertTrue(str(out['approved_contract']).startswith('MISSING'))
            finally:
                conn.rollback()


class OneOffRunTests(unittest.TestCase):
    def test_the_file_runs_from_stdin_so_no_merge_or_worker_deploy_is_needed(self):
        import pathlib
        import subprocess
        import sys
        src = pathlib.Path(X.__file__)
        r = subprocess.run([sys.executable, '-', 'not-a-build-id'], input=src.read_text(), capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 2)
        self.assertIn('usage', r.stderr)
        self.assertIn('python - bld_<hex> < omni_prod/evidence_export.py', X.__doc__)
        self.assertNotIn('from .', src.read_text())          # no relative import: it must work piped through stdin


if __name__ == '__main__':
    unittest.main()
