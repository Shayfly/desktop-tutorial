# M5 Task 4 — Versioned Build Contract + Product Architect Evidence

Date: 2026-10-04
Implementation commit: `f8f95ce5194e13cb43088451bad00a5db0fb6533`
Status: `VERIFIED_LOCAL`

## Implemented

- Immutable `BuildContract` schema with explicit contract version, status, unresolved material questions, deterministic capability-plan fingerprint, acceptance, infrastructure, security, cost-envelope references, registry versions, required skills/agents and canonical contract fingerprint.
- `ProductArchitect.compile(...)` implements Ask Less — Infer More — Verify Everything for the M5 Web/SaaS slice.
- Deterministic `OmniUniversalBrain` / `CapabilityPlanner` output is the non-removable capability floor.
- Optional model-backed `ArchitectAgent` may enrich the `ProductSpec` but cannot remove deterministic platform requirements or capability closure.
- Materially vague intent produces `NEEDS_CLARIFICATION` instead of guessed readiness.
- First M5 infrastructure contract references database, durable auth/session, object storage, scheduled HTTP work and outbound delivery; Task 6 owns provisioning.
- Cost envelope binds to conservative-maximum quote and durable reservation policy; Task 10 owns the economics execution.
- Master Skills/Agents Registry versions and required skill/agent keys are embedded in the contract.
- Append-only memory and PostgreSQL Build Contract repositories support immutable monotonic revisions and project scoping.
- Migration `020_m5_build_contracts.sql` adds `(project_id, contract_version)` uniqueness and a DB trigger rejecting UPDATE/DELETE.

## TDD evidence

RED before implementation:
- `python -m unittest tests.test_m5_product_architect -v`
- Failed with `ModuleNotFoundError: No module named 'omni_prod.build_contract'`.

GREEN after implementation:
- Targeted Task 4: `8 tests`, `OK`.
- Related capability/registry regression: `49 tests`, `OK`.
- Full suite after implementation commit candidate: `698 tests`, `OK`, `51 skipped`, `0 failures`, `0 errors`.

## Truth boundary

Local tests prove schema, deterministic floor, contract serialization/fingerprints, clarification behavior, immutable in-memory revision semantics and migration/repository contracts. A migrated live PostgreSQL runtime is still required to externally prove the database trigger and concurrent durable revision persistence. No such external proof is inferred from local tests.
