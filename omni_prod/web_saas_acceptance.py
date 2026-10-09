from __future__ import annotations

"""M5 Task 11: behavioral acceptance for running Web/SaaS previews.

A health probe only proves that an HTTP process is alive.  This module proves
that the generated product behaves like the accepted contract: auth/role,
CRUD, at least one integration/background path, responsive smoke and API
smoke.  The test plan is data, not demo-specific Python, and every step must
trace to acceptance IDs from the immutable ProductSpec/build contract.
"""

import copy
import http.cookiejar
import json
import re
from dataclasses import dataclass, replace
from typing import Any, Mapping, Protocol, Sequence
from urllib import error as urlerror
from urllib import request as urlrequest


WEB_SAAS_REQUIRED_KINDS: tuple[str, ...] = (
    'auth', 'role', 'data_create', 'data_read', 'data_update', 'data_delete',
    'integration', 'responsive', 'api_smoke',
)
# Demand-driven acceptance scope (founder principle 2026-10-07), taken from the
# immutable build contract, never from generated metadata. The `integration`
# behavior kind is required only when the contract needs outbound delivery,
# scheduled work or an external integration; otherwise it is NOT_REQUIRED for
# that build: such steps are never executed or counted as covered and are
# listed as not verified. No contract (lookup failed) -> the strict full floor.
_NON_EXTERNAL_INTEGRATIONS = frozenset({'database', 'storage'})


# Directive 2026-10-09 (autonomous completion §2): acceptance follows what
# was approved. Words that promise editing or removal in the user's request
# or the approved brief make those behaviours mandatory; otherwise they are
# NOT_REQUIRED (a booking app that only creates, lists and cancels is not
# failed for having no "edit"). Sign-in approved as NONE removes auth/role.
_UPDATE_WORDS = ('edit', 'update', 'change', 'rename', 'mark', 'complete', 'done', 'toggle', 'status',
                 'עריכ', 'ערוך', 'לערוך', 'עדכון', 'לעדכן', 'שינוי', 'לשנות', 'סימון', 'לסמן', 'סמן', 'הושלם',
                 'בוצע', 'השלמה', 'סטטוס', 'מצב')
_DELETE_WORDS = ('delete', 'remove', 'cancel', 'archive', 'מחיק', 'למחוק', 'מחק', 'הסר', 'להסיר', 'ביטול', 'לבטל',
                 'בטל', 'ארכיון')


def _no_login(contract: Mapping[str, Any]) -> bool:
    roles = [str(r) for r in (contract.get('user_roles') or ())]
    defaults = [str(d) for d in (contract.get('defaults') or contract.get('defaults_applied') or ())]
    prompt = str(contract.get('prompt') or '')
    return ('no_login_single_user' in defaults or 'Sign-in: NONE' in prompt) and roles in ([], ['user'])


def acceptance_scope(build_contract: Mapping[str, Any] | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(required floor, NOT_REQUIRED kinds) from the approved contract. No
    contract (lookup failed) -> the strict full floor, nothing waived."""
    if not build_contract:
        return WEB_SAAS_REQUIRED_KINDS, ()
    not_required: list[str] = []
    kinds = {str(i.get('kind')) for i in (build_contract.get('infrastructure') or ())
             if isinstance(i, Mapping) and i.get('required', True)}
    external = set(map(str, build_contract.get('required_integrations') or ())) - _NON_EXTERNAL_INTEGRATIONS
    if not (kinds & {'scheduled_http', 'outbound'} or external):
        not_required.append('integration')
    if 'prompt' in build_contract:  # the approved text is known: derive the rest from it
        text = str(build_contract.get('prompt') or '').lower()
        if _no_login(build_contract):
            not_required += ['auth', 'role']
        if not any(w in text for w in _UPDATE_WORDS):
            not_required.append('data_update')
        if not any(w in text for w in _DELETE_WORDS):
            not_required.append('data_delete')
    waived = tuple(dict.fromkeys(not_required))
    return tuple(k for k in WEB_SAAS_REQUIRED_KINDS if k not in waived), waived


_ALLOWED_METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'}
_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes

    def text(self) -> str:
        return self.body.decode('utf-8', errors='replace')

    def json(self) -> Any:
        return json.loads(self.text() or 'null')


class HttpTransport(Protocol):
    def request(self, *, method: str, url: str, headers: Mapping[str, str] | None = None,
                json_body: Any = None, timeout_seconds: float = 10.0) -> HttpResponse: ...


class UrllibSessionTransport:
    """Stateful stdlib HTTP client: preserves cookies across persona steps."""

    def __init__(self):
        jar = http.cookiejar.CookieJar()
        self._opener = urlrequest.build_opener(urlrequest.HTTPCookieProcessor(jar))

    def request(self, *, method: str, url: str, headers: Mapping[str, str] | None = None,
                json_body: Any = None, timeout_seconds: float = 10.0) -> HttpResponse:
        request_headers = dict(headers or {})
        data = None
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode('utf-8')
            request_headers.setdefault('Content-Type', 'application/json')
        req = urlrequest.Request(url, data=data, headers=request_headers, method=method)
        try:
            with self._opener.open(req, timeout=timeout_seconds) as resp:
                return HttpResponse(
                    status=int(resp.status), headers={k.lower(): v for k, v in resp.headers.items()},
                    body=resp.read(),
                )
        except urlerror.HTTPError as exc:
            return HttpResponse(
                status=int(exc.code), headers={k.lower(): v for k, v in exc.headers.items()}, body=exc.read(),
            )
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f'preview request failed: {type(exc).__name__}: {exc}') from exc


@dataclass(frozen=True)
class AcceptanceCheckResult:
    persona_id: str
    step_id: str
    kind: str
    acceptance_ids: tuple[str, ...]
    passed: bool
    detail: str
    http_status: int | None = None
    # Repair evidence (autonomous completion §1): what was sent and what came
    # back, truncated. Synthetic test data only; never headers or cookies.
    request: str | None = None
    response_excerpt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'persona_id': self.persona_id, 'step_id': self.step_id, 'kind': self.kind,
            'acceptance_ids': list(self.acceptance_ids), 'passed': self.passed,
            'detail': self.detail, 'http_status': self.http_status,
            'request': self.request, 'response_excerpt': self.response_excerpt,
        }


@dataclass(frozen=True)
class AcceptanceReport:
    status: str
    release_eligible: bool
    summary: str
    checks: tuple[AcceptanceCheckResult, ...]
    covered_acceptance_ids: tuple[str, ...]
    missing_acceptance_ids: tuple[str, ...]
    covered_kinds: tuple[str, ...]
    missing_kinds: tuple[str, ...]
    runtime_logs: str | None = None
    not_required_kinds: tuple[str, ...] = ()
    not_verified_steps: tuple[str, ...] = ()

    def with_runtime_logs(self, logs: str | None) -> 'AcceptanceReport':
        if logs is None:
            return self
        return replace(self, runtime_logs=str(logs)[-8000:])

    def to_dict(self) -> dict[str, Any]:
        return {
            'status': self.status, 'release_eligible': self.release_eligible, 'summary': self.summary,
            'checks': [x.to_dict() for x in self.checks],
            'covered_acceptance_ids': list(self.covered_acceptance_ids),
            'missing_acceptance_ids': list(self.missing_acceptance_ids),
            'covered_kinds': list(self.covered_kinds), 'missing_kinds': list(self.missing_kinds),
            'not_required_kinds': list(self.not_required_kinds),
            'not_verified_steps': list(self.not_verified_steps),
            'runtime_logs': self.runtime_logs,
        }


class WebSaaSAcceptanceRunner:
    def __init__(self, *, transport: HttpTransport | None = None,
                 required_kinds: Sequence[str] = WEB_SAAS_REQUIRED_KINDS,
                 timeout_seconds: float = 10.0, build_contract: Mapping[str, Any] | None = None):
        self.transport = transport or UrllibSessionTransport()
        requested = tuple(str(x).strip() for x in required_kinds if str(x).strip())
        floor, not_required = acceptance_scope(build_contract)
        self.not_required_kinds = tuple(not_required)
        # Generated metadata may ask for *more* checks, never fewer. This
        # deterministic floor prevents model output from weakening M5 acceptance.
        self.required_kinds = tuple(k for k in dict.fromkeys((*floor, *requested)) if k not in not_required)
        self.timeout_seconds = float(timeout_seconds)

    def verify(self, preview: Mapping[str, Any], contract: Any,
               personas: Sequence[Mapping[str, Any]]) -> AcceptanceReport:
        base_url = str(preview.get('preview_url') or '').strip().rstrip('/')
        if not base_url.startswith(('https://', 'http://')):
            return self._invalid('preview has no routable http(s) URL')
        contract_ids = _contract_acceptance_ids(contract)
        if not contract_ids:
            return self._invalid('contract has no acceptance IDs')

        validation_error = _validate_plan(personas, contract_ids)
        if validation_error:
            return self._invalid(validation_error, missing_ids=contract_ids)

        checks: list[AcceptanceCheckResult] = []
        passed_ids: set[str] = set()
        passed_kinds: set[str] = set()
        variables: dict[str, Any] = {}
        not_verified: list[str] = []

        for persona in personas:
            persona_id = str(persona.get('id') or '').strip()
            for raw_step in persona.get('steps', ()):
                step = copy.deepcopy(dict(raw_step))
                step_id = str(step['id'])
                kind = str(step['kind'])
                acceptance_ids = tuple(str(x) for x in step.get('acceptance_ids', ()))
                if kind in self.not_required_kinds:
                    # NOT_REQUIRED for this build: never executed, never counted.
                    not_verified.append(f'{persona_id}:{step_id}')
                    continue
                request_text = None
                try:
                    method = str(step.get('method', 'GET')).upper()
                    path = _resolve(step.get('path', '/'), variables)
                    request_text = f'{method} {path}'
                    if step.get('json') is not None:
                        request_text += ' ' + json.dumps(_resolve(step.get('json'), variables), ensure_ascii=False)[:600]
                    if not isinstance(path, str) or not path.startswith('/') or path.startswith('//'):
                        raise ValueError('path must be a relative absolute-path beginning with one /')
                    headers = _resolve(step.get('headers') or {}, variables)
                    body = _resolve(step.get('json'), variables)
                    resp = self.transport.request(
                        method=method, url=base_url + path, headers=headers, json_body=body,
                        timeout_seconds=float(step.get('timeout_seconds', self.timeout_seconds)),
                    )
                    detail = _assert_response(step, resp)
                    _capture(step.get('capture') or {}, resp, variables)
                    passed = True
                    passed_ids.update(acceptance_ids)
                    passed_kinds.add(kind)
                except Exception as exc:
                    resp = locals().get('resp')
                    detail = f'{type(exc).__name__}: {exc}'
                    passed = False
                excerpt = None
                if not passed and 'resp' in locals() and resp is not None:
                    try:
                        excerpt = resp.text()[:500]
                    except Exception:
                        excerpt = None
                checks.append(AcceptanceCheckResult(
                    persona_id=persona_id, step_id=step_id, kind=kind,
                    acceptance_ids=acceptance_ids, passed=passed, detail=detail,
                    http_status=(getattr(resp, 'status', None) if 'resp' in locals() else None),
                    request=request_text, response_excerpt=excerpt,
                ))
                if 'resp' in locals():
                    del resp

        missing_ids = tuple(sorted(contract_ids - passed_ids))
        missing_kinds = tuple(sorted(set(self.required_kinds) - passed_kinds))
        failed_count = sum(1 for x in checks if not x.passed)
        passed = bool(checks) and failed_count == 0 and not missing_ids and not missing_kinds
        if passed:
            summary = f'behavioral acceptance passed: {len(checks)} checks, {len(passed_ids)} acceptance IDs'
        else:
            parts = [f'{failed_count} failed check(s)']
            if missing_ids:
                parts.append('missing acceptance coverage: ' + ','.join(missing_ids))
            if missing_kinds:
                parts.append('missing required behavior kinds: ' + ','.join(missing_kinds))
            summary = '; '.join(parts)
        return AcceptanceReport(
            status='PASS' if passed else 'FAIL', release_eligible=passed, summary=summary,
            checks=tuple(checks), covered_acceptance_ids=tuple(sorted(passed_ids)),
            missing_acceptance_ids=missing_ids, covered_kinds=tuple(sorted(passed_kinds)),
            missing_kinds=missing_kinds, not_required_kinds=self.not_required_kinds,
            not_verified_steps=tuple(not_verified),
        )

    def _invalid(self, summary: str, *, missing_ids: set[str] | None = None) -> AcceptanceReport:
        return AcceptanceReport(
            status='FAIL', release_eligible=False, summary=summary, checks=(),
            covered_acceptance_ids=(), missing_acceptance_ids=tuple(sorted(missing_ids or ())),
            covered_kinds=(), missing_kinds=tuple(sorted(self.required_kinds)), runtime_logs=None,
        )


def _contract_acceptance_ids(contract: Any) -> set[str]:
    acceptance = getattr(contract, 'acceptance', None)
    if acceptance is not None:
        return {str(getattr(x, 'id', '')).strip() for x in acceptance if str(getattr(x, 'id', '')).strip()}
    if isinstance(contract, Mapping):
        raw = contract.get('acceptance', ())
        ids = set()
        for item in raw:
            if isinstance(item, Mapping):
                aid = str(item.get('id') or '').strip()
            else:
                aid = str(item).strip()
            if aid:
                ids.add(aid)
        return ids
    return set()


def _validate_plan(personas: Sequence[Mapping[str, Any]], contract_ids: set[str]) -> str | None:
    if not isinstance(personas, Sequence) or isinstance(personas, (str, bytes)) or not personas:
        return 'acceptance personas must be a non-empty array'
    seen_steps: set[str] = set()
    for persona in personas:
        if not isinstance(persona, Mapping) or not str(persona.get('id') or '').strip():
            return 'every acceptance persona requires an id'
        steps = persona.get('steps')
        if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)) or not steps:
            return f'persona {persona.get("id")!r} has no steps'
        for step in steps:
            if not isinstance(step, Mapping):
                return 'acceptance step must be an object'
            step_id = str(step.get('id') or '').strip()
            kind = str(step.get('kind') or '').strip()
            method = str(step.get('method', 'GET')).upper()
            ids = tuple(str(x).strip() for x in step.get('acceptance_ids', ()) if str(x).strip())
            if not step_id or step_id in seen_steps:
                return 'acceptance step ids must be non-empty and unique'
            seen_steps.add(step_id)
            if not kind:
                return f'step {step_id} requires kind'
            if method not in _ALLOWED_METHODS:
                return f'step {step_id} uses unsupported HTTP method {method}'
            if not ids:
                return f'step {step_id} must reference contract acceptance_ids'
            unknown = sorted(set(ids) - contract_ids)
            if unknown:
                return f'step {step_id} references unknown acceptance id(s): {",".join(unknown)}'
    return None


def _resolve(value: Any, variables: Mapping[str, Any]) -> Any:
    if isinstance(value, str):
        def sub(match):
            key = match.group(1)
            if key not in variables:
                raise ValueError(f'unresolved acceptance variable {key}')
            return str(variables[key])
        return _VAR.sub(sub, value)
    if isinstance(value, list):
        return [_resolve(x, variables) for x in value]
    if isinstance(value, tuple):
        return tuple(_resolve(x, variables) for x in value)
    if isinstance(value, dict):
        return {str(k): _resolve(v, variables) for k, v in value.items()}
    return value


def _assert_response(step: Mapping[str, Any], response: HttpResponse) -> str:
    expected_status = int(step.get('expect_status', 200))
    if response.status != expected_status:
        raise AssertionError(f'expected HTTP {expected_status}, got {response.status}')
    if 'expect_text_contains' in step:
        needle = str(step['expect_text_contains'])
        if not _text_contains(response.text(), needle):
            raise AssertionError(f'response text missing {needle!r}')
    if 'expect_json_contains' in step:
        actual = response.json()
        expected = step['expect_json_contains']
        if not _json_contains(actual, expected):
            raise AssertionError(f'JSON response does not contain expected subset {expected!r}')
    return f'HTTP {response.status} matched expectations'


def _text_contains(text: str, needle: str) -> bool:
    """Literal match, or match in the decoded JSON body: a JSON API may send
    Hebrew as \\u05d4 escapes (paid build bld_2e55113c, 2026-10-09: the
    conflict message was present but escaped and the check failed)."""
    if needle in text:
        return True
    try:
        decoded = json.loads(text)
    except (ValueError, TypeError):
        return False
    return needle in json.dumps(decoded, ensure_ascii=False)


def _json_contains(actual: Any, expected: Any) -> bool:
    if isinstance(expected, Mapping):
        return isinstance(actual, Mapping) and all(k in actual and _json_contains(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and all(any(_json_contains(item, wanted) for item in actual) for wanted in expected)
    return actual == expected


def _capture(capture: Mapping[str, str], response: HttpResponse, variables: dict[str, Any]) -> None:
    if not capture:
        return
    data = response.json()
    for variable, dotted_path in capture.items():
        current = data
        for part in str(dotted_path).split('.'):
            if not isinstance(current, Mapping) or part not in current:
                raise AssertionError(f'capture path {dotted_path!r} missing from response')
            current = current[part]
        variables[str(variable)] = current
