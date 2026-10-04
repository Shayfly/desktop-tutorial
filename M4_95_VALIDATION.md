# M4.95 Validation Evidence

## Baseline

- Canonical M4.9 commit: `aa1e983e2283358f47896c3c8ad1527198f6db3e`
- Execution branch: `milestone/m4.95-capability-foundation-v2`
- Baseline run date: 2026-10-04 (UTC timestamp captured in `.superpowers/sdd/m4_95_v2/baseline_meta.txt`)
- Python: `3.13.5`

### Full non-live regression

Command:

```bash
python -m unittest discover -s tests -v
```

Fresh result before M4.95 production-code changes:

```text
Ran 518 tests in 3.975s
OK (skipped=47)
```

The skipped tests are environment-gated live proofs and are not rewritten as passes.

### M4.9 clean-room and lifecycle probes

Commands:

```bash
python -m unittest tests.test_m49_clean_room -v
python -m unittest tests.test_m49_lifecycle -v
```

Fresh result:

- `test_clean_room_real_pipeline_reaches_genuine_ready_for_review`: `SKIPPED` — `psycopg` not importable in this execution environment.
- `test_A_through_E_accept_verify_rollback_verify`: `SKIPPED` — `psycopg` not importable in this execution environment.

This is recorded as **NOT CONFIGURED in this execution environment**, not as a failure and not as live-production evidence.

## M4.95 completion rule

A task is complete only after its required focused tests pass, the project regression suite is re-run when the task changes shared behavior, and the commit/ruling is recorded in the execution ledger. External/live capabilities remain `NOT_CONFIGURED` or `BLOCKED` until exercised against the named live dependency.

## Final M4.95 V2 verification

Verification date: 2026-10-04.

### Golden provider-neutral vertical slice

Focused acceptance coverage proves the M4.95 architecture can take a 3D game intent through capability planning and dependency closure, execute heterogeneous external-style capabilities through the universal provider contract, structurally verify PNG/GLB/WAV artifacts, persist usage/cost evidence, and export materialization provenance without claiming a commercial provider is live.

Command group included:

```bash
python -m unittest \
  tests.test_m495_golden_acceptance \
  tests.test_m495_capability_executor.CapabilityExecutorTests.test_restart_resumes_persisted_provider_task_without_duplicate_submit \
  tests.test_m4_worker.RunModificationJobTests.test_duplicate_delivery_is_a_noop \
  tests.test_m495_provider_router.ProviderQuotaCircuitTests.test_429_opens_provider_capability_specific_distributed_cooldown \
  tests.test_m495_capability_verification \
  tests.test_m495_truth_readiness_api \
  tests.test_m495_truth_lock -v
```

Fresh focused result after the final truth-lock correction: `22` tests run, `OK`.

The golden provider is deliberately fake/in-process. This is evidence for the provider-neutral orchestration contract, artifact verification, durable execution identity, and evidence flow. It is **not** evidence that Tripo, Meshy, Runway, ElevenLabs, or another commercial media provider is configured or live.

### Failure/recovery gates proven locally

- Crash/restart: a persisted `provider_task_id` is resumed without duplicate submit.
- Duplicate delivery: a repeated worker delivery is a no-op at the existing durable build transition boundary.
- Provider quota: HTTP 429 opens a provider+capability-scoped distributed cooldown path.
- Large artifacts: verification hashes incrementally, enforces size ceilings, detects corruption, and uses streaming file download paths rather than unbounded reads.
- Cross-tenant evidence: build capability truth denies another tenant and redacts secret-bearing evidence.
- Machine truth: capabilities, skills, agents, provider definitions, provider price truth, and cost rules share one SHA-256 fingerprint; generated files and `STATUS.md` drift fail the truth-lock check.
- Paid-provider durability: a paid adapter must expose durable idempotency **and** durable result retrieval; the synchronous compatibility media adapter is fail-closed for paid external execution because its result cache is process-local.
- Large-artifact transport: provider payloads may be file-backed and flow through streaming verification plus artifact-store `put_file` without a required in-memory byte materialization.
- Fake-provider HTTP integration: a localhost HTTP server returned real base64 media bytes through `HTTPMediaGateway` -> provider adapter -> capability executor -> structural verification -> local artifact storage -> durable usage/cost evidence.

### Final full regression

Command:

```bash
python -m unittest discover -s tests -v
```

Fresh result after Tasks 1–16, the final truth-lock changes, paid-provider durability hardening, file-backed large-artifact streaming, and the localhost HTTP fake-provider integration:

```text
Ran 633 tests in 5.526s
OK (skipped=47)
```

No failing tests were observed in this run.

### Additional release probes

- `python -m omni_prod.truth_lock --check` -> exit `0`.
- `python -m unittest tests.test_m49_clean_room -v` -> `OK (skipped=1)` because `psycopg` is unavailable here.
- `python -m unittest tests.test_m49_lifecycle -v` -> `OK (skipped=1)` for the same live-Postgres dependency.
- `OMNI_RUN_LIVE_SANDBOX=1 python -m unittest tests.integration.test_live_sandbox_security -v` -> `OK (skipped=3)` because this environment has no isolated Docker host.
- Tracked non-test/non-doc source secret-shape scan found no OpenAI-style `sk-...`, Google `AIza...`, GitHub `ghp_...`, or private-key-header matches.

### M4.95 truth boundary

M4.95 V2 is **verified locally as a provider-neutral capability foundation**. It does not claim public production deployment or live commercial media/3D providers. Live Postgres/Redis/S3, isolated Docker sandbox proofs, commercial provider credentials/contracts, and mobile signing remain environment/external gates and must keep truthful `NOT_CONFIGURED`/`BLOCKED` status until exercised.
