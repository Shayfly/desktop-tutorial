# System-wide gap audit: Conversation → Chief Architect → Agent execution → Verified product (2026-10-11)

Baseline: integration branch `milestone/pre-staging-2026-10-05` @ `2a2bba6` (PR #14 merged) plus this branch (`claude/plan-driven-execution-2026-10-11`). Statuses follow the master directive:
- **IMPLEMENTED**: the code exists.
- **TESTED**: automated tests pass. They use real PostgreSQL/Redis where stated, and test doubles for providers.
- **VERIFIED**: a real run with evidence.
- **LIVE**: used by real customers on the intended environment.
- **PARTIAL** / **BLOCKED**: as named.

LIVE is never claimed from unit tests. Nothing here is LIVE: Production still serves the old `main` (`e8f2949`, 2026-10-06).

## 0. Repository and deployment state (Stage 0)

| Item | State | Evidence |
|---|---|---|
| Integration branch | `2a2bba6` = PR #13 + PR #14 merged 2026-10-11 09:58 UTC | `git ls-remote` |
| PR #11 (Continuous Verification) | open, head `6296c2d`, reconciled with 037, CI green except deployment-verify BLOCKED (401: no bypass secret) | `docs/PR11_RECONCILIATION.md` on its branch |
| PR #9 (PDV-001) | open draft, superseded by #11; recommended: close without merge | same |
| PR #15 (ADWv1 gap audit) | open draft `5ed72e4` (docs only) | `docs/ADWV1_GAP_AUDIT.md` |
| Issue #12 (budgeted Hebrew intake) | implemented and merged (#14); **not activated** (no paid budget approved) | STATUS 2026-10-11 15:30 |
| Issue #6 (quality evidence pipeline) | release_policy + verify-replay exist; Golden E2E gate not run | STATUS |
| Migrations | 001–021, 026–037. 037 applied on pre-staging (deploy-worker run 38130249079) | `omni_prod/migrations.py` |
| Vercel Preview of the integration branch | `dpl_E3krd8kPxRSba6DHNJmZsMLXdBsK` @ `2a2bba6`, READY | Vercel API |
| Vercel Production | `main` @ `e8f2949` (2026-10-06), **old code** | Vercel API (target=production) |

## 1. Build path: component and dependency map

```
customer message
  └─ ConversationSupervisor (conversation/supervisor.py)
       ├─ complexity.classify → lanes.choose ── LOW: no model │ MEDIUM: standard │ HIGH/RISKY: escalated (NEW)
       ├─ interpreter: Deterministic │ ReservedWorkerInterpreter → intake/budget (037) → reservation_worker
       ├─ intake_agent.apply (confirmed values never overwritten)
       └─ brief_repository (revisions, fingerprint) ──► approval (build_approvals 030, server-bound)
build admission (investor_app.v28_build)
  ├─ credits reservation + attempt ledger
  └─ _bind_execution_plan → ChiefArchitect.plan (15-task web DAG, feasibility gate, permissions + deliverable NEW)
worker (_run_live_build_job)
  ├─ recorder_for → PlanBoundRecorder (agent_tasks 034)  ── OMNI_PLAN_DRIVEN=1: governs (NEW) │ else records
  ├─ engine.build: architect → generator → PlanAdmittedExecutor(NEW) → Controlled → consistency → sandbox
  │                → preview → behaviour → browser → visual → quality → review ; repair loop (plan-bounded NEW)
  ├─ release_policy.build_report (quality-report/1) + approved_criteria_covered (NEW, G3)
  └─ workspace version + preview ──► verification_contract / deployment_verify (PR #11, not merged)
```

| Component | IMPLEMENTED | TESTED | VERIFIED | LIVE | Notes |
|---|---|---|---|---|---|
| Deterministic Hebrew/English intake | yes | yes | real browser walkthrough, local server (Wave A) | no | — |
| Paid model intake + reservations | yes | real PG + Redis (25 concurrency tests) | no real provider call | no | BLOCKED: founder budget |
| Complexity routing incl. escalation | yes (escalation NEW) | yes | no | no | escalation runs only when paid intake is on |
| Requirements preservation | yes | yes | no | no | — |
| Approval binding | yes | real PG | yes (paid run 37961193099 path) | no | — |
| Chief Architect plan | yes | unit | **no (G2)** | no | needs 1 paid build |
| Plan-governed execution | yes (NEW, flag) | real PG, real engine loop, stub agents | **no** | no | flag off by default |
| Engine + verification chain | yes | yes | REAL_SERVER_VERIFIED (paid 37961193099; replay 38083686082) | no | — |
| Release policy | yes | yes | replay 38083686082 | no | — |
| Canonical verdict + deployment verifier | PR #11 only | yes | local real server VERIFIED; Vercel BLOCKED | no | merge + bypass secret |
| Workspace / versions / previews | yes | yes | free checks 38083312245 | no | — |
| Modification from chat | yes | yes | stale evidence | no | G10 |

## 2. Gaps (the 12 ADWv1 gaps + system-wide)

| # | Gap | Severity | Customer impact | Fix | Test proving the fix | Status now |
|---|---|---|---|---|---|---|
| G1 | DAG does not drive execution | high | plan is decorative; per-task budgets not enforced | **Done in this branch (flag):** `PlanBoundRecorder(enforce=True)` admits every model call and verification run; dependencies are checked under a row lock in `agent_tasks`; spend is charged per task (`AgentRuntime.charge`); the plan's repair limit bounds the engine; a superseded worker is refused; violations are sticky → `plan_violation` | `tests/test_plan_driven_execution.py` (real PG; 17 of the live tests; CI job `intake-budget-pg` fails on skip) | IMPLEMENTED + TESTED; not VERIFIED (needs G2) |
| G1b | No parallel dispatcher; no resume from a task checkpoint | medium | longer builds; a crash restarts the build | Split the verification chain into per-stage executors dispatched from READY tasks. This is a re-architecture of the engine, so it is not done | — | NOT IMPLEMENTED (documented in `plan.execution_mode.not_yet`) |
| G2 | Plan never ran on a real build | **critical** (first §38 step) | unknown | 1 paid build through conversation → approval → plan, with `OMNI_PLAN_DRIVEN=1` (cap ≈ $0.15) | evidence run + registry regeneration | BLOCKED: founder budget |
| G3 | Approved criteria are not the test basis | high | the customer's criteria might not be tested | **Done in this branch (plan-governed builds):** the binding carries `acceptance_criteria`. They are merged into the spec as `APPROVED-AC*`, so the behaviour runner must cover each with a passing step. A new mandatory check `acceptance/approved_criteria_covered` blocks READY when one is FAIL or NOT_RUN | `ApprovedCriteriaTests` | IMPLEMENTED + TESTED; not VERIFIED (G2) |
| G4 | Non-web families not executable | high | refused with a reason (409) | per family | — | NOT IMPLEMENTED (honestly refused) |
| G5 | quality-report/1 not linked to verification-result/1 | medium | — | after PR #11 merge: persist `from_quality_report` | unit | BLOCKED: PR #11 merge approval |
| G6 | Deployment verification blind on Vercel | high | — | none (code ready) | — | BLOCKED: `VERCEL_AUTOMATION_BYPASS_SECRET` |
| G7 | Reviewer independence | medium | — | second provider with credit | — | BLOCKED: billing |
| G8 | Stale real-server evidence | medium | — | free reruns after merge | — | pending merge |
| G9 | Golden E2E gate (≥10 builds, ≥90 %) | **critical** for Beta | — | 10 paid builds | — | BLOCKED: founder budget |
| G10 | Chat modification not verified end to end | high | — | 1 paid modification | — | BLOCKED: budget |
| G11 | Build path treats HTTP errors as free | medium | cost under-reported | apply intake's UNKNOWN rule to `_release_rejected` | unit + economics | NOT IMPLEMENTED |
| G12 | Accessibility advisory only | medium | — | founder decision on WCAG enforcement | — | BLOCKED: decision |
| S1 | Strong-model escalation for complex intake | medium | complex turns handled by the cheapest model | **Done:** HIGH/RISKY → `conversation_complex` (preferred 85, mandatory 70). The quote, the reservation payload and the worker call all use the same task, and a mismatch is refused before execution | `LaneTests`, `test_complex_turns_escalate…` | IMPLEMENTED + TESTED; not VERIFIED |
| S2 | Plan lacked explicit permissions / deliverable | low | — | **Done:** `plan.permissions`, `plan.deliverable` (preview must pass named release checks), `plan.execution_mode`; the graph fingerprint is unchanged | `PlanContentsTests` | IMPLEMENTED + TESTED |
| S3 | QA reviewer swallows exceptions | medium | a refused/cancelled review looked like "reviewer unavailable" | plan-governed builds: sticky violation re-raised at the next hook and after `engine.build`; legacy behaviour unchanged | `test_a_violation_swallowed…` | partial (only plan-governed builds) |
| S4 | Production serves old `main` | — | customers see a 2026-10-06 build | promotion after Beta gates | — | intentional; founder decision |

## 3. What blocks each release gate

- **Private Beta**:
  - G2 (one paid plan-governed build);
  - PR #11 merge (founder);
  - G6 bypass secret;
  - G10 one paid modification;
  - activation of paid intake (budget + flags).
- **Public Beta**: all of the above, plus:
  - G9 Golden E2E (≥ 10 builds, ≥ 90 %);
  - G7 reviewer independence;
  - G11 cost truth on builds;
  - G8 fresh evidence;
  - G12 decision.
- **Production**: all of the above, plus:
  - G1b dispatcher/resume, or an explicit decision that sequential is acceptable;
  - G4 per supported family;
  - the launch acceptance criteria in `PRODUCT_MISSION_AND_ACCEPTANCE.md` passing on the intended environment;
  - founder authorization.

## 4. Rollback

Plan-governed execution and G3 only take effect with `OMNI_PLAN_DRIVEN=1` (worker env); the plan additions (permissions, deliverable) are descriptive fields. Rollback is to unset it. The escalated intake lane only runs when paid intake is enabled. Rollback is to revert `lanes.choose` (one function). No migration was added.
