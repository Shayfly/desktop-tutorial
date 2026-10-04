from __future__ import annotations

from .provider_contracts import CapabilityProvider


class ProviderRegistry:
    """Trusted server-side registry of configured capability providers."""

    def __init__(self) -> None:
        self._providers: dict[str, CapabilityProvider] = {}

    def register(self, provider: CapabilityProvider) -> None:
        name = str(getattr(provider, "name", "")).strip()
        if not name:
            raise ValueError("provider name must not be empty")
        if name in self._providers:
            raise ValueError(f"duplicate provider: {name}")
        # Validate capability metadata on registration so startup fails closed.
        tuple(provider.capabilities())
        self._providers[name] = provider

    def get(self, name: str) -> CapabilityProvider:
        try:
            return self._providers[name]
        except KeyError as exc:
            raise KeyError(f"unknown provider: {name}") from exc

    def all(self) -> tuple[CapabilityProvider, ...]:
        return tuple(self._providers[name] for name in sorted(self._providers))

    def providers_for(self, capability_key: str) -> tuple[CapabilityProvider, ...]:
        matches = []
        for provider in self._providers.values():
            if any(item.capability_key == capability_key for item in provider.capabilities()):
                matches.append(provider)
        return tuple(sorted(matches, key=lambda item: item.name))
