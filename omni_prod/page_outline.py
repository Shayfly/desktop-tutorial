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
MAX_SECTIONS = 20
MAX_TITLE = 60
MAX_BODY = 400
_HEADING = re.compile(r'^\s*(?:מבנה\s+(?:הדף|האתר|העמוד)|סדר\s+(?:הדף|העמוד)|page\s+structure|sections)\s*:\s*$', re.I)
# "הירו — ...", "שאלות נפוצות - ...", "צור קשר: ..." -- a short title, a dash or colon, then what the section holds
_SECTION = re.compile(r'^\s*(?:\d+[.)]\s*)?(?P<title>[^—:\-–\n]{2,%d}?)\s*(?:—|–|-|:)\s*(?P<body>.+)$' % MAX_TITLE)
_LOG = logging.getLogger(__name__)


def outline(text: str) -> list[tuple[str, str]]:
    """[(title, what the customer wrote for it)] in order; [] when the request lists no structure."""
    lines = (text or '').split('--- Approved project brief')[0].splitlines()
    out: list[tuple[str, str]] = []
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
            out.append((m['title'].strip(' "\''), m['body'].strip()[:MAX_BODY]))
            if len(out) >= MAX_SECTIONS:
                _LOG.warning('PAGE_OUTLINE_CUT at %d sections', MAX_SECTIONS)
                break
        break
    return out


def with_outline(spec, sections: list[tuple[str, str]]):
    from .product_spec import ProductSpec
    data = spec.to_dict()
    if not sections or any(r['id'] == REQUIREMENT for r in data['requirements']):
        return spec
    listed = ' | '.join(f'{n}. "{t}": {b}' for n, (t, b) in enumerate(sections, start=1))
    data['requirements'].append({
        'id': REQUIREMENT, 'kind': 'functional', 'mandatory': True,
        'text': ('The page has the sections the customer listed, in this order, each with a visible heading that uses '
                 'the customer\'s name for it, and with the content the customer wrote for it: ' + listed)})
    data['acceptance'].append({
        'id': REQUIREMENT, 'requirement_id': REQUIREMENT,
        'text': ('GET / returns 200 and its HTML text contains these section names in this order: '
                 + ', '.join(f'"{t}"' for t, _ in sections))})
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
