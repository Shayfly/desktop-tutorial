"""Internal QA / staging budget for platform verification builds (Golden E2E).

Founder decision 2026-10-07: QA builds are NOT customer free tier and NOT a
fictional paid plan. They are funded by an explicit internal budget with
small hard caps, recorded as `funding_source = internal_qa` in the build's
economics evidence.

Rules (all fail closed):
* Disabled in production (`OMNI_ENV=production` or `VERCEL_ENV=production`).
* Only accounts listed in `OMNI_QA_ACCOUNT_EMAILS` qualify.
* `OMNI_QA_BUILD_MAX_USD`: hard cap on one build's maximum authorized cost.
* `OMNI_QA_BUDGET_TOTAL_USD`: hard cap on all QA builds ever reserved
  (sum of settled cost where known, else the reserved maximum), checked under
  a transaction-scoped advisory lock so concurrent builds cannot overshoot.
* Missing or invalid caps mean QA funding is unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import os
from typing import Mapping

_QA_LOCK_ID = 781234992


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
    account_emails: frozenset
    build_max_usd: Decimal | None
    total_usd: Decimal | None
    reason: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> 'QABudgetPolicy':
        env = os.environ if env is None else env
        emails = frozenset(e.strip().lower() for e in env.get('OMNI_QA_ACCOUNT_EMAILS', '').split(',') if e.strip())
        build_max = _decimal(env.get('OMNI_QA_BUILD_MAX_USD'))
        total = _decimal(env.get('OMNI_QA_BUDGET_TOTAL_USD'))
        if env.get('OMNI_ENV', '').strip().lower() == 'production' or env.get('VERCEL_ENV', '').strip().lower() == 'production':
            return cls(False, emails, build_max, total, 'internal QA funding is disabled in production')
        if not emails:
            return cls(False, emails, build_max, total, 'no QA accounts configured')
        if build_max is None or total is None:
            return cls(False, emails, build_max, total, 'QA caps are not configured')
        if build_max > total:
            return cls(False, emails, build_max, total, 'QA per-build cap exceeds total cap')
        return cls(True, emails, build_max, total, 'enabled')

    def applies_to(self, email: str | None) -> bool:
        return self.enabled and bool(email) and email.strip().lower() in self.account_emails

    def evidence(self) -> dict:
        return {'funding_source': 'internal_qa', 'qa_build_max_usd': str(self.build_max_usd),
                'qa_total_usd': str(self.total_usd)}


def authorize_qa_build(cur, policy: QABudgetPolicy, *, max_cost_usd: Decimal) -> dict:
    """Check both QA caps inside the build's reservation transaction.

    The total covers every reservation of every account whose email is in the
    QA list. Returns evidence on success; raises QABudgetDenied otherwise.
    """
    if not policy.enabled:
        raise QABudgetDenied(f'internal QA funding unavailable: {policy.reason}')
    max_cost_usd = Decimal(str(max_cost_usd))
    if max_cost_usd > policy.build_max_usd:
        raise QABudgetDenied(f'QA build maximum {max_cost_usd} exceeds per-build cap {policy.build_max_usd}')
    cur.execute('SELECT pg_advisory_xact_lock(%s)', (_QA_LOCK_ID,))
    cur.execute(
        """
        SELECT COALESCE(SUM(CASE
                   WHEN status = 'SETTLED' THEN COALESCE(settled_provider_cost_usd, estimated_provider_cost_usd)
                   WHEN status = 'RELEASED' THEN COALESCE(settled_provider_cost_usd, 0)
                   ELSE estimated_provider_cost_usd END), 0)
        FROM credit_reservations r
        JOIN creator_accounts a ON a.id = r.account_id
        WHERE lower(a.email) = ANY(%s)
        """,
        (sorted(policy.account_emails),),
    )
    used = Decimal(str(cur.fetchone()[0] or 0))
    if used + max_cost_usd > policy.total_usd:
        raise QABudgetDenied(f'QA total budget exhausted: used {used} + this build {max_cost_usd} > cap {policy.total_usd}')
    return {**policy.evidence(), 'qa_used_before_usd': str(used), 'qa_this_build_max_usd': str(max_cost_usd)}
