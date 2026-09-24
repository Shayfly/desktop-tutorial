from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from .db import DatabasePool
from .pricing import PLAN_CATALOG, PlanCode, CostClass, UsageDecision, _COST_CLASS_ESTIMATE_USD


class PostgresSubscriptionService:
    """Persistent monthly plan/usage ledger for production creator accounts."""
    def __init__(self, *, pool: DatabasePool):
        self._pool = pool

    @staticmethod
    def _cycle_now() -> str:
        return datetime.now(timezone.utc).strftime('%Y-%m')

    def _ensure(self, user_id: str, conn) -> None:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO creator_subscriptions(user_id,plan_code,cycle,credits_used,provider_spend_usd) VALUES(%s,'free',%s,0,0) ON CONFLICT(user_id) DO NOTHING",
                (user_id, self._cycle_now()),
            )

    def _load(self, user_id: str, conn, *, for_update: bool = False):
        self._ensure(user_id, conn)
        suffix = ' FOR UPDATE' if for_update else ''
        with conn.cursor() as cur:
            cur.execute('SELECT plan_code,cycle,credits_used,provider_spend_usd FROM creator_subscriptions WHERE user_id=%s'+suffix, (user_id,))
            row = cur.fetchone()
        if not row:
            raise RuntimeError('subscription row missing')
        plan = PlanCode(str(row[0])); cycle = str(row[1]); credits = int(row[2]); spend = Decimal(str(row[3]))
        current = self._cycle_now()
        if cycle != current:
            with conn.cursor() as cur:
                cur.execute('UPDATE creator_subscriptions SET cycle=%s,credits_used=0,provider_spend_usd=0 WHERE user_id=%s', (current, user_id))
            cycle, credits, spend = current, 0, Decimal('0')
        return plan, cycle, credits, spend

    def plan_for(self, user_id: str):
        with self._pool.connection() as conn:
            with conn.transaction():
                plan, _, _, _ = self._load(user_id, conn)
        return PLAN_CATALOG[plan]

    def assign_plan(self, user_id: str, plan: str | PlanCode):
        code = plan if isinstance(plan, PlanCode) else PlanCode(plan)
        with self._pool.connection() as conn:
            with conn.transaction():
                self._ensure(user_id, conn)
                with conn.cursor() as cur:
                    cur.execute('UPDATE creator_subscriptions SET plan_code=%s,cycle=%s,credits_used=0,provider_spend_usd=0 WHERE user_id=%s',
                                (code.value, self._cycle_now(), user_id))
        return PLAN_CATALOG[code]

    def snapshot(self, user_id: str) -> dict:
        with self._pool.connection() as conn:
            with conn.transaction():
                code, cycle, credits, spend = self._load(user_id, conn)
        plan = PLAN_CATALOG[code]
        return {
            'plan': plan.to_dict(), 'credits_used': credits,
            'credits_remaining': max(0, plan.included_credits - credits) if plan.included_credits else None,
            'cycle': cycle, 'provider_spend_usd': str(spend.quantize(Decimal('0.0001'))),
            'provider_budget_remaining_usd': None if plan.paid_provider_budget_usd is None else str(max(Decimal('0'), plan.paid_provider_budget_usd-spend).quantize(Decimal('0.0001'))),
        }

    def authorize(self, *, user_id: str, cost_class: str | CostClass, credits: int, category: str='new_build', estimated_provider_cost_usd: Decimal | None=None) -> UsageDecision:
        cc = cost_class if isinstance(cost_class, CostClass) else CostClass(cost_class)
        if credits < 0: raise ValueError('credits must be non-negative')
        with self._pool.connection() as conn:
            with conn.transaction():
                code, _, used, spend = self._load(user_id, conn)
        plan = PLAN_CATALOG[code]
        estimate = estimated_provider_cost_usd if estimated_provider_cost_usd is not None else _COST_CLASS_ESTIMATE_USD[cc]
        user_billable = category not in {'system_bug','missing_requirement'}
        charge = credits if user_billable else 0
        reason = 'authorized'; allowed = True
        if cc not in plan.allowed_cost_classes: allowed, reason = False, 'cost class not included in plan'
        elif plan.included_credits and used + charge > plan.included_credits: allowed, reason = False, 'monthly credits exhausted'
        elif plan.paid_provider_budget_usd is not None and spend + estimate > plan.paid_provider_budget_usd: allowed, reason = False, 'paid-provider budget exhausted'
        return UsageDecision(
            allowed, code.value, cc.value, str(estimate.quantize(Decimal('0.0001'))), charge,
            max(0, plan.included_credits - (used + charge)) if plan.included_credits else 0,
            None if plan.paid_provider_budget_usd is None else str(max(Decimal('0'), plan.paid_provider_budget_usd-(spend+estimate)).quantize(Decimal('0.0001'))),
            reason, user_billable,
        )

    def consume(self, *, user_id: str, decision: UsageDecision, actual_provider_cost_usd: Decimal | None=None) -> dict:
        if not decision.allowed: raise PermissionError(decision.reason)
        cost = Decimal(decision.estimated_provider_cost_usd) if actual_provider_cost_usd is None else actual_provider_cost_usd
        with self._pool.connection() as conn:
            with conn.transaction():
                code, _, used, spend = self._load(user_id, conn, for_update=True)
                plan = PLAN_CATALOG[code]
                new_spend = spend + cost
                if plan.paid_provider_budget_usd is not None and new_spend > plan.paid_provider_budget_usd:
                    raise PermissionError('actual provider cost exceeds plan budget')
                new_credits = used + decision.credits
                if plan.included_credits and new_credits > plan.included_credits:
                    raise PermissionError('monthly credits exhausted')
                with conn.cursor() as cur:
                    cur.execute('UPDATE creator_subscriptions SET credits_used=%s,provider_spend_usd=%s WHERE user_id=%s',
                                (new_credits, new_spend, user_id))
        return self.snapshot(user_id)
