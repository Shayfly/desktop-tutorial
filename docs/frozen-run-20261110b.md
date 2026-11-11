# Frozen run frozen-2026-11-10b — pre-registration (Michael 2026-11-10 22:54)

Supersedes `frozen-2026-11-11` (docs/frozen-run-20261110.md), which never ran an arm. That document is a byte-level
gate input (named in frozen_run_report.py) and stays UNTOUCHED; per its own rule -- a change is a new run with a new
id -- this run has its own registration. All rules of the original (no-fix, blind review, rollback by layer, models
pinned, warned/informed semantics, truth-inert, known gaps) apply unchanged; only the deltas are listed here.

Honest timing note: the amendment and the owner's ignition arrived in the same message (22:54); this registration
was committed minutes after arm 1 entered intake, and records that rather than hiding it.

## Baseline (verified)
sha e196a9251efcef98f1bcfc9cd88a24401b47eac8 (final #292 head; tree byte-identical to merge 7e97cc7, rev-parse
^{tree} equal) · manifestHash 406eff73632b66abf04261ada807b727c0cd4bd04a170bf9791ad0adea9f055f · fixturesCommit
8530b47c5f2dfaef6928d0e4b9a2ca7e8d057465 · behavioural digest flag-off 728eb139efa6f3eab28ae603ede3b5b3fa9b78029642981dfdd169ba008b9a16
(identical to the digest at 2c1d6cb -- the frozen system IS the settled baseline).

## Six arms, fixed order
| # | arm | marked | note |
|---|---|---|---|
| 1 | locksmith-hard | | two phones; STRICTER GATE: the canon must hold both phones as TWO SEPARATE facts -- anything else FAILS the arm, no warning. Extra fields: `canonFacts`, `phonesParsed`, `warnings` |
| 2 | florist-details | `informed` | the full florist brief |
| 3 | florist-nodetails | `informed`, `warned` | phone+address removed; the CANON_INCOMPLETE tick path |
| 4 | restaurant-a | | |
| 5 | restaurant-b | | variance vs a |
| 6 | refusal-control | | last -- cheap, must not cross with anything |

Pauses between arms; the report row is written immediately after each arm; triage between arms is allowed, code
fixes are not. **Decision gate: 5 of 6 pass, and gate waste under 15%.**

**Freeze: active until the END OF THE LAST ARM (no arm count, no clock); 72h is only a backstop.**

## Pre-computed, arm 1 (frozen canon on the locksmith brief)
phone=2 (+972521234567, +97289876543), address=1, hours=1, canon hash `38d1ca8224efb559` -> the strict gate passes
at canon level. Extraction gaps recorded as arm `warnings`, NOT fixed (frozen code): the quoted business name (no
'שם העסק:' prefix), the reviews line ('— author' with semicolons, not the • format), the textual Fri/Sat hours.

## Correction 1 — 2026-11-10T22:12Z (after arm 1, before arm 2) — Michael 2026-11-11 00:07

A timestamped correction, never a silent edit. Nothing above this line changed.

**The run is declared `routing-open`, all six arms, uniformly.** "Pinned" means the pinned model ANSWERED — not
that the catalog was available. Two separate states: a fallback declared in advance in the registration = still
pinned; a runtime choice from the catalog ("cheapest eligible") = NOT pinned. By that rule both the
gemini-3.8-flash escalation and the gpt-6.1-sol review routing in arm 1 were not pinned — but marking one arm
`degraded` would mark all six and the flag would mean nothing. So: arm 1 stays `passed`, the run carries
`routing-open` as a run-level limitation in the report, and `modelsUsed` is recorded per arm. Pinning should have
been ENFORCED before arm 1 and was not; documented now, the enforcement fix goes on the post-run list. No code
changes during the run.

**Arm 1 leads with its real flag: NOT AUTONOMOUS.** 13 human decisions for one brief, over the declared threshold
(>=12 = not autonomous). The technical pass does not lead the arm's reporting; this does.

**Findings of arm 1 (findings, not warnings; recorded, not fixed during the run):**
1. The reviews never entered the canon, so the truth gate never checked them in the hard arm. The brief beat the
   extraction ('— author' + semicolons vs the • format). A hole, not a warning.
2. Two punctuation-free owner messages ("לא תתחיל מאשר לך", "לא מאשר") were read as refusals. Conservative under
   ambiguity, but an intake that reads shorthand as refusal burns turns: 2 messages = 2 turns.
3. The intake re-asked a question the approved brief had already settled (content-only vs contact form).
4. Cost $1.549 ran on a founder account — not comparable to customer-lane caps; tagged `founder-account`.

Arm 1 `modelsUsed`: claude-sonnet-5-5 (architect, codegen, repairs); gemini-3.8-flash (catalog escalation after a
sonnet invalid-JSON repair reply); gpt-6.1-sol (review, runtime catalog choice).

## Correction 2 — 2026-11-11T06:35Z (after arm 2, before arm 3) — Michael 2026-11-11 08:26

A timestamped correction, never a silent edit. Nothing above this line changed.

**Arm 2 (florist-details) FAILED** in behavioural acceptance after 5 repair rounds: `missing required behavior kinds:
data_create`. The contract (unified_engine keyword rule: "הזמנה" -> modules customers/availability/bookings) required a
data_create behaviour for a page the owner explicitly made static; the builder produced a correct static page. The
decision gate (5 of 6) is no longer reachable.

**Arm 1 re-checked against its artifact, as required before the report closes.** Arm 1's contract carried the same
data requirement, but its behaviour plan covered `data_create` with a REFUSAL check (`POST /` -> HTTP 405 expected and
returned): the locksmith page writes no data. Arm 1's pass is NOT a pass on unrequested product. The difference
between arm 1 and arm 2 is the model-written behaviour plan (arm 2's plan had no data_create step at all), not the
product.

**Amended plan:**
| # | arm | status |
|---|---|---|
| 3 | florist-nodetails | runs as written, marked `reproduction` (and `informed`, `warned`) |
| 4 | restaurant-a | SKIPPED -- the decision gate is already unreachable; same contract path, same information for $2-3 |
| 5 | restaurant-b | SKIPPED -- same reason |
| 6 | refusal-control | runs LAST -- independent of the contract path, the one clean data point left |

**Outcomes of arm 3, fixed now, before it runs:**
- fails on the SAME missing kind (`data_create`) -> the stop condition is met, the defect is proven systematic, the run
  stops after arm 6;
- passes through a data_create REFUSAL check (as arm 1 did) -> the contract defect is still present and recorded; the
  pass is marked `passed-via-refusal-check` and proves only that the behaviour planner sometimes covers the kind;
- fails on anything else -> recorded as its own failure; the run still stops after arm 6.

**Findings added:**
6. The gate-waste metric counted 0 for 5 repair rounds burned on a requirement the product must NOT meet. It measures
   quarantine loops only. Any round spent on a requirement the product is not supposed to satisfy is gate waste.
7. Priority is inverted in the contract: a keyword overrode an explicit decision. An explicit decision always wins.
8. "הזמנה" sat inside a ready-made WhatsApp message (marketing copy). "The word appears" must differ from "the
   business takes orders on the site".
9. (pending) whether arm 2's draft invented testimonials for "מה אומרים עלינו" -- the brief gives none.
