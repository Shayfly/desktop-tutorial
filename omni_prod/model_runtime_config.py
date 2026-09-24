from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import json
import os
from .model_gateway import ModelEndpoint
from .model_policy import ModelUsePolicy

@dataclass(frozen=True)
class ModelRuntimeConfig:
    primary: ModelEndpoint
    fallback: tuple[ModelEndpoint, ...]
    policy: ModelUsePolicy

    @classmethod
    def from_env(cls) -> 'ModelRuntimeConfig':
        primary = ModelEndpoint(
            name=os.getenv('OMNI_LOCAL_MODEL_NAME', 'omni-local'),
            base_url=os.getenv('OMNI_LOCAL_MODEL_URL', 'http://127.0.0.1:8001/v1'),
            model=os.getenv('OMNI_LOCAL_MODEL_ID', 'local-coder'),
            api_key=os.getenv('OMNI_LOCAL_MODEL_API_KEY') or None,
            timeout_seconds=float(os.getenv('OMNI_LOCAL_MODEL_TIMEOUT', '120')),
            external=False,
        )
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
        return cls(primary, tuple(fallback), policy)
