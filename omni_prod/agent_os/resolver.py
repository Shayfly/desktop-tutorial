"""CapabilityResolver: dependency closure before any build (autonomous
completion §11). For the product family a request needs, every required
skill is AVAILABLE (LIVE), PARTIAL (code without fresh live proof, or not
configured), MISSING (no code) or BLOCKED (named external blocker) -- from
the audited Skills OS, never from an agent's name.
"""
from __future__ import annotations

AVAILABLE, PARTIAL, MISSING, BLOCKED = 'AVAILABLE', 'PARTIAL', 'MISSING', 'BLOCKED'
_MAP = {'LIVE': AVAILABLE, 'REAL_SERVER_VERIFIED': AVAILABLE, 'INTEGRATION_TESTED': PARTIAL, 'UNIT_TESTED': PARTIAL,
        'IMPLEMENTED': PARTIAL, 'NOT_IMPLEMENTED': MISSING, 'BLOCKED': BLOCKED}

WEB_SAAS = ('requirement_extraction', 'acceptance_contract_generation', 'build_plan_generation', 'cost_estimation',
            'page_generation', 'form_generation', 'api_endpoint_generation', 'request_validation', 'schema_generation',
            'unit_test_execution', 'browser_launch', 'behavioral_acceptance_test', 'repair_execution', 'secret_detection',
            'preview_deploy', 'preview_access_protect', 'persistence_verification', 'version_create', 'credit_settlement')
HEBREW = ('hebrew_localization', 'rtl_layout', 'rtl_implementation', 'locale_date')
SIGN_IN = ('signup', 'login', 'session_management', 'auth_test')
FAMILY_EXTRA = {
    'game2d': ('game_loop_design', 'player_input', 'collision', 'score_system', 'gameplay_test', 'touch_controls'),
    'media': ('text_to_image', 'image_quality_check'),
    'automation': ('trigger_definition', 'schedule_definition', 'workflow_test'),
}


def required_skills(contract: dict) -> tuple[str, ...]:
    text = str(contract.get('prompt') or '').lower()
    skills = list(WEB_SAAS)
    if any(ch in text for ch in 'אבגדהוזחטיכלמנסעפצקרשת'):
        skills += HEBREW
    roles = [str(r) for r in (contract.get('user_roles') or ())]
    if roles and roles != ['user']:
        skills += SIGN_IN
    for family, words in (('game2d', ('game', 'משחק')), ('media', ('video', 'וידאו', 'image generation')),
                          ('automation', ('automation', 'אוטומציה', 'workflow'))):
        if any(w in text for w in words):
            skills += FAMILY_EXTRA[family]
    return tuple(dict.fromkeys(skills))


def resolve(contract: dict, statuses: dict | None = None) -> dict:
    if statuses is None:
        from .audit import skill_statuses
        statuses = skill_statuses()
    rows = {k: _MAP.get(statuses.get(k, 'NOT_IMPLEMENTED'), MISSING) for k in required_skills(contract)}
    worst = (BLOCKED if BLOCKED in rows.values() else MISSING if MISSING in rows.values()
             else PARTIAL if PARTIAL in rows.values() else AVAILABLE)
    return {'overall': worst, 'skills': rows,
            'missing': sorted(k for k, v in rows.items() if v in (MISSING, BLOCKED))}
