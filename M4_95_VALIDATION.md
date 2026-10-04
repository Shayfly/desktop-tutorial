# M4.95 Validation Evidence

## Baseline

- Canonical M4.9 commit: `aa1e983e2283358f47896c3c8ad1527198f6db3e`
- Execution branch: `milestone/m4.95-capability-foundation-v2`
- Baseline run date: 2026-10-04 (UTC timestamp captured in `.superpowers/sdd/m4_95_v2/baseline_meta.txt`)
- Python: `3.13.5`

### Full non-live regression

Command:

```bash
python -m unittest discover -s tests -v
```

Fresh result before M4.95 production-code changes:

```text
Ran 518 tests in 3.975s
OK (skipped=47)
```

The skipped tests are environment-gated live proofs and are not rewritten as passes.

### M4.9 clean-room and lifecycle probes

Commands:

```bash
python -m unittest tests.test_m49_clean_room -v
python -m unittest tests.test_m49_lifecycle -v
```

Fresh result:

- `test_clean_room_real_pipeline_reaches_genuine_ready_for_review`: `SKIPPED` — `psycopg` not importable in this execution environment.
- `test_A_through_E_accept_verify_rollback_verify`: `SKIPPED` — `psycopg` not importable in this execution environment.

This is recorded as **NOT CONFIGURED in this execution environment**, not as a failure and not as live-production evidence.

## M4.95 completion rule

A task is complete only after its required focused tests pass, the project regression suite is re-run when the task changes shared behavior, and the commit/ruling is recorded in the execution ledger. External/live capabilities remain `NOT_CONFIGURED` or `BLOCKED` until exercised against the named live dependency.
