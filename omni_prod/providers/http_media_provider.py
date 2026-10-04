from __future__ import annotations

from hashlib import sha256
from typing import Callable

from ..capabilities import CapabilityRequirement
from ..media_pipeline import AssetKind, AssetRequest
from ..provider_contracts import (
    ProviderArtifactPayload,
    ProviderCapability,
    ProviderExecutionResult,
    ProviderQuote,
    ProviderTaskHandle,
    ProviderTaskState,
)


_KIND_BY_CAPABILITY = {
    "media.image.generate": AssetKind.IMAGE,
    "media.audio.generate": AssetKind.AUDIO,
    "media.music.generate": AssetKind.MUSIC,
    "media.voice.generate": AssetKind.VOICE,
    "media.video.generate": AssetKind.VIDEO,
    "media.3d.mesh.generate": AssetKind.MODEL3D,
    "media.3d.texture.generate": AssetKind.TEXTURE,
}


class HTTPMediaCapabilityProvider:
    def __init__(
        self,
        *,
        gateway,
        capability_keys: tuple[str, ...],
        output_formats: tuple[str, ...],
        quote_factory: Callable[[CapabilityRequirement], ProviderQuote],
        durable_idempotency: bool,
        paid_external: bool = False,
        commercial_use: bool = True,
    ) -> None:
        if paid_external and not durable_idempotency:
            raise ValueError("paid external providers require durable idempotency support")
        if paid_external:
            raise ValueError(
                "paid external HTTPMediaCapabilityProvider requires durable result retrieval; "
                "this synchronous compatibility adapter keeps results only in process memory"
            )
        self.gateway = gateway
        self.name = gateway.endpoint.name
        self.capability_keys = tuple(capability_keys)
        self.output_formats = tuple(output_formats)
        self.quote_factory = quote_factory
        self.durable_idempotency = durable_idempotency
        # This compatibility adapter stores completed results in process memory.
        # It is therefore never crash-resumable by provider_task_id.
        self.durable_result_retrieval = False
        self.paid_external = paid_external
        self.commercial_use = commercial_use
        self._results: dict[str, ProviderExecutionResult] = {}

    def capabilities(self) -> tuple[ProviderCapability, ...]:
        return tuple(
            ProviderCapability(key, self.output_formats, self.commercial_use)
            for key in self.capability_keys
        )

    def health(self) -> str:
        return "HEALTHY"

    def quote(self, requirement: CapabilityRequirement) -> ProviderQuote:
        if requirement.key not in self.capability_keys:
            raise LookupError(f"capability {requirement.key} is not supported by {self.name}")
        quote = self.quote_factory(requirement)
        if quote.provider != self.name or quote.capability_key != requirement.key:
            raise ValueError("quote identity does not match provider/capability")
        return quote

    def _asset_request(self, requirement: CapabilityRequirement) -> AssetRequest:
        kind = _KIND_BY_CAPABILITY.get(requirement.key)
        if kind is None:
            raise LookupError(f"capability {requirement.key} has no media asset mapping")
        prompt = str(requirement.constraints.get("prompt") or requirement.purpose)
        return AssetRequest(requirement.id, kind, requirement.purpose, prompt, requirement.required)

    def submit(self, requirement: CapabilityRequirement, *, idempotency_key: str) -> ProviderTaskHandle:
        if requirement.key not in self.capability_keys:
            raise LookupError(f"capability {requirement.key} is not supported by {self.name}")
        task_id = "sync_" + sha256(f"{self.name}\0{idempotency_key}".encode()).hexdigest()[:24]
        asset = self.gateway.generate(self._asset_request(requirement), idempotency_key=idempotency_key)
        payload = ProviderArtifactPayload(
            mime_type=asset.mime_type,
            data=asset.data,
            filename=f"{requirement.id}.bin",
            metadata=dict(asset.metadata),
            provenance={"provider": asset.provider, "idempotency_key": idempotency_key},
        )
        self._results[task_id] = ProviderExecutionResult(
            artifacts=(), actual_cost_usd=None,
            usage={"provider_metadata": dict(asset.metadata)},
            evidence={"adapter": "HTTPMediaCapabilityProvider", "durable_idempotency": self.durable_idempotency},
            payloads=(payload,),
        )
        return ProviderTaskHandle(self.name, task_id, requirement.id, idempotency_key)

    def poll(self, handle: ProviderTaskHandle) -> ProviderTaskState:
        return ProviderTaskState("SUCCEEDED", 1.0) if handle.provider_task_id in self._results else ProviderTaskState("RUNNING", 0.0)

    def collect(self, handle: ProviderTaskHandle) -> ProviderExecutionResult:
        try:
            return self._results[handle.provider_task_id]
        except KeyError as exc:
            raise RuntimeError("provider result is not available in this adapter process; idempotent resubmit is required") from exc

    def cancel(self, handle: ProviderTaskHandle) -> None:
        self._results.pop(handle.provider_task_id, None)
