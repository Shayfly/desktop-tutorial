"""Post-deployment verification of a running 148AI deployment (Continuous
Verification Engine P0.4 — the layer whose absence let a READY Vercel Preview
answer the conversation with HTTP 500 on 2026-10-11).

    python tools/deployment_verify.py https://<deployment> [--expect-sha <sha>] [--bypass-token-env NAME] [--out result.json]

Real HTTP against the real deployment, synthetic users only (never customer
data), $0 (no build, no model call). Checks, in order:
  1 deployment identity: commit SHA (vs --expect-sha), environment
  2 schema compatibility: migrations expected by the code vs applied in the database
  3 authenticated journey: register -> create project -> conversation turn ->
    conversation persists on re-read -> structured project memory
  4 access control: anonymous request denied; a second synthetic user cannot
    read the first user's conversation
Output is a canonical verification-result/1 (omni_prod/verification_contract):
FAILED on any failed check (promotion must stop); BLOCKED when the deployment
cannot be reached, is protected without a bypass token, or no --expect-sha
binds the evidence to a commit. Never VERIFIED by default. Exit code 0 only
for a promotable verdict.
The bypass token (Vercel "Protection Bypass for Automation") is read from an
environment variable and is never printed.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from omni_prod.verification_contract import (  # noqa: E402
    FAIL, NOT_RUN, PASS, PROMOTABLE, CheckResult, VerificationResult)

SUITE_VERSION = 'deployment-verify/2'


class Client:
    def __init__(self, base: str, bypass: str | None):
        self.base = base.rstrip('/')
        self.bypass = bypass
        self.token: str | None = None
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def call(self, method: str, path: str, body=None):
        headers = {'Accept': 'application/json', 'Origin': self.base}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if self.bypass:
            headers['x-vercel-protection-bypass'] = self.bypass
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        req = urllib.request.Request(self.base + path, method=method, headers=headers,
                                     data=None if body is None else json.dumps(body).encode())
        try:
            with self.opener.open(req, timeout=30) as r:
                data = _json(r.read().decode('utf-8', 'replace'))
                if isinstance(data, dict) and isinstance(data.get('token'), str) and path.endswith('/auth/register'):
                    self.token = data['token']   # kept in memory only, never printed
                return r.status, data
        except urllib.error.HTTPError as e:
            return e.code, _json(e.read().decode('utf-8', 'replace'))


def _json(raw):
    try:
        return json.loads(raw)
    except ValueError:
        return {'_text': raw[:300]}


def verify(base: str, *, expect_sha: str | None = None, bypass: str | None = None) -> dict:
    checks: list[CheckResult] = []
    meta = {'environment': 'unknown', 'commit_sha': None}

    def check(name, ok, evidence, category, mandatory=True):
        checks.append(CheckResult(check=name, status=PASS if ok else FAIL, mandatory=mandatory,
                                  category=category, evidence=evidence))
        return ok

    def skip(name, category, reason):
        checks.append(CheckResult(check=name, status=NOT_RUN, category=category, reason=reason))

    def result():
        return VerificationResult(kind='deployment', target=base, environment=meta['environment'],
                                  commit_sha=meta['commit_sha'], checks=checks,
                                  suites={'deployment_verify': SUITE_VERSION}).finish().to_dict()

    a = Client(base, bypass)
    try:
        st, dep = a.call('GET', '/api/v28/deployment')
    except Exception as exc:  # DNS, TLS, refused
        skip('deployment_endpoint', 'startup', f'unreachable: {type(exc).__name__}')
        return result()
    if st in (401, 403) and '_text' in (dep or {'_text': ''}):
        skip('deployment_endpoint', 'startup', 'deployment is protected; provide a bypass token via --bypass-token-env')
        return result()
    if not check('deployment_endpoint', st == 200, {'status': st}, 'startup'):
        return result()
    meta['environment'] = dep.get('environment') or 'unknown'
    meta['commit_sha'] = sha = dep.get('source_commit')
    if expect_sha:
        check('commit_sha', (sha or '').startswith(expect_sha),
              {'source_commit': sha, 'expected': expect_sha, 'branch': dep.get('branch')}, 'deployment_identity')
    else:
        skip('commit_sha', 'deployment_identity', 'no --expect-sha given')
    schema = dep.get('schema') or {}
    check('schema_compatible', bool(schema.get('compatible')), schema, 'migration_compatibility')

    email = f'verify-{uuid.uuid4().hex[:10]}@example.com'
    st, _ = a.call('POST', '/api/v28/auth/register', {'email': email, 'password': 'synthetic-' + uuid.uuid4().hex[:12]})
    if not check('register_synthetic_user', st in (200, 201), {'status': st}, 'critical_api'):
        return result()
    st, proj = a.call('POST', '/api/v28/projects', {'title': 'deployment verification'})
    pid = (proj or {}).get('id')
    if not check('create_project', st in (200, 201) and bool(pid), {'status': st}, 'core_journey'):
        return result()
    st, turn = a.call('POST', f'/api/v28/projects/{pid}/conversation?lang=en',
                      {'message': 'An internal tool for my team to track equipment loans, in English, no login',
                       'request_key': uuid.uuid4().hex})
    reply = ((turn or {}).get('turn') or {}).get('reply')
    check('conversation_turn', st == 200 and bool(reply), {'status': st, 'error': (turn or {}).get('detail')},
          'core_journey')
    st, conv = a.call('GET', f'/api/v28/projects/{pid}/conversation?lang=en')
    n = len((conv or {}).get('messages') or [])
    check('conversation_persists', st == 200 and n >= 2, {'status': st, 'messages': n}, 'data_integrity')
    st, mem = a.call('GET', f'/api/v28/projects/{pid}/memory')
    check('project_memory', st == 200 and (mem or {}).get('schema') == 'project-memory/1', {'status': st},
          'core_journey')
    anon = Client(base, bypass)
    st, _ = anon.call('GET', f'/api/v28/projects/{pid}/conversation')
    check('unauthenticated_denied', st in (401, 403), {'status': st}, 'auth_bypass')
    b = Client(base, bypass)
    sb, _ = b.call('POST', '/api/v28/auth/register', {'email': f'verify-{uuid.uuid4().hex[:10]}@example.com',
                                                      'password': 'synthetic-' + uuid.uuid4().hex[:12]})
    st, _ = b.call('GET', f'/api/v28/projects/{pid}/conversation')
    check('cross_user_isolation', sb in (200, 201) and st in (403, 404), {'other_user_status': st},
          'cross_user_exposure')
    return result()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='deployment_verify')
    ap.add_argument('base')
    ap.add_argument('--expect-sha')
    ap.add_argument('--bypass-token-env')
    ap.add_argument('--out')
    args = ap.parse_args(argv)
    bypass = os.getenv(args.bypass_token_env) if args.bypass_token_env else None
    result = verify(args.base, expect_sha=args.expect_sha, bypass=bypass)
    text = json.dumps(result, indent=1, ensure_ascii=False)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
    print(text)
    return 0 if result['verdict'] in PROMOTABLE else 1


if __name__ == '__main__':
    sys.exit(main())
