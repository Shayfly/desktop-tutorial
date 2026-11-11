from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import json
import os
from .model_gateway import ModelEndpoint
from .model_policy import ModelUsePolicy
from .model_catalog import CatalogModel, load_model_catalog
from .model_router import RoutingPolicy

@dataclass(frozen=True)
class ModelRuntimeConfig:
    primary: ModelEndpoint | None
    fallback: tuple[ModelEndpoint, ...]
    policy: ModelUsePolicy
    catalog: tuple[CatalogModel, ...] = ()
    routing: RoutingPolicy = RoutingPolicy()
    # T5: explicitly declared quality of the configured routes (None = unknown -> never used for a task).
    primary_quality: int | None = None
    fallback_quality: tuple[int | None, ...] = ()

    @classmethod
    def from_env(cls) -> 'ModelRuntimeConfig':
        catalog = load_model_catalog()
        routing = RoutingPolicy(
            minimum_quality=int(os.getenv('OMNI_MODEL_MIN_QUALITY', '70')),
            prefer_cost=os.getenv('OMNI_MODEL_ROUTING', 'cost') != 'quality',
        )
        # With a priced catalog and no explicitly configured self-hosted model,
        # there is no local primary: the catalog router chooses every call.
        use_local = bool(os.getenv('OMNI_LOCAL_MODEL_URL', '').strip()) or not catalog
        primary = None if not use_local else ModelEndpoint(
            name=os.getenv('OMNI_LOCAL_MODEL_NAME', 'omni-local'),
            base_url=os.getenv('OMNI_LOCAL_MODEL_URL', 'http://127.0.0.1:8001/v1'),
            model=os.getenv('OMNI_LOCAL_MODEL_ID', 'local-coder'),
            api_key=os.getenv('OMNI_LOCAL_MODEL_API_KEY') or None,
            timeout_seconds=float(os.getenv('OMNI_LOCAL_MODEL_TIMEOUT', '120')),
            external=False,
        )
        primary_quality = _declared_quality(os.getenv('OMNI_LOCAL_MODEL_QUALITY'), 'OMNI_LOCAL_MODEL_QUALITY')
        zero = os.getenv('OMNI_ZERO_COST_MODE', '1') == '1'
        allow = os.getenv('OMNI_ALLOW_EXTERNAL_FALLBACK', '0') == '1'
        budget = Decimal(os.getenv('OMNI_EXTERNAL_BUDGET_USD', '0'))
        calls = int(os.getenv('OMNI_EXTERNAL_CALLS_PER_BUILD', '0'))
        policy = ModelUsePolicy(
            zero_cost_mode=zero,
            allow_external_fallback=allow,
            external_budget_usd=budget,
            max_external_calls_per_build=calls,
        )
        fallback = []
        fallback_quality = []
        raw = os.getenv('OMNI_EXTERNAL_MODELS_JSON', '').strip()
        if raw:
            items = json.loads(raw)
            if not isinstance(items, list):
                raise RuntimeError('OMNI_EXTERNAL_MODELS_JSON must be a list')
            for item in items:
                fallback.append(ModelEndpoint(
                    name=str(item['name']),
                    base_url=str(item['base_url']),
                    model=str(item['model']),
                    api_key=str(item['api_key']),
                    timeout_seconds=float(item.get('timeout_seconds', 120)),
                    external=True,
                ))
                fallback_quality.append(_declared_quality(item.get('quality'), f"OMNI_EXTERNAL_MODELS_JSON[{item['name']}].quality"))
        return cls(primary, tuple(fallback), policy, catalog, routing,
                   primary_quality=primary_quality if primary is not None else None,
                   fallback_quality=tuple(fallback_quality))


def _declared_quality(raw, where: str) -> int | None:
    if raw is None or str(raw).strip() == '':
        return None
    try:
        value = int(str(raw).strip())
    except ValueError as exc:
        raise RuntimeError(f'{where} must be an integer 0..100') from exc
    if not 0 <= value <= 100:
        raise RuntimeError(f'{where} must be an integer 0..100')
    return value
