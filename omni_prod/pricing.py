from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from datetime import datetime, timezone
import threading
import os


class PlanCode(str, Enum):
    FREE = 'free'
    AMATEUR = 'amateur'
    PRO = 'pro'
    STUDIO = 'studio'
    ENTERPRISE = 'enterprise'
    # Deprecated aliases (CEO 2026-10-19: Basic->Amateur, Business->Studio).
    # They resolve to the new members so existing references keep working.
    BASIC = 'amateur'
    BUSINESS = 'studio'

    @classmethod
    def _missing_(cls, value):
        # Rows persisted before the rename (creator_subscriptions.plan_code,
        # billing events, Stripe metadata) still say 'basic' / 'business'.
        legacy = {'basic': cls.AMATEUR, 'business': cls.STUDIO}
        if isinstance(value, str):
            return legacy.get(value.strip().lower())
        return None


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


def _env_decimal_renamed(name: str, legacy_name: str, default: str) -> Decimal:
    """New name wins; the pre-rename name (CEO 2026-10-19: Basic->Amateur,
    Business->Studio) is still honoured so an operator value already set in
    Vercel/worker env is not silently dropped."""
    for key in (name, legacy_name):
        raw = os.getenv(key, '').strip()
        if raw:
            return Decimal(raw)
    return Decimal(default)


PLAN_CATALOG: dict[PlanCode, PlanDefinition] = {
    PlanCode.FREE: PlanDefinition(
        PlanCode.FREE, 'Free', Decimal('0'), Decimal('0'), 150, _env_decimal('OMNI_PROVIDER_CAP_FREE_USD','1.05'), 2, 1,
        # CEO 2026-10-19: Free = ZERO + LIGHT, 150 credits (~3 LIGHT builds/month),
        # margin-floor exempt; monthly paid-provider cap = 3 builds x $0.35 LIGHT cap.
        (CostClass.ZERO, CostClass.LIGHT), 'required', False, False, 'standard',
        (
            'up to 3 light builds a month', 'version history', 'rights/IP checks',
            'export with 148AI branding', 'community/self-service support',
        ),
    ),
    PlanCode.AMATEUR: PlanDefinition(
        PlanCode.AMATEUR, 'Amateur', _env_decimal_renamed('OMNI_PRICE_AMATEUR_USD', 'OMNI_PRICE_BASIC_USD','29'), _env_decimal_renamed('OMNI_PRICE_AMATEUR_ANNUAL_USD', 'OMNI_PRICE_BASIC_ANNUAL_USD','290'), 1000, _env_decimal_renamed('OMNI_PROVIDER_CAP_AMATEUR_USD', 'OMNI_PROVIDER_CAP_BASIC_USD','2.50'), 10, 1,
        # CEO 2026-10-19: economy/light only; STANDARD starts at Pro.
        (CostClass.ZERO, CostClass.LIGHT), 'subtle-required', False, False, 'standard',
        (
            'everything in Free', 'budgeted local/open-weight AI', 'light code repair',
            'limited image/audio materialization', 'private projects', 'email support',
        ),
    ),
    PlanCode.PRO: PlanDefinition(
        PlanCode.PRO, 'Pro', _env_decimal('OMNI_PRICE_PRO_USD','99'), _env_decimal('OMNI_PRICE_PRO_ANNUAL_USD','990'), 4500, _env_decimal('OMNI_PROVIDER_CAP_PRO_USD','10'), 50, 1,
        # CEO 2026-10-19: Pro goes up to STANDARD.
        (CostClass.ZERO, CostClass.LIGHT, CostClass.STANDARD),
        'optional', True, False, 'priority',
        (
            'everything in Amateur', 'standard model routing', 'deep repair loops', 'image/audio/music/voice',
            'video/3D within usage budget', 'mobile/game pipelines', 'remove visible 148AI branding', 'priority builds',
        ),
    ),
    PlanCode.STUDIO: PlanDefinition(
        PlanCode.STUDIO, 'Studio', _env_decimal_renamed('OMNI_PRICE_STUDIO_USD', 'OMNI_PRICE_BUSINESS_USD','299'), _env_decimal_renamed('OMNI_PRICE_STUDIO_ANNUAL_USD', 'OMNI_PRICE_BUSINESS_ANNUAL_USD','2990'), 10000, _env_decimal_renamed('OMNI_PROVIDER_CAP_STUDIO_USD', 'OMNI_PROVIDER_CAP_BUSINESS_USD','25'), 250, 5,
        # CEO 2026-10-19: Studio may use every cost class.
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



# CEO 2026-10-19: what an M5 build is, per plan. One class per plan; every
# plan is listed (no silent STANDARD default) and each class must be inside
# that plan's allowed_cost_classes, or reserve() refuses the build.
# Repair budget per plan (founder decision 2026-10-19): the SEAM only, not active. Until OMNI_PLAN_REPAIR_BUDGET=1
# every plan gets DEFAULT_REPAIR_ROUNDS (today's behaviour); the plan values are switched on only after the failure
# taxonomy (smoke/failure-taxonomy.jsonl) shows more rounds pay off. Plans not listed get the default.
DEFAULT_REPAIR_ROUNDS = 3
PLAN_REPAIR_ROUNDS: dict[PlanCode, int] = {PlanCode.AMATEUR: 3, PlanCode.PRO: 5, PlanCode.STUDIO: 8}


def plan_repair_budget_enabled() -> bool:
    return os.getenv('OMNI_PLAN_REPAIR_BUDGET', '0') == '1'


def repair_rounds_for_plan(plan, *, enabled: bool | None = None) -> int:
    """Repair rounds a build of `plan` may use. Off (the default): DEFAULT_REPAIR_ROUNDS for every plan."""
    if not (plan_repair_budget_enabled() if enabled is None else enabled):
        return DEFAULT_REPAIR_ROUNDS
    try:
        code = plan if isinstance(plan, PlanCode) else PlanCode(str(plan).lower())
    except ValueError:
        return DEFAULT_REPAIR_ROUNDS
    return PLAN_REPAIR_ROUNDS.get(code, DEFAULT_REPAIR_ROUNDS)


M5_BUILD_COST_CLASS: dict[PlanCode, CostClass] = {
    PlanCode.FREE: CostClass.LIGHT,
    PlanCode.AMATEUR: CostClass.LIGHT,
    PlanCode.PRO: CostClass.STANDARD,
    PlanCode.STUDIO: CostClass.HEAVY,
    PlanCode.ENTERPRISE: CostClass.EXTREME,
}

# Credits one M5 build costs, per class (CEO 2026-10-19).
M5_CLASS_BUILD_CREDITS: dict[CostClass, int] = {
    CostClass.ZERO: 20, CostClass.LIGHT: 45, CostClass.STANDARD: 200,
    CostClass.ADVANCED: 300, CostClass.HEAVY: 500, CostClass.EXTREME: 1200,
}

# Whole-build model-spend cap per class (CEO 2026-10-19), each overridable by
# its own env var OMNI_BUILD_LLM_CAP_<CLASS>_USD. A class without a cap fails closed.
# Soft cap: admission never refuses on it; overage is recorded (llm_overage).
_M5_CLASS_LLM_CAP_DEFAULT_USD: dict[CostClass, str] = {
    CostClass.ZERO: '0.05', CostClass.LIGHT: '0.35', CostClass.STANDARD: '1.60',
    CostClass.ADVANCED: '3.00', CostClass.HEAVY: '5.50', CostClass.EXTREME: '18.00',
}

# Model allowlist per class (CEO 2026-10-19 02:22): the most a routable model
# may charge per 1M output tokens. None = no price ceiling. ZERO admits only
# models that charge nothing.
M5_CLASS_MAX_OUTPUT_PER_MILLION: dict[CostClass, Decimal | None] = {
    CostClass.ZERO: Decimal('0'), CostClass.LIGHT: Decimal('1.50'), CostClass.STANDARD: Decimal('5.00'),
    CostClass.ADVANCED: Decimal('8.00'), CostClass.HEAVY: None, CostClass.EXTREME: None,
}

# Exempt from the 60% build-margin floor (CEO 2026-10-19): Enterprise is priced by
# contract; Free gets its class cap as an acquisition cost (<= $0.35/build).
MARGIN_FLOOR_EXEMPT_PLANS = frozenset({PlanCode.ENTERPRISE, PlanCode.FREE})

# Actual model spend above this multiple of the class cap is logged as an alert.
LLM_OVERAGE_ALERT_MULTIPLE = Decimal('2')


def _as_plan_code(plan_code) -> PlanCode:
    return plan_code if isinstance(plan_code, PlanCode) else PlanCode(plan_code)


def _as_cost_class(cost_class) -> CostClass:
    return cost_class if isinstance(cost_class, CostClass) else CostClass(cost_class)


def m5_build_cost_class(plan_code) -> CostClass:
    return M5_BUILD_COST_CLASS[_as_plan_code(plan_code)]


def m5_build_terms(plan_code) -> tuple[CostClass, int]:
    """(cost class, credits) one M5 build reserves on this plan."""
    cc = m5_build_cost_class(plan_code)
    return cc, M5_CLASS_BUILD_CREDITS[cc]


def m5_class_llm_cap(cost_class) -> Decimal:
    cc = _as_cost_class(cost_class)
    default = _M5_CLASS_LLM_CAP_DEFAULT_USD.get(cc)
    raw = os.getenv(f'OMNI_BUILD_LLM_CAP_{cc.value.upper()}_USD', '').strip() or default
    if raw is None:
        raise PermissionError(f'no model-spend cap is decided for cost class {cc.value}')
    cap = Decimal(raw)
    if not cap.is_finite() or cap < 0:
        raise PermissionError(f'invalid model-spend cap for cost class {cc.value}')
    return cap


def m5_model_allowed(cost_class, output_per_million, task: str | None = None) -> bool:
    # LIGHT no longer widens its price ceiling for codegen (founder 2026-10-22).
    cc = _as_cost_class(cost_class)
    ceiling = M5_CLASS_MAX_OUTPUT_PER_MILLION[cc]
    return ceiling is None or Decimal(str(output_per_million)) <= ceiling


def m5_revenue_basis(plan, credits: int) -> Decimal | None:
    """Revenue one build represents: monthly price x build credits / plan credits."""
    if plan.monthly_price_usd in (None, Decimal('0')) or not plan.included_credits:
        return None
    return Decimal(plan.monthly_price_usd) * Decimal(int(credits)) / Decimal(int(plan.included_credits))


def m5_llm_budget(plan, cost_class, credits: int, *, non_llm_usd=Decimal('0'),
                  minimum_margin=Decimal('0.60'), internal_qa: bool = False) -> tuple[Decimal, str]:
    """(model budget for one build, basis). The class cap, clipped so the whole
    build (model budget + non-model components) keeps the margin floor.
    Margin-exempt plans and internal QA get the plain cap; a plan with no
    revenue gets 0 (no paid model spend without revenue)."""
    from decimal import ROUND_DOWN
    cap = m5_class_llm_cap(cost_class)
    if internal_qa or plan.code in MARGIN_FLOOR_EXEMPT_PLANS:
        return cap, 'class_cap'
    revenue = m5_revenue_basis(plan, credits)
    if revenue is None:
        return Decimal('0'), 'no_revenue'
    ceiling = (revenue * (Decimal('1') - Decimal(minimum_margin)) - Decimal(str(non_llm_usd))).quantize(
        Decimal('0.0001'), rounding=ROUND_DOWN)
    if ceiling < cap:
        return max(Decimal('0'), ceiling), 'clipped_to_margin_floor'
    return cap, 'class_cap'


def llm_overage(actual_usd, cap_usd) -> dict:
    """Soft cap (CEO 2026-10-19): never refuses; records how far spend went over."""
    actual, cap = Decimal(str(actual_usd)), Decimal(str(cap_usd))
    if actual <= cap:
        status = 'WITHIN_CAP'
    elif actual > cap * LLM_OVERAGE_ALERT_MULTIPLE:
        status = 'OVER_2X_CAP'
    else:
        status = 'OVER_CAP'
    return {'status': status, 'actual_usd': str(actual), 'cap_usd': str(cap),
            'alert_multiple': str(LLM_OVERAGE_ALERT_MULTIPLE)}

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
        'plans': [PLAN_CATALOG[x].public_dict() for x in (PlanCode.FREE, PlanCode.AMATEUR, PlanCode.PRO, PlanCode.STUDIO, PlanCode.ENTERPRISE)],
        'principles': [
            'Free includes a small capped allowance of light paid-model builds.',
            'System bugs and missed original requirements do not consume customer credits.',
            'Paid-provider spend is hard-capped per plan before execution.',
            'Heavy media/compute is metered; no unlimited GPU promise.',
            'Annual defaults equal 10 monthly payments (about two months free) and remain configurable.',
            'Overage is hard-stop by default; no surprise provider spend is silently passed through.',
            'Prices are launch-candidate defaults and remain server-configurable before public billing goes live.',
        ],
    }
