# §14 step 3 sketch — `persistence.resolve` reads the `Field` (for Michael's signature)

Depends on: #300 (merged), #303 (IntakeDecision schema). Status: SKETCH, no code until signed.

## 0. What reads what today
`brief.fields["content_only"]` (answer) -> `discovery.requirements_text` writes `Product decisions v1: {"persistence":..}`
into the generated block -> `compile()` -> `persistence.read_decision(text)` -> `resolve`. Nothing produces an
IntakeDecision yet (the menu engine is step 4).

## 1. The channel is DERIVED from where the value was written — never written by hand
Checked in the code: a quick-reply chip arrives as `turn(answers=...)` and is stored as `source: "answer"` (its
label is what the chat shows: "פרטים אישיים: לא" in arm 1 was a chip); typed text goes through the interpreter as
a proposal and is stored as `source: "message"`. So, per brief field:

| brief field source | Field |
|---|---|
| `answer` | `from_button(v)` — stated / customer / button |
| `message` | `from_text(v)` — stated / customer / **text** (not a stated decision under G2) |
| model hint (`hints`) | `inferred(v, by_model=True)` |
| rule hint from the request | `inferred(v)` (extract) |
| absent | `MISSING` |

## 2. Producer adapter (no menu yet): `decision_from_brief(brief) -> IntakeDecision`
One artifact (`art_` ULID created once per project and stored, so it does not change between revisions), `kind` from
the family classifier as `inferred` (never stated — §12), `persistence` from `content_only` (yes -> none,
no -> records) via the table above, `requires_auth` from `login` (none -> False), `personal_data` from
`personal_data`; `raw_brief` = `brief.prompt`. Gaps by `derive_gaps`. Written to `brief_json["decision"]` on every
brief save and validated with `revision_raw_brief=brief.prompt` (F2).

## 3. The trusted channel into compile: `Product decisions v2`
`requirements_text` writes `Product decisions v2: {"artifact":"art_…","persistence":{"v":"none","conf":"stated",
"src":"customer","via":"button"}}` from the stored decision. `read_decision` prefers v2, falls back to v1, then to the
legacy CONTENT-ONLY line. Only the LAST generated block is read (unchanged rule).

Mapping into `resolve` (precedence unchanged):
- `stated/customer/button` or `stated/library` -> customer decision;
- `stated/customer/text`, `inferred/*`, `missing`, **or no decision object at all** -> NO customer decision
  (keyword path: strong cues decide, otherwise the NEEDS_CLARIFICATION backstop asks).

**Null safety (your warning):** an absent `decision`, an absent v2 line, or a field with `v: null` is NEVER read as
`none`. It is "no decision", exactly today's behaviour. Fixture: every run-10b and R1/R2 test passes unchanged with
the adapter off, and again with it on.

## 4. Shadow first, then enforce
Production intake must not stop because a new validator is wrong:
- **shadow** (this PR): the decision is built, validated and stored; a SCHEMA violation is logged
  (`intake_decision_violation`, one line per violation) and the v1 path stays authoritative. The report counts
  violations per run.
- **enforce** (a later one-line flip, signed separately after one clean evening run): v2 becomes authoritative and a
  SCHEMA violation stops the turn (§11).

## 5. One behaviour change to sign explicitly
Under G2 a TYPED persistence answer ("זה דף סטטי") stops being a customer decision once enforced: it pre-selects the
chip, and the chip must be pressed. In shadow mode nothing changes; the log shows how often it would have happened.

## 6. Fixtures
- adapter: answer -> button, message -> text, hint -> inferred, absent -> missing (one test per row of §1)
- null safety: no decision / no v2 line / v=null -> identical contract to today (run-10b fixtures, both modes)
- v2 preferred over v1 when both exist; a v2 line typed by the customer (outside the generated block) is ignored
- shadow: a forced SCHEMA violation is logged and does NOT change the contract
- the artifact id is stable across brief revisions

## 7. Signed (Michael 2026-11-11 14:26) — three conditions, binding

**C1. No enforcement before the button exists.** Enforcement (§4 "enforce", and with it §5) is not even proposed
until the §3 card with decision chips is live and working in the product. A customer who can only type must never
end up with a blocking gap nobody can close. The enforce flip PR must link the merged §3 PR and a run where the
chips were used.

**C2. Version precedence.** If v1 and v2 lines both appear in the generated block, the HIGHER version wins and v1 is
ignored entirely (not merged, not used as a fallback for missing v2 fields). One truth per brief. Fixture: v1
`records` + v2 `none` -> `none`; v1 `none` + v2 with persistence `missing` -> NO decision (not `none`).

**C3. Shadow creates no gaps that block.** In shadow mode a missing or invalid decision is written to the log only:
it does not add a gap to the turn, does not change `asked`, does not change the contract, status or questions.
Fixture: the same conversation with shadow on and off produces byte-identical contracts, turn questions and
`decision_asked`; only the log differs.

**C3 consequence (follows from it, stated so the code cannot drift):** in shadow mode the `Product decisions v2` line
is NOT written into the generated block. The block is part of the contract prompt and its fingerprint, so writing it
would already change contracts. In shadow the decision lives only in `brief_json["decision"]` and the log; the v2
line (and C2's precedence) start with enforcement.
