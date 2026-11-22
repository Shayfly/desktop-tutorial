"""The spec the customer approves, as a card (the owner's example, 2026-11-23: "זה מה שנבנה").

Gate 1 says the spec in one message: the summary of the brief's fields, the parts that are built without an
unavailable capability, the business details exactly as the customer wrote them (the fact canon, Michael 2026-11-10
condition 2), the price range and what to press. In production (the owner's screenshot, 2026-11-22 23:47) this was one
paragraph in which every detail appeared twice: the "starting content" field repeats the phone and the hours, and the
canon line lists them again.

`card()` gives the screen the same parts, structured: one row per field, the business details once (from the canon:
the customer's own words win), the notes, the price line and the next step. Nothing is added that the message does
not say, and nothing the message says is dropped, except a starting-content segment that repeats a business detail
word for word (it is shown once, under the details). The message text itself is unchanged: it stays the record, the
replay and the model's context.
"""
from __future__ import annotations

from .. import fact_canon as F


def _facts_from_line(line: str, lang: str) -> list[dict] | None:
    """The canon line "<prefix>: label: value; label: value." as rows, or None when the line is not that line."""
    template = F._TEXT['he' if lang == 'he' else 'en']['facts']
    prefix = template.split('{facts}')[0]
    if not (line.startswith(prefix) and line.endswith('.')):
        return None
    rows = []
    for part in line[len(prefix):-1].split('; '):
        label, sep, value = part.partition(': ')
        if not sep or not value.strip():
            return None                       # not the shape this function knows: the caller keeps the line as text
        rows.append({'label': label.strip(), 'value': value.strip()})
    return rows


def _without_repeats(value: str, details: list[str]) -> str:
    """The value without the '; '-separated segments that contain a business detail word for word."""
    keep = [s for s in str(value).split('; ') if not any(d and d in s for d in details)]
    return '; '.join(keep).strip()


def card(*, stage: str, rows: list[tuple[str, str, bool]], canon_lines: list[str], excluded: list[str],
         price: str, next_step: str, lang: str) -> dict:
    """rows: (label, value, is_a_safe_default) for each summary field, in the message's order."""
    facts, notes = [], []
    for i, line in enumerate(canon_lines):
        parsed = _facts_from_line(line, lang) if i == 0 else None
        if parsed is not None:
            facts = parsed
        else:
            notes.append(line)                 # a warning (CANON_INCOMPLETE), a needed fact, an image's role
    details = [f['value'] for f in facts]
    # an hours detail is "א׳–ה׳ 09:00–19:00, ו׳ 08:00–13:00": each statement is matched on its own
    details += [part.strip() for f in facts for part in f['value'].split(', ') if part.strip()]
    shown = []
    for label, value, default in rows:
        rest = _without_repeats(value, details)
        if rest:
            shown.append({'label': label, 'value': rest, 'default': bool(default)})
    return {'stage': stage, 'rows': shown, 'facts': facts, 'notes': [*excluded, *notes], 'price': price,
            'next': next_step}
