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
import logging
import re
from dataclasses import dataclass, field

from .. import discovery as d
from .interpreter import HIGH, MEDIUM, Interpretation, technical_noise

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
    dropped: list[str] = field(default_factory=list)        # proposals refused here, each with its reason


def _copy(b: d.Brief) -> d.Brief:
    return d.Brief.from_dict(json.loads(json.dumps(b.to_dict())))


CONFIRMED_SOURCES = ('answer', 'message')


_ENV_TOKEN = re.compile(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b')
_LOG = logging.getLogger(__name__)


def _off_topic(fld: str, value: str) -> bool:
    """A pasted technical token never becomes the goal or the initial content (2026-10-28: OMNI_REDIS_URL)."""
    if fld == 'goal':
        return technical_noise(value)
    if fld == 'content':           # links and prices ARE content; only a bare env-var paste is not
        return bool(_ENV_TOKEN.search(value or '')) and len(re.findall(r'[^\W\d_]{2,}', _ENV_TOKEN.sub(' ', value))) < 2
    return False


def _extends(old, new) -> bool:
    """The new text keeps the old one whole (spacing and the separators ; | , aside) and adds to it."""
    norm = lambda v: re.sub(r'[\s;|,]+', ' ', str(v or '')).strip()
    a, b = norm(old), norm(new)
    return bool(a) and len(b) > len(a) and a in b


# The owner, 2026-11-23 ("סוכן ... שידע להבין את הלקוח ... ולהפוך את המלל לתוצאה מעולה"). On ShayFly every new fact the
# customer gave -- the three packages with their prices, "מי אנחנו", the name and the phone -- was proposed by the model
# for `content` or `screens`, called "differs from a confirmed requirement" and kept out; the customer read "לא שיניתי
# -- מה נכון?" and the summary had none of it (tests/test_first_agent_keeps_every_fact.py replays those rows).
# These two fields are LISTS of what the site holds: what the customer says next is added to them, never asked back.
CUMULATIVE = ('content', 'screens')


def _norm(v) -> str:
    return re.sub(r'[\s;|,.]+', ' ', str(v or '')).strip()


_CLAUSE_SPLIT = re.compile(r'[;|\n]|(?<=[.!?])\s+')
_NUMBER = re.compile(r'\d[\d\-,.:/]*')


def _clauses(text) -> list[str]:
    return [c.strip(' .;|') for c in _CLAUSE_SPLIT.split(str(text or '')) if c and c.strip(' .;|')]


def _key(clause: str) -> str:
    """A clause without its numbers: "ייעוץ ראשון 250 ₪" and "ייעוץ ראשון 300 ₪" are the same fact, changed."""
    return _NUMBER.sub('#', _norm(clause))


def _label(clause: str) -> str:
    """What a clause is about: the words before its colon ("חבילה 1"), or before its first number ("ייעוץ ראשון").
    Numbers inside a label count, so "חבילה 1" and "חבילה 2" are two items, never one corrected."""
    head = clause.split(':', 1)[0] if ':' in clause else _NUMBER.split(clause, 1)[0]
    return _norm(head)


def _merged(old, new) -> tuple[str, list[tuple[str, str]]]:
    """Clause by clause (separators ; | a line break or a sentence end; commas stay inside a clause, as in an address):
      * a clause already there is not repeated;
      * a clause that is an existing one with another number (a price, a phone, an hour) REPLACES it -- the newest
        word is the customer's correction -- but only when both have the same non-empty label ("ייעוץ ראשון",
        "טלפון") and that fact appears once on each side, so "חבילה 2" is never read as a correction of "חבילה 1";
      * every other clause is added; a clause the new text leaves out is kept. Nothing is cut and nothing is lost.
    Returns (the merged text, [(old clause, new clause)] for each correction)."""
    old_t, new_cl = str(old or ''), _clauses(new)
    old_cl = _clauses(old_t)
    have = {_norm(c) for c in old_cl}
    old_by_key: dict[str, list[str]] = {}
    for c in old_cl:
        old_by_key.setdefault(_key(c), []).append(c)
    new_keys = [_key(c) for c in new_cl]
    added, changed, merged = [], [], old_t
    for c, k in zip(new_cl, new_keys):
        n = _norm(c)
        if not n or n in have or n in _norm(merged):
            continue
        olds = old_by_key.get(k) or []
        if _NUMBER.search(c) and len(olds) == 1 and new_keys.count(k) == 1 and _label(c) and _label(c) == _label(olds[0]) \
                and _norm(olds[0]) not in {_norm(x) for x in new_cl}:
            merged = merged.replace(olds[0], c, 1)
            changed.append((olds[0], c))
            continue
        added.append(c)
    if added:
        merged = (merged.rstrip() + '\n' if merged.strip() else '') + '; '.join(added)
    return merged, changed


def apply(brief: d.Brief, interp: Interpretation, *, infer_defaults: bool = True,
          require_confirmation: bool = False) -> TurnResult:
    new = _copy(brief)
    res = TurnResult(new)
    for p in interp.proposals:
        q = d.BY_ID.get(p.field)
        if q is None:
            continue
        if p.field == 'logo' and p.value not in ('none', 'uploaded') and new.assets.get('logo'):
            # the owner, 2026-11-23: a logo was uploaded (assets['logo'], field 'uploaded'). Re-saying "I have a logo"
            # must not downgrade it to 'later', and a guess of "a text logo" (ShayFly rev 7) must not replace it, nor
            # raise a conflict -- the uploaded logo stands until the customer says "no logo".
            continue
        old = new.fields.get(p.field)
        origin = getattr(p, 'origin', 'deterministic')
        if p.field == 'content_only' and origin == 'model':
            # R1/8.2: the persistence decision is the customer's, by chip. The model's guess (run 10b: proposed
            # four times at "high") only pre-selects the chip; it never sets the field.
            if not old:
                new.hints[p.field] = p.value
            continue
        if q.kind == 'text' and _off_topic(p.field, str(p.value)):
            # degrade, never block: the proposal is dropped with its reason, the turn continues
            why = f'{p.field}: {origin} proposal {str(p.value)[:40]!r} is technical text, not a requirement'
            res.dropped.append(why)
            _LOG.info('intake: dropped %s', why)
            continue
        if q.kind == 'text' and origin == 'model' and old and old.get('source') == 'default' \
                and p.confidence in (HIGH, MEDIUM) and old['value'] != p.value:
            # Free text (goal, screens, content...) is the model's: it replaces the rule's fallback value. Only the
            # customer's own value (answer / message) is kept over it, through the conflict rule below.
            new.fields[p.field] = {'value': p.value, 'source': 'message' if p.confidence == HIGH else 'default',
                                   'question_id': q.id, 'confidence': 'stated' if p.confidence == HIGH else 'model'}
            (res.applied if p.confidence == HIGH else res.assumed).append(
                {'field': p.field, 'value': p.value, 'source': 'message' if p.confidence == HIGH else 'default'})
            continue
        if origin == 'model' and require_confirmation and material(p.field, new.values()) and \
                (not old or old['value'] != p.value):
            new.hints[p.field] = p.value      # sensitive turn: pre-select and ask, never apply
            res.conflicts.append({'field': p.field, 'current': (old or {}).get('value'), 'proposed': p.value,
                                  'origin': origin, 'reason': 'sensitive turn: needs explicit confirmation'})
            continue
        if q.kind == 'text' and old and old.get('source') in CONFIRMED_SOURCES and p.confidence == HIGH \
                and _extends(old['value'], p.value):
            # Production 2026-11-19 (the owner's law-firm site): the model restated the content field with one fact
            # added (a WhatsApp number); every restatement differed from the confirmed text, so each turn asked "what
            # is right?" again -- a loop. A text that keeps every word of the confirmed one and adds to it extends it.
            new.fields[p.field] = {'value': p.value, 'source': 'message', 'question_id': q.id, 'confidence': 'stated'}
            res.applied.append({'field': p.field, 'value': p.value, 'source': 'message'})
            continue
        if p.field in CUMULATIVE and old and old.get('source') in CONFIRMED_SOURCES and p.confidence == HIGH \
                and not material(p.field, new.values()):
            merged, changed = _merged(old['value'], p.value)
            if merged != old['value']:
                new.fields[p.field] = {'value': merged, 'source': 'message', 'question_id': q.id, 'confidence': 'stated'}
                res.applied.append({'field': p.field, 'value': p.value, 'source': 'message'})
                res.corrected.extend({'field': p.field, 'old': a, 'new': b} for a, b in changed)
            continue
        if p.field == 'goal' and origin == 'model' and old and old.get('source') in CONFIRMED_SOURCES \
                and old['value'] != p.value:
            # the goal restated in other words: the customer's own wording stays, and nothing is asked back
            res.dropped.append(f'{p.field}: {origin} restatement kept out; the customer\'s wording stands')
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
