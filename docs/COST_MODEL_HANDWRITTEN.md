<!-- Hand-written sections of COST_MODEL.md. `python -m omni_prod.truth_lock --write` copies this file into
     COST_MODEL.md after the introduction; edit HERE, never in COST_MODEL.md. -->

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
