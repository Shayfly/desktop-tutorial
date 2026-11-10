# Frozen run — pre-registration (Michael 2026-11-10)

Written and committed BEFORE any arm runs. Nothing below may change after the first arm starts; a change is a new run
with a new id.

```yaml
run: frozen-2026-11-11
baselineSha: <the main commit that merges PR #289 -- filled in the run report, never edited here>
baseline:            # all three identify the frozen system; recorded in the run report, never edited here
  sha: <main commit after PR #291>
  manifestHash: <sha256 of omni_prod/probe_manifest.py at sha>
  fixturesCommit: <last commit touching tests/test_gate_mutations_20261110.py and tests/test_frozen_run_conditions_20261110.py>
hypothesis: "The system at baseline.sha produces passing pages for a new brief with no human code fix."
failure: "any repair round that changed code, or any human code fix, in any arm"
noFixRule: "no code change on main until the last arm finishes; fixes go to a branch and merge after the run"
gateFreeze:          # Michael 2026-11-10: the baseline must settle before it is measured
  starts: "the moment PR #291 merges"
  length: 72h
  rule: "no change to gate files (docs/gate-freeze.json gate_files) for 72h; product fixes only. The baseline SHA is the
         main commit at the END of the window; .github/workflows/gate-freeze.yml fails any PR that touches a gate file while
         docs/gate-freeze.json says the freeze is active"
blindReview: "the design critic sees screenshots and the brief only -- never the arm name, the cost or other arms"
rollback:            # by layer (Michael 2026-11-10), written, not judged case by case
  service: "a gate regression in the SERVICE (an approved page now fails) -> revert the last PR first, fix after"
  measurement: "a regression in the MEASURING TOOL itself -> fix forward, in the same PR, and mark the arm/run"
  sha: <main commit after PR #291>
knownGaps: ["json_ld_schema: no probe exists; a florist page passes without structured data -- 'passed' is not 'complete'"]
models:              # pinned: the catalog at baselineSha (infra/worker-host/model-catalog.json)
  architect: gemini-3.1-flash-lite (LIGHT lane) | claude-sonnet-5-5 (founder)
  builder:   claude-sonnet-5-5 (task-only codegen, LIGHT/STANDARD)
  repair:    claude-sonnet-5-5
  review:    claude-sonnet-5-5
  critic:    claude-sonnet-5-5 (design critic, founder builds)
providerHealthAtStart: "the first arm's model_route_events (fallbacks and rejections) are the snapshot"
```

A provider-side model update during the run invalidates it: every arm records `model_route_events`; a different
model answering than pinned marks that arm `degraded`.

## Arms

| arm | brief | what it measures |
|---|---|---|
| arm | brief | what it measures | marked |
|---|---|---|---|
| restaurant-a | the cafe brief, unchanged | pass/fail | |
| restaurant-b | the same brief again | variance (a vs b) | |
| florist-hard | Michael's florist brief, passed on **verbatim** (local phone with dashes, "רח'", uneven hours, a reviews line with no reviews) | canon + truth gate under a real load | `informed` (written by someone who knows the parser) |
| florist-new | the same florist brief with the phone and address removed | the incomplete-canon path | `informed`, `warned` |
| negative | a request outside the capability matrix (native iOS app with in-app payments) | a clean refusal, no half build | |

`truth-inert`: an arm or regression build whose canon has zero facts. The truth gate had nothing to compare, so its
pass says nothing about truth coverage; it is reported separately and never counted like a build the gate tested.

`warned` (florist-new) passes ONLY if all three happened: the `CANON_INCOMPLETE` warning was shown, the tick box was
required, and the server refused the approval until it was ticked. Otherwise the arm fails -- it must not count like
a clean pass. A truly blind generalisation test needs a real customer; it is not claimed here.

## Recorded per arm (report schema)

Every field below is mandatory (`omni_prod/frozen_run_report.py`, `REQUIRED_FIELDS`):

```json
{ "arm": "florist-new", "build_id": "bld_…", "baselineSha": "…", "passed": false, "rounds": 3,
  "codeChangingRounds": 3, "gateWasteRounds": 1, "gateWasteUsd": 0.21, "costUsd": 0.81, "gateWasteShare": 0.26,
  "humanCodeFixes": 0, "humanDecisions": 4, "degraded": false, "warned": true, "informed": true,
  "models": ["claude-sonnet-5-5", "gemini-3.1-flash-lite"], "offPinModels": [],
  "quarantinedProbes": ["_invented_contact"], "timeToPreviewSec": 214, "designScore": 83, "canonHash": "…",
  "knownGaps": ["json_ld_schema"] }
```

`humanDecisions` = customer answers + approvals in the conversation before the build (counted from the conversation
store). `omni_prod/frozen_run_report.py` derives every other field from the build's evidence.

## Stop rules

- a critical probe quarantined → the arm continues, is marked `degraded`, and does not count as proof;
- a repair round above 6 → full stop and escalation (the engine already stops at 6);
- the same probe failing in two arms → the run stops: the gate is broken (`GateEscalation` enforces this inside a
  build when an earlier build quarantined the same probe).

## Decision gate (fixed now, before results)

| result | next |
|---|---|
| restaurant-a AND restaurant-b pass, 2 of the other 3 pass, gate waste < 15% of total cost | expand to the first media asset |
| restaurant a/b split, or 1 of the other 3 | one more stabilisation round, no expansion |
| both restaurant arms fail, or 0 of the other 3 | stop expansion, back to the gates |

The two restaurant arms are one brief: variance is AND, never OR. `negative` passes when it is refused cleanly.
`warned` passes only under the rule above. A `degraded` arm never counts as a pass.

## What this run does not show

Design quality, fit for a real customer, or that the system works without the person who built it. Those are
other runs, with other people. Review is "blind" only in the narrow sense available: the design critic sees
screenshots and the brief, never the arm name or the cost.

## Gate conditions in force at baselineSha

- markup gates judge the served page; source readers are exactly the six declared in `omni_prod/probe_manifest.py`;
- quarantine needs a byte-identical DOM anchor in three consecutive rounds; critical probes (declared
  `critical: True`) in quarantine withdraw `release_ready` and mark the version "PREVIEW ONLY";
- a probe quarantined again after an earlier build quarantined it stops the build (`gate_escalation`);
- the fact canon is shown and approved with the brief; `CANON_INCOMPLETE` needs the tick box;
- `AMBIGUOUS` phone numbers are advisory; gate waste is measured from gateway spend;
- the current gates pass both previously approved builds (`.github/workflows/gate-regression.yml`).

## Amendment — Michael 2026-11-10 22:54, at ignition (supersedes the arm table above)

The 5-arm registration above never ran an arm. Per this document's own rule, the change below is a NEW RUN:
`run: frozen-2026-11-10b`. Honest timing note: the amendment and the owner's ignition arrived in the same message;
the pre-registration was committed minutes after arm 1 started, and this note records that rather than hiding it.

**Six arms, fixed order, pauses between arms, report row written immediately after each:**

| # | arm | marked | note |
|---|---|---|---|
| 1 | locksmith-hard | | NEW: two phones; STRICTER GATE: the canon must hold both phones as TWO SEPARATE facts -- anything else is a FAIL of the arm, not a warning. Extra report fields for this arm: `canonFacts`, `phonesParsed`, `warnings` |
| 2 | florist-details | `informed` | the full florist brief |
| 3 | florist-nodetails | `informed`, `warned` | phone+address removed; the CANON_INCOMPLETE tick path |
| 4 | restaurant-a | | |
| 5 | restaurant-b | | variance vs a |
| 6 | refusal-control | | last -- cheap, must not cross with anything |

**Decision gate: 5 of 6 arms pass, and gate waste under 15%.**

**Freeze: active until the END OF THE LAST ARM (not a count, not a clock); 72h remains only a backstop.**

Pre-computed for arm 1 (frozen canon on the locksmith brief, before the build finished): phone=2 (+972521234567,
+97289876543), address=1, hours=1, canon hash `38d1ca8224efb559`. Known extraction gaps recorded as arm `warnings`,
not fixed (the code is frozen): the quoted business name (no 'שם העסק:' prefix), the reviews line ('— author' with
semicolons, not the • format), and the textual Friday/Saturday hours.
