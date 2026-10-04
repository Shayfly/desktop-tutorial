from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping, Protocol, runtime_checkable

from .capabilities import CapabilityRequirement


@dataclass(frozen=True)
class ProviderCapability:
    capability_key: str
    output_formats: tuple[str, ...]
    commercial_use: bool
    max_concurrency: int | None = None
    regions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.capability_key.strip():
            raise ValueError("capability_key must not be empty")
        if not self.output_formats:
            raise ValueError("output_formats must not be empty")
        if any(not item.strip() for item in self.output_formats):
            raise ValueError("output_formats must not contain empty values")
        if self.max_concurrency is not None and self.max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1 when configured")


@dataclass(frozen=True)
class ProviderQuote:
    provider: str
    capability_key: str
    estimated_cost_usd: Decimal
    maximum_cost_usd: Decimal
    pricing_version: str
    unit_name: str
    units: Decimal
    expires_at: str | None = None

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must not be empty")
        if not self.capability_key.strip():
            raise ValueError("capability_key must not be empty")
        if self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must be >= 0")
        if self.maximum_cost_usd < self.estimated_cost_usd:
            raise ValueError("maximum_cost_usd must be >= estimated_cost_usd")
        if not self.pricing_version.strip():
            raise ValueError("pricing_version must not be empty")
        if not self.unit_name.strip():
            raise ValueError("unit_name must not be empty")
        if self.units < 0:
            raise ValueError("units must be >= 0")


@dataclass(frozen=True)
class ProviderTaskHandle:
    provider: str
    provider_task_id: str
    capability_requirement_id: str
    idempotency_key: str

    def __post_init__(self) -> None:
        for field_name in (
            "provider",
            "provider_task_id",
            "capability_requirement_id",
            "idempotency_key",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")

    def to_dict(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "provider_task_id": self.provider_task_id,
            "capability_requirement_id": self.capability_requirement_id,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProviderTaskHandle":
        return cls(
            provider=str(payload["provider"]),
            provider_task_id=str(payload["provider_task_id"]),
            capability_requirement_id=str(payload["capability_requirement_id"]),
            idempotency_key=str(payload["idempotency_key"]),
        )


_ALLOWED_TASK_STATES = frozenset({"QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"})
_TERMINAL_TASK_STATES = frozenset({"SUCCEEDED", "FAILED", "CANCELLED"})


@dataclass(frozen=True)
class ProviderTaskState:
    status: str
    progress: float | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.status not in _ALLOWED_TASK_STATES:
            raise ValueError(f"invalid provider task status: {self.status}")
        if self.progress is not None and not 0.0 <= self.progress <= 1.0:
            raise ValueError("progress must be between 0.0 and 1.0")

    @property
    def terminal(self) -> bool:
        return self.status in _TERMINAL_TASK_STATES


@dataclass(frozen=True)
class CapabilityArtifact:
    artifact_key: str
    mime_type: str
    sha256: str
    size_bytes: int
    provider: str
    capability_key: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ("artifact_key", "mime_type", "provider", "capability_key"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be >= 0")
        if len(self.sha256) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in self.sha256):
            raise ValueError("sha256 must be a 64-character hexadecimal digest")




@dataclass(frozen=True)
class ProviderArtifactPayload:
    mime_type: str
    data: bytes
    filename: str = "artifact.bin"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.mime_type.strip() or "/" not in self.mime_type:
            raise ValueError("mime_type must be a valid media type")
        if not self.data:
            raise ValueError("provider artifact payload must not be empty")
        if not self.filename.strip() or "/" in self.filename or "\\" in self.filename:
            raise ValueError("filename must be a safe basename")


@dataclass(frozen=True)
class ProviderExecutionResult:
    artifacts: tuple[CapabilityArtifact, ...]
    actual_cost_usd: Decimal | None
    usage: Mapping[str, Any]
    evidence: Mapping[str, Any]
    payloads: tuple[ProviderArtifactPayload, ...] = ()

    def __post_init__(self) -> None:
        if self.actual_cost_usd is not None and self.actual_cost_usd < 0:
            raise ValueError("actual_cost_usd must be >= 0 when reported")


@runtime_checkable
class CapabilityProvider(Protocol):
    name: str

    def capabilities(self) -> tuple[ProviderCapability, ...]: ...

    def health(self) -> str: ...

    def quote(self, requirement: CapabilityRequirement) -> ProviderQuote: ...

    def submit(
        self,
        requirement: CapabilityRequirement,
        *,
        idempotency_key: str,
    ) -> ProviderTaskHandle: ...

    def poll(self, handle: ProviderTaskHandle) -> ProviderTaskState: ...

    def collect(self, handle: ProviderTaskHandle) -> ProviderExecutionResult: ...

    def cancel(self, handle: ProviderTaskHandle) -> None: ...
