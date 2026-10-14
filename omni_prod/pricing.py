from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from datetime import datetime, timezone
import threading
import os


class PlanCode(str, Enum):
    FREE = 'free'
    BASIC = 'basic'
    PRO = 'pro'
    BUSINESS = 'business'
    ENTERPRISE = 'enterprise'


class CostClass(str, Enum):
    ZERO = 'zero'
    LIGHT = 'light'
    STANDARD = 'standard'
    ADVANCED = 'advanced'
    HEAVY = 'heavy'
    EXTREME = 'extreme'


_COST_CLASS_ESTIMATE_USD = {
    CostClass.ZERO: Decimal('0'),
    CostClass.LIGHT: Decimal('0.03'),
    CostClass.STANDARD: Decimal('0.12'),
    CostClass.ADVANCED: Decimal('0.45'),
    CostClass.HEAVY: Decimal('2.00'),
    CostClass.EXTREME: Decimal('5.00'),
}


@dataclass(frozen=True)
class PlanDefinition:
    code: PlanCode
    name: str
    monthly_price_usd: Decimal | None
    annual_price_usd: Decimal | None
    included_credits: int
    paid_provider_budget_usd: Decimal | None
    max_projects: int | None
    seats: int | None
    allowed_cost_classes: tuple[CostClass, ...]
    branding: str
    removable_branding: bool
    white_label: bool
    priority: str
    features: tuple[str, ...]
    status: str = 'prelaunch-proposed'

    def variable_margin_floor(self) -> Decimal | None:
        if self.monthly_price_usd in (None, Decimal('0')) or self.paid_provider_budget_usd is None:
            return None
        return ((self.monthly_price_usd - self.paid_provider_budget_usd) / self.monthly_price_usd).quantize(Decimal('0.001'))

    def public_dict(self) -> dict:
        """Customer-facing plan view (decision 2026-10-07 #29). Internal unit
        economics (provider budget, margin floor) are never included; the
        closed field list is enforced by tests/test_public_pricing_economics.py."""
        full = self.to_dict()
        return {k: full[k] for k in PUBLIC_PLAN_FIELDS}

    def to_dict(self) -> dict:
        """Internal view, including unit economics. Never return it to customers."""
        d = asdict(self)
        d['code'] = self.code.value
        d['monthly_price_usd'] = None if self.monthly_price_usd is None else str(self.monthly_price_usd)
        d['annual_price_usd'] = None if self.annual_price_usd is None else str(self.annual_price_usd)
        d['paid_provider_budget_usd'] = None if self.paid_provider_budget_usd is None else str(self.paid_provider_budget_usd)
        d['allowed_cost_classes'] = [x.value for x in self.allowed_cost_classes]
        margin = self.variable_margin_floor()
        d['variable_margin_floor'] = None if margin is None else str(margin)
        return d

PUBLIC_PLAN_FIELDS = ('code', 'name', 'monthly_price_usd', 'annual_price_usd', 'included_credits', 'max_projects',
                      'seats', 'allowed_cost_classes', 'branding', 'removable_branding', 'white_label', 'priority',
                      'features', 'status')


def customer_usage_view(snapshot: dict) -> dict:
    """Customer-facing subscription view: plan, credits used/remaining, cycle.
    Provider spend and provider budget stay internal (decision 2026-10-07 #29)."""
    plan = snapshot['plan']
    code = plan.code if isinstance(plan, PlanDefinition) else PlanCode(plan['code'])
    return {
        'plan': PLAN_CATALOG[code].public_dict(),
        'credits_used': snapshot.get('credits_used'),
        'credits_remaining': snapshot.get('credits_remaining'),
        'cycle': snapshot.get('cycle'),
    }


def _env_decimal(name: str, default: str) -> Decimal:
    raw=os.getenv(name,'').strip()
    return Decimal(raw) if raw else Decimal(default)


PLAN_CATALOG: dict[PlanCode, PlanDefinition] = {
    PlanCode.FREE: PlanDefinition(
        PlanCode.FREE, 'Free', Decimal('0'), Decimal('0'), 150, Decimal('0'), 2, 1,
        (CostClass.ZERO,), 'required', False, False, 'standard',
        (
            'deterministic/local zero-paid-provider builds', 'version history', 'rights/IP checks',
            'export with 148AI branding', 'community/self-service support',
        ),
    ),
    PlanCode.BASIC: PlanDefinition(
        PlanCode.BASIC, 'Basic', _env_decimal('OMNI_PRICE_BASIC_USD','12'), _env_decimal('OMNI_PRICE_BASIC_ANNUAL_USD','120'), 900, _env_decimal('OMNI_PROVIDER_CAP_BASIC_USD','2.50'), 10, 1,
        (CostClass.ZERO, CostClass.LIGHT, CostClass.STANDARD), 'subtle-required', False, False, 'standard',
        (
            'everything in Free', 'budgeted local/open-weight AI', 'standard code repair',
            'limited image/audio materialization', 'private projects', 'email support',
        ),
    ),
    PlanCode.PRO: PlanDefinition(
        PlanCode.PRO, 'Pro', _env_decimal('OMNI_PRICE_PRO_USD','39'), _env_decimal('OMNI_PRICE_PRO_ANNUAL_USD','390'), 4000, _env_decimal('OMNI_PROVIDER_CAP_PRO_USD','10'), 50, 1,
        (CostClass.ZERO, CostClass.LIGHT, CostClass.STANDARD, CostClass.ADVANCED, CostClass.HEAVY),
        'optional', True, False, 'priority',
        (
            'everything in Basic', 'advanced model routing', 'deep repair loops', 'image/audio/music/voice',
            'video/3D within usage budget', 'mobile/game pipelines', 'remove visible 148AI branding', 'priority builds',
        ),
    ),
    PlanCode.BUSINESS: PlanDefinition(
        PlanCode.BUSINESS, 'Business', _env_decimal('OMNI_PRICE_BUSINESS_USD','99'), _env_decimal('OMNI_PRICE_BUSINESS_ANNUAL_USD','990'), 12000, _env_decimal('OMNI_PROVIDER_CAP_BUSINESS_USD','25'), 250, 5,
        tuple(CostClass), 'white-label-eligible', True, True, 'high',
        (
            'everything in Pro', '5 seats', 'team/RBAC workflows', 'API access', 'white-label exports',
            'higher media/GPU budget', 'shared projects', 'audit/Company OS', 'priority support',
        ),
    ),
    PlanCode.ENTERPRISE: PlanDefinition(
        PlanCode.ENTERPRISE, 'Enterprise', None, None, 0, None, None, None,
        tuple(CostClass), 'contract', True, True, 'dedicated',
        (
            'custom usage contract', 'SSO/SCIM target', 'custom data residency', 'dedicated capacity',
            'custom SLA/support', 'security/compliance review',
        ),
    ),
}


@dataclass(frozen=True)
class UsageDecision:
    allowed: bool
    plan: str
    cost_class: str
    estimated_provider_cost_usd: str
    credits: int
    credits_remaining_after: int
    provider_budget_remaining_after_usd: str | None
    reason: str
    user_billable: bool


@dataclass
class UsageState:
    plan: PlanCode = PlanCode.FREE
    credits_used: int = 0
    provider_spend_usd: Decimal = Decimal('0')
    cycle: str = ''


class SubscriptionService:
    """In-memory reviewer implementation of plan assignment and usage guardrails.

    Payment-provider webhooks should be the only source of paid-plan changes in
    production. The service intentionally has no self-service `upgrade()` method.
    """

    def __init__(self):
        self._state: dict[str, UsageState] = {}
        self._lock = threading.RLock()
        self._billing_events: dict[str, str] = {}
        self._billing_order: dict[str, tuple[int, int]] = {}
        self._billing_source: dict[str, str] = {}
        self._billing_source_order: dict[tuple[str, str], tuple[int, int]] = {}

    def apply_billing_entitlement(self, event) -> dict:
        """Reviewer equivalent of the durable, atomic Postgres event handler."""
        with self._lock:
            PlanCode(event.plan)
            previous = self._billing_events.get(event.event_id)
            if previous is not None:
                if previous != event.fingerprint:
                    raise ValueError('billing event id reused with different contents')
                return {'processed': False, 'duplicate': True}
            self._billing_events[event.event_id] = event.fingerprint
            source_key = event.user_id, event.source_id
            if event.order <= self._billing_source_order.get(source_key, (-1, 0)):
                return {'processed': False, 'stale': True}
            # Retain cancellation tombstones even for a different current
            # subscription: its delayed checkout must never activate it later.
            self._billing_source_order[source_key] = event.order
            if event.priority and self._billing_source.get(event.user_id, event.source_id) != event.source_id:
                return {'processed': False, 'source_mismatch': True}
            if event.order <= self._billing_order.get(event.user_id, (-1, 0)):
                return {'processed': False, 'stale': True}
            self.assign_plan(event.user_id, event.plan)
            self._billing_order[event.user_id] = event.order
            self._billing_source[event.user_id] = event.source_id
            return {'processed': True}

    @staticmethod
    def _cycle_now() -> str:
        return datetime.now(timezone.utc).strftime('%Y-%m')

    def _get(self, user_id: str) -> UsageState:
        with self._lock:
            state = self._state.setdefault(user_id, UsageState(cycle=self._cycle_now()))
            current = self._cycle_now()
            if state.cycle != current:
                state.credits_used = 0
                state.provider_spend_usd = Decimal('0')
                state.cycle = current
            return state

    def plan_for(self, user_id: str) -> PlanDefinition:
        return PLAN_CATALOG[self._get(user_id).plan]

    def assign_plan(self, user_id: str, plan: str | PlanCode) -> PlanDefinition:
        code = plan if isinstance(plan, PlanCode) else PlanCode(plan)
        with self._lock:
            state = self._get(user_id)
            state.plan = code
            # Entitlement changes are not a new billing-period grant. Keep
            # usage, spend and outstanding reservations across webhook retries,
            # updates, upgrades and downgrades.
        return PLAN_CATALOG[code]

    def snapshot(self, user_id: str) -> dict:
        state = self._get(user_id)
        plan = PLAN_CATALOG[state.plan]
        return {
            'plan': plan.to_dict(),
            'credits_used': state.credits_used,
            'credits_remaining': max(0, plan.included_credits - state.credits_used) if plan.included_credits else None,
            'cycle': state.cycle,
            'provider_spend_usd': str(state.provider_spend_usd.quantize(Decimal('0.0001'))),
            'provider_budget_remaining_usd': None if plan.paid_provider_budget_usd is None else str(max(Decimal('0'), plan.paid_provider_budget_usd - state.provider_spend_usd).quantize(Decimal('0.0001'))),
        }

    def authorize(
        self,
        *,
        user_id: str,
        cost_class: str | CostClass,
        credits: int,
        category: str = 'new_build',
        estimated_provider_cost_usd: Decimal | None = None,
    ) -> UsageDecision:
        cc = cost_class if isinstance(cost_class, CostClass) else CostClass(cost_class)
        if credits < 0:
            raise ValueError('credits must be non-negative')
        state = self._get(user_id)
        plan = PLAN_CATALOG[state.plan]
        estimate = estimated_provider_cost_usd if estimated_provider_cost_usd is not None else _COST_CLASS_ESTIMATE_USD[cc]
        if estimate < 0:
            raise ValueError('estimated provider cost must be non-negative')

        # Omni-originated defects never consume customer credits. They are still
        # metered as company cost so margin and abuse controls remain truthful.
        user_billable = category not in {'system_bug', 'missing_requirement'}
        charge_credits = credits if user_billable else 0

        if cc not in plan.allowed_cost_classes:
            return self._deny(state, plan, cc, estimate, charge_credits, user_billable, 'cost class not included in plan')
        if plan.included_credits and state.credits_used + charge_credits > plan.included_credits:
            return self._deny(state, plan, cc, estimate, charge_credits, user_billable, 'monthly credits exhausted')
        if plan.paid_provider_budget_usd is not None and state.provider_spend_usd + estimate > plan.paid_provider_budget_usd:
            return self._deny(state, plan, cc, estimate, charge_credits, user_billable, 'paid-provider budget exhausted')

        credits_after = state.credits_used + charge_credits
        spend_after = state.provider_spend_usd + estimate
        return UsageDecision(
            True, plan.code.value, cc.value, str(estimate.quantize(Decimal('0.0001'))), charge_credits,
            max(0, plan.included_credits - credits_after) if plan.included_credits else 0,
            None if plan.paid_provider_budget_usd is None else str(max(Decimal('0'), plan.paid_provider_budget_usd - spend_after).quantize(Decimal('0.0001'))),
            'authorized', user_billable,
        )

    def consume(self, *, user_id: str, decision: UsageDecision, actual_provider_cost_usd: Decimal | None = None) -> dict:
        if not decision.allowed:
            raise PermissionError(decision.reason)
        with self._lock:
            state = self._get(user_id)
            plan = PLAN_CATALOG[state.plan]
            cost = Decimal(decision.estimated_provider_cost_usd) if actual_provider_cost_usd is None else actual_provider_cost_usd
            if cost < 0:
                raise ValueError('actual provider cost must be non-negative')
            new_spend = state.provider_spend_usd + cost
            if plan.paid_provider_budget_usd is not None and new_spend > plan.paid_provider_budget_usd:
                raise PermissionError('actual provider cost exceeds plan budget')
            state.credits_used += decision.credits
            state.provider_spend_usd = new_spend
        return self.snapshot(user_id)

    @staticmethod
    def _deny(state: UsageState, plan: PlanDefinition, cc: CostClass, estimate: Decimal, credits: int, user_billable: bool, reason: str) -> UsageDecision:
        return UsageDecision(
            False, plan.code.value, cc.value, str(estimate.quantize(Decimal('0.0001'))), credits,
            max(0, plan.included_credits - state.credits_used) if plan.included_credits else 0,
            None if plan.paid_provider_budget_usd is None else str(max(Decimal('0'), plan.paid_provider_budget_usd - state.provider_spend_usd).quantize(Decimal('0.0001'))),
            reason, user_billable,
        )


def catalog_payload() -> dict:
    return {
        'currency': 'USD',
        'pricing_status': 'prelaunch-proposed-configurable',
        'plans': [PLAN_CATALOG[x].public_dict() for x in (PlanCode.FREE, PlanCode.BASIC, PlanCode.PRO, PlanCode.BUSINESS, PlanCode.ENTERPRISE)],
        'principles': [
            'Free uses zero-paid-provider paths only.',
            'System bugs and missed original requirements do not consume customer credits.',
            'Paid-provider spend is hard-capped per plan before execution.',
            'Heavy media/compute is metered; no unlimited GPU promise.',
            'Annual defaults equal 10 monthly payments (about two months free) and remain configurable.',
            'Overage is hard-stop by default; no surprise provider spend is silently passed through.',
            'Prices are launch-candidate defaults and remain server-configurable before public billing goes live.',
        ],
    }
