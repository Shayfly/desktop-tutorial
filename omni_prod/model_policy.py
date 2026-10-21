from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from .model_gateway import ModelEndpoint

@dataclass(frozen=True)
class ModelUsePolicy:
    zero_cost_mode: bool = True
    allow_external_fallback: bool = False
    external_budget_usd: Decimal = Decimal('0')
    max_external_calls_per_build: int = 0

    def __post_init__(self):
        if self.external_budget_usd < 0:
            raise ValueError('external_budget_usd cannot be negative')
        if self.max_external_calls_per_build < 0:
            raise ValueError('max_external_calls_per_build cannot be negative')
        if self.zero_cost_mode and (
            self.allow_external_fallback
            or self.external_budget_usd > 0
            or self.max_external_calls_per_build > 0
        ):
            raise ValueError('zero_cost_mode forbids external model spend')

@dataclass
class ModelUseState:
    external_spend_usd: Decimal = Decimal('0')
    external_calls: int = 0

class ModelPolicyViolation(RuntimeError):
    pass


def external_spend_enabled(env=None) -> bool:
    """C32 (2026-10-20): the kill switches, read exactly as ModelRuntimeConfig.from_env reads them
    (model_runtime_config.py:37-38). Every paid external call that is not routed through a ModelUsePolicy (the intake
    reservation gateway, the Replicate image test) asks this before contacting the provider."""
    import os
    env = os.environ if env is None else env
    return env.get('OMNI_ZERO_COST_MODE', '1') != '1' and env.get('OMNI_ALLOW_EXTERNAL_FALLBACK', '0') == '1'


SPEND_DISABLED = ('external spend disabled on this host (OMNI_ZERO_COST_MODE=1 or OMNI_ALLOW_EXTERNAL_FALLBACK!=1)')

def authorize_model_call(*, endpoint: ModelEndpoint, policy: ModelUsePolicy,
                         state: ModelUseState, estimated_cost_usd: Decimal = Decimal('0')) -> None:
    if estimated_cost_usd < 0:
        raise ValueError('estimated cost cannot be negative')
    if not endpoint.external:
        return
    if policy.zero_cost_mode or not policy.allow_external_fallback:
        raise ModelPolicyViolation('external model call blocked by policy')
    if state.external_calls + 1 > policy.max_external_calls_per_build:
        raise ModelPolicyViolation('external call limit exceeded')
    if state.external_spend_usd + estimated_cost_usd > policy.external_budget_usd:
        raise ModelPolicyViolation('external model budget exceeded')
    state.external_calls += 1
    state.external_spend_usd += estimated_cost_usd
