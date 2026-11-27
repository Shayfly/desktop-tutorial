"""Render a sketch (S6.3, slice 1): the section library's own `page()`, with the draft ribbon, from the build's design
contract. Deterministic: the same direction and content give the same bytes."""
from __future__ import annotations

import hashlib

from .. import section_library as L


def render(direction, content: dict) -> tuple[str, str]:
    """(html, sha256 of the html). A heading over its script's limit raises (typography.check_headings), it is never
    cut; a section the library cannot place raises."""
    html, _skipped = L.page(content, direction.contract, order=list(direction.sections),
                            draft={'ribbon': L.DRAFT_RIBBON})
    return html, hashlib.sha256(html.encode('utf-8')).hexdigest()
