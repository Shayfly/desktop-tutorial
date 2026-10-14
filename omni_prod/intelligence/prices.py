"""Effective-dated price schedule (Wave A §4.1).

Every row comes from the provider's official pricing page, read on
`verified_at`. Future price changes are included only when that page states
them (Gemini 3.8 Flash doubles on 2027-01-01). History is never edited: a new
price is a new row with a later `effective_from`, so the cost of any past call
can be reconstructed with `price_at(model, when)`.

Billing shapes differ per modality; a row carries only the units its provider
bills (tokens, images, seconds of audio/video, songs, minutes). A missing
price is never zero: `price_at` returns None and paid managed execution must
fail closed (`require_price`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal

GOOGLE = 'https://ai.google.dev/gemini-api/docs/pricing'
OPENAI = 'https://developers.openai.com/api/docs/pricing'
ANTHROPIC = 'https://platform.claude.com/docs/en/about-claude/pricing'
OPENROUTER = 'https://openrouter.ai/api/v1/models'
REPLICATE_FLUX = 'https://replicate.com/black-forest-labs/flux-schnell'
VERIFIED = '2026-10-11'


@dataclass(frozen=True)
class PriceRow:
    provider: str
    model: str                      # provider model id, exactly as the API takes it
    effective_from: date
    effective_until: date | None    # exclusive; None = open-ended
    source_url: str
    verified_at: str
    applicable_tier: str = 'paid standard'
    currency: str = 'USD'
    input_per_million: Decimal | None = None
    cached_input_per_million: Decimal | None = None
    output_per_million: Decimal | None = None
    # Reasoning/thinking tokens: how the provider bills them.
    reasoning_accounting: str = 'billed as output tokens'
    per_image: Decimal | None = None
    per_audio_second: Decimal | None = None
    per_video_second: Decimal | None = None
    per_song: Decimal | None = None
    per_transcription_minute: Decimal | None = None
    units_note: str = ''

    def active_on(self, day: date) -> bool:
        return self.effective_from <= day and (self.effective_until is None or day < self.effective_until)

    def to_dict(self) -> dict:
        out = {}
        for k, v in self.__dict__.items():
            if v is None:
                continue
            out[k] = str(v) if isinstance(v, (Decimal, date)) else v
        return out


def _d(x) -> Decimal | None:
    return None if x is None else Decimal(str(x))


def _row(provider, model, *, src, frm='2026-10-01', until=None, tier='paid standard', inp=None, cached=None, out=None,
         image=None, audio_s=None, video_s=None, song=None, minute=None, note='', reasoning='billed as output tokens',
         verified_at=None):
    return PriceRow(provider=provider, model=model, effective_from=date.fromisoformat(frm),
                    effective_until=date.fromisoformat(until) if until else None, source_url=src,
                    verified_at=verified_at or VERIFIED,
                    applicable_tier=tier, input_per_million=_d(inp), cached_input_per_million=_d(cached),
                    output_per_million=_d(out), per_image=_d(image), per_audio_second=_d(audio_s),
                    per_video_second=_d(video_s), per_song=_d(song), per_transcription_minute=_d(minute),
                    units_note=note, reasoning_accounting=reasoning)


# The schedule. Short-context (<=200k / <=100k) standard prices; long-context
# tiers are not used by 148AI prompts (bounded well below them).
SCHEDULE: tuple[PriceRow, ...] = (
    # -- Gemini text
    _row('gemini', 'gemini-3.1-flash-lite', src=GOOGLE, inp='0.25', cached='0.025', out='1.50',
         note='output price includes thinking tokens'),
    _row('gemini', 'gemini-3.5-flash-lite', src=GOOGLE, inp='0.30', cached='0.03', out='2.50'),
    _row('gemini', 'gemini-3.8-flash', src=GOOGLE, until='2027-01-01', inp='0.75', cached='0.075', out='3.75'),
    _row('gemini', 'gemini-3.8-flash', src=GOOGLE, frm='2027-01-01', inp='1.50', cached='0.15', out='7.50',
         note='announced on the pricing page: rises on 2027-01-01'),
    _row('gemini', 'gemini-2.5-flash-lite', src=GOOGLE, inp='0.10', out='0.40',
         note='access limited to projects that used 2.5 before (deprecations page)'),
    _row('gemini', 'gemini-3.1-pro-preview', src=GOOGLE, inp='2.00', out='12.00', note='<=200k prompt tokens; preview'),
    # -- Gemini media (not connected; for estimates only)
    _row('gemini', 'gemini-3.1-flash-lite-image', src=GOOGLE, inp='0.25', image='0.0336', note='per 1K image'),
    _row('gemini', 'gemini-nano-banana-2.1', src=GOOGLE, inp='1.50', image='0.0336', note='per 1K image; 2K $0.0504, 4K $0.113'),
    _row('gemini', 'gemini-omni-1.1-flash', src=GOOGLE, inp='1.50', video_s='0.10', note='about $0.10 per second of 720p video'),
    _row('gemini', 'gemini-3.8-flash-lite-tts', src=GOOGLE, until='2027-01-01', inp='0.50', audio_s='0.00015',
         note='about $0.0015 per 10 s of audio'),
    _row('gemini', 'gemini-3.8-flash-lite-tts', src=GOOGLE, frm='2027-01-01', inp='1.00', audio_s='0.0003',
         note='about $0.003 per 10 s of audio from 2027-01-01'),
    _row('gemini', 'gemini-3.8-flash-tts', src=GOOGLE, until='2027-01-01', inp='0.50', audio_s='0.000225',
         note='about $0.00225 per 10 s of audio'),
    _row('gemini', 'gemini-3.8-flash-tts', src=GOOGLE, frm='2027-01-01', inp='1.00', audio_s='0.00045'),
    _row('gemini', 'lyria-3.5', src=GOOGLE, song='0.08', note='full song'),
    _row('gemini', 'lyria-3-clip-preview', src=GOOGLE, song='0.04', note='30 s clip; preview'),
    _row('gemini', 'gemini-embedding-2', src=GOOGLE, inp='0.20', note='text'),
    # -- OpenAI
    _row('openai', 'gpt-6-luna', src=OPENAI, inp='0.10', cached='0.01', out='0.50'),
    _row('openai', 'gpt-6.1-sol', src=OPENAI, inp='2.00', cached='0.10', out='10.00'),
    _row('openai', 'gpt-6-astra', src=OPENAI, inp='10.00', cached='1.00', out='50.00'),
    _row('openai', 'gpt-image-2.5-flare', src=OPENAI, inp='5.00', out='30.00', note='text input $5, image output $30 per 1M tokens'),
    _row('openai', 'gpt-transcribe', src=OPENAI, minute='0.0045'),
    # -- Anthropic (prompts up to 100k tokens for Haiku)
    _row('anthropic', 'claude-sonnet-5-5', src=ANTHROPIC, inp='2.00', cached='0.10', out='10.00'),
    _row('anthropic', 'claude-haiku-5-5', src=ANTHROPIC, inp='0.10', cached='0.01', out='0.50', note='<=100k prompt tokens'),
    _row('anthropic', 'claude-opus-5-5', src=ANTHROPIC, inp='4.00', cached='0.20', out='20.00'),
    # OpenRouter's public model catalog reports per-token prices. This
    # conditional route remains disabled until its isolated worker is approved.
    _row('openrouter', 'openai/gpt-4o-mini', src=OPENROUTER, frm='2026-10-14', inp='0.15', out='0.60',
         note='OpenRouter catalog price for the selected upstream model; refresh before activation',
         verified_at='2026-10-14'),
)


class PriceMissing(LookupError):
    """No source-backed price: paid managed execution must not start."""


def _day(when) -> date:
    if when is None:
        return datetime.now(timezone.utc).date()
    if isinstance(when, datetime):
        return when.astimezone(timezone.utc).date() if when.tzinfo else when.date()
    return when


def price_at(model: str, when=None, schedule=SCHEDULE) -> PriceRow | None:
    day = _day(when)
    rows = [r for r in schedule if r.model == model and r.active_on(day)]
    if len(rows) > 1:
        raise ValueError(f'overlapping price rows for {model} on {day}')
    return rows[0] if rows else None


def require_price(model: str, when=None) -> PriceRow:
    row = price_at(model, when)
    if row is None:
        raise PriceMissing(f'no source-backed price for {model}; paid execution refused')
    return row


def history(model: str, schedule=SCHEDULE) -> list[PriceRow]:
    return sorted((r for r in schedule if r.model == model), key=lambda r: r.effective_from)


def validate(schedule=SCHEDULE) -> list[str]:
    """Overlaps, missing sources, negative prices, rows with no billable unit."""
    problems = []
    by_model: dict[str, list[PriceRow]] = {}
    for r in schedule:
        by_model.setdefault(r.model, []).append(r)
        if not r.source_url.startswith('https://'):
            problems.append(f'{r.model}: source_url must be an https URL')
        units = [r.input_per_million, r.output_per_million, r.per_image, r.per_audio_second, r.per_video_second,
                 r.per_song, r.per_transcription_minute]
        if not any(u is not None for u in units):
            problems.append(f'{r.model}: no billable unit')
        if any(u is not None and u < 0 for u in units):
            problems.append(f'{r.model}: negative price')
        if r.effective_until is not None and r.effective_until <= r.effective_from:
            problems.append(f'{r.model}: empty effective range')
    for model, rows in by_model.items():
        rows.sort(key=lambda r: r.effective_from)
        for a, b in zip(rows, rows[1:]):
            if a.effective_until is None or a.effective_until > b.effective_from:
                problems.append(f'{model}: overlapping rows from {a.effective_from} and {b.effective_from}')
    return problems
