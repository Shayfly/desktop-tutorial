from __future__ import annotations

import os
from .brand_clearance import brand_readiness
from .integration_center import IntegrationCenter
from .ui_translations import UI_LANGUAGES


def launch_readiness_payload(*, logo_pack_present: bool = True) -> dict:
    integrations = IntegrationCenter().catalog()
    by = {row['provider']: row for row in integrations}
    required = ('postgres','redis','s3','open-weight-model','sandbox-runner','stripe','resend','media-provider')
    configured_blockers = [name for name in required if not by.get(name,{}).get('configured',False)]
    brand = brand_readiness(logo_pack_present=logo_pack_present)
    persistence_ok = os.getenv('OMNI_CREATOR_PERSISTENCE','memory').strip().lower() == 'postgres'
    if not persistence_ok:
        configured_blockers.append('creator-persistence-postgres-mode')
    config_ready = not configured_blockers and not brand.blockers
    live_required = [name for name in required if not by.get(name,{}).get('live_verified',False)]
    live_blockers = list(live_required)
    if not brand.public_brand_ready:
        live_blockers.extend(brand.blockers)
    return {
        'release':'V28 148AI Launch Candidate',
        'config_ready': config_ready,
        'public_launch_ready': not live_blockers,
        'configured_blockers': configured_blockers + list(brand.blockers),
        'live_blockers': live_blockers,
        'launch_locales': len(UI_LANGUAGES),
        'installable_pwa': True,
        'signed_ios_app': False,
        'signed_android_app': False,
        'truth': 'Configuration presence is not live verification. Public launch remains blocked until external integrations are harmlessly tested, domain/trademark gates are cleared, and the founder approves release.',
    }
