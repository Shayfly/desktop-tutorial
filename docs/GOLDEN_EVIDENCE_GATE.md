# Golden E2E: executable four-part evidence gate

Implemented and verified locally: the stdlib-only checker, adversarial tests,
and a reusable CI job. Not yet verified live: a trusted collector producing
this bundle through the customer UI, real R2, hosted preview, and reconciled
costs. The reusable workflow is supplied, not yet called by a live producer.
The diagnostic `golden-rehearsal.yml` intentionally writes no customer project
or R2 artifact; a green rehearsal cannot substitute for this gate.

## Run it

```bash
python tools/verify_golden_evidence.py evidence/manifest.json \
  --run-id "$GITHUB_RUN_ID" --build-id "$BUILD_ID" --commit "$BUILT_COMMIT" \
  --max-cost-usd "$AUTHORIZED_GOLDEN_BUDGET_USD" \
  --max-elapsed-ms "$AUTHORIZED_GOLDEN_TIME_LIMIT_MS"
```

All identity and limit flags are required and supplied by the trusted runner,
not inferred from the evidence. Commit is a full lowercase 40-character SHA.
The checker writes one JSON object to stdout; exit 0 requires **all four PASS**.
Missing fields/files, malformed JSON, a mismatch, UNKNOWN cost, or an exceeded
ceiling cause exit 1. Invalid CLI syntax causes exit 2, also a failed run.
No network calls, customer changes, providers or product code execution occur.
When piping output, use `set -o pipefail`; otherwise `tee` can hide exit 1.

Every verdict contains `checks.input`, `checks.r2`, `checks.preview`, and
`checks.accounting`, each with a status and errors. Root manifest failure
produces all four FAIL. Unknown/unvalidated cost is explicitly
`cost_status: "UNKNOWN", actual_cost_usd: null`; never replaced with zero,
authorized spend, a projection, or a price estimate. Measured zero is valid
only with a complete, matching ledger. No rounding is applied to cost sums.
Timing is measured to integer milliseconds, including queue and repairs;
matching monotonic and UTC durations are required, not rounded seconds.

## Evidence bundle contract (v1)

All files live beneath the manifest directory. File references have **both**
`path` (relative POSIX path) and `sha256` (64 lowercase hex characters).
References must exist, be nonempty and match their digest. Absolute paths,
parent traversal, symlinks and files above 64 MiB are rejected. JSON objects
are limited to 2 MiB; duplicate keys and nonfinite numbers are rejected.
Larger products need a separately reviewed streaming format, not a bypass.

The manifest is an object containing all these fields:

| Field | Required value |
|---|---|
| `schema_version` | integer `1` |
| `run_id`, `build_id`, `commit` | exact match to independently supplied flags |
| `manual_steps` | integer `0`, not `false`, `"0"`, or omitted |
| `input`, `r2`, `preview`, `accounting` | reference to each separate JSON receipt |

Each receipt, including the ledger, repeats `run_id`, `build_id`, `commit`.
All timestamps use UTC with exactly milliseconds, e.g.
`2026-10-19T20:00:00.000Z`. All listed fields are mandatory; `{}`, a truthy
string, or a status alone is insufficient. The synthetic fixture in
`tests/test_golden_evidence_gate.py` is the full executable format example.
It is test data, not delivery evidence; do not upload it as a live artifact.

### 1. Hebrew input receipt

- `prompt`: nonempty text containing Hebrew letters.
- `channel`: `customer_ui` (a worker-only generation call is insufficient).
- `submitted_at`, `accepted_at`: ordered timestamps from the actual UI/build admission.
- `requirements`: nonempty list of `{id, text}` with unique acceptance IDs.
- `provider_request_ids`: nonempty unique IDs of every model request in the
  build, including retry and repair calls; match the model ledger entries.

### 2. R2 receipt

- `provider`: `cloudflare_r2`; nonempty `bucket`, `key`, `version_id`.
- `put_status`: 200/201/204; `get_status`: 200 from a separate readback.
- `written_at`, `readback_at`: ordered after input admission.
- `bytes_written`, `file_count`: integers matching the actual stored ZIP.
- `sha256`, `readback_sha256`: identical to the downloaded ZIP's hash.
- `artifact`: reference to the ZIP read back from R2 (not just the local
  file that was intended for upload). ZIP member CRCs are verified, at least
  two unique files required; unsafe paths and oversized expansion rejected.

### 3. Preview receipt

- `url`: HTTPS preview URL without embedded credentials; `http_status`: 200.
- `browser`: `playwright`; `status`: `PASS` from the trusted browser runner.
- `version_id`, `artifact_sha256`: match the R2 version and content.
- `opened_at`, `verified_at`: ordered after R2 readback.
- `checks`: exactly one `{acceptance_id, passed: true, detail}` for each
  approved requirement. Observations must be nonempty; HTTP 200 alone fails.
- `screenshot`: reference to nonempty PNG/JPEG bytes from that run. The gate
  checks the bytes/header/hash, not visual quality or image semantics.

### 4. Accounting/time receipt

- `currency`: `USD`; `cost_status`: `KNOWN`; `actual_cost_usd`: a nonnegative
  decimal **string**. No float, bool, exponent, NaN, null or missing cost.
- `elapsed_ms`: submission to browser verification, positive integer.
- `queue_ms`: admission minus submission, nonnegative integer.
- `started_monotonic_ns`, `finished_monotonic_ns`: same-process monotonic
  readings at the submission/verification boundaries. Their delta in ms
  must equal `elapsed_ms`, which must also equal the UTC timestamps' delta.
- `includes_retries`, `includes_repairs`: literal `true`.
- `ledger`: reference to complete, durable accounting export described below.

Ledger: identity, `complete: true`, and nonempty `entries`. Every entry has
`id`, `kind`, `actual_cost_usd`, `basis`, `source_id`. IDs and source IDs are
unique per event. `kind` must cover all of `model`, `compute`, `storage`, and
`egress`, including evidenced zero-cost events. `basis` is `measured` or
`reconciled`; estimates/authorized reserves are rejected. `source_id` binds
to the provider request or measured/reconciled resource-charge record.
Model source IDs exactly match input's provider request IDs. All entries
sum exactly to `actual_cost_usd`; no hidden missing components permitted.

## CI use (no manual evidence editing)

The trusted producer must upload the complete directory as the artifact
`golden-e2e-evidence` in the **same Actions run**, then call:

```yaml
golden-evidence:
  needs: golden-e2e-producer
  if: always()
  uses: ./.github/workflows/golden-evidence-gate.yml
  with:
    build_id: ${{ needs.golden-e2e-producer.outputs.build_id }}
    expected_commit: ${{ github.sha }}
    max_cost_usd: '0.50'      # Example only: set the authorized cap before execution.
    max_elapsed_ms: '900000' # Example only: set the authorized limit before execution.
```

The example job `golden-e2e-producer` does not yet exist in this change.
No producer, artifact or build ID means failure; do not substitute rehearsal
fields, create fake receipts, or add `continue-on-error` to the gate. Only
the download step tolerates a missing artifact so the checker can report all
four failures. The verdict is uploaded even when validation fails.

## Trust boundary and precise limits

This is an **evidence validator**, not a live E2E runner or cryptographic
attestation service. A hash proves consistency, not that an attacker really
called R2 or opened a browser. A trustworthy collector must run outside the
generated sandbox, retain source API responses/browser traces/usage events,
bind approved requirements and the exact built SHA, and own evidence files
that generated code cannot overwrite. The producer is responsible for
complete attempt coverage, honest `manual_steps: 0`, and authentic receipts.
Do not accept bundles authored by the product/LLM or arbitrary PR code as
production proof. Later reconciliation may be necessary before accounting
can truthfully produce KNOWN. Until then, this gate fails as requested.

## Validation

```bash
python -m unittest -v tests.test_golden_evidence_gate
python tools/redteam_verification_boundaries.py
```

The second command is an adversarial diagnostic: exit 1 means it reproduced
boundary violations in the existing implementation. Its injected outputs
are synthetic and are not Golden E2E evidence.
