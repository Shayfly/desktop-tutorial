# 148AI Post-Deployment Verification — PDV-001

Status: **CANDIDATE / locally tested only**, not wired into the release gate and not tested on a deployed 148AI server.

This standard-library Python 3.11+ package verifies read-only HTTP/API contracts against explicitly approved application origins. It was independently corrected after a Gemini-generated prototype. It does **not** replace `omni_prod/release_policy.py`, `omni_prod/visual_qa.py`, any agent registry, the existing Postgres migration runner, or the active CI/Worker.

## Exact source-of-truth contracts

From `omni_prod/investor_app.py` on branch `claude/wave-a-fix-conversation-schema-2026-10-11` at `b6a99c1`:

- GET `/api/v28/pricing`: JSON object
- GET `/api/v28/me`: `id`, `email`, `created_at`, `subscription`
- GET `/api/v28/projects`: `{ "projects": [...] }`
- GET `/api/v28/projects/{project_id}/conversation`: `messages` array + `discovery`, `plan`, `plan_id`, `interpreter`
- GET `/api/v28/projects/{project_id}/memory`: JSON object
- GET `/api/v28/projects/{project_id}/discovery`: JSON object (optional check)

FastAPI emits HTTPException payloads as `{ "detail": { "error": "conversation_not_ready", "missing_migration": "036_intelligence_plane" } }`, NOT as Gemini's fabricated top-level `error_code`. The package accepts the true nested envelope and the older top-level shape for compatibility.

An HTTP 503 with missing migration is **BLOCKED**, not VERIFIED. The SPA error handling/fallback is independent and does not prove the conversation backend is usable.

## API integration

```python
from tools.qa_postdeploy import RunConfig, Verdict, run_postdeploy_checks

result = run_postdeploy_checks(RunConfig(
    base_url="https://YOUR-EXACT-STAGING-HOST.vercel.app",
    allowed_hosts=("YOUR-EXACT-STAGING-HOST.vercel.app",),
    target_environment="preview",
    bearer_token=token_from_authorized_test_account,
    project_id="preapproved_test_project_id",
    expected_commit_sha=commit_sha_from_deployment_pipeline,
    trusted_observed_commit_sha=observed_sha_from_authenticated_vercel_metadata,
))
assert result.verdict == Verdict.VERIFIED, result.blocking_reasons
```

`trusted_observed_commit_sha` MUST come from a trusted, authenticated deployment-system metadata result. Never infer it from response HTML or unverified HTTP headers. If `expected_commit_sha` is specified but trusted observed SHA is unknown or mismatched, verdict is BLOCKED. The value is caller-attested, not independently fetched by PDV-001; the deploy workflow must establish trust.

The package currently runs six GET checks. All except discovery are mandatory. Missing token, missing project ID or unknown commit attestation is *not* a passing check. Any mandatory FAIL makes final verdict FAILED; otherwise any mandatory BLOCKED/NOT_RUN makes the verdict BLOCKED; only a complete mandatory PASS set yields VERIFIED.

The package does **not** write to the release policy, Postgres or any environment; the release-job adapter must use `result.to_dict()` and map terminal verdicts to the established quality evidence system only after integration tests. A successful PDV pass is necessary for covered API functionality, **not sufficient to call the whole 148AI system or a customer product ready**.

## CLI

```bash
export QA_BEARER_TOKEN="<test-account-only-token>"
python -m tools.qa_postdeploy.cli \
  --base-url https://YOUR-EXACT-STAGING-HOST.vercel.app \
  --allowed-host YOUR-EXACT-STAGING-HOST.vercel.app \
  --environment preview \
  --project-id preapproved_project_id \
  --expected-sha <40-character-commit-sha> \
  --trusted-observed-sha <40-character-sha-from-trusted-deployment-API> \
  --json-output qa_postdeploy.json
```

Local HTTP testing uses `http://127.0.0.1:PORT` (or localhost). Non-loopback must use HTTPS and appear in `--allowed-host`. Only an origin URL, without path/query/fragment/credentials, is accepted. HTTP redirects are never followed, and standard Python HTTPS certificate validation remains enabled. System proxy environment variables are intentionally not used. URLs must be operator-provided authorized deployments; do not feed untrusted customer-supplied URLs to the verifier.

**Exit status:** 0 VERIFIED; 1 FAILED; 2 BLOCKED or NOT_RUN; 3 invalid configuration.

**CANARY is reserved and deliberately refused** in this iteration (exit 3). No automatic registration, project creation, POST, payment, model call, production write, or paid test is implemented.

## Test locally

```bash
python -m unittest discover -s tests -p 'test_qa_postdeploy.py' -v
```

The tests launch a real local loopback ThreadingHTTPServer and make real socket requests. Fixtures simulate specific HTTP responses; they do not imply a live Vercel or worker execution. The local candidate passed **37 tests** on Python 3.13; language features are compatible with Python 3.11+. No external dependencies.

## Limitations, known risks and required next work

1. Read-only GET checks only: no complete multi-turn POST chat, login lifecycle, build-worker E2E, actual browser QA or actual migration verification. Those must be executed by separate approved adapters.
2. The verifier checks that the conversation response matches a minimal structure; it does not prove persistence, correct authorization, correct AI answers or usable product features.
3. Commit verification relies on trusted metadata injected by the deployment system; do not claim real SHA evidence until integrated into Vercel/Worker CI.
4. Protected Vercel deployments may return 403; origin is not reliably identifiable. The result is BLOCKED (`HTTP_403`), not a false claim of app authorization failure.
5. The exact-host allowlist and no-redirect policy restrict accidental SSRF; a compromised trusted hostname or DNS rebinding is outside the guarantees of the standard `urllib` transport. Execute only on authorized network boundaries.
6. Tests do not contain real secrets, do not run paid AI models and do not mutate customer state.
7. Onboarding to 148AI must happen in a new integration PR after real stack tests and a reviewed CI deployment-attestation contract; do not merge this candidate directly to the active integration branch.
8. The repo's existing `release_policy.py` and durable `build_stage_results` use different stage/check schemas; write a minimal adapter only after inspecting the full consuming code, retaining fail-closed policy.
9. Document and test ephemeral staging test-account token provisioning through an authorized secrets store, with no tokens emitted to logs or artifacts.
10. `RunConfig` intentionally permits `trusted_observed_commit_sha` as an integration input and **cannot validate the trustworthiness of its source**; CI controls must own the provenance.

## Source comparison and corrections

Gemini prototype defects corrected:
- FastAPI `detail.error` migration envelope mismatch.
- No explicit remote HTTPS host allowlist; arbitrary HTTP targets allowed.
- Redirect/downgrade ambiguity and unsafe URL path/fragment handling.
- Raw exception strings could disclose sensitive data.
- Entirely unimplemented CANARY mode falsely selectable.
- Expected SHA did not block VERIFIED despite no observed SHA evidence.
- Missing/null required checks could be mistaken for success in downstream consumers.
- Claimed test results were not independently verifiable; this candidate has 37 independently executed local tests.
