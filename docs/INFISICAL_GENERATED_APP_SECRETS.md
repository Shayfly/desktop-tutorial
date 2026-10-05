# Infisical generated-app secrets

This adds a backing store for the existing generated-app SecretWriter interface.
It does not provision databases, schedulers, object credentials, images, or pricing.

## Preview configuration

Set these in the Vercel Preview environment, using a dedicated Infisical Secrets
Management project and a Member machine identity with Universal Auth:

- OMNI_GENAPP_SECRET_STORE_PROVIDER=infisical
- OMNI_INFISICAL_BASE_URL=https://eu.infisical.com (use the region of your account)
- OMNI_INFISICAL_PROJECT_ID=<your project ID>
- OMNI_INFISICAL_CLIENT_ID=<Universal Auth Client ID, not the machine identity ID>
- OMNI_INFISICAL_CLIENT_SECRET=<store directly in Vercel; never in chat or Git>
- OMNI_INFISICAL_ENVIRONMENT=dev (the Development environment slug by default)

Redeploy Preview after configuration and tested source reach its deployment branch.
The client secret is exchanged for a short-lived bearer token. Tokens are cached
in process until shortly before expiry. Redirects are refused. Error messages
exclude provider response bodies, credentials, secret values, and exception chains.

## Reference compatibility and rollout

Persisted bindings continue using the existing logical vault:<mount>/data/<path>
reference format, so no database migration is required. In Infisical mode each
complete reference maps deterministically to GA_<sha256(reference)> at the root
of the configured Infisical environment. Full references include the generated
app's project/environment/kind; different references cannot share a secret name.

Vault remains the default. Merely setting OMNI_INFISICAL_* does not select it.
Changing provider does not copy existing Vault values. Do not change provider for
an environment with existing live bindings without a deliberate migration and
read-back verification of every reference. The same warning applies to changing
the Infisical project or environment.

The platform machine identity is trusted to manage these secrets. Generated apps
must never receive its Universal Auth credentials. It is not a per-app identity.
This adapter does not resolve unrelated control-plane/model provider secrets.

## Verification

Automated contract/regression checks:

    python -m pytest -q
    python scripts/run_hostile_static_suite.py
    python scripts/run_international_gate.py

The test fixture exercises documented HTTP requests without live credentials.
It is not live Infisical evidence. Static readiness is only PARTIAL.

Live acceptance requires authenticated access from the deployed server:
create a unique test secret using the selected writer; read the exact value back;
rotate and read back; delete it and prove it no longer resolves. Then provision a
real per-app auth binding and verify that only its reference is persisted.
Do not post secret values or Universal Auth credentials in screenshots/logs.

The remaining generated-app services require their own separate configuration
and live tests. In particular, the platform's existing Neon login and artifact R2
bucket/keys must not be reused as generated-app credentials. Unknown cost quotes
remain unknown; this adapter does not bypass authorization or budget gates.

API references:
- https://infisical.com/docs/api-reference/endpoints/universal-auth/login
- https://infisical.com/docs/api-reference/endpoints/secrets/create
- https://infisical.com/docs/api-reference/endpoints/secrets/read
- https://infisical.com/docs/api-reference/endpoints/secrets/update
- https://infisical.com/docs/api-reference/endpoints/secrets/delete
