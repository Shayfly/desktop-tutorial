# PR #244 — legacy budget compatibility evidence (2026-11-04)

## Read-only database inspection

Queried Neon project `aged-tree-68103298` (148ai-db-v2) and `quiet-hat-61884615` (148ai-db). Query:

```sql
SELECT status, count(*) AS jobs,
       count(*) FILTER (
         WHERE NOT (COALESCE(evidence_json->'economics_quote'->'components', '{}'::jsonb)
                    ? 'llm_maximum_usd')
       ) AS missing_budget
FROM build_jobs
GROUP BY status ORDER BY status;
```

- 148ai-db-v2: cancelled=2 (missing budget=2), failed=4 (missing=0).
- 148ai-db: cancelled=27 (missing=0), failed=38 (missing=1), ready=11 (missing=0).
- Neither inspected database had queued/running jobs at query time.
- These are *two inspected databases*, not proof that the currently deployed worker uses either database. Worker env / other databases / outbox queues not verified. No customer data or IDs reproduced.

## Compatibility decision

The patch blocks all legacy jobs without a durable `llm_maximum_usd` before paid generation. Existing finished jobs are unaffected, but a queued/recovered legacy job elsewhere could fail closed. Do **not** silently infer a missing authorization from the worker's environment.

### Safe reauthorization proposal (not executed)

1. Identify active worker DB and all queued/running/retryable jobs, plus outbox entries; inventory build IDs and quote state securely.
2. Pause claim/dispatch for affected legacy jobs (do not cancel or double-reserve).
3. Reconstruct the cost quote using the original account, plan, project, contract, cost class, and current pricing. Obtain explicit customer approval for the new authorization; never treat an old absent quote as approval.
4. Persist a new immutable authorization/quote and its approval reference transactionally, reconcile existing reservation and idempotency, and only then requeue. If authorization cannot be established, leave the job blocked and release unused reservation through the existing exactly-once path.
5. Verify zero extra provider calls, no duplicate credit reservation, and exactly-once settlement/release. Avoid writing the authorization directly into evidence JSON without the transactional ledger.

## CI on head 5cc56ccef3e3fe3d279c35e29962317605f19321

- PASS: V28 Verify 41918911886; intake and architecture 41918911938.
- FAIL: V11 Overlay CI 41918912026; intake-budget-pg 41918911901; v24-ci 41918911941.
- Vercel commit status: success; not a substitute for CI.
- Failure signatures: `PermissionError: model_budget_missing` in legacy build test fixtures, `409 != 402` and expected-None approval tests. These are genuine behavior/fixture compatibility failures, not proven flakes.

## Release gate

HOLD: update affected test fixtures to carry an authorized quote and explicit approval where appropriate; preserve negative tests for missing budget/approval. Confirm deployed worker DB and outbox, run all CI to green, then request independent review. Do not merge or deploy until all conditions are met.

## Fixture remediation — follow-up

- `tests/test_m5_build_economics.py`: positive durable-build route fixture carries an approved approval_id and consumed-approval mock. Negative `test_build_without_an_approval_is_refused` explicitly omits it; the test's 409 assertion is unchanged.
- `tests/test_m3_preview_logic.py`: shared worker request fixture carries a positive LLM maximum; the gateway-shaped fixture now exposes `bind_budget`, preserving its pre-recorded model-spend ledger. This fixture has no CostClass to avoid changing unrelated historical spend assertions; dedicated CostClass negative tests remain in `tests/test_worker_budget_binding.py`.
- Earlier head `ac110438a90f674860a41064eea86575baef5abd` still had V11 Overlay CI, intake-budget-pg and v24-ci failures. Latest changes require a fresh CI run.
- Remaining worker fixtures in other test modules may need the same explicit authorization; **not verified as fixed**.
- Active Oracle/worker database configuration cannot be established from the two Neon project queries. **Worker identity: NO ACCESS / NOT VERIFIED**. The database inventory is not a substitute for worker runtime environment or Redis/RQ queue inspection.
- No merge and no independent review request before CI green and worker verification.
