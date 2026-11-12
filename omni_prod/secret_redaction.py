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
WITHHELD = '[log record withheld: redaction failed]'
UNFORMATTABLE = '[log message could not be formatted; arguments withheld] '


def _redact_record(record: logging.LogRecord) -> None:
    """Every text a handler can print from the record, redacted in place: message, traceback, stack."""
    try:
        message = record.getMessage()
    except Exception:                           # broken format string: the raw args never reach a handler
        message = UNFORMATTABLE + str(record.msg)
    record.msg, record.args = redact(message), None
    if record.exc_info:                         # logger.exception / exc_info=True: render the traceback now, redacted
        record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
        record.exc_info = None                  # no formatter can re-render it raw
    elif record.exc_text:
        record.exc_text = redact(record.exc_text)
    if record.stack_info:
        record.stack_info = redact(record.stack_info)


def install_log_redaction() -> None:
    """Redact every log record at creation (idempotent), FAIL-CLOSED (#96).

    The formatted message replaces msg/args, so a %-argument is redacted too; the traceback (exc_info) and stack_info are
    rendered and redacted here, before any handler sees them. If formatting fails, the arguments are dropped. If
    redaction itself fails, the whole record is replaced by WITHHELD: nothing unredacted is ever passed on.
    Not covered: records built without the factory (logging.makeLogRecord, e.g. from a socket) and custom `extra=` fields.
    """
    current = logging.getLogRecordFactory()
    if getattr(current, _INSTALLED, False):
        return

    def factory(*args, **kwargs):
        record = current(*args, **kwargs)
        try:
            _redact_record(record)
        except Exception:                       # the redactor broke: withhold, never pass the raw record on
            record.msg, record.args = WITHHELD, None
            record.exc_info = record.exc_text = record.stack_info = None
        return record
    setattr(factory, _INSTALLED, True)
    logging.setLogRecordFactory(factory)
