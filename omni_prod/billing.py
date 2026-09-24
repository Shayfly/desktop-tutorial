from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class ChargeReason(str, Enum):
    NEW_BUILD='new_build'
    CHANGE_REQUEST='change_request'
    EXTRA_COMPUTE='extra_compute'
    SYSTEM_BUG='system_bug'
    MISSING_REQUIREMENT='missing_requirement'

FREE_REASONS = {ChargeReason.SYSTEM_BUG, ChargeReason.MISSING_REQUIREMENT}

@dataclass(frozen=True)
class Plan:
    name: str
    monthly_price_usd: Decimal
    included_credits: int
    max_projects: int
    team_seats: int

@dataclass(frozen=True)
class CreditDecision:
    billable: bool
    credits: int
    reason: ChargeReason

class CreditLedger:
    def __init__(self, opening: int = 0):
        if opening < 0: raise ValueError('opening cannot be negative')
        self.balance = opening
        self.entries: list[tuple[str,int]] = [('opening', opening)] if opening else []

    def apply(self, decision: CreditDecision) -> int:
        if decision.credits < 0: raise ValueError('credits cannot be negative')
        if not decision.billable or decision.reason in FREE_REASONS:
            self.entries.append((decision.reason.value, 0)); return self.balance
        if decision.credits > self.balance:
            raise RuntimeError('insufficient credits')
        self.balance -= decision.credits
        self.entries.append((decision.reason.value, -decision.credits))
        return self.balance

    def grant(self, amount: int, reason: str='grant') -> int:
        if amount < 1: raise ValueError('grant must be positive')
        self.balance += amount; self.entries.append((reason, amount)); return self.balance

def classify_charge(*, category: str, estimated_compute_units: int = 1) -> CreditDecision:
    if estimated_compute_units < 0: raise ValueError('estimated_compute_units cannot be negative')
    if category == 'system_bug': return CreditDecision(False, 0, ChargeReason.SYSTEM_BUG)
    if category == 'missing_requirement': return CreditDecision(False, 0, ChargeReason.MISSING_REQUIREMENT)
    if category == 'change_request': return CreditDecision(True, max(1, estimated_compute_units), ChargeReason.CHANGE_REQUEST)
    return CreditDecision(True, max(1, estimated_compute_units), ChargeReason.EXTRA_COMPUTE)
