"""Which intake interpreter may run right now — the single source of truth for
both the Supervisor (what actually runs) and the API/UI label (what the
customer is told). Fail closed: anything missing means deterministic, $0.

A model (paid) runs only when ALL of these hold:
  OMNI_INTAKE_MODEL=1                       founder switch
  OMNI_INTAKE_MODEL_BUDGET_USD  > 0         per-project conversation cap
  OMNI_INTAKE_DAILY_BUDGET_USD  > 0         cap across all projects, rolling 24 h
  OMNI_INTAKE_CALL_BUDGET_USD   > 0         pre-check reserve: may a turn use a model at all (default 0.01)
  project spent + reserve <= project cap   (a call can never overshoot the cap)
  24 h spent    + reserve <= daily cap
Route: OMNI_INTAKE_VIA_WORKER=1 only. Every paid call is reserved durably
before execution (intake.budget, Issue #12) and runs on the worker, which
holds the provider key. A direct gateway on the API host would bypass the
reservation, so it is refused (deterministic) even when configured.
The spend values here are a cheap pre-check; the hard, concurrency-safe cap
check is the reservation transaction itself.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation

DETERMINISTIC, MODEL_WORKER, MODEL_DIRECT = 'deterministic', 'model-via-worker', 'model-direct'
# Owner 2026-10-30: a pre-check value, not a spend ceiling. 0.01 lets one Venice message (quoted 0.00555) pass;
# the real caps are OMNI_INTAKE_MODEL_BUDGET_USD (per project) and the daily cap, enforced by the reservation.
DEFAULT_CALL_RESERVE = Decimal('0.01')
# Cheapest REAL_EXECUTION_VERIFIED model whose intended tasks include conversation (PROVIDER_MATRIX.json).
RECOMMENDED_MODEL = 'gemini-3.1-flash-lite'
# Token envelope of one intake call (system prompt ~1.0k tokens + message <=4000 chars + JSON reply incl. thinking).
EST_INPUT_TOKENS, EST_OUTPUT_TOKENS = 2200, 700


def _money(name: str, default: str = '0') -> Decimal:
    try:
        v = Decimal(os.getenv(name, default) or default)
    except InvalidOperation:
        return Decimal('0')
    return v if v.is_finite() and v > 0 else Decimal('0')


@dataclass(frozen=True)
class IntakeMode:
    mode: str
    reason: str
    project_cap_usd: str = '0'
    project_spent_usd: str = '0'
    daily_cap_usd: str = '0'
    daily_spent_usd: str = '0'
    call_reserve_usd: str = '0'

    @property
    def paid(self) -> bool:
        return self.mode != DETERMINISTIC

    def to_dict(self) -> dict:
        return asdict(self)


def resolve(*, project_spent: Decimal = Decimal('0'), daily_spent: Decimal = Decimal('0'),
            has_direct_gateway: bool = False, worker_route_available: bool | None = None) -> IntakeMode:
    project_cap = _money('OMNI_INTAKE_MODEL_BUDGET_USD')
    daily_cap = _money('OMNI_INTAKE_DAILY_BUDGET_USD')
    reserve = _money('OMNI_INTAKE_CALL_BUDGET_USD', str(DEFAULT_CALL_RESERVE))
    caps = dict(project_cap_usd=str(project_cap), project_spent_usd=str(project_spent), daily_cap_usd=str(daily_cap),
                daily_spent_usd=str(daily_spent), call_reserve_usd=str(reserve))
    if os.getenv('OMNI_INTAKE_MODEL') != '1':
        return IntakeMode(DETERMINISTIC, 'model switch off (OMNI_INTAKE_MODEL)', **caps)
    if project_cap <= 0:
        return IntakeMode(DETERMINISTIC, 'no per-project intake budget', **caps)
    if daily_cap <= 0:
        return IntakeMode(DETERMINISTIC, 'no daily intake budget', **caps)
    if reserve <= 0:
        return IntakeMode(DETERMINISTIC, 'no per-message reserve', **caps)
    if project_spent + reserve > project_cap:
        return IntakeMode(DETERMINISTIC, 'project intake budget exhausted', **caps)
    if daily_spent + reserve > daily_cap:
        return IntakeMode(DETERMINISTIC, 'daily intake budget exhausted', **caps)
    if os.getenv('OMNI_INTAKE_VIA_WORKER') == '1':
        if worker_route_available is False:
            return IntakeMode(DETERMINISTIC, 'intake worker route is unavailable', **caps)
        return IntakeMode(MODEL_WORKER, 'authorized; routed through the worker', **caps)
    if has_direct_gateway:
        return IntakeMode(DETERMINISTIC, 'direct model calls are disabled: paid calls run only through '
                                         'reservations on the worker (set OMNI_INTAKE_VIA_WORKER=1)', **caps)
    return IntakeMode(DETERMINISTIC, 'no model route (set OMNI_INTAKE_VIA_WORKER=1)', **caps)


def estimate_message_cost(model: str = RECOMMENDED_MODEL, when=None) -> dict:
    """Upper-bound estimate for one intake message from the source-backed price table."""
    from ..intelligence.prices import price_at
    row = price_at(model, when)
    if row is None or row.input_per_million is None or row.output_per_million is None:
        return {'model': model, 'status': 'PRICE_UNVERIFIED'}
    cost = (Decimal(EST_INPUT_TOKENS) * row.input_per_million +
            Decimal(EST_OUTPUT_TOKENS) * row.output_per_million) / Decimal(1_000_000)
    return {'model': model, 'status': 'ESTIMATE', 'input_tokens': EST_INPUT_TOKENS, 'output_tokens': EST_OUTPUT_TOKENS,
            'usd_per_message': str(cost.quantize(Decimal('0.000001'))), 'price_source': row.source_url,
            'price_effective_from': str(row.effective_from)}


def resolve_with_spend(spend, *, has_direct_gateway: bool = False,
                       worker_route_available: bool | None = None) -> IntakeMode:
    """resolve() reading spend lazily: `spend()` -> (project_spent, daily_spent)
    is only called when a model could otherwise run; any failure reading it
    fails closed (deterministic)."""
    optimistic = resolve(has_direct_gateway=True, worker_route_available=worker_route_available)
    if not optimistic.paid:
        return resolve(has_direct_gateway=has_direct_gateway, worker_route_available=worker_route_available)
    try:
        project_spent, daily_spent = spend()
    except Exception as exc:  # spend unknown -> never risk an uncapped call
        return IntakeMode(DETERMINISTIC, f'intake spend unavailable ({type(exc).__name__})')
    return resolve(project_spent=project_spent, daily_spent=daily_spent, has_direct_gateway=has_direct_gateway,
                   worker_route_available=worker_route_available)
