# ADWv1 gap audit — existing architecture only (2026-10-11)

**Scope / definition.** The repository, the issues and the uploaded directives contain no definition of "ADWv1". For this audit, ADWv1 means the **autonomous development workflow, version 1**: approved customer requirements → Chief Architect plan → ExecutionGraph → AgentRuntime + Worker execution → Workspace versions/previews → verification → release. Its acceptance is the existing Golden E2E definition in `docs/OPERATING_CONTRACT_HE.md` §29K (23 "Real …" proofs, from user authentication to secret redaction, each replayable or evidence-backed) and §29L (first-pass / verified success rate, repair rate …), together with the STATUS gate of ≥ 10 diverse paid builds at ≥ 90 %. §38 sets the working rule: find the **first** step of the Web/SaaS path that is FAIL / BLOCKED / NOT VERIFIED / UNKNOWN, fix only that, with no new capability and no broad refactor. If the founder means something else, the per-component evidence below still holds; only the gap list changes.

**Method.** Every statement below cites code (file:function), a test, the capability registry (`AGENT_OS_REGISTRY.json`, statuses computed by `omni_prod.agent_os.audit` with the evidence lock), or a real run. Baseline: integration branch `2a2bba6` (+ PR #11 reconciliation `6296c2d` where stated). No new architecture is proposed. Each gap names the **existing** module to extend.

## 1. Component inventory (what exists, what it really does)

| Component | Code | What it does today (verified in code) | Registry status | Evidence |
|---|---|---|---|---|
| Conversation / intake | `conversation/supervisor.py`, `intake/*` | Hebrew-first deterministic intake. Paid model intake is reserved (037), classified, and off. | intake_agent **UNIT_TESTED**; requirements_agent REAL_SERVER_VERIFIED (older discovery path) | unit + real-PG tests; no live model turn |
| Requirements contract | `intake/contract.py` (`intake-requirements/1`) | Validated, fingerprint-bound contract from the brief, including `acceptance_criteria` | — | unit tests |
| Approval | `brief_repository.py` (`build_approvals`, 030) | Approval bound to brief revision/fingerprint, contract and quote. A change invalidates it. | product_planner REAL_SERVER_VERIFIED | real-PG tests `test_discovery_and_approval.py` |
| Chief Architect | `planning/architect.py:ChiefArchitect.plan`, `web_graph` | Builds a 15-task web DAG whose tasks map 1:1 to fixed engine stages. Non-web families get a non-executable gap graph. | chief_architect **UNIT_TESTED** | unit tests only |
| ExecutionGraph | `planning/graph.py` | Validation: cycles, closure, aggregate budget, MAX_TASKS, invalidation. **No scheduler.** | — | 2 test files |
| Feasibility | `planning/feasibility.py` | FEASIBLE / WITH_CONSTRAINTS / BLOCKED / UNSUPPORTED / UNKNOWN. Build admission refuses infeasible plans (409). | — | unit tests |
| AgentRuntime | `agent_os/runtime.py` | Durable `agent_tasks` state machine (migration 034): dependency checks, budget per task, FAILED → BLOCKED cascade. **Nothing dispatches tasks from it.** | — | real PG tests |
| Plan-bound recording | `agent_os/recorder.py:PlanBoundRecorder.start`, `worker_tasks.py` (≈ line 853) | Pre-creates the approved DAG as agent_tasks and moves them **as the fixed pipeline reaches each stage**. Best effort: never changes the build outcome. | quality_gate_agent **UNIT_TESTED** | live-PG unit tests; never on a real build with a plan |
| Worker / engine | `worker_tasks._run_live_build_job*`, `autonomous_core.py`, `sandbox_executor.py`, `remote_sandbox.py` | Fixed sequential pipeline: architecture → codegen → consistency gate → sandbox tests → repair loop (progress-ranked, rollback) → preview → behaviour → browser → visual → security → review → release policy. | architecture/coding/repair/qa/behavioral/browser/security agents REAL_SERVER_VERIFIED | paid run 37961193099 (14 agents, independent links); verify-replay 38083686082 |
| Workspace | `workspace.py` (versions + checksums, R2 artifacts), previews (`preview_*`) | Immutable versions, export, rollback, previews | deployment_agent REAL_SERVER_VERIFIED | free checks 38083312245 |
| Build verification decision | `release_policy.py` (`quality-report/1`) | READY only when every mandatory check passes. NOT_RUN/UNKNOWN block; enforced on the worker. | quality_gate_agent UNIT_TESTED; release_agent **IMPLEMENTED (stale)** | verify-replay 38083686082 (12/12 agree) |
| Canonical verdict + promotion gate | `verification_contract.py` — **only on PR #11's branch, not on the integration branch** | `verification-result/1`, trusted-policy recomputation, stale-evidence refusal | — | 60+ tests; used **only** by `tools/deployment_verify.py` |
| Post-deployment verification | `tools/deployment_verify.py` + workflow (PR #11) | 11 mandatory checks against a real deployment | — | local real server VERIFIED / FAILED; on Vercel **BLOCKED** (no bypass secret) |
| Cost | builds: `credit_reservations` + write-ahead attempt ledger; intake: `intake/budget.py` (037) | Two scopes, two mechanisms (build credits vs intake reservations) | cost_economics_agent **IMPLEMENTED (stale)** | economics run 38083624196 |
| Modification | `modification_engine.py`, `/modifications/*` endpoints, chat `confirm_modification` action | Chat offers the existing pipeline; not exercised end to end from chat | product_evolution_agent **IMPLEMENTED (stale)** | — |

## 2. Gaps (evidence → existing module to extend → how it is verified)

| # | Gap | Evidence | Extend (no second system) | Verification needed | Cost |
|---|---|---|---|---|---|
| G1 | **The DAG describes execution but does not drive it.** No task scheduling, per-task retry, parallel branches or per-task budget enforcement. Budget is enforced per build (credits + gateway `bind_budget`), not per task. | `recorder.py` maps stages → tasks; `runtime.py` has no dispatcher; `worker_tasks` runs the fixed pipeline | Make `PlanBoundRecorder` / `AgentRuntime` the **source of the stage order** in `_run_live_build_job_with_components` (refuse to start a stage whose task is not READY), then enforce `agent_tasks.budget_usd` through the existing gateway `bind_budget` per task | real-PG tests + 1 paid build per family | free code, paid verification |
| G2 | **Plan-bound execution never ran on a real build.** chief_architect, quality_gate_agent and intake_agent are UNIT_TESTED. | registry | no code; needs a real run | 1 paid build through the conversation → approval → plan path (≈ $0.15 cap) | **paid: founder approval** |
| G3 | **Approved acceptance criteria are not the test basis.** Acceptance uses the generated product spec plus the build-contract scope, not `intake-requirements/1.acceptance_criteria` (G0 finding #9 still open). | `worker_tasks.py` ≈ 1403–1412 (`PostgresSpecRepository`, `contract_scope_for_version`); no reference to contract `acceptance_criteria` in the build path | Pass the approved contract's criteria into `web_saas_acceptance` coverage (`covered/missing_acceptance_ids`) and into `release_policy` as a mandatory check "every approved criterion covered" | unit + verify-replay on stored versions (free) | free |
| G4 | **Non-web product families are not executable** (UNSUPPORTED gap graph) | `architect._gap_graph` | per family: engine stage + verifier, then `web_graph`-style mapping | per family real build | paid |
| G5 | **Two verdict layers not yet connected.** Builds persist `quality-report/1`; `verification-result/1` and `may_promote` are used only by the deployment tool; no promotion step consumes them. | `verification_contract` importers: only `tools/deployment_verify.py` | Persist `from_quality_report(...)` next to the quality report (same row/evidence), and gate Vercel promotion on the deployment-verify check | unit + Vercel setting | free + founder setting |
| G6 | **Post-deployment verification cannot see the real deployment** | runs 38113948928 / 38131318810: 401 → BLOCKED | none (code ready) | founder creates `VERCEL_AUTOMATION_BYPASS_SECRET` | founder |
| G7 | **Reviewer independence**: one working provider, so the reviewer may equal the author | `release_policy` records `independent`; STATUS risks (OpenAI 429 / Anthropic low balance) | none (code records it honestly) | second provider with credit | founder/billing |
| G8 | **Stale real-server evidence**: release_agent, cost_economics_agent, product_evolution_agent are IMPLEMENTED (code changed after the last real run) | registry `why: real-server evidence is stale` | none | free `postdeploy-checks stage=free` / `verify-replay` / `economics` after merge, then regenerate registry | free |
| G9 | **Golden E2E acceptance gate (≥ 10 builds, ≥ 90 %) NOT RUN.** Historic ledger 11/32 READY (34 %). | STATUS | none | 10 paid builds, one at a time, ≤ $0.15 each | **paid: founder approval** |
| G10 | **Modification from chat not verified end to end** | no test from chat action to accepted version | existing `/modifications` endpoints + `confirm_modification` action | 1 paid modification on the worker | paid |
| G11 | **Build path assumes HTTP errors are free** (`RoutedModelGateway._release_rejected`), unlike intake | code | `routed_gateway` + the attempt ledger's UNKNOWN exposure (already reported in economics) | unit + economics run | free |
| G12 | **accessibility_agent is instruction-only** (contrast/labels advisory) | registry `model instruction only`; G2 visual QA advisory | `visual_qa` rules → enforced after founder decision on WCAG enforcement | verify-replay | free + founder decision |

## 3. What is NOT a gap (and must not be rebuilt)
- **Outbox:** two transactional outboxes on one pattern (`build_outbox`, `intake_outbox`) for different FK domains. Do not add a third.
- **Budget:** build credits + attempt ledger (builds) and intake reservations (conversation) cover different scopes. Do not add a general budget service unless G1 needs per-task enforcement, and then extend `agent_tasks.budget_usd` + `bind_budget`.
- **Verification:** the per-check verifiers exist (consistency gate, sandbox, preview smoke, behaviour, browser, visual, security, review). The decision engine exists (`release_policy`). Only the link G5 is missing.
- **Workspace / versions / previews:** real-server verified.

## 4. Order under §38 (first unverified step of the Web/SaaS path)
Walking §29K in path order on the approved flow (conversation → approval → plan → build):

| §29K step | Status now | Gap |
|---|---|---|
| authentication | verified (free checks) | — |
| persistence | verified | — |
| **product plan** (Chief Architect plan bound to the build) | **NOT VERIFIED** (UNIT_TESTED only) | **G2** — first failing step |
| quote / budget reservation | build credits verified (paid run 37961193099); intake reservation not live | — |
| … | | |
| modification / new version | stale evidence | G8 / G10 |

So the first step to close is **G2**. It needs one paid build (≈ $0.15 cap, founder approval) and no new code. Until that budget is approved, the only §38-compatible free work is evidence hygiene that changes no product code:
1. **G8**: rerun `postdeploy-checks stage=free` / `verify-replay` / `economics` after PR #11 merges, then regenerate the registry.
2. **G6**: founder secret.

G3, G5, G1 and G11 are real gaps, but under §38 they are worked on only when they become the first failing step (G3 is the likely next one: approved acceptance criteria → tests).

## 5. Verifiable commands
```bash
python -m omni_prod.agent_os.audit            # registry statuses used above (no --write: check only)
grep -rln "ExecutionGraph" omni_prod            # architect.py, recorder.py (+ agents.py registry entry), graph.py
grep -rn "verification_contract" omni_prod tools   # none on the integration branch; tools/deployment_verify.py on PR #11
sed -n 1400,1415p omni_prod/worker_tasks.py    # acceptance contract source (G3)
```
