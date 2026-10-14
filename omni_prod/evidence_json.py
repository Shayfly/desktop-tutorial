"""JSON for build/modification evidence written to Postgres.

Golden E2E #1 on Preview (2026-10-07): a build whose model calls failed could
not be marked FAILED because its evidence held Decimal values (budget binding,
route events) and json.dumps raised TypeError inside the worker's failure
handler. The build stayed "running" forever. Evidence is now encoded with the
types it actually contains, and a terminal status is never blocked by
evidence encoding: if encoding still fails, a small marker is stored instead
and the reason is kept.

Unknown object types are not stringified wholesale (an object's repr can
carry credentials, e.g. an endpoint with its API key); they fail encoding and
fall back to the marker.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import PurePath
from typing import Any


def _default(value: Any):
    if isinstance(value, Decimal):
        return str(value)                      # exact, like the economics quote's own fields
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=str)
    if isinstance(value, PurePath):
        return str(value)
    raise TypeError(f'Object of type {type(value).__name__} is not JSON serializable')


def dumps_evidence(value: Any) -> str:
    return json.dumps(value, default=_default)


def dumps_evidence_for_terminal_state(value: Any) -> str:
    """Never raises for unencodable content: the marker records why."""
    try:
        return dumps_evidence(value)
    except (TypeError, ValueError) as exc:
        return json.dumps({'evidence_encoding_error': str(exc)[:500],
                           'evidence_keys': sorted(map(str, value)) if isinstance(value, dict) else None})

