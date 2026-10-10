"""Independent state axes for a provider/model (Wave A §3).

Each axis answers one question and has its own evidence rule. They are never
collapsed: a key being present says nothing about whether a call worked.

  credential_state    is a key configured where the model runs?
  connection_state    did a request reach the provider and get an answer?
  verification_state  did the model do real 148AI work (ledger / run evidence)?
  availability        can it take work NOW (credit, quota, lifecycle)?
  implementation      project-wide status vocabulary (agent_os.contracts)

Transition rules are data (TRANSITIONS) so tests and the matrix validator
read the same rules the code applies.
"""
from __future__ import annotations

# ---------------------------------------------------------------- credentials
NOT_CONFIGURED, CREDENTIAL_PRESENT, CREDENTIAL_UNKNOWN = 'NOT_CONFIGURED', 'CREDENTIAL_PRESENT', 'CREDENTIAL_UNKNOWN'
CREDENTIAL_STATES = (NOT_CONFIGURED, CREDENTIAL_PRESENT, CREDENTIAL_UNKNOWN)

# ----------------------------------------------------------------- connection
NOT_CONNECTED, CONNECTION_TESTED, CONNECTION_FAILED = 'NOT_CONNECTED', 'CONNECTION_TESTED', 'CONNECTION_FAILED'
CONNECTION_STATES = (NOT_CONNECTED, CONNECTION_TESTED, CONNECTION_FAILED)

# --------------------------------------------------------------- verification
UNVERIFIED, REAL_EXECUTION_VERIFIED, PRODUCTION_LIVE = 'UNVERIFIED', 'REAL_EXECUTION_VERIFIED', 'PRODUCTION_LIVE'
VERIFICATION_STATES = (UNVERIFIED, REAL_EXECUTION_VERIFIED, PRODUCTION_LIVE)

# --------------------------------------------------------------- availability
AVAILABLE, INSUFFICIENT_CREDIT, RATE_LIMITED = 'AVAILABLE', 'INSUFFICIENT_CREDIT', 'RATE_LIMITED'
TEMPORARILY_UNAVAILABLE, DEPRECATED, RETIRED, UNKNOWN = 'TEMPORARILY_UNAVAILABLE', 'DEPRECATED', 'RETIRED', 'UNKNOWN'
AVAILABILITY_STATES = (AVAILABLE, NOT_CONFIGURED, INSUFFICIENT_CREDIT, RATE_LIMITED, TEMPORARILY_UNAVAILABLE,
                       DEPRECATED, RETIRED, UNKNOWN)

# ------------------------------------------------------------- provider health
HEALTHY, DEGRADED, CREDIT_EXHAUSTED, AUTH_INVALID, UNAVAILABLE = (
    'HEALTHY', 'DEGRADED', 'CREDIT_EXHAUSTED', 'AUTH_INVALID', 'UNAVAILABLE')
HEALTH_STATES = (HEALTHY, DEGRADED, RATE_LIMITED, CREDIT_EXHAUSTED, AUTH_INVALID, UNAVAILABLE, RETIRED, UNKNOWN)
# A route in one of these states takes no work until its circuit allows a trial.
BLOCKING_HEALTH = (RATE_LIMITED, CREDIT_EXHAUSTED, AUTH_INVALID, UNAVAILABLE, RETIRED)

# ----------------------------------------------------------- evidence rules
# What an axis value needs before the matrix validator accepts it.
EVIDENCE_REQUIRED = {
    ('credential_state', CREDENTIAL_PRESENT): 'deploy annotation naming the route CONFIGURED (names only, never values)',
    ('connection_state', CONNECTION_TESTED): 'a recorded provider answer (any HTTP status) for this exact model id',
    ('connection_state', CONNECTION_FAILED): 'a recorded transport failure for this exact model id',
    ('verification_state', REAL_EXECUTION_VERIFIED): 'attempt-ledger rows with outcome ok for real 148AI work '
                                                     '(economics run) or a real-server run that used the model',
    ('verification_state', PRODUCTION_LIVE): 'a fresh run in production (none exists: never accepted)',
}

# Allowed transitions per axis (from -> to). Anything else is a bug.
TRANSITIONS = {
    'credential_state': {
        NOT_CONFIGURED: {CREDENTIAL_PRESENT, CREDENTIAL_UNKNOWN},
        CREDENTIAL_UNKNOWN: {CREDENTIAL_PRESENT, NOT_CONFIGURED},
        CREDENTIAL_PRESENT: {NOT_CONFIGURED, CREDENTIAL_UNKNOWN},
    },
    'connection_state': {
        NOT_CONNECTED: {CONNECTION_TESTED, CONNECTION_FAILED},
        CONNECTION_FAILED: {CONNECTION_TESTED, NOT_CONNECTED},
        CONNECTION_TESTED: {CONNECTION_FAILED, NOT_CONNECTED},
    },
    'verification_state': {
        UNVERIFIED: {REAL_EXECUTION_VERIFIED},
        REAL_EXECUTION_VERIFIED: {UNVERIFIED, PRODUCTION_LIVE},   # back to UNVERIFIED when the evidence goes stale
        PRODUCTION_LIVE: {UNVERIFIED, REAL_EXECUTION_VERIFIED},
    },
    'health': {
        HEALTHY: {DEGRADED, RATE_LIMITED, CREDIT_EXHAUSTED, AUTH_INVALID, UNAVAILABLE, RETIRED},
        DEGRADED: {HEALTHY, RATE_LIMITED, CREDIT_EXHAUSTED, AUTH_INVALID, UNAVAILABLE, RETIRED},
        RATE_LIMITED: {HEALTHY, DEGRADED, CREDIT_EXHAUSTED, AUTH_INVALID, UNAVAILABLE, RETIRED},
        CREDIT_EXHAUSTED: {HEALTHY, AUTH_INVALID, RETIRED},          # only a successful trial or a reset re-opens
        AUTH_INVALID: {HEALTHY, CREDIT_EXHAUSTED, RETIRED},
        UNAVAILABLE: {HEALTHY, DEGRADED, RETIRED},
        RETIRED: set(),
        UNKNOWN: set(HEALTH_STATES) - {UNKNOWN},
    },
}


def check_transition(axis: str, current: str, target: str) -> None:
    if current == target:
        return
    allowed = TRANSITIONS[axis].get(current)
    if allowed is None or target not in allowed:
        raise ValueError(f'illegal {axis} transition {current} -> {target}')


def availability_of(*, credential_state: str, health: str, lifecycle: str) -> str:
    """One answer to "can it take work now?", derived, never stored."""
    if lifecycle == 'RETIRED':
        return RETIRED
    if credential_state == NOT_CONFIGURED:
        return NOT_CONFIGURED
    if health == CREDIT_EXHAUSTED:
        return INSUFFICIENT_CREDIT
    if health == RATE_LIMITED:
        return RATE_LIMITED
    if health in (AUTH_INVALID, UNAVAILABLE):
        return TEMPORARILY_UNAVAILABLE
    if lifecycle == 'DEPRECATION_ANNOUNCED':
        return DEPRECATED
    if credential_state == CREDENTIAL_PRESENT and health in (HEALTHY, DEGRADED):
        return AVAILABLE
    return UNKNOWN
