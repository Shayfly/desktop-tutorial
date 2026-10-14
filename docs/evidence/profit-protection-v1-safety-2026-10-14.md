# Profit Protection & Credit Economy v1 — safety stage

Base: `shayfly-148ai-engineering-recovery` at `b5f0625f694d705eb122cee174928de6d3a2ee8d`.
This is the first safety slice, not a completed wallet, billing rollout, or Production release.

## Existing mechanisms and remaining gaps

| Area | Reused source of truth | Remaining v1 work |
|---|---|---|
| Agent OS | `agent_os/runtime.py`, recorder, durable run/task budgets and dependencies | Bind task resume to newly approved funding without replaying completed actions |
| Master registries | existing audit, departments and intelligence generators | New live evidence only after actual verification; modified evidence is downgraded, never promoted manually |
| Billing | `pricing.py`, `PostgresSubscriptionService`, `credit_reservations` | Funding lots for subscriptions/top-ups, invoice-period grants, refunds/reversals and period-safe allocations |
| Cost quote / meter / settle | `build_cost_plan`, provider pricing/catalog, routed gateway, attempt ledger | Dynamic customer credit quotes, net revenue basis, all-scope caps and complete recognized costs |
| Build state | queued/running/ready/failed/cancelled, leases, heartbeat/cancel, crash recovery | Budget pause and explicit durable resume state |
| Checkpoints | round ZIP snapshots, checksums and workspace versions | Persist checkpoint index/spec/task graph and continue from it instead of calling generation again |
| Frontend | approved plan, allowance, fixed 60-credit build quote, status/cancel | Remaining-credit ranges, uncertainty, top-up choices, scope adjustment and explicit resume |
| Reports | `economics_report`, metered/unknown/exposure and repair/failure accounting | Net recognized revenue, allocations, invoices and reconciled gross margin |

No parallel wallet or task runtime was introduced. No flat $3 price was found
in the audited build admission path, and none was added. Fixed build credits
are a documented remaining issue, not a per-project cost estimate.

## Root causes reproduced and repaired

1. A signed unpaid Checkout event granted a paid plan. Granting now requires
   subscription mode plus paid payment status; delayed payment success uses the
   same validation. Signature verification remains mandatory at the API boundary.
2. Subscription updates called `assign_plan`, resetting credit and provider-spend
   counters. Assignment now preserves counters; non-revoking lifecycle metadata
   is ignored and does not advance payment ordering.
3. A recovered build with earlier UNKNOWN calls and no newly metered spend was
   treated as no paid activity and released. Prior calls/UNKNOWN exposure now
   retain conservative settlement coverage.
4. The default conservative variable-margin floor was 20%, and could be lowered
   by configuration. The customer-funded floor is now at least 60%; invalid
   nonfinite or out-of-range policy is refused.
5. Process-local webhook deduplication did not survive restart and ordering was
   undefined. The subscription service now owns event identity, account ordering,
   subscription source identity and per-source revocation tombstones. Equal-second
   ambiguity resolves conservatively in favor of revocation.

Regression cases include cancellation delivered before a delayed payment,
cancellation of a superseded subscription, an ignored different-source
cancellation followed by its old payment, metadata delivered ahead of an upgrade,
duplicate/conflicting IDs, processor recreation and unsupported unpaid statuses.

## Database change and rollout boundary

Additive migration `039_billing_event_idempotency.sql` creates only the billing
event journal and entitlement watermark. No raw customer/payment payload, card
data, or credentials are stored. Effective schema requirements are updated to39.
It has **not** been run against a live database. The PostgreSQL handler deliberately
has no fallback to an in-process payment journal when the schema is missing.

Before any rollout, obtain explicit environment-specific migration/deployment
approval, use a disposable PostgreSQL instance for integration/concurrency tests,
and verify payment-event mapping in a Stripe test environment. Renewal invoices,
plan proration, disputes, refunds, top-up grants and billing-period renewal are
not activated by this stage. `past_due` retains the previous entitlement pending
an explicit dunning policy; incomplete/trialing metadata never grants one.

Rollback is a code/image rollback; preserve the new journal and watermark tables
for audit and replay protection. Do not delete payment evidence as a rollback.
Do not use an older processor against live billing merely because code can boot.

## Verification and limits

All tests run locally with provider credentials removed, zero-cost mode enabled,
and external fallback disabled. No checkout, paid model/provider call, live DB
migration, merge or Production deployment was performed.

The four original audit tests were observed failing before their fixes. Additional
ordering/source and connection-guard regressions also failed before repair.
An independent read-only review reproduced two ordering defects; both received
regression tests and fixes. The reviewer also found an unsafe opt-in database URL
guard; the test helper now validates effective libpq parameters and pins a
loopback address. Five malicious destination override cases are tested without
opening a connection.

Run the focused suite with no service credentials:

```text
python -m pytest -q tests/test_profit_protection.py tests/test_m5_build_economics.py tests/test_actual_cost_settlement.py tests/test_m495_subscription_settlement.py tests/test_public_pricing_economics.py tests/test_build_state_machine.py tests/test_v28_148ai_launch.py tests/integration/test_profit_billing_events_pg.py tests/test_deployment_verification.py::ManifestTests tests/test_agent_os.py::AuditTests tests/test_agent_os.py::TruthMatrixTests tests/test_intelligence_plane.py::ProviderMatrixTests tests/test_conversation_os.py::DepartmentTests
```

Four new PostgreSQL tests are opt-in and were **not executed**: no disposable local
PostgreSQL is configured. They require `OMNI_PROFIT_TEST_DATABASE_URL` pointing
at a loopback database named `profit_test...`; each test uses a private schema.
These skipped tests are not evidence of real database concurrency safety.

The local source snapshot omits binary branding assets, and Windows lacks the
Linux shell/container environment expected by some existing tests. Broad pytest
was attempted and is not green; temporary-directory permissions, stale generated
artifacts, schema-version fixtures and missing assets were identified. Current
focused counts and full-suite evidence are recorded in STATUS rather than
claiming a clean CI run. This branch must remain draft until relevant checks pass
on the intended environment. No new live or Production verification is claimed.

## Acceptance for later stages

- A paid funding lot grants once per verified invoice/session; Free cannot renew
  without an authorized grant. Old-cycle refunds cannot increase a new cycle.
- Quote/reserve/meter/settle/refund remain one idempotent lifecycle; outstanding
  and UNKNOWN exposure counts toward account/project/day/build caps.
- Actual provider liability is recorded in full even when it exceeds a cap;
  customer charges cannot silently exceed approved credits.
- Completion estimates use remaining work and versioned rates, expose ranges,
  freshness and uncertainty, and never promise completion for a fixed amount.
- A budget pause preserves a checksum-verified checkpoint. Resume requires fresh
  approval/reservation and does not replay completed or uncertain provider calls.
- Gross-margin reports distinguish target, estimated, measured, reconciled and
  UNKNOWN values. A passing authorization guard is not a realized-profit claim.
