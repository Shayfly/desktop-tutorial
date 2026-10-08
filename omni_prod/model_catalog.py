"""Priced multi-provider LLM catalog for cost-aware routing.

`OMNI_MODEL_CATALOG_JSON` is a JSON list of OpenAI-compatible models. Each
entry names the environment variable that holds its API key (`api_key_env`);
keys are never stored inside the catalog. An entry whose key variable is empty
is kept as NOT_CONFIGURED and is never routed to.

Prices are mandatory: an unknown price is a configuration error, never an
assumed zero. The router uses them to order candidates and to authorize a
conservative per-call maximum before any request is sent.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import json
import os
import re
from typing import Mapping
from urllib.parse import urlsplit

from .model_gateway import API_STYLES, ModelEndpoint
from .model_router import ModelOption

_KEY_ENV = re.compile(r'^[A-Z][A-Z0-9_]{2,63}$')
_NAME = re.compile(r'^[a-z0-9][a-z0-9._-]{0,63}$')


class ModelCatalogError(ValueError):
    """Safe error: never contains key values."""


@dataclass(frozen=True)
class CatalogModel:
    option: ModelOption
    endpoint: ModelEndpoint | None
    max_output_tokens: int
    api_key_env: str

    @property
    def status(self) -> str:
        return 'CONFIGURED' if self.endpoint is not None else 'NOT_CONFIGURED'

    def to_public_dict(self) -> dict:
        o = self.option
        return {
            'name': self.endpoint.name if self.endpoint else o.model,
            'provider': o.provider, 'model': o.model, 'quality': o.quality,
            'input_per_million_usd': str(o.input_per_million),
            'output_per_million_usd': str(o.output_per_million),
            'max_output_tokens': self.max_output_tokens,
            'api_key_env': self.api_key_env, 'status': self.status,
        }


def _decimal(value, field: str, name: str) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ModelCatalogError(f'{name}: {field} must be a number') from exc
    if not d.is_finite() or d < 0:
        raise ModelCatalogError(f'{name}: {field} must be a non-negative number')
    return d


def _https_base_url(value, name: str) -> str:
    url = str(value or '').strip()
    parts = urlsplit(url)
    if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment or any(c in url for c in '\r\n ')):
        raise ModelCatalogError(f'{name}: base_url must be a plain https URL')
    return url.rstrip('/')


def parse_model_catalog(raw: str, env: Mapping[str, str]) -> tuple[CatalogModel, ...]:
    raw = (raw or '').strip()
    if not raw:
        return ()
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ModelCatalogError('OMNI_MODEL_CATALOG_JSON is not valid JSON') from exc
    if not isinstance(items, list):
        raise ModelCatalogError('OMNI_MODEL_CATALOG_JSON must be a list')
    seen: set[str] = set()
    out: list[CatalogModel] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ModelCatalogError(f'entry {index} must be an object')
        name = str(item.get('name', '')).strip()
        if not _NAME.match(name):
            raise ModelCatalogError(f'entry {index}: name must match {_NAME.pattern}')
        if name in seen:
            raise ModelCatalogError(f'{name}: duplicate name')
        seen.add(name)
        if 'api_key' in item:
            raise ModelCatalogError(f'{name}: put the key in an environment variable and use api_key_env')
        key_env = str(item.get('api_key_env', '')).strip()
        if not _KEY_ENV.match(key_env):
            raise ModelCatalogError(f'{name}: api_key_env must be an UPPER_CASE variable name')
        model = str(item.get('model', '')).strip()
        if not model or len(model) > 200 or any(c in model for c in '\r\n'):
            raise ModelCatalogError(f'{name}: model is required')
        provider = str(item.get('provider', name.split('-')[0])).strip() or name
        try:
            quality = int(item.get('quality'))
        except (TypeError, ValueError) as exc:
            raise ModelCatalogError(f'{name}: quality must be an integer 0..100') from exc
        if not 0 <= quality <= 100:
            raise ModelCatalogError(f'{name}: quality must be an integer 0..100')
        for required in ('input_per_million', 'output_per_million'):
            if required not in item:
                raise ModelCatalogError(f'{name}: {required} price is required')
        input_price = _decimal(item['input_per_million'], 'input_per_million', name)
        output_price = _decimal(item['output_per_million'], 'output_per_million', name)
        try:
            max_out = int(item.get('max_output_tokens', 8192))
            latency = int(item.get('latency_ms', 3000))
            timeout = float(item.get('timeout_seconds', 120))
        except (TypeError, ValueError) as exc:
            raise ModelCatalogError(f'{name}: numeric limits are invalid') from exc
        if max_out < 1 or latency < 0 or timeout <= 0:
            raise ModelCatalogError(f'{name}: numeric limits are invalid')
        base_url = _https_base_url(item.get('base_url'), name)
        api_style = str(item.get('api', 'openai')).strip()
        if api_style not in API_STYLES:
            raise ModelCatalogError(f'{name}: api must be one of {sorted(API_STYLES)}')
        extra = item.get('extra_body') or {}
        reserved = {'model', 'messages', 'system', 'max_tokens', 'max_completion_tokens', 'temperature', 'stream'}
        if not isinstance(extra, dict) or any(not isinstance(k, str) or k in reserved for k in extra):
            raise ModelCatalogError(f'{name}: extra_body must be an object without core request fields')
        extra_body = tuple(sorted((k, json.dumps(v)) for k, v in extra.items()))
        enabled = bool(item.get('enabled', True))
        key = (env.get(key_env) or '').strip()
        option = ModelOption(provider=provider, model=model, quality=quality, latency_ms=latency,
                             input_per_million=input_price, output_per_million=output_price,
                             enabled=enabled and bool(key))
        endpoint = None
        if key and enabled:
            endpoint = ModelEndpoint(name=name, base_url=base_url, model=model, api_key=key,
                                     timeout_seconds=timeout, external=True, api_style=api_style,
                                     extra_body=extra_body)
        out.append(CatalogModel(option=option, endpoint=endpoint, max_output_tokens=max_out,
                                api_key_env=key_env))
    return tuple(out)


def load_model_catalog(env: Mapping[str, str] | None = None) -> tuple[CatalogModel, ...]:
    env = os.environ if env is None else env
    return parse_model_catalog(env.get('OMNI_MODEL_CATALOG_JSON', ''), env)
