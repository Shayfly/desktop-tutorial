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
