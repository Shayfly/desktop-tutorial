# M5 Task 3 — Project Lifecycle Evidence

Date: 2026-10-04
Implementation commit: `6df01b595d7b273126d2257f6257e04b0778dfbc`

## Implemented

- Additive migration `019_project_lifecycle.sql` adds archive/tombstone/retention metadata without hard-deleting creator project rows.
- Durable project lifecycle service supports rename, search, archive, unarchive, soft delete, owner-scoped state lookup and default active-only listing.
- Deleted projects remain as tombstones; project ID reuse is rejected by the retained primary-key row.
- Archive/delete state is enforced before project access so archived/deleted projects cannot enter build/project mutation paths through `require_project`.
- Every lifecycle mutation is owner-scoped. PostgreSQL updates include owner predicates and non-deleted guards for rename/archive transitions.
- V28 routes added for search, rename, archive, unarchive, delete and state.

## Local verification

- Targeted lifecycle + V28 regression: 28 tests, 0 failures.
- Fresh whole-suite regression before commit: 690 tests, 0 failures, 0 errors, 51 skips.
- `python -m omni_prod.truth_lock --check`: PASS.
- `python -m omni_prod.requirement_ledger --check`: PASS before ledger promotion.

## External gate

`tests/integration/test_v28_creator_persistence.py::V28CreatorPersistenceLiveTests::test_project_lifecycle_survives_service_instance_change_without_hard_delete` requires migrated live PostgreSQL plus `OMNI_RUN_V28_CREATOR_POSTGRES=1`.

## Truth boundary

Task 3 is verified locally. Live PostgreSQL persistence proof remains gated and is not inferred from local memory repository tests.
