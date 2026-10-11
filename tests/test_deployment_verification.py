"""Continuous Verification P0.2-P0.4: canonical verdict, schema compatibility,
post-deployment verification. Scenario A (conversation 500 linked to the
deployed commit), E (schema mismatch blocks promotion) and J (local green,
deployment smoke red -> release stays blocked) run against a local HTTP stub
that behaves like the deployed API. $0, no network beyond 127.0.0.1."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import uuid
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
sys.modules['deployment_verify'] = dv
_spec.loader.exec_module(dv)

SHA = '0123456789abcdef0123456789abcdef01234567'


class ManifestTests(unittest.TestCase):
    def test_manifest_matches_the_migration_files(self):
        found = tuple(m.version for m in discover_migrations(ROOT / 'infra' / 'postgres'))
        self.assertEqual(found, EXPECTED_VERSIONS, 'update omni_prod/schema_manifest.py with the new migration')
        self.assertEqual(REQUIRED_MIGRATION, max(found))

    def test_single_compatibility_rule(self):
        from omni_prod.schema_manifest import compatibility
        full = compatibility(EXPECTED_VERSIONS)
        self.assertEqual((full['status'], full['missing'], full['unknown_applied']), ('COMPATIBLE', [], []))
        pending = compatibility([v for v in EXPECTED_VERSIONS if v != 38])     # deployed code ahead of the DB
        self.assertEqual((pending['compatible'], pending['missing']), (False, [38]))
        ahead = compatibility(list(EXPECTED_VERSIONS) + [39])                   # DB ahead of this code
        self.assertEqual((ahead['compatible'], ahead['unknown_applied']), (True, [39]))
        self.assertEqual(compatibility([])['missing'], list(EXPECTED_VERSIONS))


def C(name, status, mandatory=True, reason=''):
    return vc.CheckResult(check=name, status=status, mandatory=mandatory,
                          reason=reason or ('skipped' if status in (vc.NOT_RUN, vc.NA) else ''))


def promote(result, req=('a',), pol=None, **kw):
    """may_promote under a trusted caller policy (default: check 'a' required, no NA exceptions)."""
    return vc.may_promote(result, required=req, na_policy=pol, **kw)


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
        self.assertEqual(vc.decide([C('a', vc.PASS), C('b', vc.NA)])[0], vc.BLOCKED)          # mandatory NA: fail closed
        self.assertEqual(vc.decide([C('a', vc.PASS), C('b', vc.NA, mandatory=False)])[0], vc.VERIFIED)
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
        self.assertEqual(promote(ok, commit_sha=SHA), (True, 'promotable'))
        self.assertFalse(promote(ok, commit_sha='ffffffffffffffff')[0])          # code changed after verification
        self.assertFalse(promote(ok, now=time.time() + 2 * vc.DEFAULT_TTL_SECONDS)[0])  # expired
        self.assertFalse(promote(self._ok(artifact_sha256='a'), artifact_sha256='b')[0])
        bad = vc.VerificationResult(kind='deployment', target='t', environment='preview', commit_sha=SHA,
                                    checks=[C('a', vc.PASS), C('b', vc.FAIL)]).finish().to_dict()
        self.assertFalse(promote(bad, commit_sha=SHA)[0])
        self.assertFalse(promote({'verdict': 'VERIFIED'})[0])                     # not the canonical schema

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


POLICY = {'version': 'na-exceptions/1', 'allowed': ['b'], 'reason': 'no payments in this product family'}


class ReviewFindingTests(unittest.TestCase):
    """Independent review of PR #11 (2026-10-11): exact SHA, timestamp validity, NA fail-closed."""

    def result(self, *, sha=SHA, checks=None, na_policy=None, **kw):
        return vc.VerificationResult(kind='deployment', target='t', environment='preview', commit_sha=sha,
                                     checks=checks or [C('a', vc.PASS)], na_policy=na_policy, **kw).finish().to_dict()

    # finding 1: exact full-SHA equality
    def test_forged_sha_prefixes_are_refused(self):
        ok = self.result()
        self.assertTrue(promote(ok, commit_sha=SHA)[0])
        self.assertTrue(promote(ok, commit_sha=SHA.upper())[0])               # case only
        forged = SHA[:12] + 'f' * 28                                                     # same 12-char prefix
        self.assertFalse(promote(ok, commit_sha=forged)[0])
        self.assertFalse(promote(self.result(sha=forged), commit_sha=SHA)[0])
        for short in (SHA[:7], SHA[:12], SHA[:39], SHA + '0', '', ' ' + SHA, 'g' * 40):
            with self.subTest(short=short):
                self.assertFalse(promote(ok, commit_sha=short or None)[0])
                self.assertFalse(promote(self.result(sha=short or None), commit_sha=SHA)[0])

    def test_unbound_promotion_is_refused(self):
        self.assertIn('not bound', promote(self.result())[1])
        self.assertTrue(promote(self.result(artifact_sha256='d' * 64), artifact_sha256='d' * 64)[0])

    # finding 2: timestamps and validity window
    def test_future_dated_and_malformed_timestamps_are_refused(self):
        now = time.time()
        cases = {
            'future finished_at': {'finished_at': now + 3600},
            'future started+finished': {'started_at': now + 7200, 'finished_at': now + 7300},
            'missing finished_at': {'finished_at': None},
            'missing started_at': {'started_at': None},
            'string timestamp': {'finished_at': str(now)},
            'bool timestamp': {'finished_at': True},
            'nan timestamp': {'finished_at': float('nan')},
            'inf timestamp': {'finished_at': float('inf')},
            'finished before started': {'started_at': now, 'finished_at': now - 10},
            'ttl zero': {'ttl_seconds': 0},
            'ttl negative': {'ttl_seconds': -5},
            'ttl huge': {'ttl_seconds': vc.MAX_TTL_SECONDS + 1},
            'ttl missing': {'ttl_seconds': None},
            'ttl string': {'ttl_seconds': '86400'},
            'ttl bool': {'ttl_seconds': True},
        }
        for name, patch in cases.items():
            with self.subTest(name):
                r = {**self.result(), **patch}
                self.assertFalse(promote(r, commit_sha=SHA, now=now)[0], name)
        r = self.result()
        self.assertTrue(promote(r, commit_sha=SHA, now=r['finished_at'] + 30)[0])           # small skew ok
        self.assertTrue(promote(r, commit_sha=SHA, now=r['finished_at'] - 30)[0])
        self.assertFalse(promote(r, commit_sha=SHA, now=r['finished_at'] - 3600)[0])       # clock behind
        self.assertFalse(promote(r, commit_sha=SHA, now=r['finished_at'] + vc.DEFAULT_TTL_SECONDS + 1)[0])
        short = self.result(ttl_seconds=60)
        self.assertFalse(promote(short, commit_sha=SHA, now=short['finished_at'] + 61)[0])

    def test_forged_verdict_is_recomputed_and_refused(self):
        bad = self.result(checks=[C('a', vc.PASS), C('b', vc.FAIL)])
        self.assertEqual(bad['verdict'], vc.FAILED)
        forged = {**bad, 'verdict': vc.VERIFIED}
        ok, why = promote(forged, commit_sha=SHA)
        self.assertFalse(ok)
        self.assertIn('recomputed', why)
        # a stored FAILED cannot be upgraded either: verdict must equal the recomputation
        weaker = {**self.result(), 'verdict': vc.VERIFIED_WITH_ADVISORIES}
        self.assertIn('does not match', promote(weaker, commit_sha=SHA)[1])
        self.assertFalse(promote({**self.result(), 'checks': [{'check': 'a'}]}, commit_sha=SHA)[0])
        dropped = {**self.result(checks=[C('a', vc.PASS), C('b', vc.PASS)], required=('a', 'b'))}
        dropped['checks'] = dropped['checks'][:1]                                      # required check removed
        dropped['required'] = ['a']                                                    # ...and the list forged
        self.assertFalse(promote(dropped, req=('a', 'b'), commit_sha=SHA)[0])

    # finding 3: mandatory NOT_APPLICABLE fails closed
    def test_mandatory_not_applicable_blocks_without_policy(self):
        checks = [C('a', vc.PASS), C('b', vc.NA, reason='no payments')]
        r = self.result(checks=checks)
        self.assertEqual(r['verdict'], vc.BLOCKED)
        self.assertIn('b', r['summary']['critical_blockers'])
        self.assertFalse(promote(r, commit_sha=SHA)[0])
        self.assertEqual(vc.decide([C('b', vc.NA)], na_policy=POLICY)[0], vc.BLOCKED)    # NA alone never verifies

    def test_versioned_policy_authorizes_only_named_checks(self):
        checks = [C('a', vc.PASS), C('b', vc.NA, reason='no payments')]
        r = self.result(checks=checks, na_policy=POLICY)
        self.assertEqual(r['verdict'], vc.VERIFIED_WITH_ADVISORIES)
        self.assertIn('na-exceptions/1', r['reason'])
        self.assertNotIn('b', r['summary']['critical_blockers'])
        self.assertTrue(promote(r, pol=POLICY, commit_sha=SHA)[0])                    # caller trusts POLICY
        other = [C('a', vc.PASS), C('c', vc.NA, reason='x')]
        self.assertEqual(vc.decide(other, na_policy=POLICY)[0], vc.BLOCKED)              # not named -> blocked
        # the evidence's own policy is never trusted: without the caller's policy it is refused
        self.assertFalse(promote(r, commit_sha=SHA)[0])

    def test_malformed_policies_never_authorize(self):
        checks = [C('a', vc.PASS), C('b', vc.NA, reason='x')]
        for bad in ({'allowed': ['b'], 'reason': 'r'},                     # unversioned
                    {'version': 'latest', 'allowed': ['b'], 'reason': 'r'},
                    {'version': 'na/0', 'allowed': ['b'], 'reason': 'r'},
                    {'version': 'na/1', 'allowed': 'b', 'reason': 'r'},       # string, not a list
                    {'version': 'na/1', 'allowed': [''], 'reason': 'r'},
                    {'version': 'na/1', 'allowed': ['b']},                    # no reason
                    {'version': 'na/1', 'allowed': ['b'], 'reason': '  '},
                    ['b'], 'na/1'):
            with self.subTest(policy=bad):
                self.assertEqual(vc.decide(checks, na_policy=bad)[0], vc.BLOCKED)

    def test_quality_report_mandatory_na_maps_fail_closed(self):
        rep = rp.QualityReport(build_id='b', artifact_sha256='a', product_family='web', checks=[
            rp.Check('build', 'compile', rp.PASS, True, 'x', True),
            rp.Check('payments', 'checkout', rp.NA, True, 'x', True, detail='no payments')]).to_dict()
        self.assertEqual(rep['decision'], 'READY')                                      # release-policy/1 view
        self.assertEqual(vc.from_quality_report(rep, environment='staging').verdict, vc.BLOCKED)
        pol = {'version': 'na-exceptions/1', 'allowed': ['payments/checkout'], 'reason': 'family has no payments'}
        self.assertEqual(vc.from_quality_report(rep, environment='staging', na_policy=pol).verdict,
                         vc.VERIFIED_WITH_ADVISORIES)


class ForgedEvidenceTests(unittest.TestCase):
    """Closure review: the gate must not be bypassable by forged evidence fields.
    Each case was a working bypass on 5ad2ccc (evidence-supplied policy trusted)."""

    def base(self, checks, verdict, **extra):
        now = time.time()
        return {'schema': vc.SCHEMA, 'commit_sha': SHA, 'started_at': now - 5, 'finished_at': now - 1,
                'ttl_seconds': 3600, 'verdict': verdict, 'checks': checks, **extra}

    def gate(self, r, **kw):
        return vc.may_promote(r, required=vc.DEPLOYMENT_REQUIRED_CHECKS, commit_sha=SHA, **kw)

    def test_forged_empty_required_list(self):
        r = self.base([{'check': 'deployment_endpoint', 'status': 'PASS', 'mandatory': True}], vc.VERIFIED,
                      required=[], na_policy=None)
        ok, why = self.gate(r)
        self.assertFalse(ok)
        self.assertIn('required checks missing', why)

    def test_forged_self_authorizing_na_policy(self):
        checks = [{'check': n, 'status': 'PASS', 'mandatory': True} for n in vc.DEPLOYMENT_REQUIRED_CHECKS]
        i = vc.DEPLOYMENT_REQUIRED_CHECKS.index('conversation_turn')       # by name, not position
        checks[i] = {'check': 'conversation_turn', 'status': 'NOT_APPLICABLE', 'mandatory': True, 'reason': 'x'}
        r = self.base(checks, vc.VERIFIED_WITH_ADVISORIES, required=list(vc.DEPLOYMENT_REQUIRED_CHECKS),
                      na_policy={'version': 'forged/1', 'allowed': ['conversation_turn'], 'reason': 'trust me'})
        ok, why = self.gate(r)
        self.assertFalse(ok)
        self.assertIn('not applicable without an authorizing NA policy', why)
        # a trusted caller policy for a *different* check still does not authorize it
        pol = {'version': 'na-exceptions/1', 'allowed': ['project_memory'], 'reason': 'n/a'}
        self.assertFalse(self.gate(r, na_policy=pol)[0])

    def test_duplicate_check_names(self):
        checks = [{'check': n, 'status': 'PASS', 'mandatory': True} for n in vc.DEPLOYMENT_REQUIRED_CHECKS]
        checks.append({'check': 'conversation_turn', 'status': 'FAIL', 'mandatory': False})
        ok, why = self.gate(self.base(checks, vc.VERIFIED_WITH_ADVISORIES))
        self.assertFalse(ok)
        self.assertIn('duplicate', why)

    def test_required_check_downgraded_or_mandatory_flag_not_true(self):
        for bad in (False, 'true', 1, None):
            checks = [{'check': n, 'status': 'PASS', 'mandatory': True} for n in vc.DEPLOYMENT_REQUIRED_CHECKS]
            checks[2]['mandatory'] = bad
            with self.subTest(mandatory=bad):
                self.assertFalse(self.gate(self.base(checks, vc.VERIFIED))[0])

    def test_caller_must_supply_policy(self):
        checks = [{'check': n, 'status': 'PASS', 'mandatory': True} for n in vc.DEPLOYMENT_REQUIRED_CHECKS]
        r = self.base(checks, vc.VERIFIED)
        self.assertTrue(self.gate(r)[0])                                           # genuine evidence passes
        for req in ((), [], None, ('',), list(vc.DEPLOYMENT_REQUIRED_CHECKS)):
            with self.subTest(required=req):
                self.assertFalse(vc.may_promote(r, required=req, commit_sha=SHA)[0])
        with self.assertRaises(TypeError):
            vc.may_promote(r, commit_sha=SHA)                                      # no default policy exists

    def test_genuine_tool_output_round_trips_through_the_gate(self):
        stub = _Stub()
        try:
            r = dv.verify(stub.url, expect_sha=SHA)
        finally:
            stub.close()
        self.assertEqual(self.gate(r), (True, 'promotable'))
        self.assertFalse(self.gate({**r, 'checks': r['checks'][:-1], 'required': r['required'][:-1]})[0])


class _Stub:
    """Minimal stand-in for a deployed 148AI API with switchable faults/attacks.
    Records every request's sensitive headers so leaks can be asserted."""

    def __init__(self, **faults):
        self.f = {'sha': SHA, 'env': 'preview', 'compatible': True, 'conversation_status': 200, 'leak': False,
                  'protected': False, 'bypass_ok': 'synthetic-bypass', 'anon_ok': False, 'redirect_to': None,
                  'set_cookie': False, 'sleep_on': None, 'drop_on': None, 'huge_on': None, 'html_on': None,
                  'no_token': False, 'reject_tokens': False, 'project_id': None, 'echo_auth': False,
                  'me_wrong_user': False, 'bad_contract': False, **faults}
        self.tokens, self.owner, self.messages, self.seen = {}, {}, {}, []
        stub = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body, ctype='application/json', extra=()):
                raw = body if isinstance(body, bytes) else (body.encode() if isinstance(body, str) else json.dumps(body).encode())
                self.send_response(code)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(raw)))
                for k, v in extra:
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(raw)

            def _user(self):
                if stub.f['reject_tokens']:
                    return None
                return stub.tokens.get((self.headers.get('Authorization') or '').removeprefix('Bearer '))

            def _route(self, method):
                path = self.path.split('?')[0]
                stub.seen.append({'path': path, 'auth': self.headers.get('Authorization'),
                                  'bypass': self.headers.get('x-vercel-protection-bypass'),
                                  'cookie': self.headers.get('Cookie')})
                tag = path.rsplit('/', 1)[-1]
                if stub.f['drop_on'] == tag:
                    self.connection.shutdown(2)
                    return
                if stub.f['sleep_on'] == tag:
                    time.sleep(1.5)
                if stub.f['redirect_to'] and path == stub.f.get('redirect_path', '/api/v28/deployment'):
                    return self._send(302, b'', extra=[('Location', stub.f['redirect_to'] + path)])
                if stub.f['protected'] and self.headers.get('x-vercel-protection-bypass') != stub.f['bypass_ok']:
                    return self._send(401, '<html>Authentication Required</html>', 'text/html')
                if stub.f['huge_on'] == tag:
                    return self._send(200, b'{"x":"' + b'a' * (dv.MAX_BYTES + 10) + b'"}')
                if stub.f['html_on'] == tag:
                    return self._send(200, '<html>ok</html>', 'text/html')
                body = {}
                if method == 'POST':
                    body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
                cookie = [('Set-Cookie', 'track=1; Path=/')] if stub.f['set_cookie'] else []
                if path == '/api/v28/deployment':
                    return self._send(200, {'source_commit': stub.f['sha'], 'environment': stub.f['env'], 'branch': 'b',
                                            'schema': {'required': 36, 'compatible': stub.f['compatible'],
                                                       'status': 'COMPATIBLE' if stub.f['compatible'] else 'MIGRATIONS_PENDING',
                                                       'missing': [] if stub.f['compatible'] else [36],
                                                       'note': 'free text <script> must not be copied'}}, extra=cookie)
                if path == '/api/v28/auth/register':
                    tok = f'sess-{uuid.uuid4().hex}'
                    stub.tokens[tok] = body['email']
                    return self._send(200, {} if stub.f['no_token'] else {'token': tok}, extra=cookie)
                user = self._user()
                if path == '/api/v28/me':
                    if not user:
                        return self._send(401, {'detail': 'authentication required'})
                    if stub.f['me_wrong_user']:
                        user = 'someone-else@example.com'
                    return self._send(200, {'id': 'u1', 'email': user, 'created_at': 't', 'subscription': {}})
                if path == '/api/v28/projects':
                    if not user:
                        return self._send(401, {'detail': 'authentication required'})
                    pid = stub.f['project_id'] or f'p{len(stub.owner)}'
                    stub.owner[pid] = user
                    return self._send(200, {'id': pid})
                pid = path.split('/')[4]
                if not user and not stub.f['anon_ok']:
                    return self._send(401, {'detail': 'authentication required'})
                if user and stub.owner.get(pid) != user and not stub.f['leak']:
                    return self._send(404, {'detail': 'not found'})
                if path.endswith('/conversation'):
                    if stub.f['conversation_status'] == 503:
                        return self._send(503, {'detail': {'error': 'conversation_not_ready',
                                                           'missing_migration': '036_intelligence_plane',
                                                           'message': 'free text'}})
                    if stub.f['conversation_status'] != 200:
                        echoed = self.headers.get('Authorization') if stub.f['echo_auth'] else 'Internal Server Error'
                        return self._send(stub.f['conversation_status'], {'detail': echoed})
                    if method == 'POST':
                        stub.messages.setdefault(pid, []).extend(['u', 'a'])
                        return self._send(200, {'turn': {'reply': 'ok'}})
                    body = {'messages': stub.messages.get(pid, []), 'discovery': None, 'plan': None, 'plan_id': None,
                            'interpreter': 'deterministic'}
                    if stub.f['bad_contract']:
                        body.pop('interpreter')
                    return self._send(200, body)
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
    def run_stub(self, expect_sha=SHA, bypass=None, stub=None, **kw):
        faults = {k: v for k, v in kw.items() if k not in ('trusted_observed_sha', 'allow_production_writes', 'timeout')}
        opts = {k: v for k, v in kw.items() if k in ('trusted_observed_sha', 'allow_production_writes', 'timeout')}
        stub = stub or _Stub(**faults)
        try:
            return dv.verify(stub.url, expect_sha=expect_sha, bypass=bypass, **opts)
        finally:
            stub.close()

    def status(self, result, name):
        return next(c['status'] for c in result['checks'] if c['check'] == name)

    def ev(self, result, name):
        return next(c for c in result['checks'] if c['check'] == name)['evidence']

    def assert_not_promotable(self, r):
        self.assertNotIn(r['verdict'], vc.PROMOTABLE)
        self.assertFalse(promote(r, req=vc.DEPLOYMENT_REQUIRED_CHECKS, commit_sha=SHA)[0])

    # --- journey and acceptance scenarios ---------------------------------
    def test_healthy_deployment_is_verified_and_promotable(self):
        r = self.run_stub()
        self.assertEqual(r['verdict'], vc.VERIFIED, r['reason'])
        self.assertEqual(r['commit_sha'], SHA)
        self.assertEqual([c['check'] for c in r['checks']], list(dv.REQUIRED_CHECKS))
        self.assertTrue(promote(r, req=vc.DEPLOYMENT_REQUIRED_CHECKS, commit_sha=SHA)[0])

    def test_scenario_a_conversation_500_is_linked_to_the_deployed_commit(self):
        r = self.run_stub(conversation_status=500)
        self.assertEqual(r['verdict'], vc.FAILED)
        self.assertEqual(self.status(r, 'conversation_turn'), vc.FAIL)
        self.assertEqual(r['commit_sha'], SHA)
        self.assertEqual(self.ev(r, 'conversation_turn'), {'status': 500, 'error_class': 'HTTP_500'})
        self.assert_not_promotable(r)

    def test_scenario_e_schema_mismatch_blocks_promotion(self):
        r = self.run_stub(compatible=False, conversation_status=503)
        self.assertEqual(r['verdict'], vc.FAILED)
        self.assertEqual(self.status(r, 'schema_compatible'), vc.FAIL)
        self.assertEqual(self.ev(r, 'schema_compatible')['missing'], [36])
        self.assertNotIn('note', self.ev(r, 'schema_compatible'))            # server free text never copied
        self.assertEqual(self.ev(r, 'conversation_turn')['error_class'], 'MIGRATION_NOT_APPLIED')
        self.assertEqual(self.ev(r, 'conversation_turn')['missing_migration'], '036_intelligence_plane')
        self.assertNotIn('message', self.ev(r, 'conversation_turn'))
        self.assertIn('schema_compatible', r['summary']['critical_blockers'])

    def test_scenario_j_green_locally_but_wrong_build_deployed(self):
        r = self.run_stub(sha='feedfacefeedfacefeedfacefeedfacefeedface')
        self.assertEqual(r['verdict'], vc.FAILED)
        self.assertEqual(self.status(r, 'commit_sha'), vc.FAIL)

    # --- SHA handling -------------------------------------------------------
    def test_sha_must_be_full_and_well_formed(self):
        for bad in ('0123456', 'zz' * 20, SHA + '0', ''):
            with self.assertRaises(dv.TargetError):
                dv.verify('http://127.0.0.1:9', expect_sha=bad or 'x')
        with self.assertRaises(dv.TargetError):
            dv.verify('http://127.0.0.1:9', expect_sha=SHA, trusted_observed_sha='abc')

    def test_trusted_metadata_disagreeing_with_expected_sha_fails(self):
        r = self.run_stub(trusted_observed_sha='f' * 40)
        self.assertEqual(self.status(r, 'commit_sha'), vc.FAIL)
        self.assertEqual(self.run_stub(trusted_observed_sha=SHA)['verdict'], vc.VERIFIED)

    def test_deployment_without_sha_or_without_expectation_is_blocked(self):
        r = self.run_stub(expect_sha=None)
        self.assertEqual(r['verdict'], vc.BLOCKED)
        self.assertEqual(self.status(r, 'commit_sha'), vc.NOT_RUN)
        r = self.run_stub(sha=None)
        self.assertEqual(r['verdict'], vc.BLOCKED)
        r = self.run_stub(sha='not-a-sha')
        self.assertEqual(self.status(r, 'commit_sha'), vc.NOT_RUN)
        self.assert_not_promotable(r)

    # --- access control and credentials -----------------------------------
    def test_pr9_contracts_session_identity_and_conversation_shape(self):
        r = self.run_stub(me_wrong_user=True)                       # session resolves to someone else
        self.assertEqual((r['verdict'], self.status(r, 'session_identity')), (vc.FAILED, vc.FAIL))
        r = self.run_stub(bad_contract=True)                        # 200 with a broken response shape
        self.assertEqual((r['verdict'], self.status(r, 'conversation_persists')), (vc.FAILED, vc.FAIL))
        self.assertFalse(self.ev(r, 'conversation_persists')['contract_ok'])

    def test_cross_user_exposure_and_auth_bypass_fail(self):
        self.assertEqual(self.status(self.run_stub(leak=True), 'cross_user_isolation'), vc.FAIL)
        self.assertEqual(self.status(self.run_stub(anon_ok=True), 'unauthenticated_denied'), vc.FAIL)

    def test_wrong_credentials(self):
        r = self.run_stub(protected=True, bypass='wrong-bypass')
        self.assertEqual(r['verdict'], vc.BLOCKED)
        self.assertIn('bypass token rejected', r['checks'][0]['reason'])
        r = self.run_stub(no_token=True)                       # register answers without a session token
        self.assertEqual((r['verdict'], self.status(r, 'register_synthetic_user')), (vc.FAILED, vc.FAIL))
        r = self.run_stub(reject_tokens=True)                  # token issued but not accepted
        self.assertEqual(self.ev(r, 'create_project')['error_class'], 'AUTH_INVALID')
        self.assertEqual(r['verdict'], vc.FAILED)

    def test_protected_or_unreachable_is_blocked_never_verified(self):
        prot = self.run_stub(protected=True)
        self.assertEqual(prot['verdict'], vc.BLOCKED)
        self.assertIn('protected (HTTP 401)', prot['summary']['skipped'][0]['reason'])
        self.assertEqual(self.run_stub(protected=True, bypass='synthetic-bypass')['verdict'], vc.VERIFIED)
        r = dv.verify('http://127.0.0.1:9', expect_sha=SHA)
        self.assertEqual(r['verdict'], vc.BLOCKED)
        self.assertEqual(r['checks'][0]['evidence']['error_class'], 'CONNECTION_FAILURE')

    def test_production_writes_refused_without_explicit_approval(self):
        r = self.run_stub(env='production')
        self.assertEqual(r['verdict'], vc.BLOCKED)
        reason = next(c['reason'] for c in r['checks'] if c['check'] == 'register_synthetic_user')
        self.assertIn('allow-production-writes', reason)
        self.assertEqual(self.run_stub(env='production', allow_production_writes=True)['verdict'], vc.VERIFIED)

    # --- every mandatory check accounted for -------------------------------
    def test_unreached_mandatory_checks_are_reported_not_run_and_block(self):
        r = self.run_stub(protected=True)
        self.assertEqual([c['check'] for c in r['checks']], list(dv.REQUIRED_CHECKS))
        self.assertTrue(all(c['status'] == vc.NOT_RUN and c['reason'] for c in r['checks']))
        r = self.run_stub(no_token=True)
        later = [c for c in r['checks'] if dv.REQUIRED_CHECKS.index(c['check']) > 3]
        self.assertTrue(later and all(c['status'] == vc.NOT_RUN for c in later))
        self.assertTrue(all('not reached: register_synthetic_user FAIL' in c['reason'] for c in later))

    def test_contract_blocks_when_a_required_check_is_missing_or_optional(self):
        passing = [C(n, vc.PASS) for n in dv.REQUIRED_CHECKS]
        self.assertEqual(vc.decide(passing, dv.REQUIRED_CHECKS)[0], vc.VERIFIED)
        self.assertEqual(vc.decide(passing[:-1], dv.REQUIRED_CHECKS)[0], vc.BLOCKED)
        downgraded = passing[:-1] + [C(dv.REQUIRED_CHECKS[-1], vc.FAIL, mandatory=False)]
        self.assertEqual(vc.decide(downgraded, dv.REQUIRED_CHECKS)[0], vc.BLOCKED)

    # --- network failures ---------------------------------------------------
    def test_network_failures_mid_journey_produce_a_result_not_a_crash(self):
        r = self.run_stub(drop_on='conversation')
        self.assertEqual(r['verdict'], vc.FAILED)
        self.assertEqual(self.ev(r, 'conversation_turn')['error_class'], 'CONNECTION_FAILURE')
        r = self.run_stub(sleep_on='memory', timeout=0.5)
        self.assertEqual(self.ev(r, 'project_memory')['error_class'], 'TIMEOUT')
        self.assertEqual(r['verdict'], vc.FAILED)

    def test_oversized_and_non_json_responses_fail(self):
        r = self.run_stub(huge_on='deployment')
        self.assertEqual((r['verdict'], self.ev(r, 'deployment_endpoint')['error_class']), (vc.FAILED, 'RESPONSE_TOO_LARGE'))
        r = self.run_stub(html_on='memory')
        self.assertEqual(self.ev(r, 'project_memory')['error_class'], 'INVALID_JSON')

    def test_unresolvable_or_private_targets_are_blocked(self):
        from unittest import mock
        origin = dv.validate_target('https://app-shayflys-projects.vercel.app', allowed_suffixes=('-shayflys-projects.vercel.app',))
        with mock.patch.object(dv.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('10.0.0.5', 443))]):
            self.assertEqual(dv.resolve_public(origin), (False, 'NON_PUBLIC_ADDRESS'))
        with mock.patch.object(dv.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('169.254.169.254', 443))]):
            r = dv.verify('https://app-shayflys-projects.vercel.app', expect_sha=SHA,
                          allowed_suffixes=('-shayflys-projects.vercel.app',))
        self.assertEqual((r['verdict'], r['checks'][0]['evidence']['error_class']), (vc.BLOCKED, 'NON_PUBLIC_ADDRESS'))
        with mock.patch.object(dv.socket, 'getaddrinfo', side_effect=dv.socket.gaierror('nx')):
            self.assertEqual(dv.resolve_public(origin), (False, 'DNS_FAILURE'))
        with mock.patch.object(dv.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('76.76.21.21', 443))]):
            self.assertEqual(dv.resolve_public(origin), (True, 'NONE'))

    # --- attacks: redirects, cookies, injection, token leakage --------------
    def test_cross_origin_redirect_never_receives_secrets(self):
        evil = _Stub()
        try:
            r = self.run_stub(bypass='synthetic-bypass', redirect_to=evil.url)
        finally:
            evil.close()
        self.assertEqual(evil.seen, [])                                       # nothing reached the other origin
        self.assertEqual((r['verdict'], self.ev(r, 'deployment_endpoint')['error_class']), (vc.BLOCKED, 'REDIRECT_BLOCKED'))
        self.assertIn('not followed', r['checks'][0]['reason'])

    def test_redirect_after_login_does_not_forward_the_bearer_token(self):
        evil = _Stub()
        victim = _Stub(redirect_to=evil.url, redirect_path='/api/v28/projects')
        try:
            r = self.run_stub(stub=victim, bypass='synthetic-bypass')
        finally:
            evil.close()
        self.assertEqual(evil.seen, [])
        self.assertEqual(self.ev(r, 'create_project')['error_class'], 'REDIRECT_BLOCKED')
        self.assertEqual(r['verdict'], vc.FAILED)

    def test_same_origin_redirect_is_not_followed(self):
        stub = _Stub()
        stub.f['redirect_to'] = stub.url
        stub.f['redirect_path'] = '/api/v28/deployment'
        r = self.run_stub(stub=stub)
        self.assertEqual(self.ev(r, 'deployment_endpoint')['error_class'], 'REDIRECT_BLOCKED')
        self.assertEqual(len([s for s in stub.seen if s['path'] == '/api/v28/deployment']), 1)

    def test_cookies_are_never_stored_or_sent(self):
        stub = _Stub(set_cookie=True)
        r = self.run_stub(stub=stub)
        self.assertEqual(r['verdict'], vc.VERIFIED)
        self.assertTrue(all(s['cookie'] is None for s in stub.seen))

    def test_secrets_only_go_to_the_target_and_never_into_evidence(self):
        stub = _Stub(protected=True, conversation_status=500, echo_auth=True)
        r = self.run_stub(stub=stub, bypass='synthetic-bypass')
        text = json.dumps(r)
        self.assertNotIn('synthetic-bypass', text)
        self.assertNotIn('sess-', text)                                       # session tokens
        self.assertNotIn('Bearer', text)                                      # echoed Authorization header
        self.assertTrue(all(s['bypass'] == 'synthetic-bypass' for s in stub.seen))
        anon = [s for s in stub.seen if s['auth'] is None and '/projects/' in s['path']]
        self.assertTrue(anon)                                                 # anonymous probe really anonymous

    def test_scrub_is_a_last_line_of_defence(self):
        self.assertEqual(dv._scrub({'a': 'x-secret-y'}, ['secret']), {'a': 'x-[REDACTED]-y'})

    def test_server_controlled_project_id_cannot_steer_requests(self):
        stub = _Stub(project_id='../../admin')
        r = self.run_stub(stub=stub)
        self.assertEqual(self.ev(r, 'create_project')['error_class'], 'INVALID_RESPONSE_CONTRACT')
        self.assertFalse(any('admin' in s['path'] for s in stub.seen))
        self.assertEqual(r['verdict'], vc.FAILED)

    def test_target_validation_rejects_ssrf_shapes(self):
        ok_suffix = ('-shayflys-projects.vercel.app',)
        bad = ['http://example.com', 'https://example.com', 'file:///etc/passwd', 'ftp://127.0.0.1:21',
               'https://user:pw@x-shayflys-projects.vercel.app', 'https://x-shayflys-projects.vercel.app/path',
               'https://x-shayflys-projects.vercel.app?q=1', 'https://x-shayflys-projects.vercel.app#f',
               'https://10.0.0.1', 'https://169.254.169.254', 'https://[::ffff:10.0.0.1]', 'http://localhost',
               'http://127.0.0.1:0', 'https://x-shayflys-projects.vercel.app\n', ' https://a', '',
               'https://shayflys-projects.vercel.app', 'https://evilshayflys-projects.vercel.app.attacker.com',
               'https://x-shayflys-projects.vercel.app@evil.com']
        for url in bad:
            with self.subTest(url=url), self.assertRaises(dv.TargetError):
                dv.validate_target(url, allowed_suffixes=ok_suffix)
        for suffix in ('vercel.app', 'shayflys-projects.vercel.app', '-', '.'):
            with self.subTest(suffix=suffix), self.assertRaises(dv.TargetError):
                dv.validate_target('https://a-shayflys-projects.vercel.app', allowed_suffixes=(suffix,))
        self.assertEqual(dv.validate_target('https://ABC-shayflys-projects.vercel.app/', allowed_suffixes=ok_suffix),
                         'https://abc-shayflys-projects.vercel.app')
        self.assertEqual(dv.validate_target('https://exact.example.org', allowed_hosts=('exact.example.org',)),
                         'https://exact.example.org')
        self.assertEqual(dv.validate_target('http://127.0.0.1:8148'), 'http://127.0.0.1:8148')
        with self.assertRaises(ValueError):
            dv.Client('http://127.0.0.1:1', None).call('GET', '//evil.com/x')

    def test_unsafe_resource_limits_rejected(self):
        for kw in ({'timeout': 0}, {'timeout': 61}, {'deadline_seconds': 0}, {'deadline_seconds': 601}):
            with self.subTest(**kw), self.assertRaises(dv.TargetError):
                dv.verify('http://127.0.0.1:9', expect_sha=SHA, **kw)

    # --- CLI ------------------------------------------------------------------
    def test_cli_exit_codes_and_config_error_evidence(self):
        import contextlib
        import io
        import tempfile
        stub = _Stub()
        try:
            with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                out = os.path.join(d, 'r.json')
                self.assertEqual(dv.main([stub.url, '--expect-sha', SHA, '--out', out]), 0)
                self.assertEqual(json.load(open(out))['verdict'], vc.VERIFIED)
                self.assertEqual(dv.main([stub.url, '--out', out]), 2)                       # no SHA -> BLOCKED
                stub.f['conversation_status'] = 500
                self.assertEqual(dv.main([stub.url, '--expect-sha', SHA]), 1)               # FAILED
                self.assertEqual(dv.main(['https://evil.example', '--expect-sha', SHA, '--out', out]), 3)
                bad = json.load(open(out))
                self.assertEqual((bad['verdict'], bad['target']), (vc.BLOCKED, '(rejected)'))
                self.assertEqual(dv.main([stub.url, '--bypass-token-env', 'X;rm -rf /']), 3)
                # real-run regression (run 38120874664): a dash-leading suffix as a separate argv
                # made argparse exit before writing any result
                os.remove(out)
                self.assertEqual(dv.main(['https://a-shayflys-projects.vercel.app', '--expect-sha', SHA,
                                          '--allowed-host-suffix', '-shayflys-projects.vercel.app', '--out', out]), 3)
                self.assertEqual(json.load(open(out))['verdict'], vc.BLOCKED)
                from unittest import mock
                with mock.patch.object(dv.socket, 'getaddrinfo', side_effect=dv.socket.gaierror('offline')):
                    self.assertEqual(dv.main(['https://a-shayflys-projects.vercel.app', '--expect-sha', SHA,
                                              '--allowed-host-suffix=-shayflys-projects.vercel.app', '--out', out]), 2)
                self.assertEqual(json.load(open(out))['checks'][0]['evidence']['error_class'], 'DNS_FAILURE')
        finally:
            stub.close()


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
