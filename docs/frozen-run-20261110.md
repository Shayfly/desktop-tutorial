# Frozen run — pre-registration (Michael 2026-11-10)

Written and committed BEFORE any arm runs. Nothing below may change after the first arm starts; a change is a new run
with a new id.

```yaml
run: frozen-2026-11-11
baselineSha: <the main commit that merges PR #289 -- filled in the run report, never edited here>
hypothesis: "The system at baselineSha produces passing pages for a new brief with no human code fix."
failure: "any repair round that changed code, or any human code fix, in any arm"
noFixRule: "no code change on main until the last arm finishes; fixes go to a branch and merge after"
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
| restaurant-a | the cafe brief, unchanged | pass/fail |
| restaurant-b | the same brief again | variance (a vs b) |
| florist-new | a florist landing page, no contact details | generalisation; `CANON_INCOMPLETE` ticked |
| florist-hard | the florist with a real phone and address | canon + truth gate under a real load |
| negative | a request outside the capability matrix (e.g. native iOS app with payments) | a clean refusal, no half build |

## Recorded per arm (report schema)

```json
{ "arm": "florist-new", "build_id": "bld_…", "baselineSha": "…", "passed": false, "rounds": 3,
  "codeChangingRounds": 3, "gateWasteRounds": 1, "gateWasteUsd": 0.21, "costUsd": 0.81,
  "humanCodeFixes": 0, "humanDecisions": 4, "degraded": false,
  "quarantinedProbes": ["_invented_contact"], "timeToPreviewSec": 214, "designScore": 83, "canonHash": "…" }
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
| 4/5 arms pass and gate waste < 15% of cost | expand to the first media asset |
| 2–3 pass | one more stabilisation round, no expansion |
| fewer than 2 | stop expansion, back to the gates |

`restaurant-a` and `restaurant-b` count as two arms; `negative` passes when it is refused cleanly.

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
