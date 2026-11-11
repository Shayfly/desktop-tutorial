"""IntakeDecision v1 -- the acceptance agent's output object (docs/spec/acceptance-agent-v1.1.md §1).

Design and signature: docs/design/intake-decision-schema.md (Michael 2026-11-11, sections A-F, G1, G2).

These dataclasses are the SOURCE OF TRUTH. The JSON Schema (docs/schema/intake-decision.v1.json) is generated from
them by `json_schema()` and a test fails on any drift; it is never edited by hand.

The §0 law, enforced by `validate`:
  * a DECISION (kind, persistence, requires_auth, personal_data) is `stated` only by a button (`via == "button"`);
  * a CONTENT field (purpose, audience, must_include, tone, brand_name) is never set by a button.
Gaps are DERIVED here from the fields (`derive_gaps`), never maintained by hand, so no code path can forget one.
This module only defines and checks the object; nothing reads it yet (migration of persistence.resolve is a later,
separately signed step).
"""
from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Literal

CONF = ('stated', 'inferred', 'missing')
SRC = ('customer', 'rawBrief', 'library')
VIA = ('button', 'text', 'extract', 'model')
# src = where the value came from; via = how it entered. They compose; only these pairs are valid (signed 14:12).
VALID_PAIRS = frozenset({('customer', 'button'), ('customer', 'text'), ('rawBrief', 'extract'), ('rawBrief', 'model'),
                         ('library', 'extract')})
ARTIFACT_KINDS = ('site', 'landing', 'app', 'saas', 'game', 'song', 'video', 'agent', 'combo')
GAME_GENRES = ('sport', 'adventure', 'strategy', 'learning', 'puzzle', 'action', 'simulation')   # F4: closed, seven
PLAYERS = (1, 2, 4, 'online')
SONG_USES = ('bg', 'intro', 'ad')
BILLING = ('subscription', 'oneoff')
PERSISTENCE = ('none', 'records')
PERSONAL_DATA = ('no', 'yes')
BLOCKS = ('build', 'approval', 'nothing')
RESOLVERS = ('customer', 'system')
TRIGGERS = ('missing', 'stale', 'conflict')

DECISION_FIELDS = ('kind', 'persistence', 'requires_auth', 'personal_data')       # §0: buttons only
CONTENT_FIELDS = ('purpose', 'audience', 'must_include')                           # §0: free text only
SHARED_CONTENT = ('tone', 'brand_name')
# F5: the ONLY decisions a kind fixes by itself (stated/library). Explicit allow-list; anything else is a violation.
LIBRARY_FIXED = frozenset({('song', 'persistence'), ('video', 'persistence')})
SUBOBJECT = {'game': 'game', 'song': 'song', 'saas': 'saas', 'agent': 'agent'}

_CROCKFORD = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'


def new_artifact_id(*, now_ms: int | None = None, randomness: bytes | None = None) -> str:
    """F4: `art_` + ULID (48-bit ms time + 80-bit randomness) in Crockford base32, 26 chars: sortable, collision-free."""
    ms = int(time.time() * 1000) if now_ms is None else now_ms
    rnd = os.urandom(10) if randomness is None else randomness
    if not 0 <= ms < 2 ** 48 or len(rnd) != 10:
        raise ValueError('ULID needs a 48-bit timestamp and 80 bits of randomness')
    n = (ms << 80) | int.from_bytes(rnd, 'big')
    return 'art_' + ''.join(_CROCKFORD[(n >> (5 * i)) & 31] for i in reversed(range(26)))


def is_artifact_id(value: str) -> bool:
    return (isinstance(value, str) and len(value) == 30 and value.startswith('art_')
            and all(c in _CROCKFORD for c in value[4:]) and value[4] in '01234567')


def sha256(text: str) -> str:
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


# ------------------------------------------------------------------ types

@dataclass(frozen=True)
class Field:
    """One value with its confidence, source and channel (G2: `via` makes "stated only by a button" checkable)."""
    v: Any = None
    conf: Literal['stated', 'inferred', 'missing'] = 'missing'
    src: Literal['customer', 'rawBrief', 'library'] | None = None
    via: Literal['button', 'text', 'extract'] | None = None


MISSING = Field()


# Constructors: `via` is derived from the call, never written by hand at a call site (signed 14:12).
def from_button(v) -> Field:
    """The customer pressed a chip -- the ONLY way a decision becomes stated."""
    return Field(v, 'stated', 'customer', 'button')


def from_text(v) -> Field:
    """The customer typed it -- stated content; never a stated decision."""
    return Field(v, 'stated', 'customer', 'text')


def inferred(v, *, by_model: bool = False) -> Field:
    """Read from the raw brief by rules (extract) or by the model -- inferred until a button confirms it."""
    return Field(v, 'inferred', 'rawBrief', 'model' if by_model else 'extract')


def from_library(v) -> Field:
    """A value the artifact kind fixes (allow-list LIBRARY_FIXED)."""
    return Field(v, 'stated', 'library', 'extract')


@dataclass(frozen=True)
class GameIntent:
    genre: Field = MISSING          # GAME_GENRES
    players: Field = MISSING        # PLAYERS


@dataclass(frozen=True)
class SongIntent:
    style: Field = MISSING          # free text
    seconds: Field = MISSING        # int > 0
    use: Field = MISSING            # SONG_USES


@dataclass(frozen=True)
class SaasIntent:
    payer: Field = MISSING          # free text
    billing: Field = MISSING        # BILLING


@dataclass(frozen=True)
class AgentIntent:
    skills: Field = MISSING         # list of skill ids (checked against the registry when one is given)
    runtime: Field = MISSING        # free text


@dataclass(frozen=True)
class ArtifactIntent:
    id: str
    kind: Field = MISSING                 # decision
    purpose: Field = MISSING              # content
    audience: Field = MISSING             # content
    must_include: Field = MISSING         # content (list[str])
    persistence: Field = MISSING          # decision
    requires_auth: Field = MISSING        # decision, per artifact (F3)
    personal_data: Field = MISSING        # decision
    game: GameIntent | None = None
    song: SongIntent | None = None
    saas: SaasIntent | None = None
    agent: AgentIntent | None = None


@dataclass(frozen=True)
class Gap:
    field: str                            # "<artifact id>.<field>" or "shared.<field>"
    blocks: Literal['build', 'approval', 'nothing']
    resolver: Literal['customer', 'system']
    options: tuple[str, ...] = ()
    asked_count: int = 0
    trigger: Literal['missing', 'stale', 'conflict'] = 'missing'


@dataclass(frozen=True)
class Shared:
    tone: Field = MISSING
    brand_name: Field = MISSING
    business_facts: tuple[dict, ...] = ()   # fact_canon.Fact.to_dict() rows: key, value, source, source_ref


@dataclass(frozen=True)
class IntakeDecision:
    raw_brief: str
    raw_brief_sha256: str
    artifacts: tuple[ArtifactIntent, ...]
    shared: Shared = field(default_factory=Shared)
    gaps: tuple[Gap, ...] = ()
    turns: int = 0
    mode: Literal['menu', 'free'] = 'free'
    v: Literal[1] = 1
    locale: Literal['he-IL'] = 'he-IL'

    @property
    def identity_store(self) -> str:
        """F3: derived, never stored. Any artifact needing sign-in -> ONE project-level identity store."""
        return 'project' if any(a.requires_auth.v is True for a in self.artifacts) else 'none'


# ------------------------------------------------------------------ validation

@dataclass(frozen=True)
class Violation:
    code: str            # SCHEMA | GapAskedTwice | GapStuck
    where: str
    detail: str
    stop: bool           # SCHEMA and GapStuck stop (§11); GapAskedTwice is reported only (F6)


_ALLOWED = {
    'kind': ARTIFACT_KINDS, 'persistence': PERSISTENCE, 'requires_auth': (True, False), 'personal_data': PERSONAL_DATA,
}
_DECISION_OPTIONS = {
    'kind': ARTIFACT_KINDS, 'persistence': PERSISTENCE, 'requires_auth': ('true', 'false'), 'personal_data': PERSONAL_DATA,
}


def _field_shape(f: Field, where: str, out: list[Violation]) -> None:
    def bad(msg):
        out.append(Violation('SCHEMA', where, msg, True))
    if f.conf not in CONF:
        bad(f'conf {f.conf!r} not in {CONF}')
    if f.conf == 'missing':
        if f.v is not None or f.src is not None or f.via is not None:
            bad('a missing field carries no value, source or channel')
        return
    if f.v is None:
        bad(f'{f.conf} field has no value')
    if f.src not in SRC:
        bad(f'src {f.src!r} not in {SRC}')
    if f.via not in VIA:
        bad(f'via {f.via!r} not in {VIA}')
    if f.src in SRC and f.via in VIA and (f.src, f.via) not in VALID_PAIRS:
        bad(f'src {f.src!r} cannot enter via {f.via!r} (valid pairs: {sorted(VALID_PAIRS)})')
    if f.conf == 'inferred' and f.src == 'customer':
        bad('inferred values come from the raw brief or the library, never from the customer')


def _decision(f: Field, name: str, kind: str | None, where: str, out: list[Violation]) -> None:
    _field_shape(f, where, out)
    if f.conf == 'missing':
        return
    if f.v not in _ALLOWED[name]:
        out.append(Violation('SCHEMA', where, f'{f.v!r} not in {_ALLOWED[name]}', True))
    if f.conf == 'stated':
        if f.src == 'library':
            if (kind, name) not in LIBRARY_FIXED:     # F5: explicit allow-list
                out.append(Violation('SCHEMA', where, f'stated/library is allowed only for {sorted(LIBRARY_FIXED)}', True))
        elif f.via != 'button' or f.src != 'customer':   # G2: a decision is stated only by a button
            out.append(Violation('SCHEMA', where, f'a decision is stated only by a customer button (got src={f.src}, via={f.via})', True))


def _content(f: Field, where: str, out: list[Violation]) -> None:
    _field_shape(f, where, out)
    if f.via == 'button':                                  # §0 the other direction: no button for a fact
        out.append(Violation('SCHEMA', where, 'a content field is never set by a button', True))


def validate(decision: IntakeDecision, *, revision_raw_brief: str | None = None,
             previous: IntakeDecision | None = None, skill_ids: set[str] | None = None) -> list[Violation]:
    """All violations. Any `stop` violation means SCHEMA (§11: stop). `revision_raw_brief` = the raw brief of the brief
    revision this decision is stored in (F2); `previous` = the decision of the previous revision (rawBrief immutable)."""
    out: list[Violation] = []
    if decision.v != 1 or decision.locale != 'he-IL' or decision.mode not in ('menu', 'free'):
        out.append(Violation('SCHEMA', 'decision', 'v/locale/mode', True))
    if decision.raw_brief_sha256 != sha256(decision.raw_brief):
        out.append(Violation('SCHEMA', 'raw_brief', 'raw_brief_sha256 does not match raw_brief', True))
    if revision_raw_brief is not None and decision.raw_brief_sha256 != sha256(revision_raw_brief):
        out.append(Violation('SCHEMA', 'raw_brief', 'this decision belongs to another brief revision (F2)', True))
    if previous is not None and previous.raw_brief_sha256 != decision.raw_brief_sha256:
        out.append(Violation('SCHEMA', 'raw_brief', 'raw_brief is immutable once set (V1)', True))
    if not decision.artifacts:
        out.append(Violation('SCHEMA', 'artifacts', 'at least one artifact', True))
    ids = [a.id for a in decision.artifacts]
    if len(set(ids)) != len(ids):
        out.append(Violation('SCHEMA', 'artifacts', 'artifact ids must be unique', True))
    for a in decision.artifacts:
        where = a.id
        if not is_artifact_id(a.id):
            out.append(Violation('SCHEMA', where, 'id is not art_ + a 26-char Crockford ULID (F4)', True))
        kind = a.kind.v if a.kind.conf != 'missing' else None
        for name in DECISION_FIELDS:
            _decision(getattr(a, name), name, kind, f'{where}.{name}', out)
        for name in CONTENT_FIELDS:
            _content(getattr(a, name), f'{where}.{name}', out)
        for sub, attr in SUBOBJECT.items():                # V6: the sub-object exists iff the kind is it
            present = getattr(a, attr) is not None
            if present != (kind == sub):
                out.append(Violation('SCHEMA', f'{where}.{attr}', f'{attr} must be present iff kind == {sub!r}', True))
        if a.game is not None:
            _choice(a.game.genre, GAME_GENRES, f'{where}.game.genre', out)
            _choice(a.game.players, PLAYERS, f'{where}.game.players', out)
        if a.song is not None:
            _content(a.song.style, f'{where}.song.style', out)
            _field_shape(a.song.seconds, f'{where}.song.seconds', out)
            if a.song.seconds.conf != 'missing' and not (isinstance(a.song.seconds.v, int) and a.song.seconds.v > 0):
                out.append(Violation('SCHEMA', f'{where}.song.seconds', 'seconds must be a positive int', True))
            _choice(a.song.use, SONG_USES, f'{where}.song.use', out)
        if a.saas is not None:
            _content(a.saas.payer, f'{where}.saas.payer', out)
            _choice(a.saas.billing, BILLING, f'{where}.saas.billing', out)
        if a.agent is not None:
            _field_shape(a.agent.skills, f'{where}.agent.skills', out)
            if skill_ids is not None and a.agent.skills.conf != 'missing':
                unknown = [s for s in a.agent.skills.v or () if s not in skill_ids]
                if unknown:
                    out.append(Violation('SCHEMA', f'{where}.agent.skills', f'unknown skill ids {unknown}', True))
            _content(a.agent.runtime, f'{where}.agent.runtime', out)
    for name in SHARED_CONTENT:
        _content(getattr(decision.shared, name), f'shared.{name}', out)
    known = _field_names(decision)
    for g in decision.gaps:
        if g.field not in known:
            out.append(Violation('SCHEMA', g.field, 'a gap names a field that does not exist', True))
        if g.blocks not in BLOCKS or g.resolver not in RESOLVERS or g.trigger not in TRIGGERS or g.asked_count < 0:
            out.append(Violation('SCHEMA', g.field, 'gap shape', True))
        if g.asked_count == 2:
            out.append(Violation('GapAskedTwice', g.field, 'asked twice: reported (F6)', False))
        elif g.asked_count >= 3:
            out.append(Violation('GapStuck', g.field, f'asked {g.asked_count} times: the mechanism is broken (F6)', True))
    return out


def _choice(f: Field, allowed: tuple, where: str, out: list[Violation]) -> None:
    _field_shape(f, where, out)
    if f.conf != 'missing' and f.v not in allowed:
        out.append(Violation('SCHEMA', where, f'{f.v!r} not in {allowed}', True))


def _field_names(decision: IntakeDecision) -> set[str]:
    names = {f'shared.{n}' for n in SHARED_CONTENT}
    for a in decision.artifacts:
        names |= {f'{a.id}.{n}' for n in DECISION_FIELDS + CONTENT_FIELDS}
    return names


# ------------------------------------------------------------------ gaps (derived, never hand-kept)

def derive_gaps(decision: IntakeDecision, *, stale: frozenset[str] = frozenset()) -> tuple[Gap, ...]:
    """The gaps implied by the fields, merged with the stored asked counts. Rules:
      * a decision that is missing or only inferred -> blocks BUILD (§10, §12: no decision without confirmation);
        requires_auth / personal_data are only open when the kind can store (not a library-fixed none);
      * `stale` (field paths the caller found stale, e.g. persistence "none" after a sign-up was added) -> blocks build;
      * purpose missing -> blocks APPROVAL; tone / brand name missing -> blocks nothing (shown, never forced).
    """
    asked = {g.field: g.asked_count for g in decision.gaps}
    out: list[Gap] = []

    def add(path, blocks, options=(), trigger='missing'):
        out.append(Gap(path, blocks, 'customer', tuple(options), asked.get(path, 0), trigger))

    for a in decision.artifacts:
        kind = a.kind.v if a.kind.conf != 'missing' else None
        for name in DECISION_FIELDS:
            f = getattr(a, name)
            path = f'{a.id}.{name}'
            if path in stale:
                add(path, 'build', _DECISION_OPTIONS[name], 'stale')
                continue
            if name in ('requires_auth', 'personal_data') and (kind, 'persistence') in LIBRARY_FIXED:
                continue                               # a song/video stores nothing: nobody signs in to it
            if f.conf in ('missing', 'inferred'):
                add(path, 'build', _DECISION_OPTIONS[name])
        if a.purpose.conf == 'missing':
            add(f'{a.id}.purpose', 'approval')
    for name in SHARED_CONTENT:
        if getattr(decision.shared, name).conf == 'missing':
            add(f'shared.{name}', 'nothing')
    return tuple(out)


def handoff_ready(decision: IntakeDecision) -> bool:
    """§10: hand-off only when no gap blocks the build."""
    return not any(g.blocks == 'build' for g in decision.gaps)


# ------------------------------------------------------------------ serialisation + generated JSON Schema

def to_dict(obj) -> Any:
    if is_dataclass(obj):
        return {f.name: to_dict(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, (list, tuple)):
        return [to_dict(x) for x in obj]
    return obj


def from_dict(d: dict) -> IntakeDecision:
    def fld(x):
        return Field(**x) if x else MISSING

    def sub(cls, x):
        return None if x is None else cls(**{k: fld(v) for k, v in x.items()})

    arts = tuple(ArtifactIntent(
        id=a['id'], **{n: fld(a.get(n)) for n in DECISION_FIELDS + CONTENT_FIELDS},
        game=sub(GameIntent, a.get('game')), song=sub(SongIntent, a.get('song')),
        saas=sub(SaasIntent, a.get('saas')), agent=sub(AgentIntent, a.get('agent'))) for a in d['artifacts'])
    s = d.get('shared') or {}
    shared = Shared(tone=fld(s.get('tone')), brand_name=fld(s.get('brand_name')),
                    business_facts=tuple(s.get('business_facts') or ()))
    gaps = tuple(Gap(g['field'], g['blocks'], g['resolver'], tuple(g.get('options') or ()), int(g.get('asked_count', 0)),
                     g.get('trigger', 'missing')) for g in d.get('gaps') or ())
    return IntakeDecision(raw_brief=d['raw_brief'], raw_brief_sha256=d['raw_brief_sha256'], artifacts=arts,
                          shared=shared, gaps=gaps, turns=int(d.get('turns', 0)), mode=d.get('mode', 'free'),
                          v=d.get('v', 1), locale=d.get('locale', 'he-IL'))


def _field_schema(enum=None, item=None) -> dict:
    value = {'enum': list(enum)} if enum is not None else (item or {})
    return {'type': 'object', 'additionalProperties': False, 'required': ['v', 'conf', 'src', 'via'],
            'properties': {'v': {'anyOf': [value, {'type': 'null'}]}, 'conf': {'enum': list(CONF)},
                           'src': {'enum': list(SRC) + [None]}, 'via': {'enum': list(VIA) + [None]}}}


def json_schema() -> dict:
    """The generated contract (F1). Structure and enums only; the cross-field rules live in `validate`."""
    text, texts = {'type': 'string'}, {'type': 'array', 'items': {'type': 'string'}}

    def obj(props: dict, required=None):
        return {'type': 'object', 'additionalProperties': False, 'required': required or list(props), 'properties': props}

    def nullable(schema):
        return {'anyOf': [schema, {'type': 'null'}]}

    artifact = obj({
        'id': {'type': 'string', 'pattern': '^art_[0-7][0-9A-HJKMNP-TV-Z]{25}$'},
        'kind': _field_schema(ARTIFACT_KINDS), 'purpose': _field_schema(item=text),
        'audience': _field_schema(item=text), 'must_include': _field_schema(item=texts),
        'persistence': _field_schema(PERSISTENCE), 'requires_auth': _field_schema(item={'type': 'boolean'}),
        'personal_data': _field_schema(PERSONAL_DATA),
        'game': nullable(obj({'genre': _field_schema(GAME_GENRES), 'players': _field_schema(PLAYERS)})),
        'song': nullable(obj({'style': _field_schema(item=text), 'seconds': _field_schema(item={'type': 'integer', 'minimum': 1}),
                              'use': _field_schema(SONG_USES)})),
        'saas': nullable(obj({'payer': _field_schema(item=text), 'billing': _field_schema(BILLING)})),
        'agent': nullable(obj({'skills': _field_schema(item=texts), 'runtime': _field_schema(item=text)})),
    })
    gap = obj({'field': text, 'blocks': {'enum': list(BLOCKS)}, 'resolver': {'enum': list(RESOLVERS)},
               'options': texts, 'asked_count': {'type': 'integer', 'minimum': 0}, 'trigger': {'enum': list(TRIGGERS)}})
    fact = obj({'key': text, 'value': text, 'source': text, 'source_ref': text})
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'https://148ai/schema/intake-decision.v1.json',
        'title': 'IntakeDecision v1 (generated from omni_prod/intake/decision.py -- do not edit)',
        **obj({
            'raw_brief': text, 'raw_brief_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
            'artifacts': {'type': 'array', 'minItems': 1, 'items': artifact},
            'shared': obj({'tone': _field_schema(item=text), 'brand_name': _field_schema(item=text),
                           'business_facts': {'type': 'array', 'items': fact}}),
            'gaps': {'type': 'array', 'items': gap}, 'turns': {'type': 'integer', 'minimum': 0},
            'mode': {'enum': ['menu', 'free']}, 'v': {'const': 1}, 'locale': {'const': 'he-IL'},
        }),
    }


SCHEMA_PATH = os.path.join('docs', 'schema', 'intake-decision.v1.json')


if __name__ == '__main__':      # python -m omni_prod.intake.decision --write
    import json
    import sys
    text_out = json.dumps(json_schema(), ensure_ascii=False, indent=1) + '\n'
    if '--write' in sys.argv:
        os.makedirs(os.path.dirname(SCHEMA_PATH), exist_ok=True)
        with open(SCHEMA_PATH, 'w', encoding='utf-8') as fh:
            fh.write(text_out)
    else:
        sys.stdout.write(text_out)
