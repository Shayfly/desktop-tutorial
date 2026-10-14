# 148AI Cost Model — M4.95 Truth Contract

M4.95 treats cost as release-critical evidence, not a cosmetic estimate.

## Profit Protection v1 — safety stage (2026-10-14)

Customer-funded durable build admission now enforces a conservative variable-cost
margin floor of at least 60%. `OMNI_MIN_BUILD_VARIABLE_MARGIN` may tighten the
floor but cannot lower it. Internal QA remains separately budgeted. This is an
authorization guard, **not verified realized gross margin**: the legacy revenue
basis still allocates the configured monthly plan price over included credits.
Net recognized revenue, annual discounts, payment fees, infrastructure/support
allocations and invoice reconciliation remain required before a gross-margin
claim. No flat $3 project price was added, and no provider price was changed.

A failed/recovered build with a prior UNKNOWN call now retains conservative
coverage instead of releasing its reservation. A plan entitlement change no
longer resets credit usage or provider spend. Paid Checkout evidence is required
to grant a paid entitlement; lifecycle metadata is not payment evidence.

The subsequent wallet stage must replace calendar-cycle counters and fixed
build credits with period-aware funding lots and versioned quotes. Until then,
there is no claim of complete credit economy, accurate completion-credit
estimates, or checkpoint resume. See
`docs/evidence/profit-protection-v1-safety-2026-10-14.md` for the staged audit.

## Required fields

Every paid provider action has a versioned price source and records `estimated_cost_usd`, `maximum_cost_usd`, a durable reservation ceiling, and `actual_cost_usd` when the provider exposes measured billing/usage. `pricing_version` and effective dates make historical builds auditable.

**UNKNOWN is never zero.** A provider price with status `UNKNOWN_NOT_APPROVED` cannot be used for an approved paid execution. `CUSTOMER_PAYS_DIRECTLY` is tracked separately and must never be interpreted as a free platform service.

**An estimate is never actual.** `actual_cost_usd=NULL` remains unknown; the ledger must not replace it with `estimated_cost_usd` or the reserved maximum. Contribution analysis may use a conservative cost basis, but it must label that basis `CONSERVATIVE`, not `ACTUAL`.

## Authorization lifecycle

`local versioned price catalog -> conservative maximum quote -> durable reserve -> optional live quote validation -> provider execution -> measured usage -> actual settlement/release`

A paid external provider is not called before a durable authorization ceiling exists. A live quote that exceeds the reserved maximum blocks execution or requires an explicit reservation expansion.

## Cost dimensions still required before public production

Provider/model tokens or credits, image/3D/video/audio units, retries and paid failures, sandbox CPU/GPU, build time, object storage, egress, database/queue/monitoring, payment fees, non-recoverable tax, refunds/chargebacks where applicable, and support allocation. M4.95 establishes the accounting contracts; production telemetry and commercial provider price catalogs remain `NOT_CONFIGURED` until live credentials/contracts and measured usage exist.
