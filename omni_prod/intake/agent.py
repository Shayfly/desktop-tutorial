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

Requirements preservation (Issue #12): a value the customer confirmed (source
'answer' or 'message') is never silently overwritten. A differing proposal is
applied only when it comes from the customer's own words in this turn
(deterministic origin) AND the field is not material; otherwise it becomes a
conflict that is asked back ("earlier X, now Y?") and the confirmed value
stays. With `require_confirmation` (RISKY turns) no model proposal is applied
to a material field at all -- it is only pre-selected and asked.
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
    conflicts: list[dict] = field(default_factory=list)     # {field, current, proposed, origin, reason}


def _copy(b: d.Brief) -> d.Brief:
    return d.Brief.from_dict(json.loads(json.dumps(b.to_dict())))


CONFIRMED_SOURCES = ('answer', 'message')


def apply(brief: d.Brief, interp: Interpretation, *, infer_defaults: bool = True,
          require_confirmation: bool = False) -> TurnResult:
    new = _copy(brief)
    res = TurnResult(new)
    for p in interp.proposals:
        q = d.BY_ID.get(p.field)
        if q is None:
            continue
        old = new.fields.get(p.field)
        origin = getattr(p, 'origin', 'deterministic')
        if origin == 'model' and require_confirmation and material(p.field, new.values()) and \
                (not old or old['value'] != p.value):
            new.hints[p.field] = p.value      # sensitive turn: pre-select and ask, never apply
            res.conflicts.append({'field': p.field, 'current': (old or {}).get('value'), 'proposed': p.value,
                                  'origin': origin, 'reason': 'sensitive turn: needs explicit confirmation'})
            continue
        if old and old.get('source') in CONFIRMED_SOURCES and old['value'] != p.value and \
                p.confidence in (HIGH, MEDIUM) and (origin == 'model' or material(p.field, new.values())):
            res.conflicts.append({'field': p.field, 'current': old['value'], 'proposed': p.value, 'origin': origin,
                                  'reason': 'differs from a confirmed requirement'})
            continue                          # the confirmed value stays until the customer chooses
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
                if q.delegable and q.recommended is not None and not material(q.field, new.values()) \
                        and d._recommended(q, new, new.hints) is not None:          # C9: no honest default -> asked
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
                if q.delegable and q.recommended is not None and not material(q.field, new.values()) \
                        and d._recommended(q, new, new.hints) is not None:          # C9: no honest default -> asked
                    new.fields[q.field] = {'value': d._recommended(q, new, new.hints), 'source': 'default',
                                           'question_id': q.id, 'confidence': 'inferred'}
                    res.assumed.append({'field': q.field, 'value': new.fields[q.field]['value'], 'source': 'default'})
                    changed = True
            d._drop_inapplicable(new)
    pend = d.pending(new)
    conflict_qs = [d.BY_ID[c['field']] for c in res.conflicts if c['field'] in d.BY_ID]
    urgent = [q for q in pend if q.id == 'access_scope']
    rest = [q for q in pend if q.id != 'access_scope']
    seen, asked = set(), []
    for q in conflict_qs + urgent + rest:     # conflicts are asked first, never dropped
        if q.id not in seen:
            seen.add(q.id)
            asked.append(q)
    res.asked = asked[:max(ASK_PER_TURN, len(conflict_qs))]
    res.contradictions = d.contradictions(new)
    res.brief = new
    return res


def answer_question(brief: d.Brief, question_id: str, value: str) -> d.Brief:
    """A quick-reply button in the chat: the same validated path as discovery answers."""
    return d.answer(brief, {question_id: value})
