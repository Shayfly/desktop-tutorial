# Profit Protection & Credit Economy v2 — provisional audit

**Status: BLOCKED as a canonical v2 audit.** The full, titled v2 requirements
document was not present in this checkout or PR #33 history, and an exact-text
GitHub code search did not locate it. The only normative evidence currently
available is the user's summarized scope, the v1 safety audit, the v1 staged
plan, the operating contract, and the implementation/tests at the reviewed
revision. This document is therefore a provisional audit of 22 scope areas
derived from that summary; these rows are **not** asserted to be the v2
document's canonical 22 rules or numbering. The complete rule-by-rule audit
cannot be signed off until the full v2 source is available.

## Review boundary and evidence

- Reviewed revision: `fffa7dd60ab28855bb6236a2f5f0e72eb8373f7c`, PR #33 head.
- PR #33 is an open draft for Profit Protection v1 safety, based on
  `shayfly-148ai-engineering-recovery`.
- Relevant evidence: `docs/evidence/profit-protection-v1-safety-2026-10-14.md`,
  `docs/superpowers/plans/2026-10-14-profit-protection-v1.md`,
  `omni_prod/build_cost_plan.py`, `omni_prod/provider_pricing.py`,
  `omni_prod/subscription_store.py`, `omni_prod/pricing.py`,
  `omni_prod/investor_app.py`, `omni_prod/worker_tasks.py`, migrations
  `012`, `013`, and `039`, and the economy, settlement, billing, and
  opt-in PostgreSQL tests.
- Focused local command:

  ```text
  python -m pytest -q tests/test_profit_protection.py tests/test_m5_build_economics.py tests/test_actual_cost_settlement.py tests/test_m495_subscription_settlement.py tests/test_public_pricing_economics.py tests/test_build_state_machine.py tests/test_v28_148ai_launch.py tests/integration/test_profit_billing_events_pg.py tests/test_deployment_verification.py::ManifestTests tests/test_agent_os.py::AuditTests tests/test_agent_os.py::TruthMatrixTests tests/test_intelligence_plane.py::ProviderMatrixTests tests/test_conversation_os.py::DepartmentTests tests/test_m4_acceptance.py::AcceptanceV tests/test_migration_rollback_tolerance.py::VerifyAppliedTests
  ```

  The earlier reservation-replay baseline passed **118 passed, 9 skipped**.
  The skips include database tests which require an explicitly configured
  disposable loopback PostgreSQL database. On the current PR #34 worktree, the
  focused request-idempotency/economics command passed **62 passed, 3 skipped,
  3 subtests passed**; the three skipped tests include real-Postgres
  reservation/idempotency concurrency and project-scope cases. Migration 040
  was not applied. This is local unit-test evidence, not live database,
  payment, provider, or production verification.
- On PR #34 head `7779cab`, disposable PostgreSQL CI ran the new integration
  cases but reported 175 passed, 2 failed, and 56 subtests because legacy
  rollback tests accidentally included migration 040 in a fixture intended
  to represent schema version 039. Neon bootstrap CI also exposed a stale
  generated file missing migrations 039-040 and Windows newline handling in
  its generator/verifier. Commit `1a1ce207` fixed both: push and PR PostgreSQL
  runs [38557768232](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557768232)
  and [38557773477](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557773477)
  passed without skips, and Neon bootstrap runs
  [38557768217](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557768217)
  and [38557773575](https://github.com/Shayfly/desktop-tutorial/actions/runs/38557773575)
  passed. V24/V11 runs on `1a1ce207` failed because the generated Agent OS registry
  still labeled `migration_test` REAL_SERVER_VERIFIED after the verifier
  changed. `audit --write` regenerated it and the focused registry/truth
  regression passed 4 tests locally. V24/V11 runs on `d3e9d9c` then found a
  stale `DEPARTMENT_MATRIX.json` (generated IMPLEMENTED count 9 vs committed
  8); `departments --write` regenerated it and combined local registry/
  department/truth regressions passed 5 tests. PostgreSQL and Neon bootstrap CI
  passed on `d3e9d9c`; full CI after the matrix refresh is pending.
- Migration 040 ran only in disposable PostgreSQL CI. No Preview/staging/
  Production migration, payment processor, paid provider, or production
  service was contacted.

## Status meanings

- **VERIFIED** — the stated behavior passed the listed local test evidence.
  This does not imply live verification.
- **IMPLEMENTED** — code exists, but the specific acceptance behavior lacks
  sufficient test or live evidence.
- **PARTIAL** — only part of the requested behavior is implemented or verified.
- **MISSING** — no matching end-to-end implementation was found.
- **BLOCKED** — the required canonical rule, external service, or evidence is
  unavailable, so the behavior cannot responsibly be specified or verified.

## Provisional 22-area matrix

| # | Area inferred from the task summary (not canonical v2 numbering) | Status | Evidence and remaining gap |
|---:|---|---|---|
| 1 | Minimum 60% operational contribution-margin target | PARTIAL | The pre-execution guard enforces a minimum 60% conservative variable-cost margin for paid builds. Revenue is allocated from monthly plan price by fixed build credits; this is not measured operational contribution margin, and no realized 60% outcome is verified. |
| 2 | Quote → Reserve → Execute → Meter → Settle → Release/Refund lifecycle | PARTIAL | Build quote, durable reservation, execution, metering, settlement, and release paths exist. Reservation replay for an identical `build_id` avoids a second allowance debit. PR #34 adds a caller-supplied, account/project-scoped build key and durable request/quote SHA-256 fingerprints in additive migration 040; quote fingerprints use persisted `quote-fingerprint/2` and include `category=build`. Exact replay returns the original build; changed request, quote, or persisted version conflicts before approval/reservation. Migration 040 applied successfully in the disposable PostgreSQL CI service; that head's test phase failed two unrelated rollback-fixture assertions, so a clean rerun is pending. No shared/live migration was applied. Refunds and funding-lot allocation remain missing. |
| 3 | Atomic reservations | IMPLEMENTED | Production reservation locks the subscription row and writes within the build transaction. PostgreSQL concurrency tests exist but were skipped; live atomicity is unverified. |
| 4 | Budget ceilings across account, project, day, build, and outstanding exposure | PARTIAL | Plan credit/provider-spend checks and a separate intake-budget service exist. The M5 build path does not demonstrate one end-to-end set of all-scope caps including outstanding UNKNOWN exposure. |
| 5 | Prevention of duplicate billing and replayed payment events | PARTIAL | Reviewer-service tests cover replay/order; Postgres journal and watermarks are prepared in additive migration 039. Database concurrency/restart tests were skipped and no processor test environment was used. |
| 6 | Explicit risk reserves | PARTIAL | A retry reserve can be quoted and included in the reservation. It defaults to zero, is operator-configured, and is not calibrated from observed risk or a versioned policy. |
| 7 | Estimate calibration against observed costs | MISSING | No evidence-based estimate calibration loop was found. The task itself sequences estimation after reliable measurement. |
| 8 | Versioned pricing and economics policies | PARTIAL | Provider quotes record catalog versions; runtime model policy and margin threshold are not a complete immutable, effective-dated build policy record. |
| 9 | Provider-failure costs charged to a company budget | MISSING | Omni-originated defects are credit-free in the reviewer authorization path, but a separate durable company-liability budget and full failed-provider-cost reconciliation were not found. Internal QA funding is not equivalent to that policy. |
| 10 | Retry budgets and circuit breakers | PARTIAL | Retry reserve and provider routing/resilience mechanisms exist, but a single budgeted retry policy is not shown to govern all provider failures, UNKNOWN outcomes, and circuit-breaker transitions. |
| 11 | Durable project state | IMPLEMENTED | Existing Postgres project/workspace persistence and durable build repositories are present. This audit did not connect to or independently verify the live database. |
| 12 | Checkpoint persistence and integrity | PARTIAL | Build rounds can produce snapshot artifacts/checksums; a durable checkpoint index tied to the remaining task graph is not established by the reviewed economy path. |
| 13 | Budget pause and safe resume | MISSING | No complete paused-build resume flow was found that requires fresh approval/reservation and avoids replay of completed or UNKNOWN external calls. |
| 14 | Smart Completion Estimate | MISSING | No remaining-work completion-credit range calibrated from measured data was found. |
| 15 | Subscription entitlement and renewal | PARTIAL | Plan catalog, event-gated entitlement changes, and calendar-month counters exist. Paid invoice-period grant and renewal behavior is not implemented or verified. |
| 16 | Top-ups | MISSING | No verified, durable top-up grant/refund lifecycle was found. |
| 17 | Wallet/funding lots and allocations | MISSING | The existing subscription counters/reservations are not a source-of-funds wallet with period-aware lots and refunds. |
| 18 | Price-version history | PARTIAL | Provider pricing catalog version is attached to quotes; public plan prices are environment-configurable and not represented as a complete effective-dated customer transaction history. |
| 19 | Storage limits and lifecycle | PARTIAL | Plan project-count limits exist. Per-plan storage/egress quotas and their durable enforcement were not verified in the build path. |
| 20 | Hard Free and admin limits | PARTIAL | Free has a fixed 150-credit monthly allowance, `ZERO` cost-class access, and two-project limit in the plan catalog. Calendar rollover is not an invoice grant; storage, abuse ceilings, and admin override auditing are not established by those fields alone. |
| 21 | Profitability reporting | PARTIAL | Attempt/cost evidence and conservative contribution calculations exist. Net recognized revenue, fees, refunds, allocations, provider reconciliation, and fully reconciled margin reports remain incomplete. |
| 22 | Compliance and audit reporting | BLOCKED | Some billing journals and operational evidence exist, but the v2 compliance obligations and their acceptance criteria cannot be mapped without the canonical full specification. No compliance attestation is claimed. |

## Required corrections from the task summary

1. **Free must be hard-capped.** The local catalog caps Free at 150 credits per
   calendar month, `ZERO` cost class, and two projects. This does not prove
   company-wide Free spend, storage, abuse, or admin-override limits. Whether a
   calendar reset counts as an authorized grant must be resolved by the v2
   policy.
2. **Provider failures belong to company economics.** The inspected production
   reservation path has no separate company-funded failure ledger/cap. Credit
   waivers alone do not account for provider liability.
3. **The platform owns estimate error.** UNKNOWN actual cost is retained as
   unknown and settlement conservatively covers the reservation, but the
   contract for overruns, insufficient reserve, and company liability is not
   fully implemented.
4. **Sale price is distinct from cost plus reserve.** The quote type keeps
   `revenue_usd` and authorized cost separate; however, the current revenue
   basis is an allocation from monthly list price and fixed build credits, not
   a verified sale transaction/net-recognized-revenue record. Risk reserve
   also needs its own versioned basis.
5. **Idempotency identity must be stable.** Billing event IDs and capability
   execution keys are durable/stable in their respective paths. PR #34 adds a
   caller-provided build key scoped by account and internal project, persists
   separate full request and quote SHA-256 fingerprints, returns the original
   build on exact replay, and rejects key reuse with changed content before
   approval or reservation. The UI retains the key across ambiguous network
   failures; the internal postdeploy client supplies a UUID. Legacy clients
   without a key retain contract-level deduplication/retry behavior. Migration 040 is
   additive and has run only in a disposable PostgreSQL CI database. Local unit
   tests pass; the CI run containing real-Postgres concurrency ended red on two
   rollback-fixture assertions and needs a clean rerun. Provider-level request correlation and full end-to-end
   crash recovery are still not established.

## Safe boundary

The code and tests do not justify marking the v2 economy complete. Reservation
replay and caller-key persistence are narrowly scoped Economy Core corrections,
not completion of the lifecycle. Migration 040 has not been applied outside the
disposable PostgreSQL CI service. Further
Core work should use fake payment and provider adapters and must not run live
migrations or use real payment/provider services. Estimation calibration must
wait for reliable measured-cost data. Monetization activation must wait for
verified billing behavior. The complete canonical v2 matrix remains blocked
by the absent requirements source.
