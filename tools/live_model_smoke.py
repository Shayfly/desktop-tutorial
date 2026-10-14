"""One-call live provider smoke test (never run automatically).

Run only after explicit approval:
  PowerShell: $env:OMNI_LIVE_MODEL_SMOKE_APPROVED='1'; python tools/live_model_smoke.py

The script authorizes at most one external provider attempt, disables retries,
and hard-caps the catalog-priced request envelope at $0.25. It never prints
the key or response text. This is a provider connectivity check, not product
acceptance or evidence of a complete build.
"""
from __future__ import annotations

import os
from decimal import Decimal

from omni_prod.model_policy import ModelUsePolicy
from omni_prod.model_runtime_config import ModelRuntimeConfig
from omni_prod.model_router import RoutingPolicy
from omni_prod.routed_gateway import RoutedModelGateway

APPROVAL_ENV = 'OMNI_LIVE_MODEL_SMOKE_APPROVED'
MAX_TOTAL_SPEND_USD = Decimal('0.25')
SYSTEM = 'Reply with exactly the single word READY.'
USER = 'Reply with exactly the single word READY.'
MAX_OUTPUT_TOKENS = 32


def require_approval(env=None) -> None:
    env = os.environ if env is None else env
    if env.get(APPROVAL_ENV) != '1':
        raise SystemExit(f'Refusing live provider call; set {APPROVAL_ENV}=1 only after explicit approval.')


def configured_gateway(config: ModelRuntimeConfig) -> RoutedModelGateway:
    policy = ModelUsePolicy(
        zero_cost_mode=False,
        allow_external_fallback=True,
        external_budget_usd=MAX_TOTAL_SPEND_USD,
        max_external_calls_per_build=1,
    )
    return RoutedModelGateway(
        ranked=config.catalog,
        routing_policy=RoutingPolicy(
            minimum_quality=config.routing.minimum_quality,
            maximum_latency_ms=config.routing.maximum_latency_ms,
            prefer_cost=config.routing.prefer_cost,
        ),
        policy=policy,
        transient_retries=0,
    )


def main() -> int:
    require_approval()
    config = ModelRuntimeConfig.from_env()
    try:
        gateway = configured_gateway(config)
    except ValueError as exc:
        raise SystemExit('No configured catalog route is available for a live smoke test.') from exc
    kwargs = {'system': SYSTEM, 'user': USER, 'max_tokens': MAX_OUTPUT_TOKENS}
    candidates = gateway.ranked_routes(kwargs, task='conversation')
    if not candidates:
        raise SystemExit('No priced, enabled conversation provider route is configured.')
    selected = candidates[0][0]
    if selected.max_estimated_cost_usd > MAX_TOTAL_SPEND_USD:
        raise SystemExit('The selected model request exceeds the $0.25 smoke-test cap; no provider call was made.')

    response = gateway.complete(**kwargs, task='conversation')
    if response.strip() != 'READY':
        raise SystemExit('The provider returned an unexpected smoke response.')
    successful = next((event for event in reversed(gateway.events) if event.ok), None)
    if successful is None:
        raise SystemExit('No provider route completed the smoke call.')
    usage = gateway.last_usage
    print(f'provider={successful.provider}')
    print(f'model={successful.model}')
    print(f'authorized_total_usd={gateway.state.external_spend_usd}')
    print(f'provider_usage_received={"yes" if usage is not None else "no"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
