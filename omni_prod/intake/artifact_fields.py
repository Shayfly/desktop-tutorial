"""QUESTIONS-001 / WP1: what each artifact kind needs in order to exist.

A field is MATERIAL when changing its value would change the artifact in a way the customer notices
(style, audience, language, sign-in). A missing material field is asked; a missing non-material field
takes its explicit DEFAULT and is shown as an assumption. Every field has an explicit default (a
material one uses it only when the customer says "you decide"), so "we assumed" is never a guess.

Values are neutral codes (the discovery option values), never words in one language, so a question
asked in Hebrew or Arabic leaves no English label in the spec.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    name: str            # the discovery field name (the interpreter proposes these)
    material: bool
    default: str         # explicit; used when not material, or when the customer delegates
    reason: str          # neutral reason code: what a wrong value changes (the phrasing is per language)


_COMMON = (
    Field('audience', True, 'public', 'who_reads'),
    Field('languages', True, 'he', 'text_direction'),
    Field('style', True, 'clean', 'look_and_feel'),
    Field('color', False, 'blue', 'brand_colour'),
    Field('font', False, 'heebo', 'typeface'),
    Field('logo', False, 'text', 'header_logo'),
    Field('references', False, 'none', 'inspiration'),
)
_APP = (
    Field('login', True, 'none', 'who_can_enter'),
    Field('personal_data', True, 'no', 'what_is_stored'),
    Field('dates', False, 'future_year', 'date_rules'),
    Field('duplicates', False, 'block', 'duplicate_rules'),
)

ARTIFACT_FIELDS: dict[str, tuple[Field, ...]] = {
    'website': _COMMON,
    'web_app': _COMMON + _APP,
}


def fields_for(kind: str) -> tuple[Field, ...]:
    """The declaration for a kind; an unsupported kind declares nothing (nothing is built, nothing is asked)."""
    return ARTIFACT_FIELDS.get(kind, ())
