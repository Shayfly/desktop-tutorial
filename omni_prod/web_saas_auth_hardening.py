"""Sign-in hardening checks for the behavioural acceptance (flag site_auth_v2, work order 001 mapped to 148AI).

Shipped into the sandbox APPENDED to web_saas_acceptance.py, and only when the flag is on: with it off the runner
source, the sandbox script and their bytes are exactly the baseline (tests/test_site_auth_v2.py proves it). After the
plan's own steps, the sign-in is attacked the way a stranger would: cookie flags, token rotation, a uniform error for
a wrong password and an unknown e-mail, and the 6th login in a minute answering 429.
"""
# This module's text is exec'd in the runner's namespace (no imports from omni_prod there); in the repo it imports
# the runner so it can be unit-tested.
try:
    WebSaaSAcceptanceRunner  # noqa: B018 -- defined when appended to the runner source
except NameError:  # pragma: no cover - normal import
    from .web_saas_acceptance import (AcceptanceCheckResult, HttpResponse, Mapping, UrllibSessionTransport,  # noqa: F401
                                      WebSaaSAcceptanceRunner, _resolve, http, re, replace, urlerror, urlrequest)


class _LoopbackSecurePolicy(http.cookiejar.DefaultCookiePolicy):
    """Browsers treat http://127.0.0.1 and localhost as a secure context, so a `Secure` / `__Host-` cookie set there is
    sent back. The stdlib jar does not; without this a correctly hardened product would fail its own sign-in steps."""

    def return_ok_secure(self, cookie, request):
        host = urlrequest.urlparse(request.get_full_url()).hostname or ''
        return host in ('127.0.0.1', 'localhost', '::1') or super().return_ok_secure(cookie, request)

    def set_ok(self, cookie, request):
        return True if (urlrequest.urlparse(request.get_full_url()).hostname or '') in ('127.0.0.1', 'localhost', '::1') \
            else super().set_ok(cookie, request)



class HardenedSessionTransport(UrllibSessionTransport):
    """Loopback-secure cookies, and every Set-Cookie line kept for inspection."""

    def __init__(self):
        self._opener = urlrequest.build_opener(urlrequest.HTTPCookieProcessor(
            http.cookiejar.CookieJar(policy=_LoopbackSecurePolicy())))

    def request(self, *, method, url, headers=None, json_body=None, timeout_seconds=10.0):
        import json as _json
        request_headers = dict(headers or {})
        data = None
        if json_body is not None:
            data = _json.dumps(json_body, ensure_ascii=False).encode('utf-8')
            request_headers.setdefault('Content-Type', 'application/json')
        req = urlrequest.Request(url, data=data, headers=request_headers, method=method)
        try:
            with self._opener.open(req, timeout=timeout_seconds) as resp:
                return HttpResponse(int(resp.status), _headers(resp.headers), resp.read())
        except urlerror.HTTPError as exc:
            return HttpResponse(int(exc.code), _headers(exc.headers), exc.read())
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f'preview request failed: {type(exc).__name__}: {exc}') from exc


def _headers(raw) -> dict:
    out = {k.lower(): v for k, v in raw.items()}
    out['set-cookie'] = '\n'.join(raw.get_all('Set-Cookie') or [])
    return out


class HardenedAcceptanceRunner(WebSaaSAcceptanceRunner):
    def __init__(self, *args, transport=None, transport_factory=None, **kwargs):
        super().__init__(*args, transport=transport or HardenedSessionTransport(), **kwargs)
        self._new_transport = transport_factory or HardenedSessionTransport

    def verify(self, preview, contract, personas):
        self._last_variables = {}
        report = super().verify(preview, contract, personas)
        if 'auth' in self.not_required_kinds or report.summary.startswith(('preview has no', 'contract has no')):
            return report
        base_url = str(preview.get('preview_url') or '').strip().rstrip('/')
        extra = self._auth_hardening(base_url, personas, _plan_variables(personas))
        checks = report.checks + tuple(extra)
        failed = [c for c in extra if not c.passed]
        if not failed:
            return replace(report, checks=checks)
        summary = report.summary if report.status != 'PASS' else ''
        summary = (summary + '; ' if summary else '') + 'sign-in hardening failed: ' + '; '.join(
            f'{c.step_id}: {c.detail}' for c in failed)
        return replace(report, status='FAIL', release_eligible=False, summary=summary, checks=checks)

    def _auth_hardening(self, base_url: str, personas, variables) -> list[AcceptanceCheckResult]:
        login = _login_step(personas)
        if login is None:
            return [_hardening('auth_login_found', False, 'no POST login step with a password in the plan: the sign-in '
                               'cannot be checked (add the login step to web_saas_acceptance)')]
        path = _resolve(login.get('path'), variables)
        body = dict(_resolve(login.get('json'), variables))
        pw_key = next(k for k in body if 'pass' in k.lower())
        out = []

        def attempt(transport, payload):
            return transport.request(method='POST', url=base_url + path, json_body=payload,
                                     timeout_seconds=self.timeout_seconds)

        # A fresh account of its own when the plan has a sign-up step, so the checks never depend on the plan's
        # captured variables and never lock the plan's own user out.
        signup = _signup_step(personas)
        if signup is not None:
            import secrets as _secrets
            sbody = dict(_resolve(signup.get('json'), variables) or {})
            mail_key = next((k for k in sbody if 'mail' in k.lower() or k.lower() in ('user', 'username', 'login')), None)
            spw_key = next((k for k in sbody if 'pass' in k.lower()), None)
            if mail_key and spw_key:
                sbody[mail_key] = f'hardening-{_secrets.token_hex(4)}@example.com'
                sbody[spw_key] = 'Hardening-Check-2026!'
                self._new_transport().request(method='POST', url=base_url + _resolve(signup.get('path'), variables),
                                              json_body=sbody, timeout_seconds=self.timeout_seconds)
                lmail = next((k for k in body if 'mail' in k.lower() or k.lower() in ('user', 'username', 'login')), None)
                if lmail:
                    body[lmail], body[pw_key] = sbody[mail_key], sbody[spw_key]

        first, second = self._new_transport(), self._new_transport()
        r1, r2 = attempt(first, body), attempt(second, body)
        cookie1, cookie2 = _session_cookie(r1), _session_cookie(r2)
        ok = r1.status < 300 and cookie1 is not None
        out.append(_hardening('auth_cookie_set', ok, f'login answered {r1.status}; session cookie: '
                              f'{cookie1["raw"][:80] if cookie1 else "none"}'))
        if cookie1:
            attrs = cookie1['attrs']
            missing = [a for a in ('httponly', 'secure') if a not in attrs]
            if attrs.get('samesite', '').lower() not in ('lax', 'strict'):
                missing.append('SameSite=Lax')
            if not cookie1['name'].startswith('__Host-') or attrs.get('path') != '/' or 'domain' in attrs:
                missing.append('__Host- name with Path=/ and no Domain')
            out.append(_hardening('auth_cookie_flags', not missing,
                                  'cookie flags ok' if not missing else 'session cookie lacks: ' + ', '.join(missing)))
            out.append(_hardening('auth_token_rotation', bool(cookie2) and cookie2['value'] != cookie1['value'],
                                  'every login issues a new token' if cookie2 and cookie2['value'] != cookie1['value']
                                  else 'two logins returned the same session token (no rotation)'))
        # Logout deletes the session on the server: the old token, sent by hand, must answer 401 afterwards.
        if cookie1:
            me_path, logout_path = _paths(personas, variables)
            hdr = {'Cookie': f"{cookie1['name']}={cookie1['value']}"}
            before = first.request(method='GET', url=base_url + me_path, headers=hdr, timeout_seconds=self.timeout_seconds)
            first.request(method='POST', url=base_url + logout_path, headers=hdr, json_body={},
                          timeout_seconds=self.timeout_seconds)
            after = self._new_transport().request(method='GET', url=base_url + me_path, headers=hdr,
                                                  timeout_seconds=self.timeout_seconds)
            ok = before.status == 200 and after.status == 401
            out.append(_hardening('auth_logout_server_side', ok,
                                  f'{me_path} with the token: {before.status} before logout, {after.status} after'
                                  + ('' if ok else ' (the old token must answer 401 once logged out)')))
        wrong = dict(body, **{pw_key: 'wrong-' + str(body[pw_key])})
        unknown = dict(body)
        for k in body:
            if 'mail' in k.lower() or 'user' in k.lower():
                unknown[k] = 'nobody-' + str(body[k])
        import secrets as _s

        def client():                      # an isolated bucket per check: a fresh documentation-range address
            return '203.0.113.%d' % (1 + _s.randbelow(250)), '198.51.100.%d' % (1 + _s.randbelow(250))

        def attempt_as(ip, payload, spoof=None):
            # The real path (Michael fix 2): the platform proxy (127.0.0.1, trusted) appends the visitor's address,
            # after any entries the visitor wrote himself. A second trusted hop sits on the right.
            chain = ([spoof] if spoof else []) + [ip, '127.0.0.1']
            return self._new_transport().request(method='POST', url=base_url + path, json_body=payload,
                                                 headers={'X-Forwarded-For': ', '.join(chain)},
                                                 timeout_seconds=self.timeout_seconds)
        ip_a, ip_b = client()
        a, b = attempt_as(ip_a, wrong), attempt_as(ip_b, unknown)
        same = a.status == b.status and a.status in (400, 401) and a.text().strip() == b.text().strip()
        out.append(_hardening('auth_uniform_error', same,
                              'wrong password and unknown e-mail answer the same' if same else
                              f'wrong password -> {a.status} {a.text()[:60]!r}; unknown e-mail -> {b.status} {b.text()[:60]!r}'))
        ip_c, ip_d = client()
        # Michael fix 1: every attempt forges a NEW left-most address; the limit must still hold for the real client.
        statuses = [attempt_as(ip_c, wrong, spoof='1.2.3.%d' % i).status for i in range(6)]
        limited = statuses[5] == 429
        out.append(_hardening('auth_rate_limit', limited,
                              f'6 logins in a minute from one client (each with a forged X-Forwarded-For entry) -> '
                              f'{statuses}' + ('' if limited else ': the 6th must answer 429 -- count the right-most '
                                               'untrusted hop, not the left-most (forgeable) entry')))
        other = attempt_as(ip_d, wrong).status
        out.append(_hardening('auth_rate_limit_per_client', other != 429,
                              f'another client behind the same proxy -> {other}'
                              + ('' if other != 429 else ': blocked by someone else\'s attempts (count the '
                                 'X-Forwarded-For client, not the proxy)')))
        return out



def _plan_variables(personas) -> dict:
    """The login step's own values only (no captures needed: it posts literal credentials or ${builtins})."""
    return {}


def _login_step(personas):
    for persona in personas:
        for step in persona.get('steps', ()):
            if str(step.get('kind')) != 'auth' or str(step.get('method', 'GET')).upper() != 'POST':
                continue
            path = str(step.get('path') or '')
            body = step.get('json')
            if re.search(r'log-?in|sign-?in|session', path, re.I) and not re.search(r'sign-?up|register', path, re.I) \
                    and isinstance(body, Mapping) and any('pass' in str(k).lower() for k in body):
                return step
    return None


def _paths(personas, variables) -> tuple[str, str]:
    me, logout = '/auth/me', '/auth/logout'
    for persona in personas:
        for step in persona.get('steps', ()):
            path = str(step.get('path') or '')
            if str(step.get('method', 'GET')).upper() == 'GET' and re.search(r'/(?:auth/)?me$|/session$|/account$', path):
                me = _resolve(path, variables)
            if re.search(r'log-?out|sign-?out', path, re.I):
                logout = _resolve(path, variables)
    return me, logout


def _signup_step(personas):
    for persona in personas:
        for step in persona.get('steps', ()):
            if str(step.get('kind')) == 'auth' and str(step.get('method', 'GET')).upper() == 'POST' \
                    and re.search(r'sign-?up|register', str(step.get('path') or ''), re.I) and isinstance(step.get('json'), Mapping):
                return step
    return None


def _session_cookie(resp) -> dict | None:
    raw_lines = [ln for ln in str((resp.headers or {}).get('set-cookie') or '').split('\n') if '=' in ln]
    for raw in raw_lines:
        parts = [p.strip() for p in raw.split(';')]
        name, _, value = parts[0].partition('=')
        attrs = {}
        for p in parts[1:]:
            k, _, v = p.partition('=')
            attrs[k.strip().lower()] = v.strip() if v else True
        if value and not re.search(r'csrf|xsrf|lang|theme', name, re.I):
            return {'name': name.strip(), 'value': value, 'attrs': attrs, 'raw': raw}
    return None


def _hardening(step_id: str, passed: bool, detail: str) -> AcceptanceCheckResult:
    return AcceptanceCheckResult(persona_id='auth_hardening', step_id=step_id, kind='auth_hardening', acceptance_ids=(),
                                 passed=bool(passed), detail=detail, http_status=None, request=None,
                                 response_excerpt=None)


