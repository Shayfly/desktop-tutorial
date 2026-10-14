# Security review — `tools/deployment_verify.py` (PR #11), 2026-10-11

Scope: the post-deployment verifier and its workflow `.github/workflows/deployment-verify.yml`.
The tool holds two secrets at runtime: the Vercel *Protection Bypass for
Automation* token (from an env var) and the synthetic users' session tokens.
Reviewer of record for the merge decision: independent (ChatGPT), per the founder's division of work.

## Findings on the version reviewed (`45f621c`, suite `deployment-verify/2`)

| # | Severity | Finding | Evidence | Fixed by |
|---|---|---|---|---|
| 1 | **High** | Redirects were followed by urllib's default handler, **with** `Authorization: Bearer …` and `x-vercel-protection-bypass` copied to the redirect target (any host). | Reproduced: a 302 to a second local server delivered both headers to it. | `_NoRedirect` (never follows, same-origin included); tests `test_cross_origin_redirect_never_receives_secrets`, `test_redirect_after_login_does_not_forward_the_bearer_token`, `test_same_origin_redirect_is_not_followed` |
| 2 | **High** | No target validation: any scheme/host/IP (incl. `file://`, private ranges, cloud metadata `169.254.169.254`) — SSRF, and the bypass secret would be sent to whatever URL was given. | Code inspection. | `validate_target` (origin only, https except loopback, no IP literals, no credentials/path/query/fragment, exact host or `-`/`.`-anchored suffix allowlist) + `resolve_public` (all resolved addresses must be global); tests `test_target_validation_rejects_ssrf_shapes`, `test_unresolvable_or_private_targets_are_blocked` |
| 3 | Medium | A cookie jar stored and replayed server cookies (unneeded; cross-request state). | Code inspection. | Removed; `test_cookies_are_never_stored_or_sent` |
| 4 | Medium | Network errors after the first request raised exceptions → no result file, the workflow reported "no result" instead of a verdict. | Code inspection. | Every request returns a classified outcome (TIMEOUT, DNS_FAILURE, TLS_FAILURE, CONNECTION_FAILURE, REDIRECT_BLOCKED, RESPONSE_TOO_LARGE, INVALID_JSON); `test_network_failures_mid_journey_produce_a_result_not_a_crash` |
| 5 | Medium | Unbounded response bodies (memory); server error text (`detail`) copied into evidence (could carry an echoed `Authorization` header or customer text). | Code inspection. | 1 MiB cap; evidence = status + whitelisted error codes only; final `_scrub` of all secrets; `test_secrets_only_go_to_the_target_and_never_into_evidence` (server echoes the bearer header) |
| 6 | Medium | Mandatory checks that were never reached were simply absent; correctness depended on decision-order details. | Code inspection. | Contract `required=`: a missing or downgraded required check ⇒ BLOCKED; tool always reports all 10 checks, unreached ones `NOT_RUN` with reason; tests `test_unreached_mandatory_checks_are_reported_not_run_and_block`, `test_contract_blocks_when_a_required_check_is_missing_or_optional` |
| 7 | Medium | SHA prefix match (`startswith`) accepted short/ambiguous SHAs. | Code inspection. | Full 40-hex SHA required; optional `--trusted-observed-sha` (deployment-system metadata) must also agree; tests `test_sha_must_be_full_and_well_formed`, `test_trusted_metadata_disagreeing_with_expected_sha_fails` |
| 8 | Medium | Synthetic writes would run against a production deployment. | Code inspection. | Refused unless `--allow-production-writes` (⇒ BLOCKED); workflow skips Production; `test_production_writes_refused_without_explicit_approval` |
| 9 | Low | Server-controlled project id inserted into request paths. | Code inspection. | Strict id format; `test_server_controlled_project_id_cannot_steer_requests` |
| 10 | Low | Environment proxies honoured (secrets could transit an env-configured proxy). | Code inspection. | `ProxyHandler({})` |
| 11 | Low | Workflow ran for any GitHub deployment event (anyone able to create a deployment could choose the URL). | Workflow inspection. | Runs only for `creator.login == 'vercel[bot]'` (confirmed on real run 38114225915) and the team suffix `-shayflys-projects.vercel.app` |

| 12 | Medium | Found on the first real run (38120874664): argparse treated the dash-leading suffix as an option and exited with no result file. | Real GitHub run. | `--allowed-host-suffix=…` in the workflow; argument errors produce a BLOCKED result (exit 3); CLI regression test |

## Independent review (ChatGPT, 2026-10-11 10:28) — contract findings

| # | Finding | Fix in `omni_prod/verification_contract.py` | Regression tests (`ReviewFindingTests`) |
|---|---|---|---|
| R1 | `may_promote` accepted a 12-character prefix match | promotion target must be bound (commit or artifact); commit = exact full 40-hex equality (case-insensitive), malformed SHAs refused on both sides | `test_forged_sha_prefixes_are_refused` (same 12-char prefix, 7/12/39/41 chars, non-hex, blank), `test_unbound_promotion_is_refused` |
| R2 | future-dated / missing timestamps, invalid TTL accepted | started/finished must be finite numbers, started <= finished <= now + 60 s skew, TTL int in (0, 7 days], now - finished <= TTL | `test_future_dated_and_malformed_timestamps_are_refused` (15 cases + skew/expiry boundaries) |
| R3 | mandatory NOT_APPLICABLE counted as satisfied | BLOCKED unless a versioned NA policy (`{'version': 'name/N', 'allowed': [...], 'reason': ...}`) names the check → VERIFIED_WITH_ADVISORIES with the policy version in the reason; malformed policies authorize nothing; `from_quality_report` fails closed too (release-policy/1 would call it READY) | `test_mandatory_not_applicable_blocks_without_policy`, `test_versioned_policy_authorizes_only_named_checks`, `test_malformed_policies_never_authorize`, `test_quality_report_mandatory_na_maps_fail_closed` |
| R+ | (added) stored verdict trusted as-is | `may_promote` recomputes the verdict from the stored checks, required list and NA policy; any mismatch or malformed check refuses | `test_forged_verdict_is_recomputed_and_refused` |

## Compared with PR #9 (PDV-001) — adopted / not adopted

Adopted: no-redirect handler, origin-only URL validation, https-unless-loopback, IP-literal ban, exact host allowlist, no proxies, response cap, error classification (incl. nested FastAPI `detail.error = conversation_not_ready` → `MIGRATION_NOT_APPLIED`), full-SHA requirement, trusted-metadata SHA, "secrets never in output", CLI exit codes (0/1/2/3), test shapes 14–25 and 27–33.

Added beyond PR #9: DNS resolution to public addresses only; suffix allowlist anchored on `-`/`.` (Vercel preview hosts are random); explicit required-check list in the canonical contract; production-write guard; scrub of echoed secrets; server-controlled id validation; workflow creator/environment gate; the authenticated journey (PR #9 is read-only GET and needs a pre-provisioned token and project).

Different on purpose: a 503 `conversation_not_ready` is **FAILED** here (the deployment is broken for users), BLOCKED in PR #9. Both stop promotion. A redirect on the first request is BLOCKED (could be platform SSO), later redirects FAIL.

Not adopted: separate package/`RunConfig` (kept in one tool + the existing canonical contract to avoid two verdict vocabularies).

## Residual risks (not fixed, stated honestly)

- DNS rebinding between `resolve_public` and the connection (urllib re-resolves). Mitigated by the host allowlist; full fix needs connecting to the vetted IP with SNI.
- `*.vercel.app` names are claimable by other Vercel teams; the suffix `-shayflys-projects.vercel.app` relies on Vercel reserving the team slug in generated hostnames. The `vercel[bot]` creator gate means the URL comes from Vercel itself.
- The app-reported SHA is self-reported; in CI the trusted binding is the GitHub deployment event (URL ↔ SHA from Vercel).
- Synthetic users/projects are written to the shared pre-staging DB on every Preview verification (no cleanup yet).

## Closure review (2026-10-11 ~11:00)

### C1. Promotion-gate bypasses found and fixed (were live on `5ad2ccc`)

Reproduced with hand-forged `verification-result/1` dicts (script equivalent to `ForgedEvidenceTests`):

| Forgery | On `5ad2ccc` | Now |
|---|---|---|
| A: evidence declares `required: []` and contains one passing check | **promotable** | refused: recomputed BLOCKED (required checks missing) |
| B: failing check marked NOT_APPLICABLE + evidence carries its own NA policy authorizing it | **promotable** | refused: the evidence's policy is ignored; only the caller's trusted policy counts |
| C: duplicate check name (passing mandatory copy + failing optional copy) | **promotable** | refused: duplicate check names ⇒ BLOCKED |

Fix: `may_promote(result, *, required, na_policy=None, …)` — `required` (a non-empty tuple, no default) and `na_policy` come from the caller's code (`DEPLOYMENT_REQUIRED_CHECKS`), never from the evidence; the verdict is recomputed under that policy and must be promotable **and** equal the stored verdict; `mandatory` must be literally `true`; duplicate names block. Tests: `ForgedEvidenceTests` (6) incl. a round trip of real tool output.

### C2. GitHub deployment event — trust binding (verified on run 38121979644)

| Source | Value |
|---|---|
| GitHub run (event `deployment_status`, actor `vercel[bot]`) | `head_sha` `5ad2cccc…26a6`, branch `claude/wave-a-fix-conversation-schema-2026-10-11` |
| Vercel API (deployments for that SHA) | exactly one: `dpl_B6def4hWWTkGVtz8hsxbgZagciQB`, `148aiv28-8dvvs6l5s-shayflys-projects.vercel.app` (matches the allowed suffix) |
| The deployment itself (`GET /api/v28/deployment`) | `source_commit` `5ad2cccc…26a6`, `environment` preview, schema COMPATIBLE (036) |

The URL↔SHA binding the workflow uses comes from the GitHub deployment that the Vercel app created; the job only runs when `deployment.creator.login == 'vercel[bot]'`, so a URL from any other deployment creator is never contacted.

### C3. Workflow permissions and secret boundaries

- `GITHUB_TOKEN`: `permissions: contents: read` only; checkout now `persist-credentials: false`.
- `VERCEL_AUTOMATION_BYPASS_SECRET` (not created yet): exposed only as an env var of the single "Verify deployment" step; sent only as a header to the validated origin (no redirects); never printed; result + annotations + uploaded artifact are scrubbed; GitHub log masking also applies.
- **Boundary to understand (residual):** a `deployment_status` run executes the workflow file *at the deployed commit*. Anyone who can make Vercel deploy a commit of this repo (push access, or a fork PR that Vercel builds) could change the workflow in that commit and read repo secrets. Today this equals the existing push-trigger exposure (repo is private, `v24-ci` etc. already run on push). It widens only if Vercel builds fork PRs: keep Vercel **Git Fork Protection** on (default) — not verifiable from here (settings API blocked by the session proxy). Stronger option when the secret is created: store it in a GitHub **Environment** used only by this job, and keep the bypass token scoped to this project (Vercel bypass tokens are per-project and revocable).
- Supply chain: actions are tag-pinned (`@v4`/`@v5`) like every other workflow in the repo; SHA pinning recommended repo-wide (could not resolve the action SHAs from this session).

### C4. DNS rebinding — decision

**Accepted residual risk for pre-staging**, not fixed in this PR. Reasoning: the target host must be a `*-shayflys-projects.vercel.app` name taken from a Vercel-created deployment; DNS for `vercel.app` is operated by Vercel; `resolve_public` refuses any non-public address at check time; the only secret at stake is a revocable, project-scoped bypass token for pre-staging Previews. Exploiting the gap requires control of `vercel.app` DNS.
**Minimal fix (proposed, required before the verifier is pointed at production or customer-supplied hosts):** connect to the vetted IP instead of re-resolving — a small `HTTPSConnection` subclass whose `connect()` does `socket.create_connection((vetted_ip, 443))` and `ssl_context.wrap_socket(sock, server_hostname=host)` (certificate still verified against the hostname), installed through a custom `HTTPSHandler`. ~30 lines + a loopback TLS test with a self-signed CA.

### C5. The single failing full-suite test

`tests/test_m4_acceptance.py::AcceptanceW::test_W_every_non_fastapi_test_module_passes` fails identically on the unchanged base `4cc9b91` and on the head (same assertion). Direct run of its nested command on the base: **exit 0, `Ran 1303 tests … OK (skipped=20)`**. Cause: local live-PostgreSQL tests leave `psycopg_pool` shutdown warnings after the `OK` line; the test reads only the last 200 characters. Environment-specific; passes in CI. Evidence: `docs/evidence/verification/baseline_failure_m4_acceptance_W.json`.
