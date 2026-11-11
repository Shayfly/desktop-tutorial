"""Right-to-left pages by construction (CEO 2026-11-09).

Cafe build bld_762f4759 spent repair rounds on one review finding: "Hebrew product without dir="rtl" on the page".
A rule the model may forget is enforced here instead: after generation and after every repair, each HTML page of a
Hebrew or Arabic request gets dir="rtl" (and lang) on its <html> tag when the tag does not set them. A page that
sets dir itself (e.g. dir="ltr" for an English version) is left exactly as written. Only .html/.htm files are
touched; templates inside Python or JS strings keep the review check, which the repair still answers.
"""
from __future__ import annotations

import re

_HTML_TAG = re.compile(r'<html\b([^>]*)>', re.I)


def rtl_language(prompt: str) -> str | None:
    text = prompt or ''
    if re.search(r'[֐-׿]', text):
        return 'he'
    if re.search(r'[؀-ۿ]', text):
        return 'ar'
    return None


def ensure_rtl(repo: dict, lang: str) -> dict:
    out = dict(repo)
    for path, text in repo.items():
        if not isinstance(text, str) or not path.lower().endswith(('.html', '.htm')):
            continue
        m = _HTML_TAG.search(text)
        if not m:
            continue
        attrs = m.group(1)
        add = ''
        if not re.search(r'\bdir\s*=', attrs, re.I):
            add += ' dir="rtl"'
        if not re.search(r'\blang\s*=', attrs, re.I):
            add += f' lang="{lang}"'
        if add:
            out[path] = text[:m.start()] + f'<html{attrs.rstrip()}{add}>' + text[m.end():]
    return out


class _Chained:
    """Runs the transform already installed (e.g. the approved logo), then the RTL rule; keeps its attributes."""

    def __init__(self, inner, lang):
        self._inner, self._lang = inner, lang

    def __call__(self, repo):
        return ensure_rtl(self._inner(repo) if self._inner is not None else repo, self._lang)

    def __getattr__(self, name):
        if self._inner is None:
            raise AttributeError(name)
        return getattr(self._inner, name)


def install(engine, prompt: str) -> str | None:
    """Chain the RTL rule onto the engine's repository transform. Returns the language, or None (no change)."""
    lang = rtl_language(prompt)
    if lang is None:
        return None
    core = getattr(engine, 'core', engine)
    core.repository_transform = _Chained(getattr(core, 'repository_transform', None), lang)
    return lang
