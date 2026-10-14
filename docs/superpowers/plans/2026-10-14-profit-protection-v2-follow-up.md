# Profit Protection & Credit Economy v2 — follow-up plan

**Planning status: provisional.** PR #33 is the v1 billing-safety draft at
`fffa7dd60ab28855bb6236a2f5f0e72eb8373f7c`. This plan does not replace the
missing full v2 requirements document. The gap matrix in
`docs/evidence/profit-protection-v2-provisional-audit-2026-10-14.md` is derived
only from the task summary and must not be treated as the canonical 22-rule
specification.

## Order and dependency gates

### 0. Resolve the normative source before claiming complete scope

- Obtain the full titled v2 document and map each exact rule and acceptance
  criterion to the provisional audit.
- Keep current code and behavior unchanged while the canonical rule mapping is
  unavailable.
- No pricing changes, budget changes, live migration, real payment/provider
  call, merge, or production deployment is authorized by this plan.

### 1. Economy Core — first implementation phase

Reuse the existing build reservation, cost quote, attempt ledger, billing-event
journal, and project/checkpoint systems; do not add a parallel wallet or task
runtime.

1. Specify a versioned quote object with distinct sale/revenue basis, provider
   and infrastructure maximum costs, risk/retry reserve, policy version, and
   cost basis. A quote with unknown required cost must fail closed.
2. Bind quote approval, reservation, build admission, and provider correlation
   to durable, stable idempotency identities. Replayed requests with identical
   content return the original state; identity reuse with different scope or
   quote must fail closed.
3. Make reservation and cap checks one atomic transaction. Include all
   outstanding reservations and conservative UNKNOWN exposure in each
   applicable account/project/day/build ceiling.
4. Define reserve, execute, meter, settle, release, and refund transitions with
   explicit allowed states, reconciliation behavior, and no duplicate customer
   charge or customer credit grant.
5. Add company-funded accounting and a hard company cap for provider costs
   caused by platform/system failure. Customer credits remain zero for an
   Omni-originated defect; provider liability must still be recorded in full.
6. Enforce fixed Free allowances server-side for credits, projects, provider
   cost, storage, and abuse limits. Admin exceptions need scoped authorization
   and an auditable reason.
7. Preserve projects, verified checkpoints, remaining task state, and provider
   correlation across budget pause/restart. Resume requires fresh authorization
   and must not replay completed or uncertain paid calls.
8. Use local fake payment/provider adapters to exercise duplicate event
   delivery, failure before/after external acceptance, timeouts/UNKNOWN,
   idempotency conflict, settlement overrun, release/refund, and balance
   recovery. No fake result is reported as live integration evidence.
9. Validate with focused offline tests and disposable loopback PostgreSQL
   concurrency/restart tests. Any necessary schema change must be additive,
   reviewed, and never applied as part of this task.

**Exit gate:** every canonical Economy Core rule has a test/evidence link;
concurrent admission cannot exceed caps; replays cannot double-charge; unknown
liability remains visible; fake-provider recovery is deterministic; and the
app's project/checkpoint state can resume without re-execution of completed
work.

### 2. Estimation — only after reliable measurement

- Wait until the core ledger records verified provider usage, recognized
  revenue, failures, retries, and infrastructure allocations with versioned
  sources.
- Calibrate estimate ranges by capability/model/scope from measured outcomes;
  retain freshness and uncertainty and expose remaining-work ranges, not a
  completion guarantee.
- Record estimate versions and compare forecast with actuals. Do not let model
  self-reported confidence or price serve as evidence.

**Exit gate:** measured sample sufficiency and calibration criteria are set by
the canonical v2 spec; backtests show error bounds and estimates fail closed
when evidence is insufficient.

### 3. Monetization & Compliance — only after billing verification

- Keep checkout and wallet activation disabled until fake-processor regressions
  pass and the actual processor's test environment verifies signed events,
  duplicate/reordered delivery, failure recovery, refunds, invoice periods,
  top-ups, and balance reconciliation.
- Then implement subscriptions, top-ups, wallet lots, price versions, storage
  limits, customer invoices/credits, and compliance reports as authorized by
  the canonical rules.
- Report measured, conservative, reconciled, and UNKNOWN values separately.
  Never describe the 60% authorization floor as realized profit without
  reconciled revenue and costs.

**Exit gate:** reconciliation across processor events, internal funding lots,
reservations, measured costs, refunds, and reports passes in the test
environment; any live verification is separately approved and reported.

## Current execution result

The provisional audit and dependency plan were completed, and a narrow Economy
Core hardening now makes an identical `build_id` reservation replay return its
existing RESERVED state without a second allowance debit. Reuse with a
different account, project, or reserved amount, and reuse after settlement or
release, fails closed. This is not a caller-stable idempotency key or a full
quote fingerprint.

The focused local regression suite passed **118 tests** with **9
database-dependent skips**. No live payment/provider access, database
migration, budget change, merge, or deployment was performed. Further canonical
v2 implementation remains blocked until its full source is supplied.
