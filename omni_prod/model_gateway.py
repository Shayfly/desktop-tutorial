from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Callable
from urllib import request, error

from .provider_usage import parse_openai_compatible_usage

class ModelGatewayError(RuntimeError):
    pass


# Provider answers that mean "temporarily unable, nothing was done": the
# request may be retried. Golden E2E #1 on Preview (2026-10-07) failed on
# Gemini HTTP 503 "This model is currently experiencing high demand".
TRANSIENT_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})


class ModelHTTPError(ModelGatewayError):
    """HTTP error from the provider, with the status and Retry-After hint."""

    def __init__(self, message: str, *, status: int, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.status = status
        self.retry_after_seconds = retry_after_seconds

    @property
    def transient(self) -> bool:
        return self.status in TRANSIENT_HTTP_STATUSES


def _http_error_detail(exc) -> str:
    """Provider's own error message, short. Never echoes request headers."""
    try:
        raw = exc.read()[:2000].decode('utf-8', errors='replace')
    except Exception:
        return str(getattr(exc, 'reason', '') or '')[:200]
    try:
        body = json.loads(raw)
        item = body[0] if isinstance(body, list) and body else body
        err = item.get('error', item) if isinstance(item, dict) else {}
        message = err.get('message') if isinstance(err, dict) else None
        if isinstance(message, str) and message.strip():
            return ' '.join(message.split())[:300]
    except (ValueError, AttributeError, TypeError):
        pass
    return ' '.join(raw.split())[:200]


def _retry_after(exc) -> float | None:
    headers = getattr(exc, 'headers', None)
    value = headers.get('Retry-After') if headers is not None else None
    try:
        return max(0.0, float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None

API_STYLES = frozenset({'openai', 'openai_reasoning', 'anthropic'})
ANTHROPIC_VERSION = '2023-06-01'


def quota_exhausted(exc) -> bool:
    """HTTP answer meaning this route cannot serve the rest of the build:
    a spent quota (Gemini/OpenAI "exceeded your current quota", insufficient
    balance) or a rejected key. Retrying it within seconds is pointless
    (bld_ccd38bd0, 2026-10-08: ten 429 quota answers in a row)."""
    status = getattr(exc, 'status', None)
    if status in (401, 402, 403):
        return True
    text = str(exc).lower()
    if status == 400:
        # Anthropic answers an empty prepaid balance with HTTP 400 (model probe 2026-10-08).
        return 'credit balance' in text
    if status != 429:
        return False
    return any(k in text for k in ('quota', 'billing', 'insufficient', 'credit balance', 'resource_exhausted'))


def provider_quota_depleted(exc) -> bool:
    """Provider explicitly reported exhausted quota/credits, not generic 401 or rate-limit.

    A quota signal is not a verified account balance; only the provider's own
    billing API can provide that. For 148AI user-facing notices, do not infer
    that invalid credentials or a transient throttle mean money ran out.
    """
    status = getattr(exc, 'status', None)
    message = str(exc).lower()
    if status == 402:
        return True
    signals = ('credit balance', 'insufficient_quota', 'insufficient quota',
               'exceeded your current quota', 'quota exhausted', 'quota exceeded',
               'no credits remaining', 'out of credits', 'billing hard limit',
               'resource_exhausted')
    return status in (400, 403, 429) and any(s in message for s in signals)


class ProviderQuotaUnavailable(ModelGatewayError):
    """Provider(s) reported quota/credit exhaustion and no fallback succeeded."""
    def __init__(self, providers):
        names = tuple(sorted(set(str(p)[:64] for p in providers if p)))
        self.providers = names
        super().__init__('AI provider quota/credits unavailable: ' + ', '.join(names) +
                         '; no eligible model fallback completed')


@dataclass(frozen=True)
class ModelEndpoint:
    name: str
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = 120.0
    external: bool = False
    # Request dialect: 'openai' (chat/completions with max_tokens + temperature),
    # 'openai_reasoning' (chat/completions; GPT-6-class models reject max_tokens
    # and a non-default temperature, so max_completion_tokens and no temperature),
    # 'anthropic' (native Messages API; Anthropic documents its OpenAI layer as
    # not intended for production, and Sonnet 5.5 rejects a non-default temperature).
    api_style: str = 'openai'
    # Extra top-level request fields from the catalog (e.g. reasoning effort),
    # as a tuple of (key, json-text) pairs so the endpoint stays hashable.
    extra_body: tuple = ()

    def __post_init__(self):
        if not self.name or not self.base_url or not self.model:
            raise ValueError('name, base_url and model are required')
        if self.api_style not in API_STYLES:
            raise ValueError(f'api_style must be one of {sorted(API_STYLES)}')
        if self.timeout_seconds <= 0:
            raise ValueError('timeout_seconds must be positive')
        if self.external and not self.api_key:
            raise ValueError('external endpoint requires api_key')

class OpenAICompatibleGateway:
    def __init__(self, endpoint: ModelEndpoint, *, urlopen: Callable[..., Any] | None = None):
        self.endpoint = endpoint
        self._urlopen = urlopen or request.urlopen
        # M5 Task 8: provider-reported usage of the most recent call (None until a
        # response body is received). Captured before content validation, because
        # a call that returns an unusable body is still a billed call.
        self.last_usage = None
        # Exact model/version string the provider says it served, if reported.
        self.last_response_model = None
        self.last_idempotency_key = None

    def complete(self, *, system: str, user: str, temperature: float = 0.1,
                 max_tokens: int = 4096, idempotency_key: str | None = None) -> str:
        if not 0 <= temperature <= 2:
            raise ValueError('temperature out of range')
        if max_tokens < 1:
            raise ValueError('max_tokens must be positive')
        style = self.endpoint.api_style
        headers = {'Content-Type': 'application/json', 'User-Agent': '148AI-model-gateway/1.0'}
        # G5: one stable key per *logical* call. A retry after a lost response
        # reuses the key, so a provider that honours it bills once. Providers
        # that ignore the header are unaffected; the key is still kept so a
        # double charge is provable from the provider's own bill.
        if idempotency_key and str(idempotency_key).strip():
            headers['Idempotency-Key'] = str(idempotency_key).strip()[:255]
        if style == 'anthropic':
            body = {'model': self.endpoint.model, 'system': system,
                    'messages': [{'role': 'user', 'content': user}], 'max_tokens': max_tokens}
            url = self.endpoint.base_url.rstrip('/') + '/messages'
            if self.endpoint.api_key:
                headers['x-api-key'] = self.endpoint.api_key
            headers['anthropic-version'] = ANTHROPIC_VERSION
        else:
            body = {
                'model': self.endpoint.model,
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
            }
            if style == 'openai_reasoning':
                body['max_completion_tokens'] = max_tokens
            else:
                body['temperature'] = temperature
                body['max_tokens'] = max_tokens
            url = self.endpoint.base_url.rstrip('/') + '/chat/completions'
            # Some providers sit behind bot filters that reject the default
            # Python-urllib agent; identify the platform explicitly.
            if self.endpoint.api_key:
                headers['Authorization'] = f'Bearer {self.endpoint.api_key}'
        for key, raw in self.endpoint.extra_body:
            body.setdefault(key, json.loads(raw))
        req = request.Request(url, data=json.dumps(body).encode('utf-8'), headers=headers, method='POST')
        self.last_usage = None
        self.last_finish_reason = None
        self.last_idempotency_key = headers.get('Idempotency-Key')
        try:
            with self._urlopen(req, timeout=self.endpoint.timeout_seconds) as resp:
                response_headers = getattr(resp, 'headers', None)
                payload = json.loads(resp.read().decode('utf-8'))
        except error.HTTPError as exc:
            raise ModelHTTPError(f'model request failed: HTTP {exc.code}: {_http_error_detail(exc)}',
                                 status=exc.code, retry_after_seconds=_retry_after(exc)) from exc
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ModelGatewayError(f'model request failed: {exc}') from exc
        served = payload.get('model') if isinstance(payload, dict) else None
        self.last_response_model = served.strip()[:200] if isinstance(served, str) and served.strip() else None
        self.last_usage = parse_openai_compatible_usage(
            payload, response_headers, provider=self.endpoint.name, model=self.endpoint.model,
            external=self.endpoint.external,
        )
        if style == 'anthropic':
            blocks = payload.get('content') if isinstance(payload, dict) else None
            if not isinstance(blocks, list):
                raise ModelGatewayError('invalid model response shape')
            # Adaptive thinking may put thinking blocks first; only text is the answer.
            content = ''.join(b.get('text', '') for b in blocks
                              if isinstance(b, dict) and b.get('type') == 'text')
            if not content.strip():
                raise ModelGatewayError(f"empty model response (stop_reason={payload.get('stop_reason')})")
            self.last_finish_reason = payload.get('stop_reason')
            return content
        # bld_78e26994 (2026-10-08): gemini-3.8-flash answered after 71 s with
        # "invalid model response shape" and nothing else; say why (finish
        # reason, which keys came back) so the cause is visible in evidence.
        choice = None
        try:
            choice = payload['choices'][0]
            content = choice['message']['content']
        except (KeyError, IndexError, TypeError) as exc:
            finish = choice.get('finish_reason') if isinstance(choice, dict) else None
            keys = sorted(payload)[:8] if isinstance(payload, dict) else type(payload).__name__
            raise ModelGatewayError(f'invalid model response shape (finish_reason={finish}, keys={keys})') from exc
        if not isinstance(content, str) or not content.strip():
            raise ModelGatewayError(f"empty model response (finish_reason={choice.get('finish_reason')})")
        self.last_finish_reason = choice.get('finish_reason')
        return content

    last_finish_reason = None

    def complete_json(self, *, system: str, user: str, max_tokens: int = 4096) -> dict:
        raw = self.complete(system=system, user=user, temperature=0, max_tokens=max_tokens)
        text = raw.strip()
        if text.startswith('```'):
            lines = text.splitlines()
            if lines and lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            text = '\n'.join(lines).strip()
            if text.startswith('json'):
                text = text[4:].lstrip()
        obj, exc = _parse_json_object(text)
        if exc is not None:
            # Paid builds bld_2e55113c (2026-10-09): every repair answer of the
            # strong model was refused with no reason; name it in the evidence.
            finish = getattr(self, 'last_finish_reason', None)
            raise ModelGatewayError(f'model did not return valid JSON ({exc.msg} at char {exc.pos} of {len(text)}; '
                                    f'finish_reason={finish}; starts {text[:60]!r})') from exc
        if not isinstance(obj, dict):
            raise ModelGatewayError('model JSON root must be object')
        return obj


def _parse_json_object(text: str):
    """(object, None) or (None, JSONDecodeError). Accepts, in order: the text
    as JSON; the same with raw control characters inside strings (models put
    literal newlines/tabs in code strings); the outermost {...} when the model
    wrapped the object in prose; invalid backslash escapes doubled. Nothing
    is invented beyond that."""
    first = None
    for candidate in _json_candidates(text):
        for strict in (True, False):
            try:
                return json.loads(candidate, strict=strict), None
            except json.JSONDecodeError as exc:
                first = first or exc
    return None, first


_BAD_ESCAPE = re.compile(r'(?<!\\)((?:\\\\)*)\\(?=[^"\\/bfnrtu])')


def _json_candidates(text: str):
    start, end = text.find('{'), text.rfind('}')
    bases = [text]
    if 0 <= start < end and (start > 0 or end < len(text) - 1):
        bases.append(text[start:end + 1])
    yield from bases
    # A backslash before any other character is invalid JSON; models write
    # them for regexes/paths in code ("\d+"). Doubling only those cannot change
    # the meaning of valid JSON and recovers the literal the model wrote.
    for base in bases:
        fixed = _BAD_ESCAPE.sub(lambda m: m.group(1) + '\\\\', base)
        if fixed != base:
            yield fixed


def idempotency_key_for(*, build_id: str, task: str, attempt: int = 0, call_index: int = 0) -> str:
    """Stable key for one logical provider call.

    Deterministic, so a retry of the same logical call reuses it (provider can
    dedupe); distinct per attempt and call index, so two *different* calls
    never collapse into one.
    """
    raw = f'{build_id}\x00{task}\x00{attempt}\x00{call_index}'
    return 'g5-' + hashlib.sha256(raw.encode('utf-8')).hexdigest()[:40]
