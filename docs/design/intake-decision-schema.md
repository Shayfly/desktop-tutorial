# §1 sketch — `IntakeDecision` schema + validator (for Michael's signature)

Spec: docs/spec/acceptance-agent-v1.1.md (§1, with the §0 channel law, §6 Gap, §11 failures, §12 prohibitions).
Status: SKETCH. No code until signed. Nothing here touches `resolve_persistence` (PR #300) until the schema is signed.

## A. Language and home
- Python, not TS: the intake, the brief and the contract compiler are Python. The schema is frozen dataclasses with
  `to_dict`/`from_dict`, plus a JSON Schema generated from them (for the card/UI and for tests).
- New module `omni_prod/intake/decision.py`. Stored inside the existing brief row: `project_briefs.brief_json["decision"]`.
  No migration; every brief revision carries the decision as it was at that revision (approval binds to a revision).

## B. Types (spec §1, with the undefined names filled in — each is a proposal)

```python
Conf = Literal["stated", "inferred", "missing"]
Src  = Literal["customer", "rawBrief", "library"]

@dataclass(frozen=True)
class Field(Generic[T]):
    v: T | None
    conf: Conf
    src: Src | None            # None only when conf == "missing"

ArtifactKind = Literal["site","landing","app","saas","game","song","video","agent","combo"]
ArtifactId   = str             # "a1", "a2"... stable inside one IntakeDecision; never reused after a removal
GameGenre    = Literal["puzzle","arcade","quiz","board","other"]     # PROPOSAL — the spec names the type only
SkillId      = str             # a key in omni_prod.skills_registry (validated against it, never free text)
Fact         = omni_prod.fact_canon.Fact   # REUSE: key/value/source/source_ref, already the truth gate's unit

@dataclass(frozen=True)
class ArtifactIntent:
    id: ArtifactId
    kind: Field[ArtifactKind]                  # decision -> button only
    purpose: Field[str]                        # content -> free text
    audience: Field[str]                       # content
    must_include: Field[list[str]]             # content
    persistence: Field[Literal["none","records"]]   # decision -> button only
    game: GameIntent | None = None             # present iff kind.v == "game"
    song: SongIntent | None = None             # present iff kind.v == "song"
    saas: SaasIntent | None = None             # present iff kind.v == "saas"
    agent: AgentIntent | None = None           # present iff kind.v == "agent"

@dataclass(frozen=True)
class Gap:                                      # spec §6, as signed
    field: str                                  # "a1.persistence", "shared.brandName"
    blocks: Literal["build","approval","nothing"]
    resolver: Literal["customer","system"]
    options: tuple[str, ...]
    asked_count: int
    trigger: Literal["missing","stale","conflict"]

@dataclass(frozen=True)
class IntakeDecision:
    v: Literal[1]
    locale: Literal["he-IL"]
    raw_brief: str                              # IMMUTABLE (C below)
    raw_brief_sha256: str                       # what makes "immutable" checkable across revisions
    artifacts: tuple[ArtifactIntent, ...]       # >= 1
    shared: Shared                              # tone, brand_name: Field[str]; business_facts: tuple[Fact, ...]
    gaps: tuple[Gap, ...]
    turns: int
    mode: Literal["menu","free"]
```

`login` and `personal_data` are decisions too (§0 lists them). PROPOSAL: they move into `ArtifactIntent` as
`login: Field["none","simple","roles"]` and `personal_data: Field["no","yes"]`, button-only, so the §0 decision set
is complete in one object. Today they live in `brief.fields`; the migration step maps them.

## C. Validator — `validate(decision, *, previous=None) -> list[Violation]`; any violation = `SCHEMA` (§11: stop)

| # | rule | spec |
|---|---|---|
| V1 | `raw_brief` unchanged from `previous` (sha256 equal); set once, at the first turn | §1 |
| V2 | a DECISION field (kind, persistence, login, personal_data) with `conf == "stated"` has `src == "customer"` — stated only by a button. One exception, closed list: a value the KIND fixes (persistence of song/video) is `stated/library` | §0, §12 |
| V3 | a CONTENT field never has `src == "customer"` from a button event (button events carry the field name; content names are refused) | §0, §12 |
| V4 | `conf == "inferred"` => `src in ("rawBrief","library")`; `conf == "missing"` => `v is None and src is None` | §1 |
| V5 | `len(artifacts) >= 1`; ids unique | §1 |
| V6 | the kind sub-object (game/song/saas/agent) is present iff `kind.v` is that kind; others absent | §1, §9 |
| V7 | every gap names an existing field; `asked_count >= 2` is reported as a defect (`GapAskedTwice`), not a schema stop | §6 |
| V8 | hand-off (§10) only when no gap has `blocks == "build"`; an `inferred` decision is always a `build` gap until stated | §10, §12 ("no kind without confirmation") |
| V9 | `skills` ids exist in the skills registry; `seconds > 0`; `players` in the allowed set | §1 |

Gaps are DERIVED by the validator from the fields (missing/inferred decisions, stale persistence, conflicts) and
merged with the stored `asked_count`, so a gap can never be "forgotten" by a code path that edits fields.

## D. How it meets what exists (no code change in this step)
- `persistence.resolve` (#300) will read `artifacts[i].persistence` (step 3 of §14): `stated/customer` -> customer
  decision; `inferred/rawBrief` -> keyword. The trusted channel into `compile()` stays the generated brief block,
  upgraded to `Product decisions v2: {"artifact":"a1","persistence":{"v":"none","conf":"stated","src":"customer"}}`.
- Strong cues, negations and the fact canon read `raw_brief` only (unchanged rule, now a typed field).
- `decision_asked` (8.6) becomes `Gap.asked_count`; `systemAskedDecisions` = sum over gaps with resolver=customer
  that the system raised.
- §11 `OUT_OF_SCOPE` reuses `planning/feasibility` UNSUPPORTED (arm 6's refusal) — no new refusal path.

## E. Questions for the signature
1. Python dataclasses + generated JSON Schema (not a TS source of truth) — OK?
2. Stored in `brief_json["decision"]` per revision — OK?
3. `login` / `personal_data` inside `ArtifactIntent` (per artifact) or in `shared` (per project)? I propose per
   artifact: "a site + a song" can differ.
4. The proposed `GameGenre` values and `ArtifactId` format.
5. `persistence` for kinds that cannot store (song, video): fixed `Field("none", "stated", "library")` — a library
   fact, not a customer decision, so it is never asked. This is the ONE exception to V2 (closed list, in code). OK?
6. V7: `asked_count >= 2` is a reported defect, not a stop — or should it stop?

## F. Signature answers (Michael 2026-11-11 14:03) — binding, override A-E where they differ

1. Python dataclasses are the source of truth. The JSON Schema is GENERATED and committed
   (`docs/schema/intake-decision.v1.json`); a test regenerates it and fails on any drift. Never written by hand.
2. `brief_json["decision"]` per revision, no migration — plus a check that `raw_brief_sha256` equals the sha256 of
   THAT revision's raw brief, so a decision can never attach to a brief that is not its own.
3. Both: `requires_auth: Field[bool]` is a decision PER ARTIFACT; the identity store is PROJECT-level and derived —
   if two artifacts need sign-in it is one sign-in, not two (`IntakeDecision.identity_store`, derived, never stored).
4. `GameGenre` closed, seven: sport · adventure · strategy · learning · puzzle · action · simulation.
   `ArtifactId` = `art_` + ULID in Crockford base32 (26 chars): sortable, collision-free.
5. The library exception is an explicit allow-list IN the validator (`LIBRARY_FIXED = {("song","persistence"),
   ("video","persistence")}`); anything else stated/library is a SCHEMA violation, so it cannot widen silently.
6. `asked_count == 2` -> reported defect (`GapAskedTwice`); `asked_count >= 3` -> stop (`GapStuck`).

Two added conditions:
- G1 Gap derivation has fixtures: a known missing set produces EXACTLY the expected gaps; a complete decision produces
  zero. A validator that silently returns no gaps fails.
- G2 `stated` requires a button. To make that checkable, `Field` carries its channel: `via: "button" | "text" |
  "extract" | None`. A decision `stated` with `via != "button"` is a SCHEMA violation (except the G5 allow-list); a
  content field with `via == "button"` is a SCHEMA violation (§0 both directions).
