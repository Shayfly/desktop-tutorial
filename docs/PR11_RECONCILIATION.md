# PR #11 reconciliation with the integration branch (2026-10-11)

Integration branch `milestone/pre-staging-2026-10-05` @ `2a2bba6` (PR #14 merged). PR #11 head before: `cdb9f47`. Reconciliation merge: `f5ecf28` (merge commit, no history rewrite).

## Why PR #11 was not mergeable
1. **Textual:** `STATUS.md` conflicted, because both branches prepended update sections. It was the only conflicting file.
2. **Semantic:** PR #11's `omni_prod/schema_manifest.py` pinned migration **036**, while PR #14 added **037**. After a merge, `test_manifest_matches_the_migration_files` would fail. Worse, `GET /api/v28/deployment` would have called a database *without* 037 "COMPATIBLE" with code that needs 037 for paid intake.
3. **Duplication found while reconciling:** `postdeploy_checks.stage_free` had its own migration check (max applied version vs. a glob of `infra/postgres/*.sql`), while PR #11 added a second rule for the Vercel side.

## Existing components reused (nothing parallel introduced)
| Need | Reused |
|---|---|
| migration discovery / application | `omni_prod/migrations.py`, `migration_runner.py`, `python -m omni_prod.migrate` |
| worker-host post-deploy check | `postdeploy_checks.stage_free` unchanged (see "Deliberately not changed") |
| build release decision | `release_policy.py` (`quality-report/1`) unchanged; `verification_contract.from_quality_report` only maps it |
| post-deployment verifier | one tool: `tools/deployment_verify.py`; PR #9's unique checks moved into it instead of adding `tools/qa_postdeploy/` |
| conversation / intake | PR #14 modules untouched |

## Minimal changes in `f5ecf28`
- `STATUS.md`: both histories kept, newest first.
- `schema_manifest.py`:
  - `REQUIRED_MIGRATION = 37` and `EXPECTED_VERSIONS` now include 37.
  - New pure `compatibility(applied)` that reports `missing` and `unknown_applied` (DB ahead of code).
- `investor_app._schema_compatibility()` now uses `compatibility()`.
- `tools/deployment_verify.py` + `DEPLOYMENT_REQUIRED_CHECKS`:
  - New mandatory check `session_identity`: `GET /api/v28/me` must resolve to exactly the synthetic user.
  - `conversation_persists` also requires the response contract keys.
  - Both come from PR #9.
- Tests: compatibility rule; PR #9 contract cases; the forged-evidence test now addresses checks by name, not position (the old index broke when a check was added).

## Deliberately not changed
`postdeploy_checks.stage_free` keeps its own check (max applied version == newest `.sql` file). I first rewired it to `compatibility()`. The evidence lock then (correctly) downgraded every agent whose REAL_SERVER_VERIFIED status rests on postdeploy-checks run 38083312245 to IMPLEMENTED, because that verified file changed (`test_committed_registry_is_current_and_not_inflated` failed). Losing verified status for a refactor is not a minimal change, so I reverted it.

Follow-up: switch `stage_free` to `compatibility()` *together with* a fresh `postdeploy-checks stage=free` run after the merge (free, worker host), then regenerate the registry. Both rules agree today, since the newest file is 037 and a missing middle version cannot occur through the runner.

## PR #9 vs PR #11
| Capability | PR #9 | PR #11 | Decision |
|---|---|---|---|
| No redirects, origin/allowlist validation, https, no proxies, size cap, classified network errors | yes | yes (adopted from #9 in `a35e79e`) | overlap: already in #11 |
| Nested FastAPI `detail.error` classification (`conversation_not_ready` → migration) | yes | yes | overlap |
| Full 40-hex SHA + trusted deployment SHA | yes | yes | overlap |
| Verdict model | own (`148ai-postdeploy-check/1`) | canonical `verification-result/1` with promotion gate, recomputation, required-check policy | keep #11: one vocabulary |
| Authenticated journey (register → project → conversation → persistence → memory) | no (GET only, needs a pre-provisioned token and project) | yes | #11 only |
| Anonymous denial, cross-user isolation | no | yes | #11 only |
| Schema/migration compatibility | no | yes | #11 only |
| `/api/v28/me` identity contract | yes | **added** (`session_identity`) | integrated |
| Conversation response contract keys | yes | **added** | integrated |
| Public `/api/v28/pricing` check | yes | no | not integrated: not a critical journey; low value |
| Read-only SAFE mode with a pre-provisioned token (usable on Production) | yes | no (#11 refuses Production writes → BLOCKED) | **integration requirement, not built:** needs a production synthetic account + token secret + founder authorization. When approved, add a `--read-only` mode to the existing tool (same client and contract), not a second package. |
| 37 loopback tests | yes | test shapes adopted; #11 file now covers more | — |

Recommendation: **close PR #9 without merging** (superseded; its unique checks are in #11). Do not merge it into #11's branch: it would add a second verifier and a second verdict vocabulary.

## Evidence
- Real server, merged code `f5ecf28` (FastAPI + PostgreSQL 16, synthetic users, `$0`):
  - DB at 036 → `FAILED`; only `schema_compatible` fails (`missing=[37]`), the other 10 checks pass, exit 1.
  - After `python -m omni_prod.migrate` (applied `[37]`) → `VERIFIED`, 11/11, exit 0.
  - Files: `docs/evidence/verification/merged_db036_vs_code037.json`, `merged_db037_verified.json`.
- Affected suites (deployment verification, conversation, PR #14 intake incl. real-PG/Redis concurrency, release policy): 175 passed, 0 skipped.
