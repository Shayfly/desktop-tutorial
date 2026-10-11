"""Post-deployment verification of a running 148AI deployment (Continuous
Verification P0.4 — the layer whose absence let a READY Vercel Preview answer
the conversation with HTTP 500 on 2026-10-11).

    python tools/deployment_verify.py https://<deployment> --expect-sha <40-hex> \
        --allowed-host-suffix=-shayflys-projects.vercel.app \
        [--trusted-observed-sha <40-hex>] [--bypass-token-env NAME] [--out result.json]

Real HTTP against the real deployment, synthetic users only (never customer
data), $0 (no build, no model call). Checks (all mandatory, always reported):
  deployment_endpoint, commit_sha, schema_compatible, register_synthetic_user,
  session_identity, create_project, conversation_turn, conversation_persists, project_memory,
  unauthenticated_denied, cross_user_isolation
Output: canonical verification-result/1 (omni_prod/verification_contract).
A mandatory check that did not run is NOT_RUN with a reason and makes the
verdict BLOCKED; a failed one makes it FAILED. Never VERIFIED by default.
Exit codes: 0 promotable, 1 FAILED, 2 BLOCKED, 3 configuration error.

Security model (review 2026-10-11, incorporates PR #9 / PDV-001 hardening):
  * target = origin only (no path/query/fragment/credentials); https required
    except loopback; IP literals other than loopback refused; non-loopback
    hosts must match --allowed-host (exact) or --allowed-host-suffix
    (must start with "-" or "."); the host must resolve to public addresses
    only (refuses private/link-local/metadata targets; DNS rebinding between
    this check and the connection remains a residual risk)
  * redirects are never followed (same-origin included), so the bearer token
    and the bypass secret are only ever sent to the validated origin
  * no cookie jar, no environment proxies, TLS verification on, bounded
    response size, per-request timeout and an overall deadline
  * evidence contains status codes and whitelisted error codes only, never
    response bodies, tokens or the bypass secret (final scrub enforces it)
  * writes (synthetic register/project/conversation) are refused when the
    deployment reports environment "production" unless
    --allow-production-writes is given (founder-approved runs only)
  * commit evidence: the app reports VERCEL_GIT_COMMIT_SHA; when a trusted
    deployment-system SHA (--trusted-observed-sha) is given it must agree too
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from omni_prod.verification_contract import (  # noqa: E402
    DEPLOYMENT_REQUIRED_CHECKS, FAIL, FAILED, NOT_RUN, PASS, PROMOTABLE, CheckResult, VerificationResult)

SUITE_VERSION = 'deployment-verify/3'
REQUIRED_CHECKS = DEPLOYMENT_REQUIRED_CHECKS
CATEGORY = {'deployment_endpoint': 'startup', 'commit_sha': 'deployment_identity',
            'schema_compatible': 'migration_compatibility', 'register_synthetic_user': 'critical_api',
            'session_identity': 'auth_bypass',
            'create_project': 'core_journey', 'conversation_turn': 'core_journey',
            'conversation_persists': 'data_integrity', 'project_memory': 'core_journey',
            'unauthenticated_denied': 'auth_bypass', 'cross_user_isolation': 'cross_user_exposure'}
MAX_BYTES = 1_048_576
SHA_RE = re.compile(r'[0-9a-f]{40}')
ID_RE = re.compile(r'[A-Za-z0-9_-]{1,128}')
CODE_RE = re.compile(r'[a-z0-9_]{1,80}')


class TargetError(ValueError):
    """The target or the configuration is not acceptable (exit code 3)."""


# ---------------------------------------------------------------- target ----

def _is_loopback(host: str) -> bool:
    if host.lower() == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_target(url: str, *, allowed_hosts=(), allowed_suffixes=()) -> str:
    """Return the normalized origin or raise TargetError. Syntax + allowlist only."""
    if not isinstance(url, str) or not url or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url):
        raise TargetError('invalid deployment URL')
    try:
        p = urllib.parse.urlsplit(url)
        host, port = p.hostname, p.port
    except ValueError as exc:
        raise TargetError('invalid deployment URL') from exc
    if p.scheme not in ('http', 'https') or not host:
        raise TargetError('deployment URL must be http(s) with a host')
    if p.username is not None or p.password is not None or '@' in p.netloc:
        raise TargetError('embedded credentials are not allowed')
    if p.path not in ('', '/') or p.query or p.fragment or url.rstrip('/').endswith('?') or '#' in url:
        raise TargetError('deployment URL must be an origin without path, query or fragment')
    if port == 0:
        raise TargetError('invalid port')
    loopback = _is_loopback(host)
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and not loopback:
        raise TargetError('IP literal targets other than loopback are forbidden')
    if not loopback:
        if p.scheme != 'https':
            raise TargetError('https is required for non-loopback deployments')
        for s in allowed_suffixes:
            if not (s.startswith('-') or s.startswith('.')) or '.' not in s.strip('.-'):
                raise TargetError(f'unsafe host suffix {s!r} (must start with "-" or "." and contain a domain)')
        h = host.lower().rstrip('.')
        exact = {x.lower().rstrip('.') for x in allowed_hosts}
        if h not in exact and not any(h.endswith(s.lower()) and len(h) > len(s) for s in allowed_suffixes):
            raise TargetError('deployment host is not in the allowed hosts')
    elif p.scheme == 'http' and port is None:
        raise TargetError('specify a port for local http testing')
    return f'{p.scheme}://{p.netloc.lower()}'


def resolve_public(origin: str) -> tuple[bool, str]:
    """(ok, error_class). Loopback origins pass; others must resolve to public addresses only."""
    host = urllib.parse.urlsplit(origin).hostname or ''
    if _is_loopback(host):
        return True, 'NONE'
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError, OSError):
        return False, 'DNS_FAILURE'
    for info in infos:
        addr = ipaddress.ip_address(info[4][0].split('%')[0])
        if not addr.is_global or addr.is_multicast:
            return False, 'NON_PUBLIC_ADDRESS'
    return (True, 'NONE') if infos else (False, 'DNS_FAILURE')


# ------------------------------------------------------------------ http ----

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow redirects (same-origin included): secrets stay on the validated origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


@dataclass(frozen=True)
class Outcome:
    status: int | None
    data: Any
    error: str          # NONE, REDIRECT_BLOCKED, TIMEOUT, DNS_FAILURE, TLS_FAILURE, CONNECTION_FAILURE,
                        # RESPONSE_TOO_LARGE, INVALID_JSON, DEADLINE_EXCEEDED


class Client:
    def __init__(self, origin: str, bypass: str | None, *, timeout: float = 15.0, deadline: float | None = None):
        self.origin = origin
        self.bypass = bypass
        self.token: str | None = None
        self.email: str | None = None
        self.timeout = timeout
        self.deadline = deadline
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        self.opener.addheaders = [('User-Agent', '148AI-deployment-verify/3')]

    def call(self, method: str, path: str, body=None) -> Outcome:
        if not path.startswith('/') or path.startswith('//') or any(c in path for c in '\\#\r\n '):
            raise ValueError('unsafe request path')
        if self.deadline is not None and time.monotonic() > self.deadline:
            return Outcome(None, None, 'DEADLINE_EXCEEDED')
        headers = {'Accept': 'application/json', 'Origin': self.origin}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        # Secrets are attached only here, to a URL built from the validated origin; redirects are not followed.
        if self.bypass:
            headers['x-vercel-protection-bypass'] = self.bypass
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        req = urllib.request.Request(self.origin + path, method=method, headers=headers,
                                     data=None if body is None else json.dumps(body).encode())
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                return self._read(r, r.status)
        except urllib.error.HTTPError as e:
            with e:
                return self._read(e, e.code)
        except (TimeoutError, socket.timeout):
            return Outcome(None, None, 'TIMEOUT')
        except ssl.SSLError:
            return Outcome(None, None, 'TLS_FAILURE')
        except urllib.error.URLError as e:
            r = e.reason
            if isinstance(r, (TimeoutError, socket.timeout)):
                return Outcome(None, None, 'TIMEOUT')
            if isinstance(r, socket.gaierror):
                return Outcome(None, None, 'DNS_FAILURE')
            if isinstance(r, ssl.SSLError):
                return Outcome(None, None, 'TLS_FAILURE')
            return Outcome(None, None, 'CONNECTION_FAILURE')
        except (OSError, ValueError):   # reset, remote closed, http.client protocol errors
            return Outcome(None, None, 'CONNECTION_FAILURE')

    def _read(self, resp, status: int) -> Outcome:
        if 300 <= status < 400:
            return Outcome(status, None, 'REDIRECT_BLOCKED')
        raw = resp.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return Outcome(status, None, 'RESPONSE_TOO_LARGE')
        try:
            data = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            return Outcome(status, None, 'INVALID_JSON' if 200 <= status < 300 else 'NONE')
        return Outcome(status, data, 'NONE')

    def register(self) -> Outcome:
        self.email = f'verify-{uuid.uuid4().hex[:10]}@example.com'
        out = self.call('POST', '/api/v28/auth/register', {'email': self.email,
                                                           'password': 'synthetic-' + uuid.uuid4().hex[:16]})
        tok = out.data.get('token') if isinstance(out.data, dict) else None
        if out.status in (200, 201) and isinstance(tok, str) and 0 < len(tok) <= 4096 and tok.isprintable():
            self.token = tok    # memory only, never printed or written
        return out


# ------------------------------------------------------------- evidence ----

def _error_code(data) -> dict:
    """Whitelisted application error code from a FastAPI body; never free text."""
    detail = data.get('detail') if isinstance(data, dict) else None
    detail = detail if isinstance(detail, dict) else (data if isinstance(data, dict) else {})
    out = {}
    for key in ('error', 'missing_migration'):
        v = detail.get(key)
        if isinstance(v, str) and CODE_RE.fullmatch(v):
            out[key] = v
    return out


def _http_evidence(o: Outcome) -> dict:
    ev = {'status': o.status, 'error_class': o.error if o.error != 'NONE' else _status_class(o)}
    ev.update(_error_code(o.data))
    if ev.get('error') == 'conversation_not_ready':
        ev['error_class'] = 'MIGRATION_NOT_APPLIED'
    return ev


def _status_class(o: Outcome) -> str:
    if o.status is None or 200 <= o.status < 300:
        return 'NONE'
    return {401: 'AUTH_INVALID', 403: 'HTTP_403', 404: 'HTTP_404', 500: 'HTTP_500', 502: 'HTTP_502',
            503: 'HTTP_503', 504: 'HTTP_504'}.get(o.status, 'HTTP_OTHER')


def _schema_evidence(schema) -> dict:
    if not isinstance(schema, dict):
        return {'error_class': 'INVALID_RESPONSE_CONTRACT'}
    ev = {k: schema.get(k) for k in ('required', 'applied_max') if isinstance(schema.get(k), int)}
    for k in ('status', 'required_name'):
        if isinstance(schema.get(k), str) and re.fullmatch(r'[A-Za-z0-9_]{1,64}', schema[k]):
            ev[k] = schema[k]
    if isinstance(schema.get('missing'), list):
        ev['missing'] = [v for v in schema['missing'] if isinstance(v, int)][:50]
    ev['compatible'] = schema.get('compatible') is True
    return ev


def _scrub(obj, secrets: list[str]):
    text = json.dumps(obj)
    for s in secrets:
        if s and s in text:
            text = text.replace(json.dumps(s)[1:-1], '[REDACTED]')
    return json.loads(text)


# ---------------------------------------------------------------- verify ----

def verify(base: str, *, expect_sha: str | None = None, bypass: str | None = None, allowed_hosts=(),
           allowed_suffixes=(), trusted_observed_sha: str | None = None, allow_production_writes: bool = False,
           timeout: float = 15.0, deadline_seconds: float = 120.0) -> dict:
    """Run the checks. Raises TargetError on an unacceptable target/configuration."""
    origin = validate_target(base, allowed_hosts=allowed_hosts, allowed_suffixes=allowed_suffixes)
    for name, sha in (('expect-sha', expect_sha), ('trusted-observed-sha', trusted_observed_sha)):
        if sha is not None and not SHA_RE.fullmatch(sha.lower()):
            raise TargetError(f'--{name} must be a full 40-character commit SHA')
    expect_sha = expect_sha.lower() if expect_sha else None
    trusted_observed_sha = trusted_observed_sha.lower() if trusted_observed_sha else None
    if not 0 < timeout <= 60 or not 0 < deadline_seconds <= 600:
        raise TargetError('unsafe timeout')

    checks: list[CheckResult] = []
    meta = {'environment': 'unknown', 'commit_sha': None}
    clients: list[Client] = []
    deadline = time.monotonic() + deadline_seconds

    def check(name, ok, evidence):
        checks.append(CheckResult(check=name, status=PASS if ok else FAIL, category=CATEGORY[name], evidence=evidence))
        return ok

    def skip(name, reason, evidence=None):
        checks.append(CheckResult(check=name, status=NOT_RUN, category=CATEGORY[name], reason=reason,
                                  evidence=evidence or {}))

    def client():
        c = Client(origin, bypass, timeout=timeout, deadline=deadline)
        clients.append(c)
        return c

    def result():
        done = {c.check for c in checks}
        first = next((c for c in checks if c.status != PASS), None)
        why = f'not reached: {first.check} {first.status}' if first else 'not reached'
        for name in REQUIRED_CHECKS:
            if name not in done:
                skip(name, why)
        order = {n: i for i, n in enumerate(REQUIRED_CHECKS)}
        checks.sort(key=lambda c: order.get(c.check, 99))
        r = VerificationResult(kind='deployment', target=origin, environment=meta['environment'],
                               commit_sha=meta['commit_sha'], checks=checks, required=REQUIRED_CHECKS,
                               suites={'deployment_verify': SUITE_VERSION}).finish().to_dict()
        return _scrub(r, [bypass or ''] + [c.token or '' for c in clients])

    ok, err = resolve_public(origin)
    if not ok:
        skip('deployment_endpoint', f'target not reachable safely: {err}', {'error_class': err})
        return result()
    a = client()
    o = a.call('GET', '/api/v28/deployment')
    if o.status is None:
        skip('deployment_endpoint', f'unreachable: {o.error}', {'error_class': o.error})
        return result()
    if o.error == 'REDIRECT_BLOCKED':   # e.g. platform SSO; never followed, so not proof of a broken app
        skip('deployment_endpoint', f'redirect (HTTP {o.status}) not followed: target or platform protection '
             'must answer directly', {'status': o.status, 'error_class': 'REDIRECT_BLOCKED'})
        return result()
    if o.status in (401, 403):
        # /api/v28/deployment is public in the app, so 401/403 is platform protection
        skip('deployment_endpoint', 'deployment is protected (HTTP %d); %s' % (
            o.status, 'bypass token rejected' if bypass else 'provide a bypass token via --bypass-token-env'),
            {'status': o.status, 'error_class': 'PROTECTED'})
        return result()
    dep = o.data if isinstance(o.data, dict) else None
    if not check('deployment_endpoint', o.status == 200 and o.error == 'NONE' and dep is not None, _http_evidence(o)):
        return result()
    env = dep.get('environment')
    meta['environment'] = env if isinstance(env, str) and re.fullmatch(r'[a-z0-9_-]{1,32}', env) else 'unknown'
    sha = dep.get('source_commit')
    sha = sha.lower() if isinstance(sha, str) and SHA_RE.fullmatch(sha.lower()) else None
    meta['commit_sha'] = sha
    sha_ev = {'reported': sha, 'expected': expect_sha, 'trusted_observed': trusted_observed_sha,
              'source': 'app-reported VERCEL_GIT_COMMIT_SHA'}
    if not expect_sha:
        skip('commit_sha', 'no --expect-sha given', sha_ev)
    elif sha is None:
        skip('commit_sha', 'deployment does not report a valid commit SHA', sha_ev)
    else:
        check('commit_sha', sha == expect_sha and trusted_observed_sha in (None, expect_sha), sha_ev)
    check('schema_compatible', isinstance(dep.get('schema'), dict) and dep['schema'].get('compatible') is True,
          _schema_evidence(dep.get('schema')))

    if meta['environment'] == 'production' and not allow_production_writes:
        for name in REQUIRED_CHECKS[3:]:
            skip(name, 'synthetic writes on production need --allow-production-writes (founder-approved run)')
        return result()

    o = a.register()
    if not check('register_synthetic_user', o.status in (200, 201) and a.token is not None, _http_evidence(o)):
        return result()
    # PR #9 (PDV-001) contract: the session must resolve to exactly the synthetic identity
    o = a.call('GET', '/api/v28/me')
    me = o.data if isinstance(o.data, dict) else {}
    check('session_identity', o.status == 200 and {'id', 'email', 'created_at', 'subscription'} <= set(me)
          and me.get('email') == a.email, {**_http_evidence(o), 'keys_ok': {'id', 'email', 'created_at', 'subscription'} <= set(me)})
    o = a.call('POST', '/api/v28/projects', {'title': 'deployment verification'})
    pid = o.data.get('id') if isinstance(o.data, dict) else None
    ev = _http_evidence(o)
    if pid is not None and not (isinstance(pid, str) and ID_RE.fullmatch(pid)):
        pid, ev['error_class'] = None, 'INVALID_RESPONSE_CONTRACT'   # never put server text into a URL path
    if not check('create_project', o.status in (200, 201) and pid is not None, ev):
        return result()
    o = a.call('POST', f'/api/v28/projects/{pid}/conversation?lang=en',
               {'message': 'An internal tool for my team to track equipment loans, in English, no login',
                'request_key': uuid.uuid4().hex})
    reply = ((o.data or {}).get('turn') or {}).get('reply') if isinstance(o.data, dict) else None
    check('conversation_turn', o.status == 200 and isinstance(reply, str) and bool(reply), _http_evidence(o))
    o = a.call('GET', f'/api/v28/projects/{pid}/conversation?lang=en')
    msgs = o.data.get('messages') if isinstance(o.data, dict) else None
    n = len(msgs) if isinstance(msgs, list) else 0
    contract_ok = isinstance(o.data, dict) and {'messages', 'discovery', 'plan', 'plan_id', 'interpreter'} <= set(o.data)
    check('conversation_persists', o.status == 200 and n >= 2 and contract_ok,      # PR #9 response contract
          {**_http_evidence(o), 'messages': n, 'contract_ok': contract_ok})
    o = a.call('GET', f'/api/v28/projects/{pid}/memory')
    check('project_memory', o.status == 200 and isinstance(o.data, dict) and o.data.get('schema') == 'project-memory/1',
          _http_evidence(o))
    o = client().call('GET', f'/api/v28/projects/{pid}/conversation')
    check('unauthenticated_denied', o.status in (401, 403), _http_evidence(o))
    b = client()
    ob = b.register()
    if b.token is None:
        skip('cross_user_isolation', 'second synthetic user could not register', _http_evidence(ob))
    else:
        o = b.call('GET', f'/api/v28/projects/{pid}/conversation')
        check('cross_user_isolation', o.status in (403, 404), _http_evidence(o))
    return result()


def config_error_result(base: str, reason: str) -> dict:
    checks = [CheckResult(check=n, status=NOT_RUN, category=CATEGORY[n], reason=f'configuration error: {reason}')
              for n in REQUIRED_CHECKS]
    return VerificationResult(kind='deployment', target='(rejected)', environment='unknown', commit_sha=None,
                              checks=checks, required=REQUIRED_CHECKS,
                              suites={'deployment_verify': SUITE_VERSION}).finish().to_dict()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog='deployment_verify')
    ap.add_argument('base')
    ap.add_argument('--expect-sha')
    ap.add_argument('--trusted-observed-sha', help='only from trusted deployment-system metadata, never app content')
    ap.add_argument('--allowed-host', action='append', default=[])
    ap.add_argument('--allowed-host-suffix', action='append', default=[])
    ap.add_argument('--bypass-token-env')
    ap.add_argument('--allow-production-writes', action='store_true')
    ap.add_argument('--timeout', type=float, default=15.0)
    ap.add_argument('--out')
    def _arg_error(message):
        raise TargetError(f'arguments: {message}')
    ap.error = _arg_error   # a bad command line still yields a BLOCKED result file, never "no result"
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = ap.parse_args(argv)
    except TargetError as exc:
        out = next((a.split('=', 1)[1] for a in argv if a.startswith('--out=')), None) or \
            next((argv[i + 1] for i, a in enumerate(argv[:-1]) if a == '--out'), None)
        args = argparse.Namespace(base='', out=out)
        print(f'configuration error: {exc} (a value starting with "-" needs --option=value)', file=sys.stderr)
        return _emit(config_error_result('', str(exc)), args.out, 3)
    code = 3
    try:
        if args.bypass_token_env and not re.fullmatch(r'[A-Z_][A-Z0-9_]{0,63}', args.bypass_token_env):
            raise TargetError('invalid --bypass-token-env name')
        bypass = (os.getenv(args.bypass_token_env) or None) if args.bypass_token_env else None
        result = verify(args.base, expect_sha=args.expect_sha or None, bypass=bypass,
                        allowed_hosts=tuple(args.allowed_host), allowed_suffixes=tuple(args.allowed_host_suffix),
                        trusted_observed_sha=args.trusted_observed_sha or None,
                        allow_production_writes=args.allow_production_writes, timeout=args.timeout)
        code = 0 if result['verdict'] in PROMOTABLE else (1 if result['verdict'] == FAILED else 2)
    except TargetError as exc:
        print(f'configuration error: {exc}', file=sys.stderr)
        result = config_error_result(args.base, str(exc))
    return _emit(result, args.out, code)


def _emit(result: dict, out: str | None, code: int) -> int:
    text = json.dumps(result, indent=1, ensure_ascii=False)
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            f.write(text + '\n')
    print(text)
    return code


if __name__ == '__main__':
    sys.exit(main())
