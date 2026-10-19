# Red-team verification boundaries — 2026-10-19

Baseline inspected: `1d2cd37d73e1a75a2daa8d9b5ba93845bbd2c3cc` (main).
Verification modules are unchanged from PR #70 head
`baec32ff391405e3cd3bfa6fec479ccbdc6651f3` (compared Git tree blob SHAs).
No production fixes are included. The two previously accepted findings
remain present at this baseline; this audit does not declare them fixed.

## Reproduce

```bash
python tools/redteam_verification_boundaries.py
```

Observed: `cases=26`, `violations=26`, exit 1. These are **26 injected cases**,
not 26 independent bugs, and not evidence that all paths occurred live.
Only sandbox transport/stage responses are simulated; the real executor
classes and VerificationGroup process them. No providers, R2, paid calls or
generated code are executed. The fixtures exercise verification boundaries,
not successful product generation or the complete release/worker lifecycle.

| Finding | Actual observation | Boundary/risk |
|---|---|---|
| R1 — existing: uncaught group-stage exception | TimeoutError escapes; following stage is not called | one stage aborts the group rather than reporting its failure |
| R2 — existing: failed report without failure entries | `passed=False, failures=()` produces group PASS | malformed negative result becomes success |
| R3 — browser/visual unavailable is successful at report level | Timeout and absent output/nonzero process return produce PASS | `unavailable`/`NOT_RUN` metadata does not block an upstream success report |
| R4 — unvalidated JSON shape | JSON `[]` escapes as AttributeError (browser/behaviour) or TypeError (visual); browser `{}` returns PASS | transport JSON validity is treated as sufficient without validating a result schema |
| R5 — ignored process failure | returncode=1 plus a browser/behaviour PASS-shaped payload returns PASS | text payload overrides failed execution |
| R6 — control/financial exception swallowed | inject BuildCancelled, AttemptLedgerUnavailable or ModelPolicyViolation from `_run`: preview/behaviour convert to repairable product failure; browser/visual return PASS | cancellation, budget denial and financial stop signals lose their meaning across broad `except Exception` |
| R7 — contradictory or nonboolean reports | `passed='false'` and `passed=True` with actual failures both produce group PASS | truthiness and inconsistent report fields bypass failure aggregation |

R6 is verified **at the injected executor boundary**. The audit has not
established that the live current worker raises these exceptions from
`_run`; current cancellation checks also exist on outer executor/model-call
boundaries. Do not report this as a proven live post-cancel paid call or a
proven financial loss. A later catch-all added around stage checks must not
swallow control/financial exceptions in trying to fix R1.

Browser/visual unavailability has historically been allowed deliberately.
That is a product-policy choice, but it cannot qualify as verified browser
evidence in the four-part Golden E2E contract. Full release impact still
depends on surrounding gates, quality and policy; these probes establish
executor/group behavior, not unconditional delivery of a live READY product.

## Requirements for the fix author (no fix implemented here)

- Schema-invalid/missing stage evidence is a failure, never an inferred PASS.
- Process failure and payload success cannot silently resolve to success.
- A recoverable probe failure should not suppress independent checks;
  cancellation, budget stops and mandatory financial persistence failures
  must retain their terminal semantics and prevent further paid work.
- Report types must be strict booleans with consistent pass/failure fields.
- Add distinguishing tests on old/new implementations for each corrected
  boundary; retain the original threshold short-circuit test.
- Test the worker's final state/billing behavior as well as executor output
  before claiming the control/financial paths are closed.

## Evidence gate status

`tools/verify_golden_evidence.py` implements four fail-closed sections.
`tests/test_golden_evidence_gate.py` covers missing manifest/receipt/nested
fields, malformed and duplicate JSON, unknown/nonfinite cost, missing and
tampered bytes, identity/coverage mismatches, manual steps, false booleans,
ledger incompleteness, and exceeded time/cost limits. Passing synthetic
fixtures validate the checker only. Missing live evidence returns all four
FAIL with `cost_status=UNKNOWN`, `actual_cost_usd=null`, exit 1.

The reusable workflow is prepared; no live collector or production pipeline
integration is claimed. See `GOLDEN_EVIDENCE_GATE.md` for the exact input
contract and remaining producer responsibility.
