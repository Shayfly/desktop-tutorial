from __future__ import annotations
from dataclasses import dataclass
import json
from typing import Any, Callable
from urllib import request, error

from .provider_usage import parse_openai_compatible_usage

class ModelGatewayError(RuntimeError):
    pass

@dataclass(frozen=True)
class ModelEndpoint:
    name: str
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = 120.0
    external: bool = False

    def __post_init__(self):
        if not self.name or not self.base_url or not self.model:
            raise ValueError('name, base_url and model are required')
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

    def complete(self, *, system: str, user: str, temperature: float = 0.1,
                 max_tokens: int = 4096) -> str:
        if not 0 <= temperature <= 2:
            raise ValueError('temperature out of range')
        if max_tokens < 1:
            raise ValueError('max_tokens must be positive')
        body = {
            'model': self.endpoint.model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        headers = {'Content-Type': 'application/json'}
        if self.endpoint.api_key:
            headers['Authorization'] = f'Bearer {self.endpoint.api_key}'
        req = request.Request(
            self.endpoint.base_url.rstrip('/') + '/chat/completions',
            data=json.dumps(body).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        self.last_usage = None
        try:
            with self._urlopen(req, timeout=self.endpoint.timeout_seconds) as resp:
                response_headers = getattr(resp, 'headers', None)
                payload = json.loads(resp.read().decode('utf-8'))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ModelGatewayError(f'model request failed: {exc}') from exc
        self.last_usage = parse_openai_compatible_usage(
            payload, response_headers, provider=self.endpoint.name, model=self.endpoint.model,
            external=self.endpoint.external,
        )
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
