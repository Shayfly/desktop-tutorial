# M5 Task 5 — Durable Build Request / Build Contract Binding Evidence

Date: 2026-10-04
Implementation commit: `0ab87acb4e1d60da98a9cf093e0ccb0311b973a0`
Status: `VERIFIED_LOCAL`

## Implemented

- Every new durable `build_requests` row can reference one immutable `m5_build_contracts` revision through `build_contract_id` with `ON DELETE RESTRICT`.
- PostgreSQL migration guard rejects a bound request whose `public_project_id` does not match the contract project.
- The canonical plural `/api/v28/projects/{project_id}/builds` path now either loads an explicitly requested contract revision or compiles/persists the next revision before any budget reservation.
- `NEEDS_CLARIFICATION` contracts block reservation/enqueue and return the durable contract ID plus material questions.
- Cross-project contract IDs fail closed through project-scoped repository lookup and a DB-level project-consistency trigger.
- The mutable request prompt cannot replace an explicitly selected contract. The durable request snapshots the contract prompt.
- `PostgresBuildRepository.get_request()` loads the exact contract JSON/fingerprint through a left join and labels pre-Task-5 rows `LEGACY_UNBOUND` rather than inventing a binding.
- Worker execution reconstructs the immutable `BuildContract`, verifies READY state and fingerprint/project identity, uses the contract prompt and capability plan, and records contract ID/fingerprint/binding in terminal build evidence.
- Existing legacy worker/test paths remain readable when no contract is bound.

## TDD evidence

RED before implementation:
- `python -m unittest tests.test_m5_build_contract_binding -v`
- 8 tests failed/erroring because `build_contract_id`, contract resolution, DB binding guard and immutable worker use did not exist; the worker demonstrably executed the mutated request prompt.

GREEN after implementation:
- Task-5 targeted binding suite: `8 tests`, `OK`.
- Related Product Architect + economics targeted suite: `31 tests`, `OK`.
- Fresh post-implementation-commit full regression: `706 tests`, `OK`, `51 skipped`, `0 failures`, `0 errors`.

## Truth boundary

Local tests prove immutable binding behavior, legacy-read semantics, project-scoped lookup, worker consumption of the bound contract and migration contract text. A migrated live PostgreSQL runtime is still required to externally prove the FK/trigger behavior and concurrent revision/binding persistence under real transactions. No live PostgreSQL proof is inferred from local tests.
