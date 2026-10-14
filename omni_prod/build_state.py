from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from .models import BuildStatus

_ALLOWED = {
    BuildStatus.QUEUED: {BuildStatus.RUNNING, BuildStatus.CANCELLED},
    BuildStatus.RUNNING: {BuildStatus.READY, BuildStatus.FAILED, BuildStatus.CANCELLED},
    BuildStatus.READY: set(),
    BuildStatus.FAILED: set(),
    BuildStatus.CANCELLED: set(),
}

def can_transition(current: BuildStatus, target: BuildStatus) -> bool:
    return target in _ALLOWED[current]

def assert_transition(current: BuildStatus, target: BuildStatus) -> None:
    if not can_transition(current, target):
        raise ValueError(f"illegal build transition: {current.value} -> {target.value}")

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def terminal(status: BuildStatus) -> bool:
    return not _ALLOWED[status]


# ---- running sub-states (phases) ---------------------------------------
# Production Assurance v2 §5: an explicit order within RUNNING. Phases only
# move forward while the build is RUNNING; a late write from a stale or
# duplicated worker after a terminal state, or a step backwards, is ignored.
# RECOVERING is written by crash recovery when the build goes back to QUEUED.
PHASES = ('QUEUED', 'RECOVERING', 'PLANNING', 'INFRASTRUCTURE', 'ASSETS', 'GENERATING', 'VERIFYING')
_PHASE_INDEX = {p: i for i, p in enumerate(PHASES)}


def phase_may_follow(current: str | None, target: str) -> bool:
    """True when `target` may be written after `current` (same phase again is
    allowed: a message update)."""
    if target not in _PHASE_INDEX:
        return False
    if current is None or current not in _PHASE_INDEX:
        return True  # RUNNING/legacy values: any known phase may start
    return _PHASE_INDEX[target] >= _PHASE_INDEX[current]
