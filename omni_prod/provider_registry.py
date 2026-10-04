from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .provider_contracts import CapabilityProvider


class ProviderRegistry:
    """Canonical in-process registry of configured capability providers.

    Registration is deterministic and rejects duplicate provider names so routing
    evidence never depends on import/registration order.
    """

    def __init__(self, providers: Iterable[CapabilityProvider] = ()) -> None:
        self._providers: dict[str, CapabilityProvider] = {}
        self._by_capability: dict[str, set[str]] = defaultdict(set)
        for provider in providers:
            self.register(provider)

    def register(self, provider: CapabilityProvider) -> None:
        name = str(provider.name).strip()
        if not name:
            raise ValueError("provider name must not be empty")
        if name in self._providers:
            raise ValueError(f"duplicate provider: {name}")
        capabilities = tuple(provider.capabilities())
        if not capabilities:
            raise ValueError(f"provider {name} must expose at least one capability")
        self._providers[name] = provider
        for capability in capabilities:
            self._by_capability[capability.capability_key].add(name)

    def get(self, name: str) -> CapabilityProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise LookupError(f"unknown provider: {name}") from exc

    def providers_for(self, capability_key: str) -> tuple[CapabilityProvider, ...]:
        names = sorted(self._by_capability.get(capability_key, ()))
        return tuple(self._providers[name] for name in names)

    def all(self) -> tuple[CapabilityProvider, ...]:
        return tuple(self._providers[name] for name in sorted(self._providers))
