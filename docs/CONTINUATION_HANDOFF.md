# 148AI — Continuation handoff (2026-10-10, Claude → ChatGPT / Copilot)

## WAVE A (2026-10-11 03:05) — read this first

- Branch: `claude/wave-a-intelligence-platform-2026-10-11` (pushed). Base `c20503a` = `c874998` + merge of PR #7 (`223206d`). Integration branch `milestone/pre-staging-2026-10-05` still at `67a0765` (untouched). Deployed worker `67a0765`. Vercel production target = old `main` `e8f2949`.
- Commits: `17d246e` A1–A2 · `a138ccc` A3–A9 + UI · docs commit after it (see `git log`).
- Status of each phase: `STATUS.md` (top section). Baseline/source of truth: `docs/WAVE_A_BASELINE.md`.
- Where the code is: `omni_prod/intelligence/` (matrix, prices, lifecycle, governance, task_policy, health), `omni_prod/intake/`, `omni_prod/planning/`, `omni_prod/conversation/`, `omni_prod/agent_os/departments.py`, `PlanBoundRecorder` in `agent_os/recorder.py`, endpoints in `investor_app.py` (search `Wave A`), UI in `omni_prod/assets/{index.html,app.js,app.css}`, migration `infra/postgres/036_intelligence_plane.sql`.
- Generated files (never hand-edit): `PROVIDER_MATRIX.json`, `docs/PROVIDER_MATRIX.md`, `DEPARTMENT_MATRIX.json`, `docs/DEPARTMENT_MATRIX.md` + the earlier registries. Regenerate:
  ```bash
  python -m omni_prod.registry_audit --write && python -m omni_prod.agent_os.audit --write
  python -m omni_prod.agent_os.departments --write && python -m omni_prod.intelligence.matrix --write
  python tools/generate_neon_bootstrap.py
  ```
- Tests: `python -m pytest tests/test_intelligence_plane.py tests/test_conversation_os.py tests/test_economics_report.py -q` (live PostgreSQL parts need `M4D2_DATABASE_URL`). UI: start the app with Postgres (migrations through 036), then `OMNI_UI_BASE=http://127.0.0.1:8148 python tools/ui_conversation_walkthrough.py <dir>`.

### Exact next actions (in order)
1. Check CI (`v24-ci`, `V11 Overlay CI`) for the branch head; fix any failure (local env cannot install from PyPI; CI is the authority).
2. Open/refresh the PR `claude/wave-a-intelligence-platform-2026-10-11` → `milestone/pre-staging-2026-10-05` (do not push to the integration branch directly). PR #7 is already contained in this branch.
3. Founder approval to merge → deploy-worker applies migration 036 and runs the free checks (`postdeploy-checks stage=free`); then the Vercel Preview of the integration branch serves the conversation UI for real testing.
4. Live AI conversation: needs (a) a `GEMINI_API_KEY` on Vercel (founder adds; never in chat) or routing intake through the worker, (b) `OMNI_INTAKE_MODEL=1`, (c) an approved `OMNI_INTAKE_MODEL_BUDGET_USD`, (d) the paid benchmark `python -m omni_prod.intake.benchmark --model` with `OMNI_INTAKE_BENCH_BUDGET_USD`. Until then the conversation is deterministic and must be described as such.
5. Remaining engineering: A6 typed department-handoff contract checks (backend API ↔ frontend), A8 media adapters (disabled by default, test doubles), modification-from-chat end-to-end test on the worker, `postdeploy_checks` stage for the conversation + plan-bound agent graph, paid 10-build Golden E2E gate after budget approval.

## Where the work is
- Repository: `Shayfly/desktop-tutorial` (private). **The GitHub default branch `main` is old (2026-09-22) — do not use it.**
- **Active branch: `milestone/pre-staging-2026-10-05`** — last merged + deployed code: `67a07658ae0b91b9e376fe7d44cbfe7395cf35b7`.
- Claude's task branch: `claude/g0-baseline-2026-10-09` (fast-forward merged into the active branch after green CI each time). The handoff commit (this file + STATUS + evidence registry refresh) is pushed to the task branch; see the final commit SHA in the founder report / `git log`.
- Pre-staging worker (Oracle host, self-hosted runner) runs `67a0765`; Vercel project `148aiv28` builds the active branch.
- Rollback point for this session's work: `8ce71c043c3cb2a88f92e00019ea9850064e20af` (start of Production Assurance v2).

## Completed (code + tests; real-server evidence where stated)
| Area | What | Evidence |
|---|---|---|
| G0 truth lock | Status vocabulary NOT_IMPLEMENTED/IMPLEMENTED/UNIT_TESTED/INTEGRATION_TESTED/REAL_SERVER_VERIFIED/LIVE/BLOCKED (`omni_prod/agent_os/contracts.py`, `audit.py`); LIVE requires production evidence → 0 LIVE; instruction-only skills capped at IMPLEMENTED; platform-account / model-provider evidence no longer credited to generated-app skills | `docs/G0_AUDIT_2026-10-10.md`, `TRUTH_MATRIX.json`, `docs/TRUTH_MATRIX.md` |
| G0 audit fixes | legacy template builds, in-memory hosted runtime, canned sources and gate-skipping `/patch` → 410 on staging/production (`investor_app.py` middleware); remote sandbox rejects no-op verify commands; recorder no self-certification | free checks run 38083312245 (18/18) |
| G1 release policy | `omni_prod/release_policy.py`: QualityReport `quality-report/1`, policy `release-policy/1`; READY only when every mandatory check PASS; NOT_RUN/UNKNOWN block; shadow refused on staging/production; worker fails with `release_policy_failed` (UI text he/en) | `tests/test_release_policy.py`; verify-replay 38083686082 (policy agrees with chain 12/12) |
| G1 stage evidence | migration `035_build_stage_results.sql` (immutable, idempotent per build+artifact+policy+check); worker + replay persist rows; `OMNI_SOURCE_COMMIT` written at deploy | replay wrote 11 rows/version on Neon |
| G1 state machine | `build_state.PHASES`, `update_phase` forward-only while RUNNING | `tests/test_build_state_machine.py` |
| G1 repair | consistency gate (ON), round snapshots to R2, progress-aware rollback, repair sees main file | gate-replay 38083647077: 0 blocking on 55 versions |
| G2 visual QA | `omni_prod/visual_qa.py`: desktop 1440x900 + mobile 390x844 DOM audit + JPEG screenshots; layout rules (no_mobile_viewport, h_overflow, offscreen_control, overlap, broken_image) enforced by default (0 false positives on stored products); contrast/labels advisory | real Chromium tests on fixtures; verify-replay 38083686082 (+ screenshots artifact) |
| G3 cost truth | write-ahead attempt ledger (in-flight call = UNKNOWN cost bounded by authorization), Gemini thinking tokens metered, `omni_prod/economics_report.py` + workflow stage `economics` | economics run 38083624196; `tests/test_actual_cost_settlement.py` |

## release_policy.py — state and wiring
- Called in `worker_tasks._run_live_build_job` right after `evaluate_release_gates` via `release_quality_report(...)`; if mandatory checks block and `enforcement_mode()=='enforce'` → build FAILED `release_policy_failed`; report stored in `evidence_json.quality_report` and in `build_stage_results` (`persist_quality_report`).
- Inputs come from executor evidence: consistency gate, preview smoke (`last_smoke`), behaviour (`last_report`), browser probe (`last_probe`), visual QA (`last_visual`, advisory), product review (`reviews`), quality, security, rights.
- Agent recorder: quality_gate_agent SUCCEEDED only when report decision READY; it is the only verifier of coding/repair agents.
- Not yet: requirement coverage against an approved contract (the contract floor is a generic template that contradicts approved scope, e.g. demands auth for "no login") — needs a product decision.

## Tests
- Local (no fastapi/boto3 here): last full run 1167 passed, 56 skipped, 9 failed + 14 errors = baseline, all `ModuleNotFoundError fastapi/boto3/botocore` (environment-only); regression guardian 0 problems.
- CI `v24-ci` (Python 3.12, pinned deps): green on every merged commit up to `67a0765` (run 38083044235).
- Real server (free): free checks 18/18 (38083312245); gate-replay (38083647077); verify-replay (38083686082); economics (38083624196); spend-audit (38083350856).
- NOT run: any paid build since `039574f` (budget policy) → the 10-build Golden E2E acceptance gate (≥90%) is NOT RUN; crash run on current code; backup/restore on 035 schema.

## Partial / not done
- The last local change (evidence registry refresh: `omni_prod/agent_os/evidence.py`, `skills.py`, `truth_matrix.py`) was written but `python -m omni_prod.agent_os.audit --write` could NOT be re-run (tool outage) → `AGENT_OS_REGISTRY.json`, `TRUTH_MATRIX.json` and matrices may be out of date with these sources; CI test `test_committed_registry_is_current_and_not_inflated` / truth-matrix test may fail until regenerated. **First action: run the regeneration commands below and commit.**
- Requirement coverage vs approved contract (G0 finding #9), independent reviewer (#10, provider credits), preview acceptance shown in UI (#11), unwired modules (#12), `/api/status` claims (#13).
- Performance budgets, generated-app auth, automation, games, media: NOT_IMPLEMENTED/BLOCKED.

## Exact commands to continue
```bash
git fetch origin && git checkout claude/g0-baseline-2026-10-09 && git pull --ff-only
python -m omni_prod.registry_audit --write
python -m omni_prod.agent_os.audit --write      # regenerates AGENT_OS_REGISTRY.json, TRUTH_MATRIX.json, matrices
python -m pytest -q                              # needs requirements-production.txt + requirements-test.txt
python -m omni_prod.agent_os.meta regression pytest-report.xml   # after: pytest --junitxml=pytest-report.xml
git add -A && git commit -m "Regenerate registries" && git push
# integrate: only after green CI, fast-forward (no force):
git push origin HEAD:milestone/pre-staging-2026-10-05
# free real-server checks (one at a time; the workflow concurrency group cancels pending runs):
gh workflow run postdeploy-checks.yml --ref milestone/pre-staging-2026-10-05 -f stage=free
gh workflow run postdeploy-checks.yml --ref milestone/pre-staging-2026-10-05 -f stage=verify-replay -f versions=12
```

## Next step
1. Regenerate registries (above), commit, CI, fast-forward to the active branch.
2. Founder: reconcile the Gemini bill (Google AI Studio billing) → decide paid budget → run ≥10 diverse Golden E2E builds (`-f stage=paid -f max_usd=0.15`, one at a time) to measure the ≥90% gate.
3. Founder decision: enforce contrast/label rules (3 of 5 working products have real WCAG defects).
4. Then: approved acceptance criteria shown to and approved by the customer (finding #9).

## Risks / blockers
- Budget: QA guard counts $4.527; conservative upper bound of real spend ≈ $8.27 of $10 (pre-fix Gemini thinking under-count) — unverified until invoice reconciliation (founder access).
- OpenAI (429 no credits) and Anthropic (400 low balance): no second provider; reviewer may equal author.
- Release policy now fails builds whose checks did not run; real-build pass rate under the new policy is unmeasured (no paid run).
- Historic success rate from the ledger: 11/32 builds READY (34%); 53% of spend went to failed builds.

## Avoiding conflicts (Copilot / ChatGPT / Claude)
- Do not push directly to `milestone/pre-staging-2026-10-05`; work on your own branch (`copilot/...`, `chatgpt/...`) and open a PR into the active branch; merge only fast-forward after green CI and when no build is running.
- Never hand-edit generated files (`AGENT_OS_REGISTRY.json`, `TRUTH_MATRIX.json`, `docs/AGENT_OS_REGISTRY.md`, `docs/TRUTH_MATRIX.md`, `*_MATRIX.json`, `omni_prod/registry_evidence_lock.json`, `infra/staging/bootstrap_neon_empty.sql`) — regenerate with the commands above.
- New migrations: next free number is `036`; additive only; regenerate the Neon bootstrap with `python tools/generate_neon_bootstrap.py`.
- Evidence (`omni_prod/agent_os/evidence.py`) may only reference real runs with their commit; never mark LIVE (no production).
- No paid runs, no production deploy, no force push without founder approval.
