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

    def to_dict(self) -> dict[str, Any]:
        return {
            'persona_id': self.persona_id, 'step_id': self.step_id, 'kind': self.kind,
            'acceptance_ids': list(self.acceptance_ids), 'passed': self.passed,
            'detail': self.detail, 'http_status': self.http_status,
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
            'runtime_logs': self.runtime_logs,
        }


class WebSaaSAcceptanceRunner:
    def __init__(self, *, transport: HttpTransport | None = None,
                 required_kinds: Sequence[str] = WEB_SAAS_REQUIRED_KINDS,
                 timeout_seconds: float = 10.0):
        self.transport = transport or UrllibSessionTransport()
        requested = tuple(str(x).strip() for x in required_kinds if str(x).strip())
        # Generated metadata may ask for *more* checks, never fewer. This
        # deterministic floor prevents model output from weakening M5 acceptance.
        self.required_kinds = tuple(dict.fromkeys((*WEB_SAAS_REQUIRED_KINDS, *requested)))
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

        for persona in personas:
            persona_id = str(persona.get('id') or '').strip()
            for raw_step in persona.get('steps', ()):
                step = copy.deepcopy(dict(raw_step))
                step_id = str(step['id'])
                kind = str(step['kind'])
                acceptance_ids = tuple(str(x) for x in step.get('acceptance_ids', ()))
                try:
                    method = str(step.get('method', 'GET')).upper()
                    path = _resolve(step.get('path', '/'), variables)
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
                checks.append(AcceptanceCheckResult(
                    persona_id=persona_id, step_id=step_id, kind=kind,
                    acceptance_ids=acceptance_ids, passed=passed, detail=detail,
                    http_status=(getattr(resp, 'status', None) if 'resp' in locals() else None),
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
            missing_kinds=missing_kinds,
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
        if needle not in response.text():
            raise AssertionError(f'response text missing {needle!r}')
    if 'expect_json_contains' in step:
        actual = response.json()
        expected = step['expect_json_contains']
        if not _json_contains(actual, expected):
            raise AssertionError(f'JSON response does not contain expected subset {expected!r}')
    return f'HTTP {response.status} matched expectations'


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
