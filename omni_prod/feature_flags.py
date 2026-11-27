"""Feature flags -- the ONLY place a flag is read (Michael 2026-11-10, work order 001, mapped to this codebase).

site_auth_v2: hardened sign-in in the products 148AI builds (password hashing, rate limits, __Host- cookie, token
rotation, uniform errors, reset stub, form accessibility). Off by default; while off, every instruction, prompt and
acceptance check is byte-identical to baseline 2c1d6cb (tests/test_site_auth_v2.py, the identity test). Turned on only
after the frozen run (13.11 17:53) and its own gates.
"""
from __future__ import annotations

import os


def _on(name: str) -> bool:
    return os.getenv(name, '0').strip().lower() in ('1', 'true', 'on', 'yes')


SITE_AUTH_V2: bool = _on('OMNI_SITE_AUTH_V2')


# ---- output rollout (the owner, 2026-11-27; plan S9.2) ---------------------------------------------------------------
# One question per output type: may THIS account have it? OMNI_OUTPUT_<TYPE> = off | owner | all. A type whose profile
# exists but whose rollout excludes the account gets today's "not yet" sentence from the A0 router
# (omni_prod/output_profile). Sites and web apps are always `all` unless the variable says otherwise: their behaviour is
# byte for byte what it was. Any other value raises -- a mistyped rollout is never read as `off` or as `all`
# (CLAUDE.md section 3).
OUTPUT_ROLLOUTS = ('off', 'owner', 'all')
_OUTPUT_DEFAULT = {'website': 'all', 'web_app': 'all', 'game': 'off'}


def output_rollout(kind: str, account_id=None) -> bool:
    if kind not in _OUTPUT_DEFAULT:
        raise ValueError(f'no output rollout is defined for {kind!r}; defined: {sorted(_OUTPUT_DEFAULT)}')
    mode = (os.getenv(f'OMNI_OUTPUT_{kind.upper()}') or _OUTPUT_DEFAULT[kind]).strip().lower()
    if mode not in OUTPUT_ROLLOUTS:
        raise ValueError(f'OMNI_OUTPUT_{kind.upper()} must be one of {list(OUTPUT_ROLLOUTS)}, not {mode!r}')
    if mode == 'all':
        return True
    if mode == 'owner':
        from .pricing import m5_founder_account       # the owner's own account (OMNI_FOUNDER_ACCOUNT_IDS); no one else
        return m5_founder_account(account_id)
    return False
