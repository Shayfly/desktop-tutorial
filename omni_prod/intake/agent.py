"""Intake Agent: applies an interpretation to the ProjectBrief under the
confidence policy (Wave A §5.4 "Ask less, infer more, verify everything").

  high    the customer stated it          -> brief field, source 'message' (explicit)
  medium  strongly implied                -> if the field is MATERIAL (security,
                                             privacy, who can see data) it is only
                                             pre-selected and asked; otherwise it is a
                                             documented default (source 'default'),
                                             shown as an assumption in the summary
  low     a guess                         -> ignored
  delegate ("you decide")                 -> every delegable open field gets the
                                             recommended value (source 'delegated')

Non-material open questions are filled with their recommended defaults
(source 'default') so the customer is asked only what matters. Material
questions and contradictions are always asked; `access_scope` can never be
defaulted. The agent never approves, never plans and never starts a build:
it returns a new Brief (a new immutable revision when stored).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .. import discovery as d
from .interpreter import HIGH, MEDIUM, Interpretation

ASK_PER_TURN = 2


def material(field_: str, values: dict) -> bool:
    if field_ in ('login', 'personal_data', 'access_scope'):
        return True
    if field_ == 'audience':
        return values.get('personal_data') == 'yes' and values.get('login', 'none') == 'none'
    return False


@dataclass
class TurnResult:
    brief: d.Brief
    applied: list[dict] = field(default_factory=list)       # {field, value, source}
    assumed: list[dict] = field(default_factory=list)       # defaults chosen by 148AI this turn
    corrected: list[dict] = field(default_factory=list)     # {field, old, new}
    asked: list[d.Question] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)


def _copy(b: d.Brief) -> d.Brief:
    return d.Brief.from_dict(json.loads(json.dumps(b.to_dict())))


def apply(brief: d.Brief, interp: Interpretation, *, infer_defaults: bool = True) -> TurnResult:
    new = _copy(brief)
    res = TurnResult(new)
    for p in interp.proposals:
        q = d.BY_ID.get(p.field)
        if q is None:
            continue
        old = new.fields.get(p.field)
        if p.confidence == HIGH:
            if old and old['value'] != p.value:
                res.corrected.append({'field': p.field, 'old': old['value'], 'new': p.value})
            if not old or old['value'] != p.value:
                new.fields[p.field] = {'value': p.value, 'source': 'message', 'question_id': q.id, 'confidence': 'stated'}
                res.applied.append({'field': p.field, 'value': p.value, 'source': 'message'})
        elif p.confidence == MEDIUM:
            if old:   # a medium guess never overrides something already decided
                continue
            if material(p.field, new.values()) or not q.delegable:
                new.hints[p.field] = p.value
            elif infer_defaults:
                new.fields[p.field] = {'value': p.value, 'source': 'default', 'question_id': q.id, 'confidence': 'inferred'}
                res.assumed.append({'field': p.field, 'value': p.value, 'source': 'default'})
    d._drop_inapplicable(new)
    if interp.delegate_rest:
        changed = True
        while changed:
            changed = False
            for q in d.pending(new):
                # "You decide" never covers a material (security/privacy) choice:
                # those need the customer's explicit answer.
                if q.delegable and q.recommended is not None and not material(q.field, new.values()):
                    new.fields[q.field] = {'value': d._recommended(q, new, new.hints), 'source': 'delegated',
                                           'question_id': q.id, 'confidence': 'recommended'}
                    res.assumed.append({'field': q.field, 'value': new.fields[q.field]['value'], 'source': 'delegated'})
                    changed = True
            d._drop_inapplicable(new)
    if infer_defaults:
        changed = True
        while changed:
            changed = False
            for q in d.pending(new):
                if q.delegable and q.recommended is not None and not material(q.field, new.values()):
                    new.fields[q.field] = {'value': d._recommended(q, new, new.hints), 'source': 'default',
                                           'question_id': q.id, 'confidence': 'inferred'}
                    res.assumed.append({'field': q.field, 'value': new.fields[q.field]['value'], 'source': 'default'})
                    changed = True
            d._drop_inapplicable(new)
    pend = d.pending(new)
    urgent = [q for q in pend if q.id == 'access_scope']
    rest = [q for q in pend if q.id != 'access_scope']
    res.asked = (urgent + rest)[:ASK_PER_TURN]
    res.contradictions = d.contradictions(new)
    res.brief = new
    return res


def answer_question(brief: d.Brief, question_id: str, value: str) -> d.Brief:
    """A quick-reply button in the chat: the same validated path as discovery answers."""
    return d.answer(brief, {question_id: value})
