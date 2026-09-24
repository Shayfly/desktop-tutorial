from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from .build_budget import BuildBudget, BudgetState, assert_within_budget
from .repair_loop import decide_after_failure
from .retry import RetryPolicy, can_retry

@dataclass
class OrchestrationState:
    attempt: int = 1
    phase: str = 'queued'
    budget: BudgetState = None

    def __post_init__(self):
        if self.budget is None:
            self.budget = BudgetState()

class BuildOrchestrator:
    def __init__(self, *, build_budget: BuildBudget, retry_policy: RetryPolicy):
        self.build_budget=build_budget
        self.retry_policy=retry_policy

    def record_ai_cost(self, state: OrchestrationState, amount: Decimal):
        if amount < 0: raise ValueError('amount cannot be negative')
        state.budget.ai_cost += amount
        assert_within_budget(self.build_budget,state.budget)

    def record_build_seconds(self, state: OrchestrationState, seconds: int):
        if seconds < 0: raise ValueError('seconds cannot be negative')
        state.budget.build_seconds += seconds
        assert_within_budget(self.build_budget,state.budget)

    def failure_action(self, state: OrchestrationState, error_message: str) -> str:
        decision=decide_after_failure(error_message=error_message,budget=self.build_budget,state=state.budget)
        if decision.action=='retry' and can_retry(self.retry_policy,state.attempt,True):
            state.attempt += 1
            state.phase='retrying'
            return 'retry'
        if decision.action=='repair':
            state.budget.repair_rounds += 1
            assert_within_budget(self.build_budget,state.budget)
            state.phase='repairing'
            return 'repair'
        state.phase='failed'
        return 'fail'
