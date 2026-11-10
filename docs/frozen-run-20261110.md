# Frozen run — definition (Michael 2026-11-10)

**Frozen:** system code AND gates, at the `main` commit that merges this PR. Its SHA is recorded in the run report
and in each build's evidence (`deploy SHA`); the mutation and false-positive suite
(`tests/test_gate_mutations_20261110.py`) is part of that commit and must pass on it.

**Runs:**
1. The cafe brief (project "מסעדה"), twice, unchanged — variance, not just pass/fail.
2. One new brief in another domain, with nothing fixed for it.

**Failure, decided before the runs:**
- any repair round that changed code, or
- any human code fix during the runs.
A round opened by a quarantined probe should not happen; if it does, it counts.

**Recorded per run:** build id, deploy SHA, canon hash, repair rounds, spend, `gate_waste` (rounds, measured USD,
model calls, quarantined gates), design-review score, duration.

**Gate conditions in force (from this PR):**
- quarantine only when the same finding points at a byte-identical DOM node in three consecutive rounds;
- critical gates (text_locale, copy_quality, accessibility) in quarantine withdraw `release_ready` and put a
  "preview only" banner on the version; quarantine is per build, so it expires on the next build;
- the fact canon is shown on the brief approval screen and approved with it; an empty canon on a business site is
  `CANON_INCOMPLETE` (warning, visible), never a silent pass; `AMBIGUOUS` numbers never block;
- gate waste is measured from gateway spend between the repeated reviews, not estimated;
- every static check that reads source must carry `@reads_source(reason)`; CI fails otherwise.
