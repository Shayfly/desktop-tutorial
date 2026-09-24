from __future__ import annotations
from dataclasses import dataclass
from .build_budget import BuildBudget, BudgetState, assert_within_budget
from .error_taxonomy import classify_error

@dataclass(frozen=True)
class RepairDecision:
    action: str  # retry | repair | fail
    reason: str

def decide_after_failure(*, error_message: str, budget: BuildBudget, state: BudgetState) -> RepairDecision:
    classified=classify_error(error_message)
    assert_within_budget(budget,state)
    if classified.retryable:
        return RepairDecision('retry', classified.category.value)
    if classified.repairable and state.repair_rounds < budget.max_repair_rounds:
        return RepairDecision('repair', classified.category.value)
    return RepairDecision('fail', classified.category.value)
