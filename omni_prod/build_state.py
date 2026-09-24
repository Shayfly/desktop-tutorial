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
