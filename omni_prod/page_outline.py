"""The customer's own page structure reaches the generator (conversation agent, phase 3: an exact hand-off).

Production 2026-11-17, "148 דלתות": the owner wrote the page section by section --
    מבנה הדף:
    הירו — "דלת ממד פולימרית. 1,390 ₪ כולל הובלה והרכבה." ...
    למה דלת פולימרית — שישה יתרונות ...
    שאלות נפוצות — חמש, עם תשובות אמיתיות ...
The architect rewrites the request in its own words and the generator gets the spec alone (the same hand-off that
lost the design contract), so the order and the names of those sections were the model's to keep or drop.

`outline(text)` reads the sections the customer listed under a structure heading, in order, as written. `install`
gives the generator one mandatory requirement -- these sections, in this order, under these names -- with a
criterion a sandbox test can check over HTTP. Deterministic; no model; nothing is invented: a request with no
structure heading gets no requirement.
"""
from __future__ import annotations

import logging
import re

REQUIREMENT = 'CUSTOMER-PAGE-STRUCTURE'
# The owner, 2026-11-26 (WAREHOUSE 136, option a): the customer's own outline held at most 20 sections and each
# section's text was cut at 400 characters, silently. Raised; when a bound still applies it is logged
# (PAGE_OUTLINE_CUT), written into the structure requirement itself, and said to the customer when the spec is shown
# for approval (outline_notes / notes_message, conversation.supervisor._gate1). MAX_TITLE is not a cut: it defines a
# section line (a name of at most this many characters, then a dash or a colon); a longer line is prose and ends the
# structure as before, and every line stays in the request the build reads.
MAX_SECTIONS = 60
MAX_TITLE = 120
MAX_BODY = 4000
_HEADING = re.compile(r'^\s*(?:מבנה\s+(?:הדף|האתר|העמוד)|סדר\s+(?:הדף|העמוד)|page\s+structure|sections)\s*:\s*$', re.I)
# "הירו — ...", "שאלות נפוצות - ...", "צור קשר: ..." -- a short title, a dash or colon, then what the section holds
_SECTION = re.compile(r'^\s*(?:\d+[.)]\s*)?(?P<title>[^—:\-–\n]{2,%d}?)\s*(?:—|–|-|:)\s*(?P<body>.+)$' % MAX_TITLE)
_NUMBERED = re.compile(r'^\s*\d+[.)]\s*')
# Production 2026-11-19 (bld_7da07ab0, the owner's law-firm site): "1. פתיח: ..." names the section's role, not a
# heading the page must show -- the QA review failed the page for having no "פתיח" heading. An opening section keeps its
# place and its content; it needs no visible heading of that name.
_ROLE_ONLY = re.compile(r'^(?:פתיח|פתיחה|הירו|באנר|באנר ראשי|hero|intro|introduction|opening)$', re.I)
_LOG = logging.getLogger(__name__)


def _read(text: str) -> tuple[list[tuple[str, str]], list[dict]]:
    """(the sections, what the bounds left out: [{'kind': 'body_cut' | 'sections_cut', ...}])."""
    lines = (text or '').split('--- Approved project brief')[0].splitlines()
    out: list[tuple[str, str]] = []
    notes: list[dict] = []
    numbered_list = False
    for i, line in enumerate(lines):
        if not _HEADING.match(line):
            continue
        for following in lines[i + 1:]:
            if not following.strip():
                if out:
                    break                       # a blank line after the sections ends them
                continue
            m = _SECTION.match(following)
            if not m:
                break                           # the first line that is not "title — body" ends the structure
            numbered = bool(_NUMBERED.match(following))
            if out and numbered_list and not numbered:
                break                           # a numbered list ends at its first unnumbered line ("עיצוב: ...")
            numbered_list = numbered_list or (not out and numbered)
            if len(out) >= MAX_SECTIONS:        # a section past the bound: counted and said, never dropped silently
                if notes and notes[-1]['kind'] == 'sections_cut':
                    notes[-1]['left_out'] += 1
                else:
                    notes.append({'kind': 'sections_cut', 'bound': MAX_SECTIONS, 'left_out': 1})
                continue
            title, body = m['title'].strip(' "\''), m['body'].strip()
            if len(body) > MAX_BODY:
                notes.append({'kind': 'body_cut', 'title': title, 'chars': len(body), 'bound': MAX_BODY})
            out.append((title, body[:MAX_BODY]))
        break
    return out, notes


def outline(text: str) -> list[tuple[str, str]]:
    """[(title, what the customer wrote for it)] in order; [] when the request lists no structure. What a bound left
    out is logged here (PAGE_OUTLINE_CUT) and said by outline_notes / notes_message."""
    sections, notes = _read(text)
    for note in notes:
        _LOG.warning('PAGE_OUTLINE_CUT %s', note)
    return sections


def outline_notes(text: str) -> list[dict]:
    """What the bounds left out of the customer's outline (empty when nothing)."""
    return _read(text)[1]


def notes_message(notes: list[dict], lang: str = 'he') -> list[str]:
    """Each note in the customer's words (the spec they approve says it)."""
    out = []
    for n in notes:
        if n['kind'] == 'sections_cut':
            out.append(f'במבנה הדף שכתבתם יש יותר מ-{n["bound"]} חלקים: הדף ייבנה מ-{n["bound"]} הראשונים, ו-{n["left_out"]} '
                       'האחרונים לא ייכנסו למבנה (הם נשארים בבקשה).' if lang == 'he' else
                       f'Your page outline has more than {n["bound"]} parts: the page is built from the first '
                       f'{n["bound"]}, and the last {n["left_out"]} are not part of the structure (they stay in the request).')
        elif n['kind'] == 'body_cut':
            out.append(f'מה שכתבתם לחלק "{n["title"]}" ארוך מ-{n["bound"]:,} תווים: {n["bound"]:,} התווים הראשונים נכנסים '
                       'להנחיית המבנה, והשאר נשאר בבקשה.' if lang == 'he' else
                       f'What you wrote for the part "{n["title"]}" is longer than {n["bound"]:,} characters: the first '
                       f'{n["bound"]:,} go into the structure, and the rest stays in the request.')
        else:
            raise ValueError(f'unknown outline note kind {n["kind"]!r}')
    return out


def with_outline(spec, sections: list[tuple[str, str]]):
    from .product_spec import ProductSpec
    data = spec.to_dict()
    if not sections or any(r['id'] == REQUIREMENT for r in data['requirements']):
        return spec
    listed = ' | '.join(f'{n}. "{t}": {b}' for n, (t, b) in enumerate(sections, start=1))
    named = [t for t, _ in sections if not _ROLE_ONLY.match(t.strip())]
    roles = [t for t, _ in sections if _ROLE_ONLY.match(t.strip())]
    data['requirements'].append({
        'id': REQUIREMENT, 'kind': 'functional', 'mandatory': True,
        'text': ('The page has the sections the customer listed, in this order, each with the content the customer '
                 'wrote for it; each has a visible heading that uses the customer\'s name for it'
                 + (f" -- except {', '.join(repr(r) for r in roles)}, which names the section's role (the opening "
                    'of the page) and needs no heading of that name' if roles else '') + ': ' + listed)})
    data['acceptance'].append({
        'id': REQUIREMENT, 'requirement_id': REQUIREMENT,
        'text': ('GET / returns 200 and its HTML text contains these section names in this order: '
                 + ', '.join(f'"{t}"' for t in named))})
    return ProductSpec.from_dict(data)


class OutlineArchitect:
    def __init__(self, inner, sections):
        self._inner, self.sections = inner, list(sections)

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def create_spec(self, prompt, *args, **kwargs):
        return with_outline(self._inner.create_spec(prompt, *args, **kwargs), self.sections)


def install(engine, prompt: str) -> list[tuple[str, str]]:
    sections = outline(prompt)
    if not sections:
        return sections
    core = getattr(engine, 'core', engine)
    carried = False
    for holder in (core, engine):
        architect = getattr(holder, 'architect', None)
        if architect is not None and not isinstance(architect, OutlineArchitect):
            holder.architect = OutlineArchitect(architect, sections)
        carried = carried or isinstance(getattr(holder, 'architect', None), OutlineArchitect)
    if not carried:
        _LOG.warning('PAGE_OUTLINE_NOT_CARRIED %d section(s): the engine has no architect', len(sections))
    return sections
