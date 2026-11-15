"""The proposal card (docs/spec/first-agent.md section 7): structure and price in ONE card, reviewed by the editor
before the customer sees it, with edits that write only the brief's structure and are undoable.

The API (investor_app: GET/POST .../proposal) is a thin wrapper around these functions, so the logic is tested here
without a web server. Writes go through brief_slice (structure / references only, reversible).
"""
from __future__ import annotations

from ..fact_canon import build_canon, canon_view
from . import brief_slice
from .editor import review
from .structure import apply_edit, build_card

INCLUDED_HE = ('דף אחד, מותאם לנייד', 'עברית, מימין לשמאל', 'תצוגה מקדימה וקישור')
EXCLUDED_HE = ('דומיין משלכם', 'תשלום או הזמנה באתר', 'שמירת פרטי לקוחות')


def cards_for(brief) -> list[dict]:
    """The stored structure (what the customer already edited) or, the first time, the card built from the brief."""
    if brief.structure:
        return [dict(c) for c in brief.structure]
    return [build_card(brief.prompt, canon=build_canon(brief.prompt))]


def view(row) -> dict:
    """What the proposal card shows for this brief revision. When the editor blocks, `cards` is withheld: the reason
    goes to the first agent (the conversation asks), never to the customer as a broken card."""
    brief = row.brief
    canon = build_canon(brief.prompt)
    verdict = review(cards_for(brief), canon=canon)
    facts = canon_view(brief.prompt)
    out = {'revision': row.revision, 'brief_fingerprint': row.fingerprint, 'ok': verdict['ok'],
           'price': verdict['price'], 'facts': facts.get('facts', []), 'included': list(INCLUDED_HE),
           'excluded': list(EXCLUDED_HE)}
    if verdict['ok']:
        out.update(cards=verdict['cards'], removed=verdict['removed'])
    else:
        out.update(cards=None, agent_blocks=verdict['blocks'])          # for the first agent, not for display
    return out


class StaleProposal(RuntimeError):
    pass


def edit(repo, *, project_id: str, account_id: str, revision: int, op: str, key: str, value: str | None = None) -> dict:
    """One row edit on the first card, saved as the brief's structure (a new revision). Returns the new view and
    `undo` (brief_slice) so the UI can revert exactly."""
    row = repo.latest(project_id)
    if row is None:
        raise LookupError(f'no brief for project {project_id}')
    if row.revision != revision:
        raise StaleProposal(f'the brief is at revision {row.revision}, not {revision}')
    cards = cards_for(row.brief)
    cards[0] = apply_edit(cards[0], op, key, value)
    written = brief_slice.write(repo, project_id=project_id, account_id=account_id, structure=cards)
    return {'proposal': view(written['row']), 'undo': written['undo']}


def undo(repo, *, project_id: str, account_id: str, undo: dict) -> dict:
    written = brief_slice.revert(repo, project_id=project_id, account_id=account_id, undo=undo)
    return {'proposal': view(written['row'])}
