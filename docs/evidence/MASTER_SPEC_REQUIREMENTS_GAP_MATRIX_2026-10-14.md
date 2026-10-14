# MASTER SPEC v1 requirements-to-code gap matrix

**Purpose:** one working traceability matrix for the user-supplied MASTER SPEC
v1, Appendix A, the current repository, Issue #6, and draft PRs #31, #33, #34.
This is an implementation audit, not a claim of commercial or live acceptance.

## Evidence boundary

- MASTER SPEC v1 and Appendix A were supplied as attachments and are treated as
  the target architecture for this audit.
- The supplied Product Specification part 3 ends at the beginning of section 2.
  Its section 7 list of nine unverified capabilities and section 10 conflict
  rules were not present in the received text or the repository. Those nine
  backlog items and conflict resolutions are therefore **not inferred here**.
- The full canonical Profit Protection v2 specification is also unavailable.
  PR #34's 22-area v2 audit is explicitly provisional and is not v2 compliance
  evidence.
- `docs/evidence/issue-6-pr31-34-audit-2026-10-14.md` on draft PR #34 is reusable
  prior art for Issue #6 P1/P3 and the customer build path. This matrix extends
  that evidence to the supplied MASTER SPEC and its 18 cost-saving mechanisms;
  it does not replace or certify PR #34.
- A source path or automated test proves implementation/test behavior only.
  It does not prove authenticated live use, external-provider execution,
  durable production persistence, or a Golden E2E.

## Requirements-to-code matrix

| Requirement | Reusable implementation | Local evidence | State and exact gap |
|---|---|---|---|
| Product orchestration is deterministic code and owns lifecycle, admission, ceilings, handoffs, and stop decisions | `omni_prod/orchestrator.py`, `omni_prod/conversation/supervisor.py`, `omni_prod/worker_tasks.py`, `omni_prod/build_control.py` | Conversation, build-state, budget, and worker regression suites | **PARTIAL.** Existing orchestration and state controls are reusable. A single verified end-to-end orchestrator enforcing the MASTER SPEC state sequence has not been demonstrated. |
| Product conversation creates an editable, evidence-bound Spec with contextual Hebrew follow-ups | `omni_prod/conversation/supervisor.py`, `omni_prod/intake/`, `omni_prod/brief_repository.py`, `omni_prod/conversation/store.py`, `omni_prod/assets/app.js` | `tests/test_conversation_os.py`, `tests/test_intake_assistant_he.py`, `tests/test_intake_worker_route.py` | **IMPLEMENTED / TESTED LOCALLY; LIVE BLOCKED.** The code has deterministic discovery and a reserved worker-model seam. No authenticated real provider conversation or restart-persistent staging turn has been observed. |
| Spec is explicitly approved before planning/build spend; Architect emits a bounded Plan once | `omni_prod/build_contract.py`, `omni_prod/product_architect.py`, `omni_prod/conversation/supervisor.py`, approval/build routes in `omni_prod/investor_app.py` | Contract, approval, Architect, and conversation tests | **PARTIAL.** Revision-bound local approval and plan paths exist. A live user approval followed by the same durable plan/build chain is not verified. |
| Five bounded agents and 27 typed skills exchange only Spec, Plan, Patch, Verdict artifacts | `omni_prod/agent_os/`, `omni_prod/agents_registry.py`, `omni_prod/skills_registry.py`, `omni_prod/repository_patch.py`, `omni_prod/release_policy.py` | Agent OS, skill/agent registry, patch, and release-policy tests | **PARTIAL / CONFLICT REVIEW REQUIRED.** Typed plans/tasks, patches, and verification records exist, but this checkout also contains a broader agent taxonomy. Do not replace or collapse it until the missing Product Specification section 10 resolves the conflict. |
| Quote -> atomic reserve -> execute -> meter -> settle/release with durable evidence | `omni_prod/build_cost_plan.py`, `omni_prod/provider_pricing.py`, `omni_prod/subscription_store.py`, `omni_prod/attempt_ledger.py`, `omni_prod/routed_gateway.py` | `tests/test_m5_build_economics.py`, `tests/test_actual_cost_settlement.py`, `tests/test_qa_budget.py`, `tests/test_intake_budget_pg.py` | **PARTIAL.** Existing quote/reservation/metering paths are the source to extend. Full cross-scope caps, refunds/funding lots, calibrated completion estimates, checkpoint resume, and reconciled profitability are not complete. |
| Appendix A uniform tool contract, idempotency, caller permissions, and append-only money ledger | Existing billing, reservation, model gateway, worker, sandbox, preview, and registry services above | Tool-specific unit/integration tests; PR #34 build-request idempotency tests | **PARTIAL.** No single uniform result envelope or universal tool-permission/idempotency conformance suite was found. Money and provider effects must remain in deterministic services; do not add an LLM-owned wallet or parallel tool runtime. |
| Build -> QA -> repair -> verified private preview -> customer result | `omni_prod/worker_tasks.py`, `omni_prod/agent_os/runtime.py`, `omni_prod/repair_loop.py`, `omni_prod/release_policy.py`, sandbox and preview modules | Build, repair, release, preview, and recovery suites; historical Golden records in `GOLDEN_E2E_MATRIX.json` | **PARTIAL.** Reusable implementation exists, but no current-head authenticated Golden E2E from real conversation through a real private preview is verified. |
| Savings and unit-economics measurement by project, agent, skill, model, and mechanism | `omni_prod/attempt_ledger.py`, `omni_prod/provider_usage.py`, `omni_prod/product_analytics.py`, `omni_prod/economics_report.py`, `COST_MODEL.md` | Attempt/usage/economics tests | **PARTIAL.** Token, usage, attempt, and cost fields exist. Per-mechanism counterfactual savings, estimate calibration, first-pass cost, and verified-build contribution metrics are not established as a complete measured dataset. |
| Latest Product Specification section 7: nine unverified capabilities | No exact list in the supplied part 3 excerpt or checked-out repository | Not available | **BLOCKED ON SOURCE.** The nine items cannot be named or prioritized faithfully until the remainder of part 3 (including section 7) is supplied. Do not substitute historical capability matrices. |
| Latest Product Specification section 10: conflict resolution | No section 10 text in the supplied part 3 excerpt or checked-out repository | Not available | **BLOCKED ON SOURCE.** Keep conflicts visible; do not let older vision/architecture documents override the missing current rule. |
| Canonical Profit Protection v2 requirements | No full titled v2 specification found; PR #34 records a provisional 22-area audit | PR #34 draft body and provisional audit | **BLOCKED ON SOURCE.** Do not claim full v2 compliance or implement policy inferred from the provisional numbering. |

## The 18 cost-saving mechanisms and measurement plan

The savings ranges below are **MASTER SPEC hypotheses**, not measured results.
Use comparable, accepted tasks and the effective provider price version.
Record `mechanism_id`, build/task/skill/model, activation reason, input/output
and cached tokens, cost before/after (or a versioned counterfactual), outcome,
latency, and whether the result was independently verified. If a counterfactual
or provider usage is unknown, report savings as **UNKNOWN**, never zero.

| # | Mechanism and spec hypothesis | Reusable code / current status | Required measurement and acceptance |
|---|---|---|---|
| 1 | `route_cheap_first` — 60-70% | `omni_prod/model_router.py` selects the least-cost eligible model; `omni_prod/routed_gateway.py` ranks priced routes. **PARTIAL:** quality/price routing exists, but the tier policy and achieved saving are not verified. | Per task: selected tier/model, eligible alternatives, same-price-version counterfactual, success/repair outcome, and verified cost delta. |
| 2 | `prefix_cache_align` — 70-90% on repeated input | `omni_prod/provider_usage.py` normalizes cached-token usage and `attempt_ledger.py` stores it. **NOT LOCATED:** stable cache-prefix construction/ordering was not found. | Cache-eligible versus uncached input tokens and actual provider cost for repeated, byte-identical stable prefixes; require provider-reported cache usage. |
| 3 | `narrow_context` — 40-60% input | `omni_prod/conversation/supervisor.py` bounds history; `omni_prod/project_memory.py` bounds selected memory. **PARTIAL:** no proof that agent file context is restricted to requested paths throughout execution. | Input tokens and cost versus full-context baseline, with file/path selection and task outcome recorded. |
| 4 | `diff_only` — 70-80% output | `omni_prod/repository_patch.py` and build/patch flows are reusable. **PARTIAL:** not established as the required output format for every code-writing task. | Output tokens/bytes and accepted patch rate versus full-file output on equivalent tasks; include rework cost. |
| 5 | `context_compact` — 50-70% in loops | `omni_prod/project_memory.py` deterministically bounds retained context. **PARTIAL:** T0 summarization every N execution steps is not established. | Tokens/cost per repair or multi-step loop before/after compaction, plus lost-requirement and rework rate. |
| 6 | `template_match` — 50-80% | `omni_prod/unified_engine.py` and existing product templates are reusable. **PARTIAL:** a deterministic match that demonstrably skips model planning was not verified. | Match rate, skipped calls, build acceptance, and same-family cost difference; count false matches and rework. |
| 7 | `reuse_component` — 80-95% for common UI | Existing design-system/UI code may be reused. **NOT LOCATED:** no governed reusable component library and invocation evidence were found in reviewed surfaces. | Component lookup/reuse rate, output tokens avoided, patch acceptance, and subsequent repair cost. |
| 8 | `output_cap` — 30-40% output | `omni_prod/model_gateway.py` requires positive `max_tokens`; routed completion carries an output allowance. **PARTIAL:** task-specific caps and avoided spend are not measured across skills. | Requested cap, actual output tokens, truncation, retry/rework, and cost per accepted output. |
| 9 | `fail_fast` — 30-50% | Build-cost validation, model policy, and release/acceptance gates block known-invalid work. **PARTIAL:** early detection savings before token-consuming stages are not measured end-to-end. | Cost/tokens incurred before terminal failure, stage of first deterministic failure, and avoided downstream work. |
| 10 | `batch_collect` — about 50% | **NOT LOCATED:** no Batch API collection/submission route was found. | Batch-eligible calls, batch discount/source, latency, completion/failure rate, and cost versus synchronous equivalent; do not activate a paid batch route without approval. |
| 11 | `escalate_late` — 40-60% | `omni_prod/routed_gateway.py` bounds same-route transient retries before fallback. **PARTIAL:** quality-tier escalation after exactly two task failures is not proven. | Initial-tier attempts, escalation trigger, fallback calls, total cost, first-pass success, and quality acceptance. |
| 12 | `dedupe_tasks` — 10-20% | Existing plan/build fingerprints and idempotency prevent repeated side effects. **NOT LOCATED:** duplicate-task detection/merge in the Plan was not established. | Duplicate task pairs detected/merged, dependency equivalence, avoided calls, and missed-distinct-task/rework rate. |
| 13 | `incremental_verify` — 50-70% verification | A skill entry exists in `omni_prod/skill_catalog.py`; build and QA checks exist. **PARTIAL:** changed-file/dependency-graph selection and safe invalidation are not proven as a complete path. | Changed/dependent checks run versus full suite, cost/time delta, cache-key digest, and false-negative rate from full-check sampling. |
| 14 | `estimate_gate` — prevents overspend | `omni_prod/build_cost_plan.py` blocks unknown required quotes and reserves the full maximum before enqueue. **IMPLEMENTED / TESTED LOCALLY; LIVE UNVERIFIED.** | Quote versus actual/error distribution, denied-over-cap attempts, reservation coverage, UNKNOWN exposure, and any cap overrun (acceptance: none). |
| 15 | `retry_budget` — prevents loops | `RetryPolicy`, routed-call retry caps, repair policy, and `retry_reserve_usd` exist. **PARTIAL:** a unified per-task retry/repair liability is not verified. | Attempts and cost by task/stage, retry reason, success lift, maximum liability, and proof no retry exceeds the authorized reserve. |
| 16 | `artifact_cache` — 30-60% | **NOT LOCATED:** no accepted cross-project Patch/Verdict cache with complete invalidation evidence was found. | Cache hit/miss, artifact and environment fingerprints, avoided model/test cost, invalidation correctness, and leakage/isolation tests. |
| 17 | `cold_context` — 20-30% | Bounded conversation and project-memory reads are reusable. **PARTIAL:** lazy task-open context loading versus eager preload was not verified. | Context bytes/tokens loaded at task open versus execution, time-to-first-call, and work blocked by missing context. |
| 18 | `batch_embed` — negligible direct cost, saves time | **NOT LOCATED:** no batched embedding/indexing workflow was found in the reviewed route. | Documents/vectors per batch, provider calls, cost per indexed item, query latency, freshness, and retrieval-quality regression. |

### Shared measurement roll-up

The implementation should extend existing attempt/usage records rather than
create a second ledger. Aggregate, by project/agent/skill/model/product family:

- verified-build cost and failed-build cost;
- estimate-versus-actual variance, keeping UNKNOWN distinct;
- first-pass success and rebuild/repair rate;
- per-mechanism measured savings and cache/escalation rates;
- contribution margin with revenue basis, fees, refunds, infrastructure,
  support, and tax/FX clearly separated;
- failure attribution and cost by stage.

For each mechanism, publish the sample size, price/catalog version, comparison
method, verified outcome, and uncertainty. Do not add expected percentage
ranges to customer-facing claims until measured on representative tasks.

## Immediate sequence and dependencies

1. **P0 conversation-to-approval:** retain the current worker-routed provider,
   brief, plan, approval, and UI implementation; run offline regression only.
   A real provider Golden E2E is blocked by the explicit no-paid-API rule,
   worker-side credential/caps, isolated staging services, and unapplied
   migration chain.
2. **Migration sequencing:** this PR #31 worktree adds
   `039_conversation_preferences.sql`, while PR #33 independently adds
   `039_billing_event_idempotency.sql` and PR #34 adds migration 040. Keep all
   drafts intact. A reviewed stack/numbering decision is required before
   integrating or deploying these migrations; none was applied here.
3. **Architect -> build -> repair -> preview:** reuse the existing Architect,
   Agent OS, worker, acceptance, repair, and private-preview path. Prove the
   exact customer journey only in an authorized isolated environment.
4. **Economics safety:** preserve PR #33 safety fixes and PR #34 caller-stable
   idempotency; obtain the canonical Profit Protection v2 specification before
   treating the provisional 22-area audit as normative.
5. **Nine-capability backlog and section 10 reconciliation:** ingest the full
   Product Specification part 3 before naming, reprioritizing, or implementing
   its nine capabilities or resolving architecture conflicts.

No paid provider call, migration, shared-database write, Production deployment,
merge, or billing change is authorized by this matrix.
