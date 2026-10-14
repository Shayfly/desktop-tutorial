from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class BuildBudget:
    max_ai_cost: Decimal
    max_build_seconds: int
    max_repair_rounds: int

    def __post_init__(self):
        if self.max_ai_cost < 0: raise ValueError('max_ai_cost cannot be negative')
        if self.max_build_seconds <= 0: raise ValueError('max_build_seconds must be positive')
        if self.max_repair_rounds < 0: raise ValueError('max_repair_rounds cannot be negative')

@dataclass
class BudgetState:
    ai_cost: Decimal = Decimal('0')
    build_seconds: int = 0
    repair_rounds: int = 0

def assert_within_budget(budget: BuildBudget, state: BudgetState) -> None:
    if state.ai_cost > budget.max_ai_cost: raise RuntimeError('AI budget exceeded')
    if state.build_seconds > budget.max_build_seconds: raise RuntimeError('build time budget exceeded')
    if state.repair_rounds > budget.max_repair_rounds: raise RuntimeError('repair budget exceeded')
