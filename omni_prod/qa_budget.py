"""Internal QA / staging budget for platform verification builds (Golden E2E).

Founder decisions 2026-10-07 (#8, #23, #24): QA builds are NOT customer free
tier and NOT a fictional paid plan. They are funded by an explicit internal
budget with small hard caps, recorded as `funding_source = internal_qa` on the
reservation and in the build's economics evidence.

Rules (all fail closed):
* Enabled only when `OMNI_ENV=staging`; never in production
  (`OMNI_ENV=production` or `VERCEL_ENV=production`).
* Only accounts with an active, explicit `INTERNAL_QA` entitlement in the
  `staging` scope (table `internal_entitlements`, migration 029) qualify. The
  grant is bound to the account id and audited (see omni_prod.entitlements).
* `OMNI_QA_BUILD_MAX_USD`: hard cap on one build's maximum authorized cost.
* `OMNI_QA_BUDGET_TOTAL_USD`: hard cap on all internal-QA-funded reservations
  ever made (settled cost where known, else the reserved maximum), checked
  under a transaction-scoped advisory lock so concurrent builds cannot
  overshoot. Customer-plan reservations never count, and QA reservations never
  touch the customer plan counters.
* Missing or invalid caps mean QA funding is unavailable.

Counting real money (founder 2026-10-08: "$10 real, all providers together").
A finished build or change counts its recorded provider spend: the actual
provider-reported cost when every call reported usage, otherwise the build's
spend ledger (served calls at tokens x price, refused calls at $0, unanswered
calls at their worst case) -- never the whole 0.50 reservation, which made
$9.15 "used" while Google billed about $0.30. A running reservation still
counts at its maximum. `OMNI_QA_BUDGET_SINCE` (ISO time) starts the count at a
known point: before 2026-10-08 17:12 UTC every model call ran on Gemini's free
tier or was refused for lack of credit, so it cost nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import os
from typing import Mapping

_QA_LOCK_ID = 781234992
QA_ENTITLEMENT = 'INTERNAL_QA'
QA_ENVIRONMENT = 'staging'


class QABudgetDenied(PermissionError):
    pass


def _decimal(value: str | None) -> Decimal | None:
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        return None
    return d if d.is_finite() and d > 0 else None


@dataclass(frozen=True)
class QABudgetPolicy:
    enabled: bool
    environment: str
    build_max_usd: Decimal | None
    total_usd: Decimal | None
    reason: str
    since: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> 'QABudgetPolicy':
        env = os.environ if env is None else env
        environment = env.get('OMNI_ENV', '').strip().lower()
        build_max = _decimal(env.get('OMNI_QA_BUILD_MAX_USD'))
        total = _decimal(env.get('OMNI_QA_BUDGET_TOTAL_USD'))
        if environment == 'production' or env.get('VERCEL_ENV', '').strip().lower() == 'production':
            return cls(False, environment, build_max, total, 'internal QA funding is disabled in production')
        if environment != QA_ENVIRONMENT:
            return cls(False, environment, build_max, total, 'internal QA funding requires OMNI_ENV=staging')
        if build_max is None or total is None:
            return cls(False, environment, build_max, total, 'QA caps are not configured')
        if build_max > total:
            return cls(False, environment, build_max, total, 'QA per-build cap exceeds total cap')
        since = (env.get('OMNI_QA_BUDGET_SINCE') or '').strip() or None
        if since is not None:
            from datetime import datetime
            try:
                datetime.fromisoformat(since.replace('Z', '+00:00'))
            except ValueError:
                return cls(False, environment, build_max, total, 'OMNI_QA_BUDGET_SINCE is not an ISO time')
        return cls(True, environment, build_max, total, 'enabled', since)

    def evidence(self) -> dict:
        return {'funding_source': 'internal_qa', 'entitlement': QA_ENTITLEMENT, 'environment': self.environment,
                'qa_build_max_usd': str(self.build_max_usd), 'qa_total_usd': str(self.total_usd),
                'qa_counted_since': self.since}


def qa_used_usd(cur, since: str | None = None) -> Decimal:
    """Real QA spend so far (see the module docstring for what counts)."""
    cur.execute(
        """
        SELECT COALESCE(SUM(CASE
                   WHEN r.status IN ('SETTLED', 'RELEASED') THEN COALESCE(
                        r.actual_provider_cost_usd,
                        NULLIF(COALESCE(b.evidence_json->>'provider_spend_usd', m.evidence_json->>'provider_spend_usd'), '')::numeric,
                        r.settled_provider_cost_usd,
                        CASE WHEN r.status = 'RELEASED' THEN 0 ELSE r.estimated_provider_cost_usd END)
                   ELSE r.estimated_provider_cost_usd END), 0)
        FROM credit_reservations r
        LEFT JOIN build_jobs b ON b.id = r.build_id
        LEFT JOIN modification_requests m ON m.id = r.build_id
        WHERE r.funding_source = 'internal_qa'
          AND (%s::timestamptz IS NULL OR r.created_at >= %s::timestamptz)
        """,
        (since, since),
    )
    return Decimal(str(cur.fetchone()[0] or 0))


def active_entitlement(cur, policy: QABudgetPolicy, account_id: str) -> dict | None:
    """The account's active INTERNAL_QA grant for this environment, or None."""
    if not policy.enabled or not account_id:
        return None
    cur.execute(
        "SELECT id, granted_at FROM internal_entitlements "
        "WHERE account_id = %s AND entitlement = %s AND environment = %s AND revoked_at IS NULL",
        (account_id, QA_ENTITLEMENT, policy.environment),
    )
    row = cur.fetchone()
    return None if row is None else {'entitlement_id': row[0], 'granted_at': str(row[1])}


def entitled_account(pool, policy: QABudgetPolicy, account_id: str) -> bool:
    """The single QA-funding decision used by the plan view AND build admission.

    Live evidence 2026-10-07 (STATUS.md): the plan view priced builds as the
    customer plan while admission funded them from internal QA, so a QA build
    showed NOT_AUTHORIZED and could not be started. Both now ask this. Raises
    whatever the store raises; the caller maps it to an explicit error.
    """
    if not policy.enabled or pool is None or not account_id:
        return False
    with pool.connection() as conn:
        with conn.cursor() as cur:
            return active_entitlement(cur, policy, account_id) is not None


def preauthorize_qa_build(pool, policy: QABudgetPolicy, *, account_id: str, max_cost_usd: Decimal) -> dict:
    """Plan-view twin of authorize_qa_build: the same checks, read-only.

    Runs inside its own transaction; nothing is written (the advisory lock is
    transaction-scoped and released at the end). Raises QABudgetDenied exactly
    when admission would.
    """
    with pool.connection() as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                return authorize_qa_build(cur, policy, account_id=account_id, max_cost_usd=max_cost_usd)


def authorize_qa_build(cur, policy: QABudgetPolicy, *, account_id: str, max_cost_usd: Decimal) -> dict:
    """Check entitlement and both caps inside the build's reservation transaction.

    Returns evidence on success; raises QABudgetDenied otherwise. The
    entitlement is re-read under the lock, so a grant revoked after the
    pre-check cannot fund the build.
    """
    if not policy.enabled:
        raise QABudgetDenied(f'internal QA funding unavailable: {policy.reason}')
    max_cost_usd = Decimal(str(max_cost_usd))
    if max_cost_usd > policy.build_max_usd:
        raise QABudgetDenied(f'QA build maximum {max_cost_usd} exceeds per-build cap {policy.build_max_usd}')
    cur.execute('SELECT pg_advisory_xact_lock(%s)', (_QA_LOCK_ID,))
    grant = active_entitlement(cur, policy, account_id)
    if grant is None:
        raise QABudgetDenied(f'no active {QA_ENTITLEMENT} entitlement for this account in {policy.environment}')
    used = qa_used_usd(cur, policy.since)
    if used + max_cost_usd > policy.total_usd:
        raise QABudgetDenied(f'QA total budget exhausted: used {used} + this build {max_cost_usd} > cap {policy.total_usd}')
    return {**policy.evidence(), **grant, 'qa_used_before_usd': str(used), 'qa_this_build_max_usd': str(max_cost_usd)}
