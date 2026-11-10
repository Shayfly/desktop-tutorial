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
