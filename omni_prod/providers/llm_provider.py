from __future__ import annotations

from hashlib import sha256
from typing import Callable

from ..capabilities import CapabilityRequirement
from ..provider_contracts import (
    ProviderArtifactPayload,
    ProviderCapability,
    ProviderExecutionResult,
    ProviderQuote,
    ProviderTaskHandle,
    ProviderTaskState,
)


class LLMCapabilityProvider:
    def __init__(
        self, *, name: str, gateway, capability_keys: tuple[str, ...],
        quote_factory: Callable[[CapabilityRequirement], ProviderQuote],
        commercial_use: bool = True,
    ) -> None:
        self.name = name
        self.gateway = gateway
        self.capability_keys = tuple(capability_keys)
        self.quote_factory = quote_factory
        self.commercial_use = commercial_use
        self._results: dict[str, ProviderExecutionResult] = {}

    def capabilities(self) -> tuple[ProviderCapability, ...]:
        return tuple(ProviderCapability(key, ("text/plain", "application/json"), self.commercial_use) for key in self.capability_keys)

    def health(self) -> str:
        return "HEALTHY"

    def quote(self, requirement: CapabilityRequirement) -> ProviderQuote:
        if requirement.key not in self.capability_keys:
            raise LookupError(f"capability {requirement.key} is not supported by {self.name}")
        quote = self.quote_factory(requirement)
        if quote.provider != self.name or quote.capability_key != requirement.key:
            raise ValueError("quote identity does not match provider/capability")
        return quote

    def submit(self, requirement: CapabilityRequirement, *, idempotency_key: str) -> ProviderTaskHandle:
        if requirement.key not in self.capability_keys:
            raise LookupError(f"capability {requirement.key} is not supported by {self.name}")
        task_id = "sync_" + sha256(f"{self.name}\0{idempotency_key}".encode()).hexdigest()[:24]
        prompt = str(requirement.constraints.get("prompt") or requirement.purpose)
        system = str(requirement.constraints.get("system") or "Return the requested production artifact.")
        text = self.gateway.complete(system=system, user=prompt)
        payload = ProviderArtifactPayload(
            mime_type="text/plain", data=str(text).encode("utf-8"),
            filename=f"{requirement.id}.txt",
            provenance={"provider": self.name, "idempotency_key": idempotency_key},
        )
        self._results[task_id] = ProviderExecutionResult(
            artifacts=(), actual_cost_usd=None, usage={},
            evidence={"adapter": "LLMCapabilityProvider"}, payloads=(payload,),
        )
        return ProviderTaskHandle(self.name, task_id, requirement.id, idempotency_key)

    def poll(self, handle: ProviderTaskHandle) -> ProviderTaskState:
        return ProviderTaskState("SUCCEEDED", 1.0) if handle.provider_task_id in self._results else ProviderTaskState("RUNNING", 0.0)

    def collect(self, handle: ProviderTaskHandle) -> ProviderExecutionResult:
        try:
            return self._results[handle.provider_task_id]
        except KeyError as exc:
            raise RuntimeError("provider result unavailable; idempotent resubmit is required") from exc

    def cancel(self, handle: ProviderTaskHandle) -> None:
        self._results.pop(handle.provider_task_id, None)
