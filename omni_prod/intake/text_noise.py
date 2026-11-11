"""Technical text pasted into a product brief is not the customer's requirement (2026-10-28).

Used by the deterministic interpreter, the brief (intake.agent) and the discovery defaults."""
from __future__ import annotations

import re

# Technical text pasted into a product brief (an env var name, a URL, a file path, a stack-trace line, key=value) is
# not the customer's goal: 2026-10-28 "OMNI_REDIS_URL" on its own line became "Main action: OMNI_REDIS_URL".
_NOISE_TOKEN = re.compile(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b|\b[a-z][a-z0-9+.-]*://\S+|\S+\.(?:py|js|ts|json|ya?ml|sh)\b|'
                          r'\b\w+=\S*|\bTraceback\b|\bat 0x[0-9a-f]+\b|[{}\[\]<>`|\\]')
_WORD = re.compile(r'[^\W\d_]{2,}', re.U)


def technical_noise(text: str) -> bool:
    """True when, once the technical tokens are removed, fewer than two real words are left -- or when the text has
    a technical token and under five real words ("OMNI_REDIS_URL is not set.")."""
    words = len(_WORD.findall(_NOISE_TOKEN.sub(' ', text or '')))
    return words < 2 or (bool(_NOISE_TOKEN.search(text or '')) and words < 5)


def first_sentence(text: str) -> str:
    """The customer's first business sentence: the first sentence (or line) that is not technical noise."""
    for line in (text or '').splitlines():
        for part in re.split(r'(?<=[.!?])\s+', line.strip()):
            part = part.strip()
            if len(part) >= 8 and not technical_noise(part):
                return part
    return ''
