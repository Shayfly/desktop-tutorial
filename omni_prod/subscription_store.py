from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from .db import DatabasePool
from .pricing import PLAN_CATALOG, PlanCode, CostClass, UsageDecision, _COST_CLASS_ESTIMATE_USD
from .provider_pricing import contribution_evidence


class PostgresSubscriptionService:
    """Persistent monthly plan/usage ledger for production creator accounts."""
    def __init__(self, *, pool: DatabasePool):
        self._pool = pool

    def apply_billing_entitlement(self, event) -> dict:
        """One transaction for durable deduplication, ordering and entitlement.

        Requires additive migration 039. It intentionally fails closed if the
        schema is unavailable; no fallback to process-local payment state.
        """
        code = PlanCode(event.plan)
        with self._pool.connection() as conn:
            with conn.transaction():
                self._ensure(event.user_id, conn)
                with conn.cursor() as cur:
                    cur.execute('INSERT INTO creator_billing_watermarks(account_id) VALUES (%s) '
                                'ON CONFLICT(account_id) DO NOTHING', (event.user_id,))
                    cur.execute('SELECT event_created, priority, source_id FROM creator_billing_watermarks '
                                'WHERE account_id=%s FOR UPDATE', (event.user_id,))
                    watermark = cur.fetchone()
                    latest, source = tuple(watermark[:2]), watermark[2]
                    cur.execute('SELECT fingerprint FROM creator_billing_events WHERE event_id=%s',
                                (event.event_id,))
                    previous = cur.fetchone()
                    if previous is not None:
                        if previous[0] != event.fingerprint:
                            raise ValueError('billing event id reused with different contents')
                        return {'processed': False, 'duplicate': True}
                    cur.execute('SELECT event_created, priority FROM creator_billing_events '
                                'WHERE account_id=%s AND source_id=%s '
                                'ORDER BY event_created DESC, priority DESC LIMIT 1',
                                (event.user_id, event.source_id))
                    source_latest = cur.fetchone()
                    cur.execute('INSERT INTO creator_billing_events(event_id, account_id, source_id, '
                                'event_type, event_created, priority, plan_code, fingerprint) '
                                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                                (event.event_id, event.user_id, event.source_id, event.event_type,
                                 event.created, event.priority, code.value, event.fingerprint))
                    if source_latest is not None and event.order <= tuple(source_latest):
                        return {'processed': False, 'stale': True}
                    if event.priority and source and source != event.source_id:
                        return {'processed': False, 'source_mismatch': True}
                    if event.order <= latest:
                        return {'processed': False, 'stale': True}
                    cur.execute('UPDATE creator_subscriptions SET plan_code=%s WHERE user_id=%s',
                                (code.value, event.user_id))
                    cur.execute('UPDATE creator_billing_watermarks SET event_created=%s, priority=%s, source_id=%s '
                                'WHERE account_id=%s', (event.created, event.priority, event.source_id, event.user_id))
        return {'processed': True}

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
                    # Plan metadata changes never replenish the allowance.
                    # Period renewal is separate from entitlement assignment.
                    cur.execute('UPDATE creator_subscriptions SET plan_code=%s WHERE user_id=%s',
                                (code.value, user_id))
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

    # ---- M1 Revision 2: build-credit reservation lifecycle -----------------
    # Additive (reserve/settle/release do not replace authorize/consume, which
    # existing callers such as V28Platform.build() still use for the
    # deterministic zero-cost path). `reserve()` is called from inside an
    # already-open cursor/transaction supplied by the caller (investor_app.py's
    # durable-build handler) so the reservation, build_requests row, build_jobs
    # row and outbox row commit atomically.
    #
    # DEVIATION FROM THE PASTED PATCH: the pasted `reserve()` never received a
    # project_id and inserted the literal string 'UNKNOWN' into
    # credit_reservations.project_id on every call. That column is NOT NULL
    # with no default (see infra/postgres/013_durable_async_builds.sql) and
    # every real reservation needs a real project id for reporting/audit, so a
    # `project_id` parameter was added here and must be threaded through by
    # the caller. Everything else in reserve/settle/release is unchanged from
    # the pasted patch.

    def reserve(self, cur, *, build_id: str, user_id: str, project_id: str, cost_class: str | CostClass, credits: int, category: str='new_build', estimated_provider_cost_usd: Decimal | None=None, internal_qa: bool=False) -> UsageDecision:
        """Atomically reserves credits and enforces limits within a transaction.

        internal_qa=True: the caller already authorized this build against the
        internal QA budget (omni_prod.qa_budget) in the same transaction. The
        customer plan is not read or changed at all; the reservation row is
        marked funding_source='internal_qa' and records the maximum authorized
        cost for settlement and the QA caps (migration 029).
        """
        cc = cost_class if isinstance(cost_class, CostClass) else CostClass(cost_class)
        if credits < 0: raise ValueError('credits must be non-negative')

        if internal_qa:
            estimate = Decimal(str(estimated_provider_cost_usd if estimated_provider_cost_usd is not None else Decimal('0.25')))
            if estimate < 0:
                raise ValueError('estimated provider cost must be non-negative')
            cur.execute(
                "INSERT INTO credit_reservations(build_id, account_id, project_id, credits_reserved, estimated_provider_cost_usd, status, funding_source) VALUES (%s, %s, %s, %s, %s, 'RESERVED', %s) ON CONFLICT (build_id) DO NOTHING",
                (build_id, user_id, project_id, 0, estimate, 'internal_qa'),
            )
            return UsageDecision(True, 'internal_qa', cc.value, str(estimate.quantize(Decimal('0.0001'))), 0, 0, None,
                                 'internal QA budget', False)

        # Load user sub strictly for update
        cur.execute('SELECT plan_code,cycle,credits_used,provider_spend_usd FROM creator_subscriptions WHERE user_id=%s FOR UPDATE', (user_id,))
        row = cur.fetchone()
        if not row: raise RuntimeError('subscription row missing')

        plan_code = row[0]
        cycle = str(row[1])
        used = int(row[2])
        spend = Decimal(str(row[3]))

        current_cycle = self._cycle_now()
        if cycle != current_cycle:
            cur.execute('UPDATE creator_subscriptions SET cycle=%s,credits_used=0,provider_spend_usd=0 WHERE user_id=%s', (current_cycle, user_id))
            cycle, used, spend = current_cycle, 0, Decimal('0')

        plan = PLAN_CATALOG[PlanCode(plan_code) if not isinstance(plan_code, PlanCode) else plan_code]
        estimate = estimated_provider_cost_usd if estimated_provider_cost_usd is not None else Decimal('0.25')
        estimate = Decimal(str(estimate))
        if estimate < 0:
            raise ValueError('estimated provider cost must be non-negative')
        user_billable = category not in {'system_bug','missing_requirement'}
        charge = credits if user_billable else 0

        allowed, reason = True, 'authorized'
        if cc not in plan.allowed_cost_classes:
            allowed, reason = False, 'cost class not included in plan'
        elif plan.included_credits and used + charge > plan.included_credits:
            allowed, reason = False, 'monthly credits exhausted'
        elif plan.paid_provider_budget_usd is not None and spend + estimate > plan.paid_provider_budget_usd:
            allowed, reason = False, 'paid-provider budget exhausted'

        decision = UsageDecision(
            allowed, plan.code.value, cc.value, str(estimate.quantize(Decimal('0.0001'))), charge,
            max(0, plan.included_credits - (used + charge)) if plan.included_credits else 0,
            None if plan.paid_provider_budget_usd is None else str(max(Decimal('0'), plan.paid_provider_budget_usd-(spend+estimate)).quantize(Decimal('0.0001'))),
            reason, user_billable,
        )

        if allowed:
            cur.execute(
                "INSERT INTO credit_reservations(build_id, account_id, project_id, credits_reserved, estimated_provider_cost_usd, status) VALUES (%s, %s, %s, %s, %s, 'RESERVED') ON CONFLICT (build_id) DO NOTHING",
                (build_id, user_id, project_id, charge, estimate)
            )
            # Only update if the insert wasn't ignored due to conflict (idempotency)
            if cur.rowcount == 1:
                cur.execute('UPDATE creator_subscriptions SET credits_used=%s, provider_spend_usd=%s WHERE user_id=%s', (used + charge, spend + estimate, user_id))

        return decision

    def settle(
        self, *, build_id: str, actual_provider_cost_usd: Decimal | None = None,
        revenue_usd: Decimal | None = None, infra_cost_usd: Decimal = Decimal('0'),
        payment_fee_usd: Decimal = Decimal('0'), support_allocation_usd: Decimal = Decimal('0'),
    ) -> dict | None:
        """Resolve one durable reservation without promoting estimates to actuals.

        The reservation amount remains a conservative settlement basis when the
        provider does not report an actual cost.  Contribution evidence is
        returned only when an explicit revenue basis is supplied; callers can
        persist that evidence in their durable build/deployment record.
        """
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("SELECT account_id, status, estimated_provider_cost_usd, funding_source FROM credit_reservations WHERE build_id=%s FOR UPDATE", (build_id,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    user_id, status, estimated_cost = row[0], row[1], Decimal(str(row[2]))
                    # Internal QA reservations never move customer plan counters.
                    customer_plan = row[3] != 'internal_qa'

                    if status != 'RESERVED':
                        return None

                    reported_actual = (
                        None if actual_provider_cost_usd is None
                        else Decimal(str(actual_provider_cost_usd))
                    )
                    if reported_actual is not None and reported_actual < 0:
                        raise ValueError('actual provider cost must be >= 0')

                    settlement_basis = estimated_cost if reported_actual is None else reported_actual
                    settled = settlement_basis

                    if not customer_plan:
                        pass
                    elif settlement_basis < estimated_cost:
                        refund = estimated_cost - settlement_basis
                        cur.execute("UPDATE creator_subscriptions SET provider_spend_usd = GREATEST(0, provider_spend_usd - %s) WHERE user_id=%s", (refund, user_id))
                    elif settlement_basis > estimated_cost:
                        shortfall = settlement_basis - estimated_cost
                        cur.execute("SELECT plan_code, provider_spend_usd FROM creator_subscriptions WHERE user_id=%s FOR UPDATE", (user_id,))
                        sub_row = cur.fetchone()
                        if not sub_row:
                            raise RuntimeError('subscription row missing during settlement')
                        plan = PLAN_CATALOG[PlanCode(sub_row[0])]
                        current_spend = Decimal(str(sub_row[1]))

                        if plan.paid_provider_budget_usd is not None:
                            budget_remaining = max(Decimal('0'), plan.paid_provider_budget_usd - current_spend)
                            charge = min(shortfall, budget_remaining)
                            settled = estimated_cost + charge
                        else:
                            charge = shortfall

                        cur.execute("UPDATE creator_subscriptions SET provider_spend_usd = provider_spend_usd + %s WHERE user_id=%s", (charge, user_id))

                    cur.execute("UPDATE credit_reservations SET status='SETTLED', resolved_at=now(), actual_provider_cost_usd=%s, settled_provider_cost_usd=%s WHERE build_id=%s", (reported_actual, settled, build_id))

                    result = {
                        'build_id': build_id,
                        'actual_provider_cost_usd': reported_actual,
                        'settled_provider_cost_usd': settled,
                        'provider_cost_truth': 'ACTUAL' if reported_actual is not None else 'CONSERVATIVE_RESERVATION',
                        'gross_contribution_usd': None,
                        'contribution_margin': None,
                    }
                    if revenue_usd is not None:
                        economics = contribution_evidence(
                            revenue_usd=Decimal(str(revenue_usd)),
                            actual_provider_cost_usd=reported_actual,
                            conservative_provider_cost_usd=estimated_cost,
                            infra_cost_usd=Decimal(str(infra_cost_usd)),
                            payment_fee_usd=Decimal(str(payment_fee_usd)),
                            support_allocation_usd=Decimal(str(support_allocation_usd)),
                        )
                        result['provider_cost_truth'] = economics['provider_cost_truth'] if reported_actual is not None else 'CONSERVATIVE_RESERVATION'
                        result['gross_contribution_usd'] = economics['contribution_usd']
                        result['contribution_margin'] = economics['contribution_margin']
                    return result

    def release(self, *, build_id: str) -> None:
        with self._pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("SELECT account_id, status, credits_reserved, estimated_provider_cost_usd, funding_source FROM credit_reservations WHERE build_id=%s FOR UPDATE", (build_id,))
                    row = cur.fetchone()
                    if not row: return
                    user_id, status, credits_reserved, estimated_cost = row[0], row[1], row[2], Decimal(str(row[3]))

                    if status != 'RESERVED': return

                    cur.execute("UPDATE credit_reservations SET status='RELEASED', resolved_at=now() WHERE build_id=%s", (build_id,))
                    if row[4] == 'internal_qa':
                        return  # internal QA never touched the customer plan counters
                    cur.execute("UPDATE creator_subscriptions SET credits_used = GREATEST(0, credits_used - %s), provider_spend_usd = GREATEST(0, provider_spend_usd - %s) WHERE user_id=%s", (credits_reserved, estimated_cost, user_id))
