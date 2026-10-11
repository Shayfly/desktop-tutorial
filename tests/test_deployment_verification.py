"""Continuous Verification P0.2-P0.4: canonical verdict, schema compatibility,
post-deployment verification. Scenario A (conversation 500 linked to the
deployed commit), E (schema mismatch blocks promotion) and J (local green,
deployment smoke red -> release stays blocked) run against a local HTTP stub
that behaves like the deployed API. $0, no network beyond 127.0.0.1."""
from __future__ import annotations

import importlib.util
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from omni_prod import release_policy as rp
from omni_prod import verification_contract as vc
from omni_prod.migrations import discover_migrations
from omni_prod.schema_manifest import EXPECTED_VERSIONS, REQUIRED_MIGRATION

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('deployment_verify', ROOT / 'tools' / 'deployment_verify.py')
dv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dv)

SHA = '0123456789abcdef0123456789abcdef01234567'


class ManifestTests(unittest.TestCase):
    def test_manifest_matches_the_migration_files(self):
        found = tuple(m.version for m in discover_migrations(ROOT / 'infra' / 'postgres'))
        self.assertEqual(found, EXPECTED_VERSIONS, 'update omni_prod/schema_manifest.py with the new migration')
        self.assertEqual(REQUIRED_MIGRATION, max(found))


def C(name, status, mandatory=True, reason=''):
    return vc.CheckResult(check=name, status=status, mandatory=mandatory,
                          reason=reason or ('skipped' if status in (vc.NOT_RUN, vc.NA) else ''))


class VerdictTests(unittest.TestCase):
    def test_never_verified_by_default(self):
        self.assertEqual(vc.decide([])[0], vc.BLOCKED)
        self.assertEqual(vc.decide([C('a', vc.NA)])[0], vc.BLOCKED)
        self.assertEqual(vc.decide([C('a', vc.PASS, mandatory=False)])[0], vc.BLOCKED)

    def test_rules(self):
        self.assertEqual(vc.decide([C('a', vc.PASS), C('b', vc.FAIL)])[0], vc.FAILED)
        self.assertEqual(vc.decide([C('a', vc.PASS), C('b', vc.NOT_RUN)])[0], vc.BLOCKED)
        self.assertEqual(vc.decide([C('a', vc.PASS), C('b', vc.UNKNOWN)])[0], vc.BLOCKED)
        self.assertEqual(vc.decide([C('a', vc.PASS), C('b', vc.FAIL, mandatory=False)])[0], vc.VERIFIED_WITH_ADVISORIES)
        self.assertEqual(vc.decide([C('a', vc.PASS), C('b', vc.NA)])[0], vc.VERIFIED)
        # FAIL outranks NOT_RUN
        self.assertEqual(vc.decide([C('a', vc.PASS), C('b', vc.NOT_RUN), C('c', vc.FAIL)])[0], vc.FAILED)

    def test_skips_need_a_reason(self):
        with self.assertRaises(ValueError):
            vc.CheckResult(check='x', status=vc.NOT_RUN)
        with self.assertRaises(ValueError):
            vc.CheckResult(check='x', status='GREEN')

    def _ok(self, **kw):
        return vc.VerificationResult(kind='deployment', target='t', environment='preview', commit_sha=SHA,
                                     checks=[C('a', vc.PASS)], **kw).finish().to_dict()

    def test_promotion_gate_refuses_stale_or_unverified_evidence(self):
        ok = self._ok()
        self.assertEqual(vc.may_promote(ok, commit_sha=SHA), (True, 'promotable'))
        self.assertFalse(vc.may_promote(ok, commit_sha='ffffffffffffffff')[0])          # code changed after verification
        self.assertFalse(vc.may_promote(ok, now=time.time() + 2 * vc.DEFAULT_TTL_SECONDS)[0])  # expired
        self.assertFalse(vc.may_promote(self._ok(artifact_sha256='a'), artifact_sha256='b')[0])
        bad = vc.VerificationResult(kind='deployment', target='t', environment='preview', commit_sha=SHA,
                                    checks=[C('a', vc.PASS), C('b', vc.FAIL)]).finish().to_dict()
        self.assertFalse(vc.may_promote(bad, commit_sha=SHA)[0])
        self.assertFalse(vc.may_promote({'verdict': 'VERIFIED'})[0])                     # not the canonical schema

    def test_summary_lists_blockers_and_skips_with_reasons(self):
        d = vc.VerificationResult(kind='deployment', target='t', environment='preview', commit_sha=None,
                                  checks=[C('a', vc.PASS), C('b', vc.NOT_RUN, reason='no sha'),
                                          C('w', vc.FAIL, mandatory=False)]).finish().to_dict()
        self.assertEqual(d['schema'], 'verification-result/1')
        self.assertEqual(d['summary']['critical_blockers'], ['b'])
        self.assertEqual(d['summary']['skipped'], [{'check': 'b', 'reason': 'no sha'}])
        self.assertEqual(d['summary']['warnings'], ['w'])

    def test_quality_report_maps_onto_the_contract(self):
        def report(status):
            return rp.QualityReport(build_id='b1', artifact_sha256='abc', product_family='web', checks=[
                rp.Check('build', 'compile', rp.PASS, True, 'platform:sandbox', True),
                rp.Check('runtime', 'preview_smoke', status, True, 'platform:smoke', True, detail='smoke'),
                rp.Check('visual', 'contrast', rp.FAIL, False, 'platform:visual_qa', True, 'low', 'advisory')]).to_dict()
        self.assertEqual(vc.from_quality_report(report(rp.PASS), environment='staging').verdict,
                         vc.VERIFIED_WITH_ADVISORIES)
        self.assertEqual(vc.from_quality_report(report(rp.FAIL), environment='staging').verdict, vc.FAILED)
        self.assertEqual(vc.from_quality_report(report(rp.NOT_RUN), environment='staging').verdict, vc.BLOCKED)
        # the canonical verdict agrees with the release policy decision
        self.assertEqual(rp.QualityReport(build_id='b', artifact_sha256='a', product_family='web', checks=[
            rp.Check('runtime', 'preview_smoke', rp.FAIL, True, 'x', True)]).decision, 'FAILED')


class _Stub:
    """Minimal stand-in for a deployed 148AI API with switchable faults."""

    def __init__(self, **faults):
        self.f = {'sha': SHA, 'compatible': True, 'conversation_status': 200, 'leak': False,
                  'protected': False, 'anon_ok': False, **faults}
        self.tokens, self.owner, self.messages = {}, {}, {}
        stub = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body, ctype='application/json'):
                raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
                self.send_response(code)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _user(self):
                return stub.tokens.get((self.headers.get('Authorization') or '').removeprefix('Bearer '))

            def _route(self, method):
                if stub.f['protected'] and not self.headers.get('x-vercel-protection-bypass'):
                    return self._send(401, '<html>Authentication Required</html>', 'text/html')
                body = {}
                if method == 'POST':
                    body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
                path = self.path.split('?')[0]
                if path == '/api/v28/deployment':
                    return self._send(200, {'source_commit': stub.f['sha'], 'environment': 'preview', 'branch': 'b',
                                            'schema': {'required': 36, 'compatible': stub.f['compatible'],
                                                       'status': 'COMPATIBLE' if stub.f['compatible'] else 'MIGRATIONS_PENDING',
                                                       'missing': [] if stub.f['compatible'] else [36]}})
                if path == '/api/v28/auth/register':
                    tok = f'tok{len(stub.tokens)}'
                    stub.tokens[tok] = body['email']
                    return self._send(200, {'token': tok})
                user = self._user()
                if path == '/api/v28/projects':
                    if not user:
                        return self._send(401, {'detail': 'authentication required'})
                    pid = f'p{len(stub.owner)}'
                    stub.owner[pid] = user
                    return self._send(200, {'id': pid})
                pid = path.split('/')[4]
                if not user and not stub.f['anon_ok']:
                    return self._send(401, {'detail': 'authentication required'})
                if user and stub.owner.get(pid) != user and not stub.f['leak']:
                    return self._send(404, {'detail': 'not found'})
                if path.endswith('/conversation'):
                    if stub.f['conversation_status'] != 200:
                        return self._send(stub.f['conversation_status'], 'Internal Server Error', 'text/plain')
                    if method == 'POST':
                        stub.messages.setdefault(pid, []).extend(['u', 'a'])
                        return self._send(200, {'turn': {'reply': 'ok'}})
                    return self._send(200, {'messages': stub.messages.get(pid, [])})
                if path.endswith('/memory'):
                    return self._send(200, {'schema': 'project-memory/1'})
                return self._send(404, {})

            def do_GET(self):
                self._route('GET')

            def do_POST(self):
                self._route('POST')

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class DeploymentVerifyTests(unittest.TestCase):
    def run_stub(self, expect_sha=SHA, bypass=None, **faults):
        stub = _Stub(**faults)
        try:
            return dv.verify(stub.url, expect_sha=expect_sha, bypass=bypass)
        finally:
            stub.close()

    def status(self, result, name):
        return next(c['status'] for c in result['checks'] if c['check'] == name)

    def test_healthy_deployment_is_verified_and_promotable(self):
        r = self.run_stub()
        self.assertEqual(r['verdict'], vc.VERIFIED, r['reason'])
        self.assertEqual(r['commit_sha'], SHA)
        self.assertTrue(vc.may_promote(r, commit_sha=SHA)[0])

    def test_scenario_a_conversation_500_is_linked_to_the_deployed_commit(self):
        r = self.run_stub(conversation_status=500)
        self.assertEqual(r['verdict'], vc.FAILED)
        self.assertEqual(self.status(r, 'conversation_turn'), vc.FAIL)
        self.assertEqual(r['commit_sha'], SHA)
        self.assertEqual(next(c for c in r['checks'] if c['check'] == 'conversation_turn')['evidence']['status'], 500)
        self.assertFalse(vc.may_promote(r, commit_sha=SHA)[0])

    def test_scenario_e_schema_mismatch_blocks_promotion(self):
        r = self.run_stub(compatible=False)
        self.assertEqual(r['verdict'], vc.FAILED)
        self.assertEqual(self.status(r, 'schema_compatible'), vc.FAIL)
        self.assertIn('schema_compatible', r['summary']['critical_blockers'])

    def test_scenario_j_green_locally_but_wrong_build_deployed(self):
        r = self.run_stub(sha='feedfacefeedfacefeedfacefeedfacefeedface')
        self.assertEqual(r['verdict'], vc.FAILED)
        self.assertEqual(self.status(r, 'commit_sha'), vc.FAIL)

    def test_without_expected_sha_evidence_is_not_promotable(self):
        r = self.run_stub(expect_sha=None)
        self.assertEqual(r['verdict'], vc.BLOCKED)
        self.assertFalse(vc.may_promote(r)[0])

    def test_cross_user_exposure_and_auth_bypass_fail(self):
        self.assertEqual(self.status(self.run_stub(leak=True), 'cross_user_isolation'), vc.FAIL)
        self.assertEqual(self.status(self.run_stub(anon_ok=True), 'unauthenticated_denied'), vc.FAIL)

    def test_protected_or_unreachable_is_blocked_never_verified(self):
        prot = self.run_stub(protected=True)
        self.assertEqual(prot['verdict'], vc.BLOCKED)
        self.assertIn('protected (HTTP 401)', prot['summary']['skipped'][0]['reason'])
        self.assertEqual(self.run_stub(protected=True, bypass='synthetic-bypass')['verdict'], vc.VERIFIED)
        r = dv.verify('http://127.0.0.1:9', expect_sha=SHA)
        self.assertEqual(r['verdict'], vc.BLOCKED)

    def test_bypass_and_session_tokens_never_appear_in_output(self):
        r = self.run_stub(protected=True, bypass='synthetic-bypass-value')
        text = json.dumps(r)
        self.assertNotIn('synthetic-bypass-value', text)
        self.assertNotIn('tok0', text)


class _FakeConn:
    def __init__(self, applied):
        self.applied = applied

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, *a):
        class R:
            def __init__(s, rows):
                s.rows = rows

            def fetchone(s):
                return s.rows[0]

            def fetchall(s):
                return s.rows
        if 'to_regclass' in sql:
            return R([(self.applied is not None,)])
        return R([(v,) for v in self.applied])


class _FakePool:
    def __init__(self, applied):
        self.applied = applied

    def connection(self):
        return _FakeConn(self.applied)


class SchemaCompatibilityEndpointTests(unittest.TestCase):
    def setUp(self):
        try:
            from omni_prod import investor_app
        except ModuleNotFoundError as exc:  # fastapi absent in a minimal env
            self.skipTest(str(exc))
        self.app = investor_app
        self._pool = investor_app._v28_pool

    def tearDown(self):
        self.app._v28_pool = self._pool

    def compat(self, applied):
        self.app._v28_pool = None if applied == 'none' else _FakePool(applied)
        return self.app._schema_compatibility()

    def test_states(self):
        self.assertEqual(self.compat('none')['status'], 'NOT_CONFIGURED')
        full = self.compat(list(EXPECTED_VERSIONS))
        self.assertEqual((full['status'], full['compatible'], full['missing']), ('COMPATIBLE', True, []))
        pend = self.compat([v for v in EXPECTED_VERSIONS if v != 36])
        self.assertEqual((pend['status'], pend['compatible'], pend['missing']), ('MIGRATIONS_PENDING', False, [36]))
        self.assertEqual(self.compat(None)['status'], 'MIGRATIONS_PENDING')   # no schema_migrations table at all

    def test_endpoint_exposes_no_secrets(self):
        import os
        self.app._v28_pool = None
        os.environ['VERCEL_GIT_COMMIT_SHA'] = SHA
        try:
            body = self.app.v28_deployment()
        finally:
            os.environ.pop('VERCEL_GIT_COMMIT_SHA', None)
        self.assertEqual(set(body), {'source_commit', 'environment', 'branch', 'schema'})
        self.assertEqual(body['source_commit'], SHA)


if __name__ == '__main__':
    unittest.main()
