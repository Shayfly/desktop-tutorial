from __future__ import annotations
from dataclasses import dataclass
from .canary import CanaryObservation, CanaryPolicy, evaluate_canary

@dataclass(frozen=True)
class CanaryState:
    percent: int
    status: str  # running | rolled_back | complete | holding

def next_canary_state(
    policy: CanaryPolicy,
    state: CanaryState,
    observation: CanaryObservation,
) -> CanaryState:
    if state.status in {"rolled_back", "complete"}:
        return state
    decision = evaluate_canary(policy, observation, state.percent)
    if decision == "rollback":
        return CanaryState(percent=0, status="rolled_back")
    if decision == "hold":
        return CanaryState(percent=state.percent, status="holding")
    if decision == "complete":
        return CanaryState(percent=100, status="complete")
    if decision == "advance":
        new_percent = min(100, state.percent + policy.step_percent)
        return CanaryState(
            percent=new_percent,
            status="complete" if new_percent == 100 else "running",
        )
    raise RuntimeError(f"unknown canary decision: {decision}")
