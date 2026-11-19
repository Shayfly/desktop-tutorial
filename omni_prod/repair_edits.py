"""Exact edit blocks for the agentic repairer: {path, old, new}, applied exactly once, all or nothing.

Root cause (wf_309a64e1-002, three founder builds of 2026-11-17): the only edit the agentic repairer offered was a
whole file. With the strong routes out of credit, the edit step fell to two routes whose output is limited to 8,192
tokens; a whole app.py needs about 9.4-9.8K (estimate), and all 14 of those answers were cut at 8,188 tokens. An
edit block is a few hundred tokens, whatever the size of the file it changes.

Fail closed: `old` must occur exactly once (overlapping occurrences counted) in the text as the earlier edits of the
same answer left it; no whitespace forgiveness, no fuzzy apply; any miss applies nothing and is reported back to the
model as the step's result, with a hint that is never applied.
"""
from __future__ import annotations

import difflib

MAX_EDITS = 40

BAD_SHAPE, TOO_MANY, UNSAFE_PATH, NO_SUCH_FILE, EMPTY_OLD, NOT_FOUND, AMBIGUOUS = (
    'BAD_SHAPE', 'TOO_MANY', 'UNSAFE_PATH', 'NO_SUCH_FILE', 'EMPTY_OLD', 'NOT_FOUND', 'AMBIGUOUS')


def _occurrences(text: str, needle: str) -> list[int]:
    out, start = [], text.find(needle)
    while start != -1:
        out.append(start)
        start = text.find(needle, start + 1)          # overlapping occurrences count
    return out


def resolve_edits(work: dict, edits) -> tuple[dict, list[dict]]:
    """The new text of every file the edits touch, or ({}, misses). `work` is never changed."""
    from .repository_patch import PatchValidationError, normalize_repo_path
    if edits is None:
        return {}, []
    if not isinstance(edits, list):
        return {}, [{'code': BAD_SHAPE, 'message': 'edits must be a list of {path, old, new}'}]
    if len(edits) > MAX_EDITS:
        return {}, [{'code': TOO_MANY, 'message': f'at most {MAX_EDITS} edits per answer'}]
    texts: dict[str, str] = {}
    misses: list[dict] = []
    for i, e in enumerate(edits):
        if not (isinstance(e, dict) and all(isinstance(e.get(k), str) for k in ('path', 'old', 'new'))):
            misses.append({'edit': i, 'code': BAD_SHAPE, 'message': 'each edit is {"path", "old", "new"}, all strings'})
            continue
        try:
            path = normalize_repo_path(e['path'])
        except PatchValidationError as exc:
            misses.append({'edit': i, 'code': UNSAFE_PATH, 'message': str(exc)[:200]})
            continue
        text = texts.get(path, work.get(path))
        if text is None:
            misses.append({'edit': i, 'path': path, 'code': NO_SUCH_FILE,
                           'message': 'no such file; a new file is sent whole in "files"'})
            continue
        old = e['old']
        if not old:
            misses.append({'edit': i, 'path': path, 'code': EMPTY_OLD, 'message': '"old" must not be empty'})
            continue
        at = _occurrences(text, old)
        if not at:
            first = old.splitlines()[0] if old.splitlines() else old
            near = difflib.get_close_matches(first, text.splitlines(), n=1, cutoff=0.6)
            misses.append({'edit': i, 'path': path, 'code': NOT_FOUND,
                           'message': '"old" is not in the file exactly (whitespace counts)',
                           **({'closest_line': near[0][:200]} if near else {})})
            continue
        if len(at) > 1:
            lines = [text.count('\n', 0, p) + 1 for p in at[:10]]
            misses.append({'edit': i, 'path': path, 'code': AMBIGUOUS,
                           'message': f'"old" occurs {len(at)} times; add surrounding lines so it occurs once',
                           'lines': lines})
            continue
        texts[path] = text[:at[0]] + e['new'] + text[at[0] + len(old):]
    return ({}, misses) if misses else (texts, [])
