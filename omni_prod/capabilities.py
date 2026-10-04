from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class CapabilityStatus(str, Enum):
    LIVE = "LIVE"
    PARTIAL = "PARTIAL"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class CapabilityDefinition:
    key: str
    family: str
    description: str
    artifact_kinds: tuple[str, ...] = ()
    dependency_keys: tuple[str, ...] = ()
    provider_backed: bool = False
    default_required: bool = True
    commercial_use_required: bool = True

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("capability key must not be empty")
        if not self.family.strip():
            raise ValueError("capability family must not be empty")


@dataclass(frozen=True)
class CapabilityRequirement:
    id: str
    key: str
    purpose: str
    required: bool
    quantity: int = 1
    constraints: Mapping[str, Any] = field(default_factory=dict)
    dependency_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("capability requirement id must not be empty")
        if self.quantity < 1:
            raise ValueError("capability requirement quantity must be >= 1")


@dataclass(frozen=True)
class CapabilityPlan:
    requirements: tuple[CapabilityRequirement, ...]
    target_keys: tuple[str, ...]
    notes: tuple[str, ...] = ()
