# Verification coverage map (Continuous Verification P0.1, 2026-10-11)

Audit of what already verifies 148AI before building anything new. Derived from
the repository (`omni_prod/`, `tests/`, `.github/workflows/`) at branch
`claude/wave-a-fix-conversation-schema-2026-10-11`. "Runs where" means what
actually invokes the check today, not what a contract promises.

## A. Generated products (what customers build) — well covered

| Check | Module | Runs where | Blocks release? | Tests |
|---|---|---|---|---|
| Sandboxed build/compile | `sandbox.py`, `sandbox_executor.py`, `remote_sandbox.py` | worker build job | yes | 4 files |
| Cross-file consistency | `consistency_gate.py` | worker, gate-replay | yes (ON) | yes |
| Preview HTTP smoke | `preview_smoke.py` | worker | yes (mandatory in release policy) | yes |
| Behaviour acceptance (web SaaS) | `behavior_acceptance.py`, `web_saas_acceptance.py` | worker, postdeploy-checks | yes | 7 refs |
| Real-browser probe | `browser_probe.py` | worker host (deploy-worker) | yes | yes |
| Visual QA desktop+mobile | `visual_qa.py` | worker | layout rules yes; contrast/labels advisory | yes |
| Security tests | `security_testing.py`, `web_security.py` | worker, gate-replay | yes | 2 refs |
| Product review (model) | `product_review.py` | worker | advisory when reviewer = author | 3 refs |
| Release decision | `release_policy.py` (`quality-report/1`) | worker after gates | yes (`enforce`) | yes |
| Stored-version replay | `gate_replay.py` | postdeploy-checks (manual dispatch) | report only | none direct |
| Failure injection | `tests/test_failure_injection.py` | CI | n/a | 12 tests |

## B. The platform itself (148AI web app + API on Vercel) — the gap

| Check | Before 2026-10-11 | Now (this branch) |
|---|---|---|
| Unit/integration tests on push/PR | `v24-ci` (pytest, regression guardian, registry audit) | unchanged |
| Worker host after deploy | `postdeploy-checks stage=free` — manual dispatch, against the worker host at `127.0.0.1`, **not** the Vercel deployment | unchanged |
| Vercel deployment answers the core journey | **nothing** — "READY" in Vercel was the only signal | `deployment-verify` workflow on every `deployment_status` + `tools/deployment_verify.py` |
| Deployed commit = expected commit | nothing | `commit_sha` check (`/api/v28/deployment`) |
| Code vs database schema compatibility | nothing (migrations applied only by deploy-worker on the integration branch; branch Previews share the DB) | `schema_compatible` check + `omni_prod/schema_manifest.py` (drift test) |
| Auth denial / cross-user isolation on the deployment | unit tests only | `unauthenticated_denied`, `cross_user_isolation` against the real URL |
| Conversation endpoint degrades safely on old schema | crashed with 500 | 503 `conversation_not_ready` + guided fallback (`SchemaNotReadyTests`) |
| Canonical verdict across all verifiers | `quality-report/1` (builds only) | `verification-result/1` (`omni_prod/verification_contract.py`), maps quality reports onto it |

**Why the 2026-10-11 incident was not caught:** every existing check verifies
either generated products (A) or the worker host; nothing exercised the
Vercel-hosted API against its real database after deployment, and nothing
compared the code's required schema with the applied one.

## C. Still not covered (honest list)

- Golden E2E (10 paid builds) — NOT RUN, needs budget approval.
- Live AI conversation — not verified (no provider call made).
- `deployment-verify` on a protected Preview needs the repository secret
  `VERCEL_AUTOMATION_BYPASS_SECRET`; without it the verdict is BLOCKED (never VERIFIED).
- Repair loop over deployment failures, defect intelligence, dashboards,
  adversarial suite, requirement→test traceability (P0.5–P0.12) — NOT IMPLEMENTED.
- Automatic promotion block: the workflow produces a red check on the commit;
  Vercel promotion is not yet gated on it (needs Vercel "Deployment Checks"
  configuration by the founder, or a branch protection rule).
