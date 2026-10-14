"""Model lifecycle: announced retirements and successors (Wave A §4.2).

Source: the providers' official deprecation pages, read 2026-10-11. A
shutdown date is the provider's earliest announced retirement date.

    ACTIVE                 no retirement announced
    DEPRECATION_ANNOUNCED  retirement date announced and in the future; warn
                           when it is within WARN_DAYS
    RETIRED                date passed: never routed (fail closed)
    RESTRICTED             available only to some accounts; must be probed

A successor is a suggestion, never an automatic swap: `migration_plan`
compares capability and price and the change goes through the normal
catalog/review path.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

GOOGLE_DEP = 'https://ai.google.dev/gemini-api/docs/deprecations'
OPENAI_DEP = 'https://developers.openai.com/api/docs/deprecations'
WARN_DAYS = 120

ACTIVE, DEPRECATION_ANNOUNCED, RETIRED, RESTRICTED = 'ACTIVE', 'DEPRECATION_ANNOUNCED', 'RETIRED', 'RESTRICTED'


@dataclass(frozen=True)
class Lifecycle:
    model: str
    shutdown: date | None
    successor: str | None
    source_url: str
    note: str = ''
    restricted: bool = False


def _l(model, shutdown, successor, src, note='', restricted=False):
    return Lifecycle(model, date.fromisoformat(shutdown) if shutdown else None, successor, src, note, restricted)


LIFECYCLE: tuple[Lifecycle, ...] = (
    _l('gemini-3.1-flash-lite', '2027-05-07', 'gemini-3.5-flash-lite', GOOGLE_DEP),
    _l('gemini-3.5-flash-lite', None, None, GOOGLE_DEP),
    _l('gemini-3.8-flash', None, None, GOOGLE_DEP),
    _l('gemini-2.5-flash-lite', None, None, GOOGLE_DEP,
       'not deprecated, but access is limited to projects that used 2.5 models before', restricted=True),
    _l('gemini-3.1-pro-preview', None, None, GOOGLE_DEP, 'preview model'),
    _l('gemini-3.1-flash-tts-preview', '2026-11-17', 'gemini-3.8-flash-lite-tts', GOOGLE_DEP),
    _l('veo-3.1-generate-preview', '2026-10-22', 'gemini-omni-1.1-flash', GOOGLE_DEP),
    _l('veo-3.1-fast-generate-preview', '2026-10-22', 'gemini-omni-1.1-flash', GOOGLE_DEP),
    _l('imagen-4.0-generate-001', '2026-08-17', 'gemini-nano-banana-2.1', GOOGLE_DEP),
    _l('gemini-2.5-flash-image', '2027-03-15', 'gemini-3.1-flash-lite-image', GOOGLE_DEP),
    _l('gpt-5-nano-2025-08-07', '2026-12-11', 'gpt-5.6-luna', OPENAI_DEP),
    _l('gpt-5-mini-2025-08-07', '2026-12-11', 'gpt-5.6-terra', OPENAI_DEP),
    _l('gpt-5-2025-08-07', '2026-12-11', 'gpt-5.6-sol', OPENAI_DEP),
    _l('gpt-image-1', '2026-10-23', 'gpt-image-2.5-flare', OPENAI_DEP),
    _l('sora-2', '2026-09-24', None, OPENAI_DEP, 'Videos API retired'),
    _l('tts-1', '2027-01-06', 'gpt-realtime-2.1-mini', OPENAI_DEP),
    _l('whisper-1', '2027-02-26', 'gpt-transcribe', OPENAI_DEP),
    _l('gpt-6-luna', None, None, OPENAI_DEP),
)
BY_MODEL = {x.model: x for x in LIFECYCLE}


def _day(when) -> date:
    if when is None:
        return datetime.now(timezone.utc).date()
    return when.date() if isinstance(when, datetime) else when


def state(model: str, when=None) -> str:
    entry = BY_MODEL.get(model)
    if entry is None:
        return ACTIVE
    day = _day(when)
    if entry.shutdown is not None:
        return RETIRED if day >= entry.shutdown else DEPRECATION_ANNOUNCED
    return RESTRICTED if entry.restricted else ACTIVE


def warning(model: str, when=None) -> str | None:
    entry = BY_MODEL.get(model)
    if entry is None or entry.shutdown is None:
        return None
    left = (entry.shutdown - _day(when)).days
    if left <= 0:
        return f'{model} retired on {entry.shutdown}; successor {entry.successor or "none announced"}'
    if left <= WARN_DAYS:
        return f'{model} retires on {entry.shutdown} ({left} days); successor {entry.successor or "none announced"}'
    return None


def migration_plan(model: str, *, capabilities: dict | None = None, when=None) -> dict:
    """Compatibility + price comparison for a successor. Never applies it."""
    from .prices import price_at
    entry = BY_MODEL.get(model)
    if entry is None or not entry.successor:
        return {'model': model, 'successor': None, 'action': 'none'}
    old, new = price_at(model, when), price_at(entry.successor, when)
    caps = capabilities or {}
    return {
        'model': model, 'successor': entry.successor, 'shutdown': str(entry.shutdown) if entry.shutdown else None,
        'successor_priced': new is not None,
        'price_change': None if not (old and new and old.output_per_million and new.output_per_million) else
        f'output {old.output_per_million} -> {new.output_per_million} per 1M',
        'compatibility': caps.get(entry.successor, 'UNASSESSED'),
        'action': 'review' if new is not None else 'blocked: successor price not source-backed',
    }
