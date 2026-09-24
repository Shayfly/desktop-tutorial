from __future__ import annotations
import re

_BEARER = re.compile(r'(?i)(authorization:\s*bearer\s+)([^\s]+)')
_NAMED = re.compile(r'(?i)((?:api[_-]?key|secret|password|token)\s*[=:]\s*)([^\s,;]+)')
_PGURL = re.compile(r'(?i)(postgres(?:ql)?://[^:/\s]+:)([^@\s]+)(@)')
_GENERIC_KEY = re.compile(r'\b(?:sk|pk|rk)-[A-Za-z0-9_-]{12,}\b')


def redact(text: str) -> str:
    out = text or ''
    out = _BEARER.sub(lambda m: m.group(1) + '[REDACTED]', out)
    out = _NAMED.sub(lambda m: m.group(1) + '[REDACTED]', out)
    out = _PGURL.sub(lambda m: m.group(1) + '[REDACTED]' + m.group(3), out)
    out = _GENERIC_KEY.sub('[REDACTED]', out)
    return out
