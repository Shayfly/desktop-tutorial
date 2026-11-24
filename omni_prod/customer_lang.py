"""One language rule for the server's fixed customer texts (2026-11-22).

The platform speaks Hebrew, Arabic and English (assets/app.js LANGS; investor_app._lang). Every fixed sentence the
server says to a customer -- the conversation, the approval, a failure, the fact check, the discovery questions -- is
chosen by `pick`:

    he -> he      ar -> ar      anything else (en, None, 'fr', 'he_en', 'other') -> en

Never Hebrew for a customer who is not Hebrew: until 2026-11-22 several selectors read `lang != 'en'`, so an Arabic
(or French) customer got Hebrew. A table is read with `of(table, lang)`: a table that has no entry for the language
raises KeyError -- loud, never a quiet fall to another language (tests/test_server_texts_arabic.py checks that every
table with English has Arabic, with the same keys). `say` is the same rule for a sentence written inline.
"""
from __future__ import annotations

LANGS = ('he', 'ar', 'en')


def pick(lang) -> str:
    """The language of the customer's fixed texts: 'he' or 'ar' as asked, every other value English."""
    return lang if lang in ('he', 'ar') else 'en'


def of(table: dict, lang):
    """table[pick(lang)]. A table without that language raises KeyError: it is never served in another language."""
    return table[pick(lang)]


def say(lang, *, he, ar, en):
    """One inline sentence in the customer's language (the same rule as `pick`)."""
    return {'he': he, 'ar': ar, 'en': en}[pick(lang)]
