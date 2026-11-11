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
