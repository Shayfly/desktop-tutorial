from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .secrets_manager import SecretResolver


class CredentialMode(str, Enum):
    PLATFORM_MANAGED = "PLATFORM_MANAGED"
    CUSTOMER_CONNECTED = "CUSTOMER_CONNECTED"
    BYOK = "BYOK"


class CredentialStatus(str, Enum):
    CONFIGURED = "CONFIGURED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class CredentialBinding:
    binding_id: str
    provider: str
    mode: CredentialMode
    status: CredentialStatus
    tenant_id: str | None
    secret_reference: str

    def __post_init__(self) -> None:
        if not self.binding_id.strip() or not self.provider.strip():
            raise ValueError("binding_id and provider must not be empty")
        if self.mode in {CredentialMode.CUSTOMER_CONNECTED, CredentialMode.BYOK} and not self.tenant_id:
            raise ValueError("tenant_id is required for customer credential modes")
        scheme, sep, remainder = self.secret_reference.partition(":")
        if not sep or scheme not in {"env", "vault"} or not remainder.strip():
            raise ValueError("secret reference must use an approved env: or vault: reference")
        if any(token in self.secret_reference.lower() for token in ("bearer ", "sk-live-", "sk-proj-")):
            raise ValueError("secret reference must not contain inline credential material")

    def to_public_dict(self) -> dict[str, object]:
        return {
            "binding_id": self.binding_id,
            "provider": self.provider,
            "mode": self.mode.value,
            "status": self.status.value,
            "tenant_id": self.tenant_id,
            "configured": self.status == CredentialStatus.CONFIGURED,
        }


class CredentialBindingBroker:
    def __init__(self, *, resolvers: Mapping[str, SecretResolver]) -> None:
        self.resolvers = dict(resolvers)

    def resolve(self, binding: CredentialBinding, *, tenant_id: str) -> str:
        if binding.status != CredentialStatus.CONFIGURED:
            raise RuntimeError(f"credential binding is not configured: {binding.status.value}")
        if binding.mode in {CredentialMode.CUSTOMER_CONNECTED, CredentialMode.BYOK}:
            if binding.tenant_id != tenant_id:
                raise PermissionError("tenant is not authorized for this credential binding")
        scheme = binding.secret_reference.split(":", 1)[0]
        resolver = self.resolvers.get(scheme)
        if resolver is None:
            raise RuntimeError(f"no secret resolver configured for {scheme}")
        return resolver.resolve(binding.secret_reference)
