from __future__ import annotations
from dataclasses import dataclass
import json
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
    if status != 429:
        return False
    text = str(exc).lower()
    return any(k in text for k in ('quota', 'billing', 'insufficient', 'credit balance', 'resource_exhausted'))


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

    def complete(self, *, system: str, user: str, temperature: float = 0.1,
                 max_tokens: int = 4096) -> str:
        if not 0 <= temperature <= 2:
            raise ValueError('temperature out of range')
        if max_tokens < 1:
            raise ValueError('max_tokens must be positive')
        style = self.endpoint.api_style
        headers = {'Content-Type': 'application/json', 'User-Agent': '148AI-model-gateway/1.0'}
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
            return content
        try:
            content = payload['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelGatewayError('invalid model response shape') from exc
        if not isinstance(content, str) or not content.strip():
            raise ModelGatewayError('empty model response')
        return content

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
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ModelGatewayError('model did not return valid JSON') from exc
        if not isinstance(obj, dict):
            raise ModelGatewayError('model JSON root must be object')
        return obj
