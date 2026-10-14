"""Credit/budget admission for a product modification (no web framework).

Golden E2E #1 (2026-10-07): the INTERNAL_QA account could build but its first
modification was refused with "cost class not included in plan" -- the
modification route reserved on the customer plan only, while build admission
funds an entitled account from the internal QA budget. This applies the same
decision to modifications: an entitled account is authorized against the QA
caps under the QA lock and reserved with funding_source='internal_qa'; any
other account is reserved on its customer plan exactly as before.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .qa_budget import QABudgetPolicy, authorize_qa_build


@dataclass(frozen=True)
class ModificationAdmission:
    allowed: bool
    reason: str | None
    funding: dict


def admit_modification(cur, *, subscriptions, modification_id: str, account_id: str, project_id: str,
                       cost_class: str, credits: int, internal_qa: bool,
                       qa_policy: QABudgetPolicy | None) -> ModificationAdmission:
    """Runs inside the caller's transaction (same cursor as the request and
    outbox rows). Raises qa_budget.QABudgetDenied when an entitled account's
    QA caps refuse it."""
    if internal_qa:
        # A modification may spend at most one QA build's cap; the model
        # gateway's own external budget bounds the actual spend below it.
        maximum = Decimal(str(qa_policy.build_max_usd))
        funding = authorize_qa_build(cur, qa_policy, account_id=account_id, max_cost_usd=maximum)
        decision = subscriptions.reserve(
            cur, build_id=modification_id, user_id=account_id, project_id=project_id,
            cost_class=cost_class, credits=credits, category='product_modification',
            estimated_provider_cost_usd=maximum, internal_qa=True,
        )
    else:
        funding = {'funding_source': 'customer_plan'}
        decision = subscriptions.reserve(
            cur, build_id=modification_id, user_id=account_id, project_id=project_id,
            cost_class=cost_class, credits=credits, category='product_modification',
        )
    return ModificationAdmission(bool(decision.allowed), None if decision.allowed else decision.reason, funding)
