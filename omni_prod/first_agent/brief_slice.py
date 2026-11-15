"""The only writes the first agent makes to the brief: `structure` and `references` (Michael 2026-11-15, the
warehouse slice released from ג1/ב1). Every write is reversible and touches nothing else.

Reversible by construction: brief revisions are immutable rows (BriefRepository, compare-and-set). A write is a new
revision; `revert` is one more revision that puts the previous values back -- nothing is ever deleted or overwritten.

Touches nothing else: `slice_only` compares the brief before and after with `structure` and `fields.references`
removed; any other difference raises SliceViolation and nothing is saved.

The structure is part of the brief's fingerprint (Brief.to_dict carries it when set), so an approval binds the
structure the customer saw -- a changed structure is a changed fingerprint and the old approval no longer matches.
"""
from __future__ import annotations

import copy
from dataclasses import replace

from ..discovery import Brief

REFERENCES_FIELD = 'references'


class SliceViolation(RuntimeError):
    pass


def _without_slice(d: dict) -> dict:
    d = copy.deepcopy(d)
    d.pop('structure', None)
    (d.get('fields') or {}).pop(REFERENCES_FIELD, None)
    return d


def slice_only(before: Brief, after: Brief) -> None:
    a, b = _without_slice(before.to_dict()), _without_slice(after.to_dict())
    if a != b:
        changed = sorted({k for k in set(a) | set(b) if a.get(k) != b.get(k)})
        raise SliceViolation(f'the first agent may write only structure and fields.references; changed: {changed}')


_KEEP = object()


def with_slice(brief: Brief, *, structure: list[dict] | None = None, references: str | None = None,
               references_field=_KEEP) -> Brief:
    """A new brief with the slice changed; None leaves that part as it is. An empty string removes the reference.
    `references_field` (revert only) puts back the field exactly as it was -- value AND its source/confidence -- or
    removes it when it is None, so a revert gives back the same brief and the same fingerprint."""
    fields = dict(brief.fields)
    if references_field is not _KEEP:
        if references_field is None:
            fields.pop(REFERENCES_FIELD, None)
        else:
            fields[REFERENCES_FIELD] = copy.deepcopy(references_field)
    elif references is not None:
        if references:
            fields[REFERENCES_FIELD] = {'value': references, 'source': 'first_agent', 'confidence': 'stated',
                                        'question_id': REFERENCES_FIELD}
        else:
            fields.pop(REFERENCES_FIELD, None)
    out = replace(brief, fields=fields, structure=list(structure) if structure is not None else list(brief.structure))
    slice_only(brief, out)
    return out


def current_slice(brief: Brief) -> dict:
    ref = brief.fields.get(REFERENCES_FIELD)
    return {'structure': copy.deepcopy(brief.structure),
            'references_field': copy.deepcopy(ref) if isinstance(ref, dict) else None}


def write(repo, *, project_id: str, account_id: str, structure: list[dict] | None = None,
          references: str | None = None, request_key: str | None = None, _references_field=_KEEP) -> dict:
    """Save the slice as a new revision. Returns the new row and `undo`: the previous values, for revert()."""
    row = repo.latest(project_id)
    if row is None:
        raise LookupError(f'no brief for project {project_id}')
    new = with_slice(row.brief, structure=structure, references=references, references_field=_references_field)
    saved = repo.save(project_id=project_id, account_id=account_id, brief=new, expected_revision=row.revision,
                      request_key=request_key)
    return {'row': saved, 'undo': {'revision': row.revision, **current_slice(row.brief)}}


def revert(repo, *, project_id: str, account_id: str, undo: dict) -> dict:
    """Put the slice back as it was before a write -- as one more revision (nothing is deleted)."""
    return write(repo, project_id=project_id, account_id=account_id, structure=undo['structure'],
                 _references_field=undo['references_field'])
