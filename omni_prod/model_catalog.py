"""Priced multi-provider LLM catalog for cost-aware routing.

`OMNI_MODEL_CATALOG_JSON` is a JSON list of OpenAI-compatible models. Each
entry names the environment variable that holds its API key (`api_key_env`);
keys are never stored inside the catalog. An entry whose key variable is empty
is kept as NOT_CONFIGURED and is never routed to.

An unknown price is never an assumed zero. The router uses prices to order
candidates and to authorize a conservative per-call maximum before any request
is sent. Since the owner's word of 2026-11-26 a missing price no longer stops
the catalog (or a build): the entry routes with price_known False, authorized
at UNPRICED_STAND_IN, and its calls are recorded with tokens and an UNKNOWN cost.
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


def _stand_in() -> tuple[Decimal, Decimal]:
    """The owner 2026-11-26: the per-million figures a model WITHOUT a known price is ordered and authorized at -- the
    highest input and output token prices in the source-backed schedule (intelligence.prices), so its worst case is
    never below any priced model's and cost-first routing tries it after them. Not a price: never metered, never
    shown as a cost (ModelOption.price_known is False and attempt_ledger.metered_cost returns None)."""
    from .intelligence.prices import SCHEDULE
    ins = [r.input_per_million for r in SCHEDULE if r.input_per_million is not None and r.output_per_million is not None]
    outs = [r.output_per_million for r in SCHEDULE if r.input_per_million is not None and r.output_per_million is not None]
    return max(ins), max(outs)


UNPRICED_STAND_IN = _stand_in()


class ModelCatalogError(ValueError):
    """Safe error: never contains key values."""


@dataclass(frozen=True)
class CatalogModel:
    option: ModelOption
    endpoint: ModelEndpoint | None
    max_output_tokens: int
    api_key_env: str
    # Wave A governance (omni_prod.intelligence.governance): lifecycle and
    # where the price in force comes from; notes carry warnings/replacements.
    lifecycle: str = 'ACTIVE'
    price_source: str = 'catalog'
    governance_notes: tuple[str, ...] = ()
    blocked_reason: str = ''   # set when a configured key is refused by governance

    @property
    def status(self) -> str:
        if self.lifecycle == 'RETIRED':
            return 'RETIRED'
        if self.blocked_reason:
            return self.blocked_reason
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
            'lifecycle': self.lifecycle, 'price_source': self.price_source,
            'governance_notes': list(self.governance_notes),
            # only when unknown, so a fully priced catalog keeps its price_catalog_version (the owner 2026-11-26)
            **({} if getattr(o, 'price_known', True) else {'price_known': False, 'prices_are': 'authorization stand-in'}),
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


def parse_model_catalog(raw: str, env: Mapping[str, str], *, when=None) -> tuple[CatalogModel, ...]:
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
        staged_enrollment = item.get('_activation_status') == 'PENDING_LIVE_VERIFICATION'
        enabled = item.get('enabled') is True if staged_enrollment else bool(item.get('enabled', True))
        if staged_enrollment and enabled and (type(item['quality']) is not int or quality == 0):
            raise ModelCatalogError(f'{name}: enabled enrollment requires an explicit quality score 1..100')
        # The owner 2026-11-26: an entry without a price is kept (it was a ModelCatalogError that stopped every build).
        # Its two numbers become the authorization stand-in -- never a price; the model's calls are metered as unknown.
        catalog_priced = all(k in item for k in ('input_per_million', 'output_per_million'))
        if catalog_priced:
            input_price = _decimal(item['input_per_million'], 'input_per_million', name)
            output_price = _decimal(item['output_per_million'], 'output_per_million', name)
        else:
            input_price, output_price = UNPRICED_STAND_IN
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
        from .intelligence.governance import govern
        gov = govern(model=model, base_url=base_url, input_per_million=input_price,
                     output_per_million=output_price, when=when, catalog_price_known=catalog_priced)
        input_price, output_price = gov.input_per_million, gov.output_per_million
        price_known = getattr(gov, 'price_known', True)
        if not price_known:      # ordering and authorization only: the stand-in, never the untrusted number
            input_price, output_price = UNPRICED_STAND_IN
        routable = enabled and gov.routable
        key = (env.get(key_env) or '').strip()
        option = ModelOption(provider=provider, model=model, quality=quality, latency_ms=latency,
                             input_per_million=input_price, output_per_million=output_price,
                             enabled=routable and bool(key), price_known=price_known)
        endpoint = None
        if key and routable:
            endpoint = ModelEndpoint(name=name, base_url=base_url, model=model, api_key=key,
                                     timeout_seconds=timeout, external=True, api_style=api_style,
                                     extra_body=extra_body)
        out.append(CatalogModel(option=option, endpoint=endpoint, max_output_tokens=max_out,
                                api_key_env=key_env, lifecycle=gov.lifecycle, price_source=gov.price_source,
                                governance_notes=gov.notes,
                                blocked_reason='PRICE_UNVERIFIED' if (key and enabled
                                                                      and not gov.routable
                                                                      and gov.lifecycle != 'RETIRED') else ''))
    return tuple(out)


def load_model_catalog(env: Mapping[str, str] | None = None) -> tuple[CatalogModel, ...]:
    env = os.environ if env is None else env
    return parse_model_catalog(env.get('OMNI_MODEL_CATALOG_JSON', ''), env)
