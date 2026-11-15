"""Every A2 output is a document of docs/spec/a2_direction.schema.json; a document that does not pass stops the run."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[2] / 'docs' / 'spec' / 'a2_direction.schema.json'


class A2ContractError(RuntimeError):
    """An A2 skill produced a document outside the schema. Never caught to continue: the run stops."""


@lru_cache(maxsize=1)
def _validator():
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:      # the collector cannot run unchecked
        raise A2ContractError('jsonschema is required to run A2 (requirements-test.txt pins it)') from exc
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding='utf-8')), format_checker=FormatChecker())


def checked(doc: dict) -> dict:
    errors = sorted(_validator().iter_errors(doc), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        where = '/'.join(str(p) for p in first.absolute_path) or '(root)'
        raise A2ContractError(f'{doc.get("kind")}: {len(errors)} schema error(s); first at {where}: {first.message[:300]}')
    return doc


def now_z(at: datetime | None = None) -> str:
    at = at or datetime.now(timezone.utc)
    return at.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def candidate_id(url: str) -> str:
    return 'cand_' + hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]


def run_id(*parts: str) -> str:
    return 'a2r_' + hashlib.sha256('\x1f'.join(parts).encode('utf-8')).hexdigest()[:16]


def rejection(reason_code: str, stage: str, measured, threshold, at: str, **extra) -> dict:
    return {'reason_code': reason_code, 'stage': stage, 'measured': measured, 'threshold': threshold, 'at': at, **extra}
