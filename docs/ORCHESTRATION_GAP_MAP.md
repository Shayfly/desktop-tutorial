# Orchestration gap map — current code vs `ORCHESTRATION_ARCHITECTURE_HE.md`

Date: 2026-10-07. Baseline commit `4e6a44c`. Status: PASS / PARTIAL / MISSING.

## The core distinction

The spec asks for a **Product Orchestrator** (request → Task/Capability DAG →
per-task selection by *expected total cost* → per-task verification →
repair/retry/escalate/fallback → composition → learned performance), of which
the model router is only the *Selector* component.

What runs today is a **fixed four-step pipeline** inside
`AutonomousProductEngine.build()` (`omni_prod/autonomous_core.py`):

```
Architect.create_spec → Generator.generate → Executor.execute (sandbox tests)
   → while failed and rounds < max_repair_rounds: Repair.repair → Executor.execute
```

It is effectively a hard-coded 4-node DAG with one repair loop. Every LLM call in
it goes through one `RoutedModelGateway`, which (since 2026-10-06) picks the
cheapest catalog model above one global quality floor **per call** — i.e. it
optimizes *initial_cost*, which §3.3 of the spec explicitly forbids as the sole
criterion.

## Components (spec §10.1)

| Component | Status | Today |
|---|---|---|
| Task Planner (request → DAG) | PARTIAL | Build Contract + capability plan (`build_contract`, `capabilities`) decompose *capabilities* (e.g. image). The software part is one opaque spec, not tasks. |
| DAG Executor (deps, parallel, local retry) | MISSING | Fixed sequence in `AutonomousProductEngine`; failure re-runs repair over the whole repo. |
| Model/Provider Selector | PARTIAL | LLM: `RoutedModelGateway` + priced catalog (per call, no task type). Capabilities: `CapabilityProviderRouter` (hard policy, health, quote). |
| Cost Estimator (expected **total** cost incl. retry/repair/escalation) | MISSING | Only per-call max cost and a whole-build budget. |
| Budget Manager / Reservation Ledger | PARTIAL | One durable reservation per build (`subscriptions.reserve/settle/release`); per-call authorization against it. No per-operation reservations or protected future budget. |
| Verification Engine | PARTIAL | Deterministic: sandbox tests per acceptance criterion, quality gate, hostile security scan, rights gate, capability verification. No structured `VerificationResult` (PASS/REPAIRABLE/RETRYABLE/ESCALATABLE/FATAL). |
| Repair Manager | PARTIAL | `RepairAgent` loop bounded by `OMNI_MAX_REPAIR_ROUNDS`; no expected-value check. |
| Retry Manager | PARTIAL | `retry.RetryPolicy` exists; provider errors fall through to next model. Not driven by verification class. |
| Escalation Manager | MISSING | No "repair failed → stronger model" step. |
| Fallback | PARTIAL | Next-cheapest provider on transport/provider error. |
| Product Composer | PARTIAL | Repository + capability artifacts assembled into one version; no general composer. |
| Usage & Feedback Store | PARTIAL | Route events (provider, model, reason, max cost, ok) + provider-reported usage persisted in build evidence. No per-task outcome table. |
| KPI/SLO pipeline, Error Budget, Alerting | MISSING (primitives exist) | `metrics.py`, `slo.py` primitives; nothing computes product KPIs from builds. |
| Policy Engine | PARTIAL | Env-configured policies (budget, zero-cost, quality floor). No versioned policy records. |

## Phase 1 (spec §10.4) mapped onto Golden E2E #1

Golden E2E stays first. These are the Phase-1 items that fit *inside* the
existing 4-node pipeline without a rewrite, in order:

1. **Request → Task separation**: each agent call carries a `task` type
   (`architecture`, `codegen`, `repair`, `modification`, `classification`);
   `RouteEvent` records it. (Needs: `task` kwarg on gateway calls.)
2. **Per-task selection**: catalog entries get per-task quality and a
   `tasks` allow-list; minimum quality per task (e.g. architecture/repair
   higher than classification).
3. **Cost and outcome per task**: actual cost = provider usage × catalog
   price, stored next to the authorized estimate; per-task outcome row
   (task, model, cost, latency, verification result, repair count).
4. **Basic verification classes**: map existing sandbox/quality/security
   outcomes to PASS / REPAIRABLE_FAIL / FATAL_FAIL.
5. **Bounded escalation**: after repair round N fails, raise the quality tier
   for the next repair (budget-gated).
6. **Basic KPI read-out**: success rate, cost per approved build, repair rate
   from the outcome rows.

Phases 2–3 (true DAG executor with parallel nodes, expected-total-cost
optimizer, per-operation reservations with protected future budget, learned
success probabilities, error budgets and alerting) build on these records.
None of them requires replacing `RoutedModelGateway`, the build pipeline or the
reservation model; they wrap and extend them.
