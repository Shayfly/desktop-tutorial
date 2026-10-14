# Profit Protection & Credit Economy v1 — staged implementation

Base: `shayfly-148ai-engineering-recovery` at `b5f0625f694d705eb122cee174928de6d3a2ee8d`.
Goal: extend the existing reservation, pricing, task, and build systems; never add a parallel billing authority.

## Boundaries

No live checkout, provider calls, live migration, merge, or Production deployment. Preserve existing public plan prices. A target margin is an authorization policy, not a claim of realized profit. Estimates are explicitly uncertain, never completion guarantees. Do not price all project families at $3.

## Stages and acceptance

- [x] Local safety regression: unpaid checkout grants no entitlement; subscription update preserves usage; restart/reordered events cannot restore allowance; prior UNKNOWN attempts remain covered; the margin floor cannot be lowered below 60% by configuration. PostgreSQL/live verification remains explicitly pending.
- [ ] Extend existing subscription reservations with durable funding lots, payment-event identity, period-aware allocations, settlement and refund. Invoice/checkout evidence must authorize grants once; raw client values cannot authorize credits.
- [ ] Replace fixed build credits with versioned scope/capability quotes; check account/project/day/build caps including outstanding UNKNOWN exposure before execution.
- [ ] Extend existing round snapshots and build state with budget pause and durable resume from a verified artifact, remaining task graph, and newly approved reservation.
- [ ] Add remaining-completion credit ranges and honest uncertainty to the existing frontend; extend existing economics reports to distinguish measured, reconciled, conservative, and unknown values.
- [ ] Run appropriate offline regressions and isolated database tests where available; record unsupported live checks explicitly. Open a draft PR with scope and evidence; no merge.

Execute safety first. Each stage must have failing behavior reproduced before changing product code. Reuse `PostgresSubscriptionService`, `credit_reservations`, `build_cost_plan`, `AttemptLedger`, `AgentRuntime`, and round snapshots. Keep exact status and evidence; a stage is not complete solely because its interface exists.
