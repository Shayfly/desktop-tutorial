"""THE redaction layer (C27, founder 2026-10-20).

Every text that may carry a credential goes through `redact` before it is logged, stored as evidence or printed:
  * the logging layer: `install_log_redaction()` wraps the log record factory, so EVERY logger (including ones created
    later and third-party ones) emits the redacted message; it is installed by the worker entry point and the API;
  * evidence: evidence_export.redact applies this first, then its own stricter rules for exported files;
  * structured events, the acceptance pipeline and training data call it directly.
C30 found four separate redactors and this one missing Google keys (AIza...), so a Gemini key in a log line was printed.
Not covered: a bare print() of a secret outside these paths.
"""
from __future__ import annotations
import logging
import re

_BEARER = re.compile(r'(?i)(authorization:\s*bearer\s+)([^\s]+)')
_NAMED = re.compile(r'(?i)((?:api[_-]?key|secret|password|token)\s*[=:]\s*)([^\s,;]+)')
_PGURL = re.compile(r'(?i)(postgres(?:ql)?://[^:/\s]+:)([^@\s]+)(@)')
_URL_CREDENTIALS = re.compile(r'(?i)\b([a-z][a-z0-9+.-]*://)([^/\s:@]*):([^@\s/]+)@')   # rediss://:pw@, amqp://u:pw@
_GENERIC_KEY = re.compile(r'\b(?:sk|pk|rk)-[A-Za-z0-9_-]{12,}\b')                        # OpenAI sk-, sk-proj-, sk-ant-
_GOOGLE_KEY = re.compile(r'AIza[0-9A-Za-z_-]{20,}')                                       # Gemini / Google API keys
_PROVIDER_TOKEN = re.compile(r'\b(?:ghp|gho|ghs|ghu|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b'
                             r'|\br8_[A-Za-z0-9]{20,}\b')                                 # GitHub, Replicate


def redact(text: str) -> str:
    out = text or ''
    out = _BEARER.sub(lambda m: m.group(1) + '[REDACTED]', out)
    out = _NAMED.sub(lambda m: m.group(1) + '[REDACTED]', out)
    out = _PGURL.sub(lambda m: m.group(1) + '[REDACTED]' + m.group(3), out)
    out = _URL_CREDENTIALS.sub(lambda m: m.group(1) + (m.group(2) + ':' if m.group(2) else ':') + '[REDACTED]@', out)
    out = _GENERIC_KEY.sub('[REDACTED]', out)
    out = _GOOGLE_KEY.sub('[REDACTED]', out)
    out = _PROVIDER_TOKEN.sub('[REDACTED]', out)
    return out


_INSTALLED = '_omni_redacting_factory'


def install_log_redaction() -> None:
    """Redact every log record at creation (idempotent). The formatted message replaces msg/args, so a secret passed
    as a %-argument is redacted too; exception text is redacted when it is formatted into the message by the caller."""
    current = logging.getLogRecordFactory()
    if getattr(current, _INSTALLED, False):
        return

    def factory(*args, **kwargs):
        record = current(*args, **kwargs)
        try:
            message = record.getMessage()
        except Exception:                      # a broken format string: leave the record as it is
            return record
        record.msg, record.args = redact(message), None
        return record
    setattr(factory, _INSTALLED, True)
    logging.setLogRecordFactory(factory)
