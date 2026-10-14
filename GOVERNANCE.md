# Document governance — what's canonical, what's historical

This repository accumulated a versioned status/validation/readme document for
almost every release from V10 through V28 (see the file listing at the repo
root). None of those per-version documents were ever marked superseded when
the next version shipped, so a reader — human or AI — landing in this repo
cold has no way to tell which claims are still live without reading dozens of
files and cross-checking dates. This document exists to fix that, once, and
to state the rule that keeps it from rotting again.

It does not delete or rewrite history: every file below stays exactly where
it is. This is an index, not a cleanup.

## Current source of truth (read in this order)

1. **`AGENTS.md`** — the engineering mandate. Supersedes the *tone* of every
   older document: no facade, no simulated output portrayed as real, no
   "production ready" claim before the acceptance criteria in
   `PRODUCT_MISSION_AND_ACCEPTANCE.md` actually pass.
2. **`PRODUCT_MISSION_AND_ACCEPTANCE.md`** — what 148AI is supposed to become
   and the objective release-acceptance checklist. This is a task
   specification, not a record of what already works — it says so itself.
3. **`CURRENT_TRUTH_V28_HE.md`** — the verified/not-yet-live-verified split
   for the V28 baseline (branding, tenant/plan contracts, rights gate,
   Postgres creator/subscription adapters, i18n). Last of the per-version
   "current truth" documents; nothing superseded it at that layer because V28
   is still the baseline the M1–M3 work below is layered on top of.
4. **`STATUS.md`** — required by `AGENTS.md`. Covers only the async
   build/live-preview work (M1–M3) built on top of the V28 baseline: what's
   implemented and independently verified, what's implemented but awaiting
   external live verification, what's blocked by a named service, what's not
   implemented. This is the most current statement of what actually runs.
5. **`PATCH_APPLICATION_REPORT.md`** — the evidence backing `STATUS.md`: exact
   commands, exact diffs, every deviation from a pasted directive and why.
6. **`148AI_MASTER_SPEC.md`** — the consolidated current architecture,
   constraints, product acceptance and roadmap. It is not live-status evidence;
   `STATUS.md` wins on what is actually verified.
7. **`00_START_HERE_HE.md`** — the handoff note pointing new sessions (this
   one included) at the current source-of-truth documents above.

If a claim in any other file in this repo contradicts `STATUS.md`, `STATUS.md`
wins.

## Historical / superseded — kept for audit trail, not authoritative

These are snapshots of the repo at a past version. They are real records of
what was checked *then*; none of them were updated for V28 or for the M1–M3
work, so none of them describe the repo's current behavior on their own.

- **Per-version "current truth" / status docs**: `CURRENT_TRUTH_V24_HE.md`,
  `CURRENT_TRUTH_V26_HE.md`, `CURRENT_TRUTH_V27_HE.md`, `V14_STATUS_HE.md`
  through `V23_STATUS_HE.md`. Each superseded by the next version's file, and
  all of them ultimately by `CURRENT_TRUTH_V28_HE.md` + `STATUS.md`.
- **Per-version readmes**: `README_HE.md`, `README_V24_HE.md`,
  `README_V25_HE.md`, `README_V26_HE.md`, `README_V27_HE.md`,
  `README_DEVELOPER_EN.md`, `README_DEVELOPER_V25_EN.md`.
- **Release/validation/quality-gate artifacts** (JSON, machine-generated at
  the time): `VALIDATION-V12.json` … `VALIDATION_V28.json`,
  `QUALITY_GATE_V23.json`, `QUALITY_GATE_V24.json`, `RELEASE_GATE_V27.json`,
  `HOSTILE_STATIC_V24/25/28.json`, `INTERNATIONAL_GATE_V24/25/28.json`,
  `LIVE_HTTP*.json`, `LOAD_SMOKE_V24/28.json`, `BENCHMARK_V25/V28_OFFLINE.json`,
  `YAML_VALIDATION_V24.json`, `DEPENDENCY_STATUS_V27.json`. Each is evidence
  for its own version's claims at the time it was generated, not a live gate.
- **Version-lineage / merge records**: `VERSION_LINEAGE.json`,
  `SOURCE_RECOVERY_INDEX.json`, `MERGE_MANIFEST.md`, `RELEASE-MANIFEST.json`.
  These document how V11→V27 were merged and recovered; none were extended to
  V28 or to the current M1–M3 patches. `SOURCE_RECOVERY_INDEX.json`'s own
  `recovery_rule` ("V27 is the source of truth") is itself superseded by this
  section — left unedited here since it's a machine-generated artifact, not
  prose, and nothing in `omni_prod/`, `tests/`, or `scripts/` reads it.
- **Release notes**: `RELEASE_NOTES_V25.md`, `RELEASE_NOTES_V26.md`,
  `RELEASE_NOTES_V27.md`, `RELEASE_NOTES_V28.md`.
- **Point-in-time gate/checklist docs**: `PRODUCTION_GATE.md`,
  `PRODUCTION_GATE_V12.md`, `LAUNCH_GATES_V28_HE.md`,
  `INTERNATIONAL_GRADE_CHECKLIST_V24.md`, `REVIEWER_CHECKLIST_V26.md`,
  `REVIEWER_CHECKLIST_V27.md`, `REVIEWER_CHECKLIST_V28.md`,
  `GLOBAL_PRODUCT_GATES_V26.md`.
- **External-audit responses**: `GEMINI_AUDIT_RESPONSE_HE.md` — a real
  response to a real external review of V20/V21, kept for the record.
- **Recovery/backup policy versions**: `BACKUP_AND_RECOVERY_POLICY_HE.md`,
  `BACKUP_AND_RECOVERY_POLICY_V27_HE.md`.
- **Fixed test-output transcripts**: `FRESH_UNIT_TEST_OUTPUT_V22.txt` through
  `_V28.txt` — real output at the time, not re-runnable evidence of the
  current tree. `STATUS.md`/`PATCH_APPLICATION_REPORT.md`'s commands are the
  ones to re-run today.
- **Integration guides**: `V12_INTEGRATION_GUIDE_HE.md`,
  `V13_INTEGRATION_GUIDE_HE.md`.
- **`V10_RECOVERY_AND_PARITY_HE.md`** — the V10 behavior-parity record
  referenced by `MERGE_MANIFEST.md`.
- **Roadmap**: `ROADMAP_51_100.md` — forward-looking, not a status claim.

## Investor / fundraising materials — read `STATUS.md` first

`INVESTOR_DEMO_SCRIPT_HE.md`, `PRELAUNCH_INVESTOR_READINESS_HE.md`, and
`VALUATION_EVIDENCE_PLAN_HE.md` are called out separately from the general
historical list above because the cost of treating a stale claim as current
is highest here. `PRELAUNCH_INVESTOR_READINESS_HE.md` is explicitly V23-era
and states its own rule ("don't present a capability to an investor as
existing when it's only a roadmap item") — that rule is exactly why none of
these three should be shown to anyone without first diffing their claims
against the current `STATUS.md`. None of them have been updated for V28 or
for the M1–M3 async-build/preview work, so on their own they now overstate
what's verified. Treat them as draft talking points to be refreshed from
`STATUS.md`, not as a source of truth.

## Product/brand reference (still current, not a status claim)

`BRAND_SYSTEM_V28.md`, `BRAND_PACK/` and `PRICING_AND_UNIT_ECONOMICS_V28.md`
describe intended design/pricing, not verified behavior. They aren't
superseded by anything and don't need to be — they were never status claims
in the first place.

## The rule going forward

Do not create another `CURRENT_TRUTH_V29_HE.md`-style file. `STATUS.md`
already exists for exactly this purpose and `AGENTS.md` requires it be kept
current with its four honest categories — update it in place instead of
forking a new version-numbered copy. If a genuinely new, separate body of
work needs its own status document the way M1–M3 preview/build work did,
add one section to this file's "Current source of truth" list pointing to
it, in the same edit that introduces it, rather than leaving the next reader
to guess which document is live.
