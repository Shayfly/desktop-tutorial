# QStash scheduler connector — staging checkpoint, 2026-10-06

## Configuration
The founder saved these variables in Vercel project 148aiv28, Preview only:

| Key | Type |
|---|---|
| QSTASH_URL | Config |
| QSTASH_TOKEN | Secret |
| QSTASH_CURRENT_SIGNING_KEY | Secret |
| QSTASH_NEXT_SIGNING_KEY | Secret |

EU base URL: `https://qstash-eu-central-1.upstash.io`.

The managed profile selects QStash when QSTASH_URL is present, unless
OMNI_GENAPP_SCHEDULER_PROVIDER explicitly selects another provider. The scheduler
token defaults to `env:QSTASH_TOKEN`. Existing generic_http deployments without
QSTASH_URL keep their prior configuration and behavior. Explicit provider
selection is available; parent credentials remain trusted-server-only.

## Implemented
- REST schedule create/update with a caller-supplied ID, get and idempotent cancel.
- One-time publish with a caller-supplied deduplication ID.
- Explicit operator-controlled destination allowlist; no caller-supplied API origin.
- No redirect following; fixed trusted API origins; bounded timeout/retries,
  payload/response sizes and safe exceptions without provider response bodies.
- JWT HS256 verification using current/next signing keys, issuer, exact destination,
  body digest, timestamps and token ID.
- Verification requires an injected durable atomic replay-claim function.
  No process-local set is used in the production module.
- Standard QStash variables are recognized by static readiness as PARTIAL.
  A successful read-only schedules API check does not create a LIVE binding.
  QStash binding remains BLOCKED until authenticated app delivery is proven.

## Integration boundary and remaining work
This is the provider connector, not a completed generated-app scheduling system.

Before live generated-app use, implement:
1. Authenticated, tenant-scoped schedule create/cancel API with durable owned
   schedule records and spend/rate limits. A deterministic provider ID is not
   sufficient tenant authorization.
2. A trusted control-plane delivery receiver that validates QStash signatures,
   validates project/environment ownership and uses a durable transactional inbox.
3. Delivery-side duplicate suppression by provider message ID, durable work state,
   crash recovery and retries. JWT jti protection alone does not guarantee exactly
   once business effects. A naive claim-before-effect handler can lose work on crash.
4. Gateway signing of generated-app callbacks with each app's own signing secret.
   Never distribute QSTASH_TOKEN or account-wide QStash signing keys to apps.
5. Explicit URL policy for approved generated destinations, with SSRF protection.
   The low-level allowlist must be built from trusted deployment records, not
   untrusted request fields. The provider performs outbound delivery later.
6. Real create -> trigger -> verified receipt -> retry -> cancel proof.
   Schedule administration and configuration presence do not establish LIVE.

No new public unauthenticated route, billing bypass or automatic paid call is
introduced by this change. It does not remove the other M5 build/cost gates.
Legacy generic_http health-based LIVE behavior is pre-existing and remains an
audit item; this change specifically prevents that claim for QStash.

## Verification
Unit/transport tests:
```bash
python -m pytest -q tests/test_qstash_scheduler.py tests/test_m5_managed_web_saas_profile.py
```
Full existing CI:
```bash
python -m compileall -q omni_prod tests
python -m pytest -q
python scripts/run_hostile_static_suite.py
python scripts/run_international_gate.py
```
Opt-in real administrative API test, with securely injected staging variables:
```bash
M5_QSTASH_LIVE=1 python -m pytest -q tests/integration/test_qstash_scheduler_live.py
```
The read-only test needs QSTASH_URL/QSTASH_TOKEN. The create/get/cancel test
additionally requires QSTASH_TEST_DESTINATION to be an operator-owned harmless
probe receiver. It briefly creates a uniquely named Feb-29 schedule and removes
it in finally. This is not a delivery test; do not use a customer action endpoint.

Official protocol sources checked:
- https://upstash.com/docs/qstash/api-reference/schedules/create-a-schedule
- https://upstash.com/docs/qstash/api-reference/schedules/delete-a-schedule
- https://upstash.com/docs/qstash/features/security

Test skips must be reported as missing live proof. Parent secrets are not read
in chat, committed to Git, emitted by this connector or returned in binding data.
