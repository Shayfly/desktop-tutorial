# Generated-app Cloudflare R2 credentials — staging only

## Change and decision
Select `OMNI_GENAPP_S3_PROVIDER=cloudflare_r2` to mint temporary S3 credentials
for one generated app/environment. The default `aws_sts` path is preserved.
No AWS role ARN or Cloudflare bearer API token is required for the R2 path.

The roadmap initially preferred Cloudflare's Temporary Credentials API. Current
official documentation says its action-level scope is supported only through
local signing. This implementation chooses that documented server-side signing
path to preserve the existing CRUD/list policy instead of broadening permissions
to the API's entire object-read-write preset. There is one R2 issuer, not two.

References checked 2026-10-06:
- https://developers.cloudflare.com/r2/api/s3/temporary-credentials/
- https://developers.cloudflare.com/r2/examples/authenticate-r2-temp-credentials/

The adapter accepts only the exact policy produced by `scoped_object_policy`:
one bucket and one `generated-apps/<app>/{preview,production}/` prefix.
Unknown statements, widened resources, extra actions and empty/wildcard prefixes
fail closed. Delegated actions are object get/put/delete and object listing.
Credential TTL is restricted to 1..3600 seconds.

## Preview configuration
All values below belong to Preview for project 148aiv28. Never commit real keys.
Keep the generated bucket separate from control-plane `omni-artifacts`.

| Variable | Type | Value |
|---|---|---|
| OMNI_GENAPP_S3_PROVIDER | Config | cloudflare_r2 |
| OMNI_GENAPP_S3_ENDPOINT | Config | HTTPS account endpoint shown in R2 |
| OMNI_GENAPP_S3_BUCKET | Config | 148ai-generated-assets |
| OMNI_GENAPP_S3_REGION | Config | auto |
| OMNI_GENAPP_S3_ACCESS_KEY | Secret | Dedicated bucket token Access Key ID |
| OMNI_GENAPP_S3_SECRET_KEY | Secret | Dedicated bucket token Secret Access Key |
| OMNI_GENAPP_S3_ACCESS_KEY_REF | Config | env:OMNI_GENAPP_S3_ACCESS_KEY |
| OMNI_GENAPP_S3_SECRET_KEY_REF | Config | env:OMNI_GENAPP_S3_SECRET_KEY |
| OMNI_GENAPP_S3_CREDENTIAL_TTL_SECONDS | Config, optional | 3600 default |

The parent Secret Access Key stays in the trusted control plane. R2 reuses the
parent Access Key ID for the temporary credential; its derived secret and session
token are different and scoped. Each issuance has a random nonce. All three
credential fields are needed for S3 requests. The generated secret-store writer
still performs write/read-back before binding verification.

## Validation and honest status
Unit protocol/wiring tests:
```bash
python -m pytest -q tests/test_r2_generated_credentials.py tests/test_m5_generated_app_storage_isolation.py tests/test_m5_managed_web_saas_profile.py
```
Full regression:
```bash
python -m compileall -q omni_prod tests
python -m pytest -q
python scripts/run_hostile_static_suite.py
python scripts/run_international_gate.py
```

Opt-in real R2 test, in a trusted environment with staging environment variables
already injected securely (never paste keys into chat or CLI command arguments):
```bash
M5_R2_LIVE=1 python -m pytest -q tests/integration/test_r2_generated_storage_live.py
```
This isolated storage test requires no scheduler, Vault or generated-app database.
It creates UUID-named objects, verifies scoped PUT/GET/list/DELETE and denies
GET/PUT/DELETE against existing cross-environment and cross-app sentinel objects.
Only a 403 counts as denial; cleanup removes the test objects using the parent
credentials in a finally block. The test reads the two parent keys through their
env: references. Secret-store backed parent references require a separate runner.

## Remaining limits
- Presence of configuration is PARTIAL, never live provider proof.
- The real R2 test has not run with founder-owned credentials.
- Existing bindings have a broader renewal/reuse issue recorded in the saved
  audit: a service may reuse a LIVE binding without checking its expiration.
  This change does not repair that issue or add automatic refresh; do not use
  this as production storage until expiry/renewal is implemented and tested.
- Removing stored credentials does not immediately revoke an already-issued
  R2 session; it expires at its TTL. Parent-token revocation invalidates its
  descendants and needs a separate operational drill.
- The existing production binding probe verifies write/delete and sibling
  denial. The opt-in test additionally proves read/list and cross-app isolation.
  Full runtime binding verification and continuous re-verification remain work.
- No generated-app publishing, model, worker, sandbox or scheduler claim is
  implied by this adapter.
