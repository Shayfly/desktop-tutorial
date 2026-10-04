from __future__ import annotations

from dataclasses import dataclass, asdict
import os
from .integrations import REGISTRY
from .capabilities import CapabilityDefinition, CapabilityStatus


@dataclass(frozen=True)
class IntegrationStatus:
    provider: str
    category: str
    configured: bool
    missing: tuple[str, ...]
    live_verified: bool
    note: str

    def to_dict(self) -> dict:
        d = asdict(self); d['missing'] = list(self.missing); return d


EXTRA_REQUIRED = {
    'postgres': ('OMNI_DATABASE_URL',),
    'redis': ('OMNI_REDIS_URL',),
    'open-weight-model': ('OMNI_LOCAL_MODEL_URL', 'OMNI_LOCAL_MODEL_ID'),
    'sandbox-runner': ('OMNI_SANDBOX_RUNNER_URL', 'OMNI_SANDBOX_SHARED_SECRET'),
    'media-provider': ('OMNI_MEDIA_BASE_URL',),
    'apple-signing': ('APPLE_TEAM_ID', 'APP_STORE_CONNECT_KEY_ID', 'APP_STORE_CONNECT_ISSUER_ID', 'APP_STORE_CONNECT_PRIVATE_KEY'),
    'android-signing': ('ANDROID_KEYSTORE', 'ANDROID_KEYSTORE_PASSWORD', 'ANDROID_KEY_ALIAS', 'ANDROID_KEY_PASSWORD'),
}


class IntegrationCenter:
    """Secret-safe connection readiness surface.

    It reports only presence/missing names. It never returns credential values.
    """
    def catalog(self) -> list[dict]:
        rows=[]
        for key, definition in sorted(REGISTRY.items()):
            rows.append(self._status(key, definition.category, definition.required_secrets).to_dict())
        for key, required in EXTRA_REQUIRED.items():
            rows.append(self._status(key, 'platform', required).to_dict())
        return rows

    @staticmethod
    def _status(provider: str, category: str, required: tuple[str, ...]) -> IntegrationStatus:
        missing = tuple(name for name in required if not os.getenv(name, '').strip())
        configured = not missing
        # Configuration is not equivalent to a live network verification.
        return IntegrationStatus(provider, category, configured, missing, False,
            'configured from environment/secret manager' if configured else 'not configured')


    def capability_status(self, definition: CapabilityDefinition) -> CapabilityStatus:
        """Conservative readiness projection; never infer LIVE from source presence alone."""
        key = definition.key
        if key in {
            'game.multiplayer','game.matchmaking','ecosystem.discover','ecosystem.creator_profile',
            'ecosystem.like','ecosystem.comment','ecosystem.follow','ecosystem.remix',
            'ecosystem.marketplace','ecosystem.revenue_share','target.desktop.source',
            'target.agent','target.automation',
        }:
            return CapabilityStatus.NOT_IMPLEMENTED
        if key.startswith(('media.', 'ai.')):
            # M4.95 supplies provider-neutral contracts/adapters but no claim of a
            # configured commercial provider is allowed from code presence alone.
            return CapabilityStatus.NOT_CONFIGURED
        if key.startswith(('target.android.', 'target.ios.', 'target.game.')):
            return CapabilityStatus.PARTIAL
        if key.startswith(('publish.android', 'publish.ios', 'publish.asset')):
            return CapabilityStatus.NOT_CONFIGURED
        if key.startswith('integration.'):
            return CapabilityStatus.PARTIAL
        return CapabilityStatus.PARTIAL

    def blockers(self) -> list[str]:
        required_for_public = {'postgres','redis','s3','open-weight-model','sandbox-runner','stripe','resend','media-provider'}
        by={x['provider']:x for x in self.catalog()}
        return [k for k in sorted(required_for_public) if not by[k]['configured']]
