# Model/provider routing — contract audit (2026-10-07)

Contract: *Best Result at the Lowest Justified Cost* — dynamic
cost/quality/capability routing + verification + escalation, provider-neutral,
learning from measured outcomes, every decision evidenced, all spend under
Quote → Reserve → Execute → Meter → Settle.

Scope rule: Golden E2E #1 (Web/SaaS) keeps priority. This audit records what
exists; it does not rewrite working code. Status values: PASS / PARTIAL / MISSING.

## Components that exist

| Component | Where | Used by |
|---|---|---|
| `RoutedModelGateway` | `omni_prod/routed_gateway.py` | every LLM call of Architect/Generator/Repair/Modification agents |
| Priced model catalog + per-call cost ranking | `omni_prod/model_catalog.py`, `RoutedModelGateway.ranked_routes` (added 2026-10-06) | same |
| `model_router.select_model` (price/quality/latency) | `omni_prod/model_router.py` | cost formula reused by the gateway |
| `CapabilityProviderRouter` (hard-policy, health, quote, formats, commercial use) | `omni_prod/provider_router.py` | image capability |
| Whole-build budget reservation before enqueue | `investor_app.v28_build_async`, `_m5_build_economics_quote` | builds |
| Per-call authorization against the reserved budget | `model_policy.authorize_model_call` | every external call |
| Provider-reported usage ledger | `omni_prod/provider_usage.py` | persisted in build evidence |
| Route events persisted in build evidence | `worker_tasks.py` (`model_route_events`) | builds |
| Skills / Agents registries | `MASTER_SKILLS_REGISTRY.json`, `MASTER_AGENTS_REGISTRY.json` | truth lock, capability closure |

## Contract items

| # | Requirement | Status | Evidence / gap |
|---|---|---|---|
| 1 | Provider-neutral adapters | PASS | One OpenAI-compatible adapter; providers are catalog entries (`base_url`, `model`, `api_key_env`). Anthropic/Gemini/Groq/OpenAI all expose OpenAI-compatible endpoints. |
| 2 | Price-aware selection | PASS | `ranked_routes`: cheapest model meeting `OMNI_MODEL_MIN_QUALITY` first; conservative per-call cap from catalog prices. Tests: `tests/test_model_catalog_routing.py`. |
| 3 | Quality floor / quality preference | PARTIAL | Global floor and cost-vs-quality switch exist. Quality scores are static catalog numbers, not measured. |
| 4 | Latency | PARTIAL | `RoutingPolicy.maximum_latency_ms` honored; latency values are static. |
| 5 | Escalation on failure | PARTIAL | Provider error → next ranked model, budget-gated. Escalation on *verifier/build failure* to a stronger model is MISSING: the repair loop reuses the same router order. |
| 6 | Budget gate on every call, no call before reservation | PASS | Reservation in the build transaction; `authorize_model_call` before every request; zero-cost mode blocks external calls. |
| 7 | Estimated never recorded as actual | PASS | Ledger stores provider-reported usage separately from authorized estimates (`worker_tasks.py` docstring, `provider_usage`). Actual USD from usage × catalog price is not yet computed (MISSING). |
| 8 | Routing evidence (task, provider, model, reason, max cost, outcome) | PARTIAL | `RouteEvent` now records provider, model, call kind, reason, max authorized cost, ok/error, request id, latency. Task/agent role is MISSING (gateway does not know which agent called). |
| 9 | Task/capability decomposition (DAG) before routing | PARTIAL | Build Contract + capability plan exist (image etc. routed by `CapabilityProviderRouter`). LLM sub-tasks (architecture, frontend, backend, tests, repair) are not separately routed. |
| 10 | Per-task model choice (e.g. coding vs reasoning) | MISSING | All LLM calls share one ranking. Needs a `task` tag from each agent and per-task minimum quality / required traits. |
| 11 | Context window, tool-calling, modality traits | MISSING | Catalog has no `context_window`/traits fields; requests are not checked against them. |
| 12 | Live availability / rate limits / circuit breaker for LLMs | PARTIAL | Exists for capability providers (`RedisCircuitBreaker` in `provider_router`), not for the LLM catalog. |
| 13 | User plan / remaining credits in routing | PARTIAL | Plan budget caps the reservation; routing does not vary by plan. |
| 14 | Learning from outcomes (success, repair rate, cost, verification score per model × task) | MISSING | Raw material is persisted (route events + usage + build outcome) but no aggregation table and no feedback into ranking. |
| 15 | Registries as source of truth for which providers serve which capability | PARTIAL | Skills registry has `provider_keys`/`cost_model`; the LLM catalog is configured by env, not derived from the registry. |
| 16 | Minimum number of calls | PASS | Exactly one model per call; fallbacks only on failure. |

## Extension path (no rewrite)

The gateway is the single choke point, so every missing item is additive:

1. `task` argument on `complete/complete_json` (default `general`), passed by each agent → items 8, 10.
2. Catalog fields `context_window`, `traits`, per-task quality overrides → items 10, 11.
3. Actual cost = provider usage × catalog price at call time, stored next to the estimate → item 7.
4. `model_task_outcomes` table fed from build evidence; ranking uses measured success/repair/cost when sample size is sufficient, static scores otherwise → items 3, 14 (the "Cost/Quality Intelligence Layer").
5. Verifier-driven escalation: repair round N may raise the minimum quality tier, still budget-gated → item 5.
